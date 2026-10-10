# UI acceptance criteria

Check key pages at:
- 1920×1080
- 1366×768
- 1024×768
- 768×1024
- 390×844

Must pass:
- no horizontal overflow;
- no overlapping fixed controls;
- no clipped primary CTA;
- usable mobile flow, not desktop table squeezed smaller;
- consistent component styles;
- visible keyboard focus;
- keyboard users can reveal a skip link and move focus to the main content;
- public text and primary controls meet a 4.5:1 minimum contrast target;
- error/empty/loading states;
- correct FSP-logo contrast;
- salary visible in invitation/vacancy;
- match score has explanation;
- declared vs verified evidence visually distinct;
- candidate contacts never rendered pre-unlock.

The public keyboard/contrast contract is exercised by
`qa/tests/accessibility.spec.ts` across the configured desktop, laptop, tablet
and mobile projects. Focus uses a two-tone ring so it remains visible on both
the charcoal hero and white evidence surfaces; forced-colors mode defers to
the platform highlight color.

Playwright stores evidence in `.agent/screenshots/`. The responsive screenshot suite captures the
hero, synthetic evidence card, and full public journey for all five projects; see
`docs/SCREENSHOT_EVIDENCE.md` for the artifact contract and privacy boundary.
