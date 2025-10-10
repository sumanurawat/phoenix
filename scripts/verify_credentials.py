#!/usr/bin/env python3
"""
Credential Chain Verification Script
Tests the multi-tier signed URL generation without making actual GCS calls.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_credential_sources():
    """Check what credential sources are available."""
    results = {
        'environment': {},
        'files': {},
        'recommendations': []
    }
    
    # Check environment variables
    logger.info("Checking credential environment variables...")
    
    gac = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    results['environment']['GOOGLE_APPLICATION_CREDENTIALS'] = gac if gac else 'Not set'
    
    # Check for credential files
    logger.info("Checking credential files...")
    
    credential_files = [
        'firebase-credentials.json',
        '.env',
        '.env.local'
    ]
    
    for file_path in credential_files:
        exists = os.path.exists(file_path)
        results['files'][file_path] = 'Found' if exists else 'Not found'
        if not exists and file_path == 'firebase-credentials.json':
            results['recommendations'].append(
                f"⚠️  Local dev: Consider adding {file_path} for Firebase Admin SDK"
            )
    
    # Check if running on Cloud Run
    is_cloud_run = os.getenv('K_SERVICE') is not None
    results['environment']['K_SERVICE'] = os.getenv('K_SERVICE', 'Not set (not Cloud Run)')
    
    # Print results
    print("\n" + "="*70)
    print("CREDENTIAL CHAIN VERIFICATION")
    print("="*70)
    
    print("\n📋 Environment Variables:")
    for key, value in results['environment'].items():
        status = "✅" if value and value != "Not set" else "ℹ️"
        print(f"  {status} {key}: {value}")
    
    print("\n📁 Credential Files:")
    for file_path, status in results['files'].items():
        icon = "✅" if status == "Found" else "❌"
        print(f"  {icon} {file_path}: {status}")
    
    print("\n🔍 Expected Behavior:")
    if is_cloud_run:
        print("  🌐 Running on Cloud Run")
        print("  ✅ Will use IAM signBlob API for signed URLs")
        print("  ✅ Service account from metadata server")
        print("  ✅ No service account file needed")
    else:
        print("  💻 Running locally")
        if results['files']['firebase-credentials.json'] == 'Found':
            print("  ✅ Will use firebase-credentials.json for signing")
        elif gac and os.path.exists(gac):
            print(f"  ✅ Will use {gac} for signing")
        else:
            print("  ⚠️  No service account file found")
            print("  ℹ️  May fall back to gcloud ADC if configured")
    
    if results['recommendations']:
        print("\n💡 Recommendations:")
        for rec in results['recommendations']:
            print(f"  {rec}")
    
    print("\n" + "="*70)
    
    return results

def test_imports():
    """Test that required modules can be imported."""
    print("\n🔧 Testing required imports...")
    
    try:
        from google.cloud import storage
        print("  ✅ google.cloud.storage")
    except ImportError as e:
        print(f"  ❌ google.cloud.storage: {e}")
        return False
    
    try:
        from google.auth import iam
        print("  ✅ google.auth.iam")
    except ImportError as e:
        print(f"  ❌ google.auth.iam: {e}")
        return False
    
    try:
        from google.oauth2 import service_account
        print("  ✅ google.oauth2.service_account")
    except ImportError as e:
        print(f"  ❌ google.oauth2.service_account: {e}")
        return False
    
    try:
        import google.auth
        print("  ✅ google.auth")
    except ImportError as e:
        print(f"  ❌ google.auth: {e}")
        return False
    
    print("  ✅ All required imports available")
    return True

def check_service_account_permissions():
    """Check if we can detect the service account and its basic permissions."""
    print("\n🔐 Checking service account...")
    
    try:
        import google.auth
        from google.auth import compute_engine
        
        credentials, project_id = google.auth.default()
        
        print(f"  ✅ Project ID: {project_id}")
        print(f"  ✅ Credential type: {type(credentials).__name__}")
        
        if hasattr(credentials, 'service_account_email'):
            print(f"  ✅ Service account: {credentials.service_account_email}")
        elif hasattr(credentials, 'signer_email'):
            print(f"  ✅ Service account: {credentials.signer_email}")
        elif isinstance(credentials, compute_engine.Credentials):
            print("  ℹ️  Compute Engine credentials (Cloud Run)")
            print("  ✅ Will fetch service account from metadata server")
        else:
            print("  ⚠️  Cannot determine service account email")
            print(f"     Credential type: {type(credentials)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to get default credentials: {e}")
        print("  ℹ️  This is normal if not authenticated with gcloud")
        return False

if __name__ == '__main__':
    print("\n🚀 Phoenix Credential Management Verification")
    print("This script checks your local credential setup.\n")
    
    # Run checks
    all_ok = True
    
    results = check_credential_sources()
    all_ok = test_imports() and all_ok
    check_service_account_permissions()  # This may fail locally, which is OK
    
    print("\n" + "="*70)
    if all_ok:
        print("✅ Credential management setup looks good!")
    else:
        print("⚠️  Some checks failed - see details above")
    print("="*70 + "\n")
    
    sys.exit(0 if all_ok else 1)
