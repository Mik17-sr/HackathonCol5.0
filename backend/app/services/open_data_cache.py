from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.config import get_settings


@dataclass
class CacheEntry:
    expires_at: float
    value: list[dict[str, Any]]


class OpenDataCache:
    def __init__(self, ttl_seconds: int = 86400, redis_url: str | None = None) -> None:
        self.ttl_seconds = ttl_seconds
        self.redis_url = redis_url
        self._redis: Any = None
        self._entries: dict[str, CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_set(
        self,
        key: str,
        loader: Callable[[], Awaitable[list[dict[str, Any]]]],
    ) -> list[dict[str, Any]]:
        redis_value = await self._redis_get(key)
        if redis_value is not None:
            return redis_value
        cached = self._entries.get(key)
        if cached and cached.expires_at > time.monotonic():
            return cached.value

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._entries.get(key)
            if cached and cached.expires_at > time.monotonic():
                return cached.value
            value = await loader()
            if value:
                self._entries[key] = CacheEntry(
                    expires_at=time.monotonic() + self.ttl_seconds,
                    value=value,
                )
                await self._redis_set(key, value)
            return value

    def clear(self) -> None:
        self._entries.clear()

    async def _redis_get(self, key: str) -> list[dict[str, Any]] | None:
        client = await self._get_redis()
        if client is None:
            return None
        try:
            value = await client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def _redis_set(self, key: str, value: list[dict[str, Any]]) -> None:
        client = await self._get_redis()
        if client is None:
            return
        try:
            await client.set(key, json.dumps(value), ex=self.ttl_seconds)
        except Exception:
            return

    async def _get_redis(self) -> Any:
        if not self.redis_url:
            return None
        if self._redis is None:
            try:
                from redis import asyncio as redis

                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis


open_data_cache = OpenDataCache(
    ttl_seconds=get_settings().source_config.cache_ttl_seconds,
    redis_url=get_settings().source_config.redis_url,
)
