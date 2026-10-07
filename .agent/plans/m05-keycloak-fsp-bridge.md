# M05 Keycloak/FSP identity bridge

## Purpose / user value

Close the remaining M05 integration-concept work with a demonstrable boundary
between the authenticated Keycloak account and the separately linked FSP
participant. A candidate can see which identity connection is active without
exposing the raw Keycloak subject or presenting the synthetic adapter as a
production FSP API.

## Requirement IDs

- FSP-001 — preserve the no-history/unlinked state.
- FSP-002 — keep the FSP registry behind the replaceable adapter port.
- FSP-003 — keep the candidate-owned FSP evidence/link behavior unchanged.
- FSP-004 — demonstrate the Keycloak/FSP identity bridge contract (new matrix
  evidence for the remaining M05 backlog item).

## Current behavior

Candidate FSP endpoints link a synthetic participant and return the evidence
snapshot. The UI shows provider and participant information, but there is no
explicit, tested representation of how the authenticated Keycloak identity is
related to that separate FSP identity.

## Proposed design

Add `GET /api/v1/candidate/fsp/integration`. It returns a safe, candidate-
scoped bridge record containing the configured Keycloak issuer, a truncated
SHA-256 fingerprint of the validated subject, the FSP provider/participant
state, and an explicit-link mode. It does not return the raw subject, tokens,
or external credentials. The response documents that `FspRegistryPort` is the
future replacement seam for a real FSP adapter.

Render this record in the existing candidate FSP panel so the demo visibly
shows Keycloak authentication and FSP evidence as separate identities.

## Files/modules

- `backend/app/fsp.py` — bridge response service and subject fingerprint.
- `backend/app/main.py` — typed response model and candidate route.
- `backend/tests/test_fsp.py` — API, scoping, and non-disclosure coverage.
- `frontend/src/components/candidate-fsp.tsx` — bridge status UI.
- `frontend/src/app/globals.css` — responsive bridge styling.
- `docs/FSP_INTEGRATION.md` and `docs/ARCHITECTURE.md` — integration contract.
- `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` — IMPLEMENTED evidence.

## Data/API changes

No migration. The endpoint reads the existing candidate-owned `fsp_link` and
uses the already validated Keycloak `Principal`.

## Security/privacy implications

The raw Keycloak subject is never serialized or logged. The fingerprint is
one-way and truncated for display/evidence purposes; it is not used for
matching. The route is candidate-role-only and loads the caller's own link.
The FSP link remains explicit and consent-gated; this slice does not infer
identity from email or claim a real FSP federation contract.

## Test plan

- unlinked candidate receives a safe bridge record and no raw subject;
- linked candidate receives the same Keycloak fingerprint and participant;
- a different candidate cannot see the first candidate's participant;
- employer access is denied;
- frontend typecheck/build succeeds.

## Demo/evidence

The candidate FSP panel displays `KEYCLOAK IDENTITY` and `FSP REGISTRY LINK`
states together, with the adapter contract labelled as an explicit link.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished backlog unit (M05).
- 2026-10-07: deliberately chose a safe application-link concept because the
  owner docs prohibit inventing a production FSP schema.
- 2026-10-07: implemented `GET /api/v1/candidate/fsp/integration`, the
  candidate-panel bridge rendering, and non-disclosure/cross-candidate tests.
- 2026-10-07: verified with 65 backend tests, Ruff, frontend typecheck, and
  frontend production build. External verification remains out of scope.
