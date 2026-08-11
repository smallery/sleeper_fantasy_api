"""Tests for the PersistentCache class."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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

    def test_unserializable_value_leaves_no_partial_file(self, cache, temp_cache_dir):
        """A value that fails to encode must not leave a truncated cache file.

        set() serializes fully before opening the file. Encoding into an open
        file handle instead would flush valid JSON for the prefix it managed
        before raising, leaving corrupt bytes on disk under a live key.
        """
        # Arrange -- a large valid prefix so an incremental encoder would have
        # written plenty before reaching the value it cannot handle.
        value = {f"player_{i}": {"pts_ppr": float(i)} for i in range(500)}
        value["bad"] = object()

        # Act
        cache.set("partial_key", value)

        # Assert
        assert not (temp_cache_dir / "partial_key.json").exists()
        assert cache.get("partial_key") is None

    def test_concurrent_set_keeps_every_metadata_entry(self, cache, temp_cache_dir):
        """Concurrent set() must not lose entries to a metadata write race.

        set() is a read-modify-write on one shared metadata file. Unguarded,
        interleaved threads each write back a copy missing the others' keys.
        A cache file whose metadata entry was dropped is never seen as expired
        by get(), so the damage is silent permanent staleness.
        """
        # Arrange
        keys = [f"key_{i}" for i in range(50)]
        start = threading.Barrier(len(keys), timeout=10)

        def writer(key):
            start.wait()
            cache.set(key, {"data": key})

        # Act
        with ThreadPoolExecutor(max_workers=len(keys)) as executor:
            list(executor.map(writer, keys))

        # Assert
        metadata = json.loads((temp_cache_dir / "cache_metadata.json").read_text())
        assert set(metadata) == set(keys)

        reloaded = PersistentCache(cache_dir=temp_cache_dir)
        for key in keys:
            assert reloaded.get(key) == {"data": key}

    def test_concurrent_set_and_invalidate_do_not_corrupt_metadata(
        self, cache, temp_cache_dir
    ):
        """Mixed writers and removers must leave the metadata file parseable."""
        # Arrange
        keys = [f"key_{i}" for i in range(30)]
        for key in keys:
            cache.set(key, {"data": key})
        doomed = set(keys[:15])

        def worker(key):
            if key in doomed:
                cache.invalidate(key)
            else:
                cache.set(key, {"data": "rewritten"})

        # Act
        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(worker, keys))

        # Assert
        metadata = json.loads((temp_cache_dir / "cache_metadata.json").read_text())
        assert set(metadata) == set(keys) - doomed
        for key in doomed:
            assert cache.get(key) is None
