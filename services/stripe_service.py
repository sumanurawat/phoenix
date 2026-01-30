"""
Stripe Service for subscription management and payment processing.
"""
import os
import stripe
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from firebase_admin import firestore
from services.token_security_service import TokenSecurityService

logger = logging.getLogger(__name__)

class StripeService:
    """Service for managing Stripe subscriptions and payments."""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern to avoid reinitializing on every request."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Stripe service with API keys (only once)."""
        # Skip if already initialized
        if StripeService._initialized:
            return

        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        # Try multiple possible price ID environment variables
        self.premium_price_id = (
            os.getenv('STRIPE_PREMIUM_MONTHLY_PRICE_ID') or
            os.getenv('STRIPE_PRICE_ID') or
            os.getenv('STRIPE_PRO_PRICE_ID') or
            os.getenv('STRIPE_BASIC_PRICE_ID')
        )

        # Initialize Stripe if configured
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
            self.is_configured = True

            # Log only once at startup
            key_prefix = self.stripe_secret_key[:15] if self.stripe_secret_key else "None"
            mode = "TEST" if self.stripe_secret_key.startswith('sk_test_') else "LIVE"
            logger.debug(f"Stripe service initialized (Mode: {mode})")

            if not self.premium_price_id:
                logger.warning("❌ No price ID configured - checkout will fail")
        else:
            self.is_configured = False
            logger.warning("Stripe not configured - subscription features disabled")

        StripeService._initialized = True
            
        # Initialize Firestore
        try:
            self.db = firestore.client()
            self.security_service = TokenSecurityService(self.db)
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None
            self.security_service = None
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            self.db = None

    @staticmethod
    def normalize_plan_id(plan_id: Optional[str], price_id: Optional[str] = None) -> str:
        """Normalize various plan identifiers to enum values like 'zero' (free) and 'five' (paid).

        - Free tier -> 'zero'
        - Any paid monthly plan at $5 -> 'five'
        - Legacy values like 'premium_monthly', 'premium', 'pro', or Stripe price IDs -> 'five'
        """
        if not plan_id and not price_id:
            return 'zero'

        # Explicit free markers
        lowered = (plan_id or '').lower()
        if lowered in {'zero', 'free', 'free_tier'}:
            return 'zero'

        # Any price id from Stripe indicates paid plan
        if price_id and price_id.startswith('price_'):
            return 'five'

        # Map legacy/known paid identifiers to 'five'
        if lowered in {'premium_monthly', 'premium', 'pro', 'plus', 'five'}:
            return 'five'

        # If it's not clearly free, treat as paid baseline
        return 'five'

    def ensure_free_subscription(self, firebase_uid: str, email: Optional[str] = None) -> bool:
        """Ensure a free subscription record exists for the user in Firestore.

        Creates a lightweight document for visibility and analytics. This will not
        interfere with premium checks which look for status in ['active','trialing'].
        Document ID convention: f"free_{firebase_uid}".
        """
        if not self.db or not firebase_uid:
            return False
        try:
            doc_id = f"free_{firebase_uid}"
            sub_ref = self.db.collection('user_subscriptions').document(doc_id)
            doc = sub_ref.get()
            if doc.exists:
                # Keep the record updated but don't overwrite timestamps unnecessarily
                sub_ref.set({
                    'firebase_uid': firebase_uid,
                    'email': email,
                    'status': 'free',
                    'plan_id': 'zero',
                    'updated_at': firestore.SERVER_TIMESTAMP
                }, merge=True)
            else:
                sub_ref.set({
                    'firebase_uid': firebase_uid,
                    'email': email,
                    'status': 'free',
                    'plan_id': 'zero',
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            return True
        except Exception as e:
            logger.error(f"Failed to ensure free subscription for {firebase_uid}: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get Stripe configuration for frontend."""
        return {
            'publishable_key': self.stripe_publishable_key,
            'premium_price_id': self.premium_price_id,
            'is_configured': self.is_configured
        }
    
    def create_customer(self, email: str, firebase_uid: str) -> Optional[str]:
        """Create a Stripe customer and link to Firebase user."""
        if not self.is_configured:
            return None
            
        try:
            # Check if customer already exists
            existing_customer = self.get_customer_by_firebase_uid(firebase_uid)
            if existing_customer:
                return existing_customer
            
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=email,
                metadata={'firebase_uid': firebase_uid}
            )
            
            # Store customer ID in Firestore
            if self.db:
                user_ref = self.db.collection('users').document(firebase_uid)
                user_ref.set({
                    'stripe_customer_id': customer.id,
                    'email': email,
                    'firebase_uid': firebase_uid,
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }, merge=True)
            
            logger.info(f"Created Stripe customer {customer.id} for user {firebase_uid}")
            return customer.id
            
        except Exception as e:
            logger.error(f"Failed to create customer: {e}")
            return None
    
    def get_customer_by_firebase_uid(self, firebase_uid: str) -> Optional[str]:
        """Get Stripe customer ID from Firebase UID."""
        if not self.db:
            return None
            
        try:
            user_doc = self.db.collection('users').document(firebase_uid).get()
            if user_doc.exists:
                data = user_doc.to_dict()
                return data.get('stripe_customer_id')
            return None
        except Exception as e:
            logger.error(f"Failed to get customer: {e}")
            return None
    
    def create_checkout_session(self, firebase_uid: str, email: str, 
                               success_url: str, cancel_url: str) -> Optional[Dict[str, Any]]:
        """Create a Stripe checkout session for subscription."""
        if not self.is_configured:
            logger.error("Stripe not configured - cannot create checkout session")
            return None
        
        if not self.premium_price_id:
            logger.error("No price ID configured - cannot create checkout session")
            return None
            
        try:
            # Get or create customer
            customer_id = self.get_customer_by_firebase_uid(firebase_uid)
            
            # Log the price ID being used
            logger.info(f"Creating checkout session with price ID: {self.premium_price_id}")
            
            # Create checkout session parameters
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': self.premium_price_id,
                    'quantity': 1,
                }],
                'mode': 'subscription',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': {
                    'firebase_uid': firebase_uid
                }
            }
            
            if customer_id:
                # Update existing customer's email if different
                try:
                    customer = stripe.Customer.retrieve(customer_id)
                    if customer.email != email:
                        stripe.Customer.modify(customer_id, email=email)
                        logger.info(f"Updated customer {customer_id} email to {email}")
                except Exception as e:
                    logger.warning(f"Failed to update customer email: {e}")
                
                session_params['customer'] = customer_id
            else:
                # For new customers, use customer_email (Stripe will create customer automatically)
                session_params['customer_email'] = email
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(**session_params)
            
            logger.info(f"Created checkout session {checkout_session.id} for user {firebase_uid}")
            return {
                'session_id': checkout_session.id,
                'url': checkout_session.url
            }
            
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return None
    
    
    def get_or_create_customer(self, firebase_uid: str, email: str) -> Optional[str]:
        """
        Get existing Stripe customer or create new one.
        Convenience method for token purchases and subscriptions.
        
        Args:
            firebase_uid: Firebase user ID
            email: User email address
            
        Returns:
            Stripe customer ID or None on failure
        """
        if not self.is_configured:
            logger.error("Stripe not configured")
            return None
        
        try:
            # Try to get existing customer
            customer_id = self.get_customer_by_firebase_uid(firebase_uid)
            
            if customer_id:
                logger.info(f"Found existing Stripe customer {customer_id} for user {firebase_uid}")
                return customer_id
            
            # Create new customer
            logger.info(f"Creating new Stripe customer for user {firebase_uid}")
            customer_id = self.create_customer(email=email, firebase_uid=firebase_uid)
            
            if customer_id:
                logger.info(f"Created Stripe customer {customer_id} for user {firebase_uid}")
            else:
                logger.error(f"Failed to create Stripe customer for user {firebase_uid}")
            
            return customer_id
            
        except Exception as e:
            logger.error(f"Error in get_or_create_customer: {e}", exc_info=True)
            return None


    def create_token_checkout_session(self, customer_id: str, price_id: str, 
                                     metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe checkout session for one-time token purchase.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID for the token package
            metadata: Dictionary containing firebase_uid, package_id, tokens, purchase_type
            
        Returns:
            Dictionary with session_id and url, or None on failure
        """
        if not self.is_configured:
            logger.error("Stripe not configured - cannot create token checkout session")
            return None
        
        try:
            # Redirect to friedmomo.com after purchase (not old Phoenix UI)
            frontend_url = os.getenv('FRONTEND_URL', 'https://friedmomo.com')
            success_url = f"{frontend_url}/purchase-success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{frontend_url}/shop"
            
            # Enhanced diagnostic logging
            logger.info(f"🔍 Creating checkout session with Price ID: {price_id}")
            logger.info(f"🔍 API Key being used: {stripe.api_key[:15]}...")
            logger.info(f"🔍 Customer ID: {customer_id}")
            logger.info(f"🔍 Package metadata: {metadata}")
            
            # Verify customer exists in this Stripe account
            try:
                stripe.Customer.retrieve(customer_id)
                logger.info(f"✅ Customer {customer_id} verified in current Stripe account")
            except stripe.error.InvalidRequestError as customer_error:
                logger.warning(f"⚠️ Customer {customer_id} not found in current Stripe account: {customer_error}")
                logger.warning(f"🔄 Creating new customer for user {metadata.get('firebase_uid')}")
                # Customer doesn't exist in this account, create a new one
                firebase_uid = metadata.get('firebase_uid')
                if firebase_uid and self.db:
                    # Delete old customer mapping
                    user_ref = self.db.collection('users').document(firebase_uid)
                    user_doc = user_ref.get()
                    if user_doc.exists:
                        email = user_doc.to_dict().get('email')
                        # Create new customer in current account
                        new_customer = stripe.Customer.create(
                            email=email,
                            metadata={'firebase_uid': firebase_uid}
                        )
                        customer_id = new_customer.id
                        # Update Firestore with new customer ID
                        user_ref.update({'stripe_customer_id': customer_id})
                        logger.info(f"✅ Created new customer {customer_id} in current Stripe account")
                    else:
                        logger.error(f"❌ User {firebase_uid} not found in Firestore")
                        return None
                else:
                    logger.error("❌ Cannot create new customer: missing firebase_uid or database")
                    return None
            
            # Create checkout session for one-time payment
            session_params = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': 'payment',  # One-time payment, not subscription
                'customer': customer_id,
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': metadata
            }
            
            checkout_session = stripe.checkout.Session.create(**session_params)
            
            logger.info(f"Created token checkout session {checkout_session.id} for customer {customer_id}")
            logger.info(f"Package: {metadata.get('package_id')}, Tokens: {metadata.get('tokens')}")
            
            return {
                'session_id': checkout_session.id,
                'url': checkout_session.url
            }
            
        except Exception as e:
            logger.error(f"Failed to create token checkout session: {e}", exc_info=True)
            return None

    def get_subscription_status(self, firebase_uid: str) -> Dict[str, Any]:
        """Get current subscription status for a user."""
        result = {
            'is_premium': False,
            'status': 'none',
            'current_period_end': None,
            'cancel_at_period_end': False,
            'plan_id': 'zero'
        }
        
        if not self.is_configured or not self.db:
            return result
            
        try:
            # Get subscription from Firestore
            sub_docs = self.db.collection('user_subscriptions')\
                .where(filter=firestore.FieldFilter('firebase_uid', '==', firebase_uid))\
                .where(filter=firestore.FieldFilter('status', 'in', ['active', 'trialing']))\
                .limit(1).get()
            
            if sub_docs:
                sub_data = sub_docs[0].to_dict()
                normalized_plan = self.normalize_plan_id(
                    sub_data.get('plan_id'), sub_data.get('price_id')
                )
                result.update({
                    'is_premium': True,
                    'status': sub_data.get('status', 'none'),
                    'current_period_end': sub_data.get('current_period_end'),
                    'cancel_at_period_end': sub_data.get('cancel_at_period_end', False),
                    'plan_id': normalized_plan
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get subscription status: {e}")
            return result
    
    def is_user_premium(self, firebase_uid: str) -> bool:
        """Check if user has active premium subscription."""
        status = self.get_subscription_status(firebase_uid)
        return status.get('is_premium', False)
    
    def cancel_subscription(self, firebase_uid: str) -> bool:
        """Cancel a user's subscription at period end."""
        if not self.is_configured:
            logger.warning("Stripe not configured - cannot cancel subscription")
            return False
            
        try:
            # Get subscription from Firestore
            sub_docs = self.db.collection('user_subscriptions')\
                .where(filter=firestore.FieldFilter('firebase_uid', '==', firebase_uid))\
                .where(filter=firestore.FieldFilter('status', 'in', ['active', 'trialing']))\
                .limit(1).get()
            
            if not sub_docs:
                logger.warning(f"No active subscription found for user {firebase_uid}")
                return False
            
            sub_data = sub_docs[0].to_dict()
            subscription_id = sub_data.get('stripe_subscription_id')
            
            if not subscription_id:
                logger.error(f"No Stripe subscription ID found for user {firebase_uid}")
                return False
            
            # Validate subscription ID format
            if not subscription_id.startswith('sub_'):
                logger.error(f"Invalid Stripe subscription ID format: {subscription_id}")
                # Clean up invalid record
                sub_docs[0].reference.delete()
                return False
            
            try:
                # Cancel subscription at period end
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                
                # Update Firestore
                sub_docs[0].reference.update({
                    'cancel_at_period_end': True,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                logger.info(f"Cancelled subscription {subscription_id} for user {firebase_uid}")
                return True
                
            except stripe.error.InvalidRequestError as e:
                if 'No such subscription' in str(e):
                    logger.warning(f"Subscription {subscription_id} not found in Stripe - cleaning up local record")
                    # Clean up orphaned record
                    sub_docs[0].reference.delete()
                    return False
                else:
                    raise e
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False
    
    def reactivate_subscription(self, firebase_uid: str) -> bool:
        """Reactivate a cancelled subscription."""
        if not self.is_configured:
            logger.warning("Stripe not configured - cannot reactivate subscription")
            return False
            
        try:
            # Get subscription from Firestore
            sub_docs = self.db.collection('user_subscriptions')\
                .where(filter=firestore.FieldFilter('firebase_uid', '==', firebase_uid))\
                .where(filter=firestore.FieldFilter('status', 'in', ['active', 'trialing']))\
                .where(filter=firestore.FieldFilter('cancel_at_period_end', '==', True))\
                .limit(1).get()
            
            if not sub_docs:
                logger.warning(f"No cancelled subscription found for user {firebase_uid}")
                return False
            
            sub_data = sub_docs[0].to_dict()
            subscription_id = sub_data.get('stripe_subscription_id')
            
            if not subscription_id:
                logger.error(f"No Stripe subscription ID found for user {firebase_uid}")
                return False
            
            # Validate subscription ID format
            if not subscription_id.startswith('sub_'):
                logger.error(f"Invalid Stripe subscription ID format: {subscription_id}")
                # Clean up invalid record
                sub_docs[0].reference.delete()
                return False
            
            try:
                # Reactivate subscription
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=False
                )
                
                # Update Firestore
                sub_docs[0].reference.update({
                    'cancel_at_period_end': False,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                
                logger.info(f"Reactivated subscription {subscription_id} for user {firebase_uid}")
                return True
                
            except stripe.error.InvalidRequestError as e:
                if 'No such subscription' in str(e):
                    logger.warning(f"Subscription {subscription_id} not found in Stripe - cleaning up local record")
                    # Clean up orphaned record
                    sub_docs[0].reference.delete()
                    return False
                else:
                    raise e
            
        except Exception as e:
            logger.error(f"Failed to reactivate subscription: {e}")
            return False
    
    def handle_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events."""
        logger.info("🔍 Starting webhook event processing...")
        
        if not self.is_configured:
            logger.error("❌ Stripe not configured - cannot process webhook")
            return {'error': 'Stripe not configured'}
            
        logger.info(f"✅ Stripe is configured, webhook_secret present: {bool(self.webhook_secret)}")
        
        try:
            logger.info("🔐 Verifying webhook signature...")
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            logger.info(f"✅ Webhook signature verified successfully!")
            logger.info(f"📋 Event type: {event['type']}")
            logger.info(f"📋 Event id: {event['id']}")
            
            # Handle different event types
            if event['type'] == 'checkout.session.completed':
                logger.info("🛒 Processing checkout.session.completed event")
                return self._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'customer.subscription.updated':
                logger.info("📝 Processing customer.subscription.updated event")
                return self._handle_subscription_updated(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                logger.info("🗑️ Processing customer.subscription.deleted event")
                return self._handle_subscription_deleted(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                logger.info("❌ Processing invoice.payment_failed event")
                return self._handle_payment_failed(event['data']['object'])
            else:
                logger.warning(f"⚠️ Unhandled webhook event type: {event['type']}")
                
            logger.info("✅ Webhook event processing completed successfully")
            return {'success': True}
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"❌ Invalid webhook signature: {e}")
            return {'error': 'Invalid signature'}, 400
        except Exception as e:
            logger.error(f"❌ Webhook processing failed: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'error': str(e)}, 500
    
    def _handle_checkout_completed(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful checkout session completion."""
        logger.info("🛒 Starting checkout completion processing...")
        
        try:
            session_id = session.get('id')
            logger.info(f"📋 Checkout Session ID: {session_id}")
            
            metadata = session.get('metadata', {}) or {}
            firebase_uid = metadata.get('firebase_uid')
            customer_id = session.get('customer')
            raw_subscription = session.get('subscription')
            customer_email = (session.get('customer_email') or
                              session.get('customer_details', {}) .get('email'))

            logger.info(f"👤 Firebase UID: {firebase_uid}")
            logger.info(f"💳 Customer ID: {customer_id}")
            logger.info(f"📧 Customer Email: {customer_email}")
            logger.info(f"🔔 Raw Subscription reference type: {type(raw_subscription)}")

            if not firebase_uid:
                logger.error("❌ No firebase_uid in checkout session metadata")
                logger.error(f"Available metadata: {metadata}")
                return {'error': 'Missing firebase_uid'}

            # Check if this is a token purchase (one-time payment)
            purchase_type = metadata.get('purchase_type')
            if purchase_type == 'token_package':
                logger.info("🪙 Detected token purchase - routing to token handler")
                return self._handle_token_purchase(session)
            
            # Otherwise, handle as subscription

            if not raw_subscription:
                logger.error("❌ No subscription in checkout session")
                return {'error': 'Missing subscription'}

            # Normalize subscription (it may already be expanded object/dict or simple ID string)
            subscription = None
            subscription_id = None
            try:
                from stripe import Subscription as StripeSubscription
                # Case 1: Already a Stripe Subscription instance
                if isinstance(raw_subscription, StripeSubscription):
                    logger.debug("🔍 Subscription is an expanded StripeSubscription instance")
                    subscription = raw_subscription
                # Case 2: Dict (expanded)
                elif isinstance(raw_subscription, dict):
                    logger.debug("🔍 Subscription is an expanded dict; constructing Stripe object")
                    if 'id' not in raw_subscription:
                        raise ValueError("Expanded subscription dict missing 'id'")
                    subscription = StripeSubscription.construct_from(raw_subscription, stripe.api_key)
                # Case 3: String ID -> retrieve
                elif isinstance(raw_subscription, str):
                    logger.debug("🔍 Subscription is an ID string; retrieving from Stripe")
                    subscription = stripe.Subscription.retrieve(raw_subscription)
                else:
                    raise TypeError(f"Unsupported subscription reference type: {type(raw_subscription)}")
            except Exception as sub_e:
                logger.error(f"❌ Failed to normalize/retrieve subscription: {sub_e}", exc_info=True)
                return {'error': f'Subscription retrieval failed: {sub_e}'}

            subscription_id = getattr(subscription, 'id', None)
            if not subscription_id or not isinstance(subscription_id, str):
                logger.error(f"❌ Normalized subscription has invalid id: {subscription_id}")
                return {'error': 'Invalid subscription id after normalization'}

            logger.info(f"✅ Normalized subscription: {subscription_id} (status: {getattr(subscription, 'status', 'unknown')})")
            
            # Store subscription in Firestore
            if self.db:
                logger.info("💾 Saving subscription to Firestore...")
                sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
                
                # Attempt to extract price/plan info from first item
                price_id = None
                amount = None
                interval = None
                interval_count = None
                try:
                    if getattr(subscription, 'items', None) and subscription.items.data:
                        first_item = subscription.items.data[0]
                        price_obj = getattr(first_item, 'price', None) or getattr(first_item, 'plan', None)
                        if price_obj:
                            price_id = getattr(price_obj, 'id', None)
                            amount = getattr(price_obj, 'unit_amount', getattr(price_obj, 'amount', None))
                            if hasattr(price_obj, 'recurring') and price_obj.recurring:
                                interval = getattr(price_obj.recurring, 'interval', None)
                                interval_count = getattr(price_obj.recurring, 'interval_count', None)
                except Exception as price_e:
                    logger.warning(f"⚠️ Failed to parse price info: {price_e}")

                subscription_data = {
                    'firebase_uid': firebase_uid,
                    'stripe_customer_id': customer_id,
                    'stripe_subscription_id': subscription_id,
                    # Enum plan id for $5 plan
                    'plan_id': self.normalize_plan_id('five', price_id),
                    'price_id': price_id,
                    'price_id': price_id,
                    'amount': amount,
                    'interval': interval,
                    'interval_count': interval_count,
                    'status': getattr(subscription, 'status', None),
                    'current_period_start': datetime.fromtimestamp(
                        getattr(subscription, 'current_period_start'), tz=timezone.utc
                    ) if getattr(subscription, 'current_period_start', None) else None,
                    'current_period_end': datetime.fromtimestamp(
                        getattr(subscription, 'current_period_end'), tz=timezone.utc
                    ) if getattr(subscription, 'current_period_end', None) else None,
                    'cancel_at_period_end': getattr(subscription, 'cancel_at_period_end', False),
                    'livemode': getattr(subscription, 'livemode', False),
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'source': session.get('source') or 'webhook_or_manual'
                }
                
                logger.info(f"📄 Subscription data to save: {subscription_data}")
                sub_ref.set(subscription_data)
                logger.info(f"✅ Successfully saved subscription to Firestore!")
                
                # Also create/update user record
                logger.info("👤 Creating/updating user record...")
                user_ref = self.db.collection('users').document(firebase_uid)
                user_ref.set({
                    'firebase_uid': firebase_uid,
                    'email': customer_email,
                    'stripe_customer_id': customer_id,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }, merge=True)
                logger.info("✅ User record updated successfully!")
            else:
                logger.error("❌ No Firestore database connection available!")
                return {'error': 'Database not available'}
            
            logger.info(f"🎉 Subscription {subscription_id} created successfully for user {firebase_uid}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"❌ Failed to handle checkout completion: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'error': str(e)}
    

    def _handle_token_purchase(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle token purchase completion.
        Credits tokens to user account with idempotency check.
        """
        logger.info("🪙 Starting token purchase processing...")
        
        try:
            from services.token_service import TokenService
            from services.transaction_service import TransactionService
            
            token_service = TokenService()
            transaction_service = TransactionService()
            
            session_id = session.get('id')
            metadata = session.get('metadata', {}) or {}
            
            firebase_uid = metadata.get('firebase_uid')
            package_id = metadata.get('package_id')
            tokens = metadata.get('tokens')
            
            logger.info(f"👤 User: {firebase_uid}")
            logger.info(f"📦 Package: {package_id}")
            logger.info(f"🪙 Tokens: {tokens}")
            
            if not all([firebase_uid, package_id, tokens]):
                logger.error("❌ Missing required metadata for token purchase")
                return {'error': 'Incomplete token purchase data'}
            
            # Convert tokens to integer
            try:
                tokens = int(tokens)
            except (ValueError, TypeError):
                logger.error(f"❌ Invalid token amount: {tokens}")
                return {'error': 'Invalid token amount'}
            
            # SECURITY: Validate token amount
            if self.security_service:
                valid, error_msg = self.security_service.validate_token_amount(tokens)
                if not valid:
                    logger.error(f"❌ Token validation failed: {error_msg}")
                    return {'error': error_msg}
            
            # SECURITY: Validate package and price
            if self.security_service:
                amount_paid_cents = session.get('amount_total', 0)
                valid, error_msg = self.security_service.validate_package(
                    package_id, tokens, amount_paid_cents
                )
                if not valid:
                    logger.error(f"❌ Package validation failed: {error_msg}")
                    self.security_service.log_suspicious_activity(
                        firebase_uid,
                        'invalid_package_price',
                        {
                            'package_id': package_id,
                            'tokens_claimed': tokens,
                            'amount_paid_cents': amount_paid_cents,
                            'session_id': session_id
                        }
                    )
                    return {'error': 'Package validation failed'}
            
            # SECURITY: Check rate limits
            if self.security_service:
                allowed, error_msg = self.security_service.validate_purchase_rate_limit(firebase_uid)
                if not allowed:
                    logger.warning(f"🚨 Rate limit exceeded for user {firebase_uid}")
                    self.security_service.log_suspicious_activity(
                        firebase_uid,
                        'rate_limit_exceeded',
                        {
                            'package_id': package_id,
                            'session_id': session_id
                        }
                    )
                    return {'error': error_msg}
            
            # Idempotency check: Has this session already been processed?
            logger.info(f"🔍 Checking for duplicate processing...")
            existing = transaction_service.get_by_stripe_session(session_id)
            if existing:
                logger.warning(f"⚠️ DUPLICATE EVENT: Session {session_id} already processed")
                logger.warning(f"   Original transaction ID: {existing.get('id')}")
                logger.warning(f"   Original timestamp: {existing.get('timestamp')}")
                logger.warning(f"   SKIPPING to prevent double-crediting")
                return {'success': True, 'message': 'Already processed'}

            logger.info(f"✅ No duplicate found - proceeding with token credit")

            # Credit tokens to user account
            logger.info(f"💳 [STRIPE WEBHOOK] Processing token purchase:")
            logger.info(f"   Session ID: {session_id}")
            logger.info(f"   User: {firebase_uid}")
            logger.info(f"   Package: {package_id}")
            logger.info(f"   Tokens: {tokens}")
            logger.info(f"   Amount Paid: ${session.get('amount_total', 0) / 100:.2f}")

            balance_after = None
            try:
                balance_after = token_service.add_tokens(
                    user_id=firebase_uid,
                    amount=tokens,
                    reason=f"Purchased {package_id} package"
                )
                logger.info(f"✅ Tokens credited successfully. New balance: {balance_after}")

            except ValueError as ve:
                logger.error(f"❌ VALIDATION ERROR during token credit: {ve}")
                logger.error(f"   User: {firebase_uid}")
                logger.error(f"   Session: {session_id}")
                logger.error(f"   This likely means the user document doesn't exist!")
                logger.error(f"   ACTION REQUIRED: Check if user {firebase_uid} exists in Firestore")
                raise
            except Exception as te:
                logger.error(f"❌ EXCEPTION during token credit: {te}", exc_info=True)
                logger.error(f"   User: {firebase_uid}")
                logger.error(f"   Session: {session_id}")
                raise

            # Record transaction in ledger with balance_after to avoid extra read
            logger.info(f"📝 Recording transaction in ledger...")
            try:
                transaction_id = transaction_service.record_purchase(
                    user_id=firebase_uid,
                    amount=tokens,
                    package_id=package_id,
                    stripe_session_id=session_id,
                    stripe_customer_id=session.get('customer'),
                    amount_paid=session.get('amount_total', 0) / 100,  # Convert cents to dollars
                    balance_after=balance_after  # Pass balance to avoid extra Firestore read
                )
                logger.info(f"✅ Transaction recorded with ID: {transaction_id}")
            except Exception as ledger_error:
                logger.error(f"❌ CRITICAL: Failed to record transaction in ledger!")
                logger.error(f"   Error: {ledger_error}", exc_info=True)
                logger.error(f"   TOKENS WERE CREDITED BUT NO AUDIT TRAIL!")
                logger.error(f"   Session: {session_id}")
                logger.error(f"   User: {firebase_uid}")
                logger.error(f"   Tokens: {tokens}")
                # Don't fail the webhook - tokens were already credited

            logger.info(f"🎉🎉🎉 SUCCESS: Credited {tokens} tokens to user {firebase_uid}")
            logger.info(f"   Session: {session_id}")
            logger.info(f"   Package: {package_id}")
            return {'success': True}

        except Exception as e:
            logger.error(f"❌❌❌ CRITICAL FAILURE in token purchase processing!")
            logger.error(f"   Session ID: {session_id}")
            logger.error(f"   User: {firebase_uid}")
            logger.error(f"   Package: {package_id}")
            logger.error(f"   Tokens: {tokens}")
            logger.error(f"   Exception: {e}", exc_info=True)
            logger.error(f"   Stack trace above ^^^")
            return {'error': str(e)}

    def _handle_subscription_updated(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription update events."""
        try:
            subscription_id = subscription['id']
            
            if self.db:
                # Update subscription in Firestore
                sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
                sub_ref.update({
                    'status': subscription['status'],
                    'current_period_start': datetime.fromtimestamp(
                        subscription['current_period_start'], tz=timezone.utc
                    ),
                    'current_period_end': datetime.fromtimestamp(
                        subscription['current_period_end'], tz=timezone.utc
                    ),
                    'cancel_at_period_end': subscription.get('cancel_at_period_end', False),
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"Subscription {subscription_id} updated")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle subscription update: {e}")
            return {'error': str(e)}
    
    def _handle_subscription_deleted(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription deletion events."""
        try:
            subscription_id = subscription['id']
            
            if self.db:
                # Update subscription status in Firestore
                sub_ref = self.db.collection('user_subscriptions').document(subscription_id)
                sub_ref.update({
                    'status': 'canceled',
                    'canceled_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            logger.info(f"Subscription {subscription_id} canceled")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle subscription deletion: {e}")
            return {'error': str(e)}
    
    def _handle_payment_failed(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment events."""
        try:
            subscription_id = invoice['subscription']
            
            logger.warning(f"Payment failed for subscription {subscription_id}")
            
            # Could implement email notification here
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Failed to handle payment failure: {e}")
            return {'error': str(e)}
    
    def get_usage_stats(self, firebase_uid: str) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        try:
            # Get today's usage from Firestore
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            if self.db:
                usage_doc = self.db.collection('user_usage')\
                    .document(f"{firebase_uid}_{today}").get()
                
                if usage_doc.exists:
                    return usage_doc.to_dict()
            
            return {
                'chat_messages': 0,
                'searches': 0,
                'videos_generated': 0,
                'date': today
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    def increment_usage(self, firebase_uid: str, feature: str, amount: int = 1) -> bool:
        """Increment usage counter for a feature."""
        try:
            if not self.db:
                return False
                
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            usage_ref = self.db.collection('user_usage').document(f"{firebase_uid}_{today}")
            
            # Use transaction for atomic increment
            @firestore.transactional
            def update_usage(transaction, ref):
                doc = ref.get(transaction=transaction)
                if doc.exists:
                    current = doc.get(feature, 0)
                    transaction.update(ref, {
                        feature: current + amount,
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                else:
                    transaction.set(ref, {
                        feature: amount,
                        'firebase_uid': firebase_uid,
                        'date': today,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
            
            transaction = self.db.transaction()
            update_usage(transaction, usage_ref)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to increment usage: {e}")
            return False