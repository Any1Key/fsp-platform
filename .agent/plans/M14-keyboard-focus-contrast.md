# M14 — Keyboard, focus and contrast contract

## Purpose / user value

Make the public FSP Talent entrypoint usable without a mouse and keep its
primary text, controls and focus indicators legible across the branded dark
hero and light evidence surfaces.

## Requirement IDs

- `NFR-008` — modern desktop browser accessibility evidence.
- `NFR-009` — responsive browser surface remains usable at the acceptance sizes.
- `UI-001` — keyboard navigation, visible focus and public-surface contrast
  contract (tracked here because the backlog item is narrower than the
  already-verified NFR rows).

## Current behavior

The landing page has a shared `:focus-visible` rule, but its lavender ring is
not sufficiently distinct on the white evidence card. Component-specific
focus declarations can also win over the shared rule. Keyboard users have no
skip link, and browser tests do not calculate contrast for the public text and
primary controls.

## Proposed design

- Add a visually-hidden-until-focused skip link to the main content.
- Use a two-tone keyboard focus treatment: a white inner outline for dark
  surfaces and a brand-blue outer ring for light surfaces. Keep disabled
  controls out of the focus treatment and support forced-colors mode.
- Add deterministic Playwright assertions for skip-link behavior, keyboard
  focus visibility, reduced-motion compatibility, and WCAG AA text/control
  contrast on the public landing surface.
- Document the contract and link its implementation evidence in the
  requirements matrix; do not alter supervisor-owned `VERIFIED` statuses.

## Files/modules

- `frontend/src/app/page.tsx` — skip-link target and landmark.
- `frontend/src/app/globals.css` — focus, skip-link, forced-colors and token
  styles.
- `qa/tests/accessibility.spec.ts` — browser contract and contrast helper.
- `qa/package.json` — include the contract in the default QA command.
- `docs/UI_ACCEPTANCE_CRITERIA.md` — explicit keyboard/contrast contract.
- `docs/REQUIREMENTS_MATRIX.md` — `UI-001` evidence row, `IMPLEMENTED` only.
- `.agent/BACKLOG.md` — close only M14 keyboard/focus/contrast.

## Data/API changes

None.

## Security/privacy implications

None. The change is presentation-only and does not alter candidate identity,
evidence, contact, invitation or chat visibility.

## Test plan

- Run the focused Playwright accessibility test across the configured desktop,
  laptop, tablet and mobile projects.
- Run frontend typecheck and production build.
- Confirm the existing brand/responsive contract remains intact.

## Demo/evidence

The focused browser contract demonstrates that Tab reveals a skip link and
primary navigation focus, all tested public text/control pairs meet AA
contrast, and reduced motion is honored. External supervision retains the
final `VERIFIED` and READY decisions.

## Progress / decisions / surprises

- 2026-10-10: selected as the first open item in M14 after reviewing
  `.agent/BACKLOG.md`, the existing brand audit, and the public browser
  contract. Existing `NFR-008`/`NFR-009` rows are already `VERIFIED`; this
  slice adds `UI-001` evidence without downgrading them.
- 2026-10-10: implemented the skip-link/landmark, two-tone focus ring,
  forced-colors fallback, and public contrast contract. Frontend typecheck and
  production build pass. Containerized Playwright passes the focused
  accessibility contract and the existing brand contract across all five
  required viewport projects. `UI-001` and this backlog item are
  `IMPLEMENTED`; external supervision retains `VERIFIED` and READY ownership.
