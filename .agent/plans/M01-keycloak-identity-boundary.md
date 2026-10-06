# M01 — Keycloak identity boundary

## Purpose / user value

Make candidate and employer authentication a real server-side boundary: Keycloak
owns passwords and verification, while the API validates signed access tokens,
enforces the `.ru` registration policy, and provisions the minimum local
identity needed by later domain modules.

## Requirement IDs

- AUTH-002 — registration accepts only email domains ending in `.ru`.
- AUTH-003 — working Keycloak/OIDC integration is demonstrated with JWT and role evidence.
- NFR-006 — server-side RBAC and secure token handling for the identity boundary.
- NFR-007 — Keycloak/OIDC compatibility.

AUTH-001 (Mailpit verification), role onboarding, and consent remain separate
M01 work units.

## Current behavior

The realm import and Compose services exist, but the backend does not parse
Bearer tokens, validate Keycloak claims, enforce roles, or create a local
`user_identity` record. The Keycloak realm also has no `.ru` user-profile
validator.

## Proposed design

- Add a small OIDC verifier using PyJWT and Keycloak JWKS discovery/configuration.
- Require `sub`, `exp`, `iat`, issuer, audience, verified email, and exactly one
  supported application role from realm/client role claims.
- Normalize and validate email at the API registration check and authenticated
  identity boundary; reject anything other than a domain ending in `.ru`.
- Upsert only non-secret identity metadata (`sub`, email, role, verification
  status) in `user_identity`.
- Expose `/api/v1/auth/me` plus candidate/employer context endpoints to prove
  server-side role enforcement.
- Configure Keycloak user-profile pattern validation and an audience mapper for
  the public web client.

## Files/modules

- `backend/app/auth.py` — claims, email policy, verifier, identity service.
- `backend/app/config.py` — Keycloak issuer/JWKS/client settings.
- `backend/app/main.py` and `backend/app/errors.py` — auth endpoints/errors.
- `backend/app/main.py` — narrow frontend-origin CORS policy for the browser
  token handoff.
- `backend/tests/test_auth.py` — signed-token and authorization integration tests.
- `frontend/src/components/auth-status.tsx` — browser Authorization Code + PKCE
  login/status/logout control and `/auth/me` session handoff.
- `infrastructure/keycloak/realm-fsp.json`, `docker-compose.yml`, `.env.example`.
- `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/REQUIREMENTS_MATRIX.md`,
  `.agent/BACKLOG.md`.

## Data/API changes

No migration is required: the initial migration already provides
`user_identity`. New API routes:

- `POST /api/v1/auth/registration/check` — public `.ru` policy preflight.
- `GET /api/v1/auth/me` — authenticated local identity session.
- `GET /api/v1/candidate/context` and `GET /api/v1/employer/context` — role
  protected boundary checks for future modules.

## Security/privacy implications

JWTs are accepted only from the configured issuer, signed JWKS key, audience,
and RS256 algorithm. Tokens, passwords, and raw claims are never logged or
persisted. Email and role claims are normalized before persistence; protected
profile data is outside this slice.

## Test plan

- Validate accepted/rejected `.ru` addresses and exact domain-boundary behavior.
- Validate signed token success, expiry/issuer/audience/signature rejection,
  unverified email rejection, missing/ambiguous role rejection, and role
  endpoint isolation.
- Validate first-login identity provisioning and existing-identity refresh.
- Run the full backend test suite and Ruff.

## Demo/evidence

The realm import enables email verification, candidate/employer realm roles,
PKCE, `.ru` profile validation, and an `fsp-web` audience mapper. The tests
provide deterministic JWT/role evidence without requiring live credentials.

## Progress / decisions / surprises

- 2026-10-06: Selected as the first M01 slice because M01 is the highest
  unfinished milestone. Mailpit verification and role onboarding are not
  silently claimed by this work unit.
- 2026-10-06: Implemented the verifier, identity upsert, registration
  preflight, role contexts, Keycloak import constraints, Compose settings,
  browser PKCE handoff and deterministic signed-token tests. Backend suite: 19
  passed; frontend typecheck/build and Ruff clean. Added and tested the
  narrow frontend-origin CORS preflight required by the browser handoff.
