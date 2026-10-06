# M02 — Private PDF resume upload validation

## Purpose / user value

Let a consented candidate attach a PDF resume safely so the later parser/review
flow has a private, validated source document. The upload must not expose file
bytes, paths, or resume contents to employers or logs.

## Requirement IDs

- `CAND-002` — PDF resume upload + extraction (this plan implements the upload
  and validation boundary; extraction/review remains the next M02 unit).
- `CAND-012` — candidate private data is self-scoped.
- Product journey — `consent/privacy → profile/resume`.
- Security upload controls — validate PDF filename, MIME, signature and size;
  isolate private storage and audit safe metadata only.

## Current behavior

Candidates have a consent-gated manual profile and a separate private minor
consent-document workflow, but no resume metadata table, storage adapter,
candidate resume API, or UI. The product specification expects PDF upload
before the parser/review step.

## Proposed design

- Add a `resume_document` table containing candidate ownership, safe display
  metadata, digest, UUID storage key, status and timestamps.
- Store bytes below the configured private storage directory with a UUID key and
  mode `0600`; retain replaced files for later retention handling.
- Add candidate-only `GET` and multipart `POST /api/v1/candidate/resume`.
  Require processing consent, accept only bounded PDF uploads, and return
  metadata/status without bytes or storage details.
- Mark the previous current resume `replaced` on successful replacement and
  write non-PII audit events. Database and filesystem changes are atomic from
  the API caller's perspective; failed writes roll back both sides.
- Add a signed-in candidate UI with loading, empty, error, success and upload
  disabled states. Explain that extraction/review follows in a later step.

## Files/modules

- `backend/alembic/versions/20261007_0006_resume_document.py`
- `backend/app/config.py`, `backend/app/resume.py`, `backend/app/main.py`
- `backend/tests/test_resume_upload.py`
- `frontend/src/components/candidate-resume.tsx`,
  `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/API_GUIDELINES.md`, `docs/DATA_MODEL.md`, `docs/SECURITY.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

`GET /api/v1/candidate/resume` returns the authenticated candidate's latest
safe metadata or `document: null`. `POST` accepts one `resume` multipart PDF
and returns `201` with the new current metadata. The service never returns
`storage_key`, digest, or file bytes.

## Security/privacy implications

The endpoint is candidate-role and identity scoped and requires processing
consent. Filename paths are reduced to a display basename. Storage keys are
UUIDs; file mode and root checks prevent traversal. Audit details contain only
opaque document IDs and state transitions. No parsed resume text is created or
logged in this slice.

## Test plan

- valid upload returns safe metadata and writes a `0600` private file;
- missing consent, wrong role, wrong extension/MIME/signature and oversized
  input fail without database/filesystem partial state;
- replacement marks the prior row replaced and leaves distinct protected files;
- another candidate cannot read the document; employers receive `ROLE_REQUIRED`;
- migration and full backend/frontend checks pass.

## Demo/evidence

The candidate panel shows current filename/size/status, an empty state, upload
success and validation/error feedback. Primary evidence is
`backend/tests/test_resume_upload.py`; external supervision owns verification.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished unit in M02.
- 2026-10-07: kept parser, extracted-field review, standardized PDF generation,
  and employer visibility out of scope; they require separate evidence and do
  not become silently implied by this upload boundary.
- 2026-10-07: implemented migration, private storage/API, candidate UI,
  validation/replacement/audit tests, and documentation. Backend tests (35),
  Ruff, frontend typecheck, and production build pass. CAND-002 remains
  `IN_PROGRESS` until the parser/review unit is implemented; supervisor owns
  promotion beyond implementation status.
