"""
Tests for Firestore-based rate limiting.

These tests verify the FirestoreLimiterStorage backend works correctly
with Flask-Limiter's storage interface.

Run with: pytest tests/test_rate_limiting.py -v
"""

import pytest
import time
from services.cache_service.limiter_storage import FirestoreLimiterStorage


class TestFirestoreLimiterStorage:
    """Test suite for Firestore rate limit storage."""

    @pytest.fixture
    def storage(self):
        """Create test storage instance using a separate test collection."""
        storage = FirestoreLimiterStorage(collection_name="rate_limits_test")
        yield storage
        # Cleanup after test
        storage.reset()

    def test_incr_creates_new_key(self, storage):
        """Test that incr creates a new key if it doesn't exist."""
        result = storage.incr("test_key_1", expiry=60)
        assert result == 1

    def test_incr_increments_existing_key(self, storage):
        """Test that incr increments existing counter."""
        storage.incr("test_key_2", expiry=60)
        result = storage.incr("test_key_2", expiry=60)
        assert result == 2

    def test_incr_multiple_increments(self, storage):
        """Test multiple increments on the same key."""
        for i in range(1, 6):
            result = storage.incr("test_key_multi", expiry=60)
            assert result == i

    def test_get_returns_current_count(self, storage):
        """Test that get returns the current count."""
        storage.incr("test_key_3", expiry=60)
        storage.incr("test_key_3", expiry=60)
        storage.incr("test_key_3", expiry=60)

        result = storage.get("test_key_3")
        assert result == 3

    def test_get_returns_zero_for_missing_key(self, storage):
        """Test that get returns 0 for non-existent key."""
        result = storage.get("nonexistent_key")
        assert result == 0

    def test_expired_key_resets_count(self, storage):
        """Test that expired window resets the count."""
        # Create key with 1 second expiry
        storage.incr("test_key_4", expiry=1)
        storage.incr("test_key_4", expiry=1)

        # Wait for expiry
        time.sleep(2)

        # New request should start fresh
        result = storage.incr("test_key_4", expiry=60)
        assert result == 1

    def test_get_returns_zero_for_expired_key(self, storage):
        """Test that get returns 0 for expired keys."""
        # Create key with 1 second expiry
        storage.incr("test_key_expired", expiry=1)

        # Wait for expiry
        time.sleep(2)

        # Get should return 0
        result = storage.get("test_key_expired")
        assert result == 0

    def test_check_returns_true_when_healthy(self, storage):
        """Test health check returns True when Firestore is accessible."""
        assert storage.check() is True

    def test_clear_removes_key(self, storage):
        """Test that clear removes a specific key."""
        storage.incr("test_key_5", expiry=60)
        storage.clear("test_key_5")

        result = storage.get("test_key_5")
        assert result == 0

    def test_get_expiry_returns_timestamp(self, storage):
        """Test that get_expiry returns a valid timestamp."""
        storage.incr("test_key_expiry", expiry=60)
        expiry = storage.get_expiry("test_key_expiry")

        # Should be in the future
        assert expiry > time.time()
        # Should be within ~60 seconds from now
        assert expiry < time.time() + 65

    def test_get_expiry_for_missing_key(self, storage):
        """Test that get_expiry returns current time for missing keys."""
        expiry = storage.get_expiry("missing_key_expiry")
        # Should be approximately current time
        assert abs(expiry - time.time()) < 5

    def test_key_sanitization(self, storage):
        """Test that keys with slashes are handled correctly."""
        # Flask-Limiter keys often contain slashes
        key = "user:abc123/10/1/minute"
        storage.incr(key, expiry=60)

        result = storage.get(key)
        assert result == 1

    def test_reset_clears_all_keys(self, storage):
        """Test that reset clears all keys in the collection."""
        # Create several keys
        storage.incr("reset_key_1", expiry=60)
        storage.incr("reset_key_2", expiry=60)
        storage.incr("reset_key_3", expiry=60)

        # Reset
        count = storage.reset()

        # Should have deleted at least 3 documents
        assert count >= 3

        # All keys should now return 0
        assert storage.get("reset_key_1") == 0
        assert storage.get("reset_key_2") == 0
        assert storage.get("reset_key_3") == 0

    def test_elastic_expiry_extends_window(self, storage):
        """Test that elastic_expiry extends the expiry on each request."""
        # Create with 2 second expiry
        storage.incr("elastic_key", expiry=2)

        # Wait 1 second
        time.sleep(1)

        # Increment with elastic_expiry - should extend
        storage.incr("elastic_key", expiry=2, elastic_expiry=True)

        # Wait another 1.5 seconds (would have expired without elastic)
        time.sleep(1.5)

        # Should still be valid (count should be 2, not reset to 1)
        result = storage.get("elastic_key")
        assert result == 2


# Integration test with Flask app (requires running app)
class TestFlaskLimiterIntegration:
    """Integration tests for Flask-Limiter with Firestore storage."""

    @pytest.fixture
    def app(self):
        """Create test Flask app with rate limiting."""
        import os
        # Ensure we use Firestore for testing
        os.environ['USE_FIRESTORE_RATE_LIMITS'] = '1'

        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_rate_limiter_initialized(self, app):
        """Test that the rate limiter is properly initialized."""
        assert hasattr(app, 'limiter')
        assert app.limiter is not None

    def test_rate_limit_applied_to_login(self, client):
        """Test that rate limiting is applied to the login endpoint."""
        # The login endpoint should have rate limiting
        # We just verify it doesn't error, not that it enforces the limit
        # (since we don't want to actually hit the limit in tests)
        response = client.get('/auth/login')
        # Should get some response (redirect or form), not a 500 error
        assert response.status_code in [200, 302, 401, 404]


# Run with: pytest tests/test_rate_limiting.py -v
