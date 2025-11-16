"""
Firestore Cache Backend

Implements the CacheServiceInterface using Google Cloud Firestore.

Features:
- Automatic TTL via Firestore TTL policies (no manual cleanup needed)
- Transactional updates for consistency
- Efficient querying with indexes
- Auto-scaling with zero infrastructure management

Cost: ~$0.50-60/month for small-medium apps (10K users)
Latency: 5-20ms reads, 20-50ms writes
"""

import logging
from typing import Any, Optional, Dict
from datetime import datetime, timedelta, timezone
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .interface import CacheServiceInterface


logger = logging.getLogger(__name__)


class FirestoreCache(CacheServiceInterface):
    """
    Firestore implementation of cache service.

    Storage Format:
        Collection: {collection_name} (default: 'cache_sessions')
        Document ID: {key}
        Fields:
            - data: Dict[str, Any] - The actual cached data
            - created_at: datetime - When entry was created
            - expires_at: datetime - When entry should expire (TTL field)
            - last_accessed: datetime - Last time entry was accessed

    TTL Policy:
        Firestore automatically deletes documents where expires_at < now
        (within 24 hours of expiration)
    """

    def __init__(self, collection_name: str = "cache_sessions"):
        """
        Initialize Firestore cache backend.

        Args:
            collection_name: Name of Firestore collection to use
        """
        self.collection_name = collection_name
        self.db = firestore.client()
        self.collection = self.db.collection(collection_name)
        logger.info(f"FirestoreCache initialized with collection: {collection_name}")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from Firestore cache.

        Args:
            key: Cache key (will be used as document ID)

        Returns:
            Cached data or None if not found/expired
        """
        try:
            logger.info(f"📖 Cache GET: {key}")
            doc_ref = self.collection.document(key)
            doc = doc_ref.get()

            if not doc.exists:
                logger.info(f"❌ Cache miss (not found): {key}")
                return None

            entry = doc.to_dict()
            logger.debug(f"📦 Retrieved entry with keys: {list(entry.keys())}")

            # Check if expired (Firestore TTL may not have run yet)
            expires_at = entry.get('expires_at')
            if expires_at:
                # Make timezone-aware for comparison
                now = datetime.now(timezone.utc)
                # Convert expires_at to timezone-aware if needed
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)

                time_until_expiry = (expires_at - now).total_seconds()
                logger.debug(f"⏰ Time until expiry: {time_until_expiry:.0f}s ({time_until_expiry/3600:.1f}h)")

                if expires_at < now:
                    logger.info(f"❌ Cache miss (expired): {key}")
                    # Delete expired entry
                    doc_ref.delete()
                    return None

            # Update last_accessed timestamp asynchronously (don't block read)
            self._async_update_access_time(key)

            logger.info(f"✅ Cache hit: {key}")
            return entry.get('data')

        except Exception as e:
            logger.error(f"💥 Error reading from cache: {key} - {e}", exc_info=True)
            return None

    def set(self, key: str, value: Dict[str, Any], ttl: int = 2592000) -> bool:
        """
        Store data in Firestore cache with TTL.

        Args:
            key: Cache key (document ID)
            value: Data to cache (must be JSON-serializable dict)
            ttl: Time-to-live in seconds (default: 30 days)

        Returns:
            True if successful
        """
        try:
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=ttl)

            entry = {
                'data': value,
                'created_at': now,
                'expires_at': expires_at,  # TTL field for Firestore auto-deletion
                'last_accessed': now
            }

            doc_ref = self.collection.document(key)
            doc_ref.set(entry)

            logger.info(f"💾 Cache SET: {key} (TTL: {ttl}s = {ttl/3600:.1f}h)")
            logger.debug(f"📝 Data keys: {list(value.keys()) if isinstance(value, dict) else 'non-dict'}")
            return True

        except Exception as e:
            logger.error(f"💥 Error writing to cache: {key} - {e}", exc_info=True)
            return False

    def delete(self, key: str) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            doc_ref = self.collection.document(key)
            doc = doc_ref.get()

            if not doc.exists:
                logger.info(f"🗑️  Cache delete: {key} (not found)")
                return False

            doc_ref.delete()
            logger.info(f"🗑️  Cache deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"💥 Error deleting from cache: {key} - {e}", exc_info=True)
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists and is not expired.

        Args:
            key: Cache key to check

        Returns:
            True if exists and valid
        """
        try:
            doc_ref = self.collection.document(key)
            doc = doc_ref.get()

            if not doc.exists:
                return False

            entry = doc.to_dict()
            expires_at = entry.get('expires_at')

            if expires_at:
                now = datetime.now(timezone.utc)
                # Convert expires_at to timezone-aware if needed
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now:
                    # Expired - delete it
                    doc_ref.delete()
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking cache existence: {key} - {e}", exc_info=True)
            return False

    def update_access_time(self, key: str) -> bool:
        """
        Update last_accessed timestamp.

        Args:
            key: Cache key to update

        Returns:
            True if updated
        """
        try:
            doc_ref = self.collection.document(key)
            doc_ref.update({'last_accessed': datetime.now(timezone.utc)})
            return True

        except Exception as e:
            logger.debug(f"Could not update access time for {key}: {e}")
            return False

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about cache entry.

        Args:
            key: Cache key

        Returns:
            Metadata dict or None
        """
        try:
            doc_ref = self.collection.document(key)
            doc = doc_ref.get()

            if not doc.exists:
                return None

            entry = doc.to_dict()
            expires_at = entry.get('expires_at')
            now = datetime.now(timezone.utc)

            # Check if expired
            is_expired = False
            if expires_at:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                is_expired = expires_at < now

            return {
                'created_at': entry.get('created_at'),
                'expires_at': entry.get('expires_at'),
                'last_accessed': entry.get('last_accessed'),
                'is_expired': is_expired
            }

        except Exception as e:
            logger.error(f"Error getting metadata: {key} - {e}", exc_info=True)
            return None

    def _async_update_access_time(self, key: str):
        """
        Asynchronously update access time (non-blocking).

        This is called after successful cache hits to track activity.
        Failures are logged but don't affect the read operation.
        """
        try:
            # Use Firestore's server timestamp for consistency
            doc_ref = self.collection.document(key)
            doc_ref.update({'last_accessed': firestore.SERVER_TIMESTAMP})
        except Exception as e:
            # Don't block reads if access time update fails
            logger.debug(f"Async access time update failed for {key}: {e}")

    def cleanup_expired(self) -> int:
        """
        Manually cleanup expired entries.

        Note: Firestore TTL policies handle this automatically,
        but this method exists for immediate cleanup if needed.

        Returns:
            Number of entries deleted
        """
        try:
            now = datetime.now(timezone.utc)
            # Query for expired entries
            expired_query = self.collection.where(
                filter=FieldFilter('expires_at', '<', now)
            ).limit(500)  # Process in batches

            expired_docs = expired_query.get()
            count = 0

            batch = self.db.batch()
            for doc in expired_docs:
                batch.delete(doc.reference)
                count += 1

            if count > 0:
                batch.commit()
                logger.info(f"Cleaned up {count} expired cache entries")

            return count

        except Exception as e:
            logger.error(f"Error during manual cleanup: {e}", exc_info=True)
            return 0
