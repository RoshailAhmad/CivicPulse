# ADR 0001: Triage behind a provider interface

**Status:** Accepted

## Context

The component that reads complaints will change: keyword rules today, a hosted LLM now,
maybe a fine-tuned classifier later. Hosted models are also unreliable in ways we don't
control: they time out, get rate-limited (HTTP 429) and sometimes return prose, a code
fence or a category that doesn't exist. The rest of the system must not care which
reader is active, and must never fail because the reader failed.

## Decision

- A `TriageProvider` protocol (`backend/app/providers/triage/base.py`) with one method,
  `triage(text, location) -> TriageResult`. `TriageResult` is a Pydantic model whose
  `category` and `priority` are enums and whose `summary` is at most 140 characters.
- Four implementations, chosen by the `TRIAGE_PROVIDER` environment variable in
  `factory.py`: `LLMTriage` (Groq, OpenAI-compatible), the same class pointed at Ollama
  for offline use, `RuleBasedTriage` (never fails) and `SimulatedTriage` (deterministic,
  with failure injection, for CI).
- All reliability logic lives once, in `services/triage_service.py`, not in each
  provider: content-hash cache (24 h), hard 10 s timeout, one jittered retry only for
  timeout/429/5xx, then fallback to rules recorded as `triaged_by = "rules:fallback"`.
- Every model answer goes through `parse_triage_json`: JSON only, validated against
  `TriageResult`. Nothing from the model is ever evaluated or put into SQL.

## Consequences

- Adding a provider means one new class and one line in the factory. Nothing else changes.
- CI tests the real orchestration code with fake providers that raise, time out or return
  garbage, so the fallback path is proven on every commit without network access.
- We accept that a fallback answer is less accurate than the model's. The alternative, an
  error page for a citizen reporting a flood, is worse.
- The keyword rules must be maintained, including Roman Urdu words (pani, bijli, kachra).
