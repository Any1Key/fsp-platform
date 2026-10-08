# M11 periodic employer challenges

## Purpose / user value

Give a matched candidate a short, repeatable employer challenge that keeps
employer-specific evidence current without changing the platform-wide grade.
The employer can configure a cadence and rubric; each completed cycle schedules
the next cycle and exposes a freshness deadline.

## Requirement IDs

- AST-011 — Periodic short employer challenges.

## Current behavior

M09 supports one-off employer-owned pipeline tasks after a match. There is no
separate recurring challenge lifecycle, cycle history, due scheduling, or
candidate/employer UI for freshness-aware challenge evidence.

## Proposed design

- Add a company-owned challenge bound to one existing `talent_match`.
- Store a 5–20 minute prompt, target skill label, cadence in days, and a
  deterministic rubric snapshot.
- Create cycle 1 at challenge creation. Candidates can read only challenges
  for their own matches and submit one response per cycle before its deadline.
- Employers can read only their company's cycles and grade a submitted cycle.
  A released result carries `evidence_fresh_until`; grading creates the next
  scheduled cycle, preserving prior cycles as an append-only evidence history.
- Challenge scores and results remain employer-specific and do not feed the
  platform assessment or candidate global grade.

## Files/modules

- `backend/alembic/versions/20261008_0026_periodic_challenges.py`
- `backend/app/challenges.py`, `backend/app/main.py`
- `backend/tests/test_periodic_challenges.py`
- `frontend/src/components/candidate-challenges.tsx`
- `frontend/src/components/employer-challenges.tsx`, `frontend/src/components/auth-status.tsx`
- `docs/PERIODIC_CHALLENGES.md`, `docs/DATA_MODEL.md`, `docs/REQUIREMENTS_MATRIX.md`,
  `.agent/BACKLOG.md`

## Data/API changes

Add `challenge`, `challenge_assignment`, `challenge_submission`, and
`challenge_result` tables with ownership/match foreign keys and cycle
uniqueness. Add employer create/list/grade routes and candidate list/submit
routes under `/api/v1/{employer,candidate}/challenges`.

## Security/privacy implications

All routes enforce the authenticated role and company/candidate match boundary.
Candidate responses never expose employer rubric internals; employer responses
never expose unrelated candidates. Protected candidate attributes and contacts
are not copied into challenge records or payloads.

## Test plan

- End-to-end employer creates a challenge for a matched candidate.
- Candidate cannot see it before match, can submit only its own current cycle,
  and receives the released score/freshness deadline.
- Employer grading is rubric-bounded, schedules the next cycle, and leaves the
  candidate's global dashboard unchanged.
- Outsider/company/role boundaries and overdue-cycle rejection.

## Demo/evidence

Use `backend/tests/test_periodic_challenges.py` as the AST-011 evidence path;
the two role-specific UI panels cover loading, empty, error, scheduled and
submitted states.

## Progress / decisions / surprises

- 2026-10-08: Scope chosen as a distinct recurring lifecycle instead of
  modifying M09 one-off pipeline tasks, preserving the existing employer-task
  contract.
- 2026-10-08: Implemented migration, match-scoped API, responsive candidate and
  employer panels, and backend E2E/privacy/freshness tests. AST-011 is marked
  IMPLEMENTED; no verification state or readiness flag is changed.
