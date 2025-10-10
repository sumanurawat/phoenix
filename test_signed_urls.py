#!/usr/bin/env python3
"""
Test script to verify GCS signed URL generation for Reel Maker clips.
"""
import os
from datetime import timedelta
from google.cloud import storage

# Your project details from Firestore
project_id = 'Y9uaCX6yIQOxu882uBhX'
user_id = '7Vd9KHo2rnOG36VjWTa70Z69o4k2'

# Test paths
stitched_path = f'reel-maker/{user_id}/{project_id}/stitched/stitched_{project_id}.mp4'
clip_path = f'reel-maker/{user_id}/{project_id}/raw/reeljob-14a1326d785a/prompt-00/3582064463643695297/sample_0.mp4'

# Get bucket
bucket_name = os.getenv('VIDEO_STORAGE_BUCKET', 'phoenix-videos')
client = storage.Client()
bucket = client.bucket(bucket_name)

print("=" * 80)
print("🎬 Testing GCS Signed URL Generation")
print("=" * 80)

# Test 1: Check if files exist
print("\n1️⃣ Checking if files exist in GCS...")
for path, name in [(stitched_path, "Stitched Video"), (clip_path, "First Clip")]:
    blob = bucket.blob(path)
    exists = blob.exists()
    print(f"   {name}: {'✅ EXISTS' if exists else '❌ NOT FOUND'}")
    if exists:
        blob.reload()
        print(f"      Size: {blob.size / (1024*1024):.2f} MB")

# Test 2: Generate signed URLs
print("\n2️⃣ Generating signed URLs...")
for path, name in [(stitched_path, "Stitched Video"), (clip_path, "First Clip")]:
    blob = bucket.blob(path)
    if blob.exists():
        try:
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=2),
                method="GET",
                response_type="video/mp4"
            )
            print(f"\n   {name}:")
            print(f"   ✅ Signed URL generated successfully")
            print(f"   🔗 URL: {signed_url[:100]}...")
            print(f"   ⏱️  Expires in: 2 hours")
        except Exception as e:
            print(f"   ❌ Failed to generate signed URL: {e}")

# Test 3: Check permissions
print("\n3️⃣ Checking bucket permissions...")
try:
    # Try to get bucket metadata
    bucket.reload()
    print(f"   ✅ Bucket access: OK")
    print(f"   📦 Bucket: {bucket.name}")
    print(f"   🌍 Location: {bucket.location}")
except Exception as e:
    print(f"   ❌ Permission error: {e}")

print("\n" + "=" * 80)
print("✅ Test Complete!")
print("=" * 80)
print("\nNext steps:")
print("1. Deploy the updated code to Cloud Run")
print("2. Open your 'learn 5' project in Reel Maker")
print("3. Videos should now load via signed URLs!")
print("=" * 80)
