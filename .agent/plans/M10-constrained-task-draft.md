# M10 — Constrained employer task/rubric draft

## Requirement IDs

- `EMP-014` — local CPU AI may propose employer task/rubric drafts from the
  current need and approved employer task history.
- `NFR-012` — optional local AI is isolated behind an adapter and has a
  deterministic fallback when disabled or unavailable.

## Scope

Extend the existing approved-task retrieval slice with constrained JSON draft
generation. The adapter will receive only the sanitized hiring need and the
bounded employer-scoped approved examples. The server validates the generated
task content against the current need, canonical skill set, grade and rubric
limits before returning it. The employer UI can apply the suggestion into the
existing editable form; it is never persisted or published automatically.

## Design

- Add explicit local-AI settings for an optional OpenAI-compatible local
  endpoint, model and timeout.
- Keep `DisabledLocalAiAdapter` as the default and use a small HTTP adapter
  only when explicitly enabled and configured.
- Request JSON-only output with a strict schema and low-temperature generation.
- Validate and normalize output server-side, including required-skill coverage,
  current-grade matching, known skills, field limits and positive rubric points.
- Return stable failure reasons for timeout, transport, parse and schema errors;
  do not expose model response text or persist a failed draft.
- Add focused backend tests for schema acceptance/rejection, adapter parsing,
  disabled fallback and API/UI response behavior. Update local-AI documentation,
  requirement evidence and backlog semantics.

## Verification

- Run `pytest -q` for the backend suite and focused M10 tests.
- Run Ruff on changed backend files.
- Run the frontend TypeScript check/build contract.

## Progress

- Plan created before implementation.
- Implemented strict need-aware draft validation, opt-in local HTTP adapter,
  stable failure fallback, employer review/apply UI, focused tests and docs.
