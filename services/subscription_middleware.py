"""
Subscription middleware for feature gating and usage limits.
"""
import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import session, jsonify, redirect, url_for, request, g
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

# Feature limits for free vs premium users
FEATURE_LIMITS = {
    'free': {
        'chat_messages': 5,  # Per day
        'searches': 10,  # Per day
        'videos_generated': 1,  # Per day
        'ai_models': ['gpt-3.5-turbo', 'gemini-1.0-pro'],  # Basic models only
        'export_enabled': False,
        'advanced_analytics': False,
        'custom_personalities': False,
        'priority_support': False
    },
    'premium': {
        'chat_messages': -1,  # Unlimited
        'searches': -1,  # Unlimited
        'videos_generated': 10,  # Per day
        'ai_models': 'all',  # All available models
        'export_enabled': True,
        'advanced_analytics': True,
        'custom_personalities': True,
        'priority_support': True
    }
}

def init_subscription_context():
    """Initialize subscription context for the request."""
    if 'user_id' not in session:
        g.subscription = {
            'is_premium': False,
            'status': 'none',
            'plan_id': 'zero',
            'limits': FEATURE_LIMITS['free']
        }
        return
    
    stripe_service = StripeService()
    firebase_uid = session.get('user_id')
    # Ensure a free subscription record exists for visibility/analytics
    try:
        stripe_service.ensure_free_subscription(firebase_uid, session.get('user_email'))
    except Exception:
        logger.debug("Unable to ensure free subscription record for user", exc_info=True)
    
    # Get subscription status
    subscription_status = stripe_service.get_subscription_status(firebase_uid)
    
    # Get usage stats
    usage_stats = stripe_service.get_usage_stats(firebase_uid)
    
    # Set context
    g.subscription = {
        'is_premium': subscription_status.get('is_premium', False),
        'status': subscription_status.get('status', 'none'),
        'current_period_end': subscription_status.get('current_period_end'),
        'cancel_at_period_end': subscription_status.get('cancel_at_period_end', False),
        'plan_id': subscription_status.get('plan_id', 'zero'),
        'limits': FEATURE_LIMITS['premium'] if subscription_status.get('is_premium') else FEATURE_LIMITS['free'],
        'usage': usage_stats
    }

def subscription_context_processor():
    """Flask context processor to inject subscription data into templates."""
    subscription = getattr(g, 'subscription', {
        'is_premium': False,
        'status': 'none',
        'limits': FEATURE_LIMITS['free']
    })
    return {'subscription': subscription}

def premium_required(f: Callable) -> Callable:
    """Decorator to require premium subscription for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({
                    'error': 'Authentication required',
                    'redirect': url_for('auth.login')
                }), 401
            return redirect(url_for('auth.login'))
        
        # Check subscription status
        if not hasattr(g, 'subscription'):
            init_subscription_context()
        
        if not g.subscription.get('is_premium', False):
            if request.is_json:
                return jsonify({
                    'error': 'Premium subscription required',
                    'upgrade_url': url_for('subscription.manage'),
                    'message': 'This feature requires a premium subscription'
                }), 403
            return redirect(url_for('subscription.manage'))
        
        return f(*args, **kwargs)
    return decorated_function

def check_feature_limit(feature: str, current_usage: Optional[int] = None, 
                       custom_limit: Optional[int] = None) -> Dict[str, Any]:
    """Check if user has reached feature limit."""
    result = {
        'allowed': True,
        'limit': -1,
        'current': 0,
        'remaining': -1,
        'is_premium': False,
        'message': None
    }
    
    # Get subscription context
    if not hasattr(g, 'subscription'):
        init_subscription_context()
    
    subscription = g.subscription
    result['is_premium'] = subscription.get('is_premium', False)
    
    # Get limit for feature
    limits = subscription.get('limits', FEATURE_LIMITS['free'])
    limit = custom_limit if custom_limit is not None else limits.get(feature, -1)
    
    # If unlimited (-1), always allow
    if limit == -1:
        result['limit'] = -1
        result['remaining'] = -1
        return result
    
    # Get current usage
    if current_usage is None:
        usage = subscription.get('usage', {})
        current_usage = usage.get(feature, 0)
    
    result['limit'] = limit
    result['current'] = current_usage
    result['remaining'] = max(0, limit - current_usage)
    
    # Check if limit exceeded
    if current_usage >= limit:
        result['allowed'] = False
        result['message'] = f"You've reached your daily limit of {limit} {feature.replace('_', ' ')}. Upgrade to Premium for unlimited access."
    
    return result

def increment_feature_usage(feature: str, amount: int = 1) -> bool:
    """Increment usage counter for a feature."""
    if 'user_id' not in session:
        return False
    
    stripe_service = StripeService()
    firebase_uid = session.get('user_id')
    
    return stripe_service.increment_usage(firebase_uid, feature, amount)

def feature_limited(feature: str, custom_limit: Optional[int] = None):
    """Decorator to enforce feature limits."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({
                        'error': 'Authentication required',
                        'redirect': url_for('auth.login')
                    }), 401
                return redirect(url_for('auth.login'))
            
            # Check feature limit
            limit_result = check_feature_limit(feature, custom_limit=custom_limit)
            
            if not limit_result['allowed']:
                if request.is_json:
                    return jsonify({
                        'error': 'Feature limit reached',
                        'message': limit_result['message'],
                        'upgrade_url': url_for('subscription.manage'),
                        'limit': limit_result['limit'],
                        'current': limit_result['current']
                    }), 429
                return redirect(url_for('subscription.manage'))
            
            # Increment usage
            increment_feature_usage(feature)
            
            # Call the original function
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def model_allowed(model_name: str) -> bool:
    """Check if user can access a specific AI model."""
    if not hasattr(g, 'subscription'):
        init_subscription_context()
    
    subscription = g.subscription
    limits = subscription.get('limits', FEATURE_LIMITS['free'])
    allowed_models = limits.get('ai_models', [])
    
    if allowed_models == 'all':
        return True
    
    return model_name in allowed_models

def get_available_models() -> list:
    """Get list of AI models available to the user."""
    if not hasattr(g, 'subscription'):
        init_subscription_context()
    
    subscription = g.subscription
    limits = subscription.get('limits', FEATURE_LIMITS['free'])
    allowed_models = limits.get('ai_models', [])
    
    if allowed_models == 'all':
        # Return all available models
        return [
            'gpt-4o-mini',
            'gpt-4',
            'gpt-3.5-turbo',
            'claude-3-opus',
            'claude-3-sonnet',
            'claude-3-haiku',
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-1.0-pro',
            'grok-beta'
        ]
    
    return allowed_models

def feature_enabled(feature_name: str) -> bool:
    """Check if a specific feature is enabled for the user."""
    if not hasattr(g, 'subscription'):
        init_subscription_context()
    
    subscription = g.subscription
    limits = subscription.get('limits', FEATURE_LIMITS['free'])
    
    return limits.get(feature_name, False)