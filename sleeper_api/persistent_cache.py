"""
Persistent file-based cache with configurable TTL.

This module provides a cache that stores data in JSON files within a cache directory.
Each cache entry has its own sidecar metadata file (`<key>.meta`) tracking expiration,
so writing or invalidating one entry never touches another entry's bookkeeping.

Cache directories created before this sidecar format existed used a single shared
`cache_metadata.json` indexing every key. That file is still read as a fallback: the
first access to a not-yet-migrated key transparently promotes its entry to a sidecar
file. See CHANGELOG for details.
"""
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from platformdirs import user_cache_dir

logger = logging.getLogger(__name__)

# Serializes metadata mutations. With per-key sidecar files, two threads calling
# set() for *different* keys never touch the same file, so they no longer need
# this lock to avoid stomping on each other. It is kept, and still guards every
# metadata read/write, because two other paths still share state: (1) the legacy
# `cache_metadata.json` fallback/migration path used by pre-upgrade cache
# directories, and (2) get()'s read-then-maybe-delete of a single key's own
# metadata, which must stay atomic with respect to a concurrent set()/invalidate()
# of that same key. Re-entrant because cleanup_expired() drives invalidate()-style
# file removal while already holding it.
_METADATA_LOCK = threading.RLock()


class PersistentCache:
    """
    File-based cache with configurable TTL.

    Stores JSON data in files within a cache directory.
    Each cache entry has a sidecar metadata file for expiration tracking.

    Attributes:
        cache_dir: Path to the cache directory.
        default_ttl_hours: Default time-to-live in hours.
    """

    # Suffix for per-key metadata sidecar files. Deliberately not ".json" so it
    # can never collide with the `*.json` globs used elsewhere for data files.
    _META_SUFFIX = ".meta"

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        default_ttl_hours: float = 1.0,
    ):
        """
        Initialize the persistent cache.

        Args:
            cache_dir: Directory for cache files. If None, uses platform-specific cache dir.
            default_ttl_hours: Default time-to-live in hours for cache entries.
        """
        if cache_dir is None:
            cache_dir = Path(user_cache_dir(appname="sleeper_api", appauthor="smallery"))

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_hours = default_ttl_hours
        # Legacy shared index from before the sidecar format. Only read as a
        # fallback and to sweep pre-migration entries in cleanup_expired().
        self._metadata_file = self.cache_dir / "cache_metadata.json"

    @staticmethod
    def _safe_key(key: str) -> str:
        """Sanitize a cache key for use in a filename."""
        return key.replace(":", "_").replace("/", "_").replace(" ", "_")

    def _get_cache_path(self, key: str) -> Path:
        """
        Get the file path for a cache key's data.

        Args:
            key: Cache key.

        Returns:
            Path to the cache data file.
        """
        return self.cache_dir / f"{self._safe_key(key)}.json"

    def _get_meta_path(self, key: str) -> Path:
        """
        Get the file path for a cache key's sidecar metadata.

        Args:
            key: Cache key.

        Returns:
            Path to the cache key's metadata file.
        """
        return self.cache_dir / f"{self._safe_key(key)}{self._META_SUFFIX}"

    def _load_legacy_metadata(self) -> Dict[str, Dict[str, str]]:
        """
        Load the legacy shared `cache_metadata.json` index, if present.

        Returns:
            Dictionary of cache key to metadata. Empty if the file is absent,
            unreadable, or corrupt.
        """
        if not self._metadata_file.exists():
            return {}

        try:
            with open(self._metadata_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            return {}

    def _save_legacy_metadata(self, metadata: Dict[str, Dict[str, str]]) -> None:
        """
        Save the legacy shared `cache_metadata.json` index.

        Args:
            metadata: Dictionary of cache key to metadata.
        """
        try:
            with open(self._metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def _write_entry_meta(self, key: str, entry_meta: Dict[str, str]) -> None:
        """
        Write a key's sidecar metadata file. O(1): touches only this key's file.

        Args:
            key: Cache key.
            entry_meta: Metadata dict (created_at / expires_at).
        """
        try:
            with open(self._get_meta_path(key), "w") as f:
                json.dump(entry_meta, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache metadata for key {key}: {e}")

    def _get_entry_meta(self, key: str) -> Optional[Dict[str, str]]:
        """
        Look up a key's metadata. Caller must hold `_METADATA_LOCK`.

        Checks the key's own sidecar file first (O(1)). If absent, falls back to
        the legacy shared index for backwards compatibility with cache
        directories written before the sidecar format existed -- and, on a hit,
        migrates the entry by writing its sidecar file, so this O(n) fallback is
        paid at most once per key.

        Args:
            key: Cache key.

        Returns:
            Metadata dict, or None if no metadata exists for this key anywhere.
        """
        meta_path = self._get_meta_path(key)
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache metadata for key {key}: {e}")
                return None

        legacy_entry = self._load_legacy_metadata().get(key)
        if legacy_entry:
            self._write_entry_meta(key, legacy_entry)
            return legacy_entry

        return None

    def get(self, key: str) -> Any | None:
        """
        Get a value from the persistent cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found, expired, or missing metadata.
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        # Check metadata for expiration. Read once: a missing or expired entry
        # is handled with the metadata already in hand, never by re-reading it.
        with _METADATA_LOCK:
            entry_meta = self._get_entry_meta(key)

            if entry_meta is None:
                # Fail closed: a data file with no metadata anywhere (sidecar or
                # legacy index) cannot be vouched for as fresh, so it must not
                # be served -- serving it forever is exactly what made the old
                # metadata write race in the concurrent-projections work
                # damaging rather than merely lossy. Self-heal by removing the
                # orphan file so it isn't re-evaluated on every future get().
                self._invalidate_locked(key)
                return None

            expires_at_str = entry_meta.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                except ValueError as e:
                    logger.warning(f"Invalid expiration date for key {key}: {e}")
                    self._invalidate_locked(key)
                    return None

                if datetime.now() > expires_at:
                    self._invalidate_locked(key)
                    return None

        # Load from file
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_hours: Optional[float] = None) -> None:
        """
        Store a value in the persistent cache.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON serializable).
            ttl_hours: Time-to-live in hours. If None, uses default_ttl_hours.
        """
        ttl = ttl_hours if ttl_hours is not None else self.default_ttl_hours
        cache_path = self._get_cache_path(key)

        # Serialize before opening the file, for two reasons. json.dumps() uses
        # the C encoder in one shot, while json.dump(obj, f) falls back to the
        # pure-Python incremental encoder -- measured 5x faster on a ~0.55 MB
        # projections payload (44ms -> 8.5ms), and this is the dominant cost of
        # a bulk fetch once the network is parallelized. It also means a payload
        # that fails to serialize leaves no half-written file behind.
        try:
            serialized = json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize cache value for key {key}: {e}")
            return

        try:
            with open(cache_path, "w") as f:
                f.write(serialized)
        except IOError as e:
            logger.warning(f"Failed to save cache for key {key}: {e}")
            return

        # Update this key's own metadata sidecar. O(1): unlike the old shared
        # cache_metadata.json, this never reads or rewrites any other key's
        # bookkeeping, so cost does not grow with the number of cached entries
        # (see the set() benchmark in the PR description). We deliberately do
        # NOT also touch the legacy shared index here -- doing so would read
        # and rewrite it in full on every set(), reintroducing the exact O(n)
        # cost this change removes. A stale legacy entry left behind for this
        # key is harmless: get() always checks the sidecar first, and
        # cleanup_expired() sweeps stale legacy entries for keys that already
        # have a sidecar.
        now = datetime.now()
        entry_meta = {
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=ttl)).isoformat(),
        }
        with _METADATA_LOCK:
            self._write_entry_meta(key, entry_meta)

    def _invalidate_locked(self, key: str) -> None:
        """
        Remove a cache entry's data file and sidecar metadata file.

        Caller must hold `_METADATA_LOCK`. O(1): only this key's two files are
        touched. Does not touch the legacy shared index -- see set()'s comment
        on why that would reintroduce O(n) cost; a stale legacy entry for an
        invalidated key is harmless (get() checks cache_path.exists() before
        ever consulting metadata) and is swept by cleanup_expired().

        Args:
            key: Cache key to invalidate.
        """
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                cache_path.unlink()
            except IOError as e:
                logger.warning(f"Failed to delete cache file for key {key}: {e}")

        meta_path = self._get_meta_path(key)
        if meta_path.exists():
            try:
                meta_path.unlink()
            except IOError as e:
                logger.warning(f"Failed to delete cache metadata file for key {key}: {e}")

    def invalidate(self, key: str) -> None:
        """
        Remove a specific cache entry.

        Args:
            key: Cache key to invalidate.
        """
        with _METADATA_LOCK:
            self._invalidate_locked(key)

    def _delete_entry_files_by_safe_key(self, safe_key: str) -> None:
        """
        Delete a cache entry's data and sidecar metadata files by sanitized key.

        Used by cleanup_expired(), which discovers expired sidecar files by
        globbing the directory and therefore only has the sanitized filename
        stem, not the original key string.

        Args:
            safe_key: Sanitized key, as produced by `_safe_key()`.
        """
        for path in (
            self.cache_dir / f"{safe_key}.json",
            self.cache_dir / f"{safe_key}{self._META_SUFFIX}",
        ):
            if path.exists():
                try:
                    path.unlink()
                except IOError as e:
                    logger.warning(f"Failed to delete cache file {path}: {e}")

    def clear(self) -> None:
        """
        Clear all cache entries.
        """
        with _METADATA_LOCK:
            # Remove all cache data files
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file != self._metadata_file:
                    try:
                        cache_file.unlink()
                    except IOError as e:
                        logger.warning(f"Failed to delete cache file {cache_file}: {e}")

            # Remove all sidecar metadata files
            for meta_file in self.cache_dir.glob(f"*{self._META_SUFFIX}"):
                try:
                    meta_file.unlink()
                except IOError as e:
                    logger.warning(f"Failed to delete cache file {meta_file}: {e}")

            # Remove the legacy shared index, if any
            if self._metadata_file.exists():
                try:
                    self._metadata_file.unlink()
                except IOError as e:
                    logger.warning(f"Failed to delete cache metadata file: {e}")

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Sweeps both current-format sidecar files and any entries still only in
        the legacy shared index (i.e. never accessed since upgrading, so never
        migrated). This is an O(n) directory/index scan by nature -- unlike
        set()/get()/invalidate(), it must look at every entry to find the
        expired ones, so it is not a hot path this change targets.

        Returns:
            Number of entries removed.
        """
        with _METADATA_LOCK:
            now = datetime.now()
            removed = 0
            migrated_safe_keys = set()

            # Current-format entries.
            for meta_path in list(self.cache_dir.glob(f"*{self._META_SUFFIX}")):
                safe_key = meta_path.name[: -len(self._META_SUFFIX)]
                migrated_safe_keys.add(safe_key)

                expired = False
                try:
                    with open(meta_path, "r") as f:
                        entry_meta = json.load(f)
                    expires_at_str = entry_meta.get("expires_at")
                    if expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if now > expires_at:
                            expired = True
                except (json.JSONDecodeError, IOError, ValueError):
                    # Corrupt sidecar: fail closed and drop the entry.
                    expired = True

                if expired:
                    self._delete_entry_files_by_safe_key(safe_key)
                    removed += 1

            # Entries still only in the legacy shared index.
            if self._metadata_file.exists():
                legacy = self._load_legacy_metadata()
                legacy_changed = False

                for key, entry_meta in list(legacy.items()):
                    safe_key = self._safe_key(key)

                    if safe_key in migrated_safe_keys:
                        # Already evaluated above via its sidecar file; drop
                        # the stale legacy copy so this index shrinks toward
                        # empty as the cache is used.
                        del legacy[key]
                        legacy_changed = True
                        continue

                    expires_at_str = entry_meta.get("expires_at")
                    is_expired = False
                    if expires_at_str:
                        try:
                            expires_at = datetime.fromisoformat(expires_at_str)
                            is_expired = now > expires_at
                        except ValueError:
                            is_expired = True

                    if is_expired:
                        self._delete_entry_files_by_safe_key(safe_key)
                        del legacy[key]
                        legacy_changed = True
                        removed += 1

                if legacy_changed:
                    self._save_legacy_metadata(legacy)

            return removed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (entries count, total size).
        """
        meta_files = list(self.cache_dir.glob(f"*{self._META_SUFFIX}"))
        counted_safe_keys = {p.name[: -len(self._META_SUFFIX)] for p in meta_files}
        entries = len(counted_safe_keys)

        # Count not-yet-migrated legacy entries once each, without double
        # counting keys that already have a sidecar.
        if self._metadata_file.exists():
            for key in self._load_legacy_metadata():
                if self._safe_key(key) not in counted_safe_keys:
                    entries += 1

        total_size = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file != self._metadata_file:
                total_size += cache_file.stat().st_size

        return {
            "entries": entries,
            "size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
        }
