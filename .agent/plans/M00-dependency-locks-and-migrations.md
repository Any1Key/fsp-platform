# M00 — Reproducible dependencies and initial database migration

## Purpose / user value

Make the bootstrap reproducible from a clean checkout and give the application
an auditable, repeatable empty-database schema foundation before later feature
work adds persistence.

## Requirement IDs

- NFR-004 — reproducible Docker Compose startup.
- NFR-011 — CPU-only core dependency/runtime profile.
- DOC-007 — libraries/components with versions.
- DOC-008 — step-by-step build/deploy/local run.
- AST-003 / AST-013 — preserve assessment category/scoring provenance in the
  persistence boundary without claiming the assessment UI or employer wiring is
  complete.

## Current behavior

Python and Node dependencies are declared as ranges without lockfiles. The
backend image uses `pip install -e ".[dev]"` and the Node images use `npm
install`. Alembic is listed but has no configuration, environment, migration,
or automated empty-database evidence. Assessment state is process-local.

## Proposed design

- Generate `package-lock.json` files for the frontend and Playwright QA image.
- Add a committed Python `requirements.lock` with exact direct and transitive
  versions, used by the backend image while retaining editable source imports.
- Add Alembic configuration and one portable initial migration. The migration
  contains only foundation identity/profile and assessment provenance tables;
  feature behavior remains in its later milestones.
- Keep migration execution explicit (`alembic upgrade head`) and test it against
  a fresh SQLite database using Alembic’s public command API. Production uses
  the configured PostgreSQL `DATABASE_URL`.

## Files/modules

- `backend/alembic.ini`, `backend/alembic/env.py`,
  `backend/alembic/script.py.mako`
- `backend/alembic/versions/20261006_0001_initial_foundation.py`
- `backend/requirements.lock`, `backend/Dockerfile`
- `backend/.dockerignore`, `frontend/.dockerignore`, `qa/.dockerignore`
- `frontend/package-lock.json`, `qa/package-lock.json`
- `backend/tests/test_migrations.py`
- `docs/COMPONENTS.md`, `docs/DEPLOYMENT.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

No HTTP API changes. The initial schema adds:

- identity and candidate profile records;
- specialization/grade taxonomy references;
- assessment blueprint, question family/template/variant provenance;
- assessment attempts/items/answers/results with uniqueness and integrity
  constraints.

## Security/privacy implications

The migration stores opaque identity references and assessment provenance, not
passwords, tokens, answer keys, raw contacts, DOB, minor documents, or chat
content. Candidate private fields are separated from the public profile record.
The migration is not a claim of complete authorization or retention controls;
those remain later work units.

## Test plan

- run the migration against a fresh temporary SQLite database;
- assert the expected tables, primary/foreign keys, and uniqueness constraints;
- downgrade to base and assert the schema is empty;
- run the existing backend test suite and frontend/QA lockfile validation;
- build the backend using the locked requirements path where the environment
  supports Docker.

## Demo/evidence

`backend/tests/test_migrations.py` is the repeatable empty-database evidence.
`docs/COMPONENTS.md` records locked direct versions and `docs/DEPLOYMENT.md`
documents the migration command. External supervisor owns verification and this
plan must not mark requirements VERIFIED.

## Progress / decisions / surprises

- 2026-10-06: selected as the first unfinished M00 work unit because all
  later persistent slices depend on reproducible installs and a schema runner.
- 2026-10-06: chose a portable SQLAlchemy/Alembic migration with string UUID
  storage so migration tests can run on SQLite while deployment remains
  PostgreSQL-first.
- 2026-10-06: generated frontend/QA npm locks and Python uv/requirements locks;
  updated images to consume them with `npm ci`/`pip install --requirement`.
- 2026-10-06: added startup migration execution and fresh-database upgrade /
  downgrade evidence. Backend tests: 6 passed; frontend typecheck, Ruff,
  Compose config, lock checks, and backend image build passed. QA image tag
  `v1.55.1-noble` resolved, but its redundant fresh ~800 MB pull was stopped
  after the prior full QA image build had already passed with the same locked
  install path.
