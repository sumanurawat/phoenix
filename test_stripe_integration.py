"""Tests for Stripe integration."""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_stripe_service_imports():
    """Test that Stripe service can be imported without actual credentials."""
    logger.info("Testing Stripe service imports...")
    
    # Mock environment variables for testing
    with patch.dict(os.environ, {
        'STRIPE_SECRET_KEY': 'sk_test_123',
        'STRIPE_PUBLISHABLE_KEY': 'pk_test_123',
        'STRIPE_WEBHOOK_SECRET': 'whsec_test_123',
        'STRIPE_PREMIUM_MONTHLY_PRICE_ID': 'price_test_123'
    }):
        try:
            # Mock Firebase admin initialization to avoid credentials requirement
            with patch('firebase_admin.initialize_app'), \
                 patch('firebase_admin._apps', []):
                
                # Mock Firestore client
                with patch('firebase_admin.firestore.client') as mock_firestore:
                    mock_db = MagicMock()
                    mock_firestore.return_value = mock_db
                    
                    # Mock Stripe API
                    with patch('stripe.api_key'), \
                         patch('stripe.Customer'), \
                         patch('stripe.checkout.Session'), \
                         patch('stripe.Subscription'), \
                         patch('stripe.Webhook'):
                        
                        from services.stripe_service import StripeService
                        
                        # Test service initialization
                        service = StripeService()
                        assert service is not None
                        assert service.stripe_secret_key == 'sk_test_123'
                        assert service.stripe_publishable_key == 'pk_test_123'
                        assert service.webhook_secret == 'whsec_test_123'
                        
                        logger.info("✅ Stripe service imported successfully")
                        return True
                        
        except Exception as e:
            logger.error(f"❌ Error importing Stripe service: {e}")
            return False

def test_subscription_middleware_imports():
    """Test that subscription middleware can be imported."""
    logger.info("Testing subscription middleware imports...")
    
    try:
        # Mock environment variables and Stripe service
        with patch.dict(os.environ, {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_PUBLISHABLE_KEY': 'pk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_test_123'
        }):
            # Mock Firebase and Stripe dependencies
            with patch('firebase_admin.initialize_app'), \
                 patch('firebase_admin._apps', []), \
                 patch('firebase_admin.firestore.client'), \
                 patch('stripe.api_key'):
                
                from services.subscription_middleware import (
                    premium_required, 
                    get_user_subscription_context,
                    check_feature_limit
                )
                
                assert premium_required is not None
                assert get_user_subscription_context is not None
                assert check_feature_limit is not None
                
                logger.info("✅ Subscription middleware imported successfully")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error importing subscription middleware: {e}")
        return False

def test_stripe_routes_imports():
    """Test that Stripe routes can be imported."""
    logger.info("Testing Stripe routes imports...")
    
    try:
        # Mock environment variables and dependencies
        with patch.dict(os.environ, {
            'STRIPE_SECRET_KEY': 'sk_test_123',
            'STRIPE_PUBLISHABLE_KEY': 'pk_test_123',
            'STRIPE_WEBHOOK_SECRET': 'whsec_test_123'
        }):
            # Mock Flask and dependencies
            with patch('firebase_admin.initialize_app'), \
                 patch('firebase_admin._apps', []), \
                 patch('firebase_admin.firestore.client'), \
                 patch('stripe.api_key'):
                
                from api.stripe_routes import stripe_bp
                
                assert stripe_bp is not None
                assert stripe_bp.name == 'stripe'
                
                logger.info("✅ Stripe routes imported successfully")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error importing Stripe routes: {e}")
        return False

def test_feature_limits():
    """Test feature limit checking logic."""
    logger.info("Testing feature limit logic...")
    
    try:
        # Mock environment to simulate no Stripe configuration
        with patch.dict(os.environ, {}, clear=True):
            # Mock Flask session
            with patch('services.subscription_middleware.session', {'user_id': 'test_user'}):
                from services.subscription_middleware import check_feature_limit
                
                # Test free user limits
                result = check_feature_limit('chat_messages', 3, 5)
                assert result['allowed'] == True
                assert result['is_premium'] == False
                assert result['usage'] == 3
                assert result['limit'] == 5
                assert result['remaining'] == 2
                
                # Test hitting limit
                result = check_feature_limit('chat_messages', 5, 5)
                assert result['allowed'] == False
                assert result['remaining'] == 0
                
                logger.info("✅ Feature limit logic working correctly")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error testing feature limits: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🧪 Running Stripe integration tests...")
    
    tests = [
        test_stripe_service_imports,
        test_subscription_middleware_imports,
        test_stripe_routes_imports,
        test_feature_limits
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All Stripe integration tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed. Check implementation.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)