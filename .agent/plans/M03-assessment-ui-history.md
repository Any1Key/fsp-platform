# M03 — Candidate assessment UI and history

## Purpose / user value

Let an authenticated candidate choose a specialization and declared grade,
complete the generated base assessment, see the system-scored outcome, and
return to a self-scoped history that clearly distinguishes verified and
unconfirmed grades.

## Requirement IDs

AST-001, AST-002, AST-003, CAND-004 (assessment UI/history slice), AUTH-004
(server-side candidate ownership boundary).

## Current behavior

The calibrated assessment factory and candidate dashboard projection exist,
but assessment endpoints accept a caller-supplied `candidate_id` without
authentication. The frontend only renders the dashboard summary; it cannot
start or submit an assessment.

## Proposed design

- Require the authenticated candidate principal for assessment create, read,
  and submit routes.
- Derive the candidate ID from the Keycloak subject and reject access to
  another candidate's attempt as not found.
- Preserve server-side answer keys and deterministic scoring.
- Add a responsive assessment panel with specialization/grade selection,
  generated item form, progressive follow-ups, submit state, and result
  refresh through the existing dashboard endpoint.
- Render the supported calibrated specialization from the taxonomy catalog;
  unsupported catalog entries remain visible but disabled until their
  blueprint is administered.

## Files/modules

- `backend/app/main.py` — authenticated assessment request models/routes.
- `backend/tests/test_assessments.py` — authenticated API ownership and
  candidate flow evidence.
- `backend/tests/test_errors.py` — authenticated assessment error contract.
- `frontend/src/components/candidate-assessment.tsx` — candidate assessment
  flow.
- `frontend/src/components/candidate-dashboard.tsx` and
  `frontend/src/components/auth-status.tsx` — refresh and mounting.
- `frontend/src/app/globals.css` — responsive states and form styling.
- `docs/ASSESSMENT_ENGINE.md`, `docs/CANDIDATE_DASHBOARD.md`,
  `docs/API_GUIDELINES.md` — current UI/API behavior.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — IMPLEMENTED evidence.

## Data/API changes

The existing assessment paths become authenticated candidate resources:

- `POST /api/v1/assessments/attempts`
- `GET /api/v1/assessments/attempts/{attempt_id}`
- `POST /api/v1/assessments/attempts/{attempt_id}/submit`

Create no longer accepts `candidate_id`; the server derives it from the
verified principal. The process-local repository remains the documented
bootstrap storage boundary.

## Security/privacy implications

Answer keys remain server-only. Attempt IDs cannot be used to read or submit
another candidate's assessment. The UI does not collect or expose DOB,
contacts, or other protected profile data. Integrity signals remain advisory.

## Test plan

- authenticated candidate can create and submit an attempt;
- create ignores caller-owned identity fields by rejecting `candidate_id`;
- another candidate cannot read or submit the attempt;
- employer and unauthenticated callers are rejected;
- browser-safe response still excludes answer keys and exposes the scored
  result only after submission;
- frontend typecheck/build succeeds.

## Demo/evidence

Backend integration tests cover the authenticated candidate lifecycle and
authorization boundary. The candidate page mounts the assessment panel beside
the Skill Passport history. External supervisor owns VERIFIED status.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished work unit in M03.
- 2026-10-07: kept the process-local repository because persistence is not
  part of this UI/history slice; ownership is enforced at the API boundary.
- 2026-10-07: implemented authenticated create/read/submit ownership, the
  responsive candidate assessment panel, dashboard refresh, documentation,
  and regression coverage. Backend suite: 47 passed; frontend typecheck and
  production build passed.
