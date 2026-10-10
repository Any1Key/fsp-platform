# M14 responsive screenshot evidence suite

## Purpose / user value

Provide repeatable visual evidence for the branded public FSP Talent journey at every required
desktop, laptop, tablet, and mobile viewport. The evidence must remain safe to share with reviewers:
it uses the public synthetic profile rendered by the landing page and never depends on an
authenticated account or private candidate data.

## Requirement IDs

- NFR-008 — modern desktop browsers.
- NFR-009 — responsive tablet/mobile.
- UI acceptance criteria in `docs/UI_ACCEPTANCE_CRITERIA.md` — no horizontal overflow, usable mobile
  flow, no clipped primary CTA, and representative responsive screenshots.

## Current behavior

`qa/tests/screenshots.spec.ts` captured one full-page landing screenshot per viewport. It did not
capture the initial hero and evidence card as separate reviewable surfaces, did not assert that the
content was the known synthetic fixture, and did not document the generated artifact set.

## Proposed design

- Keep the capture test on the real Next.js landing page.
- Use a small in-test fixture containing only the public synthetic profile values and assert those
  values before writing screenshots.
- Route the browser's public Keycloak hostname to the Compose Keycloak service so the auth shell can
  settle deterministically during QA; the test does not sign in or create an account.
- Capture the full page, the top-of-page hero, and the evidence-card viewport for each configured
  project. Use reduced-motion mode and wait for the web font before capture.
- Emit `screenshot-manifest.json` beside the PNGs with the fixture name, viewport, surface, and
  privacy scope.

## Files/modules

- `qa/tests/screenshots.spec.ts`
- `docs/SCREENSHOT_EVIDENCE.md`
- `docs/UI_ACCEPTANCE_CRITERIA.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `.agent/BACKLOG.md`

## Data/API changes

None. This is a browser evidence and documentation slice.

## Security/privacy implications

The capture remains unauthenticated and uses only deterministic public demo values. The suite
explicitly documents that screenshots must not be collected from authenticated storage states.

## Test plan

- Run `npm run screenshots` through the Compose `test` profile.
- Confirm three PNG surfaces per project across 1920×1080, 1366×768, 1024×768, 768×1024, and
  390×844, plus the manifest.
- Preserve the existing brand/responsive assertions as the behavioral contract.

## Demo/evidence

`docs/SCREENSHOT_EVIDENCE.md` describes the artifact names, fixture, viewport matrix, and review
procedure. External supervision owns final visual verification and any `VERIFIED` status.

## Progress / decisions / surprises

- 2026-10-10: selected as the highest-priority unfinished backlog work unit.
- 2026-10-10: implementation started; existing public synthetic profile is the only screenshot
  data source, and authenticated screenshot capture is intentionally out of scope for this slice.
- 2026-10-10: `docker compose --profile test run --rm qa npm run screenshots` passed all five
  projects and generated 15 PNG surfaces plus `screenshot-manifest.json`.
