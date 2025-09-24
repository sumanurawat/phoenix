"""
Stripe API routes for subscription management.
"""
import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from api.auth_routes import login_required
from services.stripe_service import StripeService
from services.subscription_middleware import (
    init_subscription_context, 
    premium_required,
    check_feature_limit
)

logger = logging.getLogger(__name__)

# Create blueprint
stripe_bp = Blueprint('stripe', __name__, url_prefix='/api/stripe')
subscription_bp = Blueprint('subscription', __name__)

# Initialize Stripe service
from middleware.csrf_protection import csrf_protect
stripe_service = StripeService()

# API Routes
@stripe_bp.route('/config', methods=['GET'])
def get_stripe_config():
    """Get Stripe configuration for frontend."""
    config = stripe_service.get_config()
    return jsonify(config)

@stripe_bp.route('/create-checkout-session', methods=['POST'])
@csrf_protect
@login_required
def create_checkout_session():
    """Create a Stripe checkout session."""
    try:
        firebase_uid = session.get('user_id')
        email = session.get('user_email')
        
        if not firebase_uid or not email:
            return jsonify({'error': 'User information missing'}), 400
        
        # Get URLs for redirect
        success_url = url_for('subscription.success', _external=True)
        cancel_url = url_for('subscription.cancel', _external=True)
        
        # Create checkout session
        result = stripe_service.create_checkout_session(
            firebase_uid=firebase_uid,
            email=email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if not result:
            return jsonify({'error': 'Failed to create checkout session'}), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': str(e)}), 500

@stripe_bp.route('/subscription/status', methods=['GET'])
@login_required
def get_subscription_status():
    """Get current subscription status."""
    try:
        firebase_uid = session.get('user_id')
        status = stripe_service.get_subscription_status(firebase_uid)
        
        # Add usage stats
        usage = stripe_service.get_usage_stats(firebase_uid)
        status['usage'] = usage
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        return jsonify({'error': str(e)}), 500

@stripe_bp.route('/subscription/cancel', methods=['POST'])
@csrf_protect
@login_required
def cancel_subscription():
    """Cancel subscription at period end."""
    try:
        firebase_uid = session.get('user_id')
        
        # Check if user has an active subscription first
        subscription_status = stripe_service.get_subscription_status(firebase_uid)
        if not subscription_status.get('is_premium'):
            return jsonify({
                'error': 'No active subscription found',
                'message': 'You do not have an active premium subscription to cancel.'
            }), 400
        
        success = stripe_service.cancel_subscription(firebase_uid)
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Subscription will be canceled at the end of the billing period'
            })
        else:
            return jsonify({
                'error': 'Unable to cancel subscription',
                'message': 'There was an issue canceling your subscription. Please contact support if this problem persists.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return jsonify({
            'error': 'Subscription cancellation failed',
            'message': 'An unexpected error occurred. Please try again or contact support.'
        }), 500

@stripe_bp.route('/subscription/reactivate', methods=['POST'])
@csrf_protect
@login_required
def reactivate_subscription():
    """Reactivate a cancelled subscription."""
    try:
        firebase_uid = session.get('user_id')
        success = stripe_service.reactivate_subscription(firebase_uid)
        
        if success:
            return jsonify({'success': True, 'message': 'Subscription reactivated successfully'})
        else:
            return jsonify({'error': 'Failed to reactivate subscription'}), 500
            
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        return jsonify({'error': str(e)}), 500

@stripe_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    logger.info("🔔 WEBHOOK RECEIVED! Processing Stripe webhook...")
    
    # Log request details
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request path: {request.path}")
    logger.info(f"Content-Type: {request.headers.get('Content-Type', 'Not provided')}")
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    logger.info(f"Payload size: {len(payload)} bytes")
    logger.info(f"Signature header present: {bool(sig_header)}")
    
    if not sig_header:
        logger.error("❌ No Stripe signature header found in webhook request")
        return jsonify({'error': 'No signature header'}), 400
    
    # Preview the payload (first 200 chars)
    payload_preview = payload.decode('utf-8')[:200] if payload else "Empty payload"
    logger.info(f"Payload preview: {payload_preview}...")
    
    logger.info("🔄 Calling stripe_service.handle_webhook_event()...")
    result = stripe_service.handle_webhook_event(payload, sig_header)
    logger.info(f"✅ Webhook processing completed with result: {type(result)}")
    
    if isinstance(result, tuple):
        logger.info(f"Returning tuple result: {result[0]}, status code: {result[1]}")
        return jsonify(result[0]), result[1]
    
    logger.info(f"Returning single result: {result}")
    return jsonify(result)

@stripe_bp.route('/usage/check/<feature>', methods=['GET'])
@login_required
def check_usage(feature):
    """Check if user can use a feature based on limits."""
    try:
        result = check_feature_limit(feature)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error checking usage: {e}")
        return jsonify({'error': str(e)}), 500

# UI Routes
@subscription_bp.route('/subscription')
@login_required
def manage():
    """Subscription management page."""
    # Initialize subscription context
    init_subscription_context()
    
    firebase_uid = session.get('user_id')
    
    # Get subscription status
    subscription_status = stripe_service.get_subscription_status(firebase_uid)
    
    # Get usage stats
    usage_stats = stripe_service.get_usage_stats(firebase_uid)
    
    # Get Stripe config
    stripe_config = stripe_service.get_config()
    
    context = {
        'title': 'Manage Subscription',
        'subscription': subscription_status,
        'usage': usage_stats,
        'stripe_config': stripe_config,
        'user_email': session.get('user_email'),
        'user_name': session.get('user_name')
    }
    
    return render_template('subscription.html', **context)

@subscription_bp.route('/subscription/success')
@login_required
def success():
    """Subscription success page with fallback processing."""
    logger.info("🎉 User reached subscription success page")
    
    firebase_uid = session.get('user_id')
    user_email = session.get('user_email')
    
    logger.info(f"👤 Processing success page for user: {firebase_uid} ({user_email})")
    
    # Fallback mechanism: Check if subscription was created by webhook
    # If not, try to process any recent successful checkout sessions
    try:
        logger.info("🔍 Checking if subscription already exists...")
        status = stripe_service.get_subscription_status(firebase_uid)
        
        if not status.get('is_premium'):
            logger.info("⚠️ User is not premium yet - webhook might have failed. Checking for recent checkout sessions...")
            
            # Look for recent successful checkout sessions for this user
            import stripe
            recent_sessions = stripe.checkout.Session.list(
                limit=10,
                expand=['data.subscription']
            )
            
            logger.info(f"📋 Found {len(recent_sessions.data)} recent checkout sessions")
            
            for checkout_session in recent_sessions.data:
                # Check if this session belongs to our user and is completed
                session_firebase_uid = checkout_session.metadata.get('firebase_uid')
                session_customer_email = checkout_session.customer_email
                
                logger.info(f"🔍 Checking session {checkout_session.id}:")
                logger.info(f"   Firebase UID: {session_firebase_uid}")
                logger.info(f"   Customer Email: {session_customer_email}")
                logger.info(f"   Status: {checkout_session.status}")
                logger.info(f"   Payment Status: {checkout_session.payment_status}")
                
                if (checkout_session.status == 'complete' and 
                    checkout_session.payment_status == 'paid' and 
                    (session_firebase_uid == firebase_uid or session_customer_email == user_email)):
                    
                    logger.info(f"✅ Found matching completed session: {checkout_session.id}")
                    
                    # Check if we already have a subscription record for this
                    if checkout_session.subscription:
                        # Handle both string ID and Subscription object
                        if isinstance(checkout_session.subscription, str):
                            subscription_id = checkout_session.subscription
                        else:
                            subscription_id = checkout_session.subscription.id
                        logger.info(f"🔍 Checking if subscription {subscription_id} exists in Firebase...")
                        
                        # Check if subscription already exists in our database
                        if stripe_service.db:
                            existing_sub = stripe_service.db.collection('user_subscriptions').document(subscription_id).get()
                            if not existing_sub.exists:
                                logger.info(f"🚨 Subscription {subscription_id} not found in Firebase - processing manually!")
                                
                                # Manually process this checkout session
                                result = stripe_service._handle_checkout_completed(checkout_session)
                                if result.get('success'):
                                    logger.info(f"🎉 Successfully processed checkout session {checkout_session.id} manually!")
                                else:
                                    logger.error(f"❌ Failed to process checkout session manually: {result}")
                            else:
                                logger.info(f"✅ Subscription {subscription_id} already exists in Firebase")
                    break
        else:
            logger.info("✅ User is already premium - webhook worked correctly")
            
    except Exception as e:
        logger.error(f"❌ Error in fallback processing: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    return render_template('subscription_success.html', title='Payment Successful')

@subscription_bp.route('/subscription/cancel')
@login_required
def cancel():
    """Subscription cancellation page."""
    return render_template('subscription_cancel.html', title='Payment Cancelled')