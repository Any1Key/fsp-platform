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
