# Deployment

```bash
cp .env.example .env
# replace CHANGE_ME values
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

Default:
- frontend `http://HOST:3000`
- Swagger `http://HOST:8000/docs`
- Keycloak `http://HOST:8081`
- Mailpit `http://HOST:8025`

The backend container applies the committed Alembic migrations before starting
the API. To apply or inspect the schema manually from the repository:

```bash
cd backend
DATABASE_URL='postgresql+psycopg://fsp:REDACTED@app-db:5432/fsp' alembic upgrade head
alembic current
```

The API creates one SQLAlchemy engine and request-scoped session factory from
`DATABASE_URL`. `/health` is a dependency-free liveness probe; use
`/health/ready` for readiness because it executes `SELECT 1` against the
configured application database. Database failures return HTTP 503 without
exposing connection details.

For an isolated migration smoke test without PostgreSQL:

```bash
cd backend
DATABASE_URL='sqlite:///./local-foundation.sqlite' alembic upgrade head
```

The assessment service is still process-local until a separate assessment
persistence work unit wires repositories to this schema; the database session
boundary and migration establish the shared persistence foundation but do not
claim that feature is complete.

## Continuous integration

`.github/workflows/ci.yml` is the repository CI baseline. It runs backend
tests/Ruff, frontend typecheck/build, the locked QA toolchain, the QA/Playwright
version contract, and `docker compose --profile test config -q`. Backend
dependencies come from `backend/requirements.lock`; frontend and QA use
`npm ci` with their committed lockfiles. Pull-request and push jobs use
read-only repository permissions and cancel superseded runs.

The local contract check is repeatable without starting services:

```bash
bash agent/test-ci-contract.sh
```

CI configuration and contract checks establish the automated gate only. The
external supervisor remains responsible for running the full Compose startup,
health checks and Playwright E2E flow before assigning `VERIFIED` status.

Stop:
```bash
docker compose down
```

Logs:
```bash
docker compose logs -f --tail=200
```

Fresh destructive demo reset:
```bash
./scripts/demo-reset.sh
```

Do not expose bootstrap directly to the public Internet as production. Add TLS/reverse proxy, production
secrets, real SMTP, backups, monitoring and hardened identity before public deployment.
