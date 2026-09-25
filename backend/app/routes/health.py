"""/health = liveness (is the process alive?) -> failing it RESTARTS the pod,
so it must never depend on the database.
/ready = readiness (can I serve traffic?) -> failing it only REMOVES the pod
from the Service, so it SHOULD check Postgres and Redis."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis import Redis

from app.dependencies import get_health_repository, get_redis
from app.repositories.complaints import HealthRepository
from app.services.readiness import failed_dependencies

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(
    health_repo: HealthRepository = Depends(get_health_repository),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    failed = failed_dependencies(health_repo, redis)
    if failed:
        return JSONResponse(status_code=503, content={"status": "not_ready", "failed": failed})
    return JSONResponse(status_code=200, content={"status": "ready"})


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
