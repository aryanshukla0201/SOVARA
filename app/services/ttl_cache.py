from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Bounded in-memory TTL cache with deterministic LRU eviction."""

    def __init__(
        self,
        *,
        max_size: int = 256,
        ttl_seconds: float = 300.0,
        clock=time.monotonic,
    ) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: OrderedDict[str, _CacheEntry[T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None

        if entry.expires_at <= self._clock():
            self._entries.pop(key, None)
            return None

        self._entries.move_to_end(key)
        return entry.value

    def set(self, key: str, value: T) -> None:
        now = self._clock()
        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=now + self.ttl_seconds,
        )
        self._entries.move_to_end(key)

        while len(self._entries) > self.max_size:
            self._entries.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
