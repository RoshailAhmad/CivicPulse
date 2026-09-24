"""Application entry point: builds the FastAPI app and wires the layers."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIdMiddleware
from app.routes import health

logger = logging.getLogger("civicpulse")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup", extra={"triage_provider": get_settings().triage_provider})
    yield
    # Runs after uvicorn receives SIGTERM and in-flight requests finish.
    # DB/Redis pools get closed here in step 6.
    logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="CivicPulse API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    return app


app = create_app()
