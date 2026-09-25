"""The TriageProvider interface and the shared, strict output parser."""

import json
import re
from typing import Protocol

from pydantic import ValidationError

from app.domain import TriageResult


class TriageProvider(Protocol):
    name: str

    def triage(self, text: str, location: str) -> TriageResult: ...


class TriageError(Exception):
    """Provider failed. NOT worth retrying (e.g. HTTP 400, bad output)."""


class RetryableTriageError(TriageError):
    """Provider failed in a way worth ONE retry: timeout, 429, 5xx, network."""


class MalformedTriageOutputError(TriageError):
    """Provider answered, but not with valid JSON matching TriageResult."""


_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_triage_json(raw: str) -> TriageResult:
    """Parse model output as data. Never eval, never trust it.

    Anything that is not a JSON object matching TriageResult exactly
    (unknown category, 400-char summary, prose) raises and triggers fallback.
    """
    cleaned = _CODE_FENCE.sub("", raw.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise MalformedTriageOutputError("output is not valid JSON") from exc
    if not isinstance(data, dict):
        raise MalformedTriageOutputError("output is not a JSON object")
    try:
        return TriageResult.model_validate(data)
    except ValidationError as exc:
        raise MalformedTriageOutputError(
            f"output failed schema: {exc.error_count()} errors"
        ) from exc
