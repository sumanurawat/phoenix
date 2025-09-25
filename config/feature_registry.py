"""
Feature Registry - Centralized feature definitions and policies.

This module defines all features, their access requirements, usage limits,
and tier-based restrictions in a single, authoritative location.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union, Any


class MembershipTier(Enum):
    """User membership tiers in hierarchical order."""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"  # Future expansion
    
    @classmethod
    def get_hierarchy_level(cls, tier: 'MembershipTier') -> int:
        """Get numeric level for tier comparison."""
        hierarchy = {
            cls.FREE: 0,
            cls.PREMIUM: 1,
            cls.ENTERPRISE: 2
        }
        return hierarchy.get(tier, 0)
    
    def can_access_tier(self, required_tier: 'MembershipTier') -> bool:
        """Check if current tier can access features of required tier."""
        return self.get_hierarchy_level(self) >= self.get_hierarchy_level(required_tier)


class FeatureCategory(Enum):
    """Feature categories for organization and reporting."""
    CHAT = "chat"
    SEARCH = "search"
    VIDEO = "video"
    NEWS = "news"
    DATASET = "dataset"
    ANALYTICS = "analytics"
    CORE = "core"


class LimitType(Enum):
    """Types of usage limits."""
    DAILY = "daily"
    MONTHLY = "monthly"
    CONCURRENT = "concurrent"
    TOTAL = "total"


@dataclass
class UsageLimit:
    """Usage limit definition for a feature."""
    limit_type: LimitType
    value: int  # -1 means unlimited
    reset_schedule: Optional[str] = None  # Cron expression for custom resets
    
    @property
    def is_unlimited(self) -> bool:
        return self.value == -1


@dataclass
class FeatureDefinition:
    """Complete feature definition with access rules and limits."""
    
    # Basic feature info
    feature_id: str
    name: str
    description: str
    category: FeatureCategory
    
    # Access control
    minimum_tier: MembershipTier
    requires_auth: bool = True
    
    # Usage limits by tier
    tier_limits: Dict[MembershipTier, List[UsageLimit]] = None
    
    # Model/resource restrictions
    allowed_models: Dict[MembershipTier, Union[List[str], str]] = None
    
    # Dependencies (other features that must be available)
    dependencies: List[str] = None
    
    # Feature flags
    is_active: bool = True
    is_beta: bool = False
    
    def __post_init__(self):
        if self.tier_limits is None:
            self.tier_limits = {}
        if self.allowed_models is None:
            self.allowed_models = {}
        if self.dependencies is None:
            self.dependencies = []
    
    def get_limits_for_tier(self, tier: MembershipTier) -> List[UsageLimit]:
        """Get usage limits for a specific tier."""
        return self.tier_limits.get(tier, [])
    
    def get_models_for_tier(self, tier: MembershipTier) -> Union[List[str], str]:
        """Get allowed models for a specific tier."""
        return self.allowed_models.get(tier, [])
    
    def is_accessible_by_tier(self, tier: MembershipTier) -> bool:
        """Check if tier can access this feature."""
        return tier.can_access_tier(self.minimum_tier)


# Global model definitions
AVAILABLE_MODELS = {
    'free': [
        'gemini-1.0-pro',
        'gpt-3.5-turbo'
    ],
    'premium': [
        'gemini-1.0-pro',
        'gpt-3.5-turbo',
        'gpt-4o-mini',
        'gpt-4',
        'claude-3-opus',
        'claude-3-sonnet', 
        'claude-3-haiku',
        'gemini-1.5-pro',
        'gemini-1.5-flash',
        'grok-beta'
    ]
}

# Feature Registry - The single source of truth for all features
FEATURE_REGISTRY: Dict[str, FeatureDefinition] = {
    
    # Chat & Conversation Features
    'chat_basic': FeatureDefinition(
        feature_id='chat_basic',
        name='Basic Chat',
        description='Basic chat messaging functionality',
        category=FeatureCategory.CHAT,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 5)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        },
        allowed_models={
            MembershipTier.FREE: AVAILABLE_MODELS['free'],
            MembershipTier.PREMIUM: AVAILABLE_MODELS['premium']
        }
    ),
    
    'chat_document_upload': FeatureDefinition(
        feature_id='chat_document_upload',
        name='Document Upload',
        description='Upload documents for chat context',
        category=FeatureCategory.CHAT,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 2)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        },
        dependencies=['chat_basic']
    ),
    
    'chat_enhanced': FeatureDefinition(
        feature_id='chat_enhanced',
        name='Enhanced Chat',
        description='Advanced chat with conversation management',
        category=FeatureCategory.CHAT,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 3)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        },
        dependencies=['chat_basic']
    ),
    
    'chat_premium_models': FeatureDefinition(
        feature_id='chat_premium_models',
        name='Premium AI Models',
        description='Access to GPT-4, Claude, and other premium models',
        category=FeatureCategory.CHAT,
        minimum_tier=MembershipTier.PREMIUM,
        allowed_models={
            MembershipTier.PREMIUM: ['gpt-4', 'gpt-4o-mini', 'claude-3-opus', 'claude-3-sonnet']
        }
    ),
    
    # Search Features
    'search_basic': FeatureDefinition(
        feature_id='search_basic',
        name='Basic Search',
        description='Web and news search functionality',
        category=FeatureCategory.SEARCH,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 10)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        }
    ),
    
    'search_ai_summary': FeatureDefinition(
        feature_id='search_ai_summary',
        name='AI Search Summaries',
        description='AI-powered search result summaries',
        category=FeatureCategory.SEARCH,
        minimum_tier=MembershipTier.PREMIUM,
        dependencies=['search_basic']
    ),
    
    # Video Generation Features
    'video_generation': FeatureDefinition(
        feature_id='video_generation',
        name='Video Generation',
        description='AI-powered video generation from prompts',
        category=FeatureCategory.VIDEO,
        minimum_tier=MembershipTier.PREMIUM,
        tier_limits={
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, 10)]
        }
    ),
    
    # News Features
    'news_search': FeatureDefinition(
        feature_id='news_search',
        name='News Search',
        description='Search news articles',
        category=FeatureCategory.NEWS,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 5)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        }
    ),
    
    'news_content_extraction': FeatureDefinition(
        feature_id='news_content_extraction',
        name='Article Content Extraction',
        description='Extract full content from news articles',
        category=FeatureCategory.NEWS,
        minimum_tier=MembershipTier.PREMIUM,
        dependencies=['news_search']
    ),
    
    'news_ai_summary': FeatureDefinition(
        feature_id='news_ai_summary',
        name='News AI Summaries',
        description='AI-powered news article summarization',
        category=FeatureCategory.NEWS,
        minimum_tier=MembershipTier.PREMIUM,
        dependencies=['news_content_extraction']
    ),
    
    # Dataset Features
    'dataset_search': FeatureDefinition(
        feature_id='dataset_search',
        name='Dataset Search',
        description='Search Kaggle datasets',
        category=FeatureCategory.DATASET,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 5)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        }
    ),
    
    'dataset_download': FeatureDefinition(
        feature_id='dataset_download',
        name='Dataset Download',
        description='Download datasets for analysis',
        category=FeatureCategory.DATASET,
        minimum_tier=MembershipTier.PREMIUM,
        dependencies=['dataset_search']
    ),
    
    'dataset_analysis': FeatureDefinition(
        feature_id='dataset_analysis',
        name='Dataset Analysis',
        description='AI-powered dataset analysis',
        category=FeatureCategory.DATASET,
        minimum_tier=MembershipTier.PREMIUM,
        tier_limits={
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, 5)]
        },
        dependencies=['dataset_download']
    ),
    
    # Analytics Features
    'url_shortening': FeatureDefinition(
        feature_id='url_shortening',
        name='URL Shortening',
        description='Create shortened URLs',
        category=FeatureCategory.ANALYTICS,
        minimum_tier=MembershipTier.FREE,
        tier_limits={
            MembershipTier.FREE: [UsageLimit(LimitType.DAILY, 10)],
            MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, -1)]
        }
    ),
    
    'url_analytics': FeatureDefinition(
        feature_id='url_analytics',
        name='URL Analytics',
        description='View link click analytics',
        category=FeatureCategory.ANALYTICS,
        minimum_tier=MembershipTier.PREMIUM,
        dependencies=['url_shortening']
    )
}


def get_feature(feature_id: str) -> Optional[FeatureDefinition]:
    """Get feature definition by ID."""
    return FEATURE_REGISTRY.get(feature_id)


def get_features_by_category(category: FeatureCategory) -> List[FeatureDefinition]:
    """Get all features in a category."""
    return [f for f in FEATURE_REGISTRY.values() if f.category == category]


def get_features_for_tier(tier: MembershipTier) -> List[FeatureDefinition]:
    """Get all features accessible by a tier."""
    return [f for f in FEATURE_REGISTRY.values() if f.is_accessible_by_tier(tier)]


def validate_registry() -> Dict[str, List[str]]:
    """Validate the feature registry for consistency."""
    errors = {
        'missing_dependencies': [],
        'circular_dependencies': [],
        'invalid_models': []
    }
    
    # Check dependencies exist
    for feature in FEATURE_REGISTRY.values():
        for dep in feature.dependencies:
            if dep not in FEATURE_REGISTRY:
                errors['missing_dependencies'].append(f"{feature.feature_id} -> {dep}")
    
    # TODO: Add circular dependency detection
    # TODO: Add model validation
    
    return errors