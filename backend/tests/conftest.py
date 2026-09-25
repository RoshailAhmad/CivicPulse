"""Test setup: SQLite in memory + fakeredis, so the suite needs no Docker,
no network, and gives the same result on every run."""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@db-not-used:5432/test")
os.environ.setdefault("TRIAGE_PROVIDER", "simulated")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

from collections.abc import Callable, Iterator  # noqa: E402

import fakeredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import dependencies as deps  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.triage.base import TriageProvider  # noqa: E402
from app.providers.triage.simulated import SimulatedTriage  # noqa: E402
from app.repositories import models  # noqa: E402,F401
from app.repositories.db import Base  # noqa: E402
from app.services.triage_service import TriageService  # noqa: E402


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    # Tests build tables with create_all; the real app uses Alembic migrations.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def make_client(
    session_factory: sessionmaker[Session], redis: fakeredis.FakeRedis
) -> Iterator[Callable[..., TestClient]]:
    def _make(provider: TriageProvider | None = None) -> TestClient:
        chosen = provider or SimulatedTriage()

        def session_override() -> Iterator[Session]:
            with session_factory() as session:
                yield session

        app.dependency_overrides[deps.get_session] = session_override
        app.dependency_overrides[deps.get_redis] = lambda: redis
        app.dependency_overrides[deps.get_triage_provider] = lambda: chosen
        app.dependency_overrides[deps.get_triage_service] = lambda: TriageService(
            chosen,
            redis,
            sleep=lambda _: None,  # never really sleep in tests
        )
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


VALID = {
    "text": "Burst water main flooding Street 12 since fajr, water entering ground floors",
    "location": "Street 12, G-9/2, Islamabad",
    "reporter_contact": "0300-1234567",
}
