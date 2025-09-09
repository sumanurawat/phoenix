"""Routes for Stripe payment processing and subscription management."""
import os
import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from api.auth_routes import login_required
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

stripe_bp = Blueprint('stripe', __name__, url_prefix='/api/stripe')

# Initialize Stripe service
stripe_service = None
try:
    stripe_service = StripeService()
except ValueError as e:
    logger.warning(f"Stripe service not initialized: {e}")


@stripe_bp.route('/config', methods=['GET'])
@login_required
def get_stripe_config():
    """Get Stripe configuration for frontend."""
    if not stripe_service:
        return jsonify({'error': 'Stripe not configured'}), 503
    
    return jsonify({
        'publishable_key': stripe_service.stripe_publishable_key,
        'plans': {
            'premium_monthly': {
                'name': 'Premium Monthly',
                'price': '$5.00',
                'currency': 'USD',
                'interval': 'month',
                'features': [
                    'Unlimited AI conversations',
                    'Advanced analytics',
                    'Premium models access',
                    'Priority support'
                ]
            }
        }
    })


@stripe_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session for subscription."""
    if not stripe_service:
        return jsonify({'error': 'Stripe not configured'}), 503
    
    try:
        data = request.get_json()
        plan_id = data.get('plan_id', 'premium_monthly')
        
        firebase_uid = session.get('user_id')
        email = session.get('user_email')
        
        if not firebase_uid or not email:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Check if user already has active subscription
        if stripe_service.is_user_premium(firebase_uid):
            return jsonify({'error': 'User already has active subscription'}), 400
        
        # Create checkout session
        success_url = request.url_root.rstrip('/') + '/subscription/success?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = request.url_root.rstrip('/') + '/subscription/cancel'
        
        session_data = stripe_service.create_checkout_session(
            firebase_uid=firebase_uid,
            email=email,
            plan_id=plan_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return jsonify({
            'success': True,
            'session_id': session_data['session_id'],
            'url': session_data['url']
        })
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500


@stripe_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    if not stripe_service:
        return jsonify({'error': 'Stripe not configured'}), 503
    
    try:
        payload = request.get_data()
        signature = request.headers.get('stripe-signature')
        
        if not signature:
            return jsonify({'error': 'Missing signature'}), 400
        
        # Handle webhook event
        result = stripe_service.handle_webhook_event(payload, signature)
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500


@stripe_bp.route('/subscription/status', methods=['GET'])
@login_required
def get_subscription_status():
    """Get user's current subscription status."""
    if not stripe_service:
        return jsonify({'error': 'Stripe not configured'}), 503
    
    try:
        firebase_uid = session.get('user_id')
        if not firebase_uid:
            return jsonify({'error': 'User not authenticated'}), 401
        
        subscription = stripe_service.get_user_subscription(firebase_uid)
        is_premium = stripe_service.is_user_premium(firebase_uid)
        
        response_data = {
            'is_premium': is_premium,
            'subscription': subscription
        }
        
        if subscription:
            response_data['subscription'].update({
                'current_period_end_date': subscription.get('current_period_end'),
                'cancel_at_period_end': subscription.get('cancel_at_period_end', False)
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        return jsonify({'error': 'Failed to get subscription status'}), 500


@stripe_bp.route('/subscription/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user's subscription at period end."""
    if not stripe_service:
        return jsonify({'error': 'Stripe not configured'}), 503
    
    try:
        firebase_uid = session.get('user_id')
        if not firebase_uid:
            return jsonify({'error': 'User not authenticated'}), 401
        
        success = stripe_service.cancel_subscription(firebase_uid)
        
        if success:
            return jsonify({'success': True, 'message': 'Subscription will be canceled at period end'})
        else:
            return jsonify({'error': 'No active subscription found'}), 404
            
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500


# UI Routes for subscription management
@stripe_bp.route('/subscription', methods=['GET'])
@login_required
def subscription_page():
    """Render subscription management page."""
    return render_template('subscription.html', title='Subscription Management')


@stripe_bp.route('/subscription/success', methods=['GET'])
@login_required
def subscription_success():
    """Handle successful subscription creation."""
    session_id = request.args.get('session_id')
    return render_template('subscription_success.html', 
                         title='Subscription Successful',
                         session_id=session_id)


@stripe_bp.route('/subscription/cancel', methods=['GET'])
@login_required
def subscription_cancel():
    """Handle subscription cancellation."""
    return render_template('subscription_cancel.html', 
                         title='Subscription Canceled')