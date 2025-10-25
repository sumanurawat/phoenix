#!/usr/bin/env python3
"""Quick test script to verify R2 upload functionality"""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

def test_r2_connection():
    """Test basic R2 connectivity and upload"""
    print("🔍 Testing Cloudflare R2 Connection...")
    print("=" * 60)
    
    # Get R2 credentials from environment
    access_key_id = os.getenv("R2_ACCESS_KEY_ID")
    secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
    endpoint_url = os.getenv("R2_ENDPOINT_URL")
    bucket_name = os.getenv("R2_BUCKET_NAME")
    public_url = os.getenv("R2_PUBLIC_URL")
    
    # Validate credentials
    if not all([access_key_id, secret_access_key, endpoint_url, bucket_name]):
        print("❌ Missing R2 credentials in .env file")
        print(f"   R2_ACCESS_KEY_ID: {'✓' if access_key_id else '✗'}")
        print(f"   R2_SECRET_ACCESS_KEY: {'✓' if secret_access_key else '✗'}")
        print(f"   R2_ENDPOINT_URL: {'✓' if endpoint_url else '✗'}")
        print(f"   R2_BUCKET_NAME: {'✓' if bucket_name else '✗'}")
        return False
    
    print(f"✅ R2 credentials loaded")
    print(f"   Endpoint: {endpoint_url}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Public URL: {public_url}")
    print()
    
    try:
        # Initialize R2 client
        print("📡 Initializing boto3 S3 client for R2...")
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name='auto'
        )
        print("✅ R2 client initialized")
        print()
        
        # Test upload
        test_key = "test/r2_connection_test.txt"
        test_content = f"R2 connection test - {os.getenv('USER', 'unknown')} - {__file__}"
        
        print(f"📤 Uploading test file: {test_key}")
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain',
            Metadata={
                'test': 'true',
                'uploaded_by': 'test_r2_upload.py'
            }
        )
        print("✅ Upload successful")
        print()
        
        # Construct public URL
        if public_url:
            public_test_url = f"{public_url}/{test_key}"
            print(f"🌐 Public URL: {public_test_url}")
            print()
            print("⚠️  NOTE: Visit the URL above in your browser to verify public access")
        
        print()
        print("=" * 60)
        print("🎉 R2 connection test PASSED!")
        print("=" * 60)
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"❌ R2 ClientError: {error_code} - {error_msg}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_r2_connection()
    sys.exit(0 if success else 1)
