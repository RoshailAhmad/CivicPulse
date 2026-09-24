"""Application entry point: builds the FastAPI app and wires the layers."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.dependencies import get_redis, get_triage_provider
from app.errors import InvalidTransitionError, NotFoundError
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.repositories.db import get_engine
from app.routes import complaints, health, meta, stats

logger = logging.getLogger("civicpulse")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    provider = get_triage_provider()  # fail fast on bad config (e.g. llm without key)
    logger.info("startup", extra={"triage_provider": provider.name})
    yield
    # Graceful shutdown: uvicorn gets SIGTERM, stops accepting connections,
    # waits for in-flight requests (--timeout-graceful-shutdown), THEN runs this.
    get_engine().dispose()
    get_redis().close()
    logger.info("shutdown complete: pools closed")


def _field_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    errors = []
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        errors.append({"field": ".".join(loc) or "body", "message": err["msg"]})
    return errors


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="CivicPulse API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": "Validation failed", "errors": _field_errors(exc)},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidTransitionError)
    async def conflict_handler(_: Request, exc: InvalidTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    app.include_router(health.router)
    app.include_router(complaints.router)
    app.include_router(stats.router)
    app.include_router(meta.router)
    return app


app = create_app()
