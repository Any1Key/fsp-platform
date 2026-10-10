# M14 official FSP brand audit

## Objective

Complete one coherent M14 work unit by turning the shared frontend brand foundation and public landing page into an auditable FSP-branded, responsive browser surface.

## Requirement IDs

- NFR-008 — modern desktop browsers.
- NFR-009 — responsive tablet/mobile.
- UI acceptance criteria in `docs/UI_ACCEPTANCE_CRITERIA.md` — correct logo contrast, no overflow/clipped CTA, visible focus and consistent responsive states.

## Scope

- Audit and normalize the shared FSP palette, typography, logo treatment, semantic focus state, reduced-motion behavior and responsive landing layout.
- Replace bootstrap/placeholder presentation copy with product-facing reverse-recruitment language.
- Add browser assertions for palette/font/logo contrast, focus visibility, reduced motion, and all five required viewport sizes.
- Record the audit decisions and evidence in the brand documentation.

Out of scope: new product journeys, server/API changes, external brand-asset downloads, and the separate M14 screenshot-evidence-suite work unit.

## Files expected to change

- `frontend/src/app/globals.css`
- `frontend/src/app/page.tsx`
- `qa/tests/fsp-brand.spec.ts`
- `docs/BRAND_GUIDE.md`
- `docs/DESIGN_SYSTEM.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `.agent/BACKLOG.md`

## Verification

- `npm run typecheck` in `frontend`.
- `npm run build` in `frontend`.
- Playwright `fsp-brand.spec.ts` at desktop, laptop, tablet and mobile projects, including keyboard focus and reduced-motion assertions.

## Progress

- 2026-10-10: implemented the audited public shell, semantic brand tokens,
  approved inverse-logo treatment, keyboard/reduced-motion contract and
  browser assertions. Frontend typecheck/build pass; the pinned QA container
  passes the five-project brand test. Requirement IDs `NFR-008` and `NFR-009`
  are `IMPLEMENTED`; external supervisor owns VERIFIED and READY state.
