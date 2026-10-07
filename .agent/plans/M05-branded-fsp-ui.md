# ExecPlan: M05 branded FSP evidence UI

## Scope

- Requirement IDs: FSP-001, FSP-003.
- Backlog unit: M05 — branded FSP UI.
- Deliver one candidate-facing UI slice only. Employer-side FSP rendering remains M06.

## Evidence and existing boundaries

- `backend/app/fsp.py` and `backend/tests/test_fsp.py` already provide the candidate-owned
  link/no-history API, normalized achievements, and bounded contribution contract.
- `frontend/src/components/candidate-fsp.tsx` is already mounted for authenticated candidates,
  but needs stronger FSP brand treatment and browser-level state evidence.
- Official palette/assets are documented in `docs/BRAND_GUIDE.md` and the responsive/accessibility
  expectations are documented in `docs/DESIGN_SYSTEM.md` and `docs/UI_ACCEPTANCE_CRITERIA.md`.

## Implementation steps

1. Add a branded FSP evidence header, status summary, achievement cards, no-history state, and
   clear synthetic/demo provenance without changing API semantics or privacy rules.
2. Refine responsive/focus styles for desktop and mobile, preserving the no-horizontal-overflow
   contract and the explicit "no history is not a penalty" message.
3. Add a deterministic Playwright brand contract for the public FSP entry point across the configured
   responsive viewports; candidate no-history and linked-achievement state behavior remains covered by
   the existing authenticated backend integration tests until candidate-session browser fixtures exist.
4. Update FSP integration documentation and mark only the M05 backlog unit as IMPLEMENTED. Keep
   requirement-matrix statuses at IMPLEMENTED (never VERIFIED).

## Verification

- `npm run build` in `frontend`.
- `npm run test` in `qa` (or the focused Playwright test when the full service stack is unavailable).
- Existing backend FSP tests remain unchanged; host execution was unavailable because the shell
  has no `pytest`, so the locked Compose test environment remains the supervisor's verification path.

## Status

- [x] Plan created
- [x] Implementation
- [x] Tests
- [x] Documentation/status updates
