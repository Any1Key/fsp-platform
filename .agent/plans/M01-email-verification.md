# M01 — Email registration and verification

## Purpose / user value

Let a candidate or employer create an account through the working Keycloak
realm and complete email verification using the local Mailpit demo inbox.
Unverified accounts must not be treated as authenticated platform identities.

## Requirement IDs

- AUTH-001 — email registration + verification.
- AUTH-002 — retain the existing `.ru` registration restriction as a boundary
  dependency, without changing its status in this work unit.

## Current behavior

The imported realm has `registrationAllowed` and `verifyEmail` enabled and
Mailpit is present in Compose, but the browser only exposed a generic login
button. There was no automated journey proving that registration sends a
verification email and changes the Keycloak user state after the link is used.

## Proposed design

- Expose separate Login and Create account actions through the existing
  Keycloak JS client.
- Keep registration and password handling in Keycloak; the application never
  stores credentials or verification tokens.
- Add a Compose test-profile configuration for internal Keycloak/Mailpit URLs
  and admin credentials supplied from the existing `.env` values.
- Add a Playwright E2E test that creates a unique `.ru` user, reads the
  verification link from Mailpit's local API, follows it, and checks the
  resulting `emailVerified` state through Keycloak's admin API.

## Files/modules

- `frontend/src/components/auth-status.tsx` — explicit registration action.
- `frontend/src/app/globals.css` — compact auth action layout.
- `infrastructure/keycloak/realm-fsp.json` — QA-network redirect/origin.
- `docker-compose.yml` — QA-only internal auth/mail environment.
- `qa/tests/auth-registration.spec.ts` — Mailpit/Keycloak E2E.
- `qa/package.json` — include the auth test in the standard QA command.
- `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md` — operator
  flow and security evidence.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — mark only AUTH-001
  `IMPLEMENTED`.

## Data/API changes

No application database migration or public API change. Keycloak remains the
system of record for credentials and verification state. The QA test uses
Keycloak admin and Mailpit APIs only inside the test profile.

## Security/privacy implications

The test uses synthetic, unique `.ru` addresses and a generated password. The
admin password is injected from Compose environment variables and is never
committed or printed. Verification links and test mail stay inside the local
Mailpit/Keycloak network. The application continues to require the verified
email claim at its JWT boundary.

## Test plan

- frontend typecheck/build;
- QA Playwright smoke tests;
- Compose-profile auth E2E: registration, unverified intermediate state,
  Mailpit delivery, link consumption, and verified Keycloak state;
- existing backend tests and Ruff.

## Demo/evidence

The deployment guide documents the browser registration path and Mailpit
inbox. The Playwright test is the repeatable evidence path for AUTH-001; the
external supervisor may later promote it from `IMPLEMENTED` to `VERIFIED`.

## Progress / decisions / surprises

- 2026-10-06: Scoped this unit to AUTH-001. Role onboarding and consent remain
  separate M01 work units.
- 2026-10-06: Keycloak 26.8 rejects the legacy top-level `userProfile` realm
  field. Replaced it with the supported declarative user-profile component
  representation and added the Compose-network client redirect/origin needed
  by the QA browser.
- 2026-10-06: Auth E2E passed against live Keycloak 26.8 and Mailpit. QA is
  single-worker to keep the Compose validation profile within the CPU/RAM
  target under constrained hosts.
