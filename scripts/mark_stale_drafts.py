#!/usr/bin/env python3
"""
Mark Stale Drafts as Failed

This script finds creations that have been stuck in 'pending' or 'processing' 
status for too long and marks them as 'failed' with appropriate error messages.

Usage:
    python scripts/mark_stale_drafts.py [--dry-run] [--max-age-hours HOURS]
    
Examples:
    # Preview what would be marked as failed (no changes)
    python scripts/mark_stale_drafts.py --dry-run
    
    # Mark drafts older than 1 hour as failed
    python scripts/mark_stale_drafts.py --max-age-hours 1
    
    # Mark drafts older than 24 hours as failed (default)
    python scripts/mark_stale_drafts.py
"""

import sys
import os
import argparse
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firestore.client()

def mark_stale_drafts(dry_run=False, max_age_hours=24):
    """
    Find and mark stale drafts as failed
    
    Args:
        dry_run (bool): If True, only print what would be done without making changes
        max_age_hours (int): Maximum age in hours before marking as stale
    """
    db = init_firebase()
    
    print(f"{'🔍 DRY RUN MODE' if dry_run else '🔧 PROCESSING'}: Finding stale drafts...")
    print(f"⏰ Max age: {max_age_hours} hours\n")
    
    # Calculate cutoff time
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    print(f"📅 Cutoff time: {cutoff_time.isoformat()}")
    print(f"   (Any creation older than this will be marked as failed)\n")
    
    # Query for pending creations
    pending_query = db.collection('creations').where('status', '==', 'pending')
    pending_docs = list(pending_query.stream())
    
    # Query for processing creations
    processing_query = db.collection('creations').where('status', '==', 'processing')
    processing_docs = list(processing_query.stream())
    
    all_stale_docs = pending_docs + processing_docs
    
    print(f"📊 Found {len(pending_docs)} pending and {len(processing_docs)} processing creations\n")
    
    stale_count = 0
    updated_count = 0
    
    for doc in all_stale_docs:
        data = doc.to_dict()
        creation_id = doc.id
        status = data.get('status')
        created_at = data.get('createdAt')
        prompt = data.get('prompt', 'N/A')[:50]
        
        # Parse createdAt timestamp
        if isinstance(created_at, datetime):
            created_time = created_at
        elif hasattr(created_at, 'seconds'):
            # Firestore Timestamp
            created_time = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
        else:
            print(f"⚠️  Skipping {creation_id}: Invalid createdAt format")
            continue
        
        # Check if stale
        age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            stale_count += 1
            print(f"🔴 STALE: {creation_id}")
            print(f"   Status: {status}")
            print(f"   Age: {age_hours:.1f} hours ({age_hours/24:.1f} days)")
            print(f"   Prompt: {prompt}...")
            print(f"   Created: {created_time.isoformat()}")
            
            if not dry_run:
                # Update to failed status
                try:
                    doc.reference.update({
                        'status': 'failed',
                        'error': f'Generation timeout: Task stuck in {status} status for {age_hours:.1f} hours',
                        'failedAt': datetime.now(timezone.utc),
                        'updatedAt': datetime.now(timezone.utc)
                    })
                    print(f"   ✅ Marked as failed")
                    updated_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to update: {e}")
            else:
                print(f"   🔄 Would mark as failed (dry run)")
            
            print()
    
    print("\n" + "="*60)
    print(f"📋 Summary:")
    print(f"   Total checked: {len(all_stale_docs)}")
    print(f"   Stale found: {stale_count}")
    
    if dry_run:
        print(f"   Would update: {stale_count}")
        print(f"\n💡 Run without --dry-run to actually update these drafts")
    else:
        print(f"   Updated: {updated_count}")
        print(f"   Failed to update: {stale_count - updated_count}")
    
    print("="*60)
    
    return stale_count, updated_count

def main():
    parser = argparse.ArgumentParser(
        description='Mark stale drafts as failed',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without making them
  python scripts/mark_stale_drafts.py --dry-run
  
  # Mark drafts older than 1 hour as failed
  python scripts/mark_stale_drafts.py --max-age-hours 1
  
  # Mark drafts older than 24 hours as failed (default)
  python scripts/mark_stale_drafts.py
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without actually updating documents'
    )
    
    parser.add_argument(
        '--max-age-hours',
        type=float,
        default=24,
        help='Maximum age in hours before marking as stale (default: 24)'
    )
    
    args = parser.parse_args()
    
    stale_count, updated_count = mark_stale_drafts(
        dry_run=args.dry_run,
        max_age_hours=args.max_age_hours
    )
    
    if stale_count > 0 and args.dry_run:
        sys.exit(1)  # Exit with error code to indicate action needed
    
    sys.exit(0)

if __name__ == '__main__':
    main()
