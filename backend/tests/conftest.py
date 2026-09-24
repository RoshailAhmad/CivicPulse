import os

# Deterministic test settings. Set before the app is imported.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@db-not-used:5432/test")
os.environ.setdefault("TRIAGE_PROVIDER", "simulated")
