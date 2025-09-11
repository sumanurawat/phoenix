"""
Subscription Expiration Service

This service handles automated subscription expiration checking and management.
It ensures that subscription status in Firebase is always up-to-date with actual
subscription periods, even if webhooks fail.

Industry Standard Features:
- Daily automated expiration checks
- Grace period handling for failed payments  
- Automatic downgrade of expired subscriptions
- Comprehensive logging and monitoring
- Webhook failure recovery
"""

import os
import logging
import stripe
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from firebase_admin import firestore
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

class SubscriptionExpirationService:
    """Service for managing subscription expiration and status synchronization."""
    
    def __init__(self):
        """Initialize the expiration service."""
        self.stripe_service = StripeService()
        self.db = self.stripe_service.db
        
        # Configure grace periods (industry standard: 3-7 days)
        self.grace_period_days = int(os.getenv('SUBSCRIPTION_GRACE_PERIOD_DAYS', '7'))
        
        # Configure check intervals
        self.check_interval_hours = int(os.getenv('SUBSCRIPTION_CHECK_INTERVAL_HOURS', '24'))
        
        logger.info(f"Subscription expiration service initialized with {self.grace_period_days} day grace period")
    
    def check_all_expired_subscriptions(self) -> Dict[str, Any]:
        """
        Check all subscriptions for expiration and handle accordingly.
        
        Returns:
            Dict with results of the expiration check process
        """
        logger.info("🔍 Starting automated subscription expiration check...")
        
        results = {
            'total_checked': 0,
            'expired_found': 0,
            'downgraded': 0,
            'in_grace_period': 0,
            'sync_needed': 0,
            'errors': 0,
            'details': []
        }
        
        if not self.db or not self.stripe_service.is_configured:
            logger.error("Database or Stripe not configured - cannot check subscriptions")
            return results
        
        try:
            # Get all active/trialing subscriptions from Firebase
            active_subscriptions = self.db.collection('user_subscriptions')\
                .where('status', 'in', ['active', 'trialing'])\
                .get()
            
            results['total_checked'] = len(active_subscriptions)
            logger.info(f"📋 Found {results['total_checked']} active subscriptions to check")
            
            current_time = datetime.now(timezone.utc)
            
            for sub_doc in active_subscriptions:
                try:
                    sub_data = sub_doc.to_dict()
                    result = self._check_single_subscription(sub_data, current_time)
                    
                    # Update counters based on result
                    if result['action'] == 'expired_downgraded':
                        results['expired_found'] += 1
                        results['downgraded'] += 1
                    elif result['action'] == 'grace_period':
                        results['expired_found'] += 1
                        results['in_grace_period'] += 1
                    elif result['action'] == 'sync_needed':
                        results['sync_needed'] += 1
                    elif result['action'] == 'error':
                        results['errors'] += 1
                    
                    results['details'].append(result)
                    
                except Exception as e:
                    logger.error(f"Error checking subscription {sub_doc.id}: {e}")
                    results['errors'] += 1
                    results['details'].append({
                        'subscription_id': sub_doc.id,
                        'action': 'error',
                        'error': str(e)
                    })
            
            logger.info(f"✅ Expiration check completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to check expired subscriptions: {e}")
            results['errors'] = 1
            return results
    
    def _check_single_subscription(self, sub_data: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
        """
        Check a single subscription for expiration.
        
        Args:
            sub_data: Subscription data from Firebase
            current_time: Current UTC timestamp
            
        Returns:
            Dict with details about the action taken
        """
        firebase_uid = sub_data.get('firebase_uid')
        subscription_id = sub_data.get('stripe_subscription_id')
        current_period_end = sub_data.get('current_period_end')
        cancel_at_period_end = sub_data.get('cancel_at_period_end', False)
        
        result = {
            'firebase_uid': firebase_uid,
            'subscription_id': subscription_id,
            'action': 'no_action',
            'message': 'Subscription is current'
        }
        
        try:
            # Check if subscription has expired
            if current_period_end:
                # Convert Firestore timestamp to datetime if needed
                if hasattr(current_period_end, 'timestamp'):
                    period_end_dt = datetime.fromtimestamp(current_period_end.timestamp(), tz=timezone.utc)
                elif isinstance(current_period_end, datetime):
                    period_end_dt = current_period_end.replace(tzinfo=timezone.utc) if current_period_end.tzinfo is None else current_period_end
                else:
                    logger.error(f"Invalid current_period_end format for subscription {subscription_id}")
                    result['action'] = 'error'
                    result['message'] = 'Invalid period end format'
                    return result
                
                # Check if subscription has expired
                if current_time > period_end_dt:
                    grace_period_end = period_end_dt + timedelta(days=self.grace_period_days)
                    
                    if cancel_at_period_end or current_time > grace_period_end:
                        # Subscription should be downgraded
                        result = self._downgrade_expired_subscription(firebase_uid, subscription_id, sub_data)
                    else:
                        # Still in grace period
                        days_in_grace = (current_time - period_end_dt).days
                        result.update({
                            'action': 'grace_period',
                            'message': f'Subscription expired but in grace period (day {days_in_grace}/{self.grace_period_days})'
                        })
                        logger.warning(f"Subscription {subscription_id} in grace period (day {days_in_grace})")
                
                # Verify subscription status with Stripe for accuracy
                elif self._should_sync_with_stripe(sub_data):
                    sync_result = self._sync_subscription_with_stripe(subscription_id, sub_data)
                    if sync_result:
                        result.update({
                            'action': 'sync_needed',
                            'message': 'Subscription synced with Stripe'
                        })
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking subscription {subscription_id}: {e}")
            result.update({
                'action': 'error',
                'message': str(e)
            })
            return result
    
    def _downgrade_expired_subscription(self, firebase_uid: str, subscription_id: str, sub_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Downgrade an expired subscription to free tier.
        
        Args:
            firebase_uid: User's Firebase UID
            subscription_id: Stripe subscription ID
            sub_data: Current subscription data
            
        Returns:
            Dict with details about the downgrade action
        """
        try:
            logger.info(f"🔄 Downgrading expired subscription {subscription_id} for user {firebase_uid}")
            
            # Update subscription status in Firebase
            sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
            sub_ref.update({
                'status': 'expired',
                'expired_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'downgrade_reason': 'automatic_expiration'
            })
            
            # Ensure user has a free subscription record for continued access
            success = self.stripe_service.ensure_free_subscription(
                firebase_uid, 
                sub_data.get('email')
            )
            
            if success:
                logger.info(f"✅ Successfully downgraded subscription {subscription_id}")
                return {
                    'firebase_uid': firebase_uid,
                    'subscription_id': subscription_id,
                    'action': 'expired_downgraded',
                    'message': 'Subscription expired and user downgraded to free tier'
                }
            else:
                logger.error(f"Failed to create free subscription for user {firebase_uid}")
                return {
                    'firebase_uid': firebase_uid,
                    'subscription_id': subscription_id,
                    'action': 'error',
                    'message': 'Failed to create free subscription record'
                }
                
        except Exception as e:
            logger.error(f"Failed to downgrade subscription {subscription_id}: {e}")
            return {
                'firebase_uid': firebase_uid,
                'subscription_id': subscription_id,
                'action': 'error',
                'message': f'Downgrade failed: {str(e)}'
            }
    
    def _should_sync_with_stripe(self, sub_data: Dict[str, Any]) -> bool:
        """
        Determine if a subscription should be synced with Stripe.
        
        Args:
            sub_data: Subscription data from Firebase
            
        Returns:
            True if sync is needed
        """
        # Sync every 24 hours or if never synced
        last_updated = sub_data.get('updated_at')
        if not last_updated:
            return True
        
        # Convert to datetime if needed
        if hasattr(last_updated, 'timestamp'):
            last_updated_dt = datetime.fromtimestamp(last_updated.timestamp(), tz=timezone.utc)
        else:
            last_updated_dt = last_updated
        
        hours_since_update = (datetime.now(timezone.utc) - last_updated_dt).total_seconds() / 3600
        return hours_since_update >= self.check_interval_hours
    
    def _sync_subscription_with_stripe(self, subscription_id: str, sub_data: Dict[str, Any]) -> bool:
        """
        Sync subscription data with Stripe to ensure accuracy.
        
        Args:
            subscription_id: Stripe subscription ID
            sub_data: Current subscription data from Firebase
            
        Returns:
            True if sync was successful
        """
        try:
            # Retrieve current subscription status from Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Check if status has changed
            firebase_status = sub_data.get('status')
            stripe_status = stripe_subscription.status
            
            if firebase_status != stripe_status:
                logger.info(f"📝 Syncing subscription {subscription_id}: {firebase_status} → {stripe_status}")
                
                # Update Firebase with current Stripe data
                sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
                update_data = {
                    'status': stripe_status,
                    'current_period_start': datetime.fromtimestamp(
                        stripe_subscription.current_period_start, tz=timezone.utc
                    ),
                    'current_period_end': datetime.fromtimestamp(
                        stripe_subscription.current_period_end, tz=timezone.utc
                    ),
                    'cancel_at_period_end': stripe_subscription.cancel_at_period_end,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'last_stripe_sync': firestore.SERVER_TIMESTAMP
                }
                
                sub_ref.update(update_data)
                logger.info(f"✅ Subscription {subscription_id} synced successfully")
                return True
            else:
                # Just update the sync timestamp
                sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
                sub_ref.update({
                    'last_stripe_sync': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                return False
                
        except stripe.error.InvalidRequestError as e:
            if 'No such subscription' in str(e):
                logger.warning(f"Subscription {subscription_id} not found in Stripe - marking as canceled")
                # Mark subscription as canceled since it doesn't exist in Stripe
                sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
                sub_ref.update({
                    'status': 'canceled',
                    'canceled_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'cancellation_reason': 'not_found_in_stripe'
                })
                return True
            else:
                logger.error(f"Stripe API error syncing subscription {subscription_id}: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to sync subscription {subscription_id} with Stripe: {e}")
            return False
    
    def get_expiration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of subscription expiration status.
        
        Returns:
            Dict with expiration statistics
        """
        if not self.db:
            return {'error': 'Database not available'}
        
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get all active subscriptions
            active_subs = self.db.collection('user_subscriptions')\
                .where('status', 'in', ['active', 'trialing'])\
                .get()
            
            summary = {
                'total_active': len(active_subs),
                'expiring_soon': 0,  # Within 7 days
                'in_grace_period': 0,  # Expired but within grace period
                'needs_attention': 0,  # Requires manual review
                'last_check': current_time.isoformat()
            }
            
            for sub_doc in active_subs:
                sub_data = sub_doc.to_dict()
                current_period_end = sub_data.get('current_period_end')
                
                if current_period_end:
                    if hasattr(current_period_end, 'timestamp'):
                        period_end_dt = datetime.fromtimestamp(current_period_end.timestamp(), tz=timezone.utc)
                    elif isinstance(current_period_end, datetime):
                        period_end_dt = current_period_end.replace(tzinfo=timezone.utc) if current_period_end.tzinfo is None else current_period_end
                    else:
                        summary['needs_attention'] += 1
                        continue
                    
                    days_until_expiry = (period_end_dt - current_time).days
                    
                    if days_until_expiry < 0:
                        # Already expired
                        days_in_grace = abs(days_until_expiry)
                        if days_in_grace <= self.grace_period_days:
                            summary['in_grace_period'] += 1
                        else:
                            summary['needs_attention'] += 1
                    elif days_until_expiry <= 7:
                        summary['expiring_soon'] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get expiration summary: {e}")
            return {'error': str(e)}