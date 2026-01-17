"""
Account Deletion Service
========================

Comprehensive, production-quality service for complete account deletion.
Ensures ALL user artifacts are removed from the system to:
- Free cloud resources (storage, database documents)
- Comply with GDPR/privacy regulations (right to deletion)
- Allow username reuse after deletion

Architecture:
- Each cleanup function is modular and handles one artifact type
- Functions are idempotent (safe to run multiple times)
- Detailed logging for audit trail and debugging
- Fail-safe: continues cleanup even if one step fails
- Returns comprehensive summary of what was deleted

Collections Cleaned:
--------------------
1. users           - Main user document (contains profile, tokenBalance, etc.)
2. usernames       - Username claim (releases username for reuse)
3. creations       - All images/videos with comments subcollection
4. transactions    - Complete transaction/ledger history
5. user_subscriptions - Stripe subscription records
6. user_usage      - Daily usage tracking records
7. user_social_accounts - Connected social media accounts
8. social_posts    - Synced social media posts
9. oauth_states    - OAuth temporary tokens
10. cache_sessions - Flask session data
11. security_alerts - Rate limit and security event logs
12. image_generations - Legacy image generation history (from /api/image)

External Resources Cleaned:
---------------------------
1. Cloudflare R2   - All images and videos in storage bucket
2. Stripe API      - Customer record (cascades to subscriptions)
3. Firebase Auth   - Auth user record (frees email for reuse)

Usage:
------
    from services.account_deletion_service import get_deletion_service

    # Delete account via API
    service = get_deletion_service()
    result = service.delete_account(user_id="firebase_uid_here")

    # Admin script usage
    result = service.delete_account(user_id, admin_initiated=True)

Author: Friedmomo Engineering
Version: 2.0.0 (Production)
"""
from __future__ import annotations

import os
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from urllib.parse import urlparse

import stripe
from firebase_admin import firestore, auth as firebase_auth
from google.cloud.firestore_v1.base_query import FieldFilter

# R2/S3 client (lazy import to avoid startup cost if not needed)
_s3_client = None

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS
# =============================================================================

class AccountDeletionError(Exception):
    """Base exception for account deletion failures."""
    pass


class UserNotFoundError(AccountDeletionError):
    """Raised when the user to delete does not exist."""
    pass


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class AccountDeletionService:
    """
    Production service for complete account deletion.

    This service orchestrates the deletion of ALL user artifacts across:
    - Firestore collections (10+ collections)
    - Cloudflare R2 storage (images, videos)
    - Stripe customer records

    Design Principles:
    ------------------
    1. MODULAR: Each artifact type has its own cleanup function
    2. IDEMPOTENT: Safe to run multiple times without side effects
    3. FAIL-SAFE: Continues cleanup even if individual steps fail
    4. AUDITABLE: Comprehensive logging for debugging and compliance
    5. COMPLETE: Deletes EVERYTHING - no orphaned data
    """

    # Batch size for Firestore operations (max 500 per batch)
    BATCH_SIZE = 500

    def __init__(self, db=None):
        """
        Initialize the account deletion service.

        Args:
            db: Firestore client instance. If None, creates a new client.
        """
        self.db = db or firestore.client()

        # Initialize Stripe if configured
        self.stripe_configured = bool(os.getenv('STRIPE_SECRET_KEY'))
        if self.stripe_configured:
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

        # R2 configuration (lazy-loaded when needed)
        self.r2_bucket = os.getenv('R2_BUCKET_NAME', 'ai-image-posts-prod')
        self.r2_public_url = os.getenv('R2_PUBLIC_URL', '')

        logger.info(
            f"AccountDeletionService initialized | "
            f"Stripe: {'enabled' if self.stripe_configured else 'disabled'} | "
            f"R2 Bucket: {self.r2_bucket}"
        )

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    def delete_account(
        self,
        user_id: str,
        admin_initiated: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a user account and ALL associated data.

        This is the main entry point for account deletion. It orchestrates
        cleanup across all services and storage systems.

        Args:
            user_id: Firebase Auth UID of the account to delete
            admin_initiated: True if triggered by admin (for audit logging)

        Returns:
            Comprehensive deletion summary:
            {
                'success': bool,
                'user_id': str,
                'username': str | None,
                'deleted_at': ISO timestamp,
                'duration_ms': int,
                'cleanup_summary': {
                    'firestore': {...},  # Document counts per collection
                    'storage': {...},    # File counts per storage type
                    'external': {...}    # External API cleanup status
                },
                'errors': List[str]  # Any errors encountered
            }

        Raises:
            ValueError: If user_id is empty
            UserNotFoundError: If user does not exist (optional - see code)
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")

        user_id = user_id.strip()
        start_time = datetime.now(timezone.utc)

        # Initialize tracking
        errors: List[str] = []
        cleanup_summary = {
            'firestore': {},
            'storage': {},
            'external': {}
        }

        initiator = "ADMIN" if admin_initiated else "USER"
        logger.warning(
            f"{'='*60}\n"
            f"🗑️  ACCOUNT DELETION STARTED\n"
            f"{'='*60}\n"
            f"   User ID: {user_id}\n"
            f"   Initiated by: {initiator}\n"
            f"   Timestamp: {start_time.isoformat()}\n"
            f"{'='*60}"
        )

        # ---------------------------------------------------------------------
        # STEP 1: Get user data for context (username, stripe_customer_id)
        # ---------------------------------------------------------------------
        username = None
        stripe_customer_id = None

        try:
            user_data = self._get_user_data(user_id)
            if user_data:
                username = user_data.get('username')
                stripe_customer_id = user_data.get('stripe_customer_id')
                logger.info(
                    f"📋 User found: @{username or 'no-username'} | "
                    f"Stripe: {stripe_customer_id or 'none'}"
                )
            else:
                logger.warning(f"⚠️  User document not found for {user_id}")
        except Exception as e:
            errors.append(f"Failed to get user data: {e}")
            logger.error(f"❌ Error getting user data: {e}")

        # ---------------------------------------------------------------------
        # STEP 2: Delete creations (images/videos) and their comments
        # Also collects media URLs for R2 cleanup
        # ---------------------------------------------------------------------
        try:
            count, media_urls = self._delete_user_creations_with_media(user_id)
            cleanup_summary['firestore']['creations'] = count
            cleanup_summary['firestore']['creation_comments'] = 'included'
            logger.info(f"✅ Deleted {count} creations (with comments)")
        except Exception as e:
            media_urls = []
            errors.append(f"Failed to delete creations: {e}")
            logger.error(f"❌ Error deleting creations: {e}")

        # ---------------------------------------------------------------------
        # STEP 3: Delete R2 media files (images/videos)
        # ---------------------------------------------------------------------
        try:
            r2_count = self._delete_r2_media_files(user_id, media_urls)
            cleanup_summary['storage']['r2_files'] = r2_count
            logger.info(f"✅ Deleted {r2_count} files from R2 storage")
        except Exception as e:
            errors.append(f"Failed to delete R2 files: {e}")
            logger.error(f"❌ Error deleting R2 files: {e}")

        # ---------------------------------------------------------------------
        # STEP 4: Delete transactions (financial ledger)
        # ---------------------------------------------------------------------
        try:
            count = self._delete_collection_by_user_id(
                'transactions', 'userId', user_id
            )
            cleanup_summary['firestore']['transactions'] = count
            logger.info(f"✅ Deleted {count} transactions")
        except Exception as e:
            errors.append(f"Failed to delete transactions: {e}")
            logger.error(f"❌ Error deleting transactions: {e}")

        # ---------------------------------------------------------------------
        # STEP 5: Delete user subscriptions (Stripe records in Firestore)
        # ---------------------------------------------------------------------
        try:
            count = self._delete_user_subscriptions(user_id)
            cleanup_summary['firestore']['user_subscriptions'] = count
            logger.info(f"✅ Deleted {count} subscription records")
        except Exception as e:
            errors.append(f"Failed to delete subscriptions: {e}")
            logger.error(f"❌ Error deleting subscriptions: {e}")

        # ---------------------------------------------------------------------
        # STEP 6: Delete user usage records (daily tracking)
        # ---------------------------------------------------------------------
        try:
            count = self._delete_user_usage_records(user_id)
            cleanup_summary['firestore']['user_usage'] = count
            logger.info(f"✅ Deleted {count} usage records")
        except Exception as e:
            errors.append(f"Failed to delete usage records: {e}")
            logger.error(f"❌ Error deleting usage records: {e}")

        # ---------------------------------------------------------------------
        # STEP 7: Delete social media connections
        # ---------------------------------------------------------------------
        try:
            count = self._delete_collection_by_user_id(
                'user_social_accounts', 'user_id', user_id
            )
            cleanup_summary['firestore']['social_accounts'] = count
            logger.info(f"✅ Deleted {count} social accounts")
        except Exception as e:
            errors.append(f"Failed to delete social accounts: {e}")
            logger.error(f"❌ Error deleting social accounts: {e}")

        # ---------------------------------------------------------------------
        # STEP 8: Delete synced social posts
        # ---------------------------------------------------------------------
        try:
            count = self._delete_collection_by_user_id(
                'social_posts', 'user_id', user_id
            )
            cleanup_summary['firestore']['social_posts'] = count
            logger.info(f"✅ Deleted {count} social posts")
        except Exception as e:
            errors.append(f"Failed to delete social posts: {e}")
            logger.error(f"❌ Error deleting social posts: {e}")

        # ---------------------------------------------------------------------
        # STEP 9: Delete OAuth states
        # ---------------------------------------------------------------------
        try:
            count = self._delete_collection_by_user_id(
                'oauth_states', 'user_id', user_id
            )
            cleanup_summary['firestore']['oauth_states'] = count
            logger.info(f"✅ Deleted {count} OAuth states")
        except Exception as e:
            errors.append(f"Failed to delete OAuth states: {e}")
            logger.error(f"❌ Error deleting OAuth states: {e}")

        # ---------------------------------------------------------------------
        # STEP 10: Delete security alerts
        # ---------------------------------------------------------------------
        try:
            count = self._delete_collection_by_user_id(
                'security_alerts', 'user_id', user_id
            )
            cleanup_summary['firestore']['security_alerts'] = count
            logger.info(f"✅ Deleted {count} security alerts")
        except Exception as e:
            errors.append(f"Failed to delete security alerts: {e}")
            logger.error(f"❌ Error deleting security alerts: {e}")

        # ---------------------------------------------------------------------
        # STEP 10b: Delete legacy image_generations records
        # (Legacy collection from original image generator, separate from creations)
        # ---------------------------------------------------------------------
        try:
            count = self._delete_collection_by_user_id(
                'image_generations', 'user_id', user_id
            )
            cleanup_summary['firestore']['image_generations'] = count
            logger.info(f"✅ Deleted {count} legacy image generation records")
        except Exception as e:
            errors.append(f"Failed to delete image_generations: {e}")
            logger.error(f"❌ Error deleting image_generations: {e}")

        # ---------------------------------------------------------------------
        # STEP 11: Delete session cache entries
        # ---------------------------------------------------------------------
        try:
            count = self._delete_user_sessions(user_id)
            cleanup_summary['firestore']['sessions'] = count
            logger.info(f"✅ Deleted {count} session entries")
        except Exception as e:
            errors.append(f"Failed to delete sessions: {e}")
            logger.error(f"❌ Error deleting sessions: {e}")

        # ---------------------------------------------------------------------
        # STEP 12: Delete user's comments on OTHER users' creations
        # ---------------------------------------------------------------------
        try:
            count = self._delete_user_comments_on_others(user_id)
            cleanup_summary['firestore']['comments_on_others'] = count
            logger.info(f"✅ Deleted {count} comments on other users' content")
        except Exception as e:
            errors.append(f"Failed to delete comments: {e}")
            logger.error(f"❌ Error deleting comments: {e}")

        # ---------------------------------------------------------------------
        # STEP 13: Delete Stripe customer (external API)
        # ---------------------------------------------------------------------
        if stripe_customer_id and self.stripe_configured:
            try:
                deleted = self._delete_stripe_customer(stripe_customer_id)
                cleanup_summary['external']['stripe_customer'] = 'deleted' if deleted else 'not_found'
                logger.info(f"✅ Stripe customer {'deleted' if deleted else 'not found'}")
            except Exception as e:
                errors.append(f"Failed to delete Stripe customer: {e}")
                logger.error(f"❌ Error deleting Stripe customer: {e}")
        else:
            cleanup_summary['external']['stripe_customer'] = 'skipped'

        # ---------------------------------------------------------------------
        # STEP 14: Delete Firebase Auth user (permanent - frees email)
        # ---------------------------------------------------------------------
        try:
            deleted = self._delete_firebase_auth_user(user_id)
            cleanup_summary['external']['firebase_auth'] = 'deleted' if deleted else 'not_found'
            logger.info(f"✅ Firebase Auth user {'deleted' if deleted else 'not found'}")
        except Exception as e:
            errors.append(f"Failed to delete Firebase Auth user: {e}")
            logger.error(f"❌ Error deleting Firebase Auth user: {e}")

        # ---------------------------------------------------------------------
        # STEP 16: Release username (allows reuse)
        # ---------------------------------------------------------------------
        if username:
            try:
                released = self._release_username(username)
                cleanup_summary['firestore']['username_released'] = username if released else 'failed'
                logger.info(f"✅ Username '{username}' released for reuse")
            except Exception as e:
                errors.append(f"Failed to release username: {e}")
                logger.error(f"❌ Error releasing username: {e}")

        # ---------------------------------------------------------------------
        # STEP 17: Delete main user document (MUST BE LAST)
        # ---------------------------------------------------------------------
        try:
            deleted = self._delete_user_document(user_id)
            cleanup_summary['firestore']['user_document'] = 'deleted' if deleted else 'not_found'
            logger.info(f"✅ User document {'deleted' if deleted else 'not found'}")
        except Exception as e:
            errors.append(f"Failed to delete user document: {e}")
            logger.error(f"❌ Error deleting user document: {e}")

        # ---------------------------------------------------------------------
        # FINAL: Calculate results and return summary
        # ---------------------------------------------------------------------
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        success = len(errors) == 0
        result = {
            'success': success,
            'user_id': user_id,
            'username': username,
            'deleted_at': end_time.isoformat(),
            'duration_ms': duration_ms,
            'cleanup_summary': cleanup_summary,
            'errors': errors
        }

        # Log final summary
        status_emoji = "🎉" if success else "⚠️"
        logger.warning(
            f"\n{'='*60}\n"
            f"{status_emoji} ACCOUNT DELETION {'COMPLETED' if success else 'COMPLETED WITH ERRORS'}\n"
            f"{'='*60}\n"
            f"   User: @{username or user_id}\n"
            f"   Duration: {duration_ms}ms\n"
            f"   Firestore docs deleted: {sum(v for v in cleanup_summary['firestore'].values() if isinstance(v, int))}\n"
            f"   R2 files deleted: {cleanup_summary['storage'].get('r2_files', 0)}\n"
            f"   Errors: {len(errors)}\n"
            f"{'='*60}"
        )

        if errors:
            logger.error(f"Deletion errors for {user_id}: {errors}")

        return result

    # =========================================================================
    # HELPER METHODS - USER DATA
    # =========================================================================

    def _get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the user document from Firestore.

        Args:
            user_id: Firebase Auth UID

        Returns:
            User document data or None if not found
        """
        user_ref = self.db.collection('users').document(user_id)
        user_doc = user_ref.get()
        return user_doc.to_dict() if user_doc.exists else None

    def _delete_user_document(self, user_id: str) -> bool:
        """
        Delete the main user document.

        Args:
            user_id: Firebase Auth UID

        Returns:
            True if deleted, False if not found
        """
        user_ref = self.db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            user_ref.delete()
            logger.debug(f"Deleted user document: {user_id}")
            return True

        return False

    def _release_username(self, username: str) -> bool:
        """
        Release a username by deleting it from the usernames collection.
        This allows the username to be claimed by another user.

        Args:
            username: The username to release (will be lowercased)

        Returns:
            True if deleted, False if not found
        """
        username_lower = username.lower().strip()
        username_ref = self.db.collection('usernames').document(username_lower)
        username_doc = username_ref.get()

        if username_doc.exists:
            username_ref.delete()
            logger.debug(f"Released username: {username}")
            return True

        logger.debug(f"Username not found to release: {username}")
        return False

    # =========================================================================
    # HELPER METHODS - CREATIONS & MEDIA
    # =========================================================================

    def _delete_user_creations_with_media(
        self,
        user_id: str
    ) -> tuple[int, List[str]]:
        """
        Delete all creations owned by the user, including their comments.
        Also collects media URLs for subsequent R2 cleanup.

        Args:
            user_id: Firebase Auth UID

        Returns:
            Tuple of (deleted_count, list_of_media_urls)
        """
        query = (
            self.db.collection('creations')
            .where(filter=FieldFilter('userId', '==', user_id))
        )

        deleted_count = 0
        media_urls = []

        for doc in query.stream():
            creation_data = doc.to_dict()

            # Collect media URL for R2 cleanup
            media_url = creation_data.get('mediaUrl')
            if media_url:
                media_urls.append(media_url)

            # Also collect thumbnail if different
            thumbnail_url = creation_data.get('thumbnailUrl')
            if thumbnail_url and thumbnail_url != media_url:
                media_urls.append(thumbnail_url)

            # Delete all comments on this creation (subcollection)
            self._delete_subcollection(doc.reference, 'comments')

            # Delete the creation document
            doc.reference.delete()
            deleted_count += 1
            logger.debug(f"Deleted creation: {doc.id}")

        return deleted_count, media_urls

    def _delete_subcollection(
        self,
        parent_ref,
        subcollection_name: str
    ) -> int:
        """
        Delete all documents in a subcollection using batched writes.

        Args:
            parent_ref: Parent document reference
            subcollection_name: Name of the subcollection to delete

        Returns:
            Number of documents deleted
        """
        subcollection = parent_ref.collection(subcollection_name)
        deleted_count = 0

        while True:
            docs = list(subcollection.limit(self.BATCH_SIZE).stream())
            if not docs:
                break

            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
            batch.commit()

        return deleted_count

    def _delete_r2_media_files(
        self,
        user_id: str,
        media_urls: List[str]
    ) -> int:
        """
        Delete media files from Cloudflare R2 storage.

        Strategy:
        1. Extract R2 object keys from media URLs
        2. Also list all objects with user_id prefix (catch-all)
        3. Delete all found objects

        Args:
            user_id: Firebase Auth UID
            media_urls: List of media URLs from creations

        Returns:
            Number of files deleted
        """
        s3_client = self._get_s3_client()
        if not s3_client:
            logger.warning("R2 not configured - skipping media cleanup")
            return 0

        deleted_count = 0
        keys_to_delete = set()

        # Extract keys from known media URLs
        for url in media_urls:
            key = self._extract_r2_key_from_url(url)
            if key:
                keys_to_delete.add(key)

        # Also list all objects with user_id prefix (catch-all for orphaned files)
        try:
            prefix = f"{user_id}/"
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.r2_bucket, Prefix=prefix)

            for page in pages:
                for obj in page.get('Contents', []):
                    keys_to_delete.add(obj['Key'])
        except Exception as e:
            logger.warning(f"Could not list R2 objects by prefix: {e}")

        # Delete all collected keys
        if keys_to_delete:
            # R2/S3 supports batch delete of up to 1000 objects
            keys_list = list(keys_to_delete)
            for i in range(0, len(keys_list), 1000):
                batch = keys_list[i:i + 1000]
                try:
                    s3_client.delete_objects(
                        Bucket=self.r2_bucket,
                        Delete={
                            'Objects': [{'Key': k} for k in batch],
                            'Quiet': True
                        }
                    )
                    deleted_count += len(batch)
                except Exception as e:
                    logger.error(f"Failed to delete R2 batch: {e}")

        return deleted_count

    def _extract_r2_key_from_url(self, url: str) -> Optional[str]:
        """
        Extract the R2 object key from a media URL.

        Expected URL format:
        https://{bucket}.r2.dev/{key} or https://custom-domain/{key}

        Args:
            url: Full media URL

        Returns:
            Object key or None if cannot be extracted
        """
        if not url or not self.r2_public_url:
            return None

        try:
            # Remove the base URL to get the key
            if url.startswith(self.r2_public_url):
                key = url[len(self.r2_public_url):].lstrip('/')
                return key if key else None

            # Fallback: parse URL path
            parsed = urlparse(url)
            if parsed.path:
                return parsed.path.lstrip('/')
        except Exception:
            pass

        return None

    def _get_s3_client(self):
        """
        Get or create the S3 client for R2 operations (lazy initialization).

        Returns:
            boto3 S3 client or None if not configured
        """
        global _s3_client

        if _s3_client is not None:
            return _s3_client

        # Check R2 configuration
        r2_access_key = os.getenv('R2_ACCESS_KEY_ID', '').strip()
        r2_secret_key = os.getenv('R2_SECRET_ACCESS_KEY', '').strip()
        r2_endpoint = os.getenv('R2_ENDPOINT_URL', '').strip()

        if not all([r2_access_key, r2_secret_key, r2_endpoint]):
            logger.debug("R2 not configured - credentials missing")
            return None

        try:
            import boto3
            _s3_client = boto3.client(
                's3',
                endpoint_url=r2_endpoint,
                aws_access_key_id=r2_access_key,
                aws_secret_access_key=r2_secret_key,
                region_name='auto'
            )
            logger.debug("R2 S3 client initialized")
            return _s3_client
        except Exception as e:
            logger.error(f"Failed to create R2 client: {e}")
            return None

    # =========================================================================
    # HELPER METHODS - GENERIC COLLECTION DELETION
    # =========================================================================

    def _delete_collection_by_user_id(
        self,
        collection_name: str,
        user_id_field: str,
        user_id: str
    ) -> int:
        """
        Delete all documents in a collection where user_id_field equals user_id.
        Uses batched writes for efficiency.

        Args:
            collection_name: Firestore collection name
            user_id_field: Name of the field containing user ID (e.g., 'userId' or 'user_id')
            user_id: Firebase Auth UID

        Returns:
            Number of documents deleted
        """
        query = (
            self.db.collection(collection_name)
            .where(filter=FieldFilter(user_id_field, '==', user_id))
        )

        deleted_count = 0

        while True:
            docs = list(query.limit(self.BATCH_SIZE).stream())
            if not docs:
                break

            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
            batch.commit()

        return deleted_count

    # =========================================================================
    # HELPER METHODS - SPECIFIC COLLECTIONS
    # =========================================================================

    def _delete_user_subscriptions(self, user_id: str) -> int:
        """
        Delete subscription records from user_subscriptions collection.
        Handles both document ID patterns:
        - Stripe subscription ID: 'sub_xxxxx'
        - Free tier ID: 'free_{user_id}'

        Args:
            user_id: Firebase Auth UID

        Returns:
            Number of documents deleted
        """
        deleted_count = 0

        # Pattern 1: Query by firebase_uid field
        query = (
            self.db.collection('user_subscriptions')
            .where(filter=FieldFilter('firebase_uid', '==', user_id))
        )
        for doc in query.stream():
            doc.reference.delete()
            deleted_count += 1
            logger.debug(f"Deleted subscription: {doc.id}")

        # Pattern 2: Direct document ID for free tier
        free_doc_ref = self.db.collection('user_subscriptions').document(f"free_{user_id}")
        free_doc = free_doc_ref.get()
        if free_doc.exists:
            free_doc_ref.delete()
            deleted_count += 1
            logger.debug(f"Deleted free subscription: free_{user_id}")

        return deleted_count

    def _delete_user_usage_records(self, user_id: str) -> int:
        """
        Delete daily usage records from user_usage collection.
        Document IDs follow pattern: {user_id}_{YYYY-MM-DD}

        Args:
            user_id: Firebase Auth UID

        Returns:
            Number of documents deleted
        """
        deleted_count = 0

        # Query by user_id field (if present)
        try:
            query = (
                self.db.collection('user_usage')
                .where(filter=FieldFilter('firebase_uid', '==', user_id))
            )
            for doc in query.stream():
                doc.reference.delete()
                deleted_count += 1
        except Exception:
            pass  # Field might not exist

        # Also scan by document ID prefix (more reliable)
        # Note: Firestore doesn't support prefix queries on document IDs,
        # so we query by user_id field stored in the document
        try:
            query = (
                self.db.collection('user_usage')
                .where(filter=FieldFilter('user_id', '==', user_id))
            )
            for doc in query.stream():
                doc.reference.delete()
                deleted_count += 1
        except Exception:
            pass

        return deleted_count

    def _delete_user_sessions(self, user_id: str) -> int:
        """
        Delete session cache entries for the user.
        Sessions are keyed by session ID, not user ID, so we must scan.

        Args:
            user_id: Firebase Auth UID

        Returns:
            Number of sessions deleted
        """
        deleted_count = 0

        # Scan all sessions (necessary because sessions are keyed by session ID)
        sessions = self.db.collection('cache_sessions').stream()

        for doc in sessions:
            try:
                data = doc.to_dict()
                session_data = data.get('data', {})

                # Check if this session belongs to the user
                if session_data.get('user_id') == user_id:
                    doc.reference.delete()
                    deleted_count += 1
                    logger.debug(f"Deleted session: {doc.id}")
            except Exception as e:
                logger.debug(f"Error checking session {doc.id}: {e}")

        return deleted_count

    def _delete_user_comments_on_others(self, user_id: str) -> int:
        """
        Delete comments made by the user on OTHER users' creations.
        Also decrements the comment count on those creations.

        Note: Comments on the user's OWN creations are deleted when
        the creations are deleted (handled separately).

        Args:
            user_id: Firebase Auth UID

        Returns:
            Number of comments deleted
        """
        deleted_count = 0

        # Get all creations (we need to check their comments subcollections)
        # This is expensive but necessary for complete cleanup
        creations = self.db.collection('creations').stream()

        for creation_doc in creations:
            try:
                creation_data = creation_doc.to_dict()

                # Skip creations owned by this user (already handled)
                if creation_data.get('userId') == user_id:
                    continue

                # Find and delete user's comments on this creation
                comments = (
                    creation_doc.reference.collection('comments')
                    .where(filter=FieldFilter('userId', '==', user_id))
                    .stream()
                )

                for comment_doc in comments:
                    comment_doc.reference.delete()
                    deleted_count += 1

                    # Decrement comment count on the creation
                    try:
                        creation_doc.reference.update({
                            'commentCount': firestore.Increment(-1)
                        })
                    except Exception:
                        pass  # Non-critical if this fails

            except Exception as e:
                logger.debug(f"Error processing creation {creation_doc.id}: {e}")

        return deleted_count

    # =========================================================================
    # HELPER METHODS - EXTERNAL SERVICES
    # =========================================================================

    def _delete_stripe_customer(self, customer_id: str) -> bool:
        """
        Delete a Stripe customer record via the Stripe API.
        This also cascades to delete all subscriptions and payment methods.

        Args:
            customer_id: Stripe customer ID (cus_xxxxx)

        Returns:
            True if deleted, False if not found or error
        """
        if not self.stripe_configured:
            logger.debug("Stripe not configured - skipping customer deletion")
            return False

        if not customer_id or not customer_id.startswith('cus_'):
            logger.debug(f"Invalid Stripe customer ID: {customer_id}")
            return False

        try:
            # Delete the customer (cascades to subscriptions)
            stripe.Customer.delete(customer_id)
            logger.info(f"Deleted Stripe customer: {customer_id}")
            return True
        except stripe.error.InvalidRequestError as e:
            if 'No such customer' in str(e):
                logger.debug(f"Stripe customer not found: {customer_id}")
                return False
            raise
        except Exception as e:
            logger.error(f"Failed to delete Stripe customer {customer_id}: {e}")
            raise

    def _delete_firebase_auth_user(self, user_id: str) -> bool:
        """
        Delete the Firebase Auth user record.

        This permanently removes the user's authentication identity:
        - Email becomes available for new registrations
        - All auth tokens are invalidated
        - User cannot sign in anymore

        WARNING: This is irreversible. The user must create a completely
        new account to use the platform again.

        Args:
            user_id: Firebase Auth UID

        Returns:
            True if deleted, False if not found
        """
        try:
            firebase_auth.delete_user(user_id)
            logger.info(f"Deleted Firebase Auth user: {user_id}")
            return True
        except firebase_auth.UserNotFoundError:
            logger.debug(f"Firebase Auth user not found: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete Firebase Auth user {user_id}: {e}")
            raise

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of all data associated with a user.
        Useful for showing users what will be deleted before deletion.

        Args:
            user_id: Firebase Auth UID

        Returns:
            Summary of user data counts
        """
        summary = {
            'user_id': user_id,
            'exists': False,
            'username': None,
            'data_counts': {}
        }

        # Check user exists
        user_data = self._get_user_data(user_id)
        if not user_data:
            return summary

        summary['exists'] = True
        summary['username'] = user_data.get('username')
        summary['email'] = user_data.get('email')
        summary['token_balance'] = user_data.get('tokenBalance', 0)

        # Count creations
        creations_query = (
            self.db.collection('creations')
            .where(filter=FieldFilter('userId', '==', user_id))
        )
        summary['data_counts']['creations'] = len(list(creations_query.stream()))

        # Count transactions
        transactions_query = (
            self.db.collection('transactions')
            .where(filter=FieldFilter('userId', '==', user_id))
        )
        summary['data_counts']['transactions'] = len(list(transactions_query.stream()))

        # Count social accounts
        social_query = (
            self.db.collection('user_social_accounts')
            .where(filter=FieldFilter('user_id', '==', user_id))
        )
        summary['data_counts']['social_accounts'] = len(list(social_query.stream()))

        return summary


# =============================================================================
# SINGLETON PATTERN
# =============================================================================

_deletion_service: Optional[AccountDeletionService] = None


def get_deletion_service() -> AccountDeletionService:
    """
    Get or create the account deletion service singleton.

    Returns:
        AccountDeletionService instance
    """
    global _deletion_service
    if _deletion_service is None:
        _deletion_service = AccountDeletionService()
    return _deletion_service
