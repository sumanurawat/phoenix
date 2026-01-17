#!/usr/bin/env python3
"""
Account Deletion Admin Script (Killswitch)
==========================================

Admin tool for deleting user accounts and all associated data.
Use this to remove problematic accounts, spam accounts, or honor user deletion requests.

CAUTION: This action is IRREVERSIBLE. All user data will be permanently deleted:
- Profile and account settings
- All generated images and videos (including R2 storage)
- Transaction history
- Social media connections
- Comments on other users' content
- Stripe customer record (cascades to subscriptions)
- Session data

Usage:
------
    python scripts/delete_account.py <username_or_user_id> [--dry-run] [--force]

Examples:
---------
    # Preview what would be deleted (RECOMMENDED FIRST STEP)
    python scripts/delete_account.py johndoe --dry-run

    # Delete account by username (with confirmation prompt)
    python scripts/delete_account.py johndoe

    # Delete account by Firebase UID (with confirmation prompt)
    python scripts/delete_account.py abc123def456

    # Delete account without confirmation (DANGEROUS - use with caution)
    python scripts/delete_account.py johndoe --force

Security Notes:
---------------
- This script should only be run by authorized administrators
- All deletions are logged for audit purposes
- Consider backing up important data before deletion

Author: Friedmomo Engineering
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import firebase_admin
from firebase_admin import credentials, firestore


def init_firebase():
    """
    Initialize Firebase Admin SDK if not already initialized.

    Uses Application Default Credentials (ADC) for authentication.
    Make sure GOOGLE_APPLICATION_CREDENTIALS is set or you're running on GCP.

    Returns:
        Firestore client instance
    """
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firestore.client()


def resolve_user_id(db, identifier: str) -> tuple:
    """
    Resolve a username or user ID to the actual Firebase UID.

    Args:
        db: Firestore client
        identifier: Username or Firebase UID

    Returns:
        Tuple of (user_id, username, user_data) or (None, None, None) if not found
    """
    # Strategy 1: Try to look up as username (most common case)
    username_lower = identifier.lower().strip()
    username_ref = db.collection('usernames').document(username_lower)
    username_doc = username_ref.get()

    if username_doc.exists:
        user_id = username_doc.to_dict().get('userId')
        if user_id:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                return user_id, user_data.get('username'), user_data

    # Strategy 2: Try as Firebase UID directly
    user_ref = db.collection('users').document(identifier)
    user_doc = user_ref.get()

    if user_doc.exists:
        user_data = user_doc.to_dict()
        return identifier, user_data.get('username'), user_data

    return None, None, None


def preview_deletion(db, user_id: str, username: str):
    """
    Show a detailed preview of what will be deleted.

    Args:
        db: Firestore client
        user_id: Firebase UID
        username: Username (for display)
    """
    print("\n" + "=" * 70)
    print("📋 DATA TO BE DELETED")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Count creations
    # -------------------------------------------------------------------------
    creations_query = db.collection('creations').where('userId', '==', user_id)
    creations = list(creations_query.stream())

    published_count = sum(1 for c in creations if c.to_dict().get('status') == 'published')
    draft_count = sum(1 for c in creations if c.to_dict().get('status') in ['draft', 'pending', 'processing'])
    failed_count = sum(1 for c in creations if c.to_dict().get('status') == 'failed')

    print(f"\n🎨 Creations: {len(creations)} total")
    print(f"   ├─ Published: {published_count}")
    print(f"   ├─ Drafts/Processing: {draft_count}")
    print(f"   └─ Failed: {failed_count}")

    # Count comments on user's creations
    total_comments_on_own = 0
    for creation in creations:
        comments = list(creation.reference.collection('comments').stream())
        total_comments_on_own += len(comments)
    if total_comments_on_own > 0:
        print(f"   └─ Comments on these creations: {total_comments_on_own}")

    # -------------------------------------------------------------------------
    # Count R2 media files
    # -------------------------------------------------------------------------
    media_files = sum(1 for c in creations if c.to_dict().get('mediaUrl'))
    print(f"\n📁 R2 Storage Files: ~{media_files} (images/videos)")

    # -------------------------------------------------------------------------
    # Count transactions
    # -------------------------------------------------------------------------
    transactions_query = db.collection('transactions').where('userId', '==', user_id)
    transactions = list(transactions_query.stream())
    print(f"\n💳 Transactions: {len(transactions)}")

    # -------------------------------------------------------------------------
    # Count subscriptions
    # -------------------------------------------------------------------------
    subs_query = db.collection('user_subscriptions').where('firebase_uid', '==', user_id)
    subs = list(subs_query.stream())
    # Also check for free tier document
    free_doc = db.collection('user_subscriptions').document(f"free_{user_id}").get()
    sub_count = len(subs) + (1 if free_doc.exists else 0)
    print(f"\n📦 Subscription Records: {sub_count}")

    # -------------------------------------------------------------------------
    # Count social accounts
    # -------------------------------------------------------------------------
    social_query = db.collection('user_social_accounts').where('user_id', '==', user_id)
    social_accounts = list(social_query.stream())
    print(f"\n📱 Social Account Connections: {len(social_accounts)}")

    # -------------------------------------------------------------------------
    # Count social posts
    # -------------------------------------------------------------------------
    posts_query = db.collection('social_posts').where('user_id', '==', user_id)
    social_posts = list(posts_query.stream())
    print(f"📰 Synced Social Posts: {len(social_posts)}")

    # -------------------------------------------------------------------------
    # Check username claim
    # -------------------------------------------------------------------------
    if username:
        username_ref = db.collection('usernames').document(username.lower())
        username_doc = username_ref.get()
        print(f"\n👤 Username Claim: {'Yes' if username_doc.exists else 'No'}")
        if username_doc.exists:
            print(f"   └─ '{username}' will become available for others")

    # -------------------------------------------------------------------------
    # User document
    # -------------------------------------------------------------------------
    print(f"\n📄 User Document: Yes")

    # -------------------------------------------------------------------------
    # Stripe customer (if exists)
    # -------------------------------------------------------------------------
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        stripe_customer_id = user_data.get('stripe_customer_id')
        if stripe_customer_id:
            print(f"\n💰 Stripe Customer: {stripe_customer_id}")
            print("   └─ Will be deleted (cascades to payment methods)")

    print("\n" + "=" * 70)


def delete_account(identifier: str, dry_run: bool = False, force: bool = False):
    """
    Delete a user account and all associated data.

    Args:
        identifier: Username or Firebase UID
        dry_run: If True, only preview without making changes
        force: If True, skip confirmation prompt

    Returns:
        True if deletion was successful, False otherwise
    """
    db = init_firebase()

    # -------------------------------------------------------------------------
    # Resolve user
    # -------------------------------------------------------------------------
    user_id, username, user_data = resolve_user_id(db, identifier)

    if not user_id:
        print(f"\n❌ User not found: {identifier}")
        print("   The identifier could not be resolved to a user ID.")
        print("   Try using the exact username or Firebase UID.")
        return False

    # -------------------------------------------------------------------------
    # Display user info
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("⚠️  ACCOUNT DELETION REQUEST")
    print("=" * 70)
    print(f"\n👤 Username: @{username or 'no-username'}")
    print(f"🆔 User ID:  {user_id}")

    if user_data:
        print(f"📧 Email:    {user_data.get('email', 'N/A')}")
        print(f"💰 Tokens:   {user_data.get('tokenBalance', 0)}")
        created_at = user_data.get('createdAt')
        if created_at:
            print(f"📅 Created:  {created_at}")

    # -------------------------------------------------------------------------
    # Show deletion preview
    # -------------------------------------------------------------------------
    preview_deletion(db, user_id, username)

    # -------------------------------------------------------------------------
    # Dry run mode
    # -------------------------------------------------------------------------
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes were made")
        print("   Remove --dry-run flag to actually delete the account")
        return True

    # -------------------------------------------------------------------------
    # Confirmation prompt (unless --force)
    # -------------------------------------------------------------------------
    if not force:
        print("\n" + "=" * 70)
        print("⚠️  WARNING: This action is PERMANENT and IRREVERSIBLE!")
        print("=" * 70)
        print("\n   All data shown above will be permanently deleted.")
        print("   The user will need to create a new account to use the platform.\n")

        confirm_text = username or user_id
        user_input = input(f"   Type '{confirm_text}' to confirm deletion: ").strip()

        if user_input.lower() != confirm_text.lower():
            print("\n❌ Deletion CANCELLED - confirmation did not match")
            return False

    # -------------------------------------------------------------------------
    # Execute deletion
    # -------------------------------------------------------------------------
    print("\n🗑️  Starting account deletion...")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Import and run deletion service
    from services.account_deletion_service import get_deletion_service

    deletion_service = get_deletion_service()
    result = deletion_service.delete_account(user_id, admin_initiated=True)

    # -------------------------------------------------------------------------
    # Display results
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)

    if result['success']:
        print("✅ ACCOUNT DELETED SUCCESSFULLY")
        print("=" * 70)

        print(f"\n📊 Cleanup Summary:")
        print(f"   Firestore Collections:")
        for key, value in result.get('cleanup_summary', {}).get('firestore', {}).items():
            if isinstance(value, int):
                print(f"      {key}: {value} documents")
            else:
                print(f"      {key}: {value}")

        storage = result.get('cleanup_summary', {}).get('storage', {})
        if storage:
            print(f"\n   Cloud Storage:")
            for key, value in storage.items():
                print(f"      {key}: {value} files")

        external = result.get('cleanup_summary', {}).get('external', {})
        if external:
            print(f"\n   External Services:")
            for key, value in external.items():
                print(f"      {key}: {value}")

        print(f"\n⏱️  Duration: {result.get('duration_ms', 0)}ms")

        if username:
            print(f"\n👤 Username '@{username}' is now available for reuse")

        return True

    else:
        print("⚠️  DELETION COMPLETED WITH ERRORS")
        print("=" * 70)

        print(f"\n📊 Partial Cleanup Summary:")
        for key, value in result.get('cleanup_summary', {}).get('firestore', {}).items():
            print(f"   {key}: {value}")

        print(f"\n❌ Errors ({len(result.get('errors', []))}):")
        for error in result.get('errors', []):
            print(f"   - {error}")

        print("\n⚠️  Some data may not have been deleted. Check errors above.")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Delete a user account and all associated data (ADMIN ONLY)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
════════════════════════════════════════════════════════════════════════
⚠️  CAUTION: This action is IRREVERSIBLE!
════════════════════════════════════════════════════════════════════════

All user data will be permanently deleted including:
  • User profile and account settings
  • All generated images and videos (from R2 storage)
  • Transaction history and token balance
  • Social media connections
  • Comments on other users' content
  • Stripe customer record (and subscriptions)
  • Session data

Examples:
  # Preview deletion (RECOMMENDED first step)
  python scripts/delete_account.py johndoe --dry-run

  # Delete account with confirmation prompt
  python scripts/delete_account.py johndoe

  # Delete by Firebase UID
  python scripts/delete_account.py abc123def456ghi789

  # Force delete without confirmation (DANGEROUS)
  python scripts/delete_account.py johndoe --force

════════════════════════════════════════════════════════════════════════
        """
    )

    parser.add_argument(
        'identifier',
        help='Username or Firebase UID of the account to delete'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be deleted WITHOUT making any changes'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt (DANGEROUS - use with extreme caution)'
    )

    args = parser.parse_args()

    # Run deletion
    success = delete_account(
        identifier=args.identifier,
        dry_run=args.dry_run,
        force=args.force
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
