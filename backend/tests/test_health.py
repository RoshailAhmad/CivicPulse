from typing import Any

from fastapi.testclient import TestClient

from app import dependencies as deps
from app.main import app


def test_health_ok_without_database() -> None:
    # No overrides: DATABASE_URL points at a host that does not exist,
    # so a 200 proves /health never touches the database.
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_request_id_generated_when_missing_or_unsafe(client: TestClient) -> None:
    assert len(client.get("/health").headers["X-Request-ID"]) == 32
    unsafe = client.get("/health", headers={"X-Request-ID": "bad id\nINJECTED"})
    assert unsafe.headers["X-Request-ID"] != "bad id\nINJECTED"


def test_ready_when_dependencies_up(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200


def test_ready_names_failed_dependency(client: TestClient) -> None:
    class DownRepo:
        def ping(self) -> Any:
            raise ConnectionError("postgres is down")

    app.dependency_overrides[deps.get_health_repository] = lambda: DownRepo()
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["failed"] == ["postgres"]


def test_metrics_exposed(client: TestClient) -> None:
    client.get("/health")
    body = client.get("/metrics").text
    assert "civicpulse_http_requests_total" in body
    assert "civicpulse_triage_fallbacks_total" in body
