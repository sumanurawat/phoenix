#!/usr/bin/env python3
"""Check user token balance and transactions in Firestore"""

import os
import sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment
load_dotenv()

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {
        'projectId': os.getenv('GOOGLE_CLOUD_PROJECT', 'phoenix-project-386')
    })

db = firestore.client()

def check_user_by_email(email: str):
    """Check user data by email"""
    print(f"\n{'='*80}")
    print(f"🔍 Searching for user: {email}")
    print(f"{'='*80}\n")

    # Query users collection for this email
    users = db.collection('users').where('email', '==', email).limit(1).stream()

    user_doc = None
    for user in users:
        user_doc = user
        break

    if not user_doc:
        print(f"❌ No user found with email: {email}")
        return None

    user_data = user_doc.to_dict()
    user_id = user_doc.id

    print(f"✅ User Found!")
    print(f"   Firebase UID: {user_id}")
    print(f"   Email: {user_data.get('email', 'N/A')}")
    print(f"   Name: {user_data.get('name', 'N/A')}")
    print(f"\n📊 Token Balance:")
    print(f"   Current Balance: {user_data.get('tokenBalance', 0)} tokens")
    print(f"   Total Earned: {user_data.get('totalTokensEarned', 0)} tokens")
    print(f"   Total Purchased: {user_data.get('totalTokensPurchased', 0)} tokens")
    print(f"   Total Spent: {user_data.get('totalTokensSpent', 0)} tokens")

    if user_data.get('stripe_customer_id'):
        print(f"\n💳 Stripe Info:")
        print(f"   Customer ID: {user_data.get('stripe_customer_id')}")

    return user_id

def check_transactions(user_id: str):
    """Check transaction history for user"""
    print(f"\n{'='*80}")
    print(f"📜 Transaction History for {user_id}")
    print(f"{'='*80}\n")

    # Query transactions without ordering (to avoid index requirement)
    transactions = db.collection('transactions')\
        .where('userId', '==', user_id)\
        .limit(50)\
        .stream()

    tx_list = list(transactions)

    if not tx_list:
        print("❌ No transactions found")
        return

    print(f"Found {len(tx_list)} recent transactions:\n")

    for i, tx in enumerate(tx_list, 1):
        tx_data = tx.to_dict()
        print(f"{i}. Transaction ID: {tx.id}")
        print(f"   Type: {tx_data.get('type')}")
        print(f"   Amount: {tx_data.get('amount')} tokens")
        print(f"   Timestamp: {tx_data.get('timestamp')}")

        details = tx_data.get('details', {})
        if details:
            print(f"   Details:")
            for key, value in details.items():
                print(f"      {key}: {value}")
        print()

def check_recent_checkouts(user_id: str):
    """Check for recent Stripe checkout sessions in logs"""
    print(f"\n{'='*80}")
    print(f"🔍 Checking for recent checkout sessions")
    print(f"{'='*80}\n")

    # We can't query Stripe logs from Firestore, but we can check if there are
    # any pending sessions that haven't been processed
    print("Session from logs: cs_test_a1yeW9aT93TDWMR2B5oaqd8Qr4WrokS7PJSmtXTPige1d8U7Q6CpihiT6S")
    print("\nChecking if this session was processed...")

    # Check if there's a transaction with this session ID
    transactions = db.collection('transactions')\
        .where('details.stripeSessionId', '==', 'cs_test_a1yeW9aT93TDWMR2B5oaqd8Qr4WrokS7PJSmtXTPige1d8U7Q6CpihiT6S')\
        .limit(1)\
        .stream()

    tx_list = list(transactions)

    if tx_list:
        print("✅ Session WAS processed!")
        for tx in tx_list:
            tx_data = tx.to_dict()
            print(f"\n   Transaction ID: {tx.id}")
            print(f"   Type: {tx_data.get('type')}")
            print(f"   Amount: {tx_data.get('amount')} tokens")
            print(f"   Timestamp: {tx_data.get('timestamp')}")
    else:
        print("❌ Session was NOT processed - webhook likely never fired or failed!")

if __name__ == "__main__":
    email = "sumanurawat12@gmail.com"

    # Check user
    user_id = check_user_by_email(email)

    if user_id:
        # Check transactions
        check_transactions(user_id)

        # Check recent checkout
        check_recent_checkouts(user_id)

    print(f"\n{'='*80}")
    print("✅ Investigation complete")
    print(f"{'='*80}\n")
