# Responsive screenshot evidence

The repository's visual evidence suite is `qa/tests/screenshots.spec.ts`. It runs against the real
Next.js public landing page and captures the same synthetic, public profile at every required
viewport. It does not use an authenticated storage state.

## Captured surfaces

Each Playwright project writes three PNGs to `.agent/screenshots/latest/`:

- `fsp-<project>-hero.png` — the branded entrypoint and primary CTA;
- `fsp-<project>-evidence.png` — the synthetic verified-profile evidence card;
- `fsp-<project>-full-page.png` — the complete landing journey, including the three product
  principles.

The suite also writes `screenshot-manifest.json`, which records the fixture, privacy scope, projects,
and surfaces present in the capture directory.

## Viewport matrix

| Project | Viewport |
|---|---:|
| `desktop-1920` | 1920×1080 |
| `laptop-1366` | 1366×768 |
| `tablet-1024` | 1024×768 |
| `tablet-768` | 768×1024 |
| `mobile-390` | 390×844 |

The capture uses reduced-motion mode, waits for the JetBrains Mono font, and routes the public
Keycloak hostname to the Compose service so the public auth shell settles without creating or using
an account. The screenshot assertions verify the synthetic category, score, skills, and bounded FSP
evidence text before any image is written.

## Synthetic fixture and privacy boundary

The fixture is the public landing card:

- `Backend · Middle`
- assessment score `87`
- `Python`, `FastAPI`, and `PostgreSQL`
- `FSP evidence becomes a bounded verified signal`

These values are product demonstration content, not a candidate record. Screenshots must not be
captured from authenticated storage states and must not contain real candidate PII, resumes, chat,
contacts, tokens, or minor-consent documents. `.agent/screenshots/` is runtime evidence and is
ignored by Git; external supervision may archive a reviewed capture.

## Running the suite

With the Compose services available:

```sh
docker compose --profile test run --rm qa npm run screenshots
```

Or directly inside the QA container:

```sh
docker compose --profile test run --rm qa npm run screenshots
```

The resulting files are the implementation evidence for the M14 screenshot work unit. External
supervision owns visual review and any `VERIFIED` decision.
