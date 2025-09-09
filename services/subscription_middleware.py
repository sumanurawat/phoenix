"""
Subscription Middleware for Feature Gating and Access Control

This module provides decorators and utilities for subscription-based feature gating,
ensuring that premium features are only accessible to users with active subscriptions.
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import session, jsonify, redirect, url_for, g, request

from services.stripe_service import StripeService

logger = logging.getLogger(__name__)


class SubscriptionMiddleware:
    """Middleware for handling subscription-based access control."""
    
    def __init__(self):
        self.stripe_service = StripeService()
    
    def get_user_subscription_status(self, firebase_uid: Optional[str] = None) -> Dict[str, Any]:
        """Get subscription status for current user or specified user."""
        if not firebase_uid:
            firebase_uid = session.get('firebase_uid')
        
        if not firebase_uid:
            return {
                'is_premium': False,
                'status': 'not_authenticated',
                'plan_id': None,
                'current_period_end': None,
                'cancel_at_period_end': False
            }
        
        return self.stripe_service.get_subscription_status(firebase_uid)
    
    def check_feature_limit(self, feature_name: str, current_usage: int, free_limit: int, firebase_uid: Optional[str] = None) -> Dict[str, Any]:
        """Check if user can access a feature based on their subscription and usage."""
        subscription_status = self.get_user_subscription_status(firebase_uid)
        
        # Premium users have unlimited access
        if subscription_status['is_premium']:
            return {
                'allowed': True,
                'reason': 'premium_user',
                'limit': None,
                'current_usage': current_usage,
                'upgrade_url': None
            }
        
        # Check free tier limits
        if current_usage >= free_limit:
            return {
                'allowed': False,
                'reason': 'limit_exceeded',
                'limit': free_limit,
                'current_usage': current_usage,
                'upgrade_url': url_for('subscription_page')
            }
        
        return {
            'allowed': True,
            'reason': 'within_free_limit',
            'limit': free_limit,
            'current_usage': current_usage,
            'upgrade_url': url_for('subscription_page')
        }


# Global middleware instance
subscription_middleware = SubscriptionMiddleware()


def premium_required(f: Callable) -> Callable:
    """
    Decorator that requires an active premium subscription to access the endpoint.
    
    Usage:
        @premium_required
        def premium_feature():
            return "This is a premium feature"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        firebase_uid = session.get('firebase_uid')
        
        if not firebase_uid:
            if request.is_json:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'auth_required'
                }), 401
            return redirect(url_for('auth.login'))
        
        subscription_status = subscription_middleware.get_user_subscription_status(firebase_uid)
        
        if not subscription_status['is_premium']:
            if request.is_json:
                return jsonify({
                    'error': 'Premium subscription required',
                    'code': 'premium_required',
                    'upgrade_url': url_for('subscription_page')
                }), 403
            return redirect(url_for('subscription_page'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def subscription_context_processor():
    """
    Context processor to inject subscription status into all templates.
    
    This should be registered with the Flask app:
        app.context_processor(subscription_context_processor)
    """
    firebase_uid = session.get('firebase_uid')
    
    if not firebase_uid:
        return {
            'subscription': {
                'is_premium': False,
                'status': 'not_authenticated',
                'plan_id': None,
                'current_period_end': None,
                'cancel_at_period_end': False,
                'stripe_configured': subscription_middleware.stripe_service.is_configured()
            }
        }
    
    subscription_status = subscription_middleware.get_user_subscription_status(firebase_uid)
    subscription_status['stripe_configured'] = subscription_middleware.stripe_service.is_configured()
    
    return {
        'subscription': subscription_status
    }


def check_feature_limit(feature_name: str, current_usage: int, free_limit: int, firebase_uid: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if user can access a feature based on their subscription and usage.
    
    Args:
        feature_name: Name of the feature being checked
        current_usage: Current usage count for the user
        free_limit: Maximum allowed usage for free users
        firebase_uid: User ID (optional, uses session if not provided)
    
    Returns:
        Dictionary with 'allowed' boolean and additional metadata
    """
    return subscription_middleware.check_feature_limit(feature_name, current_usage, free_limit, firebase_uid)


def get_subscription_status(firebase_uid: Optional[str] = None) -> Dict[str, Any]:
    """
    Get subscription status for a user.
    
    Args:
        firebase_uid: User ID (optional, uses session if not provided)
    
    Returns:
        Dictionary with subscription status information
    """
    return subscription_middleware.get_user_subscription_status(firebase_uid)


# Feature limits configuration
FEATURE_LIMITS = {
    'chat_messages': {
        'free_limit': 5,
        'description': 'AI conversations per day'
    },
    'search_queries': {
        'free_limit': 10,
        'description': 'Search queries per day'
    },
    'dataset_analysis': {
        'free_limit': 2,
        'description': 'Dataset analyses per day'
    },
    'short_links': {
        'free_limit': 10,
        'description': 'Short links created'
    },
    'export_conversations': {
        'free_limit': 0,
        'description': 'Conversation exports (Premium only)'
    },
    'advanced_models': {
        'free_limit': 0,
        'description': 'Access to premium AI models (Premium only)'
    }
}


def get_feature_limits() -> Dict[str, Dict[str, Any]]:
    """Get all feature limits configuration."""
    return FEATURE_LIMITS


def get_usage_stats(firebase_uid: str) -> Dict[str, Any]:
    """
    Get usage statistics for a user.
    
    This is a placeholder - in a real implementation, you would track
    actual usage in your database.
    """
    # TODO: Implement actual usage tracking
    return {
        'chat_messages': 3,
        'search_queries': 7,
        'dataset_analysis': 1,
        'short_links': 5,
        'export_conversations': 0,
        'advanced_models': 0
    }