# M01 — Consent and privacy controls

## Purpose / user value

Let a candidate make an explicit, versioned choice about platform processing
and employer discoverability, withdraw publication safely, and request a data
export without exposing private data to another account.

## Requirement IDs

- CAND-010 — privacy settings and processing/publication consent.
- NFR-006 — RBAC, secure tokens, consent/privacy.
- LEGAL-001 — 152-FZ-oriented minimization, consent, RBAC and audit controls.
- LEGAL-002 — withdrawal/export MVP concept.

This is the consent/privacy slice of M01. Candidate profile fields, minor
documents and deletion/retention execution remain in later milestones.

## Current behavior

The foundation schema has only `candidate_profile.is_discoverable` and a bare
`publication_consent_at` column. There is no processing consent, version/source
provenance, candidate privacy endpoint, audit record, export request concept,
or candidate UI for changing these settings.

## Design

- Add versioned processing and publication consent fields to
  `candidate_profile`; the active policy version comes from application
  settings and is never supplied by the browser.
- Add a minimal `audit_event` table containing only actor, event type, and
  structured non-PII details. Record consent grants/withdrawals and
  discoverability changes.
- Add `privacy_request` with an authenticated export request state. The MVP
  records the request and its audit event; a later privacy worker can fulfill
  it without changing this authorization boundary.
- Add self-scoped candidate `GET/PATCH /api/v1/candidate/privacy` and
  `POST /api/v1/candidate/privacy/export`. Processing consent is required for
  publication consent; publication consent is required for discoverability.
  Withdrawal turns off dependent settings and removes the candidate from
  future search.
- Add a candidate-only browser panel with loading, error, saved, disabled and
  export-request states. Employer and unauthenticated sessions never receive
  candidate privacy data.

## Files/modules

- `backend/alembic/versions/20261006_0002_privacy_consent.py`
- `backend/app/privacy.py`, `backend/app/config.py`, `backend/app/main.py`,
  `backend/app/errors.py`
- `backend/tests/test_auth.py`, `backend/tests/test_migrations.py`
- `frontend/src/components/privacy-settings.tsx`,
  `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`,
  `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`

## Test plan

- A candidate starts with all privacy choices off, cannot publish without
  processing consent, and cannot become discoverable without publication
  consent.
- Granting both consents and discoverability returns the current policy
  version and timestamps; withdrawal removes discoverability and leaves audit
  evidence without storing token or contact data.
- Export requests are self-scoped, idempotency is not implied, and each request
  is persisted as `requested` with a safe audit event.
- Employer and unauthenticated requests are rejected by server-side role
  checks; existing authentication and migration tests remain green.
- Run backend pytest/Ruff and frontend typecheck/build.

## Progress / decisions / surprises

- 2026-10-06: selected as the highest-priority unfinished backlog unit.
- 2026-10-06: used the configured policy version (`2026-10-06`) and a stored
  export-request concept because exact legal wording and fulfillment/retention
  rules require later legal review and worker infrastructure.
- 2026-10-06: implemented migration, self-scoped API, candidate UI, audit
  events, export request state and regression tests. Backend: 22 tests passed
  and Ruff passed; frontend typecheck and production build passed. External
  supervisor owns verification.
