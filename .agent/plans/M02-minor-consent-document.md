# M02 — Parent/legal-representative consent document

## Purpose / user value

Give a minor candidate a private, auditable way to attach the required
parent/legal-representative consent document before making the professional
profile discoverable. The document must never be returned to employers or
included in matching/reporting data.

## Requirement IDs

- `CAND-013` — Minor candidate can upload private parent/legal-representative consent documentation.
- `CAND-014` — Age/minor data remains private and excluded from matching.
- Product specification §14 / conference clarification §8 — document status is private,
  configurable and legally reviewable.

## Current behavior

The candidate can store a server-derived minor state from a private DOB, but no
document metadata/storage, upload/status API, or publication gate exists. The
privacy API can therefore mark a minor discoverable without the required
representative document.

## Proposed design

- Add a `minor_consent_document` table with candidate ownership, policy version,
  safe metadata, content digest, status, and optional reviewer audit fields.
- Store the uploaded PDF under a UUID-based key in a configured private storage
  directory; never expose that key or serve the file through an employer-facing route.
- Add candidate-only `GET` and multipart `POST /api/v1/candidate/minor-consent-document`.
  Accept a bounded PDF with a PDF signature, replace the previous current record,
  and return status/metadata only.
- Gate publication/discoverability for a server-derived minor on a submitted
  current document. Processing consent remains required for upload and privacy changes.
- Add non-PII upload/replacement audit events and candidate/employer/self-scope tests.
- Add a candidate UI panel shown only for the minor state.

## Files/modules

- `backend/alembic/versions/20261007_0005_minor_consent_document.py`
- `backend/app/config.py`, `backend/app/minor_consent.py`, `backend/app/privacy.py`,
  `backend/app/main.py`
- `backend/tests/test_minor_consent.py`
- `frontend/src/components/candidate-minor-consent.tsx`,
  `frontend/src/components/candidate-protected-profile.tsx`,
  `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/API_GUIDELINES.md`, `docs/DATA_MODEL.md`, `docs/SECURITY.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

`GET` returns the authenticated candidate's derived minor state, whether a
document is required, policy version, and current safe metadata. `POST` accepts
one `document` multipart part and returns `201` with metadata. Only `submitted`
documents satisfy the publication gate in this work unit; reviewer workflow and
legal wording remain future configurable policy work.

## Security/privacy implications

All document operations are candidate-role and identity scoped. File names are
stored as a display label only; storage keys are UUIDs. The API never returns
file bytes, storage paths, DOB, email, or raw content. Employers receive the
normal role error, and audit details contain only non-PII identifiers/status.

## Test plan

- minor candidate uploads a valid PDF and sees current submitted status;
- non-PDF, wrong signature, oversized, missing-consent, adult, and no-DOB cases
  are rejected without a database/file partial update;
- publication is rejected before upload and succeeds after upload;
- replacement marks the previous record replaced and stores a distinct file;
- another candidate and an employer cannot read or upload the document;
- uploaded bytes are present only in configured private storage and not in API output;
- migration, backend tests, Ruff, frontend typecheck/build pass.

## Demo/evidence

The signed-in candidate UI shows the private document status and upload control
after a minor DOB is saved. Backend integration tests are the primary evidence;
external supervisor owns verification and must not promote this work beyond
`IMPLEMENTED`.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished work unit in M02.
- 2026-10-07: exact legal wording and reviewer approval remain configurable;
  this slice uses a server policy version and treats a validated private upload
  as `submitted` evidence for publication gating.
- 2026-10-07: implemented migration, private storage adapter, candidate-only
  API/UI, publication invariant, audit events and integration tests. Status is
  `IMPLEMENTED`; external supervisor owns verification.
