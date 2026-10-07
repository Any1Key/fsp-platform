# M09 — Ordered employer hiring-stage builder

## Purpose / user value

Let an employer turn a hiring need into a transparent, ordered hiring
pipeline. Candidates can see the expected stage format and approximate time
before accepting a salary-bearing invitation, while detailed employer tasks
remain a later M09 unit.

## Requirement IDs

- EMP-011 — employer can configure additional ordered hiring stages.
- M09 — ordered stage builder.

## Current behavior

The platform stores an employer's current hiring need, but has no persisted
pipeline or stage ordering. Invitations expose salary and offer information
only; candidates cannot see whether additional stages are expected.

## Proposed design

- Add a one-to-one `hiring_pipeline` for each hiring need and ordered
  `pipeline_stage` rows with validated stage type, title, required flag and
  estimated minutes.
- Seed a minimal platform-review/final-decision boundary when a pipeline is
  first read, and replace the employer's draft order atomically through a
  single `PUT` endpoint. The boundary stages cannot be removed; employer
  stages may be inserted and reordered.
- Keep stage configuration employer-scoped and role-protected. Snapshot only
  safe stage metadata into an invitation at creation time so a candidate can
  review the expected format before accepting; no contacts, task answers or
  private data are added.
- Add the employer builder UI with keyboard-accessible move/remove controls,
  required/optional and duration fields, plus loading/error/saved states.

## Files/modules

- `backend/app/pipelines.py` — pipeline domain and ownership rules.
- `backend/app/main.py` — request/response models and routes.
- `backend/alembic/versions/20261007_0015_hiring_pipeline.py` — schema.
- `backend/app/invitations.py` and invitation schema/UI — safe stage snapshot.
- `backend/tests/test_pipeline.py` and invitation assertions — E2E evidence.
- `frontend/src/components/employer-hiring-pipeline.tsx` and styles.
- `docs/EMPLOYER_ASSESSMENTS.md`, `docs/API_GUIDELINES.md` — contract.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — `IMPLEMENTED` evidence.

## Data/API changes

- `GET /api/v1/employer/hiring-pipeline` returns the employer-owned ordered
  pipeline, creating the two boundary stages when needed.
- `PUT /api/v1/employer/hiring-pipeline` validates and atomically replaces the
  configured order.
- Invitation responses add `pipeline_stages` containing only stage type,
  title, required flag and estimated minutes.

## Security/privacy implications

Pipeline reads/writes require the employer role and resolve ownership through
the authenticated identity's company and hiring need. Candidate invitation
previews contain no private candidate data, contact details or task content.
The global platform grade is not touched by this configuration unit.

## Test plan

- Migration creates and downgrades pipeline tables.
- Employer can read defaults, reorder/add optional stages, and read the saved
  order; duplicate/missing boundary stages and invalid durations are rejected
  without partial writes.
- Other employers and candidates cannot read or update the pipeline.
- Invitation creation snapshots the configured safe stage preview and the
  candidate sees it before accepting.
- Run the full backend suite, frontend typecheck and production build.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished work unit in M09.
- 2026-10-07: implementation completed; `EMP-011` is marked `IMPLEMENTED`.
  External supervisor owns verification and any `VERIFIED` status.
