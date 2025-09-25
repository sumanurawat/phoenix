"""
Feature Registry Service - Business logic for feature access and validation.

This service provides methods to check feature access, validate usage limits,
and manage feature availability based on user subscriptions.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from flask import session, g

from config.feature_registry import (
    FEATURE_REGISTRY, MembershipTier, FeatureDefinition, UsageLimit, LimitType,
    get_feature, get_features_by_category, get_features_for_tier
)
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)


class FeatureRegistryService:
    """Service for feature access control and validation."""
    
    def __init__(self):
        self.stripe_service = StripeService()
    
    def get_user_tier(self, user_id: str = None) -> MembershipTier:
        """Get user's membership tier."""
        if user_id is None:
            user_id = session.get('user_id')
        
        if not user_id:
            return MembershipTier.FREE
        
        # Get subscription status from Stripe service
        subscription_status = self.stripe_service.get_subscription_status(user_id)
        is_premium = subscription_status.get('is_premium', False)
        
        return MembershipTier.PREMIUM if is_premium else MembershipTier.FREE
    
    def can_access_feature(self, feature_id: str, user_id: str = None) -> Tuple[bool, str]:
        """
        Check if user can access a feature.
        
        Returns:
            Tuple of (can_access, reason_if_not)
        """
        feature = get_feature(feature_id)
        if not feature:
            return False, f"Feature '{feature_id}' not found"
        
        if not feature.is_active:
            return False, f"Feature '{feature_id}' is currently disabled"
        
        if not feature.requires_auth:
            return True, ""
        
        if user_id is None:
            user_id = session.get('user_id')
        
        if not user_id:
            return False, "Authentication required"
        
        user_tier = self.get_user_tier(user_id)
        
        if not feature.is_accessible_by_tier(user_tier):
            required_tier = feature.minimum_tier.value
            return False, f"This feature requires {required_tier} subscription"
        
        # Check dependencies
        for dep_id in feature.dependencies:
            can_access_dep, reason = self.can_access_feature(dep_id, user_id)
            if not can_access_dep:
                return False, f"Required feature '{dep_id}' is not available: {reason}"
        
        return True, ""
    
    def check_usage_limit(self, feature_id: str, user_id: str = None) -> Dict[str, Any]:
        """
        Check current usage against limits for a feature.
        
        Returns:
            Dictionary with limit check results
        """
        feature = get_feature(feature_id)
        if not feature:
            return {
                'allowed': False,
                'error': f"Feature '{feature_id}' not found"
            }
        
        if user_id is None:
            user_id = session.get('user_id')
        
        if not user_id:
            return {
                'allowed': False,
                'error': 'Authentication required'
            }
        
        user_tier = self.get_user_tier(user_id)
        limits = feature.get_limits_for_tier(user_tier)
        
        # If no limits defined, allow access
        if not limits:
            return {
                'allowed': True,
                'unlimited': True
            }
        
        # Check each limit type
        for limit in limits:
            if limit.is_unlimited:
                continue
                
            current_usage = self._get_current_usage(user_id, feature_id, limit.limit_type)
            
            if current_usage >= limit.value:
                return {
                    'allowed': False,
                    'limit_type': limit.limit_type.value,
                    'limit': limit.value,
                    'current': current_usage,
                    'remaining': 0,
                    'message': self._get_limit_message(feature, limit, current_usage)
                }
        
        # All limits passed
        current_usage = self._get_current_usage(user_id, feature_id, LimitType.DAILY)
        daily_limit = self._get_daily_limit(feature, user_tier)
        
        return {
            'allowed': True,
            'limit': daily_limit,
            'current': current_usage,
            'remaining': max(0, daily_limit - current_usage) if daily_limit > 0 else -1
        }
    
    def increment_usage(self, feature_id: str, amount: int = 1, user_id: str = None) -> bool:
        """Increment usage counter for a feature."""
        if user_id is None:
            user_id = session.get('user_id')
        
        if not user_id:
            return False
        
        return self.stripe_service.increment_usage(user_id, feature_id, amount)
    
    def get_available_models(self, feature_id: str = None, user_id: str = None) -> List[str]:
        """Get list of AI models available to user for a feature."""
        if user_id is None:
            user_id = session.get('user_id')
        
        user_tier = self.get_user_tier(user_id)
        
        if feature_id:
            feature = get_feature(feature_id)
            if feature:
                models = feature.get_models_for_tier(user_tier)
                if isinstance(models, list):
                    return models
                elif models == 'all':
                    # Return all premium models
                    from config.feature_registry import AVAILABLE_MODELS
                    return AVAILABLE_MODELS['premium']
        
        # Default model list based on tier
        from config.feature_registry import AVAILABLE_MODELS
        return AVAILABLE_MODELS.get(user_tier.value, AVAILABLE_MODELS['free'])
    
    def is_model_allowed(self, model_name: str, feature_id: str = None, user_id: str = None) -> bool:
        """Check if user can access a specific AI model."""
        available_models = self.get_available_models(feature_id, user_id)
        return model_name in available_models
    
    def get_user_features(self, user_id: str = None) -> Dict[str, Any]:
        """Get comprehensive feature access info for user."""
        if user_id is None:
            user_id = session.get('user_id')
        
        user_tier = self.get_user_tier(user_id)
        accessible_features = get_features_for_tier(user_tier)
        
        result = {
            'tier': user_tier.value,
            'features': {},
            'models': self.get_available_models(user_id=user_id)
        }
        
        for feature in accessible_features:
            if not feature.is_active:
                continue
                
            can_access, reason = self.can_access_feature(feature.feature_id, user_id)
            if can_access:
                limit_info = self.check_usage_limit(feature.feature_id, user_id)
                result['features'][feature.feature_id] = {
                    'name': feature.name,
                    'description': feature.description,
                    'category': feature.category.value,
                    'accessible': True,
                    'is_beta': feature.is_beta,
                    'limits': limit_info
                }
            else:
                result['features'][feature.feature_id] = {
                    'name': feature.name,
                    'description': feature.description,
                    'category': feature.category.value,
                    'accessible': False,
                    'reason': reason
                }
        
        return result
    
    def get_upgrade_suggestions(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get features that would be unlocked by upgrading."""
        if user_id is None:
            user_id = session.get('user_id')
        
        user_tier = self.get_user_tier(user_id)
        
        if user_tier == MembershipTier.PREMIUM:
            return []  # Already at highest tier
        
        premium_features = get_features_for_tier(MembershipTier.PREMIUM)
        current_features = get_features_for_tier(user_tier)
        current_feature_ids = {f.feature_id for f in current_features}
        
        upgrade_features = []
        for feature in premium_features:
            if feature.feature_id not in current_feature_ids and feature.is_active:
                upgrade_features.append({
                    'feature_id': feature.feature_id,
                    'name': feature.name,
                    'description': feature.description,
                    'category': feature.category.value
                })
        
        return upgrade_features
    
    def _get_current_usage(self, user_id: str, feature_id: str, limit_type: LimitType) -> int:
        """Get current usage count for a feature and limit type."""
        if limit_type == LimitType.DAILY:
            usage_stats = self.stripe_service.get_usage_stats(user_id)
            return usage_stats.get(feature_id, 0)
        
        # TODO: Implement monthly, concurrent, total limits
        return 0
    
    def _get_daily_limit(self, feature: FeatureDefinition, tier: MembershipTier) -> int:
        """Get daily limit for a feature and tier."""
        limits = feature.get_limits_for_tier(tier)
        for limit in limits:
            if limit.limit_type == LimitType.DAILY:
                return limit.value
        return -1  # Unlimited
    
    def _get_limit_message(self, feature: FeatureDefinition, limit: UsageLimit, current: int) -> str:
        """Generate user-friendly limit exceeded message."""
        feature_name = feature.name.lower()
        limit_type = limit.limit_type.value
        
        if limit_type == 'daily':
            return f"You've reached your daily limit of {limit.value} {feature_name}. Upgrade to Premium for unlimited access."
        elif limit_type == 'monthly':
            return f"You've reached your monthly limit of {limit.value} {feature_name}. Upgrade for higher limits."
        else:
            return f"You've reached the {limit_type} limit for {feature_name}. Consider upgrading your plan."


# Global service instance
feature_registry_service = FeatureRegistryService()