# M13 — Validation Dashboard

## Purpose / user value

Give the jury/demo reviewer one responsive view of the deterministic synthetic
matching and assessment validation evidence already produced by M13. The view
must make grade discrimination, confusion data, ranking metrics, and integrity
signals visible without exposing candidate PII or assessment answer material.

## Requirement IDs

- `INNOV-007` — Validation Dashboard demo UI.

## Current behavior

`backend/app/matching_metrics.py` and `backend/app/assessment_validation.py`
produce reproducible offline artifacts, but there is no aggregate API or
frontend projection. The existing employer workspace has no validation panel.

## Proposed design

- Add a cached, deterministic dashboard projection that composes the default
  matching-metrics and assessment-validation reports.
- Expose `GET /api/v1/validation/dashboard` to authenticated employers,
  reviewers, and admins. Candidates remain forbidden. The response contains
  only aggregate synthetic IDs/metrics and no raw labels, answers, identities,
  or contact data.
- Add a responsive employer-side dashboard with loading, error, metric,
  confusion-matrix, item-discrimination, and calibration-caveat states.

## Files/modules

- `backend/app/validation_dashboard.py` — projection and cache.
- `backend/app/main.py` — typed response models, dependency boundary, route.
- `backend/tests/test_validation_dashboard.py` — API/auth/privacy contract.
- `frontend/src/components/validation-dashboard.tsx` — demo UI.
- `frontend/src/components/auth-status.tsx` — employer workspace mount.
- `frontend/src/app/globals.css` — dashboard visual/responsive states.
- `docs/API_GUIDELINES.md` and `docs/VALIDATION_DASHBOARD.md` — contract and
  evidence documentation.

## Data/API changes

No database migration. The API is read-only and computes a fixed-seed report
from the repository-owned synthetic fixtures. Dashboard version and source
versions are explicit in the response for auditability.

## Security/privacy implications

The route requires a validated `.ru` Keycloak identity with employer,
reviewer, or admin role. Candidate identities are rejected server-side. The
projection is aggregate and excludes raw relevance labels, answer keys,
submission text, email addresses, and database records.

## Test plan

- authenticated employer receives stable matching and assessment aggregates;
- candidate and unauthenticated requests are rejected;
- response contains no PII or answer-key fields;
- repeated projections are deterministic and include confusion/discrimination
  evidence;
- backend focused tests plus frontend typecheck/build.

## Demo/evidence

The employer workspace shows the dashboard after Talent Radar. The dashboard
labels the metrics as synthetic calibration evidence and surfaces the two
non-positive item-discrimination observations rather than hiding them.

## Progress / decisions / surprises

- 2026-10-10: selected as the first unfinished M13 work unit after the
  completed validation dataset, labeled relevance, baseline, metric, and
  assessment-validation units.
- 2026-10-10: implemented the cached aggregate API, employer demo panel,
  privacy/role tests, documentation, and responsive styles. Focused backend
  tests (3), opt-in responsive Playwright scenario, frontend typecheck, and
  production build pass. Requirement
  `INNOV-007` is `IMPLEMENTED`; external supervisor retains verification and
  readiness ownership.
