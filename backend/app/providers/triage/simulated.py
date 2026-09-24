"""Deterministic fake for CI: no network, same input -> same output,
with failure injection so tests can exercise every error path."""

import json
from typing import Literal

from app.domain import TriageResult
from app.providers.triage.base import RetryableTriageError, TriageError, parse_triage_json
from app.providers.triage.rules import RuleBasedTriage

FailureMode = Literal["none", "raise", "retryable", "malformed"]


class SimulatedTriage:
    name = "simulated"

    def __init__(self, failure_mode: FailureMode = "none") -> None:
        self.failure_mode = failure_mode
        self.calls = 0
        self._rules = RuleBasedTriage()

    def triage(self, text: str, location: str) -> TriageResult:
        self.calls += 1
        if self.failure_mode == "raise":
            raise TriageError("simulated hard failure")
        if self.failure_mode == "retryable":
            raise RetryableTriageError("simulated timeout")
        if self.failure_mode == "malformed":
            # Goes through the real parser, like a model returning prose.
            return parse_triage_json("Sure! This looks like a water problem.")

        result = self._rules.triage(text, location)
        raw = json.dumps({**result.model_dump(mode="json"), "confidence": 0.99})
        return parse_triage_json(raw)
