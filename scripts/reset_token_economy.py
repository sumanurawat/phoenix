#!/usr/bin/env python3
"""
Reset Token Economy Script

This script clears all transaction history and resets all user token balances to zero.
Use this when you want to start fresh with the token economy tracking.

DANGER: This is IRREVERSIBLE! All transaction history will be permanently deleted.

Usage:
    python scripts/reset_token_economy.py --confirm

Options:
    --confirm           Required flag to confirm you want to reset everything
    --dry-run           Show what would be deleted without actually deleting
    --project PROJECT   Firebase project ID (default: phoenix-project-386)
"""

import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path to import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as gcloud_firestore


def initialize_firebase(project_id):
    """Initialize Firebase Admin SDK."""
    try:
        # Check if already initialized
        firebase_admin.get_app()
        print("✅ Firebase already initialized")
    except ValueError:
        # Initialize Firebase
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not cred_path:
            print("❌ Error: GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
            sys.exit(1)

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'projectId': project_id
        })
        print(f"✅ Firebase initialized for project: {project_id}")

    return firestore.client()


def get_all_transactions(db):
    """Get all transaction documents."""
    transactions_ref = db.collection('transactions')
    docs = list(transactions_ref.stream())
    return docs


def get_all_users_with_tokens(db):
    """Get all users who have token balances."""
    users_ref = db.collection('users')

    # Get all users
    users = []
    for doc in users_ref.stream():
        user_data = doc.to_dict()
        if user_data.get('tokenBalance', 0) != 0 or user_data.get('totalTokensEarned', 0) != 0:
            users.append({
                'id': doc.id,
                'tokenBalance': user_data.get('tokenBalance', 0),
                'totalTokensEarned': user_data.get('totalTokensEarned', 0)
            })

    return users


def delete_all_transactions(db, dry_run=False):
    """Delete all transactions from Firestore."""
    print("\n📋 Fetching all transactions...")
    transactions = get_all_transactions(db)

    if not transactions:
        print("   No transactions found")
        return 0

    print(f"   Found {len(transactions)} transactions")

    if dry_run:
        print(f"   [DRY RUN] Would delete {len(transactions)} transactions")
        return len(transactions)

    print(f"   Deleting {len(transactions)} transactions...")

    # Delete in batches of 500 (Firestore limit)
    batch = db.batch()
    count = 0

    for doc in transactions:
        batch.delete(doc.reference)
        count += 1

        # Commit every 500 docs
        if count % 500 == 0:
            batch.commit()
            print(f"   Deleted {count}/{len(transactions)}...")
            batch = db.batch()

    # Commit remaining
    if count % 500 != 0:
        batch.commit()

    print(f"   ✅ Deleted {count} transactions")
    return count


def reset_user_balances(db, dry_run=False):
    """Reset all user token balances to zero."""
    print("\n👥 Fetching all users with token balances...")
    users = get_all_users_with_tokens(db)

    if not users:
        print("   No users with token balances found")
        return 0

    print(f"   Found {len(users)} users with token balances")

    # Show summary
    total_balance = sum(u['tokenBalance'] for u in users)
    total_earned = sum(u['totalTokensEarned'] for u in users)
    print(f"   Total tokens in economy: {total_balance:,}")
    print(f"   Total tokens earned: {total_earned:,}")

    if dry_run:
        print(f"   [DRY RUN] Would reset {len(users)} user balances to zero")
        return len(users)

    print(f"   Resetting {len(users)} user balances to zero...")

    # Reset in batches
    batch = db.batch()
    count = 0

    for user in users:
        user_ref = db.collection('users').document(user['id'])
        batch.update(user_ref, {
            'tokenBalance': 0,
            'totalTokensEarned': 0
        })
        count += 1

        # Commit every 500 docs
        if count % 500 == 0:
            batch.commit()
            print(f"   Reset {count}/{len(users)}...")
            batch = db.batch()

    # Commit remaining
    if count % 500 != 0:
        batch.commit()

    print(f"   ✅ Reset {count} user balances")
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Reset token economy: delete all transactions and reset balances to zero',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--confirm', action='store_true',
                       help='Required flag to confirm you want to reset everything')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--project', default='phoenix-project-386',
                       help='Firebase project ID (default: phoenix-project-386)')

    args = parser.parse_args()

    print("=" * 70)
    print("🔥 TOKEN ECONOMY RESET SCRIPT")
    print("=" * 70)

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
    elif not args.confirm:
        print("\n❌ ERROR: You must use --confirm flag to proceed")
        print("\nThis script will:")
        print("  • Delete ALL transaction history (IRREVERSIBLE)")
        print("  • Reset ALL user token balances to zero")
        print("  • Reset ALL user totalTokensEarned to zero")
        print("\nTo proceed, run with --confirm flag:")
        print("  python scripts/reset_token_economy.py --confirm")
        print("\nOr to see what would be deleted without deleting:")
        print("  python scripts/reset_token_economy.py --dry-run")
        sys.exit(1)
    else:
        print("\n⚠️  WARNING: This will DELETE ALL token data!")
        print("   This action is IRREVERSIBLE!")
        print("\nPress Ctrl+C now to cancel, or Enter to continue...")
        input()

    # Initialize Firebase
    db = initialize_firebase(args.project)

    # Delete transactions
    tx_count = delete_all_transactions(db, dry_run=args.dry_run)

    # Reset user balances
    user_count = reset_user_balances(db, dry_run=args.dry_run)

    # Summary
    print("\n" + "=" * 70)
    if args.dry_run:
        print("🔍 DRY RUN COMPLETE")
        print(f"   Would delete: {tx_count:,} transactions")
        print(f"   Would reset: {user_count:,} user balances")
    else:
        print("✅ RESET COMPLETE")
        print(f"   Deleted: {tx_count:,} transactions")
        print(f"   Reset: {user_count:,} user balances")
        print(f"   Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)


if __name__ == '__main__':
    main()
