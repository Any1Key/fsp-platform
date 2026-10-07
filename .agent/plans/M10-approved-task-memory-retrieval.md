# M10 — Approved employer-task memory and retrieval

## Purpose / user value

Give the optional employer task copilot a bounded, explainable memory of the
employer's own approved task versions. Employers can see when relevant approved
examples are available, while the core authoring flow remains usable with AI
disabled.

## Requirement IDs

- `EMP-014` — local CPU AI task/rubric assistance must use the current need and
  approved employer task history; this slice implements the approved-history
  storage and retrieval input, not generation.
- `NFR-012` — optional local AI remains isolated behind `LocalAiPort` with a
  deterministic disabled fallback; this slice keeps that boundary and adds
  bounded retrieval before an adapter call.

## Current behavior

Employer task versions can be published, but publication does not create an
approved-example index. The local-AI route calls the disabled adapter with only
the current hiring need, and the UI can show only the AI-off status.

## Proposed design

Add an `employer_task_example` metadata/index table. Publishing a task version
records an approved immutable example scoped to the owning company. Retrieval
loads only approved examples for that company, scores specialization/grade and
required/preferred skill overlap deterministically, and returns a small bounded
set. Full task content is passed only through the replaceable local-AI context;
the HTTP response exposes employer-owned metadata and count for explainability.

## Files/modules

- `backend/alembic/versions/20261007_0019_approved_task_memory.py`
- `backend/app/local_ai.py`
- `backend/app/employer_tasks.py`
- `backend/app/main.py`
- `backend/tests/test_local_ai.py`
- `backend/tests/test_employer_tasks.py`
- `backend/tests/test_migrations.py`
- `frontend/src/components/employer-task-authoring.tsx`
- `docs/LOCAL_AI.md`, `docs/EMPLOYER_ASSESSMENTS.md`, `docs/DATA_MODEL.md`,
  `docs/API_GUIDELINES.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`

## Data/API changes

- Create `employer_task_example` with unique source version, company scope,
  current need taxonomy/skill metadata, approved status, and audit timestamps.
- Extend `EmployerTaskDraftContext` with retrieved approved examples.
- Extend `POST /api/v1/employer/tasks/draft-suggestion` with bounded metadata
  (`approved_example_count`, `approved_examples`) while preserving the
  deterministic disabled response.

## Security/privacy implications

Retrieval is scoped by the authenticated employer's company before scoring.
No candidate, chat, token, or external data is included. Draft and unpublished
task content never enters the approved index. The UI/API does not expose other
employers' examples.

## Test plan

- Migration creates the memory table and foreign keys.
- Publishing indexes a version exactly once; later versions are separate
  immutable examples.
- Retrieval prefers matching specialization/grade/skills, is bounded, and
  cannot cross employer ownership.
- Disabled adapter remains deterministic and receives the retrieved context
  without emitting a draft.
- Existing authoring and AI-off flows continue to pass.

## Demo/evidence

Employer publishes an approved task, changes the hiring need to a related
specialization/grade/skill set, and opens the task authoring panel. The panel
shows the number and titles of approved examples available to the optional
copilot while manual authoring remains enabled.

## Progress / decisions / surprises

- Plan created before implementation.
- Implemented migration `20261007_0019`, publication indexing, bounded
  deterministic retrieval, adapter-context propagation, employer-only response
  metadata and authoring-panel display.
- Focused slice tests pass (10); full backend suite passes (99); Ruff and
  frontend TypeScript checks pass.
- Generation, feedback capture, background jobs, and runtime model integration
  remain separate M10 backlog units.
