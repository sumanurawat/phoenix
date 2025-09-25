"""
Tests for the feature registry system.
"""
import unittest
from unittest.mock import patch, MagicMock

from config.feature_registry import (
    MembershipTier, FeatureDefinition, FeatureCategory, 
    LimitType, UsageLimit, FEATURE_REGISTRY,
    get_feature, get_features_by_category, get_features_for_tier
)
from services.feature_registry_service import FeatureRegistryService


class TestFeatureRegistry(unittest.TestCase):
    """Test feature registry configuration."""
    
    def test_membership_tier_hierarchy(self):
        """Test tier hierarchy comparison."""
        self.assertTrue(MembershipTier.PREMIUM.can_access_tier(MembershipTier.FREE))
        self.assertTrue(MembershipTier.FREE.can_access_tier(MembershipTier.FREE))
        self.assertFalse(MembershipTier.FREE.can_access_tier(MembershipTier.PREMIUM))
    
    def test_usage_limit_unlimited(self):
        """Test unlimited usage limit detection."""
        limited = UsageLimit(LimitType.DAILY, 5)
        unlimited = UsageLimit(LimitType.DAILY, -1)
        
        self.assertFalse(limited.is_unlimited)
        self.assertTrue(unlimited.is_unlimited)
    
    def test_feature_definition_creation(self):
        """Test feature definition creation and properties."""
        feature = FeatureDefinition(
            feature_id='test_feature',
            name='Test Feature',
            description='A test feature',
            category=FeatureCategory.CHAT,
            minimum_tier=MembershipTier.FREE
        )
        
        self.assertEqual(feature.feature_id, 'test_feature')
        self.assertTrue(feature.is_accessible_by_tier(MembershipTier.FREE))
        self.assertTrue(feature.is_accessible_by_tier(MembershipTier.PREMIUM))
    
    def test_feature_registry_completeness(self):
        """Test that feature registry has expected features."""
        expected_features = [
            'chat_basic', 'chat_document_upload', 'chat_enhanced',
            'search_basic', 'video_generation', 'news_search',
            'dataset_search', 'url_shortening'
        ]
        
        for feature_id in expected_features:
            self.assertIn(feature_id, FEATURE_REGISTRY, 
                         f"Feature '{feature_id}' missing from registry")
    
    def test_get_feature(self):
        """Test getting feature by ID."""
        feature = get_feature('chat_basic')
        self.assertIsNotNone(feature)
        self.assertEqual(feature.feature_id, 'chat_basic')
        
        # Test non-existent feature
        self.assertIsNone(get_feature('non_existent'))
    
    def test_get_features_by_category(self):
        """Test getting features by category."""
        chat_features = get_features_by_category(FeatureCategory.CHAT)
        self.assertGreater(len(chat_features), 0)
        
        for feature in chat_features:
            self.assertEqual(feature.category, FeatureCategory.CHAT)
    
    def test_get_features_for_tier(self):
        """Test getting features accessible by tier."""
        free_features = get_features_for_tier(MembershipTier.FREE)
        premium_features = get_features_for_tier(MembershipTier.PREMIUM)
        
        # Premium should have at least as many features as free
        self.assertGreaterEqual(len(premium_features), len(free_features))
        
        # Check specific features
        free_feature_ids = {f.feature_id for f in free_features}
        premium_feature_ids = {f.feature_id for f in premium_features}
        
        self.assertIn('chat_basic', free_feature_ids)
        self.assertIn('video_generation', premium_feature_ids)
        self.assertNotIn('video_generation', free_feature_ids)


class TestFeatureRegistryService(unittest.TestCase):
    """Test feature registry service."""
    
    def setUp(self):
        self.service = FeatureRegistryService()
    
    @patch('services.feature_registry_service.session')
    @patch.object(FeatureRegistryService, 'stripe_service')
    def test_get_user_tier_free(self, mock_stripe, mock_session):
        """Test getting user tier - free user."""
        mock_session.get.return_value = 'test_user'
        mock_stripe.get_subscription_status.return_value = {'is_premium': False}
        
        tier = self.service.get_user_tier()
        self.assertEqual(tier, MembershipTier.FREE)
    
    @patch('services.feature_registry_service.session')
    @patch.object(FeatureRegistryService, 'stripe_service')
    def test_get_user_tier_premium(self, mock_stripe, mock_session):
        """Test getting user tier - premium user."""
        mock_session.get.return_value = 'test_user'
        mock_stripe.get_subscription_status.return_value = {'is_premium': True}
        
        tier = self.service.get_user_tier()
        self.assertEqual(tier, MembershipTier.PREMIUM)
    
    @patch('services.feature_registry_service.session')
    def test_get_user_tier_no_user(self, mock_session):
        """Test getting user tier - no user logged in."""
        mock_session.get.return_value = None
        
        tier = self.service.get_user_tier()
        self.assertEqual(tier, MembershipTier.FREE)
    
    @patch('services.feature_registry_service.session')
    @patch.object(FeatureRegistryService, 'get_user_tier')
    def test_can_access_feature_success(self, mock_get_tier, mock_session):
        """Test successful feature access check."""
        mock_session.get.return_value = 'test_user'
        mock_get_tier.return_value = MembershipTier.FREE
        
        can_access, reason = self.service.can_access_feature('chat_basic')
        self.assertTrue(can_access)
        self.assertEqual(reason, "")
    
    @patch('services.feature_registry_service.session')
    @patch.object(FeatureRegistryService, 'get_user_tier')
    def test_can_access_feature_insufficient_tier(self, mock_get_tier, mock_session):
        """Test feature access denied due to insufficient tier."""
        mock_session.get.return_value = 'test_user'
        mock_get_tier.return_value = MembershipTier.FREE
        
        can_access, reason = self.service.can_access_feature('video_generation')
        self.assertFalse(can_access)
        self.assertIn('premium subscription', reason)
    
    @patch('services.feature_registry_service.session')
    def test_can_access_feature_no_auth(self, mock_session):
        """Test feature access denied due to no authentication."""
        mock_session.get.return_value = None
        
        can_access, reason = self.service.can_access_feature('chat_basic')
        self.assertFalse(can_access)
        self.assertEqual(reason, "Authentication required")
    
    def test_can_access_feature_not_found(self):
        """Test feature access check for non-existent feature."""
        can_access, reason = self.service.can_access_feature('non_existent')
        self.assertFalse(can_access)
        self.assertIn('not found', reason)
    
    @patch('services.feature_registry_service.session')
    @patch.object(FeatureRegistryService, 'get_user_tier')
    def test_get_available_models_free(self, mock_get_tier, mock_session):
        """Test getting available models for free user."""
        mock_session.get.return_value = 'test_user'
        mock_get_tier.return_value = MembershipTier.FREE
        
        models = self.service.get_available_models()
        self.assertIn('gemini-1.0-pro', models)
        self.assertIn('gpt-3.5-turbo', models)
        self.assertNotIn('gpt-4', models)
    
    @patch('services.feature_registry_service.session')
    @patch.object(FeatureRegistryService, 'get_user_tier')
    def test_get_available_models_premium(self, mock_get_tier, mock_session):
        """Test getting available models for premium user."""
        mock_session.get.return_value = 'test_user'
        mock_get_tier.return_value = MembershipTier.PREMIUM
        
        models = self.service.get_available_models()
        self.assertIn('gpt-4', models)
        self.assertIn('claude-3-opus', models)
        self.assertIn('gemini-1.5-pro', models)


if __name__ == '__main__':
    unittest.main()