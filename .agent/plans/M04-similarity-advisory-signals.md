# M04 — Cross-submission similarity advisory signals

## Purpose / user value

Give assessment reviewers a bounded, explainable signal when submitted text or
code-like rationale is unusually similar to another completed attempt, without
pretending that similarity proves misconduct or using an AI detector as a gate.

## Requirement IDs

AST-015, INNOV-005.

The slice covers the M04 backlog item `code/text similarity advisory signals`.
It does not include synthetic grade validation or delayed canonical-answer
exposure.

## Current behavior

Assessment submissions retain no response text after scoring. The service can
flag disclosed paste/focus telemetry and failed hidden checks, but cannot
compare completed responses across attempts or show similarity evidence.

## Proposed design

- Retain submitted progressive responses only in the assessment repository's
  server-side attempt record; never expose another attempt or its content.
- Compare responses only for the same template family and only after both
  attempts are submitted.
- Use lexical normalization for prose and comment/identifier/number-normalized
  token fingerprints for code-like responses. Require a meaningful response
  length and a high combined similarity threshold to limit boilerplate noise.
- Add a stable `cross_submission_similarity_review` advisory signal and
  privacy-safe evidence containing modality, item scope and rounded similarity;
  never include the comparator attempt ID, candidate identity or copied text.
- Keep deterministic score, grade state and discoverability unchanged.

## Files/modules

- `backend/app/assessments.py` — response retention, normalizers, comparison,
  advisory evidence and public serialization.
- `backend/tests/test_assessments.py` — text/code similarity, threshold,
  same-family scoping, no-grade-change and API evidence tests.
- `frontend/src/components/candidate-assessment.tsx` and
  `frontend/src/app/globals.css` — candidate-safe review-signal notice.
- `docs/AI_ASSESSMENT_INTEGRITY.md` — implemented signal semantics and limits.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — implementation status only.

## Data/API changes

Submitted attempts expose `integrity_evidence` only after submission. Each item
contains a stable signal code, `text` or `code` modality, a family-scoped
`progressive_response` scope and a rounded similarity score. No comparator
identity or source content is returned.

## Security/privacy implications

Comparison is server-side and candidate-scoped at the API boundary. Raw
responses stay out of logs and public payloads. Similarity is an advisory
review signal, not an automatic rejection, grade mutation or AI-content
classification.

## Test plan

- Identical normalized prose and structurally identical code-like responses
  produce a signal only for the same template family.
- Different-family and below-minimum/low-similarity responses do not signal.
- The signal leaves score and grade state unchanged and carries no comparator
  identity or copied content.
- API output includes safe evidence only after submission; the UI renders the
  signal as review-only language.
- Existing assessment authorization, secrecy, uniqueness and integrity tests
  remain green.

## Demo/evidence

The assessment API and candidate UI show `Сигналы для ручной проверки` after a
flagged submission. Backend tests provide deterministic text/code fixtures and
assert the score/grade invariants.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished work unit in highest-priority
  unfinished milestone M04.
- 2026-10-07: reused the existing progressive follow-up field as the current
  text/code response surface; no new assessment question type was introduced.
- 2026-10-07: implemented server-side same-family comparison, privacy-safe
  evidence serialization, and candidate result UI wording. Score and grade
  invariants are covered by backend tests.
- 2026-10-07: validation passed with `PYTHONPATH=. .venv/bin/pytest -q` (50
  tests), Ruff on the changed backend files, frontend typecheck and production
  build.
