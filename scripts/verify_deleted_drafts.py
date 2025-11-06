#!/usr/bin/env python3
"""
Verify Deleted Drafts Script

This script checks if a specific creation ID exists in Firestore.
Useful for confirming deletions actually removed the document.

Usage:
    python scripts/verify_deleted_drafts.py <creation_id>
    python scripts/verify_deleted_drafts.py 614d3d77-ebd7-4308-aeb9-c47484491f51
"""

import sys
import os

# Add parent directory to path to import Firebase setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

def init_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firestore.client()

def check_creation_exists(creation_id):
    """Check if a creation exists in Firestore"""
    db = init_firebase()
    
    try:
        doc_ref = db.collection('creations').document(creation_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            print(f"❌ STILL EXISTS: Creation {creation_id}")
            print(f"   Status: {data.get('status')}")
            print(f"   User ID: {data.get('userId')}")
            print(f"   Prompt: {data.get('prompt', 'N/A')[:60]}...")
            print(f"   Created: {data.get('createdAt')}")
            print("\n⚠️  The document was NOT deleted from Firestore!")
            return True
        else:
            print(f"✅ CONFIRMED DELETED: Creation {creation_id}")
            print(f"   The document does not exist in Firestore.")
            return False
            
    except Exception as e:
        print(f"❌ ERROR checking creation {creation_id}: {e}")
        return None

def list_user_drafts(user_id, status_filter=None):
    """List all drafts for a user (useful for seeing what's left)"""
    db = init_firebase()
    
    try:
        query = db.collection('creations').where('userId', '==', user_id)
        
        if status_filter:
            query = query.where('status', '==', status_filter)
        
        docs = list(query.stream())
        
        print(f"\n📋 User {user_id} has {len(docs)} creations")
        if status_filter:
            print(f"   (filtered by status: {status_filter})")
        
        # Group by status
        by_status = {}
        for doc in docs:
            data = doc.to_dict()
            status = data.get('status', 'unknown')
            if status not in by_status:
                by_status[status] = []
            by_status[status].append({
                'id': doc.id,
                'prompt': data.get('prompt', 'N/A')[:40],
                'createdAt': data.get('createdAt'),
                'mediaType': data.get('mediaType', 'unknown')
            })
        
        # Print summary
        for status, items in sorted(by_status.items()):
            print(f"\n   {status.upper()}: {len(items)} creations")
            for item in items[:5]:  # Show first 5 of each status
                print(f"      • {item['id'][:20]}... | {item['mediaType']} | {item['prompt']}")
            if len(items) > 5:
                print(f"      ... and {len(items) - 5} more")
        
        return docs
        
    except Exception as e:
        print(f"❌ ERROR listing drafts: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_deleted_drafts.py <creation_id>")
        print("\nOr to list all creations for a user:")
        print("Usage: python scripts/verify_deleted_drafts.py --user <user_id>")
        print("\nExample:")
        print("  python scripts/verify_deleted_drafts.py 614d3d77-ebd7-4308-aeb9-c47484491f51")
        print("  python scripts/verify_deleted_drafts.py --user 7Vd9KHo2rnOG36VjWTa70Z69o4k2")
        sys.exit(1)
    
    if sys.argv[1] == '--user':
        if len(sys.argv) < 3:
            print("❌ Please provide user ID")
            sys.exit(1)
        user_id = sys.argv[2]
        status_filter = sys.argv[3] if len(sys.argv) > 3 else None
        list_user_drafts(user_id, status_filter)
    else:
        creation_id = sys.argv[1]
        check_creation_exists(creation_id)

if __name__ == '__main__':
    main()
