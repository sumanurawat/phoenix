"""
Stripe Service for Payment Processing and Subscription Management

This service handles all Stripe-related operations including:
- Customer management
- Subscription lifecycle management
- Webhook processing
- Payment processing
"""

import os
import logging
from typing import Dict, Any, Optional, List
from firebase_admin import firestore

logger = logging.getLogger(__name__)

# Import Stripe only if available
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("Stripe library not available. Running in development mode.")


class StripeService:
    """Service for handling Stripe payment operations and subscription management."""
    
    def __init__(self):
        """Initialize Stripe service with configuration."""
        self.stripe_configured = self._configure_stripe()
        self.db = firestore.client()
        
    def _configure_stripe(self) -> bool:
        """Configure Stripe with API keys."""
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe library not available")
            return False
            
        secret_key = os.getenv('STRIPE_SECRET_KEY')
        self.publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        self.premium_monthly_price_id = os.getenv('STRIPE_PREMIUM_MONTHLY_PRICE_ID')
        
        if not secret_key:
            logger.warning("STRIPE_SECRET_KEY not configured. Running in development mode.")
            return False
            
        stripe.api_key = secret_key
        return True
    
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        return self.stripe_configured and STRIPE_AVAILABLE
    
    def get_config(self) -> Dict[str, Any]:
        """Get Stripe configuration for frontend."""
        return {
            'publishable_key': self.publishable_key if self.is_configured() else None,
            'configured': self.is_configured()
        }
    
    def create_customer(self, firebase_uid: str, email: str, name: Optional[str] = None) -> Optional[str]:
        """Create a Stripe customer and store in Firestore."""
        if not self.is_configured():
            logger.warning("Stripe not configured, cannot create customer")
            return None
            
        try:
            # Create Stripe customer
            customer_data = {
                'email': email,
                'metadata': {
                    'firebase_uid': firebase_uid
                }
            }
            if name:
                customer_data['name'] = name
                
            customer = stripe.Customer.create(**customer_data)
            
            # Store in Firestore
            user_ref = self.db.collection('users').document(firebase_uid)
            user_ref.set({
                'firebase_uid': firebase_uid,
                'email': email,
                'stripe_customer_id': customer.id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            logger.info(f"Created Stripe customer {customer.id} for user {firebase_uid}")
            return customer.id
            
        except Exception as e:
            logger.error(f"Failed to create Stripe customer for {firebase_uid}: {e}")
            return None
    
    def get_or_create_customer(self, firebase_uid: str, email: str, name: Optional[str] = None) -> Optional[str]:
        """Get existing customer or create new one."""
        if not self.is_configured():
            return None
            
        try:
            # Check if customer exists in Firestore
            user_doc = self.db.collection('users').document(firebase_uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                stripe_customer_id = user_data.get('stripe_customer_id')
                if stripe_customer_id:
                    # Verify customer exists in Stripe
                    try:
                        stripe.Customer.retrieve(stripe_customer_id)
                        return stripe_customer_id
                    except stripe.error.InvalidRequestError:
                        logger.warning(f"Stripe customer {stripe_customer_id} not found, creating new one")
            
            # Create new customer
            return self.create_customer(firebase_uid, email, name)
            
        except Exception as e:
            logger.error(f"Failed to get or create customer for {firebase_uid}: {e}")
            return None
    
    def create_checkout_session(self, firebase_uid: str, email: str, success_url: str, cancel_url: str) -> Optional[str]:
        """Create a Stripe checkout session for subscription."""
        if not self.is_configured():
            logger.warning("Stripe not configured, cannot create checkout session")
            return None
            
        try:
            customer_id = self.get_or_create_customer(firebase_uid, email)
            if not customer_id:
                logger.error(f"Failed to get customer for {firebase_uid}")
                return None
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': self.premium_monthly_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer=customer_id,
                metadata={
                    'firebase_uid': firebase_uid
                },
                billing_address_collection='required',
                customer_update={
                    'address': 'auto',
                    'name': 'auto'
                }
            )
            
            logger.info(f"Created checkout session {session.id} for user {firebase_uid}")
            return session.url
            
        except Exception as e:
            logger.error(f"Failed to create checkout session for {firebase_uid}: {e}")
            return None
    
    def get_subscription_status(self, firebase_uid: str) -> Dict[str, Any]:
        """Get user's subscription status."""
        try:
            # Get subscription from Firestore
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_doc = subscription_ref.get()
            
            if not subscription_doc.exists:
                return {
                    'is_premium': False,
                    'status': 'none',
                    'plan_id': None,
                    'current_period_end': None,
                    'cancel_at_period_end': False
                }
            
            subscription_data = subscription_doc.to_dict()
            status = subscription_data.get('status', 'none')
            
            return {
                'is_premium': status == 'active',
                'status': status,
                'plan_id': subscription_data.get('plan_id'),
                'current_period_end': subscription_data.get('current_period_end'),
                'cancel_at_period_end': subscription_data.get('cancel_at_period_end', False),
                'stripe_subscription_id': subscription_data.get('stripe_subscription_id')
            }
            
        except Exception as e:
            logger.error(f"Failed to get subscription status for {firebase_uid}: {e}")
            return {
                'is_premium': False,
                'status': 'error',
                'plan_id': None,
                'current_period_end': None,
                'cancel_at_period_end': False
            }
    
    def is_user_premium(self, firebase_uid: str) -> bool:
        """Check if user has active premium subscription."""
        subscription_status = self.get_subscription_status(firebase_uid)
        return subscription_status.get('is_premium', False)
    
    def cancel_subscription(self, firebase_uid: str) -> bool:
        """Cancel user's subscription at period end."""
        if not self.is_configured():
            logger.warning("Stripe not configured, cannot cancel subscription")
            return False
            
        try:
            subscription_status = self.get_subscription_status(firebase_uid)
            stripe_subscription_id = subscription_status.get('stripe_subscription_id')
            
            if not stripe_subscription_id:
                logger.error(f"No subscription found for user {firebase_uid}")
                return False
            
            # Cancel at period end in Stripe
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update Firestore
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_ref.update({
                'cancel_at_period_end': True,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Cancelled subscription {stripe_subscription_id} for user {firebase_uid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription for {firebase_uid}: {e}")
            return False
    
    def reactivate_subscription(self, firebase_uid: str) -> bool:
        """Reactivate a cancelled subscription."""
        if not self.is_configured():
            logger.warning("Stripe not configured, cannot reactivate subscription")
            return False
            
        try:
            subscription_status = self.get_subscription_status(firebase_uid)
            stripe_subscription_id = subscription_status.get('stripe_subscription_id')
            
            if not stripe_subscription_id:
                logger.error(f"No subscription found for user {firebase_uid}")
                return False
            
            # Reactivate in Stripe
            subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=False
            )
            
            # Update Firestore
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_ref.update({
                'cancel_at_period_end': False,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Reactivated subscription {stripe_subscription_id} for user {firebase_uid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reactivate subscription for {firebase_uid}: {e}")
            return False
    
    def handle_webhook(self, payload: bytes, signature: str) -> bool:
        """Handle Stripe webhook events."""
        if not self.is_configured():
            logger.warning("Stripe not configured, cannot handle webhook")
            return False
            
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            logger.info(f"Processing Stripe webhook event: {event['type']}")
            
            if event['type'] == 'checkout.session.completed':
                self._handle_checkout_session_completed(event['data']['object'])
            elif event['type'] == 'customer.subscription.updated':
                self._handle_subscription_updated(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                self._handle_payment_failed(event['data']['object'])
            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
            
            return True
            
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return False
        except Exception as e:
            logger.error(f"Failed to handle webhook: {e}")
            return False
    
    def _handle_checkout_session_completed(self, session):
        """Handle successful checkout session completion."""
        try:
            firebase_uid = session['metadata'].get('firebase_uid')
            if not firebase_uid:
                logger.error("No firebase_uid in checkout session metadata")
                return
            
            # Get subscription details
            subscription_id = session['subscription']
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Store subscription in Firestore
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_ref.set({
                'firebase_uid': firebase_uid,
                'stripe_customer_id': session['customer'],
                'stripe_subscription_id': subscription_id,
                'plan_id': 'premium_monthly',
                'status': subscription['status'],
                'current_period_start': subscription['current_period_start'],
                'current_period_end': subscription['current_period_end'],
                'cancel_at_period_end': subscription['cancel_at_period_end'],
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Stored subscription {subscription_id} for user {firebase_uid}")
            
        except Exception as e:
            logger.error(f"Failed to handle checkout session completed: {e}")
    
    def _handle_subscription_updated(self, subscription):
        """Handle subscription updates."""
        try:
            customer_id = subscription['customer']
            
            # Find user by customer ID
            users_query = self.db.collection('users').where('stripe_customer_id', '==', customer_id).limit(1)
            users = list(users_query.stream())
            
            if not users:
                logger.error(f"No user found for customer {customer_id}")
                return
            
            firebase_uid = users[0].to_dict()['firebase_uid']
            
            # Update subscription in Firestore
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_ref.update({
                'status': subscription['status'],
                'current_period_start': subscription['current_period_start'],
                'current_period_end': subscription['current_period_end'],
                'cancel_at_period_end': subscription['cancel_at_period_end'],
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Updated subscription for user {firebase_uid}")
            
        except Exception as e:
            logger.error(f"Failed to handle subscription updated: {e}")
    
    def _handle_subscription_deleted(self, subscription):
        """Handle subscription deletion."""
        try:
            customer_id = subscription['customer']
            
            # Find user by customer ID
            users_query = self.db.collection('users').where('stripe_customer_id', '==', customer_id).limit(1)
            users = list(users_query.stream())
            
            if not users:
                logger.error(f"No user found for customer {customer_id}")
                return
            
            firebase_uid = users[0].to_dict()['firebase_uid']
            
            # Update subscription status
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_ref.update({
                'status': 'canceled',
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Marked subscription as canceled for user {firebase_uid}")
            
        except Exception as e:
            logger.error(f"Failed to handle subscription deleted: {e}")
    
    def _handle_payment_failed(self, invoice):
        """Handle failed payment."""
        try:
            customer_id = invoice['customer']
            
            # Find user by customer ID
            users_query = self.db.collection('users').where('stripe_customer_id', '==', customer_id).limit(1)
            users = list(users_query.stream())
            
            if not users:
                logger.error(f"No user found for customer {customer_id}")
                return
            
            firebase_uid = users[0].to_dict()['firebase_uid']
            
            # Update subscription status to past_due
            subscription_ref = self.db.collection('user_subscriptions').document(firebase_uid)
            subscription_ref.update({
                'status': 'past_due',
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Marked subscription as past_due for user {firebase_uid}")
            
        except Exception as e:
            logger.error(f"Failed to handle payment failed: {e}")