"""
Rate limiting and security controls for token operations.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from firebase_admin import firestore

logger = logging.getLogger(__name__)

class TokenSecurityService:
    """Security controls for token operations."""
    
    # Rate limits
    MAX_PURCHASES_PER_HOUR = 5
    MAX_PURCHASES_PER_DAY = 20
    MAX_TOKENS_PER_PURCHASE = 10000
    
    # Package definitions with price validation
    # CRITICAL: Must match TOKEN_PACKAGES in api/token_routes.py exactly!
    VALID_PACKAGES = {
        'starter': {'tokens': 50, 'price_cents': 499},      # $4.99 - Starter Pack
        'popular': {'tokens': 110, 'price_cents': 999},     # $9.99 - Popular Pack (100 + 10 bonus)
        'pro': {'tokens': 250, 'price_cents': 1999},        # $19.99 - Pro Pack (200 + 50 bonus)
        'creator': {'tokens': 700, 'price_cents': 4999},    # $49.99 - Creator Pack (500 + 200 bonus)
    }
    
    def __init__(self, db: firestore.Client):
        """Initialize security service."""
        self.db = db
        
    def validate_purchase_rate_limit(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if user has exceeded purchase rate limits.
        
        Returns:
            (allowed, error_message) tuple
        """
        try:
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            one_day_ago = now - timedelta(days=1)
            
            # Query recent purchases
            purchases_last_hour = self.db.collection('transactions')\
                .where(filter=firestore.FieldFilter('userId', '==', user_id))\
                .where(filter=firestore.FieldFilter('type', '==', 'purchase'))\
                .where(filter=firestore.FieldFilter('timestamp', '>=', one_hour_ago))\
                .count().get()
            
            purchases_last_day = self.db.collection('transactions')\
                .where(filter=firestore.FieldFilter('userId', '==', user_id))\
                .where(filter=firestore.FieldFilter('type', '==', 'purchase'))\
                .where(filter=firestore.FieldFilter('timestamp', '>=', one_day_ago))\
                .count().get()
            
            hour_count = purchases_last_hour[0][0].value
            day_count = purchases_last_day[0][0].value
            
            if hour_count >= self.MAX_PURCHASES_PER_HOUR:
                logger.warning(f"🚨 Rate limit exceeded: {user_id} has {hour_count} purchases in last hour")
                return False, f"Rate limit exceeded: Maximum {self.MAX_PURCHASES_PER_HOUR} purchases per hour"
            
            if day_count >= self.MAX_PURCHASES_PER_DAY:
                logger.warning(f"🚨 Rate limit exceeded: {user_id} has {day_count} purchases in last day")
                return False, f"Rate limit exceeded: Maximum {self.MAX_PURCHASES_PER_DAY} purchases per day"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to check rate limits for {user_id}: {e}", exc_info=True)
            # Fail open - don't block legitimate purchases due to rate limit check errors
            return True, None
    
    def validate_package(
        self,
        package_id: str,
        tokens: int,
        amount_paid_cents: int
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that package details match expected values.
        
        Args:
            package_id: Package identifier (e.g., 'starter')
            tokens: Number of tokens claimed
            amount_paid_cents: Amount paid in cents
            
        Returns:
            (valid, error_message) tuple
        """
        if package_id not in self.VALID_PACKAGES:
            logger.error(f"❌ Invalid package ID: {package_id}")
            return False, f"Invalid package: {package_id}"
        
        expected = self.VALID_PACKAGES[package_id]
        
        if tokens != expected['tokens']:
            logger.error(f"❌ Token mismatch for {package_id}: expected {expected['tokens']}, got {tokens}")
            return False, "Token amount validation failed"
        
        if amount_paid_cents != expected['price_cents']:
            logger.error(f"❌ Price mismatch for {package_id}: expected {expected['price_cents']} cents, got {amount_paid_cents}")
            return False, "Price validation failed"
        
        return True, None
    
    def validate_token_amount(self, amount: int) -> tuple[bool, Optional[str]]:
        """
        Validate token amount is within acceptable bounds.
        
        Returns:
            (valid, error_message) tuple
        """
        if amount <= 0:
            return False, "Token amount must be positive"
        
        if amount > self.MAX_TOKENS_PER_PURCHASE:
            logger.warning(f"🚨 Excessive token amount: {amount}")
            return False, f"Token amount exceeds maximum of {self.MAX_TOKENS_PER_PURCHASE}"
        
        return True, None
    
    def log_suspicious_activity(
        self,
        user_id: str,
        activity_type: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log suspicious activity for investigation.
        
        Args:
            user_id: User ID involved
            activity_type: Type of suspicious activity
            details: Additional context
        """
        try:
            self.db.collection('security_alerts').add({
                'userId': user_id,
                'activityType': activity_type,
                'details': details,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'severity': 'medium',
                'status': 'pending_review'
            })
            
            logger.warning(f"🚨 SECURITY ALERT: {activity_type} for user {user_id}: {details}")
            
        except Exception as e:
            logger.error(f"Failed to log suspicious activity: {e}", exc_info=True)
