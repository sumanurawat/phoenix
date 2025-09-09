"""Test Flask app startup with Stripe integration."""
import os
import logging
from unittest.mock import patch, MagicMock
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_app_startup():
    """Test that the Flask app starts with Stripe integration."""
    logger.info("🧪 Testing Flask app startup with Stripe integration...")
    
    # Create a temporary directory for sessions
    temp_dir = tempfile.mkdtemp()
    
    # Mock environment variables for testing
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key-for-testing',
        'FLASK_ENV': 'development',
        'FLASK_DEBUG': 'False',
        'SESSION_FILE_DIR': temp_dir,
        'STRIPE_SECRET_KEY': 'sk_test_123456789',
        'STRIPE_PUBLISHABLE_KEY': 'pk_test_123456789',
        'STRIPE_WEBHOOK_SECRET': 'whsec_test_123456789',
        'STRIPE_PREMIUM_MONTHLY_PRICE_ID': 'price_test_123456789'
    }):
        # Mock Firebase admin initialization
        with patch('firebase_admin._apps', []):
            with patch('firebase_admin.initialize_app'):
                with patch('firebase_admin.credentials.Certificate'):
                    # Mock Firestore client
                    with patch('firebase_admin.firestore.client', return_value=MagicMock()):
                        # Mock Stripe API
                        with patch('stripe.api_key'):
                            try:
                                # Import and create the app
                                from app import create_app
                                
                                app = create_app()
                                
                                # Test that the app was created successfully
                                assert app is not None
                                logger.info("✅ Flask app created successfully")
                                
                                # Test that Stripe blueprint is registered
                                blueprint_names = [bp.name for bp in app.blueprints.values()]
                                assert 'stripe' in blueprint_names
                                logger.info("✅ Stripe blueprint registered")
                                
                                # Test that the app has the correct configuration
                                assert app.config['SECRET_KEY'] == 'test-secret-key-for-testing'
                                logger.info("✅ App configuration working")
                                
                                # Test basic routes exist
                                with app.test_client() as client:
                                    # Test index route
                                    response = client.get('/')
                                    assert response.status_code in [200, 302]  # 302 if redirecting to login
                                    logger.info("✅ Index route working")
                                    
                                    # Test Stripe config route (should require auth)
                                    response = client.get('/api/stripe/config')
                                    assert response.status_code in [401, 302]  # Should require login
                                    logger.info("✅ Stripe config route protected")
                                
                                return True
                                
                            except Exception as e:
                                logger.error(f"Error creating app: {e}")
                                import traceback
                                traceback.print_exc()
                                return False

def test_subscription_context():
    """Test subscription context injection."""
    logger.info("🧪 Testing subscription context injection...")
    
    temp_dir = tempfile.mkdtemp()
    
    with patch.dict(os.environ, {
        'SECRET_KEY': 'test-secret-key-for-testing',
        'FLASK_ENV': 'development',
        'SESSION_FILE_DIR': temp_dir,
        'STRIPE_SECRET_KEY': 'sk_test_123456789',
        'STRIPE_PUBLISHABLE_KEY': 'pk_test_123456789'
    }):
        with patch('firebase_admin._apps', []):
            with patch('firebase_admin.initialize_app'):
                with patch('firebase_admin.credentials.Certificate'):
                    with patch('firebase_admin.firestore.client', return_value=MagicMock()):
                        with patch('stripe.api_key'):
                            try:
                                from app import create_app
                                
                                app = create_app()
                                
                                # Test context processor
                                with app.app_context():
                                    # Mock session without user
                                    with patch('app.session', {}):
                                        from app import inject_subscription_context
                                        context = inject_subscription_context()
                                        
                                        assert 'subscription' in context
                                        assert context['subscription']['is_premium'] == False
                                        logger.info("✅ Subscription context injection working")
                                
                                return True
                                
                            except Exception as e:
                                logger.error(f"Error testing context: {e}")
                                import traceback
                                traceback.print_exc()
                                return False

def main():
    """Run app startup tests."""
    logger.info("🚀 Running Flask app startup tests...")
    
    tests = [
        test_app_startup,
        test_subscription_context
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 Flask app startup tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed.")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)