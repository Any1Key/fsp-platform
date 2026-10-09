# M12 — Employer trust / anti-fraud MVP

## Purpose / user value

Give candidates a safe, explainable way to assess a reverse-recruitment offer
and report a suspicious employer without weakening the core invitation/match
flow. Give employers and reviewers a small, privacy-safe trust surface with
explicitly verified evidence separated from advisory heuristics.

## Requirement IDs

- `BONUS-001` — fake-vacancy / bad-employer protection concept/MVP.
- Supporting boundaries: `CORE-001`, `EMP-008`, `CAND-005`, `PRIV-001`,
  `NFR-006`, `LEGAL-001`.

## Current behavior

`docs/TRUST_AND_ANTI_FRAUD.md` describes future signals, but the product has
no persisted invitation/employer report, trust projection, reviewer queue, or
server-side outbound limit. Candidates can report only a matched chat.

## Proposed design

- Add a read-time company trust projection. Keycloak email verification is the
  only trust badge evidence; domain, website, profile completeness, account
  age, rejection rate, duplicate offers, and offer anomaly checks are labeled
  heuristics.
- Persist candidate reports against the invitation/company with a unique
  candidate/invitation boundary. An open report is the review queue entry and
  is visible to a reviewer without exposing candidate contact or report text in
  audit logs.
- Apply a conservative server-side daily invitation limit: normal employers
  have a larger limit; employers with an open report or multiple independent
  high-risk heuristic signals receive the smaller review limit. A single
  heuristic never blocks an invitation.
- Add reviewer/admin list and resolve endpoints, plus employer and candidate
  UI cards. Core matching, salary validation, privacy, and match unlock stay
  unchanged.

## Files/modules

- `backend/alembic/versions/20261009_0028_employer_trust.py` — report queue.
- `backend/app/trust.py` — trust projection, reporting, rate limits, review.
- `backend/app/invitations.py`, `backend/app/main.py`, `backend/app/errors.py`
  — invitation guard and API contracts.
- `backend/tests/test_employer_trust.py` — report, signal, scope, review, and
  rate-limit integration tests.
- `frontend/src/components/employer-trust.tsx`,
  `frontend/src/components/employer-company-profile.tsx`,
  `frontend/src/components/candidate-invitations.tsx`,
  `frontend/src/components/auth-status.tsx`, and `frontend/src/app/globals.css`
  — responsive trust/report surfaces.
- `docs/TRUST_AND_ANTI_FRAUD.md`, `docs/DATA_MODEL.md`, `docs/API_GUIDELINES.md`
  — implemented contract and safety boundaries.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — implementation evidence.

## Data/API changes

Add `employer_trust_report` with invitation/company/reporter ownership,
reason, details, status, timestamps, and uniqueness per reporter/invitation.

Add:

- `GET /api/v1/employer/trust`
- `POST /api/v1/candidate/invitations/{invitation_id}/report`
- `GET /api/v1/reviewer/trust/reports`
- `PATCH /api/v1/reviewer/trust/reports/{report_id}`

Invitation responses include a safe `employer_trust` summary. No candidate
contact, DOB, document, token, or raw report content is added to employer or
candidate invitation payloads beyond the reporting candidate's own UI state.

## Security/privacy implications

All report and reviewer routes are role- and ownership-scoped server-side.
Audit details contain only opaque report/company/invitation IDs and reason or
resolution status. Trust signals never use age, protected attributes, ranking
features, or candidate data. Heuristic signals are advisory and are not a
pass/fail gate.

## Test plan

- Employer trust projection distinguishes verified email from heuristics and
  exposes normal limits without protected data.
- Candidate can report only an invitation addressed to them; duplicate reports
  are idempotent and the report is audit-safe.
- An open report changes the employer to review state and lowers the server
  invitation limit; one advisory heuristic alone does not.
- Reviewer can list and resolve reports; candidate/employer roles cannot.
- Existing invitation salary, privacy, acceptance, and match behavior remains
  intact.
- Run focused and full backend tests, Ruff, frontend typecheck, and build.

## Demo/evidence

The candidate invitation card shows the verified-email badge and a report
action. The employer workspace shows trust signals and the current outbound
limit. A reviewer token can inspect the open queue and close a report. The
matrix records `BONUS-001` as `IMPLEMENTED`; external supervision owns
verification/readiness.

## Progress / decisions / surprises

- 2026-10-09: selected as the first unfinished item in M12.
- 2026-10-09: chose invitation-scoped reporting plus a derived trust projection
  instead of a global employer score, preserving explainability and avoiding a
  new opaque fraud model.
- 2026-10-09: implemented migration, trust projection, candidate report and
  reviewer queue APIs, conservative invitation throttle, and responsive
  employer/candidate UI. Focused trust/invitation/migration tests pass (12),
  the full backend suite passes (136), Ruff passes, and frontend typecheck plus
  production build pass. External supervision still owns verification.
