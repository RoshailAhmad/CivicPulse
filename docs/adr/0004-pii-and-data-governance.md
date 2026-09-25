# ADR 0004: Personal data and the hosted LLM

**Status:** Accepted

## Context

Complaints contain personal data: citizens type their name, house number, phone number
or email into the description, and the form has an optional contact field. With
`TRIAGE_PROVIDER=llm`, complaint text is sent to a third-party model provider (Groq) over
the internet. Some free tiers, such as Google AI Studio, may use inputs to improve their
models. We are responsible for what leaves our infrastructure.

## What leaves our machine, to whom

| Data | Sent to the LLM? |
|---|---|
| `reporter_contact` field | **Never.** It is stored in Postgres only; the triage call doesn't receive it. |
| Phone numbers and emails inside the complaint text | **No.** `redact_pii()` in `backend/app/providers/triage/llm.py` replaces them with `[phone]` / `[email]` before the request is built. |
| The rest of the complaint text and the location | **Yes**, to Groq, only when `TRIAGE_PROVIDER=llm`. |
| Anything, when `TRIAGE_PROVIDER` is `rules`, `simulated` or `ollama` | **No.** Nothing leaves the machine. |

## Decision

1. Send only what classification needs: the complaint body and location, with phone
   numbers and emails redacted. Never the contact field.
2. Prefer a provider whose API terms say inputs are not used for training. Before
   enabling a provider, a team member reads its current data-use terms and records the
   date and link below.
3. Keep a fully local option: the Ollama provider runs in our Compose stack, so a
   municipality that can't accept any external processing can switch with one variable.
4. Never log complaint text alongside the API key, and never log the key at all.

## Why this is acceptable

A burst pipe report is operational data, mostly about public places. With contacts and
direct identifiers removed, what reaches the provider is close to what a citizen would
say on a public helpline. Redaction is imperfect (a name typed in a sentence still goes),
so the residual risk is documented here, and the local Ollama path exists for anyone
who needs zero exposure.

## Provider terms checked

| Provider | Date checked | Link | Uses API inputs for training? |
|---|---|---|---|
| Groq | *(fill in)* | *(fill in)* | *(fill in from the page you read)* |
