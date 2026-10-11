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

## Production deployment

Set the deployment-specific public values in `.env` before starting. The
repository does not contain a site-specific domain:

```dotenv
APP_BASE_URL=https://your-domain.example
NEXT_PUBLIC_API_URL=https://your-domain.example
NEXT_PUBLIC_KEYCLOAK_URL=https://your-domain.example/auth
KEYCLOAK_PUBLIC_URL=https://your-domain.example/auth
KEYCLOAK_ISSUER=https://your-domain.example/auth/realms/fsp
CORS_ALLOWED_ORIGINS=https://your-domain.example
PROXY_NETWORK=your_reverse_proxy_network
```

The current VPS is one deployment instance; its domain is not required by the
repository.
Production startup uses both Compose files:

```bash
docker compose -f docker-compose.yml -f compose.prod.yml config
docker compose -f docker-compose.yml -f compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f compose.prod.yml ps
```

The production override keeps frontend, backend and Keycloak off the public
host ports. The external reverse proxy terminates TLS and routes `/` to the
frontend, `/api/*` to the backend and `/auth/*` to Keycloak.

The browser-visible OIDC base is `KEYCLOAK_PUBLIC_URL`; the backend uses the
same public issuer from `KEYCLOAK_ISSUER` for JWT validation and the internal
Docker JWKS URL for key retrieval. The Keycloak client is `fsp-web`, with
HTTPS redirect and web-origin settings matching `APP_BASE_URL`.

After changing any `NEXT_PUBLIC_*` value, rebuild the frontend image. A
restart alone does not change values already embedded into the Next.js bundle.

## Email verification demo

Select `Создать аккаунт` on the landing page. Keycloak hosts the registration
form and accepts only the configured `.ru` email domain. After submitting the
form, open Mailpit, open the Keycloak verification message, and follow its
link. Keycloak owns the password and verification token; the application only
accepts a verified email claim in an access token.

The repeatable Compose-profile evidence is:

```bash
docker compose --profile test run --rm qa npm test
```

For the production OIDC browser path, run the focused check with the
production URL variables and rebuild the QA image so the current test source is
used:

```bash
docker compose -f docker-compose.yml -f compose.prod.yml --profile test run --build --rm \
  -e KEYCLOAK_E2E_BASE_URL=http://keycloak:8080/auth \
  -e KEYCLOAK_PUBLIC_E2E_BASE_URL=https://your-domain.example/auth \
  -e FRONTEND_E2E_REDIRECT_URI=https://your-domain.example/ \
  qa npx playwright test tests/auth-registration.spec.ts --project=desktop-1920 --retries=0
```

It uses a synthetic unique `.ru` address, asserts the newly-created account is
initially unverified, reads the link from Mailpit's local API, follows it, and
asserts Keycloak's user state becomes verified. Admin credentials are supplied
from `.env` to the disposable QA container and are not stored in the repo.

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
docker compose --profile test config -q
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

Fresh destructive demo reset (removes only this Compose project's named volumes;
the confirmation guard is intentional):
```bash
DEMO_RESET_CONFIRM=YES ./scripts/demo-reset.sh
```

The reset applies the empty-database migrations and runs `python -m app.seed_demo`,
which verifies the deterministic taxonomy baseline. It does not create Keycloak
users, passwords, verification messages, chat, or candidate documents. Create
synthetic `.ru` accounts through normal Keycloak registration during the jury demo.

For a real production deployment beyond the jury demo, add production secrets,
real SMTP, backups, monitoring, log retention/access controls and a reviewed
identity configuration. The current public demo uses the reverse proxy and TLS
configuration outside this repository; Mailpit remains a demo SMTP sink.
