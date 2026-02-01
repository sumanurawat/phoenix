# Task: Firestore Collection Cleanup

## Overview

This document provides instructions for auditing and cleaning up unused Firestore collections in the friedmomo.com (Phoenix) project. The goal is to remove legacy/orphaned collections that are no longer used by the application.

---

## Background

The friedmomo.com platform has evolved over time, with features being added and removed. As a result, some Firestore collections exist in the database that are no longer referenced by the codebase. These orphaned collections:

1. Increase storage costs (even if minimal)
2. Create confusion during debugging
3. May contain stale/sensitive data
4. Clutter the Firebase Console

---

## Current Collections Audit

Based on analysis of the Firebase Console and codebase search, here is the status of all collections:

### ACTIVELY USED COLLECTIONS (DO NOT DELETE)

| Collection | Purpose | Used By |
|------------|---------|---------|
| `users` | User profiles, token balances, settings | `token_service.py`, `auth_routes.py`, `creation_service.py`, `stripe_service.py` |
| `usernames` | Username reservation/lookup | `account_deletion_service.py`, `feed_routes.py` |
| `creations` | User-generated images/videos | `creation_service.py`, `feed_routes.py`, `image_routes.py` |
| `transactions` | Token purchase/spend history | `token_security_service.py`, `creation_service.py`, `stripe_service.py` |
| `user_subscriptions` | Stripe subscription records | `stripe_service.py`, `account_deletion_service.py` |
| `user_social_accounts` | Connected social media accounts | `socials_service.py` |
| `cache_sessions` | Flask session storage | `flask_adapter.py`, `account_deletion_service.py` |
| `rate_limits` | API rate limiting records | `limiter_storage.py` (new) |
| `security_alerts` | Token security violation alerts | `token_security_service.py` |
| `website_stats` | Global site statistics | `website_stats_service.py` |

### LEGACY COLLECTIONS (SAFE TO DELETE)

| Collection | Original Purpose | Why Delete |
|------------|-----------------|------------|
| `link_clicks` | Click tracking for shortened URLs | Feature removed; `click_tracking_service.py` was deleted |
| `shortened_links` | URL shortener data | Feature removed; only referenced in `website_stats_service.py` for migration but not actively used |
| `deepface_jobs` | Face analysis AI jobs | Feature removed; DeepFace routes/service deleted |
| `video_generations` | Old video generation tracking | Replaced by `creations` collection; no code references this |
| `conversations` | AI chat conversations | Chat feature removed; only Firestore rules/indexes reference it |
| `messages` | AI chat messages | Chat feature removed; only Firestore rules/indexes reference it |
| `reel_jobs` | Reel Maker job tracking | Feature deprecated; replaced by Cloud Run Jobs using `creations` |
| `reel_job_checkpoints` | Reel Maker checkpoints | Feature deprecated; only docs reference it |
| `reel_maker_jobs` | Duplicate reel job tracking | Appears to be duplicate of `reel_jobs`; no code references |
| `reel_maker_projects` | Reel Maker project data | Feature deprecated; no code references |

---

## Deletion Instructions

### Pre-Deletion Checklist

Before deleting any collection:

1. **Backup the data** (if it might be needed for reference)
2. **Verify no code references** exist by running:
   ```bash
   grep -r "collection_name" --include="*.py" --include="*.js" --include="*.ts"
   ```
3. **Check Firestore rules** for any references
4. **Check Firestore indexes** for any indexes on the collection

### Step-by-Step Deletion Process

#### Option A: Manual Deletion via Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project: `sumanurawat-phoenix`
3. Navigate to **Firestore Database**
4. For each collection to delete:
   - Click on the collection name
   - Click the **three dots** menu (⋮) next to the collection name
   - Select **Delete collection**
   - Type the collection name to confirm
   - Click **Delete**

#### Option B: Script-Based Deletion (Recommended for large collections)

Create and run this script to delete collections safely:

```python
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
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Collections marked for deletion
COLLECTIONS_TO_DELETE = [
    'link_clicks',
    'shortened_links',
    'deepface_jobs',
    'video_generations',
    'conversations',
    'messages',
    'reel_jobs',
    'reel_job_checkpoints',
    'reel_maker_jobs',
    'reel_maker_projects',
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
        # Truncate large fields
        for key, value in sample.items():
            if isinstance(value, str) and len(value) > 100:
                sample[key] = value[:100] + '...'

    return {
        'count': count,
        'count_note': '1000+' if count == 1000 else str(count),
        'sample': sample
    }


def main():
    parser = argparse.ArgumentParser(description='Clean up unused Firestore collections')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without deleting')
    args = parser.parse_args()

    # Initialize Firebase
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    db = firestore.client()

    print("=" * 60)
    print("FIRESTORE COLLECTION CLEANUP")
    print(f"Mode: {'DRY RUN (no changes)' if args.dry_run else 'LIVE DELETE'}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    # Safety check
    for collection_name in COLLECTIONS_TO_DELETE:
        if collection_name in PROTECTED_COLLECTIONS:
            print(f"\n❌ ERROR: '{collection_name}' is in PROTECTED_COLLECTIONS!")
            print("   Remove it from COLLECTIONS_TO_DELETE or review the protection list.")
            return

    total_deleted = 0

    for collection_name in COLLECTIONS_TO_DELETE:
        print(f"\n📦 Collection: {collection_name}")

        collection_ref = db.collection(collection_name)
        stats = get_collection_stats(db, collection_name)

        print(f"   Documents: {stats['count_note']}")

        if stats['count'] == 0:
            print("   Status: Already empty ✓")
            continue

        if stats['sample']:
            print(f"   Sample keys: {list(stats['sample'].keys())}")

        if args.dry_run:
            print(f"   [DRY RUN] Would delete {stats['count']} documents")
            total_deleted += stats['count']
        else:
            print(f"   Deleting...")
            deleted = delete_collection(db, collection_ref, dry_run=False)
            print(f"   Deleted: {deleted} documents ✓")
            total_deleted += deleted

    print("\n" + "=" * 60)
    print(f"SUMMARY: {'Would delete' if args.dry_run else 'Deleted'} {total_deleted} documents total")

    if args.dry_run:
        print("\nTo actually delete, run without --dry-run flag")
    else:
        print("\n⚠️  Remember to also:")
        print("   1. Clean up Firestore indexes for deleted collections")
        print("   2. Clean up Firestore rules for deleted collections")
    print("=" * 60)


if __name__ == '__main__':
    main()
```

### Post-Deletion Cleanup

After deleting collections, also clean up:

#### 1. Firestore Indexes (`firestore.indexes.json`)

Remove these index entries for deleted collections:

```json
// DELETE these index blocks:
{
  "collectionGroup": "conversations",
  ...
},
{
  "collectionGroup": "messages",
  ...
},
{
  "collectionGroup": "reel_jobs",
  ...
}
```

#### 2. Firestore Rules (`firestore.rules`)

Remove these rule blocks for deleted collections:

```
// DELETE these rule sections:

// Specific rules for chat conversations
match /conversations/{conversationId} { ... }

// Specific rules for chat messages
match /messages/{messageId} { ... }

// Any references to: link_clicks, shortened_links, deepface_jobs, etc.
```

#### 3. Documentation References

Update these docs that reference deleted collections:
- `docs/CLOUD_RUN_JOBS_ARCHITECTURE.md` - References `reel_jobs`, `reel_job_checkpoints`
- `docs/social_gallery/CREATOR_PORTFOLIO_VISION.md` - References `link_clicks`
- `docs/ai-agents/system-overview.md` - References `conversations`

---

## Verification

After cleanup, verify:

1. **Application works normally**
   ```bash
   # Run local server
   ./start_local.sh

   # Test key flows:
   # - User login
   # - Image generation
   # - Video generation
   # - Token operations
   # - Feed viewing
   ```

2. **No console errors** in Firebase Console

3. **Run the script in dry-run mode** to confirm nothing unexpected:
   ```bash
   python scripts/cleanup_firestore_collections.py --dry-run
   # Should show "Already empty" for all deleted collections
   ```

---

## Rollback Plan

If something goes wrong:

1. **Collections cannot be restored** once deleted (unless you have a backup)
2. **Firestore has no recycle bin** - deletions are permanent
3. **If you backed up data**, you can re-import using:
   ```bash
   gcloud firestore import gs://your-bucket/backup-name
   ```

---

## Future Prevention

To prevent orphaned collections in the future:

1. **Always update docs** when removing features
2. **Delete collections** as part of feature removal PR
3. **Run periodic audits** (quarterly) to check for unused collections
4. **Add collection names to service docstrings** so grep can find them

---

## Summary

| Action | Collections |
|--------|-------------|
| **KEEP** (10) | users, usernames, creations, transactions, user_subscriptions, user_social_accounts, cache_sessions, rate_limits, security_alerts, website_stats |
| **DELETE** (10) | link_clicks, shortened_links, deepface_jobs, video_generations, conversations, messages, reel_jobs, reel_job_checkpoints, reel_maker_jobs, reel_maker_projects |

**Estimated storage savings**: Minimal (collections are likely small), but improves maintainability significantly.

---

## Approval

- [ ] Reviewed collection list for accuracy
- [ ] Confirmed no active code uses deleted collections
- [ ] Created backup of important data (if any)
- [ ] Ready to execute cleanup

**Approved by**: _________________ **Date**: _________________
