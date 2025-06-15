"""
Stripe API Routes

Handles Stripe Checkout session creation and webhook events for managing subscriptions.
"""
import stripe
from flask import Blueprint, request, jsonify, current_app, session as flask_session # Renamed to avoid conflict
from functools import wraps # For login_required decorator
import logging # For logging if current_app.logger is not set up
from datetime import datetime

from services.membership_service import MembershipService
from config import settings as app_config # To access STRIPE_WEBHOOK_SECRET directly if needed

# Placeholder for authentication - User needs to implement these
# based on their Firebase Authentication setup.
def get_current_user_id():
    """
    Placeholder: Returns the current authenticated user's ID.
    User should implement this to retrieve user ID from session or token.
    Example: return flask_session.get('user_id')
    """
    # Assuming user_id is stored in session after login by auth_routes.py
    user_id = flask_session.get('user_id')
    if not user_id:
        current_app.logger.warning("get_current_user_id: user_id not found in session.")
    return user_id

def get_current_user_email():
    """
    Placeholder: Returns the current authenticated user's email.
    User should implement this to retrieve user email from session or token.
    Example: return flask_session.get('user_email')
    """
    # Assuming user_email is stored in session after login by auth_routes.py
    user_email = flask_session.get('user_email')
    if not user_email:
        current_app.logger.warning("get_current_user_email: user_email not found in session.")
    return user_email

def login_required(f):
    """
    Placeholder: Decorator to ensure the user is logged in.
    User should replace this with their actual login_required decorator
    from their authentication system (e.g., one that checks Firebase ID token).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in flask_session : # or however user session is identified
            current_app.logger.warning("Access denied: User not logged in.")
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

stripe_bp = Blueprint('stripe_api', __name__, url_prefix='/api/stripe')

# Configure Stripe API key at blueprint level or ensure it's set globally
# stripe.api_key is already set in membership_service.py, which is good.

@stripe_bp.route('/create-checkout-session', methods=['POST'])
@login_required # Apply your authentication decorator
def create_checkout_session():
    """
    Creates a Stripe Checkout Session for a user to subscribe to a plan.
    Expects a 'priceId' in the JSON request body.
    """
    data = request.get_json()
    price_id = data.get('priceId')

    if not price_id:
        return jsonify({'error': 'priceId is required'}), 400

    user_id = get_current_user_id()
    user_email = get_current_user_email()

    if not user_id or not user_email:
        # This case should ideally be caught by @login_required,
        # but as a fallback if placeholder functions return None.
        current_app.logger.error(f"User ID or Email not found for checkout session. User ID: {user_id}, Email: {user_email}")
        return jsonify({'error': 'User authentication details not found. Please log in again.'}), 401

    try:
        membership_service = MembershipService()
        stripe_customer_id = membership_service.ensure_stripe_customer(user_id, user_email)

        # User needs to add APP_BASE_URL to their config/settings.py
        # e.g., APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:8080')
        # For deployed environments, this should be the actual domain.
        your_domain = app_config.APP_BASE_URL if hasattr(app_config, 'APP_BASE_URL') else current_app.config.get('APP_BASE_URL', 'http://localhost:8080')
        if not your_domain or your_domain == 'http://localhost:8080':
             current_app.logger.warning("APP_BASE_URL is not configured or default. Ensure it's set for proper redirect URLs.")


        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=f"{your_domain}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{your_domain}/payment/cancel",
            client_reference_id=user_id  # CRITICAL: Pass your internal user ID
        )
        return jsonify({'sessionId': checkout_session.id})
    except Exception as e:
        # Use current_app.logger if configured, otherwise fallback to print or standard logging
        logger = current_app.logger if hasattr(current_app, 'logger') and current_app.logger else logging.getLogger(__name__)
        logger.error(f"Error creating Stripe checkout session for user {user_id}: {e}")
        return jsonify({'error': str(e)}), 500


@stripe_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """
    Handles incoming webhook events from Stripe.
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    # Ensure STRIPE_WEBHOOK_SECRET is loaded, e.g., from app_config or current_app.config
    # It's loaded in config.settings.py, so app_config.STRIPE_WEBHOOK_SECRET should work.
    webhook_secret = app_config.STRIPE_WEBHOOK_SECRET

    logger = current_app.logger if hasattr(current_app, 'logger') and current_app.logger else logging.getLogger(__name__)

    if not webhook_secret:
        logger.error("Stripe webhook secret is not configured.")
        return jsonify({'error': 'Webhook secret not configured on server.'}), 500

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:  # Invalid payload
        logger.error(f"Webhook ValueError: Invalid payload. {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:  # Invalid signature
        logger.error(f"Webhook SignatureVerificationError: Invalid signature. {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error(f"Webhook construction error: {e}")
        return jsonify({'error': 'Webhook construction failed'}), 400

    membership_service = MembershipService()

    # Handle the event
    if event.type == 'checkout.session.completed':
        session = event.data.object  # stripe.checkout.Session object
        logger.info(f"Received event: {event.type} for client_reference_id: {session.get('client_reference_id')}")
        if session.payment_status == 'paid':
            membership_service.update_membership_from_stripe_checkout_session(session)
        else:
            logger.info(f"Checkout session {session.id} completed but payment_status is '{session.payment_status}'. No immediate membership update based on this event state.")

    elif event.type == 'customer.subscription.created':
        subscription = event.data.object # stripe.Subscription object
        logger.info(f"Received event: {event.type} for customer {subscription.customer}, subscription {subscription.id}")
        # This event is often informational. `checkout.session.completed` or `invoice.paid` usually trigger active status.
        # However, it can be useful to ensure the subscription record starts to exist in your system.
        membership_service.update_membership_from_stripe_subscription_event(subscription)

    elif event.type == 'customer.subscription.updated':
        subscription = event.data.object  # stripe.Subscription object
        logger.info(f"Received event: {event.type} for customer {subscription.customer}, subscription {subscription.id}")
        membership_service.update_membership_from_stripe_subscription_event(subscription)

    elif event.type == 'customer.subscription.deleted': # Occurs when a subscription is actually canceled
        subscription = event.data.object  # stripe.Subscription object
        logger.info(f"Received event: {event.type} for customer {subscription.customer}, subscription {subscription.id}")
        membership_service.update_membership_from_stripe_subscription_event(subscription)

    # Example: Handling invoice payment success, which can also confirm an active subscription
    elif event.type == 'invoice.payment_succeeded':
        invoice = event.data.object # stripe.Invoice object
        logger.info(f"Received event: {event.type} for invoice {invoice.id}, customer {invoice.customer}, subscription {invoice.subscription}")
        if invoice.subscription: # Ensure it's related to a subscription
            try:
                # Retrieve the subscription to get its current state, as invoice event might not have all details
                stripe_subscription = stripe.Subscription.retrieve(invoice.subscription)
                membership_service.update_membership_from_stripe_subscription_event(stripe_subscription)
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error retrieving subscription {invoice.subscription} after invoice.payment_succeeded: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing invoice.payment_succeeded for subscription {invoice.subscription}: {e}")
        else:
            logger.info(f"Invoice {invoice.id} payment succeeded but not linked to a subscription. No membership update from this event path.")

    # Example: Handling invoice payment failure
    elif event.type == 'invoice.payment_failed':
        invoice = event.data.object # stripe.Invoice object
        logger.info(f"Received event: {event.type} for invoice {invoice.id}, customer {invoice.customer}, subscription {invoice.subscription}")
        if invoice.subscription:
            try:
                stripe_subscription = stripe.Subscription.retrieve(invoice.subscription)
                # The subscription status (e.g., 'past_due') should reflect this.
                # The 'customer.subscription.updated' event often follows.
                membership_service.update_membership_from_stripe_subscription_event(stripe_subscription)
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error retrieving subscription {invoice.subscription} after invoice.payment_failed: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing invoice.payment_failed for subscription {invoice.subscription}: {e}")
        else:
            logger.info(f"Invoice {invoice.id} payment failed but not linked to a subscription. No membership update from this event path.")

    else:
        logger.info(f"Unhandled Stripe event type: {event.type}")

    return jsonify({'status': 'success'}), 200


@stripe_bp.route('/create-customer-portal-session', methods=['POST'])
@login_required
def create_customer_portal_session():
    """
    Creates a Stripe Billing Portal session for the user to manage their subscription.
    """
    logger = current_app.logger if hasattr(current_app, 'logger') and current_app.logger else logging.getLogger(__name__)
    user_id = get_current_user_id()

    if not user_id:
        logger.error("create_customer_portal_session: User ID not found. User must be logged in.")
        return jsonify({'error': 'User authentication failed.'}), 401

    try:
        membership_service = MembershipService()
        membership_data = membership_service.get_user_membership(user_id)
        stripe_customer_id = membership_data.get('stripeCustomerId')

        if not stripe_customer_id:
            logger.warning(f"User {user_id} attempted to access customer portal without a Stripe customer ID.")
            return jsonify({'error': 'Stripe customer ID not found for this user. No active subscription to manage or payment method on file.'}), 404

        # Construct the return_url
        # User needs to add APP_BASE_URL to their config/settings.py
        your_domain = app_config.APP_BASE_URL if hasattr(app_config, 'APP_BASE_URL') else current_app.config.get('APP_BASE_URL', 'http://localhost:8080')
        if not your_domain or your_domain == 'http://localhost:8080':
             logger.warning("APP_BASE_URL is not configured or default for customer portal return. Ensure it's set for proper redirect URLs.")

        # User should adjust '/profile' to their desired return page after portal session
        return_url = f"{your_domain}/profile"

        portal_session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url
        )
        return jsonify({'url': portal_session.url})

    except stripe.error.StripeError as se:
        logger.error(f"Stripe Billing Portal session creation StripeError for user {user_id}: {se}")
        return jsonify({'error': f"Stripe error: {str(se)}"}), 500
    except ConnectionError as ce: # If MembershipService had issues
        logger.error(f"Connection error while creating portal session for user {user_id}: {ce}")
        return jsonify({'error': "Service initialization failed. Please try again later."}), 503
    except Exception as e:
        logger.error(f"Unexpected error creating Stripe Billing Portal session for user {user_id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not create customer portal session due to an unexpected error.'}), 500


# Ensure current_app.logger is configured in your main app.py.
# If not, you might use:
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# And use `logger.info`, `logger.error` etc.
# However, Flask's `current_app.logger` is preferred when available.
# For the purpose of this script, we assume current_app.logger will be available
# once the blueprint is registered with the Flask app.
# The placeholder functions for user ID/email also use current_app.logger.
# If flask_session is used, it needs to be initialized by the app.
```
