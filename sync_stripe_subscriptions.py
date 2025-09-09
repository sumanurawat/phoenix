#!/usr/bin/env python3
"""
Phoenix AI - Manual Stripe Subscription Sync

This script manually syncs subscription data from Stripe to Firebase.
Use this when webhooks aren't working or to recover from missed webhooks.

Usage:
python sync_stripe_subscriptions.py                  # Sync all recent subscriptions
python sync_stripe_subscriptions.py --email EMAIL    # Sync specific user by email
python sync_stripe_subscriptions.py --session SESSION_ID  # Sync specific checkout session
"""

import os
import sys
import argparse
from datetime import datetime, timezone
import stripe
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_services():
    """Initialize Stripe and Firebase services."""
    # Initialize Stripe
    stripe_key = os.getenv('STRIPE_SECRET_KEY')
    if not stripe_key:
        print("❌ No Stripe secret key found in environment!")
        return False
    
    stripe.api_key = stripe_key
    print("✅ Stripe API initialized successfully")
    
    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        print("✅ Firebase initialized")
        return db
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")
        return None

def find_firebase_uid_by_email(db, email):
    """Find Firebase UID by email from auth or existing records."""
    # First check if we have a user record with this email
    users = db.collection('users').where('email', '==', email).limit(1).get()
    if users:
        return users[0].to_dict().get('firebase_uid')
    
    # If not found, prompt for manual entry
    print(f"\n⚠️  Firebase UID not found for {email}")
    print("Please provide the Firebase UID from Firebase Auth console:")
    firebase_uid = input("Firebase UID: ").strip()
    
    if firebase_uid:
        # Create user record for future reference
        db.collection('users').document(firebase_uid).set({
            'firebase_uid': firebase_uid,
            'email': email,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        print(f"✅ User record created for {email}")
    
    return firebase_uid

def sync_checkout_session(db, session_id):
    """Sync a specific checkout session."""
    try:
        print(f"\n🔍 Fetching checkout session: {session_id}")
        session = stripe.checkout.Session.retrieve(session_id)
        
        print(f"   Customer: {session.customer}")
        print(f"   Customer Email: {session.customer_email}")
        print(f"   Status: {session.status}")
        print(f"   Payment Status: {session.payment_status}")
        
        if session.status != 'complete' or session.payment_status != 'paid':
            print("❌ Session not completed/paid")
            return False
        
        # Get subscription
        if not session.subscription:
            print("❌ No subscription ID in session")
            return False
        
        subscription = stripe.Subscription.retrieve(session.subscription)
        
        # Get or find Firebase UID
        firebase_uid = session.metadata.get('firebase_uid')
        if not firebase_uid and session.customer_email:
            firebase_uid = find_firebase_uid_by_email(db, session.customer_email)
        
        if not firebase_uid:
            print("❌ Could not determine Firebase UID")
            return False
        
        # Create/update subscription record
        subscription_data = {
            'firebase_uid': firebase_uid,
            'stripe_customer_id': session.customer,
            'stripe_subscription_id': session.subscription,
            'plan_id': 'premium_monthly',
            'status': subscription.status,
            'current_period_start': datetime.fromtimestamp(
                subscription.current_period_start, tz=timezone.utc
            ),
            'current_period_end': datetime.fromtimestamp(
                subscription.current_period_end, tz=timezone.utc
            ),
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        # Save to Firestore
        sub_ref = db.collection('user_subscriptions').document(session.subscription)
        sub_ref.set(subscription_data, merge=True)
        
        print(f"✅ Subscription synced for user {firebase_uid}")
        print(f"   Subscription ID: {session.subscription}")
        print(f"   Status: {subscription.status}")
        print(f"   Period End: {subscription_data['current_period_end']}")
        
        # Also ensure user record exists
        user_ref = db.collection('users').document(firebase_uid)
        user_ref.set({
            'firebase_uid': firebase_uid,
            'email': session.customer_email,
            'stripe_customer_id': session.customer,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Error syncing session: {e}")
        return False

def sync_customer_subscriptions(db, email):
    """Sync all subscriptions for a customer by email."""
    try:
        print(f"\n🔍 Searching for customer with email: {email}")
        
        # Search for customer in Stripe
        customers = stripe.Customer.list(email=email, limit=1)
        if not customers.data:
            print(f"❌ No Stripe customer found with email: {email}")
            return False
        
        customer = customers.data[0]
        print(f"✅ Found customer: {customer.id}")
        
        # Get Firebase UID
        firebase_uid = find_firebase_uid_by_email(db, email)
        if not firebase_uid:
            print("❌ Could not determine Firebase UID")
            return False
        
        # Get all subscriptions for this customer
        subscriptions = stripe.Subscription.list(customer=customer.id, limit=10)
        
        active_count = 0
        for subscription in subscriptions.data:
            if subscription.status in ['active', 'trialing']:
                active_count += 1
                
                subscription_data = {
                    'firebase_uid': firebase_uid,
                    'stripe_customer_id': customer.id,
                    'stripe_subscription_id': subscription.id,
                    'plan_id': 'premium_monthly',
                    'status': subscription.status,
                    'current_period_start': datetime.fromtimestamp(
                        subscription.current_period_start, tz=timezone.utc
                    ),
                    'current_period_end': datetime.fromtimestamp(
                        subscription.current_period_end, tz=timezone.utc
                    ),
                    'cancel_at_period_end': subscription.cancel_at_period_end,
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }
                
                # Save to Firestore
                sub_ref = db.collection('user_subscriptions').document(subscription.id)
                sub_ref.set(subscription_data, merge=True)
                
                print(f"✅ Synced subscription: {subscription.id} ({subscription.status})")
        
        if active_count == 0:
            print(f"⚠️  No active subscriptions found for {email}")
        else:
            print(f"✅ Synced {active_count} active subscription(s)")
        
        # Ensure user record exists
        user_ref = db.collection('users').document(firebase_uid)
        user_ref.set({
            'firebase_uid': firebase_uid,
            'email': email,
            'stripe_customer_id': customer.id,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Error syncing customer: {e}")
        return False

def sync_recent_sessions(db, hours=24):
    """Sync all recent checkout sessions."""
    try:
        print(f"\n🔍 Fetching checkout sessions from last {hours} hours...")
        
        # Get recent sessions
        sessions = stripe.checkout.Session.list(limit=100)
        
        synced_count = 0
        for session in sessions.data:
            if session.status == 'complete' and session.subscription:
                print(f"\n📋 Session: {session.id}")
                print(f"   Email: {session.customer_email}")
                print(f"   Created: {datetime.fromtimestamp(session.created)}")
                
                if sync_checkout_session(db, session.id):
                    synced_count += 1
        
        print(f"\n✅ Synced {synced_count} subscription(s)")
        return True
        
    except Exception as e:
        print(f"❌ Error syncing recent sessions: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Manually sync Stripe subscriptions to Firebase"
    )
    
    parser.add_argument('--email', help='Sync subscriptions for specific email')
    parser.add_argument('--session', help='Sync specific checkout session ID')
    parser.add_argument('--recent', type=int, default=24, 
                       help='Sync sessions from last N hours (default: 24)')
    parser.add_argument('--all', action='store_true', 
                       help='Sync all recent sessions')
    
    args = parser.parse_args()
    
    # Initialize services
    db = initialize_services()
    if not db:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Phoenix AI - Stripe Subscription Sync")
    print("=" * 60)
    
    success = False
    
    if args.session:
        # Sync specific session
        success = sync_checkout_session(db, args.session)
    
    elif args.email:
        # Sync by email
        success = sync_customer_subscriptions(db, args.email)
    
    elif args.all:
        # Sync all recent
        success = sync_recent_sessions(db, args.recent)
    
    else:
        # Interactive mode
        print("\nWhat would you like to sync?")
        print("1. Specific checkout session")
        print("2. Customer by email")
        print("3. All recent sessions")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            session_id = input("Enter checkout session ID: ").strip()
            if session_id:
                success = sync_checkout_session(db, session_id)
        
        elif choice == '2':
            email = input("Enter customer email: ").strip()
            if email:
                success = sync_customer_subscriptions(db, email)
        
        elif choice == '3':
            success = sync_recent_sessions(db)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Sync completed successfully!")
    else:
        print("❌ Sync failed or incomplete")
    print("=" * 60)

if __name__ == '__main__':
    main()