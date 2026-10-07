# M10 — Employer review feedback for local-AI task drafts

## Purpose / user value

Give employers a clear human-control loop for local-AI suggestions: they can
keep a useful draft, record edits, or reject it, while the platform remains
usable with AI disabled and no suggestion is published implicitly.

## Requirement IDs

- `EMP-014` — local CPU AI may propose employer task/rubric drafts from the
  current need and approved employer task history.
- `NFR-012` — optional local AI is isolated, asynchronous and has a
  deterministic fallback when disabled or unavailable.

## Scope

Complete the employer review loop for an optional task draft. The employer can
explicitly approve, edit, or reject a generated suggestion. The decision is
stored as employer/company-scoped feedback with a sanitized need snapshot and,
for approval or edit, the reviewed draft. Feedback is advisory memory only: it
does not publish a task, alter the platform grade, or make AI required.

## Current behavior

The constrained draft endpoint can return a need-validated suggestion and the
authoring UI can apply it to the editable task form, but no review decision or
review history is persisted.

## Design

- Add a migration-backed `employer_task_draft_feedback` table with decision,
  reviewed draft JSON, optional employer note, need snapshot, and timestamps.
- Add an employer-only feedback API that validates an approved/edited draft
  against the current hiring need and returns a stable history projection.
- Keep rejected drafts content-free by default; store only the decision and
  optional bounded note.
- Show feedback actions and recent feedback in the authoring panel. Applying a
  suggestion still only changes the editable form; the employer must save and
  publish separately.
- Add integration tests for all decisions, validation, ownership, persistence,
  and the AI-off/manual fallback path.

## Files / modules

- `backend/alembic/versions/20261008_0020_employer_draft_feedback.py`
- `backend/app/local_ai.py`, `backend/app/main.py`, `backend/app/errors.py`
- `frontend/src/components/employer-task-authoring.tsx` and its styles
- `backend/tests/test_local_ai.py`, `backend/tests/test_migrations.py`

## Data / API changes

- Add employer/need-scoped `employer_task_draft_feedback` records.
- Extend draft suggestions with recent feedback history.
- Add employer-only `GET` and `POST`
  `/api/v1/employer/tasks/draft-suggestion/feedback` endpoints.

## Security / privacy implications

Ownership is checked through the authenticated employer company and current
hiring need. Rejected generated content is not stored, and the stored need
snapshot and reviewed drafts are returned only to that employer. Feedback does
not expose candidate data or influence candidate matching/global grade.

## Test plan

- Verify all feedback decisions round-trip and are ordered in employer-scoped
  history.
- Reject missing/invalid drafts and confirm no task is published.
- Verify migration tables/foreign keys, full backend suite, Ruff, and frontend
  typecheck/build.

## Demo / evidence

In Employer Task Authoring, request a suggestion, optionally apply/edit it,
choose Approve, Save as edited, or Reject, and observe the decision in Recent
decisions. The task still requires the separate Save draft and Publish actions.

## Verification

- Run focused local-AI and migration tests, then the full backend suite.
- Run Ruff on changed backend files.
- Run the frontend TypeScript check/build contract.

## Progress

- Plan created before implementation.
- Implemented migration, employer-scoped feedback API/history, need-aware
  validation, authoring-panel actions, focused integration tests, and docs.
