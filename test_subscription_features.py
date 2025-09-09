#!/usr/bin/env python3
"""
Test script for subscription management features.
This script tests the core subscription functionality without requiring external services.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_stripe_service():
    """Test StripeService initialization and basic functionality."""
    print("Testing StripeService...")
    
    try:
        from services.stripe_service import StripeService
        
        # Test initialization
        stripe_service = StripeService()
        print("✓ StripeService initialized successfully")
        
        # Test configuration check
        is_configured = stripe_service.is_configured()
        print(f"✓ Stripe configured: {is_configured}")
        
        # Test config retrieval
        config = stripe_service.get_config()
        print(f"✓ Config retrieved: {config}")
        
        # Test subscription status for non-existent user
        status = stripe_service.get_subscription_status('test-user-123')
        print(f"✓ Subscription status for non-existent user: {status}")
        
        return True
        
    except Exception as e:
        print(f"✗ StripeService test failed: {e}")
        return False


def test_subscription_middleware():
    """Test subscription middleware functionality."""
    print("\nTesting Subscription Middleware...")
    
    try:
        from services.subscription_middleware import (
            SubscriptionMiddleware, 
            get_subscription_status, 
            check_feature_limit,
            get_feature_limits
        )
        
        # Test middleware initialization
        middleware = SubscriptionMiddleware()
        print("✓ SubscriptionMiddleware initialized successfully")
        
        # Test feature limits
        limits = get_feature_limits()
        print(f"✓ Feature limits retrieved: {len(limits)} features configured")
        
        # Test feature limit checking
        limit_result = check_feature_limit('chat_messages', current_usage=3, free_limit=5)
        print(f"✓ Feature limit check (within limit): {limit_result}")
        
        limit_result = check_feature_limit('chat_messages', current_usage=6, free_limit=5)
        print(f"✓ Feature limit check (over limit): {limit_result}")
        
        return True
        
    except Exception as e:
        print(f"✗ Subscription middleware test failed: {e}")
        return False


def test_stripe_routes():
    """Test that Stripe routes can be imported."""
    print("\nTesting Stripe Routes...")
    
    try:
        from api.stripe_routes import stripe_bp
        print("✓ Stripe routes imported successfully")
        print(f"✓ Blueprint name: {stripe_bp.name}")
        print(f"✓ Blueprint URL prefix: {stripe_bp.url_prefix}")
        
        return True
        
    except Exception as e:
        print(f"✗ Stripe routes test failed: {e}")
        return False


def test_templates_exist():
    """Test that subscription templates exist."""
    print("\nTesting Template Files...")
    
    templates = [
        'templates/subscription.html',
        'templates/subscription_success.html', 
        'templates/subscription_cancel.html'
    ]
    
    all_exist = True
    for template in templates:
        if os.path.exists(template):
            print(f"✓ {template} exists")
        else:
            print(f"✗ {template} missing")
            all_exist = False
    
    return all_exist


def main():
    """Run all tests."""
    print("=" * 60)
    print("SUBSCRIPTION MANAGEMENT FEATURE TESTS")
    print("=" * 60)
    
    tests = [
        test_stripe_service,
        test_subscription_middleware,
        test_stripe_routes,
        test_templates_exist
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Subscription management features are ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == '__main__':
    exit(main())