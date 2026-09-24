from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok_without_database() -> None:
    # DATABASE_URL points at a host that doesn't exist, so a 200 here proves
    # /health does not touch the database.
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_echoed() -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_request_id_generated_when_missing_or_unsafe() -> None:
    generated = client.get("/health").headers["X-Request-ID"]
    assert len(generated) == 32
    unsafe = client.get("/health", headers={"X-Request-ID": "bad id\nINJECTED"})
    assert unsafe.headers["X-Request-ID"] != "bad id\nINJECTED"
