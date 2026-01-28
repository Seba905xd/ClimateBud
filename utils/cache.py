"""Caching utilities for ClimateBud data fetching."""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional

import config


class Cache:
    """Simple file-based cache for API responses."""

    def __init__(self, cache_dir: str = None, expiry_hours: int = None):
        self.cache_dir = cache_dir or config.CACHE_DIR
        self.expiry_hours = expiry_hours or config.CACHE_EXPIRY_HOURS
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_key(self, key: str) -> str:
        """Generate a hash-based filename for the cache key."""
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        """Get the full path for a cache file."""
        return os.path.join(self.cache_dir, f"{self._get_cache_key(key)}.json")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if valid."""
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            # Check expiry
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cached_time > timedelta(hours=self.expiry_hours):
                os.remove(cache_path)
                return None

            return cached["data"]
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def set(self, key: str, data: Any) -> None:
        """Store data in cache."""
        cache_path = self._get_cache_path(key)
        cached = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        with open(cache_path, "w") as f:
            json.dump(cached, f)

    def clear(self) -> None:
        """Clear all cached data."""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                os.remove(os.path.join(self.cache_dir, filename))

    def invalidate(self, key: str) -> None:
        """Remove a specific cache entry."""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            os.remove(cache_path)
