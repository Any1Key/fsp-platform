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
