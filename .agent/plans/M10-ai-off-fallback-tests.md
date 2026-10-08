# M10 — AI-off employer task fallback

## Purpose / user value

Prove that employer task authoring remains a complete manual workflow when the
optional CPU-local AI is disabled. The suggestion endpoint must return a
deterministic disabled result without creating a background job, and the
employer must still be able to save and publish an employer-owned task.

## Requirement IDs

- `EMP-014` — optional local CPU AI may propose employer task/rubric drafts.
- `NFR-012` — optional local AI is isolated and has a deterministic fallback.

## Current behavior

The disabled adapter and immediate API response were already implemented, but
the focused tests did not prove the complete fallback path through manual task
creation and publication or guard against accidental queueing in disabled mode.

## Proposed design

Extend the local-AI integration coverage so the disabled route is tested with a
real employer hiring pipeline and task authoring flow. Patch the queue entry
point to fail the test if disabled mode attempts to enqueue work. Document that
manual authoring and explicit publication are the supported fallback, with no
AI-generated task or job created.

## Files/modules

- `backend/tests/test_local_ai.py`
- `docs/LOCAL_AI.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `.agent/BACKLOG.md`

## Data/API changes

None. This slice verifies the existing disabled API contract:
`POST /api/v1/employer/tasks/draft-suggestion` returns `200` with
`status=disabled`, `draft=null`, and no `job_id`.

## Security/privacy implications

Disabled mode does not enqueue or retain an AI context. The manual task remains
company-scoped and follows the existing employer ownership and publication
checks.

## Test plan

- Verify disabled suggestion is deterministic and contains no draft/job.
- Verify queue submission is not attempted while disabled.
- Verify the same employer can create and explicitly publish a task afterward.
- Run focused local-AI tests, the full backend suite, Ruff, and frontend
  typecheck.

## Demo/evidence

In the employer task authoring panel with `LOCAL_AI_ENABLED` unset/false, the
panel shows `LOCAL AI OFF`; the employer can complete the manual task editor,
save a draft, and publish it independently of AI.

## Progress / decisions / surprises

- Plan created before implementation.
- Existing requirement rows are already `VERIFIED` in the supplied repository;
  this work does not change or re-mark those statuses. The backlog item is
  updated only to `IMPLEMENTED`.
- Implemented the no-queue guard and manual create/publish integration test,
  documented the fallback contract, and updated requirement evidence.
