"""
Subscription Service

Handles Stripe integration and user subscription management.
"""
import os
import logging
import stripe
from datetime import datetime
from typing import Optional, Dict, Any
from firebase_admin import firestore

from models.subscription import Subscription, SUBSCRIPTION_TIERS
from config.settings import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, FLASK_ENV

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

class SubscriptionService:
    """Service for managing user subscriptions with Stripe."""
    
    def __init__(self):
        self.db = firestore.client()
        self.collection_name = "user_subscriptions"
        self.webhook_secret = STRIPE_WEBHOOK_SECRET
        self.development_mode = FLASK_ENV == "development" and not STRIPE_SECRET_KEY
    
    def create_checkout_session(self, user_id: str, price_id: str, success_url: str, cancel_url: str) -> str:
        """
        Create a Stripe Checkout session for the user.
        
        Args:
            user_id: The user's Firebase UID
            price_id: Stripe price ID for the subscription
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels
            
        Returns:
            Stripe Checkout session URL
        """
        try:
            # Development mode: simulate checkout session creation
            if self.development_mode or not STRIPE_SECRET_KEY:
                logger.warning("Development mode: Simulating Stripe checkout session")
                # Create a mock subscription for testing
                tier = self._get_tier_from_price_id(price_id)
                subscription_data = Subscription(
                    subscription_tier=tier,
                    stripe_customer_id=f"cus_mock_{user_id}",
                    stripe_subscription_id=f"sub_mock_{user_id}",
                    status="active",
                    current_period_end=datetime.utcnow().replace(month=datetime.utcnow().month + 1),
                    last_updated=datetime.utcnow()
                )
                self._save_subscription(user_id, subscription_data)
                logger.info(f"Mock subscription created for user {user_id}: {tier}")
                return f"{success_url}&mock=true"
            
            # Get user email from their document or session
            user_email = self._get_user_email(user_id)
            
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user_email,
                metadata={
                    'user_id': user_id,
                    'firebase_uid': user_id
                }
            )
            
            logger.info(f"Created Stripe checkout session for user {user_id}: {session.id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {e}")
            
            # If it's a price not found error, suggest what to do
            if "No such price" in str(e):
                logger.error(f"Price ID '{price_id}' not found. Please create this price in your Stripe dashboard or update the price IDs in models/subscription.py")
                raise Exception(f"Stripe price not configured. Please check your Stripe dashboard and update price IDs in the code.")
            
            raise Exception(f"Payment processing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise
    
    def handle_stripe_webhook(self, event: Dict[str, Any]) -> bool:
        """
        Handle Stripe webhook events and update user subscription status.
        
        Args:
            event: Stripe webhook event data
            
        Returns:
            True if event was processed successfully
        """
        try:
            event_type = event['type']
            logger.info(f"Processing Stripe webhook event: {event_type}")
            
            if event_type == 'checkout.session.completed':
                self._handle_checkout_completed(event['data']['object'])
            elif event_type == 'customer.subscription.updated':
                self._handle_subscription_updated(event['data']['object'])
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event['data']['object'])
            elif event_type == 'invoice.payment_failed':
                self._handle_payment_failed(event['data']['object'])
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling Stripe webhook: {e}")
            return False
    
    def get_subscription_status(self, user_id: str) -> Optional[Subscription]:
        """
        Get the current subscription status for a user.
        
        Args:
            user_id: The user's Firebase UID
            
        Returns:
            Subscription object or None if not found
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return Subscription.from_dict(doc.to_dict())
            else:
                # Return default free subscription
                return Subscription(subscription_tier="free", status="active")
                
        except Exception as e:
            logger.error(f"Error getting subscription status for user {user_id}: {e}")
            # Return free subscription as fallback
            return Subscription(subscription_tier="free", status="active")
    
    def has_feature_access(self, user_id: str, feature: str) -> bool:
        """
        Check if user has access to a specific feature based on their subscription.
        
        Args:
            user_id: The user's Firebase UID
            feature: Feature to check access for
            
        Returns:
            True if user has access to the feature
        """
        subscription = self.get_subscription_status(user_id)
        if not subscription or not subscription.is_active():
            return False
        
        tier_config = SUBSCRIPTION_TIERS.get(subscription.subscription_tier, {})
        features = tier_config.get('features', [])
        
        return feature in features or subscription.subscription_tier == "pro"
    
    def get_tier_config(self, tier: str) -> Dict[str, Any]:
        """Get configuration for a subscription tier."""
        return SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
    
    def _handle_checkout_completed(self, session_data: Dict[str, Any]):
        """Handle successful checkout completion."""
        try:
            user_id = session_data.get('metadata', {}).get('user_id')
            customer_id = session_data.get('customer')
            subscription_id = session_data.get('subscription')
            
            if not user_id:
                logger.error("No user_id found in checkout session metadata")
                return
            
            # Retrieve subscription details from Stripe
            subscription = stripe.Subscription.retrieve(subscription_id)
            price_id = subscription['items']['data'][0]['price']['id']
            
            # Map price ID to tier
            tier = self._get_tier_from_price_id(price_id)
            
            # Create or update subscription record
            subscription_data = Subscription(
                subscription_tier=tier,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status="active",
                current_period_end=datetime.fromtimestamp(subscription['current_period_end']),
                last_updated=datetime.utcnow()
            )
            
            self._save_subscription(user_id, subscription_data)
            logger.info(f"Subscription activated for user {user_id}: {tier}")
            
        except Exception as e:
            logger.error(f"Error handling checkout completion: {e}")
    
    def _handle_subscription_updated(self, subscription_data: Dict[str, Any]):
        """Handle subscription updates from Stripe."""
        try:
            subscription_id = subscription_data.get('id')
            customer_id = subscription_data.get('customer')
            status = subscription_data.get('status')
            
            # Find user by Stripe subscription ID
            user_id = self._find_user_by_subscription_id(subscription_id)
            if not user_id:
                logger.error(f"No user found for subscription ID: {subscription_id}")
                return
            
            # Update subscription status
            current_subscription = self.get_subscription_status(user_id)
            if current_subscription:
                current_subscription.status = status
                current_subscription.current_period_end = datetime.fromtimestamp(
                    subscription_data.get('current_period_end', 0)
                )
                current_subscription.cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
                current_subscription.last_updated = datetime.utcnow()
                
                self._save_subscription(user_id, current_subscription)
                logger.info(f"Subscription updated for user {user_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error handling subscription update: {e}")
    
    def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]):
        """Handle subscription cancellation."""
        try:
            subscription_id = subscription_data.get('id')
            
            # Find user by Stripe subscription ID
            user_id = self._find_user_by_subscription_id(subscription_id)
            if not user_id:
                logger.error(f"No user found for subscription ID: {subscription_id}")
                return
            
            # Update subscription to canceled
            current_subscription = self.get_subscription_status(user_id)
            if current_subscription:
                current_subscription.status = "canceled"
                current_subscription.last_updated = datetime.utcnow()
                
                self._save_subscription(user_id, current_subscription)
                logger.info(f"Subscription canceled for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {e}")
    
    def _handle_payment_failed(self, invoice_data: Dict[str, Any]):
        """Handle failed payment."""
        try:
            subscription_id = invoice_data.get('subscription')
            
            # Find user by Stripe subscription ID
            user_id = self._find_user_by_subscription_id(subscription_id)
            if not user_id:
                logger.error(f"No user found for subscription ID: {subscription_id}")
                return
            
            # Update subscription to past_due
            current_subscription = self.get_subscription_status(user_id)
            if current_subscription:
                current_subscription.status = "past_due"
                current_subscription.last_updated = datetime.utcnow()
                
                self._save_subscription(user_id, current_subscription)
                logger.info(f"Subscription marked as past_due for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
    
    def _get_tier_from_price_id(self, price_id: str) -> str:
        """Map Stripe price ID to subscription tier."""
        for tier, config in SUBSCRIPTION_TIERS.items():
            if config.get('price_id') == price_id:
                return tier
        return "basic"  # Default fallback
    
    def _get_user_email(self, user_id: str) -> str:
        """Get user email from Firestore or return placeholder."""
        try:
            # Try to get email from users collection or wherever you store user data
            # For now, return a placeholder - you might want to implement this based on your user storage
            return f"user-{user_id}@example.com"
        except Exception:
            return f"user-{user_id}@example.com"
    
    def _find_user_by_subscription_id(self, subscription_id: str) -> Optional[str]:
        """Find user ID by Stripe subscription ID."""
        try:
            # Query Firestore for subscription with this Stripe subscription ID
            query = self.db.collection(self.collection_name).where(
                'stripe_subscription_id', '==', subscription_id
            ).limit(1)
            
            results = query.get()
            if results:
                return results[0].id
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by subscription ID: {e}")
            return None
    
    def _save_subscription(self, user_id: str, subscription: Subscription):
        """Save subscription data to Firestore."""
        try:
            doc_ref = self.db.collection(self.collection_name).document(user_id)
            doc_ref.set(subscription.to_dict(), merge=True)
            logger.info(f"Subscription saved for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving subscription for user {user_id}: {e}")
            raise
