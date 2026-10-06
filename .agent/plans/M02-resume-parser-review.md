# M02 resume parser and review

## Purpose / user value

Let a candidate turn an uploaded PDF into an editable profile draft without
silently publishing parser claims. The candidate can inspect provenance and
confidence, edit the professional fields, then explicitly save them.

## Requirement IDs

- CAND-002 — PDF resume upload + extraction.
- CAND-001 — the approved professional fields reuse the existing candidate
  profile boundary.
- LEGAL-001 — consent-gated processing and data minimization.

## Current behavior

The candidate upload endpoint validates and stores a private PDF, but returns
only document metadata. Parsing and review are not implemented.

## Proposed design

Add a deterministic, CPU-only parser using PDF text extraction plus bounded
section/pattern rules and a small skill dictionary. Store only structured
extraction JSON and status on a candidate-owned `resume_extraction` record;
do not persist raw extracted text. Upload creates `needs_review` extraction.
The candidate can accept edited professional fields or reject the draft.
Contacts are shown only in the private review response and are never imported
into the profile model. Accepted data is ordinary candidate-declared evidence,
not a verified grade/category.

## Files/modules

- `backend/app/resume_parser.py` — text extraction and deterministic mapping.
- `backend/app/resume.py` — extraction persistence and review use cases.
- `backend/app/main.py` — response/request models and review route.
- `backend/alembic/versions/*resume_extraction.py` — schema.
- `backend/tests/test_resume_parser.py`, `backend/tests/test_resume_upload.py`.
- `frontend/src/components/candidate-resume.tsx` and `globals.css` — review UI.
- `docs/RESUME_PARSING.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`.

## Data/API changes

- Upload/GET resume responses include a structured extraction and status.
- `PATCH /api/v1/candidate/resume/{document_id}/review` accepts explicit
  candidate-edited fields and `accepted: true|false`.
- Accepted review writes only display name, headline, summary, skills, and
  experience to `candidate_profile`; no contact field is added.

## Security/privacy implications

Processing remains blocked without candidate processing consent and all routes
remain candidate-self scoped. Parser input is bounded by the existing upload
limit. Stored fields are structured, public-profile-safe claims; contacts are
not included in profile writes or logs.

## Test plan

- deterministic parser extracts known name, contacts, skills, grade, roles,
  dates, and soft skills from a text fixture;
- upload creates `needs_review` extraction and does not mutate profile;
- explicit accept persists edited professional fields and marks extraction
  reviewed;
- reject leaves profile unchanged;
- consent, employer-role, and cross-candidate boundaries remain enforced;
- frontend typecheck/build and backend targeted tests.

## Demo/evidence

Candidate dashboard shows “needs review”, extracted confidence/provenance, and
explicit save/reject actions. Evidence path will be recorded as IMPLEMENTED in
the matrix; external supervisor owns VERIFIED.

## Progress / decisions / surprises

- 2026-10-07: selected synchronous deterministic extraction for the MVP so the
  core flow has no worker or GPU dependency. Scanned/image-only PDFs return an
  `unsupported` extraction state and remain safely reviewable as unparsed.
