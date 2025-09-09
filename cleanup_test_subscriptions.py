#!/usr/bin/env python3
"""
Phoenix AI - Test Subscription Cleanup Script

This script helps clean up invalid or test subscription data from Firestore.
Use this when you have orphaned subscription records that reference non-existent Stripe subscriptions.

Usage:
python cleanup_test_subscriptions.py --list        # List all subscriptions
python cleanup_test_subscriptions.py --cleanup     # Clean invalid subscriptions
python cleanup_test_subscriptions.py --user UID    # Clean subscriptions for specific user
"""

import os
import sys
import argparse
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import stripe

def initialize_services():
    """Initialize Firebase and Stripe services."""
    # Initialize Firebase
    try:
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate('firebase-credentials.json')
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized with service account")
            except FileNotFoundError:
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized with default credentials")
        
        db = firestore.client()
        
        # Initialize Stripe
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if stripe_key:
            stripe.api_key = stripe_key
            print("✅ Stripe initialized successfully")
            stripe_configured = True
        else:
            print("⚠️  Stripe not configured - will only show local data")
            stripe_configured = False
        
        return db, stripe_configured
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        return None, None

def list_all_subscriptions(db):
    """List all subscription records in Firestore."""
    print("\n📋 Current Subscription Records:")
    print("=" * 80)
    
    try:
        # Get all subscription records
        subs = db.collection('user_subscriptions').get()
        
        if not subs:
            print("No subscription records found.")
            return []
        
        subscription_data = []
        for doc in subs:
            data = doc.to_dict()
            subscription_data.append({
                'doc_id': doc.id,
                'firebase_uid': data.get('firebase_uid', 'N/A'),
                'stripe_subscription_id': data.get('stripe_subscription_id', 'N/A'),
                'status': data.get('status', 'N/A'),
                'plan_id': data.get('plan_id', 'N/A'),
                'cancel_at_period_end': data.get('cancel_at_period_end', False),
                'created_at': data.get('created_at'),
                'data': data
            })
        
        # Display in table format
        for i, sub in enumerate(subscription_data, 1):
            print(f"{i}. Document ID: {sub['doc_id']}")
            print(f"   User: {sub['firebase_uid']}")
            print(f"   Stripe ID: {sub['stripe_subscription_id']}")
            print(f"   Status: {sub['status']}")
            print(f"   Plan: {sub['plan_id']}")
            print(f"   Cancel at Period End: {sub['cancel_at_period_end']}")
            
            if sub['created_at']:
                created = sub['created_at'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(sub['created_at'], 'strftime') else str(sub['created_at'])
                print(f"   Created: {created}")
            
            print()
        
        return subscription_data
        
    except Exception as e:
        print(f"❌ Failed to list subscriptions: {e}")
        return []

def validate_stripe_subscriptions(subscription_data, stripe_configured):
    """Validate subscription records against Stripe."""
    if not stripe_configured:
        print("⚠️  Skipping Stripe validation - not configured")
        return subscription_data
    
    print("\n🔍 Validating Subscriptions with Stripe:")
    print("=" * 50)
    
    valid_subs = []
    invalid_subs = []
    
    for sub in subscription_data:
        stripe_id = sub['stripe_subscription_id']
        
        if not stripe_id or stripe_id == 'N/A':
            print(f"❌ {sub['doc_id']}: Missing Stripe subscription ID")
            invalid_subs.append(sub)
            continue
        
        if not stripe_id.startswith('sub_'):
            print(f"❌ {sub['doc_id']}: Invalid Stripe ID format: {stripe_id}")
            invalid_subs.append(sub)
            continue
        
        try:
            # Check if subscription exists in Stripe
            stripe_sub = stripe.Subscription.retrieve(stripe_id)
            print(f"✅ {sub['doc_id']}: Valid - {stripe_sub.status}")
            valid_subs.append(sub)
            
        except stripe.error.InvalidRequestError as e:
            if 'No such subscription' in str(e):
                print(f"❌ {sub['doc_id']}: Subscription not found in Stripe: {stripe_id}")
                invalid_subs.append(sub)
            else:
                print(f"❌ {sub['doc_id']}: Stripe error: {e}")
                invalid_subs.append(sub)
        except Exception as e:
            print(f"❌ {sub['doc_id']}: Validation error: {e}")
            invalid_subs.append(sub)
    
    print(f"\n📊 Validation Summary:")
    print(f"Valid subscriptions: {len(valid_subs)}")
    print(f"Invalid subscriptions: {len(invalid_subs)}")
    
    return valid_subs, invalid_subs

def cleanup_invalid_subscriptions(db, invalid_subs, dry_run=True):
    """Clean up invalid subscription records."""
    if not invalid_subs:
        print("No invalid subscriptions to clean up.")
        return
    
    action = "Would delete" if dry_run else "Deleting"
    print(f"\n🧹 {action} Invalid Subscriptions:")
    print("=" * 50)
    
    for sub in invalid_subs:
        print(f"{action}: {sub['doc_id']} (User: {sub['firebase_uid']}, Stripe ID: {sub['stripe_subscription_id']})")
        
        if not dry_run:
            try:
                db.collection('user_subscriptions').document(sub['doc_id']).delete()
                print(f"✅ Deleted: {sub['doc_id']}")
            except Exception as e:
                print(f"❌ Failed to delete {sub['doc_id']}: {e}")
    
    if dry_run:
        print(f"\n⚠️  DRY RUN - No data was actually deleted")
        print("Run with --confirm to actually delete the records")

def cleanup_user_subscriptions(db, firebase_uid, dry_run=True):
    """Clean up all subscriptions for a specific user."""
    try:
        user_subs = db.collection('user_subscriptions')\
            .where('firebase_uid', '==', firebase_uid).get()
        
        if not user_subs:
            print(f"No subscriptions found for user: {firebase_uid}")
            return
        
        action = "Would delete" if dry_run else "Deleting"
        print(f"\n🧹 {action} subscriptions for user {firebase_uid}:")
        print("=" * 60)
        
        for doc in user_subs:
            data = doc.to_dict()
            stripe_id = data.get('stripe_subscription_id', 'N/A')
            print(f"{action}: {doc.id} (Stripe ID: {stripe_id})")
            
            if not dry_run:
                try:
                    doc.reference.delete()
                    print(f"✅ Deleted: {doc.id}")
                except Exception as e:
                    print(f"❌ Failed to delete {doc.id}: {e}")
        
        if dry_run:
            print(f"\n⚠️  DRY RUN - No data was actually deleted")
            print("Run with --confirm to actually delete the records")
    
    except Exception as e:
        print(f"❌ Failed to cleanup user subscriptions: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Phoenix AI Subscription Cleanup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--list', action='store_true', help='List all subscription records')
    parser.add_argument('--cleanup', action='store_true', help='Clean up invalid subscriptions (dry run)')
    parser.add_argument('--user', help='Clean up subscriptions for specific user (Firebase UID)')
    parser.add_argument('--confirm', action='store_true', help='Actually perform deletions (not dry run)')
    
    args = parser.parse_args()
    
    if not any([args.list, args.cleanup, args.user]):
        parser.print_help()
        return
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Initialize services
    db, stripe_configured = initialize_services()
    if not db:
        sys.exit(1)
    
    if args.list:
        subscription_data = list_all_subscriptions(db)
        if subscription_data and stripe_configured:
            validate_stripe_subscriptions(subscription_data, stripe_configured)
    
    elif args.cleanup:
        print("🔍 Analyzing subscription data...")
        subscription_data = list_all_subscriptions(db)
        
        if subscription_data:
            if stripe_configured:
                valid_subs, invalid_subs = validate_stripe_subscriptions(subscription_data, stripe_configured)
                cleanup_invalid_subscriptions(db, invalid_subs, dry_run=not args.confirm)
            else:
                print("⚠️  Cannot validate without Stripe configuration")
        else:
            print("No subscriptions found to cleanup.")
    
    elif args.user:
        cleanup_user_subscriptions(db, args.user, dry_run=not args.confirm)

if __name__ == '__main__':
    main()