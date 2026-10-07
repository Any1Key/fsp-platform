# M09 employer task authoring/versioning

## Purpose / user value

Let an employer define a job-specific task in the Hiring Pipeline, edit it as
a draft, and explicitly publish a version. Candidates are not exposed to task
content until the later assignment unit; this slice establishes the employer's
ownership and audit boundary for task definitions.

## Requirement IDs

- EMP-012 — Employer can author job-specific tasks/tests.
- Supporting M09 contract: employer-authored task content is distinct from the
  platform-wide verified grade and remains employer-owned.

## Current behavior

The platform stores ordered pipeline stages and safe invitation previews, but
has no task content, version records, draft/publish lifecycle, or employer UI
for task authoring.

## Proposed design

- Add `employer_task` and immutable `employer_task_version` tables.
- Attach a task to the employer's current hiring need and an
  `employer_task` pipeline stage. The stage reference is nullable only so a
  later pipeline edit cannot delete task history; creation requires a stage
  belonging to that employer's pipeline. No candidate-facing task route is
  introduced here.
- Create version 1 as a draft. Editing a published task creates a new draft
  version. Publishing is explicit and only one version is published at a time.
- Store target skill slugs, expected grade, time/deadline policy, and rubric
  dimensions as validated JSON owned by the employer task version.
- Expose employer-only list/create/edit-version/publish endpoints and a
  responsive editor in the employer workspace.

## Files/modules

- `backend/alembic/versions/20261007_0016_employer_task_authoring.py`
- `backend/app/employer_tasks.py`
- `backend/app/main.py`, `backend/app/errors.py`
- `backend/tests/test_employer_tasks.py`
- `frontend/src/components/employer-task-authoring.tsx`, `auth-status.tsx`,
  `globals.css`
- `docs/EMPLOYER_ASSESSMENTS.md`, `docs/API_GUIDELINES.md`, `docs/DATA_MODEL.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

Employer-only:

- `GET /api/v1/employer/tasks`
- `POST /api/v1/employer/tasks`
- `POST /api/v1/employer/tasks/{task_id}/versions`
- `PATCH /api/v1/employer/tasks/{task_id}/draft`
- `POST /api/v1/employer/tasks/{task_id}/publish`

The API returns task/version metadata and content only to the owning employer.
Published versions are immutable; editing creates a new draft version.

## Security/privacy implications

All ownership checks derive from the authenticated Keycloak subject's local
employer identity and company/hiring need. Candidate, other-employer, and
pre-match routes cannot read task content. No candidate PII, answer key, or
grading result is stored by this slice.

## Test plan

- create, list, update draft, publish, and create a new version;
- validate employer-task stage ownership, skills, rubric and duration/deadline;
- reject candidate and other-employer access without partial writes;
- verify published version immutability and database migration readiness;
- frontend typecheck/build.

## Demo/evidence

Evidence will be recorded in `backend/tests/test_employer_tasks.py` and the
API/UI documentation. Statuses will be updated only to `IMPLEMENTED`.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished unit in M09. Assignment,
  submission, employer grading, and global-grade isolation remain TODO.
- 2026-10-07: implemented migration, ownership-scoped service, API, editor,
  integration tests, migration coverage, and evidence documentation. Version
  records retain creator/editor/publisher identity and timestamps; no candidate
  content route was added.
