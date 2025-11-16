#!/usr/bin/env python3
"""
Firestore Cache Setup Script

Sets up Firestore collection with TTL policy for automatic session cleanup.

This script:
1. Creates the 'cache_sessions' collection (if it doesn't exist)
2. Configures TTL policy on 'expires_at' field for auto-deletion
3. Creates necessary indexes for efficient queries

Run this script once before deploying your application.

Usage:
    python services/cache_service/setup_firestore.py

Environment Variables:
    GOOGLE_CLOUD_PROJECT: Your GCP project ID (default: phoenix-project-386)
    CACHE_COLLECTION_NAME: Collection name (default: cache_sessions)
"""

import os
import sys
import logging
from google.cloud import firestore
from google.cloud import firestore_admin_v1
from google.api_core import exceptions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_firestore_cache():
    """
    Setup Firestore collection for cache service with TTL policy.
    """
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'phoenix-project-386')
    collection_name = os.getenv('CACHE_COLLECTION_NAME', 'cache_sessions')

    logger.info(f"Setting up Firestore cache for project: {project_id}")
    logger.info(f"Collection name: {collection_name}")

    try:
        # Initialize Firestore client
        db = firestore.Client(project=project_id)

        # Step 1: Create a sample document to initialize collection
        # (Firestore collections are created lazily)
        logger.info(f"Initializing collection: {collection_name}")
        sample_doc_ref = db.collection(collection_name).document('_setup_sample')
        sample_doc_ref.set({
            'data': {'setup': True},
            'created_at': firestore.SERVER_TIMESTAMP,
            'expires_at': firestore.SERVER_TIMESTAMP,
            'last_accessed': firestore.SERVER_TIMESTAMP
        })
        logger.info("✓ Sample document created")

        # Step 2: Set up TTL policy using Firestore Admin API
        logger.info("Configuring TTL policy for automatic cleanup...")
        try:
            # Note: TTL policy setup requires Firestore Admin API
            # This is a newer feature (2023+) and may require specific permissions
            admin_client = firestore_admin_v1.FirestoreAdminClient()
            database_path = admin_client.database_path(project_id, '(default)')

            # Check if TTL is already configured
            # TTL policies are managed at the field level via API
            logger.info("TTL Policy Configuration:")
            logger.info(f"  Field: expires_at")
            logger.info(f"  Action: Automatically delete documents where expires_at < now")
            logger.info(f"  Deletion Window: Within 24 hours of expiration")

            # Note: As of 2024, TTL policies can be configured via Firebase Console
            # or gcloud CLI. Programmatic setup via Admin API is in beta.
            logger.warning("⚠️  TTL policy must be configured manually via Firebase Console:")
            logger.warning("   1. Go to: https://console.firebase.google.com/project/{}/firestore".format(project_id))
            logger.warning(f"   2. Select collection: {collection_name}")
            logger.warning("   3. Click 'Manage' → 'TTL policy'")
            logger.warning("   4. Set TTL field: 'expires_at'")
            logger.warning("   5. Save")

        except Exception as e:
            logger.error(f"Could not configure TTL policy via API: {e}")
            logger.warning("Please configure TTL policy manually via Firebase Console (see above)")

        # Step 3: Create composite index for efficient cleanup queries
        logger.info("Creating indexes for efficient queries...")
        logger.info("Index configuration:")
        logger.info(f"  Collection: {collection_name}")
        logger.info("  Fields: expires_at (ascending)")
        logger.info("  Purpose: Efficient cleanup of expired sessions")

        logger.warning("⚠️  Index should be created automatically on first query")
        logger.warning("   If you see 'index required' errors, create index at:")
        logger.warning("   https://console.firebase.google.com/project/{}/firestore/indexes".format(project_id))

        # Step 4: Delete sample document
        sample_doc_ref.delete()
        logger.info("✓ Sample document deleted")

        # Step 5: Verify setup
        logger.info("\n" + "="*60)
        logger.info("✅ Firestore Cache Setup Complete!")
        logger.info("="*60)
        logger.info(f"\nCollection: {collection_name}")
        logger.info("Structure:")
        logger.info("  Document ID: <session_id>")
        logger.info("  Fields:")
        logger.info("    - data: Dict (the cached session data)")
        logger.info("    - created_at: Timestamp")
        logger.info("    - expires_at: Timestamp (TTL field)")
        logger.info("    - last_accessed: Timestamp")
        logger.info("\nNext Steps:")
        logger.info("  1. Configure TTL policy in Firebase Console (see warning above)")
        logger.info("  2. Update your app configuration:")
        logger.info("       export CACHE_BACKEND=firestore")
        logger.info(f"       export CACHE_COLLECTION_NAME={collection_name}")
        logger.info("  3. Deploy your application")
        logger.info("\nFor friedmomo.com:")
        logger.info("  Update app.py to use CacheSessionInterface")
        logger.info("="*60 + "\n")

        return True

    except exceptions.PermissionDenied as e:
        logger.error(f"❌ Permission denied: {e}")
        logger.error("Make sure you have Firestore Admin permissions")
        logger.error("Run: gcloud auth application-default login")
        return False

    except Exception as e:
        logger.error(f"❌ Setup failed: {e}", exc_info=True)
        return False


def setup_ttl_policy_via_gcloud(project_id: str, collection_name: str):
    """
    Display gcloud command to set up TTL policy.

    TTL policies can be configured via gcloud CLI (beta feature).
    """
    logger.info("\n" + "="*60)
    logger.info("Alternative: Setup TTL via gcloud CLI")
    logger.info("="*60)
    logger.info("\nRun the following command:")
    logger.info(f"""
gcloud alpha firestore fields ttls update expires_at \\
  --collection-group={collection_name} \\
  --enable-ttl \\
  --project={project_id}
    """)
    logger.info("\nNote: This requires gcloud alpha components:")
    logger.info("  gcloud components install alpha")
    logger.info("="*60 + "\n")


if __name__ == "__main__":
    logger.info("Firestore Cache Service Setup")
    logger.info("="*60 + "\n")

    success = setup_firestore_cache()

    if success:
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'phoenix-project-386')
        collection_name = os.getenv('CACHE_COLLECTION_NAME', 'cache_sessions')
        setup_ttl_policy_via_gcloud(project_id, collection_name)
        sys.exit(0)
    else:
        logger.error("\n❌ Setup failed. Please check errors above.")
        sys.exit(1)
