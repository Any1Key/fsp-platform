# M14 responsive desktop/tablet/mobile surfaces

## Purpose / user value

Make the FSP Talent public entrypoint and authenticated dashboard shell usable at the required
desktop, laptop, tablet and mobile sizes. Employers must be able to reach discovery actions and
candidates must be able to reach evidence and assessment actions without horizontal scrolling or
desktop layouts being squeezed into a narrow column.

## Requirement IDs

- NFR-008 — modern desktop browsers.
- NFR-009 — responsive tablet/mobile.
- UI acceptance criteria in `docs/UI_ACCEPTANCE_CRITERIA.md` — no horizontal overflow, no clipped
  primary CTA, usable mobile flow, and consistent responsive states.

## Current behavior

The public shell and authenticated components share `globals.css`, but most responsive overrides
begin at 850px. At the 1024px acceptance viewport the hero still reserves a narrow second column,
which constrains the signed-in panel and keeps dense dashboard grids in their desktop arrangement.
The browser contract only exercises the public landing page.

## Proposed design

- Add a tablet breakpoint that gives the product shell a full-width content column while preserving
  the evidence card as a bounded secondary surface.
- Add explicit `min-width: 0` and safe wrapping behavior to the authenticated shell and high-density
  card/list regions.
- Preserve the existing 850px mobile transformations and strengthen the few remaining dense rows
  so controls and primary actions stay reachable.
- Extend the responsive browser contract across all five required viewport projects with bounds and
  overflow assertions for the public CTA/evidence surface.

## Files/modules

- `frontend/src/app/globals.css`
- `qa/tests/fsp-brand.spec.ts`
- `docs/DESIGN_SYSTEM.md`
- `docs/BRAND_GUIDE.md`
- `.agent/BACKLOG.md`

## Data/API changes

None.

## Security/privacy implications

None. This work changes layout only and does not change visibility, role checks, contact unlocks,
or candidate evidence projections.

## Test plan

- Frontend TypeScript check and production build.
- Playwright brand/responsive contract at 1920×1080, 1366×768, 1024×768, 768×1024 and 390×844.
- Assert no document overflow and that the primary CTA and evidence card remain within the viewport.

## Demo/evidence

The browser contract is the implementation evidence. External supervision owns the final screenshot
and `VERIFIED` decision.

## Progress / decisions / surprises

- 2026-10-10: selected as the highest-priority unfinished backlog work unit; the existing M14
  brand audit is complete, so this plan is limited to responsive surface hardening.
- 2026-10-10: added the 1100px tablet shell collapse, safe authenticated-panel sizing, and mobile
  task-rubric wrapping in `globals.css`; extended `fsp-brand.spec.ts` with viewport-boundary checks.
- 2026-10-10: frontend typecheck/build passed; the pinned QA Compose profile passed all five
  responsive brand projects. NFR-008/NFR-009 were already `VERIFIED` in the requirements matrix,
  so no status was changed or downgraded.
