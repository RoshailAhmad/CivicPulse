"""Structured JSON logging to stdout, with a request_id on every line."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Holds the current request's id. Each request (and the thread serving it)
# sees its own value, so concurrent requests never mix ids.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        # Anything passed via logger.info("...", extra={...}) becomes a JSON field.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)  # stdout, never a file
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Route uvicorn's own loggers through our JSON handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers[:] = []
        lg.propagate = True
    # Our middleware logs each request; uvicorn's access log would duplicate it.
    logging.getLogger("uvicorn.access").disabled = True
