#!/usr/bin/env python3
"""Phase 3 Deployment Verification Script

Verifies that all Phase 3 components are correctly configured before deployment.
"""
import os
import sys
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description} MISSING: {file_path}")
        return False

def check_import(module_name: str, description: str) -> bool:
    """Check if a Python module can be imported."""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description} IMPORT FAILED: {module_name}")
        print(f"   Error: {e}")
        return False

def check_env_var(var_name: str, description: str, required: bool = True) -> bool:
    """Check if an environment variable is set."""
    value = os.getenv(var_name)
    if value:
        # Mask sensitive values
        if any(secret in var_name.lower() for secret in ['key', 'secret', 'password']):
            display_value = f"{value[:10]}..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"✅ {description}: {display_value}")
        return True
    else:
        status = "❌ REQUIRED" if required else "⚠️  OPTIONAL"
        print(f"{status} {description}: {var_name} not set")
        return not required

def main():
    print("=" * 80)
    print("Phase 3: Async Video Generation - Deployment Verification")
    print("=" * 80)
    print()

    all_checks_passed = True

    # Check core files
    print("📁 Checking Phase 3 Files...")
    print("-" * 80)
    all_checks_passed &= check_file_exists("celery_app.py", "Celery app configuration")
    all_checks_passed &= check_file_exists("api/video_generation_routes.py", "Video generation API routes")
    all_checks_passed &= check_file_exists("jobs/async_video_generation_worker.py", "Async video worker")
    all_checks_passed &= check_file_exists("infrastructure/gcp/redis-memorystore.sh", "Redis provisioning script")
    all_checks_passed &= check_file_exists("firestore.rules", "Firestore security rules")
    print()

    # Check Python imports
    print("🐍 Checking Python Dependencies...")
    print("-" * 80)
    all_checks_passed &= check_import("celery", "Celery (task queue)")
    all_checks_passed &= check_import("redis", "Redis (broker)")
    all_checks_passed &= check_import("flask", "Flask (web framework)")
    all_checks_passed &= check_import("firebase_admin", "Firebase Admin SDK")
    all_checks_passed &= check_import("boto3", "Boto3 (R2 storage)")
    all_checks_passed &= check_import("google.cloud.storage", "Google Cloud Storage")
    print()

    # Check environment variables
    print("🔧 Checking Environment Variables...")
    print("-" * 80)
    all_checks_passed &= check_env_var("REDIS_HOST", "Redis host", required=False)
    all_checks_passed &= check_env_var("REDIS_PORT", "Redis port", required=False)
    all_checks_passed &= check_env_var("R2_ACCESS_KEY_ID", "R2 access key", required=True)
    all_checks_passed &= check_env_var("R2_SECRET_ACCESS_KEY", "R2 secret key", required=True)
    all_checks_passed &= check_env_var("R2_ENDPOINT_URL", "R2 endpoint URL", required=True)
    all_checks_passed &= check_env_var("R2_BUCKET_NAME", "R2 bucket name", required=True)
    all_checks_passed &= check_env_var("R2_PUBLIC_URL", "R2 public URL", required=True)
    all_checks_passed &= check_env_var("GOOGLE_CLOUD_PROJECT", "GCP project ID", required=True)
    print()

    # Check configuration
    print("⚙️  Checking Flask Configuration...")
    print("-" * 80)
    try:
        from app import create_app
        app = create_app()

        # Check if video_generation_bp is registered
        blueprints = [bp.name for bp in app.blueprints.values()]
        if 'video_generation' in blueprints:
            print("✅ Video generation blueprint registered")
        else:
            print("❌ Video generation blueprint NOT registered")
            all_checks_passed = False

        # Check if celery_app is importable from Flask context
        try:
            from celery_app import celery_app
            print("✅ Celery app importable")

            # Check Celery configuration
            if 'jobs.async_video_generation_worker' in celery_app.conf.include:
                print("✅ Worker module included in Celery")
            else:
                print("❌ Worker module NOT included in Celery")
                all_checks_passed = False

        except ImportError as e:
            print(f"❌ Celery app import failed: {e}")
            all_checks_passed = False

    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        all_checks_passed = False
    print()

    # Check Firestore rules
    print("🔐 Checking Firestore Rules...")
    print("-" * 80)
    with open('firestore.rules', 'r') as f:
        rules_content = f.read()
        if 'match /creations/{creationId}' in rules_content:
            print("✅ Creations collection rules defined")
        else:
            print("❌ Creations collection rules MISSING")
            all_checks_passed = False
    print()

    # Final summary
    print("=" * 80)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Ready for deployment!")
        print()
        print("Next steps:")
        print("  1. Provision Redis: ./infrastructure/gcp/redis-memorystore.sh")
        print("  2. Store Redis credentials in Secret Manager")
        print("  3. Update cloudbuild.yaml with worker service")
        print("  4. Deploy: gcloud builds submit --config cloudbuild.yaml .")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Fix issues before deployment")
        print()
        print("Review the errors above and:")
        print("  - Install missing dependencies: pip install -r requirements.txt")
        print("  - Set missing environment variables in .env")
        print("  - Verify all files are created")
        return 1

if __name__ == "__main__":
    sys.exit(main())
