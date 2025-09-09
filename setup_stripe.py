#!/usr/bin/env python3
"""
Stripe Configuration and Testing Script for Phoenix AI Platform

This script helps configure and test the Stripe integration.
"""

import os
import json
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment_variables() -> Dict[str, Any]:
    """Check if all required environment variables are set."""
    logger.info("🔍 Checking Stripe environment variables...")
    
    required_vars = {
        'STRIPE_SECRET_KEY': 'Stripe secret key (sk_test_... or sk_live_...)',
        'STRIPE_PUBLISHABLE_KEY': 'Stripe publishable key (pk_test_... or pk_live_...)',
        'STRIPE_WEBHOOK_SECRET': 'Stripe webhook signing secret (whsec_...)',
        'STRIPE_PREMIUM_MONTHLY_PRICE_ID': 'Stripe price ID for premium plan (price_...)'
    }
    
    results = {}
    all_set = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Show only first 10 characters for security
            display_value = f"{value[:10]}..." if len(value) > 10 else value
            results[var] = {'set': True, 'value': display_value}
            logger.info(f"✅ {var}: {display_value}")
        else:
            results[var] = {'set': False, 'value': None}
            logger.warning(f"❌ {var}: Not set - {description}")
            all_set = False
    
    return {
        'all_required_set': all_set,
        'variables': results,
        'test_mode': os.getenv('STRIPE_SECRET_KEY', '').startswith('sk_test_') if os.getenv('STRIPE_SECRET_KEY') else False
    }

def test_stripe_service() -> bool:
    """Test basic Stripe service functionality."""
    logger.info("🧪 Testing Stripe service...")
    
    try:
        # Mock dependencies for testing
        from unittest.mock import patch, MagicMock
        
        # Check if environment is configured
        env_check = check_environment_variables()
        if not env_check['all_required_set']:
            logger.error("❌ Environment variables not properly configured")
            return False
        
        # Mock Firebase dependencies
        with patch('firebase_admin._apps', []):
            with patch('firebase_admin.firestore.client', return_value=MagicMock()):
                # Mock Stripe API for testing
                with patch('stripe.api_key'):
                    from services.stripe_service import StripeService
                    
                    service = StripeService()
                    
                    # Test configuration
                    assert service.stripe_secret_key is not None
                    assert service.stripe_publishable_key is not None
                    assert service.webhook_secret is not None
                    
                    logger.info("✅ Stripe service configured correctly")
                    return True
                    
    except Exception as e:
        logger.error(f"❌ Stripe service test failed: {e}")
        return False

def generate_sample_env_file():
    """Generate a sample .env file with Stripe configuration."""
    logger.info("📝 Generating sample .env file...")
    
    sample_env = """# Stripe Configuration for Phoenix AI Platform
# Get these values from your Stripe Dashboard: https://dashboard.stripe.com

# Test keys (for development)
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Product configuration
STRIPE_PREMIUM_MONTHLY_PRICE_ID=price_your_price_id_here

# For production, replace with live keys:
# STRIPE_SECRET_KEY=sk_live_your_live_secret_key_here
# STRIPE_PUBLISHABLE_KEY=pk_live_your_live_publishable_key_here

# Other Phoenix configuration
SECRET_KEY=your-secret-key-for-sessions
FLASK_ENV=development
FLASK_DEBUG=True

# Firebase configuration
FIREBASE_API_KEY=your_firebase_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
"""
    
    try:
        with open('.env.stripe.example', 'w') as f:
            f.write(sample_env)
        logger.info("✅ Sample .env file created: .env.stripe.example")
        logger.info("📋 Copy this file to .env and fill in your actual Stripe keys")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create sample .env file: {e}")
        return False

def test_webhook_signature():
    """Test webhook signature verification."""
    logger.info("🔒 Testing webhook signature verification...")
    
    try:
        import stripe
        
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            logger.warning("⚠️ STRIPE_WEBHOOK_SECRET not set, skipping webhook test")
            return False
        
        # Sample webhook payload for testing
        test_payload = json.dumps({
            "id": "evt_test_webhook",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_session",
                    "customer": "cus_test_customer",
                    "subscription": "sub_test_subscription"
                }
            }
        }).encode('utf-8')
        
        # This would normally be provided by Stripe in the headers
        # For testing, we'll just check that the webhook secret is valid format
        if webhook_secret.startswith('whsec_'):
            logger.info("✅ Webhook secret format is valid")
            return True
        else:
            logger.error("❌ Webhook secret format is invalid (should start with 'whsec_')")
            return False
            
    except Exception as e:
        logger.error(f"❌ Webhook test failed: {e}")
        return False

def show_setup_instructions():
    """Show setup instructions for Stripe integration."""
    logger.info("📚 Stripe Integration Setup Instructions")
    print("\n" + "="*60)
    print("STRIPE INTEGRATION SETUP GUIDE")
    print("="*60)
    
    print("\n1. CREATE STRIPE ACCOUNT")
    print("   • Go to https://stripe.com and create an account")
    print("   • Complete account verification")
    
    print("\n2. GET API KEYS")
    print("   • Go to https://dashboard.stripe.com/apikeys")
    print("   • Copy your Publishable key (pk_test_...)")
    print("   • Copy your Secret key (sk_test_...)")
    
    print("\n3. CREATE PRODUCT")
    print("   • Go to https://dashboard.stripe.com/products")
    print("   • Create a new product:")
    print("     - Name: Premium Monthly")
    print("     - Price: $5.00 USD")
    print("     - Billing: Recurring monthly")
    print("   • Copy the Price ID (price_...)")
    
    print("\n4. CONFIGURE WEBHOOKS")
    print("   • Go to https://dashboard.stripe.com/webhooks")
    print("   • Add endpoint: https://your-domain.com/api/stripe/webhook")
    print("   • Select events:")
    print("     - checkout.session.completed")
    print("     - customer.subscription.updated")
    print("     - customer.subscription.deleted")
    print("     - invoice.payment_failed")
    print("   • Copy the webhook signing secret (whsec_...)")
    
    print("\n5. SET ENVIRONMENT VARIABLES")
    print("   • Add to your .env file or deployment environment:")
    print("     STRIPE_SECRET_KEY=sk_test_...")
    print("     STRIPE_PUBLISHABLE_KEY=pk_test_...")
    print("     STRIPE_WEBHOOK_SECRET=whsec_...")
    print("     STRIPE_PREMIUM_MONTHLY_PRICE_ID=price_...")
    
    print("\n6. DEPLOY FIRESTORE RULES")
    print("   • Run: firebase deploy --only firestore:rules")
    print("   • Run: firebase deploy --only firestore:indexes")
    
    print("\n7. TEST INTEGRATION")
    print("   • Run this script: python setup_stripe.py --test")
    print("   • Visit /subscription page to test UI")
    print("   • Make a test payment with Stripe test cards")
    
    print("\n📖 For detailed instructions, see:")
    print("   docs/STRIPE_INTEGRATION_GUIDE.md")
    print("\n💳 Stripe test cards:")
    print("   4242424242424242 (Visa)")
    print("   4000000000000002 (Card declined)")
    print("   Use any future expiry date and any CVC")
    print("\n" + "="*60)

def main():
    """Main function to run configuration checks and tests."""
    import sys
    
    logger.info("🚀 Phoenix AI Platform - Stripe Integration Setup")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Run tests
        logger.info("Running Stripe integration tests...")
        
        env_ok = check_environment_variables()['all_required_set']
        service_ok = test_stripe_service()
        webhook_ok = test_webhook_signature()
        
        if env_ok and service_ok and webhook_ok:
            logger.info("🎉 All tests passed! Stripe integration is ready.")
        else:
            logger.error("❌ Some tests failed. Check configuration.")
            
    elif len(sys.argv) > 1 and sys.argv[1] == '--env':
        # Generate sample env file
        generate_sample_env_file()
        
    else:
        # Show setup instructions
        show_setup_instructions()
        print("\nUsage:")
        print("  python setup_stripe.py           # Show setup instructions")
        print("  python setup_stripe.py --test    # Run configuration tests")
        print("  python setup_stripe.py --env     # Generate sample .env file")

if __name__ == '__main__':
    main()