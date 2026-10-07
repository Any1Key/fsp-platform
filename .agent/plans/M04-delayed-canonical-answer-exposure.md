# M04 — Delayed canonical-answer exposure policy

## Purpose / user value

Give candidates useful score and integrity feedback immediately after a base
assessment while preventing reusable answer keys and detailed solutions from
being published while the corresponding item family/version is active.

## Requirement IDs

AST-015, AST-016, DOC-002. This is the M04 backlog item `delayed
canonical-answer exposure policy`; AST-016 is already marked VERIFIED in the
matrix and will not be downgraded.

## Current behavior

Submitted attempts return score, grade state, and advisory integrity signals,
but template families do not have a versioned canonical review policy. The
public serializer has no delayed/available review state and no safe way to
release detailed canonical explanations after a configured window or family
retirement.

## Proposed design

- Version template families and attach server-only canonical explanations.
- Start a per-family/version exposure window on first exposure; default to 90
  days and make the duration configurable at the application boundary.
- Allow a controlled domain retirement operation to release a family/version
  before the time window closes.
- Return a candidate-safe `canonical_review` status after submission. While
  delayed, return only the release timestamp and no answer key/rationale. Once
  every family/version in the attempt is eligible, return detailed canonical
  item explanations.
- Keep score, grade state, discoverability, and integrity signals unchanged.

## Files/modules

- `backend/app/assessments.py` — versioned family metadata, exposure-window
  state, retirement, policy serialization.
- `backend/app/config.py` and `backend/app/main.py` — configurable policy
  boundary and API serialization.
- `backend/tests/test_assessments.py` — delayed, retired, elapsed-window,
  privacy, and score/grade invariant tests.
- `docs/AI_ASSESSMENT_INTEGRITY.md`, `docs/ASSESSMENT_ENGINE.md`,
  `docs/API_GUIDELINES.md`, `.env.example` — policy and API evidence.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — IMPLEMENTED evidence
  only; never VERIFIED/READY.

## Data/API changes

Submitted attempt responses add `canonical_review` with `status` and
`available_at`. The `available` form additionally contains per-item family
version, correct option, and canonical explanation. These fields are absent
from in-progress attempts, and answer keys never appear while status is
`delayed`.

## Security/privacy implications

Canonical answers remain server-side until the family/version is retired or
the configured exposure window has elapsed. Retirement is an explicit domain
operation, not an automatic candidate action. No comparator identity, raw
responses, or integrity internals are added to the response.

## Test plan

- Newly submitted attempts expose a delayed review without canonical answers.
- Advancing the service clock beyond the configured window exposes canonical
  details and only then.
- Retiring a family/version releases its details early; other active families
  keep the whole review delayed until all item versions are eligible.
- Score, grade state, integrity signals, and answer secrecy remain unchanged.
- API output follows the same policy and existing authorization tests remain
  green.

## Demo/evidence

The candidate assessment API and UI can display the delayed review state after
submission; the response becomes detailed only after policy eligibility. The
backend tests provide deterministic clock and retirement evidence.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished work unit in highest-priority
  unfinished milestone M04.
- 2026-10-07: implemented versioned family exposure timestamps, configurable
  90-day default release window, explicit retirement, candidate-safe API
  serialization, and assessment result UI states.
- 2026-10-07: backend suite passed with 52 tests; Ruff, frontend typecheck,
  and production build passed. No VERIFIED or READY state was changed.
