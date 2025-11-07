#!/usr/bin/env python3
"""Quick script to check video creation status"""
import sys
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase if needed
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

creation_id = sys.argv[1] if len(sys.argv) > 1 else "e1acb3be-09a3-4b40-869e-c4f2cc524b80"

doc_ref = db.collection('creations').document(creation_id)
doc = doc_ref.get()

if not doc.exists:
    print(f"❌ Creation {creation_id} not found")
    sys.exit(1)

data = doc.to_dict()
print(f"📋 Creation ID: {creation_id}")
print(f"📊 Status: {data.get('status')}")
print(f"📈 Progress: {data.get('progress', 0.0)}")
print(f"👤 User: {data.get('userId')}")
print(f"💬 Prompt: {data.get('prompt', 'N/A')[:80]}...")
print(f"🕐 Created: {data.get('createdAt')}")
print(f"🔄 Updated: {data.get('updatedAt')}")

if data.get('error'):
    print(f"❌ Error: {data.get('error')}")

if data.get('r2Url'):
    print(f"✅ Video URL: {data.get('r2Url')}")

print(f"\n📝 Full data: {data}")
