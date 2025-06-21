"""
Subscription API Routes

API endpoints for handling Stripe subscription operations.
"""
import os
import logging
import stripe
from flask import Blueprint, request, jsonify, session, url_for
from api.auth_routes import login_required
from services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

subscription_bp = Blueprint('subscription', __name__)
subscription_service = SubscriptionService()

@subscription_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """
    Create a Stripe Checkout session for the logged-in user.
    
    Expected JSON payload:
    {
        "price_id": "price_1RcFAyGgo4tk9CEitD4wp0W"
    }
    """
    try:
        # Get user ID from session (never trust client data)
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get price ID from request
        data = request.get_json()
        if not data or 'price_id' not in data:
            return jsonify({'error': 'price_id is required'}), 400
        
        price_id = data['price_id']
        
        # Validate price ID (security check)
        valid_price_ids = [
            'price_1RcFAyGgo4tk9CEitD4wp0W',   # Basic - your actual Stripe price ID (corrected)
            'price_1RcFBNGgo4tk9CEiho0eTpaJ'     # Pro - your actual Stripe price ID
        ]
        
        # In development mode, also allow these common test patterns
        if os.getenv('FLASK_ENV') == 'development':
            valid_price_ids.extend([
                'price_test_basic', 'price_test_pro',  # Test patterns
                'price_1234567890abcdef',  # Example Stripe format
            ])
        
        if price_id not in valid_price_ids:
            return jsonify({'error': f'Invalid price_id: {price_id}. Please check your Stripe dashboard.'}), 400
        
        # Create success and cancel URLs
        base_url = request.url_root.rstrip('/')
        success_url = f"{base_url}{url_for('auth.profile')}?success=true"
        cancel_url = f"{base_url}{url_for('auth.profile')}?canceled=true"
        
        # Create Stripe checkout session
        checkout_url = subscription_service.create_checkout_session(
            user_id=user_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return jsonify({'checkout_url': checkout_url})
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'Failed to create checkout session'}), 500


@subscription_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    
    This endpoint receives events from Stripe when subscription status changes.
    """
    try:
        # Get the raw body and signature
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Verify webhook signature (security)
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, subscription_service.webhook_secret
            )
        except ValueError:
            logger.error("Invalid payload in Stripe webhook")
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in Stripe webhook")
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Handle the event
        success = subscription_service.handle_stripe_webhook(event)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to process webhook'}), 500
            
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500


@subscription_bp.route('/status', methods=['GET'])
@login_required
def get_subscription_status():
    """
    Get the current user's subscription status.
    
    Returns subscription information including tier, status, and features.
    """
    try:
        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get subscription status
        subscription = subscription_service.get_subscription_status(user_id)
        
        if not subscription:
            # Return default free subscription
            return jsonify({
                'subscription_tier': 'free',
                'status': 'active',
                'is_premium': False,
                'features': subscription_service.get_tier_config('free')['features']
            })
        
        # Get tier configuration
        tier_config = subscription_service.get_tier_config(subscription.subscription_tier)
        
        return jsonify({
            'subscription_tier': subscription.subscription_tier,
            'status': subscription.status,
            'is_premium': subscription.is_premium(),
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'features': tier_config['features'],
            'limits': tier_config['limits']
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        return jsonify({'error': 'Failed to get subscription status'}), 500


@subscription_bp.route('/plans', methods=['GET'])
def get_available_plans():
    """
    Get information about available subscription plans.
    
    This endpoint is public and doesn't require authentication.
    """
    try:
        from models.subscription import SUBSCRIPTION_TIERS
        
        plans = []
        for tier_id, config in SUBSCRIPTION_TIERS.items():
            if tier_id != 'free':  # Don't include free tier in purchasable plans
                plans.append({
                    'id': tier_id,
                    'name': config['name'],
                    'price': config['price'],
                    'price_id': config.get('price_id'),
                    'features': config['features'],
                    'limits': config['limits']
                })
        
        return jsonify({'plans': plans})
        
    except Exception as e:
        logger.error(f"Error getting available plans: {e}")
        return jsonify({'error': 'Failed to get plans'}), 500


@subscription_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """
    Cancel the current user's subscription.
    
    This will set the subscription to cancel at the end of the current period.
    """
    try:
        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get current subscription
        subscription = subscription_service.get_subscription_status(user_id)
        if not subscription or not subscription.stripe_subscription_id:
            return jsonify({'error': 'No active subscription found'}), 404
        
        # Cancel subscription in Stripe (at period end)
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        return jsonify({'status': 'success', 'message': 'Subscription will be canceled at the end of the current period'})
        
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500
