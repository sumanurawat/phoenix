"""Stub Rate Limiter

This is a minimal stub implementation to satisfy imports while video features are disabled.
TODO: Implement full rate limiting functionality.
"""

import logging
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """Stub rate limiter."""
    
    def __init__(self):
        logger.warning("RateLimiter is using stub implementation")
    
    def limit(self, *args, **kwargs):
        """Stub decorator - no rate limiting applied."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator


# Create a global instance
rate_limiter = RateLimiter()