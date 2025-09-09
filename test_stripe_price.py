#!/usr/bin/env python3
"""Test script to verify Stripe price configuration."""

import os
import stripe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Stripe configuration
stripe_key = os.getenv('STRIPE_SECRET_KEY')
price_id = os.getenv('STRIPE_PRICE_ID') or os.getenv('STRIPE_PRO_PRICE_ID')

print("=" * 50)
print("Testing Stripe Price Configuration")
print("=" * 50)
print(f"Using Stripe Key: {stripe_key[:8]}...{stripe_key[-4:]}" if stripe_key else "Not set")
print(f"Using Price ID: {price_id}")
print()

if not stripe_key:
    print("❌ No Stripe secret key found!")
    exit(1)

if not price_id:
    print("❌ No price ID found!")
    exit(1)

# Initialize Stripe
stripe.api_key = stripe_key

try:
    # Retrieve the price
    price = stripe.Price.retrieve(price_id)
    
    print("✅ Price found!")
    print(f"   ID: {price.id}")
    print(f"   Product: {price.product}")
    print(f"   Amount: ${price.unit_amount/100:.2f} {price.currency.upper()}")
    print(f"   Recurring: {price.recurring.interval if price.recurring else 'One-time'}")
    print(f"   Active: {price.active}")
    
    # Get product details
    if price.product:
        try:
            product = stripe.Product.retrieve(price.product)
            print(f"\n📦 Product Details:")
            print(f"   Name: {product.name}")
            print(f"   Description: {product.description or 'N/A'}")
            print(f"   Active: {product.active}")
        except Exception as e:
            print(f"   Could not retrieve product: {e}")
    
    print("\n✅ Price configuration is valid and ready for use!")
    
except stripe.error.InvalidRequestError as e:
    print(f"❌ Invalid price ID: {e}")
except stripe.error.AuthenticationError as e:
    print(f"❌ Authentication failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("Test completed!")
print("=" * 50)