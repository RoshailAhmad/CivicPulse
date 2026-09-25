from pydantic import SecretStr

from app.config import Settings
from app.providers.triage.factory import build_provider


def _settings(**overrides: object) -> Settings:
    return Settings(database_url="postgresql+psycopg://u:p@h/d", **overrides)  # type: ignore[arg-type]


def test_factory_selects_provider_from_environment() -> None:
    assert build_provider(_settings(triage_provider="rules")).name == "rules"
    assert build_provider(_settings(triage_provider="simulated")).name == "simulated"
    assert build_provider(_settings(triage_provider="ollama")).name == "llm:ollama"
    groq = build_provider(_settings(triage_provider="llm", llm_api_key=SecretStr("k")))
    assert groq.name == "llm:groq"


def test_llm_without_key_falls_back_to_rules_instead_of_crashing() -> None:
    assert build_provider(_settings(triage_provider="llm")).name == "rules"
