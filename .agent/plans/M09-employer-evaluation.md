# M09 employer-owned evaluation and evidence isolation

## Purpose / user value

After a matched candidate submits an employer-authored task, the owning
employer can review the preserved task version and candidate submissions,
grade each rubric dimension, and optionally release a final score/feedback to
the candidate. The result remains evidence for that employer's hiring
pipeline and never changes the platform-wide verified grade.

## Requirement IDs

- EMP-013 — Employer is final grader for employer-authored tasks.
- EMP-015 — Employer-specific result does not silently overwrite global
  verified grade.
- Supporting M09 contract — employer-specific evaluation is scoped to the
  matched assignment/task version and may be released to the candidate.

## Design

- Add one `employer_evaluation` per assignment. It stores the owning employer
  identity, the derived 0–100 score, rubric awards, feedback, release state,
  and audit timestamps.
- Add employer-only assignment listing scoped through the employer-owned
  company/hiring need. It includes candidate professional label, preserved
  task version/rubric, and submission history; no unrelated assignment is
  visible.
- Add an employer-only upsert evaluation endpoint. The service validates that
  all rubric dimensions match the assigned immutable version, awards stay
  within each dimension's points, and derives the total score. An evaluation
  requires a candidate submission. Re-saving updates the same employer-owned
  evidence row and can release it.
- Candidate assignment responses expose only a released evaluation's score,
  feedback and release time. Rubric details remain employer-only.
- No platform assessment tables are written or read by the evaluation write
  path. Regression tests compare the candidate dashboard/global assessment
  before and after grading.

## Files/modules

- `backend/alembic/versions/20261007_0018_employer_evaluations.py`
- `backend/app/employer_evaluations.py`
- `backend/app/task_assignments.py`, `backend/app/main.py`,
  `backend/app/errors.py`
- `backend/tests/test_employer_evaluations.py`, `backend/tests/test_migrations.py`
- `frontend/src/components/employer-task-authoring.tsx` or a focused employer
  evaluation panel, `frontend/src/components/candidate-task-assignments.tsx`
- `docs/API_GUIDELINES.md`, `docs/EMPLOYER_ASSESSMENTS.md`,
  `docs/DATA_MODEL.md`, `.agent/BACKLOG.md`,
  `docs/REQUIREMENTS_MATRIX.md`

## API

- `GET /api/v1/employer/task-assignments`
- `PUT /api/v1/employer/task-assignments/{assignment_id}/evaluation`
- Candidate assignment responses add nullable `evaluation`, populated only
  when the owning employer has released it.

## Test plan

- migration creates/drops evaluation storage and foreign keys;
- employer sees only matched assignments belonging to its company and can
  grade submitted responses;
- invalid/missing/foreign rubric dimensions are rejected without writes;
- candidate sees no unreleased evaluation and sees released score/feedback;
- candidate, outsider employer, and pre-match access cannot read or mutate
  another employer's assignment;
- evaluation updates the employer evidence row only; candidate global
  assessment/dashboard is unchanged;
- backend suite, lint, and frontend typecheck/build remain green.

## Status

- 2026-10-07: selected as the highest-priority unfinished M09 work unit.
- 2026-10-07: implemented migration, employer review/evaluation API, released
  candidate projection, responsive employer/candidate UI, privacy/ownership
  tests and global-grade regression evidence. Status is `IMPLEMENTED`; external
  supervisor owns verification.
