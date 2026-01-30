"""
Cache Service Factory

Creates appropriate cache backend based on configuration.
Allows easy swapping between Firestore, Redis, etc.

Environment Variables:
    CACHE_BACKEND: "firestore" or "redis" (default: "firestore")
    CACHE_COLLECTION_NAME: Firestore collection name (default: "cache_sessions")
    REDIS_HOST: Redis host (for Redis backend)
    REDIS_PORT: Redis port (for Redis backend)
    REDIS_PASSWORD: Redis password (for Redis backend)
"""

import os
import logging
from typing import Optional

from .interface import CacheServiceInterface
from .firestore_backend import FirestoreCache


logger = logging.getLogger(__name__)

# Global cache instance (singleton pattern)
_cache_instance: Optional[CacheServiceInterface] = None


def get_cache_service(force_recreate: bool = False) -> CacheServiceInterface:
    """
    Get cache service instance (singleton).

    Args:
        force_recreate: Force creation of new instance (for testing)

    Returns:
        Cache service instance

    Raises:
        ValueError: If invalid backend specified
    """
    global _cache_instance

    if _cache_instance is not None and not force_recreate:
        return _cache_instance

    backend = os.getenv('CACHE_BACKEND', 'firestore').lower()
    logger.debug(f"Initializing cache service with backend: {backend}")

    if backend == 'firestore':
        collection_name = os.getenv('CACHE_COLLECTION_NAME', 'cache_sessions')
        _cache_instance = FirestoreCache(collection_name=collection_name)

    elif backend == 'redis':
        # Future implementation
        from .redis_backend import RedisCache
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD')
        _cache_instance = RedisCache(
            host=redis_host,
            port=redis_port,
            password=redis_password
        )

    else:
        raise ValueError(f"Invalid CACHE_BACKEND: {backend}. Use 'firestore' or 'redis'")

    logger.debug(f"Cache service initialized: {type(_cache_instance).__name__}")
    return _cache_instance


def reset_cache_instance():
    """
    Reset global cache instance.

    Useful for testing or forcing reconfiguration.
    """
    global _cache_instance
    _cache_instance = None
    logger.info("Cache service instance reset")
