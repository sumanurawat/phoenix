"""
Subscription Model

Data class for user subscription information with Stripe integration.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Subscription:
    """User subscription data model."""
    
    subscription_tier: str  # "basic", "pro", "free"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    status: str = "inactive"  # "active", "inactive", "canceled", "past_due"
    current_period_end: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    cancel_at_period_end: bool = False
    
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status == "active"
    
    def is_premium(self) -> bool:
        """Check if user has premium access (basic or pro)."""
        return self.subscription_tier in ["basic", "pro"] and self.is_active()
    
    def to_dict(self) -> dict:
        """Convert subscription to dictionary for Firestore storage."""
        return {
            "subscription_tier": self.subscription_tier,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "status": self.status,
            "current_period_end": self.current_period_end,
            "last_updated": self.last_updated or datetime.utcnow(),
            "cancel_at_period_end": self.cancel_at_period_end
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Subscription':
        """Create subscription instance from Firestore document."""
        return cls(
            subscription_tier=data.get("subscription_tier", "free"),
            stripe_customer_id=data.get("stripe_customer_id"),
            stripe_subscription_id=data.get("stripe_subscription_id"),
            status=data.get("status", "inactive"),
            current_period_end=data.get("current_period_end"),
            last_updated=data.get("last_updated"),
            cancel_at_period_end=data.get("cancel_at_period_end", False)
        )


# Subscription tier configurations
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "price": 0,
        "features": [
            "Basic URL shortening",
            "Limited analytics",
            "Community support"
        ],
        "limits": {
            "max_links": 10,
            "analytics_retention_days": 30
        }
    },
    "basic": {
        "name": "Basic",
        "price": 5,
        "price_id": "price_1RcFAyGgo4tk9CEitD4wp0W",  # Your actual Stripe price ID (corrected)
        "features": [
            "Unlimited URL shortening",
            "Enhanced analytics",
            "Email support",
            "Custom aliases"
        ],
        "limits": {
            "max_links": 1000,
            "analytics_retention_days": 90
        }
    },
    "pro": {
        "name": "Pro",
        "price": 20,
        "price_id": "price_1RcFBNGgo4tk9CEiho0eTpaJ",  # Your actual Stripe price ID
        "features": [
            "Unlimited URL shortening",
            "Advanced analytics",
            "Priority support",
            "Custom domains",
            "API access",
            "Bulk operations"
        ],
        "limits": {
            "max_links": -1,  # Unlimited
            "analytics_retention_days": 365
        }
    }
}
