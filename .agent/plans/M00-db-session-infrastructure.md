# M00 — Database and session infrastructure

## Purpose / user value

Provide a single, testable database boundary for the FastAPI application so
later candidate, assessment, matching, invitation and chat modules can use
PostgreSQL without creating their own engines or leaking connections.

## Requirement IDs

- M00 — DB/session infrastructure.
- NFR-003 — clear frontend/backend/storage separation.
- NFR-004 — preserve the existing migration-backed Compose startup contract;
  this work adds the runtime session boundary without changing its status.

## Current behavior

Alembic can create the foundation schema, but the application has no settings
object, SQLAlchemy engine/session factory, request-scoped session dependency,
transaction helper or database readiness probe. The only health endpoint is a
process liveness check.

## Proposed design

- Load `DATABASE_URL` and small pool settings through `pydantic-settings`, with
  an in-memory SQLite default for tests and local import safety.
- Build one engine and `sessionmaker` at the application boundary, with
  PostgreSQL pre-ping/pool settings and SQLite thread-safe test behavior.
- Expose a FastAPI dependency that rolls back failed requests and always closes
  its session, plus an explicit `session_scope` helper for service-level
  transactions.
- Add `/health/ready` to verify the database connection while keeping
  `/health` a dependency-free liveness endpoint.

## Files/modules

- `backend/app/config.py` — application/database settings.
- `backend/app/db.py` — engine, session factory, dependency and transaction
  helper.
- `backend/app/main.py` — database readiness endpoint.
- `backend/tests/test_database.py` — transaction and readiness evidence.
- `docker-compose.yml` — use database readiness for backend health checks.
- `docs/DEPLOYMENT.md` — runtime configuration and probe documentation.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — implementation status.

## Data/API changes

- Adds `GET /health/ready`, returning `{"status":"ok","database":"ok"}`
  when the configured database can execute a probe; failures return HTTP 503.
- No schema or domain data changes. Assessment storage remains process-local
  until its own coherent persistence work unit.

## Security/privacy implications

Database credentials remain configuration-only and are not returned by the
API. Sessions are request-scoped, failed requests are rolled back, and the
readiness response contains no connection details or PII.

## Test plan

- Create a temporary SQLite database through the same engine factory.
- Verify `session_scope` commits successful work and rolls back an exception.
- Override the application dependency and verify `/health/ready` executes a
  real database probe while `/health` remains available independently.
- Run the complete backend test suite and Ruff.

## Demo/evidence

`backend/tests/test_database.py` is repeatable evidence for the session
boundary and readiness behavior. External supervisor owns runtime Compose and
verification status; this plan does not mark anything VERIFIED.

## Progress / decisions / surprises

- 2026-10-06: selected as the first unfinished M00 work unit because all
  persistent domain slices need a shared runtime database boundary.
- 2026-10-06: retained process-local assessment storage to keep this unit
  coherent and avoid claiming partial domain persistence.
- 2026-10-06: implemented settings-backed SQLAlchemy engine/session
  infrastructure, transaction rollback behavior and `/health/ready`.
- 2026-10-06: backend suite passes 8 tests; Ruff and compileall pass. Runtime
  Compose verification remains owned by the external supervisor.
