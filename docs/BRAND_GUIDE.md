# FSP brand guide for the product

Sources:
- supplied FSP brand archive;
- official FSP brandbook page: `https://fsp-russia.ru/press/brandbook/`.

## Official palette

Primary:
- `#402FFF` — FSP electric blue/violet.
- `#EC1D35` — FSP red.
- `#EDEDED` — light neutral.

Additional documented colors:
- `#C8C9CA` — neutral gray.
- `#1B1C21` — dark charcoal.

## Typography

Official brand font: **JetBrains Mono**.

The supplied font archive is intentionally not redistributed in this bootstrap. Frontend may install
JetBrains Mono through an open-source package dependency.

Recommended product treatment:
- JetBrains Mono for headings, metrics, badges and code-like labels;
- a readable system sans-serif for dense body/form text is allowed if it materially improves usability;
- primary brand moments retain JetBrains Mono.

## Official visual language

The official page describes:
- a human/wireframe head as a potential participant in sports-programming competitions;
- a map of Russia as the regional-presence motif;
- connecting lines as the visual metaphor for links between regional representations.

Product use:
- wireframe head: onboarding/verified-talent hero, assessment completion;
- map: FSP achievements/regions or institutional context;
- connector lines: subtle matching/connection background motif.

Use motifs sparingly. This is a SaaS product, not a poster.

## Supplied assets

`frontend/public/brand/`:
- `logo_big_blue.png`
- `logo_small_blue.png`
- `logo_white1.png`
- `photo.jpeg`

Use the correct contrast variant. Do not stretch or recolor raster logos.

## Additional official assets

Run `./scripts/fetch-brand-assets.sh` when the Synology host has Internet access. It fetches the official
wireframe head, Russia map and connector line from the public FSP site.

## Visual direction

**FSP identity × verified engineering evidence × modern B2B SaaS.**

Avoid:
- generic admin-template look;
- gratuitous gradients;
- overuse of red;
- dense dashboard clutter;
- fake "AI" visual noise;
- copying a conventional job-board layout.

Prioritize:
- strong hierarchy;
- verification/evidence;
- clear cards;
- obvious salary;
- meaningful match explanations;
- responsive behavior.

## 2026-10 brand audit record

The shared frontend foundation and public entrypoint were audited against this guide on 2026-10-10.

- Palette tokens use the official primary blue/violet `#402FFF`, red `#EC1D35`, light neutral
  `#EDEDED`, muted gray `#C8C9CA` and charcoal `#1B1C21`.
- `logo_white1.png` is reserved for the charcoal hero/header surface; the supplied blue logo variants
  remain available for light surfaces. Raster assets are rendered with `object-fit: contain` and are
  never recolored or stretched.
- JetBrains Mono remains the product voice for the public shell and evidence labels.
- The landing page uses a restrained charcoal/blue/red treatment. Red is limited to evidence emphasis,
  while the product story centers on verified evidence and reverse recruitment.
- All public navigation controls expose a 3px keyboard focus ring, and reduced-motion users receive
  an automatic-scroll/transition reduction.
- The shared shell gives the 1024px tablet surface a full content column and collapses dense dashboard
  grids at the mobile breakpoint; the required desktop, laptop, tablet and mobile viewport checks
  assert no horizontal overflow and keep primary surfaces inside the viewport in
  `qa/tests/fsp-brand.spec.ts`.
