#!/usr/bin/env python3
"""
Manually process recent Stripe checkout sessions that weren't processed by webhooks.
This script mimics the fallback mechanism but can be run independently.
"""

import os
import sys
sys.path.append('.')

from services.stripe_service import StripeService
import stripe
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Initialize Firebase first
    if not firebase_admin._apps:
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")
    
    # Initialize Stripe service
    stripe_service = StripeService()
    
    if not stripe_service.is_configured:
        print("❌ Stripe not configured")
        return
    
    print("🔍 Looking for recent unprocessed checkout sessions...")
    
    # Get recent sessions
    recent_sessions = stripe.checkout.Session.list(
        limit=10,
        expand=['data.subscription']
    )
    
    print(f"📋 Found {len(recent_sessions.data)} recent checkout sessions")
    
    for checkout_session in recent_sessions.data:
        if (checkout_session.status == 'complete' and 
            checkout_session.payment_status == 'paid' and 
            checkout_session.subscription):
            
            session_id = checkout_session.id
            firebase_uid = checkout_session.metadata.get('firebase_uid')
            
            print(f"\n🔍 Checking session {session_id}:")
            print(f"   Firebase UID: {firebase_uid}")
            print(f"   Customer Email: {checkout_session.customer_email}")
            print(f"   Status: {checkout_session.status}")
            print(f"   Payment Status: {checkout_session.payment_status}")
            
            if firebase_uid:
                # Get subscription ID
                if isinstance(checkout_session.subscription, str):
                    subscription_id = checkout_session.subscription
                else:
                    subscription_id = checkout_session.subscription.id
                
                print(f"   Subscription ID: {subscription_id}")
                
                # Check if subscription already exists in Firebase
                if stripe_service.db:
                    existing_sub = stripe_service.db.collection('user_subscriptions').document(subscription_id).get()
                    if not existing_sub.exists:
                        print(f"🚨 Subscription {subscription_id} not found in Firebase - processing manually!")
                        
                        # Manually process this checkout session
                        result = stripe_service._handle_checkout_completed(checkout_session)
                        if result.get('success'):
                            print(f"🎉 Successfully processed checkout session {session_id} manually!")
                        else:
                            print(f"❌ Failed to process checkout session manually: {result}")
                    else:
                        print(f"✅ Subscription {subscription_id} already exists in Firebase")
                else:
                    print("❌ No Firebase connection")

if __name__ == '__main__':
    main()