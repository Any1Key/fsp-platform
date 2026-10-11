# M15 upload hardening

## Purpose / user value

Keep candidate resumes and minor legal-representative documents private when
they cross the API boundary. Upload metadata must not become a filesystem
path, oversized or non-PDF content must not be persisted, and a failed upload
must not leave a usable partial artifact.

## Requirement IDs

- `LEGAL-001` — 152-FZ-oriented data minimization, consent, RBAC, and audit
  controls; this slice supplies private-upload and storage-boundary evidence.
- Supporting `CAND-002` — PDF resume upload and extraction.
- Supporting `CAND-013` — private minor-consent document upload.

## Current behavior

Resume and minor-consent services duplicated PDF checks and private-file
writes. Existing-directory permissions were not reasserted, control
characters in display filenames were accepted, and file creation did not use
a shared no-follow atomic storage primitive.

## Proposed design

- Centralize bounded PDF validation for both upload types.
- Normalize only display filenames, reject control characters and enforce a
  UTF-8 filesystem-safe length; never use the original filename as a path.
- Reassert mode `0700` on the private root and reject a configured root
  symlink.
- Create storage files with exclusive creation, `O_NOFOLLOW` when available,
  mode `0600`, flush/fsync, and transaction-safe cleanup.

## Files/modules

- `backend/app/upload_security.py` — shared validation and private storage.
- `backend/app/resume.py`, `backend/app/minor_consent.py` — use the shared
  boundary while preserving endpoint contracts.
- `backend/tests/test_upload_security.py` — unit tests for filenames,
  storage-root and atomic permission behavior.
- `backend/tests/test_resume_upload.py`, `backend/tests/test_minor_consent.py`
  — integration coverage remains the candidate/minor end-to-end evidence.
- `docs/SECURITY.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` —
  upload contract and implemented evidence.

## Data/API changes

No schema or response changes. Existing safe filename metadata and error codes
are preserved; storage paths, hashes, and bytes remain private.

## Security/privacy implications

The shared boundary limits parser input before persistence, excludes path and
control-character injection through filenames, repairs private directory
permissions, prevents final-path symlink following, and cleans up failed
writes. Consent and candidate ownership checks remain in the domain services.

## Test plan

- Unit-test shared PDF validation for control characters, Windows separators,
  byte-length limits, MIME/signature/size checks, and private-root traversal.
- Unit-test existing-root permission repair, mode `0600` storage, exclusive
  replacement refusal, and root-symlink rejection.
- Run resume/minor integration tests and the full backend test suite.

## Demo/evidence

The candidate resume and minor-consent API tests demonstrate consent,
ownership, safe metadata, bounded PDF input, and no partial storage. The
shared unit tests demonstrate the filesystem hardening independently of the
database.

## Progress / decisions / surprises

- 2026-10-11: selected as the first unfinished M15 backlog work unit.
- 2026-10-11: retained basename normalization for compatibility with the
  existing safe display metadata contract; added explicit control-character
  rejection rather than exposing upload filenames as paths.
