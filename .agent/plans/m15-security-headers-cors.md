# M15 security headers and CORS boundary

## Purpose / user value

Harden the browser-to-platform boundary so the frontend can call every scoped
API operation, while cross-origin access remains explicit and browser-facing
responses carry baseline anti-sniffing, framing, referrer, and capability
policies.

## Requirement IDs

- NFR-006 — RBAC, secure tokens, consent/privacy.
- LEGAL-001 — 152-FZ-oriented data minimization, consent, RBAC, and audit
  controls (transport/browser boundary evidence only; this slice does not claim
  legal certification).

## Current behavior

- FastAPI allows configured origins and Bearer preflight headers, but its CORS
  method list omits `DELETE`, which is used by candidate/employer flows.
- API responses have a request ID but no centralized security response headers.
- Next.js has no response-header policy.
- CORS origins are parsed as a comma-separated string without rejecting a
  wildcard or malformed origin.

## Proposed design

- Validate configured CORS origins as explicit HTTP(S) origins and reject `*`.
- Allow the REST methods used by the API, expose only `X-Request-ID`, and keep
  credentials disabled because authentication uses Bearer tokens.
- Add a small security-header middleware that applies to successful and error
  responses. HSTS is emitted only when `APP_ENV=production`.
- Add equivalent static security headers to all Next.js responses. TLS
  termination remains an infrastructure concern; the frontend policy does not
  force HSTS on local HTTP development.

## Files/modules

- `backend/app/config.py` — CORS origin validation and derived policy.
- `backend/app/security.py` — response-header policy and middleware.
- `backend/app/main.py` — install policy and complete CORS contract.
- `frontend/next.config.mjs` — browser security headers.
- `backend/tests/test_security.py` — policy and API integration tests.
- `qa/tests/security-headers.spec.ts` — frontend/backend browser contract.
- `qa/package.json` — include the contract in the QA suite.
- `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/REQUIREMENTS_MATRIX.md`,
  `.agent/BACKLOG.md` — evidence and status.

## Data/API changes

No database or endpoint payload changes. CORS preflight now supports `DELETE`
and responses expose `X-Request-ID`.

## Security/privacy implications

The policy blocks wildcard browser origins, prevents MIME sniffing and framing,
limits referrer leakage and browser capabilities, and preserves bearer-token
authentication without enabling ambient credentials. HSTS is opt-in through
the production environment boundary.

## Test plan

- Unit-test valid/invalid origin configuration and development/production
  header sets.
- Test API headers on success and errors.
- Test allowed `DELETE` preflight and rejection of an unconfigured origin.
- Run the frontend typecheck/build and the QA security-header contract when
  the Compose QA environment is available.

## Demo/evidence

The API and frontend expose the same documented browser boundary. Evidence is
the backend integration test, the Playwright contract, and the security/
architecture documentation links in the requirements matrix.

## Progress / decisions / surprises

- 2026-10-11: selected as the single M15 work unit because it is the first
  unfinished backlog item and closes an end-to-end browser boundary gap.
- HSTS is intentionally production-only so local HTTP Compose development is
  not pinned to HTTPS by the application.
- 2026-10-11: implementation and focused/full backend tests completed; frontend
  typecheck/build and local header smoke passed. QA contract parses into the
  required responsive projects; full Compose QA execution remains supervisor
  verification because the running stack uses prior images.
