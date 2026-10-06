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

Frontend: Authorization Code + PKCE.
Backend: JWT issuer/audience/signature/role validation.
Application stores no user passwords.
Registration permits only email domains ending in `.ru`.

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
