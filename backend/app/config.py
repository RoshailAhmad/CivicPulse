"""Application settings, read from environment variables (12-factor style).

Nothing secret has a default here: DATABASE_URL must be provided by the
environment (.env locally, Compose/Kubernetes/GitHub Secrets elsewhere).
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Real environment variables always win over values in the .env file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    database_url: str  # required, no default
    redis_url: str = "redis://cache:6379/0"

    triage_provider: Literal["llm", "ollama", "rules", "simulated"] = "rules"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.1-8b-instant"
    llm_api_key: SecretStr | None = None  # SecretStr never prints its value
    llm_timeout_seconds: float = 10.0
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:1b"

    rate_limit_per_minute: int = 10
    stats_cache_ttl_seconds: int = 30
    triage_cache_ttl_seconds: int = 86_400


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
