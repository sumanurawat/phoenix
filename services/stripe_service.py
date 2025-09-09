"""Service for handling Stripe payments and subscription management."""
import os
import logging
from typing import Dict, Any, Optional
import stripe
from firebase_admin import firestore

logger = logging.getLogger(__name__)


class StripeService:
    """Handle Stripe payment processing and subscription management."""
    
    def __init__(self):
        """Initialize Stripe service with API keys."""
        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not self.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
            
        stripe.api_key = self.stripe_secret_key
        
        # Initialize Firestore client
        self.db = firestore.client()
        
        # Subscription plan configuration
        self.plans = {
            'premium_monthly': {
                'price_id': os.getenv('STRIPE_PREMIUM_MONTHLY_PRICE_ID'),
                'name': 'Premium Monthly',
                'amount': 500,  # $5.00 in cents
                'currency': 'usd',
                'interval': 'month'
            }
        }
    
    def get_or_create_customer(self, firebase_uid: str, email: str, name: str = None) -> str:
        """Get existing Stripe customer or create a new one."""
        try:
            # Check if user already has a Stripe customer ID
            user_ref = self.db.collection('users').document(firebase_uid)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                stripe_customer_id = user_data.get('stripe_customer_id')
                
                if stripe_customer_id:
                    # Verify customer exists in Stripe
                    try:
                        customer = stripe.Customer.retrieve(stripe_customer_id)
                        return customer.id
                    except stripe.error.InvalidRequestError:
                        # Customer doesn't exist in Stripe, create new one
                        logger.warning(f"Stripe customer {stripe_customer_id} not found, creating new one")
            
            # Create new Stripe customer
            customer_data = {
                'email': email,
                'metadata': {
                    'firebase_uid': firebase_uid
                }
            }
            if name:
                customer_data['name'] = name
                
            customer = stripe.Customer.create(**customer_data)
            
            # Update or create user document with Stripe customer ID
            user_ref.set({
                'email': email,
                'firebase_uid': firebase_uid,
                'stripe_customer_id': customer.id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            logger.info(f"Created Stripe customer {customer.id} for user {firebase_uid}")
            return customer.id
            
        except Exception as e:
            logger.error(f"Error getting/creating customer: {e}")
            raise
    
    def create_checkout_session(self, firebase_uid: str, email: str, plan_id: str = 'premium_monthly', 
                               success_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        """Create a Stripe checkout session for subscription."""
        try:
            plan = self.plans.get(plan_id)
            if not plan:
                raise ValueError(f"Invalid plan ID: {plan_id}")
            
            if not plan['price_id']:
                raise ValueError(f"Price ID not configured for plan: {plan_id}")
            
            # Get or create Stripe customer
            customer_id = self.get_or_create_customer(firebase_uid, email)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan['price_id'],
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or 'https://your-domain.com/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url or 'https://your-domain.com/cancel',
                metadata={
                    'firebase_uid': firebase_uid,
                    'plan_id': plan_id
                }
            )
            
            return {
                'session_id': session.id,
                'url': session.url,
                'customer_id': customer_id
            }
            
        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise
    
    def handle_webhook_event(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        try:
            if not self.webhook_secret:
                raise ValueError("STRIPE_WEBHOOK_SECRET not configured")
            
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            event_type = event['type']
            event_data = event['data']['object']
            
            logger.info(f"Processing Stripe webhook: {event_type}")
            
            if event_type == 'checkout.session.completed':
                self._handle_checkout_completed(event_data)
            elif event_type == 'customer.subscription.updated':
                self._handle_subscription_updated(event_data)
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event_data)
            elif event_type == 'invoice.payment_failed':
                self._handle_payment_failed(event_data)
            else:
                logger.info(f"Unhandled event type: {event_type}")
            
            return {'status': 'success', 'event_type': event_type}
            
        except ValueError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise
    
    def _handle_checkout_completed(self, session) -> None:
        """Handle successful checkout completion."""
        try:
            firebase_uid = session['metadata'].get('firebase_uid')
            if not firebase_uid:
                logger.error("No firebase_uid in checkout session metadata")
                return
            
            customer_id = session['customer']
            subscription_id = session['subscription']
            
            # Retrieve subscription details
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            # Create subscription record in Firestore
            subscription_ref = self.db.collection('user_subscriptions').document()
            subscription_ref.set({
                'firebase_uid': firebase_uid,
                'stripe_customer_id': customer_id,
                'stripe_subscription_id': subscription_id,
                'plan_id': session['metadata'].get('plan_id', 'premium_monthly'),
                'status': subscription['status'],
                'current_period_start': subscription['current_period_start'],
                'current_period_end': subscription['current_period_end'],
                'cancel_at_period_end': subscription['cancel_at_period_end'],
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Created subscription record for user {firebase_uid}")
            
        except Exception as e:
            logger.error(f"Error handling checkout completion: {e}")
    
    def _handle_subscription_updated(self, subscription) -> None:
        """Handle subscription updates."""
        try:
            subscription_id = subscription['id']
            
            # Find subscription in Firestore
            query = self.db.collection('user_subscriptions').where(
                'stripe_subscription_id', '==', subscription_id
            )
            docs = query.get()
            
            if not docs:
                logger.warning(f"Subscription {subscription_id} not found in Firestore")
                return
            
            # Update subscription record
            for doc in docs:
                doc.reference.update({
                    'status': subscription['status'],
                    'current_period_start': subscription['current_period_start'],
                    'current_period_end': subscription['current_period_end'],
                    'cancel_at_period_end': subscription['cancel_at_period_end'],
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"Updated subscription {subscription_id}")
            
        except Exception as e:
            logger.error(f"Error handling subscription update: {e}")
    
    def _handle_subscription_deleted(self, subscription) -> None:
        """Handle subscription cancellation."""
        try:
            subscription_id = subscription['id']
            
            # Find subscription in Firestore
            query = self.db.collection('user_subscriptions').where(
                'stripe_subscription_id', '==', subscription_id
            )
            docs = query.get()
            
            for doc in docs:
                doc.reference.update({
                    'status': 'canceled',
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"Marked subscription {subscription_id} as canceled")
            
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {e}")
    
    def _handle_payment_failed(self, invoice) -> None:
        """Handle failed payment."""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return
            
            # Find subscription in Firestore
            query = self.db.collection('user_subscriptions').where(
                'stripe_subscription_id', '==', subscription_id
            )
            docs = query.get()
            
            for doc in docs:
                doc.reference.update({
                    'status': 'past_due',
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"Marked subscription {subscription_id} as past_due")
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
    
    def get_user_subscription(self, firebase_uid: str) -> Optional[Dict[str, Any]]:
        """Get user's current subscription status."""
        try:
            query = self.db.collection('user_subscriptions').where(
                'firebase_uid', '==', firebase_uid
            ).where(
                'status', 'in', ['active', 'trialing']
            ).limit(1)
            
            docs = query.get()
            
            if docs:
                subscription_data = docs[0].to_dict()
                return subscription_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None
    
    def cancel_subscription(self, firebase_uid: str) -> bool:
        """Cancel user's subscription at period end."""
        try:
            # Get user's subscription
            subscription_data = self.get_user_subscription(firebase_uid)
            if not subscription_data:
                return False
            
            stripe_subscription_id = subscription_data['stripe_subscription_id']
            
            # Cancel at period end in Stripe
            stripe.Subscription.modify(
                stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update Firestore record
            query = self.db.collection('user_subscriptions').where(
                'stripe_subscription_id', '==', stripe_subscription_id
            )
            docs = query.get()
            
            for doc in docs:
                doc.reference.update({
                    'cancel_at_period_end': True,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"Canceled subscription for user {firebase_uid}")
            return True
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {e}")
            return False
    
    def is_user_premium(self, firebase_uid: str) -> bool:
        """Check if user has active premium subscription."""
        subscription = self.get_user_subscription(firebase_uid)
        return subscription is not None and subscription.get('status') in ['active', 'trialing']