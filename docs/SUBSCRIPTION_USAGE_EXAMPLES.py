"""
Example: Using Subscription Decorators in Existing Routes

This file shows how to add subscription-based access control to existing features.
"""

# Example 1: Protect a deeplink feature with subscription requirement
from utils.subscription_decorators import subscription_required, feature_required, usage_limit_check
from api.auth_routes import login_required
from flask import Blueprint, jsonify

# Example route that requires Basic subscription or higher
@subscription_required("basic")
@login_required
def create_premium_link():
    """Create a link with premium features like custom alias."""
    # Only users with Basic or Pro subscription can access this
    return jsonify({"message": "Premium link created"})


# Example route that requires specific feature access
@feature_required("API access")
@login_required
def api_endpoint():
    """API endpoint only available to Pro subscribers."""
    # Only users with "API access" feature (Pro tier) can access this
    return jsonify({"message": "API data"})


# Example route with usage limits
@usage_limit_check("max_links", increment=1)
@login_required
def create_link():
    """Create a link with usage limit enforcement."""
    # This will check if user has reached their link creation limit
    # based on their subscription tier
    return jsonify({"message": "Link created"})


# Example: Adding subscription check to existing deeplink routes
# You would modify your existing deeplink_routes.py like this:

"""
In api/deeplink_routes.py, you could add:

from utils.subscription_decorators import subscription_required, usage_limit_check

@deeplink_bp.route('/create', methods=['POST'])
@login_required
@usage_limit_check("max_links", increment=1)  # Check link creation limit
def create_short_link():
    # Your existing link creation logic
    pass

@deeplink_bp.route('/analytics/<short_code>')
@login_required
@feature_required("Enhanced analytics")  # Only Basic+ users get enhanced analytics
def get_enhanced_analytics(short_code):
    # Enhanced analytics logic
    pass

@deeplink_bp.route('/api/bulk-create', methods=['POST'])
@login_required
@feature_required("Bulk operations")  # Only Pro users get bulk operations
def bulk_create_links():
    # Bulk creation logic
    pass
"""

# Example: Service-level subscription checks
from services.subscription_service import SubscriptionService

def some_business_logic(user_id: str):
    """Example of checking subscription in business logic."""
    subscription_service = SubscriptionService()
    
    # Check if user has specific feature access
    if subscription_service.has_feature_access(user_id, "Custom domains"):
        # Allow custom domain functionality
        pass
    
    # Get subscription limits
    subscription = subscription_service.get_subscription_status(user_id)
    tier_config = subscription_service.get_tier_config(subscription.subscription_tier)
    max_links = tier_config['limits']['max_links']
    
    if max_links != -1:  # -1 means unlimited
        # Check current usage and enforce limit
        pass
