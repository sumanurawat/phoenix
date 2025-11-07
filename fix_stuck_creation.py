#!/usr/bin/env python3
"""
Quick script to manually mark a stuck creation as failed in Firestore.
"""
import os
import sys
from google.cloud import firestore
from datetime import datetime, timezone

# Initialize Firestore
db = firestore.Client()

def fix_stuck_creation(creation_id: str):
    """Mark a stuck creation as failed."""
    try:
        creation_ref = db.collection('creations').document(creation_id)
        creation_doc = creation_ref.get()

        if not creation_doc.exists:
            print(f"❌ Creation {creation_id} not found")
            return False

        data = creation_doc.to_dict()
        print(f"📋 Current status: {data.get('status')}")
        print(f"📋 Created at: {data.get('createdAt')}")
        print(f"📋 User ID: {data.get('userId')}")
        print(f"📋 Prompt: {data.get('prompt', 'N/A')[:100]}")

        # Update to failed status
        creation_ref.update({
            'status': 'failed',
            'errorMessage': 'Generation timeout: manually marked as failed after being stuck',
            'completedAt': datetime.now(timezone.utc)
        })

        print(f"✅ Successfully marked creation {creation_id} as failed")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_stuck_creation.py <creation_id>")
        sys.exit(1)

    creation_id = sys.argv[1]
    success = fix_stuck_creation(creation_id)
    sys.exit(0 if success else 1)
