"""Liveness endpoint. Deliberately touches nothing but the process itself:
Kubernetes restarts the pod when this fails, so a slow database must never
make it fail. Readiness (/ready, with real dependency checks) comes in step 3."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
