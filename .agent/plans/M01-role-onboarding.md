# M01 — Role onboarding

## Purpose / user value

Let a verified `.ru` Keycloak account choose exactly one FSP platform role when
Keycloak has not assigned an application role yet. The choice provisions the
minimum local identity and immediately unlocks the correct candidate or
employer workspace.

## Requirement IDs

- AUTH-003 — working Keycloak/OIDC identity and role boundary.
- AUTH-004 — verified account can complete one-time candidate/employer role onboarding.
- NFR-006 — server-side RBAC and secure token handling.
- NFR-007 — Keycloak/OIDC compatibility.

The backlog item is the role-onboarding slice of M01. Consent/privacy is out of
scope and remains TODO.

## Current behavior

The API rejects tokens without a supported `candidate` or `employer` role, even
when the account is otherwise a valid verified `.ru` Keycloak user. The browser
has no role-selection screen, so a newly registered account cannot enter either
product journey.

## Proposed design

- Accept a verified token with no application role as an explicit `pending`
  principal; tokens with ambiguous or unknown roles remain rejected.
- Return a pending session from `/api/v1/auth/me` without creating a partially
  authorized identity.
- Add an authenticated `POST /api/v1/auth/onboarding/role` endpoint accepting
  only `candidate` or `employer`. Provision the local identity exactly once;
  replays of the same choice are idempotent and role changes are rejected.
- Resolve the persisted local role for subsequent no-role tokens. Explicit
  Keycloak roles must agree with the bound local role, preserving a server-side
  role boundary without storing tokens or passwords.
- Add a browser role chooser and refresh the session after successful binding.

## Files/modules

- `backend/app/auth.py`, `backend/app/main.py`, `backend/app/errors.py`.
- `backend/tests/test_auth.py`.
- `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`.
- `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/DATA_MODEL.md`,
  `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md`.

## Data/API changes

- No schema change: `user_identity` is created only after role selection.
- `GET /api/v1/auth/me` now returns `role: "pending"`, `identity_id: null` and
  `onboarding_required: true` for a verified account without a bound role.
- `POST /api/v1/auth/onboarding/role` binds one public role and returns the
  normal authenticated session.

## Security/privacy implications

Role choice is never trusted from the browser for authorization. The API
validates the verified JWT first, allows only the two public roles, persists the
binding against the Keycloak subject, and checks it on every protected request.
Unknown/ambiguous roles, role changes, unverified email and non-`.ru` email
remain rejected. Consent and profile data are not collected in this slice.

## Test plan

- Pending no-role token receives a pending session and cannot access either
  role context.
- Candidate and employer selections provision identities and unlock only their
  own context; repeat selection is safe and switching is rejected.
- A no-role token uses the persisted role after onboarding, while an explicit
  conflicting Keycloak role is rejected.
- Existing signed-token, `.ru`, CORS, and identity-refresh tests remain green.
- Run backend pytest/Ruff and frontend typecheck/build.

## Demo/evidence

The landing page displays the role chooser after Keycloak login for a verified
account without an application role. Selecting a role calls the authenticated
API, then shows the candidate or employer workspace state. API tests provide
deterministic signed-token evidence without requiring external credentials.

## Progress / decisions / surprises

- 2026-10-06: Selected as the first unfinished work unit in M01.
- 2026-10-06: Chose a local one-time role binding because the public Keycloak
  client has no admin credential and new self-registered users do not receive a
  platform role automatically. Explicit Keycloak roles remain authoritative
  when present and must agree with the local binding.
- 2026-10-06: Implemented pending sessions, role binding/replay protection,
  local-role resolution, browser role chooser, stable error codes and docs.
  Backend: 20 tests passed; Ruff passed with a temporary writable cache;
  frontend typecheck and production build passed.
