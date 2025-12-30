"""
Persistent file-based cache with configurable TTL.

This module provides a cache that stores data in JSON files within a cache directory.
Each cache entry includes metadata for expiration tracking.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from platformdirs import user_cache_dir

logger = logging.getLogger(__name__)


class PersistentCache:
    """
    File-based cache with configurable TTL.

    Stores JSON data in files within a cache directory.
    Each cache entry includes metadata for expiration tracking.

    Attributes:
        cache_dir: Path to the cache directory.
        default_ttl_hours: Default time-to-live in hours.
    """

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
        self._metadata_file = self.cache_dir / "cache_metadata.json"

    def _get_cache_path(self, key: str) -> Path:
        """
        Get the file path for a cache key.

        Args:
            key: Cache key.

        Returns:
            Path to the cache file.
        """
        # Sanitize key for filesystem
        safe_key = key.replace(":", "_").replace("/", "_").replace(" ", "_")
        return self.cache_dir / f"{safe_key}.json"

    def _load_metadata(self) -> Dict[str, Dict[str, str]]:
        """
        Load cache metadata from file.

        Returns:
            Dictionary of cache key to metadata.
        """
        if not self._metadata_file.exists():
            return {}

        try:
            with open(self._metadata_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache metadata: {e}")
            return {}

    def _save_metadata(self, metadata: Dict[str, Dict[str, str]]) -> None:
        """
        Save cache metadata to file.

        Args:
            metadata: Dictionary of cache key to metadata.
        """
        try:
            with open(self._metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def get(self, key: str) -> Any | None:
        """
        Get a value from the persistent cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        # Check metadata for expiration
        metadata = self._load_metadata()
        entry_meta = metadata.get(key, {})

        if entry_meta:
            expires_at_str = entry_meta.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() > expires_at:
                        self.invalidate(key)
                        return None
                except ValueError as e:
                    logger.warning(f"Invalid expiration date for key {key}: {e}")
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

        # Save data
        try:
            with open(cache_path, "w") as f:
                json.dump(value, f)
        except (TypeError, IOError) as e:
            logger.warning(f"Failed to save cache for key {key}: {e}")
            return

        # Update metadata
        metadata = self._load_metadata()
        now = datetime.now()
        metadata[key] = {
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=ttl)).isoformat(),
        }
        self._save_metadata(metadata)

    def invalidate(self, key: str) -> None:
        """
        Remove a specific cache entry.

        Args:
            key: Cache key to invalidate.
        """
        cache_path = self._get_cache_path(key)

        # Remove cache file
        if cache_path.exists():
            try:
                cache_path.unlink()
            except IOError as e:
                logger.warning(f"Failed to delete cache file for key {key}: {e}")

        # Remove from metadata
        metadata = self._load_metadata()
        if key in metadata:
            del metadata[key]
            self._save_metadata(metadata)

    def clear(self) -> None:
        """
        Clear all cache entries.
        """
        # Remove all cache files
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file != self._metadata_file:
                try:
                    cache_file.unlink()
                except IOError as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

        # Clear metadata
        self._save_metadata({})

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed.
        """
        metadata = self._load_metadata()
        now = datetime.now()
        removed = 0

        keys_to_remove = []
        for key, entry_meta in metadata.items():
            expires_at_str = entry_meta.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if now > expires_at:
                        keys_to_remove.append(key)
                except ValueError:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            self.invalidate(key)
            removed += 1

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (entries count, total size).
        """
        metadata = self._load_metadata()
        total_size = 0

        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file != self._metadata_file:
                total_size += cache_file.stat().st_size

        return {
            "entries": len(metadata),
            "size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
        }
