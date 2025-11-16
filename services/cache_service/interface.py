"""
Cache Service Interface

Abstract base class defining the contract for all cache backends.
This allows swapping between Firestore, Redis, Memcached without
changing application code.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from datetime import datetime


class CacheServiceInterface(ABC):
    """
    Abstract interface for cache operations.

    All cache backends (Firestore, Redis, etc.) must implement this interface.
    This ensures we can swap backends without changing application code.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache.

        Args:
            key: Unique identifier for the cached data

        Returns:
            Cached data as dictionary, or None if not found/expired
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl: int = 2592000) -> bool:
        """
        Store data in cache with automatic expiration.

        Args:
            key: Unique identifier for the data
            value: Data to cache (must be JSON-serializable dict)
            ttl: Time-to-live in seconds (default: 30 days)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Remove data from cache.

        Args:
            key: Unique identifier to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache and is not expired.

        Args:
            key: Unique identifier to check

        Returns:
            True if exists and not expired, False otherwise
        """
        pass

    @abstractmethod
    def update_access_time(self, key: str) -> bool:
        """
        Update last_accessed timestamp for a cache entry.

        Useful for session management to track activity.

        Args:
            key: Unique identifier to update

        Returns:
            True if updated, False if not found
        """
        pass

    @abstractmethod
    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a cache entry (created_at, expires_at, etc.)

        Args:
            key: Unique identifier

        Returns:
            Metadata dict or None if not found
        """
        pass
