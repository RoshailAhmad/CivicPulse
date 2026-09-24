"""Per-request context: request-ID propagation, one JSON access-log line,
and Prometheus request metrics."""

import logging
import re
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import request_id_ctx
from app.metrics import HTTP_LATENCY, HTTP_REQUESTS

logger = logging.getLogger("civicpulse.access")

# Only accept safe ids from clients, so nobody can inject junk into our logs.
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_QUIET_PATHS = {"/health", "/ready", "/metrics"}  # probes: log at DEBUG only


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id", b"").decode("latin-1").strip()
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex

        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            # Label by route template (/api/complaints/{complaint_id}), not the raw
            # path, or every UUID would create a new metric series.
            route = scope.get("route")
            path = getattr(route, "path", "unmatched")
            HTTP_REQUESTS.labels(scope["method"], path, str(status_code)).inc()
            HTTP_LATENCY.labels(scope["method"], path).observe(elapsed)
            level = logging.DEBUG if scope["path"] in _QUIET_PATHS else logging.INFO
            logger.log(
                level,
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round(elapsed * 1000, 2),
                },
            )
            request_id_ctx.reset(token)
