"""
Feature Gating Decorators - New centralized system for feature access control.

This module provides decorators and utilities for enforcing feature access
based on the centralized feature registry.
"""
import logging
from functools import wraps
from typing import Callable, Optional, Dict, Any

from flask import session, jsonify, redirect, url_for, request, g

from services.feature_registry_service import feature_registry_service
from config.feature_registry import MembershipTier

logger = logging.getLogger(__name__)


def feature_required(feature_id: str, *, check_limits: bool = True, model_param: str = None):
    """
    Decorator to require a specific feature for route access.
    
    Args:
        feature_id: The feature ID from the registry
        check_limits: Whether to check and enforce usage limits
        model_param: If specified, validates model access from request parameter
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            user_id = session.get('user_id')
            if not user_id:
                return _handle_auth_required()
            
            # Check feature access
            can_access, reason = feature_registry_service.can_access_feature(feature_id, user_id)
            if not can_access:
                return _handle_access_denied(feature_id, reason)
            
            # Check usage limits if enabled
            if check_limits:
                limit_result = feature_registry_service.check_usage_limit(feature_id, user_id)
                if not limit_result.get('allowed', True):
                    return _handle_limit_exceeded(feature_id, limit_result)
            
            # Check model access if specified
            if model_param:
                model_name = _extract_model_from_request(model_param)
                if model_name and not feature_registry_service.is_model_allowed(model_name, feature_id, user_id):
                    return _handle_model_denied(model_name, feature_id)
            
            # Increment usage counter if limits are checked
            if check_limits:
                feature_registry_service.increment_usage(feature_id, user_id=user_id)
            
            # Call the original function
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def model_required(model_group: str = None):
    """
    Decorator to enforce model access restrictions.
    
    Args:
        model_group: Optional model group restriction (e.g., 'premium', 'basic')
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return _handle_auth_required()
            
            # Extract model from request
            model_name = _extract_model_from_request()
            if not model_name:
                # No model specified, allow through
                return f(*args, **kwargs)
            
            # Check model access
            if not feature_registry_service.is_model_allowed(model_name, user_id=user_id):
                return _handle_model_denied(model_name)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def tier_required(minimum_tier: MembershipTier):
    """
    Decorator to require a minimum subscription tier.
    
    Args:
        minimum_tier: The minimum tier required for access
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return _handle_auth_required()
            
            user_tier = feature_registry_service.get_user_tier(user_id)
            if not user_tier.can_access_tier(minimum_tier):
                return _handle_tier_required(minimum_tier)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def feature_limit_override(feature_id: str, limit_overrides: Dict[str, int]):
    """
    Decorator to override default feature limits for specific routes.
    
    Args:
        feature_id: The feature ID to override limits for
        limit_overrides: Dictionary of limit_type -> value overrides
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # TODO: Implement custom limit overrides
            # For now, use standard feature_required behavior
            return feature_required(feature_id)(f)(*args, **kwargs)
        
        return decorated_function
    return decorator


def beta_feature(feature_id: str):
    """
    Decorator for beta features with special handling.
    
    Args:
        feature_id: The beta feature ID
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Add beta feature logging
            logger.info(f"Beta feature '{feature_id}' accessed by user {session.get('user_id')}")
            
            # Use standard feature gating
            return feature_required(feature_id)(f)(*args, **kwargs)
        
        return decorated_function
    return decorator


# Helper functions

def _extract_model_from_request(param_name: str = 'model') -> Optional[str]:
    """Extract model name from request parameters."""
    if request.is_json:
        data = request.get_json() or {}
        return data.get(param_name)
    else:
        return request.form.get(param_name) or request.args.get(param_name)


def _handle_auth_required():
    """Handle authentication required response."""
    if request.is_json:
        return jsonify({
            'error': 'Authentication required',
            'code': 'AUTH_REQUIRED',
            'redirect': url_for('auth.login')
        }), 401
    return redirect(url_for('auth.login'))


def _handle_access_denied(feature_id: str, reason: str):
    """Handle feature access denied response."""
    if request.is_json:
        return jsonify({
            'error': 'Feature access denied',
            'code': 'ACCESS_DENIED',
            'feature_id': feature_id,
            'reason': reason,
            'upgrade_url': url_for('subscription.manage') if 'subscription' in reason else None
        }), 403
    
    if 'subscription' in reason:
        return redirect(url_for('subscription.manage'))
    return jsonify({'error': reason}), 403


def _handle_limit_exceeded(feature_id: str, limit_result: Dict[str, Any]):
    """Handle usage limit exceeded response."""
    if request.is_json:
        return jsonify({
            'error': 'Usage limit exceeded',
            'code': 'LIMIT_EXCEEDED',
            'feature_id': feature_id,
            'message': limit_result.get('message', 'Usage limit reached'),
            'limit': limit_result.get('limit'),
            'current': limit_result.get('current'),
            'remaining': limit_result.get('remaining', 0),
            'upgrade_url': url_for('subscription.manage')
        }), 429
    return redirect(url_for('subscription.manage'))


def _handle_model_denied(model_name: str, feature_id: str = None):
    """Handle model access denied response."""
    available_models = feature_registry_service.get_available_models(feature_id)
    
    if request.is_json:
        return jsonify({
            'error': 'Model access denied',
            'code': 'MODEL_DENIED',
            'requested_model': model_name,
            'available_models': available_models,
            'message': f'Model "{model_name}" requires premium subscription',
            'upgrade_url': url_for('subscription.manage')
        }), 403
    return redirect(url_for('subscription.manage'))


def _handle_tier_required(required_tier: MembershipTier):
    """Handle tier requirement not met response."""
    if request.is_json:
        return jsonify({
            'error': 'Subscription upgrade required',
            'code': 'TIER_REQUIRED',
            'required_tier': required_tier.value,
            'message': f'This feature requires {required_tier.value} subscription',
            'upgrade_url': url_for('subscription.manage')
        }), 403
    return redirect(url_for('subscription.manage'))


# Utility functions for template and service use

def get_user_feature_access(user_id: str = None) -> Dict[str, Any]:
    """Get user's feature access information for templates."""
    return feature_registry_service.get_user_features(user_id)


def is_feature_accessible(feature_id: str, user_id: str = None) -> bool:
    """Quick check if user can access a feature."""
    can_access, _ = feature_registry_service.can_access_feature(feature_id, user_id)
    return can_access


def get_feature_usage_status(feature_id: str, user_id: str = None) -> Dict[str, Any]:
    """Get current usage status for a feature."""
    return feature_registry_service.check_usage_limit(feature_id, user_id)