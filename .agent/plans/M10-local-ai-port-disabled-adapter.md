# M10 — LocalAiPort and disabled adapter

## Purpose / user value

Give employer task authoring a replaceable local-AI boundary while keeping manual
authoring fully usable when AI is disabled. The disabled response must be explicit
so the UI does not imply that a draft was generated.

## Requirement IDs

- `EMP-014` — local CPU AI can propose employer task/rubric drafts from a need and approved history (this slice establishes the adapter boundary and AI-off response; the enabled proposal remains future work).
- `NFR-012` — optional local AI is isolated, asynchronous and has deterministic fallback (this slice implements the async port and deterministic disabled fallback; persistence/jobs remain future work).

## Current behavior

Employer task authoring is manual only. `docs/LOCAL_AI.md` describes a future
`LocalAiPort`, but no backend port or API-visible disabled state exists.

## Proposed design

- Add `backend/app/local_ai.py` with typed, sanitized draft context, an async
  `LocalAiPort` protocol, a result object, and `DisabledLocalAiAdapter`.
- Build the current adapter from settings; default and only available adapter in
  this slice is disabled.
- Add an employer-scoped task draft-assistance endpoint that loads the current
  hiring need, calls the port, and returns a deterministic `disabled` result.
- Display the result in the existing employer task authoring UI while retaining
  the manual editor as the fallback.

## Files/modules

- `backend/app/local_ai.py`
- `backend/app/main.py`
- `backend/tests/test_local_ai.py`
- `frontend/src/components/employer-task-authoring.tsx`
- `frontend/src/app/globals.css`
- `docs/LOCAL_AI.md`
- `docs/EMPLOYER_ASSESSMENTS.md`
- `.agent/BACKLOG.md`

## Data/API changes

Add `POST /api/v1/employer/tasks/draft-suggestion` with no request body. It is
employer-scoped, requires an existing hiring need, and returns adapter status,
source, reason, and nullable draft. The endpoint does not persist a task or
send candidate data anywhere.

## Security/privacy implications

Only sanitized hiring-need metadata is passed to the port. No candidate profile,
resume, chat, contact, token, or real personal data enters the adapter. The
endpoint uses the existing employer role dependency and hiring-need ownership.

## Test plan

- Unit-test the disabled adapter's deterministic async result and context safety.
- Integration-test employer success, missing-need, candidate denial, and manual
  task authoring fallback status.
- Run backend tests, Ruff, and frontend typecheck/build.

## Demo/evidence

Employer task authoring shows “AI disabled — author manually” after the scoped
probe. The API response and tests provide machine-readable evidence for the
disabled adapter boundary without claiming enabled generation.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished M10 backlog unit.
- 2026-10-07: no requirement status is promoted until the enabled-generation and
  job/timeout portions provide the full `EMP-014`/`NFR-012` evidence.
- 2026-10-07: implemented; full backend suite (96 tests), focused AI/task tests,
  Ruff, frontend typecheck, production build, and diff hygiene pass.
