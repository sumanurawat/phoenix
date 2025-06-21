"""
Subscription Decorators

Decorators for protecting routes and features based on subscription status.
"""
import functools
from flask import session, jsonify, redirect, url_for, request
from services.subscription_service import SubscriptionService

subscription_service = SubscriptionService()

def subscription_required(tier_required="basic"):
    """
    Decorator to require a specific subscription tier for access.
    
    Args:
        tier_required: Minimum subscription tier required ("basic" or "pro")
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if user is logged in
            user_id = session.get('user_id')
            if not user_id:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    return redirect(url_for('auth.login', next=request.url))
            
            # Check subscription status
            subscription = subscription_service.get_subscription_status(user_id)
            
            if not subscription or not subscription.is_active():
                if request.is_json:
                    return jsonify({'error': 'Active subscription required'}), 403
                else:
                    return redirect(url_for('auth.profile') + '?upgrade=true')
            
            # Check if user has required tier
            tier_levels = {"free": 0, "basic": 1, "pro": 2}
            user_level = tier_levels.get(subscription.subscription_tier, 0)
            required_level = tier_levels.get(tier_required, 1)
            
            if user_level < required_level:
                if request.is_json:
                    return jsonify({'error': f'{tier_required.title()} subscription required'}), 403
                else:
                    return redirect(url_for('auth.profile') + '?upgrade=true')
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def feature_required(feature_name):
    """
    Decorator to require access to a specific feature.
    
    Args:
        feature_name: Name of the feature to check access for
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if user is logged in
            user_id = session.get('user_id')
            if not user_id:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    return redirect(url_for('auth.login', next=request.url))
            
            # Check feature access
            has_access = subscription_service.has_feature_access(user_id, feature_name)
            
            if not has_access:
                if request.is_json:
                    return jsonify({'error': f'Feature "{feature_name}" requires a subscription'}), 403
                else:
                    return redirect(url_for('auth.profile') + '?upgrade=true')
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def usage_limit_check(limit_type, increment=1):
    """
    Decorator to check and enforce usage limits based on subscription.
    
    Args:
        limit_type: Type of limit to check (e.g., "max_links", "api_calls")
        increment: Amount to increment usage by (default 1)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if user is logged in
            user_id = session.get('user_id')
            if not user_id:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                else:
                    return redirect(url_for('auth.login', next=request.url))
            
            # Get subscription and limits
            subscription = subscription_service.get_subscription_status(user_id)
            tier_config = subscription_service.get_tier_config(
                subscription.subscription_tier if subscription else "free"
            )
            
            limits = tier_config.get('limits', {})
            limit_value = limits.get(limit_type, 0)
            
            # -1 means unlimited
            if limit_value == -1:
                return func(*args, **kwargs)
            
            # TODO: Implement actual usage tracking
            # For now, we'll skip the usage check and just proceed
            # In a real implementation, you would:
            # 1. Check current usage from database
            # 2. Compare with limit
            # 3. Return error if limit exceeded
            # 4. Increment usage counter after successful execution
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
