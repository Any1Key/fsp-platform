# M11 — Evidence freshness state

## Purpose / user value

Make employer-specific periodic-challenge evidence actionable. Candidates and
employers should see whether a released result is fresh, nearing renewal, or
stale instead of interpreting a timestamp themselves.

## Requirement IDs

- `INNOV-002` — evidence freshness is represented in the domain and UI.
- `AST-011` — this extends the existing periodic challenge result lifecycle
  without changing its employer-owned scope.

## Current behavior

`challenge_result.evidence_fresh_until` is persisted when an employer releases
a result. The API returns the timestamp and the candidate UI prints a date, but
neither side receives a derived freshness state or remaining-day value.

## Proposed design

- Derive `fresh`, `expiring`, or `stale` server-side from the release expiry.
  Results with three or fewer whole days remaining are `expiring`; expired
  results are `stale`.
- Return the derived state and non-negative `days_remaining` in the existing
  result object, preserving `evidence_fresh_until` for compatibility.
- Render a compact freshness summary and per-result status in candidate and
  employer challenge panels. The status is advisory evidence freshness only;
  it never changes the platform grade, match, or chat permissions.

## Files/modules

- `backend/app/challenges.py`
- `backend/tests/test_periodic_challenges.py`
- `frontend/src/components/candidate-challenges.tsx`
- `frontend/src/components/employer-challenges.tsx`
- `frontend/src/app/globals.css`
- `docs/PERIODIC_CHALLENGES.md`, `docs/API_GUIDELINES.md`
- `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`

## Security/privacy implications

The derived fields contain no new personal data and remain behind the existing
candidate/employer match-scoped challenge authorization. Candidate payloads
continue to omit rubric internals; employer-specific evidence remains separate
from global assessment evidence.

## Test plan

- Existing released result returns `fresh` and a bounded remaining-day value.
- Moving the stored expiry into the past returns `stale` and zero remaining
  days without changing the score or global candidate dashboard.
- API/UI type contracts keep both workspaces buildable and role-scoped.

## Demo/evidence

`backend/tests/test_periodic_challenges.py` demonstrates the released result,
freshness state, stale transition, and unchanged global dashboard. The two
challenge panels visibly distinguish fresh, renewal-soon, and stale evidence.

## Progress / decisions / surprises

- Plan created before implementation.
- Implemented server-derived freshness with a three-day renewal warning
  threshold, normalized timestamps, role-scoped UI badges/summaries, and a
  stale-transition regression test. Freshness remains advisory and does not
  feed global grade, matching, or chat authorization.
- Focused challenge tests pass (4); full backend suite passes (121); Ruff,
  frontend typecheck, and production build pass. External supervisor owns
  verification.
