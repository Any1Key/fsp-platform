# Brandbook analysis

Reviewed inputs:
1. supplied brand archive;
2. official FSP brandbook page.

## Supplied archive contents used

- `logo_big_blue.png`
- `logo_small_blue.png`
- `logo_white1.png`
- `photo.jpeg`
- JetBrains Mono archive was present in the source package; font binaries are not redistributed in this bootstrap.
  The frontend references the open-source font through a package dependency.

## Official page findings

The official page explicitly defines:
- standard palette: `#402FFF`, `#EC1D35`, `#EDEDED`;
- additional palette: `#C8C9CA`, `#1B1C21`;
- primary typeface: JetBrains Mono;
- main graphic motifs:
  - wireframe human head — potential participant;
  - Russia map — FSP regional presence;
  - connecting lines — links between regional representations;
- multiple logo variations.

## Product interpretation

The application should not simply reproduce a federation poster/site.
The visual system extends the identity into a modern SaaS product:
- charcoal/dark institutional hero surfaces;
- FSP blue/violet as primary action/verification accent;
- red used sparingly for emphasis/alerts;
- white/light cards for dense work screens;
- JetBrains Mono as the recognizable brand voice;
- head/map/connector motifs reserved for meaningful branded moments.

This interpretation is documented in `BRAND_GUIDE.md` and `DESIGN_SYSTEM.md`.
