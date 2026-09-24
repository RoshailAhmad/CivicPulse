"""Read-through cache for /api/stats: TTL 30 s AND explicit invalidation.

Invalidation makes a new complaint show up immediately; the TTL is the
safety net if an invalidation is ever missed (e.g. Redis blip during a write)."""

import json
import logging
from typing import Any

from redis import Redis, RedisError

from app.repositories.complaints import ComplaintRepository

logger = logging.getLogger(__name__)
STATS_KEY = "stats:v1"


class StatsCache:
    def __init__(self, redis: Redis, ttl_seconds: int = 30) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def get(self) -> dict[str, Any] | None:
        try:
            raw = self._redis.get(STATS_KEY)
        except RedisError:
            return None
        return json.loads(str(raw)) if raw else None

    def set(self, data: dict[str, Any]) -> None:
        try:
            self._redis.set(STATS_KEY, json.dumps(data), ex=self._ttl)
        except RedisError:
            logger.warning("stats cache write failed")

    def invalidate(self) -> None:
        try:
            self._redis.delete(STATS_KEY)
        except RedisError:
            logger.warning("stats cache invalidation failed; TTL will expire it")


class StatsService:
    def __init__(self, repo: ComplaintRepository, cache: StatsCache) -> None:
        self._repo = repo
        self._cache = cache

    def get_stats(self) -> tuple[dict[str, Any], bool]:
        """Returns (stats, cache_hit)."""
        cached = self._cache.get()
        if cached is not None:
            return cached, True
        data = self._repo.stats()
        self._cache.set(data)
        return data, False
