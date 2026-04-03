"""
Simple thread-safe in-memory TTL cache.

Usage:
    from app.utils.cache import cache

    value = cache.get("my_key")
    if value is None:
        value = expensive_operation()
        cache.set("my_key", value, ttl=60)   # cache for 60 s

    cache.delete("my_key")   # invalidate manually
"""

import threading
import time
from typing import Any


class _TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 60) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Module-level singleton — import and use directly.
cache = _TTLCache()
