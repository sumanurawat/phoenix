#!/usr/bin/env python3
"""
Phoenix AI - Stripe Integration Setup Script

This script helps you configure and test the Stripe integration for Phoenix AI.
Run with different flags for different operations:

python setup_stripe.py           # Show setup instructions
python setup_stripe.py --test    # Test current configuration  
python setup_stripe.py --env     # Generate sample .env file
"""

import os
import sys
import argparse
from pathlib import Path

def show_setup_instructions():
    """Display comprehensive setup instructions."""
    print("🚀 Phoenix AI - Stripe Integration Setup")
    print("=" * 50)
    print()
    
    print("📋 QUICK SETUP CHECKLIST:")
    print()
    print("1. Stripe Account Setup:")
    print("   • Sign up at https://stripe.com")
    print("   • Create a Product: 'Premium Monthly' at $5.00 USD")
    print("   • Copy the Price ID (starts with 'price_')")
    print()
    
    print("2. Environment Configuration:")
    print("   • Copy .env.stripe to .env")
    print("   • Fill in your Stripe API keys")
    print("   • Set your Price ID")
    print()
    
    print("3. Webhook Setup:")
    print("   • In Stripe Dashboard > Webhooks")
    print("   • Add endpoint: https://your-domain.com/api/stripe/webhook")
    print("   • Select events:")
    print("     - checkout.session.completed")
    print("     - customer.subscription.updated") 
    print("     - customer.subscription.deleted")
    print("     - invoice.payment_failed")
    print("   • Copy webhook signing secret")
    print()
    
    print("4. Deploy Firestore Changes:")
    print("   firebase deploy --only firestore:rules")
    print("   firebase deploy --only firestore:indexes")
    print()
    
    print("5. Install Dependencies:")
    print("   pip install -r requirements.txt")
    print()
    
    print("🧪 TEST YOUR SETUP:")
    print("   python setup_stripe.py --test")
    print()
    
    print("📚 DOCUMENTATION:")
    print("   See docs/STRIPE_INTEGRATION_GUIDE.md for complete guide")
    print()

def test_configuration():
    """Test the current Stripe configuration."""
    print("🧪 Testing Stripe Configuration...")
    print("=" * 40)
    print()
    
    # Check environment variables
    required_vars = [
        'STRIPE_SECRET_KEY',
        'STRIPE_PUBLISHABLE_KEY', 
        'STRIPE_WEBHOOK_SECRET',
        'STRIPE_PREMIUM_MONTHLY_PRICE_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var:
                masked = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    print()
    
    if missing_vars:
        print("❌ Configuration incomplete!")
        print(f"Missing variables: {', '.join(missing_vars)}")
        print()
        print("💡 Next steps:")
        print("1. Copy .env.stripe to .env")
        print("2. Fill in the missing values")
        print("3. Run this test again")
        return False
    
    # Test Stripe connection
    print("🔗 Testing Stripe API connection...")
    
    try:
        import stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        # Test API connection by listing products
        products = stripe.Product.list(limit=1)
        print("✅ Stripe API connection successful")
        
        # Test price ID
        price_id = os.getenv('STRIPE_PREMIUM_MONTHLY_PRICE_ID')
        try:
            price = stripe.Price.retrieve(price_id)
            print(f"✅ Price ID valid: {price.nickname or price.id} - ${price.unit_amount/100:.2f}")
        except stripe.error.InvalidRequestError:
            print(f"❌ Invalid Price ID: {price_id}")
            return False
            
    except ImportError:
        print("❌ Stripe library not installed")
        print("Run: pip install -r requirements.txt")
        return False
    except stripe.error.AuthenticationError:
        print("❌ Invalid Stripe API key")
        return False
    except Exception as e:
        print(f"❌ Stripe API error: {e}")
        return False
    
    # Test Firebase connection
    print()
    print("🔥 Testing Firebase connection...")
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Initialize Firebase if not already done
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate('firebase-credentials.json')
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized with service account")
            except FileNotFoundError:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized with default credentials")
        
        # Test Firestore connection
        db = firestore.client()
        
        # Test write permissions (create a test doc)
        test_ref = db.collection('_stripe_test').document('test')
        test_ref.set({'test': True})
        test_ref.delete()
        
        print("✅ Firestore connection and permissions OK")
        
    except Exception as e:
        print(f"❌ Firebase error: {e}")
        return False
    
    print()
    print("🎉 All tests passed! Your Stripe integration is ready.")
    print()
    print("🚀 Next steps:")
    print("1. Start your Flask application")
    print("2. Visit /subscription to test the UI")
    print("3. Use Stripe test cards for testing payments")
    print("   • 4242 4242 4242 4242 (Visa)")
    print("   • 4000 0000 0000 0002 (Declined)")
    print()
    
    return True

def generate_env_file():
    """Generate a sample .env file from the template."""
    print("📄 Generating .env file from template...")
    print()
    
    source_file = Path('.env.stripe')
    target_file = Path('.env')
    
    if not source_file.exists():
        print("❌ Template file .env.stripe not found!")
        return False
    
    if target_file.exists():
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return False
    
    # Copy template to .env
    content = source_file.read_text()
    target_file.write_text(content)
    
    print(f"✅ Created {target_file}")
    print()
    print("📝 Next steps:")
    print("1. Edit .env and fill in your actual values")
    print("2. Get your Stripe keys from https://dashboard.stripe.com/apikeys")
    print("3. Create a product and copy the Price ID")
    print("4. Set up webhooks and copy the signing secret")
    print("5. Run: python setup_stripe.py --test")
    print()
    
    return True

def main():
    """Main script entry point."""
    parser = argparse.ArgumentParser(
        description="Phoenix AI Stripe Integration Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--test', 
        action='store_true',
        help='Test current Stripe configuration'
    )
    
    parser.add_argument(
        '--env',
        action='store_true', 
        help='Generate sample .env file from template'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # Load environment variables from .env file if it exists
        env_file = Path('.env')
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv()
        
        success = test_configuration()
        sys.exit(0 if success else 1)
    
    elif args.env:
        success = generate_env_file() 
        sys.exit(0 if success else 1)
    
    else:
        show_setup_instructions()

if __name__ == '__main__':
    main()