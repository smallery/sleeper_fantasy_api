"""Tests for the PersistentCache class."""
import time
import pytest
from sleeper_api.persistent_cache import PersistentCache


class TestPersistentCache:
    """Test cases for PersistentCache."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create a temporary cache directory."""
        cache_dir = tmp_path / "test_cache"
        cache_dir.mkdir()
        return cache_dir

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a PersistentCache instance with temp directory."""
        return PersistentCache(cache_dir=temp_cache_dir, default_ttl_hours=1.0)

    def test_set_and_get(self, cache):
        """Test setting and getting a value."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value"}

        # Act
        cache.set(key, value)
        result = cache.get(key)

        # Assert
        assert result == value

    def test_get_nonexistent_key(self, cache):
        """Test getting a nonexistent key returns None."""
        # Act
        result = cache.get("nonexistent")

        # Assert
        assert result is None

    def test_expiration(self, cache):
        """Test that expired entries return None."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value"}
        cache.set(key, value, ttl_hours=0.0001)  # Very short TTL

        # Act
        time.sleep(0.5)  # Wait for expiration
        result = cache.get(key)

        # Assert
        assert result is None

    def test_invalidate(self, cache):
        """Test invalidating a cache entry."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value"}
        cache.set(key, value)

        # Act
        cache.invalidate(key)
        result = cache.get(key)

        # Assert
        assert result is None

    def test_clear(self, cache):
        """Test clearing all cache entries."""
        # Arrange
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        # Act
        cache.clear()

        # Assert
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self, cache):
        """Test cleaning up expired entries."""
        # Arrange
        cache.set("key1", {"data": "value1"}, ttl_hours=0.0001)
        cache.set("key2", {"data": "value2"}, ttl_hours=10.0)
        time.sleep(0.5)  # Wait for key1 to expire

        # Act
        removed = cache.cleanup_expired()

        # Assert
        assert removed == 1
        assert cache.get("key1") is None
        assert cache.get("key2") is not None

    def test_get_stats(self, cache):
        """Test getting cache statistics."""
        # Arrange
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        # Act
        stats = cache.get_stats()

        # Assert
        assert stats["entries"] == 2
        assert stats["size_bytes"] > 0
        assert "cache_dir" in stats

    def test_metadata_persistence(self, cache, temp_cache_dir):
        """Test that metadata persists across cache instances."""
        # Arrange
        key = "test_key"
        value = {"data": "test_value"}
        cache.set(key, value)

        # Act - Create new cache instance with same directory
        new_cache = PersistentCache(cache_dir=temp_cache_dir)
        result = new_cache.get(key)

        # Assert
        assert result == value
