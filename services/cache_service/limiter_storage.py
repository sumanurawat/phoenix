"""
Flask-Limiter Storage Backend using Firestore

Implements Flask-Limiter's storage interface using our Firestore cache service.
This allows rate limits to persist across container restarts and work correctly
with multiple Cloud Run instances.

Usage:
    from services.cache_service.limiter_storage import FirestoreLimiterStorage, register_firestore_storage

    # Register the storage scheme first
    register_firestore_storage()

    limiter = Limiter(
        app=app,
        storage_uri="firestore://",
        storage_options={"collection_name": "rate_limits"}
    )
"""

import logging
import time
from typing import Optional, Tuple, Type
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore
from google.api_core import exceptions as google_exceptions
from limits.storage import Storage

logger = logging.getLogger(__name__)


class FirestoreLimiterStorage(Storage):
    """
    Firestore storage backend for Flask-Limiter.

    Storage Format:
        Collection: rate_limits (configurable)
        Document ID: {key} (rate limit key, e.g., "user:abc123/10/1/minute")
        Fields:
            - count: int - Current request count
            - expiry: datetime - When this window expires
            - created_at: datetime - When first request in window occurred

    TTL Policy:
        Documents auto-delete after expiry via Firestore TTL policy.
    """

    STORAGE_SCHEME = ["firestore"]

    def __init__(self, uri: str = None, collection_name: str = "rate_limits", **options):
        """
        Initialize Firestore limiter storage.

        Args:
            uri: Storage URI (not used, just for compatibility)
            collection_name: Firestore collection for rate limits
            **options: Additional options
        """
        # Call parent __init__ to properly initialize the Storage base class
        super().__init__(uri, **options)
        self.collection_name = options.get('collection_name', collection_name)
        self.db = firestore.client()
        self.collection = self.db.collection(self.collection_name)
        logger.info(f"FirestoreLimiterStorage initialized with collection: {self.collection_name}")

    @property
    def base_exceptions(self) -> Tuple[Type[Exception], ...]:
        """
        Return the base exceptions that should be caught and wrapped.

        Returns:
            Tuple of exception types that indicate Firestore errors
        """
        return (
            google_exceptions.GoogleAPIError,
            google_exceptions.GoogleAPICallError,
        )

    def _make_key(self, key: str) -> str:
        """
        Sanitize key for use as Firestore document ID.

        Firestore document IDs cannot contain '/' so we replace with '__'.
        """
        return key.replace('/', '__')

    def incr(self, key: str, expiry: int, elastic_expiry: bool = False, amount: int = 1) -> int:
        """
        Increment the counter for a rate limit key.

        Args:
            key: Rate limit key (e.g., "user:abc123/10/1/minute")
            expiry: Window expiry in seconds
            elastic_expiry: If True, extend expiry on each request
            amount: Amount to increment (default: 1)

        Returns:
            New counter value
        """
        doc_key = self._make_key(key)
        doc_ref = self.collection.document(doc_key)

        try:
            # Use transaction for atomic increment
            @firestore.transactional
            def increment_in_transaction(transaction, doc_ref):
                doc = doc_ref.get(transaction=transaction)
                now = datetime.now(timezone.utc)

                if doc.exists:
                    data = doc.to_dict()
                    expiry_time = data.get('expiry')

                    # Check if window has expired
                    if expiry_time and expiry_time.tzinfo is None:
                        expiry_time = expiry_time.replace(tzinfo=timezone.utc)

                    if expiry_time and expiry_time > now:
                        # Window still valid - increment
                        new_count = data.get('count', 0) + amount

                        update_data = {'count': new_count}
                        if elastic_expiry:
                            update_data['expiry'] = now + timedelta(seconds=expiry)

                        transaction.update(doc_ref, update_data)
                        return new_count

                # Window expired or doesn't exist - create new
                new_expiry = now + timedelta(seconds=expiry)
                transaction.set(doc_ref, {
                    'count': amount,
                    'expiry': new_expiry,
                    'created_at': now,
                    'key': key  # Store original key for debugging
                })
                return amount

            transaction = self.db.transaction()
            result = increment_in_transaction(transaction, doc_ref)
            logger.debug(f"Rate limit incr: {key} -> {result}")
            return result

        except Exception as e:
            logger.error(f"Error incrementing rate limit {key}: {e}")
            # On error, be permissive (don't block user)
            return 1

    def get(self, key: str) -> int:
        """
        Get current counter value for a rate limit key.

        Args:
            key: Rate limit key

        Returns:
            Current count, or 0 if not found/expired
        """
        doc_key = self._make_key(key)

        try:
            doc = self.collection.document(doc_key).get()

            if not doc.exists:
                return 0

            data = doc.to_dict()
            expiry_time = data.get('expiry')
            now = datetime.now(timezone.utc)

            # Check if expired
            if expiry_time:
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                if expiry_time < now:
                    return 0

            return data.get('count', 0)

        except Exception as e:
            logger.error(f"Error getting rate limit {key}: {e}")
            return 0

    def get_expiry(self, key: str) -> int:
        """
        Get expiry timestamp for a rate limit key.

        Args:
            key: Rate limit key

        Returns:
            Unix timestamp of expiry, or current time if not found
        """
        doc_key = self._make_key(key)

        try:
            doc = self.collection.document(doc_key).get()

            if not doc.exists:
                return int(time.time())

            data = doc.to_dict()
            expiry_time = data.get('expiry')

            if expiry_time:
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                return int(expiry_time.timestamp())

            return int(time.time())

        except Exception as e:
            logger.error(f"Error getting expiry for {key}: {e}")
            return int(time.time())

    def check(self) -> bool:
        """
        Check if Firestore is accessible.

        Returns:
            True if storage is healthy
        """
        try:
            # Simple health check - try to access collection
            list(self.collection.limit(1).stream())
            return True
        except Exception as e:
            logger.error(f"Firestore health check failed: {e}")
            return False

    def reset(self) -> Optional[int]:
        """
        Reset all rate limits (delete all documents in collection).

        WARNING: Use only for testing!

        Returns:
            Number of documents deleted
        """
        try:
            docs = self.collection.stream()
            count = 0
            batch = self.db.batch()

            for doc in docs:
                batch.delete(doc.reference)
                count += 1

                # Firestore batches limited to 500 operations
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()

            if count % 500 != 0:
                batch.commit()

            logger.warning(f"Rate limits reset: deleted {count} documents")
            return count

        except Exception as e:
            logger.error(f"Error resetting rate limits: {e}")
            return None

    def clear(self, key: str) -> None:
        """
        Clear a specific rate limit key.

        Args:
            key: Rate limit key to clear
        """
        doc_key = self._make_key(key)

        try:
            self.collection.document(doc_key).delete()
            logger.debug(f"Cleared rate limit: {key}")
        except Exception as e:
            logger.error(f"Error clearing rate limit {key}: {e}")


def register_firestore_storage():
    """
    Register FirestoreLimiterStorage with Flask-Limiter's storage registry.

    Call this before creating the Limiter instance.
    """
    from limits.storage.registry import SCHEMES

    # Register our custom scheme
    SCHEMES['firestore'] = FirestoreLimiterStorage
    logger.info("Registered 'firestore://' storage scheme for Flask-Limiter")
