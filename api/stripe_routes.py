"""
Stripe API Routes for Subscription Management

This module provides Flask routes for handling Stripe operations including:
- Checkout session creation
- Subscription status retrieval
- Subscription management (cancel/reactivate)
- Webhook handling
"""

import os
import logging
from flask import Blueprint, request, jsonify, session, url_for

from services.stripe_service import StripeService
from services.subscription_middleware import get_subscription_status

logger = logging.getLogger(__name__)

# Create blueprint
stripe_bp = Blueprint('stripe', __name__, url_prefix='/api/stripe')

# Initialize service
stripe_service = StripeService()


@stripe_bp.route('/config', methods=['GET'])
def get_stripe_config():
    """Get Stripe configuration for frontend."""
    try:
        config = stripe_service.get_config()
        return jsonify(config)
    except Exception as e:
        logger.error(f"Failed to get Stripe config: {e}")
        return jsonify({
            'error': 'Failed to get configuration',
            'configured': False
        }), 500


@stripe_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session for subscription."""
    try:
        # Check authentication
        firebase_uid = session.get('firebase_uid')
        email = session.get('email')
        
        if not firebase_uid or not email:
            return jsonify({
                'error': 'Authentication required'
            }), 401
        
        # Check if user already has active subscription
        subscription_status = get_subscription_status(firebase_uid)
        if subscription_status['is_premium']:
            return jsonify({
                'error': 'User already has active subscription'
            }), 400
        
        # Create checkout session
        success_url = request.form.get('success_url') or url_for('subscription_success', _external=True)
        cancel_url = request.form.get('cancel_url') or url_for('subscription_cancel', _external=True)
        
        checkout_url = stripe_service.create_checkout_session(
            firebase_uid=firebase_uid,
            email=email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if not checkout_url:
            return jsonify({
                'error': 'Failed to create checkout session'
            }), 500
        
        return jsonify({
            'checkout_url': checkout_url
        })
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return jsonify({
            'error': 'Failed to create checkout session'
        }), 500


@stripe_bp.route('/subscription/status', methods=['GET'])
def get_subscription_status_api():
    """Get user's subscription status."""
    try:
        firebase_uid = session.get('firebase_uid')
        
        if not firebase_uid:
            return jsonify({
                'error': 'Authentication required'
            }), 401
        
        subscription_status = get_subscription_status(firebase_uid)
        return jsonify(subscription_status)
        
    except Exception as e:
        logger.error(f"Failed to get subscription status: {e}")
        return jsonify({
            'error': 'Failed to get subscription status'
        }), 500


@stripe_bp.route('/subscription/cancel', methods=['POST'])
def cancel_subscription():
    """Cancel user's subscription (at period end)."""
    try:
        firebase_uid = session.get('firebase_uid')
        
        if not firebase_uid:
            return jsonify({
                'error': 'Authentication required'
            }), 401
        
        success = stripe_service.cancel_subscription(firebase_uid)
        
        if not success:
            return jsonify({
                'error': 'Failed to cancel subscription'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Subscription will be cancelled at the end of the current billing period'
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return jsonify({
            'error': 'Failed to cancel subscription'
        }), 500


@stripe_bp.route('/subscription/reactivate', methods=['POST'])
def reactivate_subscription():
    """Reactivate a cancelled subscription."""
    try:
        firebase_uid = session.get('firebase_uid')
        
        if not firebase_uid:
            return jsonify({
                'error': 'Authentication required'
            }), 401
        
        success = stripe_service.reactivate_subscription(firebase_uid)
        
        if not success:
            return jsonify({
                'error': 'Failed to reactivate subscription'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Subscription reactivated successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to reactivate subscription: {e}")
        return jsonify({
            'error': 'Failed to reactivate subscription'
        }), 500


@stripe_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        payload = request.get_data()
        signature = request.headers.get('Stripe-Signature')
        
        if not signature:
            logger.error("No Stripe signature in webhook request")
            return jsonify({'error': 'No signature'}), 400
        
        success = stripe_service.handle_webhook(payload, signature)
        
        if not success:
            return jsonify({'error': 'Webhook processing failed'}), 400
        
        return jsonify({'received': True})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 400


# Error handlers for the blueprint
@stripe_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@stripe_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500