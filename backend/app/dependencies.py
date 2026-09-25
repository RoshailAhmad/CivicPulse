"""Dependency wiring: builds repositories and services for each request.
Routes ask for a *service*; they never open a session themselves.
Tests replace these functions via app.dependency_overrides."""

from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.providers.rate_limiter import RateLimiter
from app.providers.triage.base import TriageProvider
from app.providers.triage.factory import build_provider
from app.repositories.complaints import ComplaintRepository, HealthRepository
from app.repositories.db import get_sessionmaker
from app.services.complaint_service import ComplaintService
from app.services.stats_service import StatsCache, StatsService
from app.services.triage_service import TriageService


def get_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2,
    )


@lru_cache
def get_triage_provider() -> TriageProvider:
    return build_provider(get_settings())


def get_triage_service(
    redis: Redis = Depends(get_redis),
    provider: TriageProvider = Depends(get_triage_provider),
) -> TriageService:
    return TriageService(provider, redis, get_settings().triage_cache_ttl_seconds)


def get_stats_cache(redis: Redis = Depends(get_redis)) -> StatsCache:
    return StatsCache(redis, get_settings().stats_cache_ttl_seconds)


def get_complaint_repository(session: Session = Depends(get_session)) -> ComplaintRepository:
    return ComplaintRepository(session)


def get_health_repository(session: Session = Depends(get_session)) -> HealthRepository:
    return HealthRepository(session)


def get_complaint_service(
    repo: ComplaintRepository = Depends(get_complaint_repository),
    triage: TriageService = Depends(get_triage_service),
    stats_cache: StatsCache = Depends(get_stats_cache),
) -> ComplaintService:
    return ComplaintService(repo, triage, stats_cache)


def get_stats_service(
    repo: ComplaintRepository = Depends(get_complaint_repository),
    cache: StatsCache = Depends(get_stats_cache),
) -> StatsService:
    return StatsService(repo, cache)


def get_rate_limiter(redis: Redis = Depends(get_redis)) -> RateLimiter:
    return RateLimiter(redis, limit=get_settings().rate_limit_per_minute)


def enforce_rate_limit(request: Request, limiter: RateLimiter = Depends(get_rate_limiter)) -> None:
    client_ip = request.client.host if request.client else "unknown"
    decision = limiter.hit(client_ip)
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many complaints from this address. Please wait and try again.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
