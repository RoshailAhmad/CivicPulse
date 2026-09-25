# ---- Stage 1: builder — install dependencies into a virtualenv ----
FROM python:3.12.8-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
# requirements BEFORE source: this layer is reused until dependencies change,
# so editing a .py file doesn't reinstall every package.
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- Stage 2: runtime — only the venv and our code, no build tools ----
FROM python:3.12.8-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
USER 10001
EXPOSE 8000
# Checks its OWN /health inside the container (127.0.0.1 is this container).
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]
# Exec form: uvicorn is PID 1 and receives SIGTERM directly, then drains
# in-flight requests for up to 20 s before closing pools and exiting.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--timeout-graceful-shutdown", "20"]
