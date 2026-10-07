# M06 — Talent Radar discovery

## Purpose / user value

Give an employer a consent-gated Talent Radar for the current hiring need. The
employer sees category context, concrete candidates, a transparent ProofMatch
score, evidence sources, freshness/confidence, and gaps before any invitation
or contact flow exists.

## Requirement IDs

- CORE-002, CORE-003
- AST-003
- EMP-003, EMP-004, EMP-005, EMP-006
- MATCH-001 through MATCH-007

## Current behavior

Employers can save a company profile and one structured hiring need. Candidate
assessment results remain in the existing process-local assessment service, and
candidate profile/FSP/privacy data is persisted, but there is no employer-facing
candidate discovery endpoint or UI.

## Proposed design

Add a read-only employer Talent Radar projection. It will:

1. require the employer's current hiring need;
2. include only candidates with publication/discoverability consent;
3. derive category and grade state from the latest submitted assessment;
4. keep unconfirmed and unassessed candidates visible with explicit labels;
5. score specialization, grade, skill coverage, assessment strength,
   evidence confidence/freshness, and the bounded FSP contribution;
6. return human-readable reasons, per-skill evidence edges, and gaps;
7. support search, specialization/grade/skill filters, and explicit inclusion
   of unconfirmed candidates through query parameters; and
8. render the response in a responsive employer Talent Radar panel without
   exposing email, DOB, minor documents, or direct contacts.

## Files/modules

- `backend/app/discovery.py` — ProofMatch projection and ranking boundary.
- `backend/app/main.py` — response models and employer route.
- `backend/tests/test_talent_radar.py` — API, ranking, privacy, and filter tests.
- `frontend/src/components/employer-talent-radar.tsx` — employer discovery UI.
- `frontend/src/components/auth-status.tsx` — mount employer panel.
- `frontend/src/app/globals.css` — responsive radar styles.
- `docs/MATCHING_ENGINE.md` — implemented projection/evidence notes.
- `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` — mark only this slice
  `IMPLEMENTED`.

## Data/API changes

Add `GET /api/v1/employer/talent-radar` with optional `q`, `specialization`,
`grade`, `skill`, `include_unconfirmed`, and `limit` query parameters. The
response contains the current need, category aggregates, a filter snapshot,
and ranked candidate cards. It is employer-role protected and is read-only;
no migration is required.

## Security/privacy implications

Only `is_discoverable` candidates with publication consent are projected. The
projection excludes identity email, date of birth, minor state, resume
documents, raw OIDC subjects, and FSP participant IDs. Age and protected traits
are not read by the ranking code. Missing FSP history is zero contribution,
never an eligibility failure. Candidate contacts remain outside this API.

## Test plan

- consent and role isolation;
- verified candidate ranking and score breakdown;
- unconfirmed candidate visibility/toggle and explicit grade marker;
- no-FSP candidate remains searchable with zero FSP bonus;
- required/preferred evidence coverage and gaps;
- search and specialization/grade/skill/FSP filters;
- category aggregates and stable filter snapshot;
- response does not contain contact/protected fields.

## Demo/evidence

Employer workspace shows a `TALENT RADAR` panel with category counts, active
filters, ProofMatch scores, verified/unconfirmed badges, evidence chips, gaps,
and a disabled invitation placeholder until M07 implements salary-bearing
invitations.

## Progress / decisions / surprises

- 2026-10-07: Selected as the highest-priority unfinished backlog milestone.
- 2026-10-07: Kept the existing process-local assessment repository boundary;
  persistence migration is outside this single coherent work unit.
- 2026-10-07: Added an ephemeral audit-friendly snapshot with selected IDs and
  scoring/evidence/need versions; durable saved snapshots remain outside M06.
- 2026-10-07: Implemented the employer route/UI, consent and privacy boundary,
  filters, and evidence explanations. Backend suite: 73 passed; Ruff,
  frontend typecheck, and production build passed.
