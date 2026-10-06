# M02 — Protected DOB and derived minor state

## Purpose / user value

Let a candidate maintain the date-of-birth information needed for privacy and
future minor-consent handling while keeping it private and out of matching.
The API derives the current minor state on the server so clients cannot submit
or rank on an asserted age.

## Requirement IDs

- `CAND-014` — Age/minor data is private and excluded from matching.
- M02 — Protected DOB/minor state (never ranking input).
- Security/privacy contract — protected candidate attributes are separate from
  the professional profile and employer-facing data.

`CAND-013` (parent/legal-representative consent-document flow) remains a later,
separate work unit.

## Current behavior

`candidate_profile` has no date-of-birth field. The candidate profile API is
self-scoped but intentionally contains only professional fields, so there is
no protected DOB/minor-state read or update path and no UI for it.

## Proposed design

- Add a nullable `date_of_birth` column to `candidate_profile`.
- Add candidate-only `GET`/`PATCH /api/v1/candidate/protected-profile` routes.
- Require processing consent for writes; compute `minor_state` from DOB and the
  configurable `adult_age_years` setting (18 by default).
- Return the DOB and derived state only from the protected route. Keep it absent
  from the professional profile response and any future matching input.
- Record only a non-PII state transition in `audit_event`.
- Add a responsive candidate UI with loading, empty, validation/error, save and
  success states, plus an explicit privacy/ranking explanation.

## Files/modules

- `backend/alembic/versions/20261007_0004_protected_candidate_attributes.py`
- `backend/app/config.py`, `backend/app/protected_candidate.py`,
  `backend/app/main.py`
- `backend/tests/test_protected_candidate.py`
- `frontend/src/components/candidate-protected-profile.tsx`,
  `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/API_GUIDELINES.md`, `docs/DATA_MODEL.md`, `docs/SECURITY.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

`candidate_profile.date_of_birth` is a nullable SQL `DATE`. The protected
response contains `date_of_birth`, `minor_state` (`not_set`, `minor`, or
`adult`), and the configured threshold. No exact age is returned or persisted.
`PATCH` accepts a date or `null` and never accepts a client-supplied state.

## Security/privacy implications

The server resolves the candidate profile through the verified token subject and
candidate role dependency. Employer tokens receive the standard role error;
another candidate receives only their own row. DOB is not included in the
professional profile, audit details, logs, or matching inputs. This unit does
not claim that a minor has supplied legal-representative consent.

## Test plan

- migration creates the protected column;
- candidate reads empty state, saves adult/minor DOB, reloads and clears it;
- processing consent gates writes;
- future/invalid DOB is rejected without persistence;
- employer access is rejected and another candidate cannot read the value;
- audit details contain state transition only, never DOB/email;
- professional profile remains free of protected fields;
- backend tests, Ruff, frontend typecheck and build pass.

## Demo/evidence

Backend integration tests and the signed-in candidate UI demonstrate the
protected boundary. Status is `IMPLEMENTED`; the external supervisor owns
verification and must not promote it to `VERIFIED` here.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished item in M02.
- 2026-10-07: kept legal-representative document upload/status out of this
  slice because its exact wording and retention policy are still configurable.
- 2026-10-07: implemented migration, candidate-only protected API, consent
  gate, server-derived state, non-PII audit transition and responsive UI.
  Backend (28 tests), Ruff, frontend typecheck and production build pass;
  status remains `IMPLEMENTED` pending external supervisor verification.
