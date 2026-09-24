"""Triage orchestration: cache -> provider (timeout, one jittered retry)
-> fallback to rules. A caller never sees an exception from here."""

import hashlib
import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis import Redis, RedisError

from app.domain import FALLBACK_PROVIDER, TriageResult
from app.metrics import TRIAGE_CACHE, TRIAGE_FALLBACKS, TRIAGE_LATENCY
from app.providers.triage.base import RetryableTriageError, TriageProvider
from app.providers.triage.rules import RuleBasedTriage

logger = logging.getLogger(__name__)

RECENT_KEY = "triage:recent"
HITS_KEY = "triage:cache:hits"
MISSES_KEY = "triage:cache:misses"


@dataclass(frozen=True)
class TriageOutcome:
    result: TriageResult
    triaged_by: str
    latency_ms: int
    cache_hit: bool


def content_hash(text: str) -> str:
    """Same complaint, different spacing or capitals -> same hash."""
    normalised = " ".join(text.lower().split())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


class TriageService:
    def __init__(
        self,
        provider: TriageProvider,
        redis: Redis,
        cache_ttl_seconds: int = 86_400,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._provider = provider
        self._fallback = RuleBasedTriage()
        self._redis = redis
        self._ttl = cache_ttl_seconds
        self._sleep = sleep  # injectable, so tests never really sleep
        self._jitter = jitter

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def triage(self, complaint_id: UUID, text: str, location: str) -> TriageOutcome:
        start = time.perf_counter()
        cache_key = f"triage:v1:{content_hash(text)}"

        cached = self._cache_get(cache_key)
        if cached is not None:
            result = TriageResult.model_validate(cached["result"])
            outcome = self._finish(start, result, cached["triaged_by"], cache_hit=True)
            self._record(outcome, fallback=False, error=None)
            return outcome

        error: str | None = None
        try:
            result = self._call_with_retry(text, location)
            triaged_by = self._provider.name
            self._cache_set(cache_key, result, triaged_by)
        except Exception as exc:  # noqa: BLE001 - any provider failure means fallback
            error = type(exc).__name__
            logger.warning(
                "triage fallback",
                extra={
                    "complaint_id": str(complaint_id),
                    "provider": self._provider.name,
                    "error_class": error,
                    "error": str(exc)[:200],
                },
            )
            TRIAGE_FALLBACKS.labels(provider=self._provider.name, error=error).inc()
            result = self._fallback.triage(text, location)
            triaged_by = FALLBACK_PROVIDER  # not cached: next time the LLM gets a chance

        outcome = self._finish(start, result, triaged_by, cache_hit=False)
        self._record(outcome, fallback=error is not None, error=error)
        return outcome

    def _call_with_retry(self, text: str, location: str) -> TriageResult:
        try:
            return self._provider.triage(text, location)
        except RetryableTriageError:
            # Retry ONCE, only for timeout/429/5xx, after 0.5-1.5 s of jitter
            # so many pods don't all retry at the same instant.
            self._sleep(0.5 + self._jitter())
            return self._provider.triage(text, location)

    def _finish(
        self, start: float, result: TriageResult, triaged_by: str, cache_hit: bool
    ) -> TriageOutcome:
        elapsed = time.perf_counter() - start
        TRIAGE_LATENCY.labels(provider=triaged_by).observe(elapsed)
        return TriageOutcome(result, triaged_by, int(elapsed * 1000), cache_hit)

    # ---- Redis helpers: a Redis failure must never break triage ----
    def _cache_get(self, key: str) -> dict[str, Any] | None:
        try:
            raw = self._redis.get(key)
            self._redis.incr(HITS_KEY if raw else MISSES_KEY)
        except RedisError:
            return None
        TRIAGE_CACHE.labels(result="hit" if raw else "miss").inc()
        return json.loads(str(raw)) if raw else None

    def _cache_set(self, key: str, result: TriageResult, triaged_by: str) -> None:
        payload = {"result": result.model_dump(mode="json"), "triaged_by": triaged_by}
        try:
            self._redis.set(key, json.dumps(payload), ex=self._ttl)
        except RedisError:
            logger.warning("triage cache write failed")

    def _record(self, outcome: TriageOutcome, *, fallback: bool, error: str | None) -> None:
        entry = {
            "provider": outcome.triaged_by,
            "latency_ms": outcome.latency_ms,
            "fallback": fallback,
            "cache_hit": outcome.cache_hit,
            "error": error,
            "at": datetime.now(UTC).isoformat(),
        }
        try:
            pipe = self._redis.pipeline()
            pipe.lpush(RECENT_KEY, json.dumps(entry))
            pipe.ltrim(RECENT_KEY, 0, 19)  # keep the last 20
            pipe.execute()
        except RedisError:
            pass

    def meta(self) -> dict[str, Any]:
        try:
            recent = [json.loads(x) for x in self._redis.lrange(RECENT_KEY, 0, 19)]  # type: ignore[union-attr]
            hits = int(self._redis.get(HITS_KEY) or 0)  # type: ignore[arg-type]
            misses = int(self._redis.get(MISSES_KEY) or 0)  # type: ignore[arg-type]
        except RedisError:
            recent, hits, misses = [], 0, 0
        total = hits + misses
        return {
            "active_provider": self._provider.name,
            "recent": recent,
            "triage_cache": {
                "hits": hits,
                "misses": misses,
                "hit_rate": round(hits / total, 3) if total else 0.0,
            },
        }
