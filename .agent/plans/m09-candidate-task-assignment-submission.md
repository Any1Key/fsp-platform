# M09 candidate task assignment and submission

## Purpose / user value

After a candidate accepts a salary-bearing invitation and a match is created,
the candidate can open published employer tasks, see the preserved task
version and deadline, and submit a text response. The candidate can review
submission history without exposing task content before match or to another
candidate.

## Requirement IDs

- M09 first unfinished work unit: candidate assignment/submission.
- EMP-012: employer-authored task content remains the source for the assigned
  task and published versions are immutable.
- EMP-013 and EMP-015 remain out of scope for this slice: employer grading and
  global-grade isolation are later M09 work units.

## Current behavior

Published employer tasks can be authored and versioned, and accepted
invitations create a match and chat. There is no assignment, candidate task
read model, deadline, submission persistence, or candidate UI.

## Proposed design

- Add `task_assignment`, bound to a `talent_match`, candidate, pipeline stage,
  task, and the exact published task version. The unique match/task key makes
  assignment creation idempotent.
- On match creation, assign all currently published tasks for that employer's
  hiring need. Candidate task listing also reconciles newly published tasks for
  an existing match, preserving the version selected at assignment time.
- Add append-only `task_submission` rows with numbered response history. A
  candidate may submit or revise before the server-derived deadline; each
  submission changes the assignment to `submitted`.
- Expose candidate-only list and submit endpoints. Responses include task
  instructions and safe metadata, but never employer rubric or unrelated
  candidates' records.
- Add a responsive candidate task panel with loading, empty, error, deadline,
  history, and submission states.

## Files/modules

- `backend/alembic/versions/20261007_0017_task_assignments.py`
- `backend/app/task_assignments.py`
- `backend/app/invitations.py`, `backend/app/main.py`, `backend/app/errors.py`
- `backend/tests/test_task_assignments.py`
- `frontend/src/components/candidate-task-assignments.tsx`
- `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/API_GUIDELINES.md`, `docs/EMPLOYER_ASSESSMENTS.md`,
  `docs/DATA_MODEL.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

- `GET /api/v1/candidate/task-assignments`
- `POST /api/v1/candidate/task-assignments/{assignment_id}/submissions`
- Candidate assignment response includes stage, task version, due time,
  status, and safe submission history.
- Submission response returns the refreshed assignment.

## Security/privacy implications

All assignment and submission queries are scoped through the authenticated
candidate's profile and accepted match. Employer task content is not exposed
until match. Rubric, contacts, identity subjects, and other candidates' data
are excluded. Submission bodies are not copied into audit/log metadata.

## Test plan

- Migration creates/drops the assignment and submission tables.
- Accepted match assigns only published tasks and preserves the published
  version even after a later employer draft/version change.
- Candidate can read and submit; repeated submissions are numbered and visible
  only to that candidate.
- Pre-match, outsider, employer, and unknown-assignment access is denied or
  returns an empty/not-found safe result; expired assignments cannot submit.
- Frontend typecheck/build remains green.

## Demo/evidence

The candidate workspace shows a task only after accepting an invitation. The
task card displays the stage, deadline, instructions and revision history;
the employer-authored rubric is not presented as a platform grade.

## Progress / decisions / surprises

- 2026-10-07: started from the first unchecked M09 backlog item.
- Assignment is automatic at match boundary and reconciles later published
  tasks on candidate read, so no employer-side assignment UI is needed for
  this focused slice.
- 2026-10-07: implemented migration, candidate-only API, match integration,
  responsive candidate panel, and privacy/deadline/version-history tests.
- 2026-10-07: backend full suite passed (90 tests); focused migration and
  assignment tests pass; Ruff and frontend typecheck/build pass.
