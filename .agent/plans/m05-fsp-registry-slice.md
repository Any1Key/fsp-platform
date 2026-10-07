# M05 FSP registry slice

## Purpose / user value

Let a candidate demonstrate an FSP ID link against a replaceable synthetic registry while keeping the normal no-FSP-history state explicit and valid. This creates the evidence boundary needed by later employer matching without inventing a production FSP API.

## Requirement IDs

- FSP-001 — support the correct no-FSP-history case.
- FSP-002 — provide a synthetic replaceable adapter.
- CAND-011 — link a candidate profile to an FSP ID.

The bounded ranking contribution and employer display remain separate M05/M06 work and are not included in this slice.

## Current behavior

There is no FSP link storage, registry port, candidate FSP API, or candidate UI. The repository has only the documented integration concept.

## Proposed design

- Define `FspRegistryPort` with participant verification and achievement retrieval.
- Implement `SyntheticFspRegistryAdapter` with deterministic demo IDs, including a valid ID with no achievements.
- Persist a candidate-scoped link and a replaceable snapshot of non-sensitive achievements.
- Require processing consent for linking; keep GET candidate-scoped and return an explicit `not_linked`/`no_history` state.
- Add candidate UI for link, unlink, loading, error, linked-achievement, and no-history states.

## Files/modules

- `backend/app/fsp.py` — port, adapter, service and response mapping.
- `backend/alembic/versions/20261007_0009_fsp_registry.py` — link/achievement schema.
- `backend/app/main.py` — request/response models and candidate endpoints.
- `backend/tests/test_fsp.py` — adapter, API, consent, scope and no-history tests.
- `frontend/src/components/candidate-fsp.tsx`, `auth-status.tsx`, `globals.css` — UI.
- `docs/FSP_INTEGRATION.md`, `docs/DATA_MODEL.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` — evidence.

## Data/API changes

- `POST /api/v1/candidate/fsp-link` with `{ "fsp_id": "FSP-DEMO-001" }`.
- `DELETE /api/v1/candidate/fsp-link` to remove the candidate-owned link/snapshot.
- `GET /api/v1/candidate/fsp` returns link state and safe achievement fields.

## Security/privacy implications

Only the authenticated candidate can link/read/remove their own FSP data. Processing consent is required before creating the link. Protected profile data, contacts, tokens, and external secrets are not stored or returned. FSP data is informational and not a ranking gate.

## Test plan

- Synthetic adapter returns deterministic participant/achievement data and a valid no-history participant.
- Link requires processing consent and rejects unknown IDs.
- Candidate can link/read/unlink their own record; another candidate and employer cannot access it.
- No-link and no-achievement responses remain explicit and empty rather than errors.
- Full backend suite plus frontend production build.

## Demo/evidence

Use `FSP-DEMO-001` for linked synthetic achievements and `FSP-DEMO-NONE` for the no-history state. Evidence is recorded in the requirements matrix after tests pass.

## Progress / decisions / surprises

- 2026-10-07: selected as the first coherent work unit in the highest-priority unfinished M05 milestone.
- 2026-10-07: ranking contribution intentionally deferred to the matching slice; this work stores/display evidence but does not score candidates.
- 2026-10-07: implemented migration, registry port/adapter, candidate API/UI, consent/audit boundary, and integration coverage. Backend suite: 59 passed; frontend production build passed.
