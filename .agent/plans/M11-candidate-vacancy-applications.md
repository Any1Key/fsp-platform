# M11 candidate vacancy applications

## Purpose / user value

Let an authenticated candidate discover published, salary-bearing vacancies, submit one application per vacancy, and track the application's current status without exposing private employer or candidate data.

## Requirement IDs

- CAND-007 — browse vacancies
- CAND-008 — candidate applies to vacancy
- CAND-009 — candidate sees application statuses

EMP-010 and the later M11 items (accepted application → match, periodic challenges, evidence freshness) remain outside this work unit.

## Current behavior

Employers can create, edit, publish, and close company-owned vacancies. Candidate vacancy routes, application persistence, and application UI do not exist. The data-model documentation names `application` and application status history as planned entities.

## Proposed design

- Add `application` and append-only `application_status_history` tables.
- A candidate route lists only published vacancies and includes safe company name plus the candidate's own application status, if any.
- A candidate can apply only to a published vacancy and only after processing consent. The API rejects duplicate applications and preserves no candidate contact or protected profile fields in the vacancy response.
- A candidate route lists only the authenticated candidate's applications, including vacancy summary, current status, and status history. The initial status is `submitted`; employer status management is a later unit.
- No match, contact unlock, or chat authorization changes in this slice.

## Files/modules

- `backend/alembic/versions/20261008_0023_candidate_vacancy_applications.py`
- `backend/app/vacancy_applications.py`
- `backend/app/main.py`, `backend/app/errors.py`
- `backend/tests/test_candidate_vacancies.py`, `backend/tests/test_migrations.py`
- `frontend/src/components/candidate-vacancies.tsx`, `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/CANDIDATE_VACANCIES.md`, `docs/DATA_MODEL.md`, `docs/EMPLOYER_VACANCIES.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`

## Data/API changes

- `GET /api/v1/candidate/vacancies`
- `POST /api/v1/candidate/vacancies/{vacancy_id}/applications`
- `GET /api/v1/candidate/applications`
- Application statuses: `submitted`, `reviewing`, `shortlisted`, `rejected`, `withdrawn`.

## Security/privacy implications

All routes require the candidate role and scope through the authenticated candidate profile. Vacancy discovery exposes only published vacancy fields and company name, never employer contact details. Application reads are candidate-scoped. Processing consent is required before persisting an application; protected candidate fields and contact/chat unlock remain out of scope.

## Test plan

- Migration creates application tables, constraints, indexes, and foreign-key boundaries.
- Published-only candidate listing and company-safe fields.
- Candidate role and cross-candidate isolation.
- Processing-consent gate, duplicate rejection, closed/draft rejection.
- Application status/history response and no match/chat side effects.
- Frontend production build and backend focused/full test suite.

## Demo/evidence

The candidate workspace will show a vacancy board with salary, employer, status, and an application-status panel. Evidence paths will be recorded in the requirements matrix after tests pass.

## Progress / decisions / surprises

- 2026-10-08: selected as the first coherent unfinished M11 unit.
- 2026-10-08: candidate application starts at `submitted`; accepted application → match is deliberately deferred to the next M11 unit so the existing invitation/match boundary remains unchanged.
- 2026-10-08: implemented migration, candidate-scoped service/API/UI, focused tests, and documentation. Backend suite: 114 passed; frontend production build and Ruff checks passed.
