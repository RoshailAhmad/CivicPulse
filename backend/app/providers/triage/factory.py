"""Chooses the provider from TRIAGE_PROVIDER. The rest of the app only
ever sees the TriageProvider interface."""

from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def build_provider(settings: Settings) -> TriageProvider:
    match settings.triage_provider:
        case "llm":
            if settings.llm_api_key is None or not settings.llm_api_key.get_secret_value():
                raise ValueError("TRIAGE_PROVIDER=llm needs LLM_API_KEY to be set")
            return LLMTriage.from_settings(
                name="llm:groq",
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key.get_secret_value(),
                model=settings.llm_model,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        case "ollama":
            return LLMTriage.from_settings(
                name="llm:ollama",
                base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
                api_key="ollama",  # Ollama ignores it; the SDK requires a value
                model=settings.ollama_model,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        case "simulated":
            return SimulatedTriage(failure_mode=settings.simulated_failure_mode)
        case _:
            return RuleBasedTriage()
