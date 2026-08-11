"""Tests for the PersistentCache class."""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
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

    def test_set_writes_sidecar_metadata_not_shared_file(self, cache, temp_cache_dir):
        """set() must write a per-key sidecar, and must not touch a shared index.

        This is the O(1) fix for #13: a shared cache_metadata.json rewritten in
        full on every set() is what made cost grow with total entry count.
        """
        # Act
        cache.set("test_key", {"data": "test_value"})

        # Assert
        assert (temp_cache_dir / "test_key.meta").exists()
        assert not (temp_cache_dir / "cache_metadata.json").exists()

    def test_set_cost_does_not_grow_with_entry_count(self, temp_cache_dir):
        """set() must stay O(1) as the number of existing entries grows.

        Regression guard for #13. Not a strict timing assertion (too flaky
        across machines/CI) -- instead asserts the O(n) tell directly: writing
        one more key must not read or grow any shared metadata file. See the
        PR description for a timing benchmark at 10 / 1,000 / 5,000 entries.
        """
        cache = PersistentCache(cache_dir=temp_cache_dir, default_ttl_hours=1.0)
        for i in range(500):
            cache.set(f"prepop_{i}", {"data": i})

        # A pure-sidecar cache never creates the legacy shared index at all.
        assert not (temp_cache_dir / "cache_metadata.json").exists()

        cache.set("one_more", {"data": "last"})
        assert (temp_cache_dir / "one_more.meta").exists()
        assert not (temp_cache_dir / "cache_metadata.json").exists()

    def test_get_reads_metadata_once_for_expired_entry(self, cache, monkeypatch):
        """get() on an expired entry must read metadata once, not twice (#14).

        The old code called _load_metadata() to discover the entry was
        expired, then invalidate() called it again for the same data. Spy on
        the single read path (_get_entry_meta) and assert it runs exactly
        once for the whole get() call, including the invalidation it triggers.
        """
        # Arrange
        cache.set("test_key", {"data": "test_value"}, ttl_hours=0.0001)
        time.sleep(0.5)

        calls = []
        original = PersistentCache._get_entry_meta

        def spy(self, key):
            calls.append(key)
            return original(self, key)

        monkeypatch.setattr(PersistentCache, "_get_entry_meta", spy)

        # Act
        result = cache.get("test_key")

        # Assert
        assert result is None
        assert calls == ["test_key"]

    def test_get_reads_metadata_once_for_live_entry(self, cache, monkeypatch):
        """get() on a live entry must read metadata exactly once."""
        # Arrange
        cache.set("test_key", {"data": "test_value"})

        calls = []
        original = PersistentCache._get_entry_meta

        def spy(self, key):
            calls.append(key)
            return original(self, key)

        monkeypatch.setattr(PersistentCache, "_get_entry_meta", spy)

        # Act
        result = cache.get("test_key")

        # Assert
        assert result == {"data": "test_value"}
        assert calls == ["test_key"]

    def test_get_with_no_metadata_anywhere_fails_closed(self, cache, temp_cache_dir):
        """A cache file with no metadata entry must not be served (#14).

        Previously get() treated a missing metadata entry as "never expires"
        and served the file forever. It must now fail closed: refuse to serve
        it, and self-heal by removing the orphaned file so it isn't
        re-evaluated (and doesn't linger) on every future get().
        """
        # Arrange -- a data file that was never set() through the cache, e.g.
        # dropped in by hand or left behind by a corrupted metadata write.
        (temp_cache_dir / "orphan_key.json").write_text(json.dumps({"data": "orphan"}))
        assert (temp_cache_dir / "orphan_key.json").exists()

        # Act
        result = cache.get("orphan_key")

        # Assert
        assert result is None
        assert not (temp_cache_dir / "orphan_key.json").exists()

    def test_get_reads_legacy_format_cache_and_migrates(self, temp_cache_dir):
        """A pre-upgrade cache directory (shared cache_metadata.json, no
        sidecars) must still be readable, and get() must transparently
        migrate the accessed entry to a sidecar file.
        """
        # Arrange -- hand-write an old-format cache directory.
        now = datetime.now()
        legacy_metadata = {
            "old_key": {
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
            }
        }
        (temp_cache_dir / "old_key.json").write_text(json.dumps({"data": "legacy_value"}))
        (temp_cache_dir / "cache_metadata.json").write_text(json.dumps(legacy_metadata))

        cache = PersistentCache(cache_dir=temp_cache_dir)
        assert not (temp_cache_dir / "old_key.meta").exists()

        # Act
        result = cache.get("old_key")

        # Assert -- served correctly, and now migrated to the fast path.
        assert result == {"data": "legacy_value"}
        assert (temp_cache_dir / "old_key.meta").exists()
        migrated = json.loads((temp_cache_dir / "old_key.meta").read_text())
        assert migrated["expires_at"] == legacy_metadata["old_key"]["expires_at"]

        # A second get() must succeed via the sidecar without needing the
        # legacy file at all.
        (temp_cache_dir / "cache_metadata.json").unlink()
        assert cache.get("old_key") == {"data": "legacy_value"}

    def test_get_legacy_format_expired_entry_is_invalidated(self, temp_cache_dir):
        """An expired entry recorded only in the legacy index must still expire."""
        # Arrange
        now = datetime.now()
        legacy_metadata = {
            "old_key": {
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "expires_at": (now - timedelta(hours=1)).isoformat(),
            }
        }
        (temp_cache_dir / "old_key.json").write_text(json.dumps({"data": "stale"}))
        (temp_cache_dir / "cache_metadata.json").write_text(json.dumps(legacy_metadata))

        cache = PersistentCache(cache_dir=temp_cache_dir)

        # Act
        result = cache.get("old_key")

        # Assert
        assert result is None
        assert not (temp_cache_dir / "old_key.json").exists()

    def test_cleanup_expired_sweeps_legacy_and_sidecar_entries(self, temp_cache_dir):
        """cleanup_expired() must remove expired entries in both formats."""
        # Arrange -- one expired legacy-only entry, one live legacy-only entry,
        # plus a normal sidecar entry written through the current cache.
        now = datetime.now()
        legacy_metadata = {
            "legacy_expired": {
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "expires_at": (now - timedelta(hours=1)).isoformat(),
            },
            "legacy_live": {
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
            },
        }
        for key in legacy_metadata:
            (temp_cache_dir / f"{key}.json").write_text(json.dumps({"data": key}))
        (temp_cache_dir / "cache_metadata.json").write_text(json.dumps(legacy_metadata))

        cache = PersistentCache(cache_dir=temp_cache_dir)
        cache.set("sidecar_expired", {"data": "x"}, ttl_hours=0.0001)
        cache.set("sidecar_live", {"data": "y"}, ttl_hours=10.0)
        time.sleep(0.5)

        # Act
        removed = cache.cleanup_expired()

        # Assert
        assert removed == 2
        assert cache.get("legacy_expired") is None
        assert cache.get("legacy_live") == {"data": "legacy_live"}
        assert cache.get("sidecar_expired") is None
        assert cache.get("sidecar_live") == {"data": "y"}

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
        """Concurrent set() must not lose entries.

        Under the old shared-cache_metadata.json format this was a genuine
        read-modify-write race: unguarded, interleaved threads each wrote back
        a copy missing the others' keys, and a cache file whose metadata entry
        was dropped was served forever (never seen as expired). Under the
        per-key sidecar format each key owns its own metadata file, so the
        race is structurally impossible -- this test now guards against a
        regression back to a shared file, or any other way a concurrent
        writer could clobber another key's bookkeeping.
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

        # Assert -- every key has its own sidecar metadata file, and it's valid.
        for key in keys:
            meta_path = temp_cache_dir / f"{key}.meta"
            assert meta_path.exists(), f"missing sidecar metadata for {key}"
            entry = json.loads(meta_path.read_text())
            assert "created_at" in entry and "expires_at" in entry

        reloaded = PersistentCache(cache_dir=temp_cache_dir)
        for key in keys:
            assert reloaded.get(key) == {"data": key}

    def test_concurrent_set_and_invalidate_do_not_corrupt_metadata(
        self, cache, temp_cache_dir
    ):
        """Mixed writers and removers must not corrupt or lose each other's metadata."""
        # Arrange
        keys = [f"key_{i}" for i in range(30)]
        for key in keys:
            cache.set(key, {"data": key})
        doomed = set(keys[:15])
        survivors = set(keys) - doomed

        def worker(key):
            if key in doomed:
                cache.invalidate(key)
            else:
                cache.set(key, {"data": "rewritten"})

        # Act
        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(worker, keys))

        # Assert
        for key in doomed:
            assert cache.get(key) is None
            assert not (temp_cache_dir / f"{key}.meta").exists()
        for key in survivors:
            meta_path = temp_cache_dir / f"{key}.meta"
            assert meta_path.exists()
            entry = json.loads(meta_path.read_text())  # still parseable JSON
            assert "expires_at" in entry
            assert cache.get(key) == {"data": "rewritten"}

    def test_concurrent_get_migrates_legacy_cache_without_corruption(
        self, temp_cache_dir
    ):
        """Concurrent reads against a still-shared legacy index must not corrupt it.

        Pre-sidecar cache directories keep every key's metadata in one shared
        cache_metadata.json. The migration-on-read path (_get_entry_meta's
        legacy fallback) still loads and, on a hit, writes a sidecar for that
        one key -- it does not touch the shared file itself, but this is the
        one remaining place several threads can be driven through the same
        legacy read concurrently. Nothing should be lost or corrupted.
        """
        # Arrange -- write an old-format cache directory by hand: one shared
        # cache_metadata.json plus bare data files, no sidecars.
        keys = [f"legacy_key_{i}" for i in range(40)]
        legacy_metadata = {}
        now = datetime.now()
        for key in keys:
            (temp_cache_dir / f"{key}.json").write_text(json.dumps({"data": key}))
            legacy_metadata[key] = {
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
            }
        (temp_cache_dir / "cache_metadata.json").write_text(json.dumps(legacy_metadata))

        cache = PersistentCache(cache_dir=temp_cache_dir)
        start = threading.Barrier(len(keys), timeout=10)

        def reader(key):
            start.wait()
            return cache.get(key)

        # Act
        with ThreadPoolExecutor(max_workers=len(keys)) as executor:
            results = list(executor.map(reader, keys))

        # Assert -- every read succeeded and every key migrated to its own sidecar.
        assert results == [{"data": key} for key in keys]
        for key in keys:
            assert (temp_cache_dir / f"{key}.meta").exists()
        # The legacy index itself must still be valid JSON (not truncated/corrupted).
        json.loads((temp_cache_dir / "cache_metadata.json").read_text())

    def test_concurrent_get_during_set_publish_window_does_not_lose_data(
        self, cache, temp_cache_dir, monkeypatch
    ):
        """Regression test for PR #26 review finding 1.

        set() writes the data file, then (previously) released the lock
        boundary before writing the sidecar metadata. A get() landing in
        that gap saw a data file with no metadata anywhere -- indistinguishable
        from a true orphan -- and the #14 fail-closed path deleted the data
        file this very set() had just written. set() then wrote its sidecar
        for a file that no longer existed and returned success: a completed
        write silently discarded.

        Deterministically forces that interleaving via a monkeypatched hook
        (`_after_data_write`, a no-op test seam called mid-set(), after the
        data write and before the sidecar write) instead of sleeps, so this
        cannot be flaky in CI. The hook fires at the same point in the
        function regardless of the fix; what changes is whether it fires
        while `_METADATA_LOCK` is held. If the lock now spans both writes
        (the fix), a concurrent get() attempting to acquire it blocks until
        set() finishes publishing -- so it can never observe, and therefore
        never delete, the half-published entry.
        """
        # Arrange
        key = "race_key"
        value = {"data": "value"}

        data_written = threading.Event()
        proceed_with_meta = threading.Event()

        def hook(self):
            data_written.set()
            # If the lock is held here (the fix), a concurrent get() cannot
            # make progress until proceed_with_meta is set below and this
            # hook returns. If the lock is NOT held here (the bug), a
            # concurrent get() runs to completion immediately.
            proceed_with_meta.wait(timeout=5)

        monkeypatch.setattr(PersistentCache, "_after_data_write", hook)

        get_result = {}

        def setter():
            cache.set(key, value)

        def getter():
            get_result["value"] = cache.get(key)

        # Act
        setter_thread = threading.Thread(target=setter)
        setter_thread.start()
        assert data_written.wait(timeout=5), "set() never reached the post-data-write hook"

        # At this instant the data file is on disk but the sidecar is not --
        # exactly the window finding 1 describes. A get() started now must
        # not be able to run to completion (and thus must not be able to
        # wrongly invalidate anything) until set() finishes publishing.
        getter_thread = threading.Thread(target=getter)
        getter_thread.start()
        getter_thread.join(timeout=0.3)
        assert getter_thread.is_alive(), (
            "get() completed while set() was still mid-publish -- the "
            "data-to-metadata publication window is observable as an "
            "orphan, which is exactly the finding-1 race"
        )

        proceed_with_meta.set()
        setter_thread.join(timeout=5)
        getter_thread.join(timeout=5)

        # Assert -- the write completed successfully and nothing was lost:
        # the concurrent getter (once unblocked) sees the real value, a
        # fresh get() sees it too, and the sidecar exists.
        assert not setter_thread.is_alive()
        assert not getter_thread.is_alive()
        assert get_result["value"] == value
        assert cache.get(key) == value
        assert (temp_cache_dir / "race_key.meta").exists()
        assert (temp_cache_dir / "race_key.json").exists()

    def test_corrupt_sidecar_falls_back_to_valid_legacy_entry(self, temp_cache_dir):
        """Regression test for PR #26 review finding 2.

        Simulates an interrupted migration: a truncated/corrupt <key>.meta
        sits next to a still-valid legacy cache_metadata.json record for the
        same key. Metadata lookup must not treat the unreadable sidecar as
        authoritative absence -- it must fall back to the legacy entry
        rather than causing get() to delete an otherwise-readable data file.
        """
        # Arrange
        now = datetime.now()
        legacy_metadata = {
            "old_key": {
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
            }
        }
        (temp_cache_dir / "old_key.json").write_text(json.dumps({"data": "legacy_value"}))
        (temp_cache_dir / "cache_metadata.json").write_text(json.dumps(legacy_metadata))
        # A sidecar that exists but is truncated/corrupt, as an interrupted
        # migration write could leave behind.
        (temp_cache_dir / "old_key.meta").write_text("{not valid json")

        cache = PersistentCache(cache_dir=temp_cache_dir)

        # Act
        result = cache.get("old_key")

        # Assert -- served from the still-valid legacy entry, not destroyed.
        assert result == {"data": "legacy_value"}
        assert (temp_cache_dir / "old_key.json").exists()
        # The corrupt sidecar should have been repaired (overwritten), not
        # left truncated.
        migrated = json.loads((temp_cache_dir / "old_key.meta").read_text())
        assert migrated["expires_at"] == legacy_metadata["old_key"]["expires_at"]

    def test_get_stats_excludes_invalidated_legacy_only_entry(self, temp_cache_dir):
        """Regression test for PR #26 review finding 4.

        invalidate() removes a legacy-only key's data file and sidecar but,
        by design, does not rewrite the shared legacy index (see set()'s
        comment on why that would reintroduce O(n) cost). get_stats() must
        not keep counting the entry using the stale legacy record alone.
        """
        # Arrange
        now = datetime.now()
        legacy_metadata = {
            "legacy_key": {
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
            }
        }
        (temp_cache_dir / "legacy_key.json").write_text(json.dumps({"data": "x"}))
        (temp_cache_dir / "cache_metadata.json").write_text(json.dumps(legacy_metadata))

        cache = PersistentCache(cache_dir=temp_cache_dir)
        assert cache.get_stats()["entries"] == 1

        # Act -- invalidate the legacy-only entry without ever migrating it
        # to a sidecar first.
        cache.invalidate("legacy_key")

        # Assert -- excluded immediately, not counted until the legacy TTL
        # would otherwise expire and cleanup_expired() sweeps it.
        assert cache.get_stats()["entries"] == 0
