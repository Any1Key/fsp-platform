# Architecture

## Decision

Use a **modular monolith** for MVP. It is simpler and more reproducible than microservices while preserving clear boundaries. Core operation requires no GPU.

```text
Browser
  |
Next.js frontend
  |
FastAPI REST/WebSocket API -----> Keycloak / OIDC
  |
  +---- PostgreSQL
  +---- FSP Registry Adapter (synthetic now / real later)
  +---- Resume Parser Adapter
  +---- Optional Local AI Adapter/worker (CPU, async, replaceable)
```

Supporting:
- Mailpit for local email verification/demo;
- Playwright QA runner;
- load-test runner;
- Telegram supervisor reporter outside application runtime.

## Backend target modules

- `identity`
- `candidates`
- `companies`
- `taxonomy`
- `assessments`
- `assessment_integrity`
- `evidence`
- `fsp`
- `matching`
- `invitations`
- `matches`
- `chat`
- `vacancies`
- `applications`
- `hiring_pipeline`
- `employer_tasks`
- `documents`
- `local_ai`
- `audit`

Rules:
- routers call application services;
- services own use cases;
- domain rules do not depend on FastAPI;
- repositories isolate persistence;
- external systems use ports/adapters;
- authorization is enforced server-side.

## Frontend

Feature-oriented:

```text
src/
  app/
  components/ui/
  features/
    auth/
    candidate/
    employer/
    assessment/
    matching/
    invitations/
    chat/
    hiring-pipeline/
    vacancies/
  lib/
  styles/
```

## API

REST under `/api/v1`; chat may additionally use `/ws/...`.
FastAPI-generated OpenAPI is mandatory for HTTP endpoints. Every endpoint needs typed request/response and documented validation/error behavior.

## Auth

Keycloak realm `fsp`.
Roles:
- `candidate`
- `employer`
- future `admin/reviewer`

Frontend: Authorization Code + PKCE through `frontend/src/components/auth-status.tsx` and
the `fsp-web` public client.
Backend: JWT issuer/audience/signature/role validation.
Application stores no user passwords.
Registration permits only email domains ending in `.ru`.

Registration and email verification remain Keycloak-owned flows. The landing
page exposes both login and registration actions; Keycloak sends the
verification message to the Compose Mailpit adapter. `qa/tests/auth-registration.spec.ts`
proves the unverified-to-verified transition through the local Mailpit and
Keycloak admin APIs using synthetic test data only.

The identity boundary is implemented by `backend/app/auth.py` and
`backend/app/main.py`. The API accepts only RS256 access tokens from the
configured Keycloak issuer and `fsp-web` audience, resolves signing keys from
the configured JWKS endpoint, requires `sub`/`exp`/`iat` and a verified email,
and accepts exactly one supported role from realm or client role claims. The
validated subject, normalized email, role and verification state are upserted
into `user_identity`; no token or password is stored. Keycloak's imported user
profile applies the same `.ru` pattern during self-registration, while
`POST /api/v1/auth/registration/check` gives the frontend a deterministic
preflight. The API allows only the documented localhost/127.0.0.1 frontend
origins for browser requests, with explicit Bearer-header preflight support;
credentials are not enabled.

## Match/chat authorization

Conversation creation requires a valid match domain event. All history/message operations verify conversation membership server-side.

## Local AI

Optional service behind `LocalAiPort`. Core works with adapter disabled. Inference is asynchronous, one worker by default, with timeout/rate limit and deterministic fallback. Prefer retrieval from approved employer tasks over production-host fine-tuning.

## Performance target

Target host: about 8 CPU / 32–64 GB RAM, no GPU. Optimize the core profile first. Avoid N+1 ranking queries and add indexes for category/grade, evidence, assessment result, matching snapshots, invitations and chat membership/time.

## Observability

Structured logs: request_id, actor subject, action, status, duration, safe error metadata.
Never log secrets, raw minor documents, full chat messages or unnecessary PII.

Load/performance evidence is part of release validation.
