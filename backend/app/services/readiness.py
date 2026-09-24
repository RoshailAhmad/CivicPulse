"""Readiness = can this pod serve traffic right now? Checks Postgres and Redis."""

from redis import Redis

from app.repositories.complaints import HealthRepository


def failed_dependencies(health_repo: HealthRepository, redis: Redis) -> list[str]:
    failed: list[str] = []
    try:
        health_repo.ping()
    except Exception:  # noqa: BLE001 - any failure means "not ready"
        failed.append("postgres")
    try:
        redis.ping()
    except Exception:  # noqa: BLE001
        failed.append("redis")
    return failed
