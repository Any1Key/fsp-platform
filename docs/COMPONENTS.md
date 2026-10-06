# Components / versions

Application dependencies are declared in the package manifests and resolved
in the committed lockfiles. The Python lock is exported from `backend/uv.lock`
to `backend/requirements.lock` for the Docker build.

| Area | Locked versions/evidence |
|---|---|
| Backend | FastAPI 0.142.2, SQLAlchemy 2.1.3, Alembic 1.20.0, psycopg 3.3.6 — `backend/requirements.lock` |
| Backend tooling | pytest 8.4.2, pytest-asyncio 1.4.0, Ruff 0.16.10 — `backend/requirements.lock` |
| Frontend | Next.js, React, TypeScript, JetBrains Mono and keycloak-js 26.2.0 — `frontend/package-lock.json` |
| QA | Playwright 1.55.1 — `qa/package-lock.json` |
| Runtime services | PostgreSQL 17-alpine, Keycloak 26.8.0, Mailpit 1.27 — `docker-compose.yml` |

The backend image installs only from the Python lock and runs `alembic upgrade
head` before Uvicorn. Node images use `npm ci` against their lockfiles. Core
services remain CPU-only; no GPU or model runtime is a dependency.
