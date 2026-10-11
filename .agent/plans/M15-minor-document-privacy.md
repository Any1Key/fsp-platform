# M15 — Minor-document privacy lifecycle

## Purpose / user value

Keep parent/legal-representative consent PDFs private for their entire candidate-owned lifecycle. A candidate can replace or withdraw a document, and withdrawn/replaced bytes are removed from private storage while safe status/audit history remains.

## Requirement IDs

- CAND-013 — minor candidate can upload private parent/legal-representative consent documentation.
- CAND-014 — age/minor data is private and excluded from matching.
- NFR-006 — RBAC, secure tokens, consent/privacy.

## Current behavior

Candidate-only GET/POST upload and status endpoints validate PDFs and store UUID-keyed mode-0600 files. Replacement changes the old row to `replaced`, but the old private artifact remains on disk. There is no candidate-controlled withdrawal endpoint, so the current artifact cannot be removed through the product flow.

## Proposed design

- Add candidate-only `DELETE /api/v1/candidate/minor-consent-document`.
- Mark the current document `withdrawn`, retain only safe metadata/audit history, revoke minor publication/discoverability in the same database transaction, then remove its private artifact after the durable commit.
- Remove superseded private artifacts after a successful replacement commit.
- Keep candidate A, candidate B, and employer access isolated; never return bytes, storage keys, hashes, or audit filenames.
- Add a responsive candidate UI action for withdrawal and re-upload.

## Files/modules

- `backend/app/minor_consent.py`
- `backend/app/main.py`
- `backend/tests/test_minor_consent.py`
- `frontend/src/components/candidate-minor-consent.tsx`
- `frontend/src/app/globals.css`
- `docs/SECURITY.md`
- `docs/DATA_MODEL.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `.agent/BACKLOG.md`

## Data/API changes

No migration is required: the existing document status constraint already supports `withdrawn`. The new DELETE returns `204 No Content`; status remains available through the candidate-only GET endpoint.

## Security/privacy implications

Storage cleanup is scoped to validated UUID storage keys under the private root. Replacement/withdrawal audit events contain only document IDs and status values. Deleting the current minor document withdraws publication/discoverability before the transaction commits and removes the private artifact immediately after that durable state change.

## Test plan

- replacement removes the old private artifact;
- withdrawal removes the current artifact, marks the row withdrawn, revokes publication/discoverability, and records non-PII audit events;
- withdrawal is candidate-scoped and employer-forbidden;
- existing PDF validation, consent, no-partial-storage, and age/matching privacy tests stay green;
- backend tests plus frontend typecheck.

## Demo/evidence

Candidate protected-profile UI shows the current document status and a withdrawal action. The requirements matrix records CAND-013 as `IMPLEMENTED` with the lifecycle test evidence. External supervisor owns verification.

## Progress / decisions / surprises

- 2026-10-11: selected as the first unfinished M15 backlog work unit.
- 2026-10-11: reused the existing `withdrawn` database status and private storage boundary; no migration needed.
- 2026-10-11: implemented candidate-only withdrawal, replacement/withdrawal
  artifact cleanup, publication rollback, UI action, and authorization tests.
- 2026-10-11: focused minor-document tests (5), full backend suite (182),
  Ruff checks, and frontend TypeScript typecheck pass.
