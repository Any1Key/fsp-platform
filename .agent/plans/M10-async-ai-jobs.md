# M10 — Asynchronous local-AI task drafting

## Scope

Implement exactly the remaining M10 work unit for asynchronous jobs, rate
limiting, and timeout handling for optional employer task drafting. The AI-off
path remains synchronous and deterministic; enabled local-AI generation is
queued and never awaited by the request handler.

## Requirement IDs

- `EMP-014` — optional CPU-local AI proposes employer task/rubric drafts and
  remains human-reviewed.
- `NFR-012` — optional local AI is isolated, asynchronous, and has a
  deterministic fallback.

## Evidence and existing boundaries

- `backend/app/local_ai.py` already owns the replaceable async adapter and
  strict draft validation.
- `POST /api/v1/employer/tasks/draft-suggestion` was the synchronous boundary
  to replace; it now returns a scoped queued job when AI is enabled.
- `frontend/src/components/employer-task-authoring.tsx` now polls queued jobs
  while preserving the immediate AI-off result.
- `docs/LOCAL_AI.md` defines the CPU-only adapter, queue, and fallback policy.

## Design

1. Add a migration for company-scoped local-AI draft jobs containing a
   sanitized need/example snapshot, status, result, timestamps, and attempt
   count.
2. Add a bounded in-process worker backed by the job table. It uses one worker
   for the optional CPU-local runtime, claims queued rows, applies the existing
   adapter timeout, validates results again, and stores only safe result data.
3. Enforce a per-company active-job limit and rolling request limit before
   enqueueing. Return a stable `429` error with `Retry-After` when exceeded.
4. Return `202` plus a scoped polling ID for enabled generation and add a GET
   polling endpoint. Keep disabled mode as an immediate `disabled` result.
5. Update the employer authoring UI to poll queued jobs and preserve manual
   authoring/fallback behavior.
6. Add migration, queue, timeout, rate-limit, authorization, AI-off, and UI
   contract tests; update local-AI docs, env/config examples, backlog, and
   requirement evidence to `IMPLEMENTED` only.

## Verification

- Focused backend tests for local-AI and migrations.
- Full backend test suite and frontend type/build checks where available.
- No requirement or backlog item is marked `VERIFIED`; readiness remains under
  external supervisor control.

## Result

Implemented in the configured agent branch. Focused verification passed 15
tests; the full backend suite passed 107 tests; Ruff, frontend typecheck, and
the production frontend build passed. `EMP-014` and `NFR-012` remain
`IMPLEMENTED` only.
