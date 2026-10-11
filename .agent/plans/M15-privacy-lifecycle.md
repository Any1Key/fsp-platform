 # M15 privacy lifecycle requests

 ## Purpose / user value

 Give candidates a complete, auditable privacy-control flow for consent withdrawal,
 data export, and account deletion requests without exposing protected data or
 performing irreversible deletion before the retention/legal policy is fulfilled.

 ## Requirement IDs

 - CAND-010 — privacy settings and processing/publication consent
 - LEGAL-001 — 152-FZ-oriented data minimization, consent, RBAC and audit controls
 - LEGAL-002 — withdrawal/deletion/export/retention workflows or demonstrable MVP concepts

 ## Current behavior

 - Candidate can grant/withdraw processing and publication consent.
 - Processing/publication withdrawal cascades to discoverability and is audited.
 - Export requests are inserted as `requested`, but there is no request list/status
   endpoint, idempotency, retention schedule, or deletion request flow.
 - Privacy UI only exposes consent toggles and export creation.
 - `privacy_request` already allows `deletion` by schema but has no API use.

 ## Proposed design

 - Add configurable `privacy_retention_days` setting.
 - Add request lifecycle metadata (`updated_at`, `scheduled_for`) and a unique
   active-request index per identity/type.
 - Make export creation idempotent while a request is active.
 - Add candidate-only request history endpoint.
 - Add candidate-only deletion request endpoint. It immediately withdraws
   publication/discoverability and records non-PII audit events, while leaving
   destructive fulfillment queued for a reviewed worker at `scheduled_for`.
 - Return the request ledger to the privacy UI with retention/deletion explanation
   and a guarded deletion action.

 ## Files/modules

 - `backend/alembic/versions/20261011_0029_privacy_lifecycle.py`
 - `backend/app/config.py`
 - `backend/app/privacy.py`
 - `backend/app/main.py`
 - `backend/tests/test_auth.py`
 - `frontend/src/components/privacy-settings.tsx`
 - `docs/SECURITY.md`
 - `docs/LEGAL_152FZ.md`
 - `docs/API_GUIDELINES.md`
 - `.agent/BACKLOG.md`
 - `docs/REQUIREMENTS_MATRIX.md`

 ## Data/API changes

 - `GET /api/v1/candidate/privacy/requests`
 - `POST /api/v1/candidate/privacy/export` (idempotent active request)
 - `POST /api/v1/candidate/privacy/delete`
 - Request response includes id, type, status, created/updated timestamps and
   scheduled retention date.

 ## Security/privacy implications

 All endpoints use the candidate role dependency and resolve requests through the
 authenticated identity. Audit details contain only event type, request type,
 request ID and safe state; no email, document names, file contents or raw
 profile data. Deletion is not executed inline; the API only queues a reviewed
 fulfillment action and withdraws future publication immediately.

 ## Test plan

 - Candidate sees empty request history and can create export/deletion requests.
 - Repeated active export/deletion requests return the same request.
 - Deletion immediately turns off publication/discoverability and produces safe
   audit events.
 - Request history is identity-scoped; employers receive role denial.
 - Migration creates lifecycle metadata and preserves downgrade path.
 - Frontend type/build checks and privacy contract checks pass.

 ## Demo/evidence

 - Privacy UI shows active request status and scheduled retention date.
 - API integration tests in `backend/tests/test_auth.py`.
 - Updated security/legal docs and requirements evidence.

 ## Progress / decisions / surprises

- 2026-10-11: Selected as the first unfinished M15 backlog unit.
- Existing export concept is retained and extended rather than replaced.
- Destructive deletion stays queued because exact retention/legal wording is an
  explicit clarification/open legal-review item.
- 2026-10-11: Implemented migration, candidate-scoped APIs/UI, idempotency,
  immediate withdrawal, audit coverage and retention scheduling. Supervisor
  verification remains outstanding.
