# M02 candidate dashboard

## Purpose / user value

Give an authenticated candidate one responsive view of the current assessed
category/grade and the history that explains how that state was reached. Keep
unconfirmed grades visible and clearly labeled so the dashboard does not turn
an incomplete assessment into a false verified claim.

## Requirement IDs

- CAND-004 — show category/grade and assessment history.
- CAND-012 — candidate data is self-scoped and cannot be read by another user.
- NFR-009 — candidate dashboard remains usable on tablet/mobile layouts.

## Current behavior

Candidate profile, privacy, protected-profile and resume panels exist, but
there is no candidate-scoped dashboard endpoint or UI. The calibrated
assessment service stores bootstrap attempts in memory and already has the
candidate ID, result state, score and creation time needed for a summary.

## Proposed design

- Add an authenticated `GET /api/v1/candidate/dashboard` endpoint.
- Resolve assessment ownership from the verified principal subject, never from
  a client-supplied candidate ID.
- Return the safe current assessment summary, cooldown timestamp, profile
  display fields and a chronological list of public attempt summaries.
- Render loading, error, empty, verified and unconfirmed states in the signed-in
  candidate experience; do not render answer keys, integrity telemetry or
  protected identity data.

## Files/modules

- `backend/app/assessments.py` — candidate-scoped history projection.
- `backend/app/main.py` — typed dashboard response and route.
- `backend/tests/test_candidate_dashboard.py` — API, state and privacy tests.
- `frontend/src/components/candidate-dashboard.tsx` — responsive dashboard UI.
- `frontend/src/components/auth-status.tsx` — mount the dashboard for candidates.
- `frontend/src/app/globals.css` — dashboard states and responsive layout.
- `docs/API_GUIDELINES.md`, `docs/CANDIDATE_DASHBOARD.md` — API/UI contract.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — mark only the implemented
  requirement evidence.

## Data/API changes

`GET /api/v1/candidate/dashboard` returns profile display fields, a nullable
`current_assessment`, `retest_available_at`, and safe attempt summaries. The
route is candidate-role-only and has no client-controlled subject parameter.

## Security/privacy implications

The route uses the existing server-side candidate role dependency and keys the
projection by the authenticated principal subject. It does not return email,
DOB/minor state, contact data, answer keys, integrity telemetry or assessment
prompts. Employer access receives the standard role error.

## Test plan

- empty candidate dashboard has a stable empty state;
- submitted verified and unconfirmed attempts are projected correctly;
- attempt history is candidate-scoped and does not cross between subjects;
- employer access is denied;
- frontend typecheck/build and the focused backend tests pass.

## Demo/evidence

The dashboard is mounted in the authenticated candidate workspace and exposes
verified, unconfirmed and no-assessment states. Evidence is recorded as
IMPLEMENTED; external supervisor owns VERIFIED.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished unit in M02 because CAND-004
  is the only remaining M02 work item that can be completed coherently with
  the current assessment bootstrap repository.
- 2026-10-07: implemented the candidate-subject projection, typed dashboard
  route, responsive signed-in UI and empty/verified/unconfirmed/history states.
  Full backend suite (44 tests), Ruff, frontend typecheck and production build
  pass. CAND-004 is IMPLEMENTED; verification remains with the external
  supervisor.
