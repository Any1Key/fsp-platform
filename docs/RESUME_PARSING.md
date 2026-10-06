# Resume parsing

## Required extraction

From candidate PDF where present:
- full name;
- contacts;
- stack/skills;
- declared grade;
- roles;
- experience duration/history;
- soft skills.

## Trust model

Resume extraction is **declared evidence**, not verified assessment evidence.

## Workflow

`upload → validate PDF → parse text → extract structured fields → confidence/provenance →
candidate review/edit → save`

Never silently overwrite profile fields from a parser.

## Implementation

Core must work without paid AI:
- PDF text extraction;
- deterministic patterns;
- skill dictionary/taxonomy mapping.

Optional AI may improve field extraction/mapping, but candidate review is mandatory.

Scanned/image-only PDF can be reported as unsupported in MVP or routed to a bounded OCR path if implemented safely.
