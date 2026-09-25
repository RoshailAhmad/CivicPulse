"""Prometheus metrics, exposed at GET /metrics."""

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "civicpulse_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "civicpulse_http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)
TRIAGE_LATENCY = Histogram(
    "civicpulse_triage_duration_seconds",
    "Triage latency including cache lookup and fallback",
    ["provider"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)
TRIAGE_FALLBACKS = Counter(
    "civicpulse_triage_fallbacks_total", "Triage fallbacks to rules", ["provider", "error"]
)
TRIAGE_CACHE = Counter("civicpulse_triage_cache_total", "Triage cache lookups", ["result"])
