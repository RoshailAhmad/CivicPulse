from collections.abc import Callable

import fakeredis
from fastapi.testclient import TestClient

from app import dependencies as deps
from app.main import app
from app.providers.rate_limiter import RateLimiter
from tests.conftest import VALID


def test_rate_limit_returns_429_with_retry_after(
    make_client: Callable[..., TestClient], redis: fakeredis.FakeRedis
) -> None:
    client = make_client()
    app.dependency_overrides[deps.get_rate_limiter] = lambda: RateLimiter(redis, limit=2)
    assert client.post("/api/complaints", json=VALID).status_code == 201
    assert client.post("/api/complaints", json=VALID).status_code == 201
    blocked = client.post("/api/complaints", json=VALID)
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60


def test_limiter_is_shared_across_instances(redis: fakeredis.FakeRedis) -> None:
    # Two "pods" sharing one Redis: the limit is global, not per pod.
    pod_a = RateLimiter(redis, limit=2, clock=lambda: 1000.0)
    pod_b = RateLimiter(redis, limit=2, clock=lambda: 1000.0)
    assert pod_a.hit("1.2.3.4").allowed
    assert pod_b.hit("1.2.3.4").allowed
    assert not pod_a.hit("1.2.3.4").allowed
