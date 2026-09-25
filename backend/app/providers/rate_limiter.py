"""Distributed fixed-window rate limiter in Redis.

It must live in Redis, not a Python dict: with 4 pods, an in-process
limiter would allow 4x the traffic, because each pod counts separately."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from redis import Redis, RedisError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class RateLimiter:
    def __init__(
        self,
        redis: Redis,
        limit: int,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis = redis
        self._limit = limit
        self._window = window_seconds
        self._clock = clock

    def hit(self, client_id: str) -> RateLimitDecision:
        now = self._clock()
        window_start = int(now // self._window)
        key = f"ratelimit:complaints:{client_id}:{window_start}"
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self._window)
            count = int(pipe.execute()[0])
        except RedisError:
            # Fail open: a Redis blip should not stop citizens reporting a flood.
            logger.warning("rate limiter unavailable, allowing request", exc_info=True)
            return RateLimitDecision(allowed=True)

        if count > self._limit:
            retry_after = max(1, int(self._window - (now % self._window)))
            return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
        return RateLimitDecision(allowed=True)
