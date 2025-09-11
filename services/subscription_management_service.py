"""
Subscription Management Service

This service handles subscription upgrades, downgrades, and tier changes
according to industry standards for SaaS platforms.

Industry Standard Features:
- Instant upgrades with prorated billing
- Scheduled downgrades at period end  
- Multiple subscription tiers support
- Proper billing calculations
- Comprehensive audit logging
"""

import os
import logging
import stripe
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from firebase_admin import firestore
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

class SubscriptionManagementService:
    """Service for managing subscription upgrades, downgrades, and tier changes."""
    
    # Define subscription tiers with pricing and features
    SUBSCRIPTION_TIERS = {
        'free': {
            'plan_id': 'zero',
            'name': 'Free',
            'price_monthly': 0,
            'price_annual': 0,
            'features': {
                'chat_messages': 5,
                'searches': 10,
                'datasets_analyzed': 2,
                'videos_generated': 1,
                'ai_models': ['gpt-3.5-turbo', 'gemini-1.0-pro'],
                'export_enabled': False,
                'advanced_analytics': False,
                'priority_support': False
            }
        },
        'basic': {
            'plan_id': 'five',
            'name': 'Basic',
            'price_monthly': 5,
            'price_annual': 50,  # 2 months free
            'stripe_price_monthly': os.getenv('STRIPE_BASIC_MONTHLY_PRICE_ID'),
            'stripe_price_annual': os.getenv('STRIPE_BASIC_ANNUAL_PRICE_ID'),
            'features': {
                'chat_messages': -1,  # Unlimited
                'searches': -1,
                'datasets_analyzed': -1,
                'videos_generated': 10,
                'ai_models': 'all',
                'export_enabled': True,
                'advanced_analytics': True,
                'priority_support': False
            }
        },
        'pro': {
            'plan_id': 'fifteen',
            'name': 'Pro',
            'price_monthly': 15,
            'price_annual': 150,  # 2 months free
            'stripe_price_monthly': os.getenv('STRIPE_PRO_MONTHLY_PRICE_ID'),
            'stripe_price_annual': os.getenv('STRIPE_PRO_ANNUAL_PRICE_ID'),
            'features': {
                'chat_messages': -1,
                'searches': -1,
                'datasets_analyzed': -1,
                'videos_generated': 50,
                'ai_models': 'all',
                'export_enabled': True,
                'advanced_analytics': True,
                'priority_support': True,
                'custom_personalities': True,
                'api_access': True
            }
        },
        'enterprise': {
            'plan_id': 'fifty',
            'name': 'Enterprise',
            'price_monthly': 50,
            'price_annual': 500,  # 2 months free
            'stripe_price_monthly': os.getenv('STRIPE_ENTERPRISE_MONTHLY_PRICE_ID'),
            'stripe_price_annual': os.getenv('STRIPE_ENTERPRISE_ANNUAL_PRICE_ID'),
            'features': {
                'chat_messages': -1,
                'searches': -1,
                'datasets_analyzed': -1,
                'videos_generated': -1,  # Unlimited
                'ai_models': 'all',
                'export_enabled': True,
                'advanced_analytics': True,
                'priority_support': True,
                'custom_personalities': True,
                'api_access': True,
                'white_label': True,
                'dedicated_support': True
            }
        }
    }
    
    def __init__(self):
        """Initialize the subscription management service."""
        self.stripe_service = StripeService()
        self.db = self.stripe_service.db
        
        logger.info("Subscription management service initialized")
    
    def get_subscription_tiers(self) -> Dict[str, Any]:
        """Get all available subscription tiers with pricing and features."""
        return self.SUBSCRIPTION_TIERS
    
    def get_current_subscription_tier(self, firebase_uid: str) -> str:
        """
        Get the current subscription tier for a user.
        
        Args:
            firebase_uid: User's Firebase UID
            
        Returns:
            Tier name (free, basic, pro, enterprise)
        """
        if not self.db:
            return 'free'
        
        try:
            # Get current subscription status
            status = self.stripe_service.get_subscription_status(firebase_uid)
            plan_id = status.get('plan_id', 'zero')
            
            # Map plan_id to tier
            for tier_name, tier_data in self.SUBSCRIPTION_TIERS.items():
                if tier_data['plan_id'] == plan_id:
                    return tier_name
            
            return 'free'  # Default fallback
            
        except Exception as e:
            logger.error(f"Failed to get subscription tier for user {firebase_uid}: {e}")
            return 'free'
    
    def can_upgrade_immediately(self, from_tier: str, to_tier: str) -> bool:
        """
        Check if a subscription upgrade can be processed immediately.
        
        Args:
            from_tier: Current subscription tier
            to_tier: Target subscription tier
            
        Returns:
            True if immediate upgrade is allowed
        """
        if from_tier == to_tier:
            return False
        
        # Get tier pricing
        from_price = self.SUBSCRIPTION_TIERS.get(from_tier, {}).get('price_monthly', 0)
        to_price = self.SUBSCRIPTION_TIERS.get(to_tier, {}).get('price_monthly', 0)
        
        # Upgrades (higher price) can be immediate
        return to_price > from_price
    
    def should_schedule_downgrade(self, from_tier: str, to_tier: str) -> bool:
        """
        Check if a subscription change should be scheduled for period end.
        
        Args:
            from_tier: Current subscription tier
            to_tier: Target subscription tier
            
        Returns:
            True if change should be scheduled
        """
        if from_tier == to_tier:
            return False
        
        # Get tier pricing
        from_price = self.SUBSCRIPTION_TIERS.get(from_tier, {}).get('price_monthly', 0)
        to_price = self.SUBSCRIPTION_TIERS.get(to_tier, {}).get('price_monthly', 0)
        
        # Downgrades (lower price) should be scheduled
        return to_price < from_price
    
    def calculate_prorated_amount(self, firebase_uid: str, from_tier: str, to_tier: str) -> Dict[str, Any]:
        """
        Calculate prorated amount for subscription upgrade.
        
        Args:
            firebase_uid: User's Firebase UID
            from_tier: Current subscription tier
            to_tier: Target subscription tier
            
        Returns:
            Dict with prorated calculation details
        """
        try:
            # Get current subscription
            current_subscription = self._get_current_subscription(firebase_uid)
            if not current_subscription:
                return {'error': 'No active subscription found'}
            
            # Get pricing information
            from_price = self.SUBSCRIPTION_TIERS.get(from_tier, {}).get('price_monthly', 0)
            to_price = self.SUBSCRIPTION_TIERS.get(to_tier, {}).get('price_monthly', 0)
            
            if to_price <= from_price:
                return {'error': 'Cannot calculate prorated amount for downgrade'}
            
            # Calculate days remaining in current period
            current_time = datetime.now(timezone.utc)
            period_end = current_subscription.get('current_period_end')
            
            if not period_end:
                return {'error': 'No period end date found'}
            
            # Convert to datetime if needed
            if hasattr(period_end, 'timestamp'):
                period_end_dt = datetime.fromtimestamp(period_end.timestamp(), tz=timezone.utc)
            else:
                period_end_dt = period_end
            
            days_remaining = (period_end_dt - current_time).days
            if days_remaining < 0:
                days_remaining = 0
            
            # Calculate prorated amounts
            daily_from_rate = from_price / 30  # Approximate monthly rate
            daily_to_rate = to_price / 30
            
            unused_credit = daily_from_rate * days_remaining
            new_charge = daily_to_rate * days_remaining
            prorated_amount = new_charge - unused_credit
            
            return {
                'from_tier': from_tier,
                'to_tier': to_tier,
                'from_price': from_price,
                'to_price': to_price,
                'days_remaining': days_remaining,
                'unused_credit': round(unused_credit, 2),
                'new_charge': round(new_charge, 2),
                'prorated_amount': round(max(0, prorated_amount), 2),
                'period_end': period_end_dt.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate prorated amount: {e}")
            return {'error': str(e)}
    
    def upgrade_subscription(self, firebase_uid: str, to_tier: str, billing_interval: str = 'monthly') -> Dict[str, Any]:
        """
        Upgrade subscription with immediate prorated billing.
        
        Args:
            firebase_uid: User's Firebase UID
            to_tier: Target subscription tier
            billing_interval: 'monthly' or 'annual'
            
        Returns:
            Dict with upgrade result
        """
        try:
            logger.info(f"🔄 Processing upgrade for user {firebase_uid} to {to_tier}")
            
            # Get current tier
            current_tier = self.get_current_subscription_tier(firebase_uid)
            
            # Validate upgrade
            if not self.can_upgrade_immediately(current_tier, to_tier):
                return {
                    'success': False,
                    'error': 'Invalid upgrade path',
                    'message': f'Cannot upgrade from {current_tier} to {to_tier}'
                }
            
            # Get target tier configuration
            target_config = self.SUBSCRIPTION_TIERS.get(to_tier)
            if not target_config:
                return {
                    'success': False,
                    'error': 'Invalid tier',
                    'message': f'Tier {to_tier} not found'
                }
            
            # Get Stripe price ID
            price_key = f'stripe_price_{billing_interval}'
            stripe_price_id = target_config.get(price_key)
            
            if not stripe_price_id:
                return {
                    'success': False,
                    'error': 'Price not configured',
                    'message': f'No {billing_interval} price configured for {to_tier} tier'
                }
            
            # Get current subscription
            current_subscription = self._get_current_subscription(firebase_uid)
            if not current_subscription:
                # No current subscription - create new one
                return self._create_new_subscription(firebase_uid, to_tier, stripe_price_id, billing_interval)
            
            # Upgrade existing subscription
            return self._upgrade_existing_subscription(
                firebase_uid, 
                current_subscription, 
                to_tier, 
                stripe_price_id, 
                billing_interval
            )
            
        except Exception as e:
            logger.error(f"Failed to upgrade subscription: {e}")
            return {
                'success': False,
                'error': 'Upgrade failed',
                'message': str(e)
            }
    
    def schedule_downgrade(self, firebase_uid: str, to_tier: str) -> Dict[str, Any]:
        """
        Schedule a subscription downgrade at the end of the current period.
        
        Args:
            firebase_uid: User's Firebase UID
            to_tier: Target subscription tier
            
        Returns:
            Dict with scheduling result
        """
        try:
            logger.info(f"📅 Scheduling downgrade for user {firebase_uid} to {to_tier}")
            
            # Get current tier
            current_tier = self.get_current_subscription_tier(firebase_uid)
            
            # Validate downgrade
            if not self.should_schedule_downgrade(current_tier, to_tier):
                return {
                    'success': False,
                    'error': 'Invalid downgrade path',
                    'message': f'Cannot downgrade from {current_tier} to {to_tier}'
                }
            
            # Get current subscription
            current_subscription = self._get_current_subscription(firebase_uid)
            if not current_subscription:
                return {
                    'success': False,
                    'error': 'No active subscription',
                    'message': 'No active subscription found to downgrade'
                }
            
            # Schedule the downgrade
            subscription_id = current_subscription.get('stripe_subscription_id')
            
            # Store downgrade instruction in Firebase
            downgrade_ref = self.db.collection('scheduled_downgrades').document(subscription_id)
            downgrade_ref.set({
                'firebase_uid': firebase_uid,
                'subscription_id': subscription_id,
                'current_tier': current_tier,
                'target_tier': to_tier,
                'scheduled_at': firestore.SERVER_TIMESTAMP,
                'effective_date': current_subscription.get('current_period_end'),
                'status': 'scheduled'
            })
            
            # Update subscription to cancel at period end if downgrading to free
            if to_tier == 'free':
                success = self.stripe_service.cancel_subscription(firebase_uid)
                if not success:
                    return {
                        'success': False,
                        'error': 'Failed to cancel subscription',
                        'message': 'Could not schedule cancellation in Stripe'
                    }
            
            logger.info(f"✅ Downgrade scheduled successfully for subscription {subscription_id}")
            return {
                'success': True,
                'message': f'Downgrade to {to_tier} scheduled for end of current billing period',
                'effective_date': current_subscription.get('current_period_end'),
                'current_tier': current_tier,
                'target_tier': to_tier
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule downgrade: {e}")
            return {
                'success': False,
                'error': 'Scheduling failed',
                'message': str(e)
            }
    
    def process_scheduled_downgrades(self) -> Dict[str, Any]:
        """
        Process all scheduled downgrades that should take effect now.
        
        Returns:
            Dict with processing results
        """
        logger.info("🔄 Processing scheduled downgrades...")
        
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        if not self.db:
            return results
        
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get all scheduled downgrades that should be effective now
            scheduled_downgrades = self.db.collection('scheduled_downgrades')\
                .where('status', '==', 'scheduled')\
                .where('effective_date', '<=', current_time)\
                .get()
            
            results['total_processed'] = len(scheduled_downgrades)
            
            for downgrade_doc in scheduled_downgrades:
                downgrade_data = downgrade_doc.to_dict()
                result = self._execute_scheduled_downgrade(downgrade_data, downgrade_doc.reference)
                
                if result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append(result)
            
            logger.info(f"✅ Processed {results['total_processed']} scheduled downgrades: {results['successful']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Failed to process scheduled downgrades: {e}")
            results['failed'] = 1
            return results
    
    def _get_current_subscription(self, firebase_uid: str) -> Optional[Dict[str, Any]]:
        """Get the current active subscription for a user."""
        if not self.db:
            return None
        
        try:
            sub_docs = self.db.collection('user_subscriptions')\
                .where('firebase_uid', '==', firebase_uid)\
                .where('status', 'in', ['active', 'trialing'])\
                .limit(1).get()
            
            if sub_docs:
                return sub_docs[0].to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Failed to get current subscription: {e}")
            return None
    
    def _create_new_subscription(self, firebase_uid: str, tier: str, stripe_price_id: str, billing_interval: str) -> Dict[str, Any]:
        """Create a new subscription for a user."""
        # This would typically redirect to Stripe Checkout for new subscriptions
        # For now, return checkout session URL
        user_email = self._get_user_email(firebase_uid)
        if not user_email:
            return {
                'success': False,
                'error': 'User email not found',
                'message': 'Cannot create subscription without user email'
            }
        
        # Create checkout session with the specific price
        from urllib.parse import urljoin
        base_url = os.getenv('BASE_URL', 'http://localhost:8080')
        success_url = urljoin(base_url, '/subscription/success')
        cancel_url = urljoin(base_url, '/subscription/cancel')
        
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user_email,
                metadata={
                    'firebase_uid': firebase_uid,
                    'tier': tier,
                    'billing_interval': billing_interval
                }
            )
            
            return {
                'success': True,
                'requires_payment': True,
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            }
            
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return {
                'success': False,
                'error': 'Checkout creation failed',
                'message': str(e)
            }
    
    def _upgrade_existing_subscription(self, firebase_uid: str, current_subscription: Dict[str, Any], 
                                     to_tier: str, stripe_price_id: str, billing_interval: str) -> Dict[str, Any]:
        """Upgrade an existing subscription with prorated billing."""
        try:
            subscription_id = current_subscription.get('stripe_subscription_id')
            
            # Modify the subscription in Stripe
            stripe_subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': stripe.Subscription.retrieve(subscription_id).items.data[0].id,
                    'price': stripe_price_id,
                }],
                proration_behavior='create_prorations',  # Create prorated invoice
                metadata={
                    'tier': to_tier,
                    'billing_interval': billing_interval,
                    'upgraded_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Update Firebase with new tier information
            sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
            sub_ref.update({
                'plan_id': self.SUBSCRIPTION_TIERS[to_tier]['plan_id'],
                'price_id': stripe_price_id,
                'tier': to_tier,
                'billing_interval': billing_interval,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_upgrade': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"✅ Successfully upgraded subscription {subscription_id} to {to_tier}")
            return {
                'success': True,
                'message': f'Successfully upgraded to {to_tier}',
                'subscription_id': subscription_id,
                'new_tier': to_tier,
                'billing_interval': billing_interval
            }
            
        except Exception as e:
            logger.error(f"Failed to upgrade existing subscription: {e}")
            return {
                'success': False,
                'error': 'Upgrade failed',
                'message': str(e)
            }
    
    def _execute_scheduled_downgrade(self, downgrade_data: Dict[str, Any], downgrade_ref) -> Dict[str, Any]:
        """Execute a scheduled downgrade."""
        try:
            firebase_uid = downgrade_data.get('firebase_uid')
            target_tier = downgrade_data.get('target_tier')
            subscription_id = downgrade_data.get('subscription_id')
            
            logger.info(f"Executing scheduled downgrade for user {firebase_uid} to {target_tier}")
            
            if target_tier == 'free':
                # Ensure free subscription record exists
                user_email = self._get_user_email(firebase_uid)
                success = self.stripe_service.ensure_free_subscription(firebase_uid, user_email)
                
                if success:
                    # Mark the downgrade as completed
                    downgrade_ref.update({
                        'status': 'completed',
                        'completed_at': firestore.SERVER_TIMESTAMP
                    })
                    
                    return {
                        'success': True,
                        'subscription_id': subscription_id,
                        'firebase_uid': firebase_uid,
                        'target_tier': target_tier,
                        'message': 'Successfully downgraded to free tier'
                    }
                else:
                    return {
                        'success': False,
                        'subscription_id': subscription_id,
                        'firebase_uid': firebase_uid,
                        'error': 'Failed to create free subscription record'
                    }
            else:
                # For paid tier downgrades, would need to modify Stripe subscription
                # This is more complex and would require additional logic
                downgrade_ref.update({
                    'status': 'requires_manual_processing',
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                return {
                    'success': False,
                    'subscription_id': subscription_id,
                    'firebase_uid': firebase_uid,
                    'error': 'Paid tier downgrades require manual processing'
                }
                
        except Exception as e:
            logger.error(f"Failed to execute scheduled downgrade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_user_email(self, firebase_uid: str) -> Optional[str]:
        """Get user email from Firebase."""
        if not self.db:
            return None
        
        try:
            user_doc = self.db.collection('users').document(firebase_uid).get()
            if user_doc.exists:
                return user_doc.to_dict().get('email')
            return None
        except Exception as e:
            logger.error(f"Failed to get user email: {e}")
            return None