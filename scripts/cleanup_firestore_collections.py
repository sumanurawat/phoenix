#!/usr/bin/env python3
"""
Firestore Collection Cleanup Script
Deletes orphaned/legacy collections from friedmomo.com

Usage:
    python scripts/cleanup_firestore_collections.py --dry-run  # Preview what will be deleted
    python scripts/cleanup_firestore_collections.py            # Actually delete

WARNING: This is irreversible! Make sure you have backups.
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Collections marked for deletion (verified as unused in codebase)
COLLECTIONS_TO_DELETE = [
    'link_clicks',           # Click tracking feature removed
    'shortened_links',       # URL shortener feature removed
    'deepface_jobs',         # DeepFace AI feature removed
    'video_generations',     # Replaced by 'creations' collection
    'conversations',         # Chat feature removed
    'messages',              # Chat feature removed
    'reel_jobs',             # Deprecated reel maker feature
    'reel_job_checkpoints',  # Deprecated reel maker feature
    'reel_maker_jobs',       # Deprecated duplicate collection
    'reel_maker_projects',   # Deprecated reel maker feature
]

# Collections that MUST NOT be deleted (safety check)
PROTECTED_COLLECTIONS = [
    'users',
    'usernames',
    'creations',
    'transactions',
    'user_subscriptions',
    'user_social_accounts',
    'cache_sessions',
    'rate_limits',
    'security_alerts',
    'website_stats',
]


def delete_collection(db, collection_ref, batch_size=100, dry_run=True):
    """Delete all documents in a collection in batches."""
    docs = collection_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        if dry_run:
            print(f"  [DRY RUN] Would delete: {collection_ref.id}/{doc.id}")
        else:
            doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        # Recurse for more documents
        return deleted + delete_collection(db, collection_ref, batch_size, dry_run)

    return deleted


def get_collection_stats(db, collection_name):
    """Get document count and sample data from a collection."""
    collection_ref = db.collection(collection_name)

    # Get approximate count (limited to 1000 for speed)
    docs = list(collection_ref.limit(1000).stream())
    count = len(docs)

    # Get sample document
    sample = None
    if docs:
        sample = docs[0].to_dict()
        # Truncate large fields for display
        for key, value in list(sample.items()):
            if isinstance(value, str) and len(value) > 100:
                sample[key] = value[:100] + '...'
            elif isinstance(value, bytes):
                sample[key] = f'<bytes: {len(value)} bytes>'
            elif isinstance(value, dict):
                sample[key] = f'<dict: {len(value)} keys>'
            elif isinstance(value, list):
                sample[key] = f'<list: {len(value)} items>'

    return {
        'count': count,
        'count_note': '1000+' if count == 1000 else str(count),
        'sample': sample
    }


def main():
    parser = argparse.ArgumentParser(
        description='Clean up unused Firestore collections for friedmomo.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run          Preview what will be deleted
  %(prog)s                    Delete collections (IRREVERSIBLE!)
  %(prog)s --list             List all collections and their status
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without deleting')
    parser.add_argument('--list', action='store_true',
                        help='List all collections without deleting')
    parser.add_argument('--collection', type=str,
                        help='Delete only this specific collection')
    args = parser.parse_args()

    # Initialize Firebase
    if not firebase_admin._apps:
        try:
            creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

            # Try to load from JSON file
            if os.path.exists(creds_path):
                print(f"Using credentials from: {creds_path}")
                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)
            # Alternatively, load from environment variable
            elif os.getenv("FIREBASE_CREDENTIALS"):
                import json
                print("Using credentials from FIREBASE_CREDENTIALS env var")
                cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            # Try GOOGLE_APPLICATION_CREDENTIALS or gcloud ADC
            else:
                print("Using default application credentials")
                firebase_admin.initialize_app()
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            print("\nMake sure you have one of:")
            print("  1. firebase-credentials.json in project root")
            print("  2. FIREBASE_CREDENTIALS env var with JSON credentials")
            print("  3. GOOGLE_APPLICATION_CREDENTIALS env var set")
            print("  4. Run: gcloud auth application-default login")
            sys.exit(1)

    db = firestore.client()

    print("=" * 70)
    print("FIRESTORE COLLECTION CLEANUP - friedmomo.com")
    print("=" * 70)

    if args.list:
        print(f"Mode: LIST ONLY (no changes)")
    elif args.dry_run:
        print(f"Mode: DRY RUN (preview changes)")
    else:
        print(f"Mode: LIVE DELETE (IRREVERSIBLE!)")

    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)

    # If --list, show all collections
    if args.list:
        print("\n📋 PROTECTED COLLECTIONS (will NOT be deleted):")
        for name in PROTECTED_COLLECTIONS:
            stats = get_collection_stats(db, name)
            status = "empty" if stats['count'] == 0 else f"{stats['count_note']} docs"
            print(f"   ✓ {name}: {status}")

        print("\n🗑️  COLLECTIONS TO DELETE:")
        for name in COLLECTIONS_TO_DELETE:
            stats = get_collection_stats(db, name)
            status = "empty" if stats['count'] == 0 else f"{stats['count_note']} docs"
            print(f"   ✗ {name}: {status}")

        return

    # Determine which collections to process
    if args.collection:
        if args.collection in PROTECTED_COLLECTIONS:
            print(f"\n❌ ERROR: '{args.collection}' is PROTECTED and cannot be deleted!")
            sys.exit(1)
        if args.collection not in COLLECTIONS_TO_DELETE:
            print(f"\n⚠️  WARNING: '{args.collection}' is not in the approved deletion list.")
            confirm = input("Are you sure you want to delete it? (type 'yes' to confirm): ")
            if confirm.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        collections_to_process = [args.collection]
    else:
        collections_to_process = COLLECTIONS_TO_DELETE

    # Safety check
    for collection_name in collections_to_process:
        if collection_name in PROTECTED_COLLECTIONS:
            print(f"\n❌ ERROR: '{collection_name}' is in PROTECTED_COLLECTIONS!")
            print("   Remove it from COLLECTIONS_TO_DELETE or review the protection list.")
            sys.exit(1)

    # Confirm before live delete
    if not args.dry_run:
        print("\n⚠️  WARNING: This will PERMANENTLY DELETE data!")
        print(f"   Collections: {', '.join(collections_to_process)}")
        confirm = input("\nType 'DELETE' to confirm: ")
        if confirm != 'DELETE':
            print("Aborted.")
            sys.exit(0)

    total_deleted = 0

    for collection_name in collections_to_process:
        print(f"\n📦 Collection: {collection_name}")

        collection_ref = db.collection(collection_name)
        stats = get_collection_stats(db, collection_name)

        print(f"   Documents: {stats['count_note']}")

        if stats['count'] == 0:
            print("   Status: Already empty ✓")
            continue

        if stats['sample']:
            sample_keys = list(stats['sample'].keys())[:5]  # Show first 5 keys
            print(f"   Sample keys: {sample_keys}")

        if args.dry_run:
            print(f"   [DRY RUN] Would delete {stats['count']} documents")
            total_deleted += stats['count']
        else:
            print(f"   Deleting...")
            deleted = delete_collection(db, collection_ref, dry_run=False)
            print(f"   Deleted: {deleted} documents ✓")
            total_deleted += deleted

    print("\n" + "=" * 70)
    print(f"SUMMARY: {'Would delete' if args.dry_run else 'Deleted'} {total_deleted} documents total")

    if args.dry_run:
        print("\n💡 To actually delete, run without --dry-run flag")
    else:
        print("\n✅ Cleanup complete!")
        print("\n⚠️  Next steps:")
        print("   1. Update firestore.indexes.json - remove indexes for deleted collections")
        print("   2. Update firestore.rules - remove rules for deleted collections")
        print("   3. Deploy updated rules: firebase deploy --only firestore:rules")
        print("   4. Deploy updated indexes: firebase deploy --only firestore:indexes")
    print("=" * 70)


if __name__ == '__main__':
    main()
