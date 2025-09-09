"""Middleware for subscription-based access control."""
import logging
from functools import wraps
from flask import session, jsonify, request, redirect, url_for, flash
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

# Initialize Stripe service
stripe_service = None
try:
    stripe_service = StripeService()
except ValueError as e:
    logger.warning(f"Stripe service not initialized: {e}")


def premium_required(f):
    """Decorator to require premium subscription for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not stripe_service:
            # If Stripe is not configured, allow access (for development)
            logger.warning("Stripe not configured, allowing access to premium feature")
            return f(*args, **kwargs)
        
        firebase_uid = session.get('user_id')
        if not firebase_uid:
            # User not authenticated
            if request.headers.get('Content-Type') == 'application/json' or \
               request.headers.get('Accept', '').find('application/json') > -1 or \
               request.path.startswith('/api/'):
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            else:
                return redirect(url_for('auth.login', next=request.url))
        
        # Check if user has premium subscription
        if not stripe_service.is_user_premium(firebase_uid):
            if request.headers.get('Content-Type') == 'application/json' or \
               request.headers.get('Accept', '').find('application/json') > -1 or \
               request.path.startswith('/api/'):
                return jsonify({
                    "error": "Premium subscription required",
                    "subscription_required": True,
                    "upgrade_url": "/subscription"
                }), 403
            else:
                flash('Premium subscription required to access this feature.', 'warning')
                return redirect(url_for('stripe.subscription_page'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_user_subscription_context(firebase_uid: str) -> dict:
    """Get subscription context for templates."""
    if not stripe_service or not firebase_uid:
        return {
            'is_premium': False,
            'subscription': None,
            'stripe_configured': False
        }
    
    try:
        is_premium = stripe_service.is_user_premium(firebase_uid)
        subscription = stripe_service.get_user_subscription(firebase_uid)
        
        return {
            'is_premium': is_premium,
            'subscription': subscription,
            'stripe_configured': True
        }
    except Exception as e:
        logger.error(f"Error getting subscription context: {e}")
        return {
            'is_premium': False,
            'subscription': None,
            'stripe_configured': True,
            'error': str(e)
        }


def check_feature_limit(feature_name: str, current_usage: int, free_limit: int) -> dict:
    """Check if user has exceeded feature limits based on subscription status."""
    firebase_uid = session.get('user_id')
    
    if not stripe_service or not firebase_uid:
        # If Stripe not configured, use free limits
        return {
            'allowed': current_usage < free_limit,
            'is_premium': False,
            'usage': current_usage,
            'limit': free_limit,
            'remaining': max(0, free_limit - current_usage)
        }
    
    try:
        is_premium = stripe_service.is_user_premium(firebase_uid)
        
        if is_premium:
            # Premium users have unlimited access
            return {
                'allowed': True,
                'is_premium': True,
                'usage': current_usage,
                'limit': None,  # Unlimited
                'remaining': None
            }
        else:
            # Free users have limits
            return {
                'allowed': current_usage < free_limit,
                'is_premium': False,
                'usage': current_usage,
                'limit': free_limit,
                'remaining': max(0, free_limit - current_usage)
            }
    except Exception as e:
        logger.error(f"Error checking feature limit: {e}")
        # Default to free limits on error
        return {
            'allowed': current_usage < free_limit,
            'is_premium': False,
            'usage': current_usage,
            'limit': free_limit,
            'remaining': max(0, free_limit - current_usage),
            'error': str(e)
        }