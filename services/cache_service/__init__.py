"""
Cache Service - Reusable Session & Key-Value Store

A production-ready, backend-agnostic caching service that can be used
across multiple projects. Currently implements Firestore backend with
future support for Redis.

Usage:
    from services.cache_service import get_cache_service

    cache = get_cache_service()
    cache.set("key", {"data": "value"}, ttl=3600)
    data = cache.get("key")
"""

from .interface import CacheServiceInterface
from .factory import get_cache_service

__all__ = ["CacheServiceInterface", "get_cache_service"]
__version__ = "1.0.0"
