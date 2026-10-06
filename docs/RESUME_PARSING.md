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

## Implemented MVP contract

The candidate upload is consent-gated and creates a private structured extraction
with parser version, field confidence, and provenance. The extraction status is
`needs_review` until the candidate explicitly accepts or rejects it through
`PATCH /api/v1/candidate/resume/{document_id}/review`.

Accepted fields are limited to professional profile data (name, headline,
summary, skills, and experience). Contacts remain visible only in the private
review response and are never copied into the profile. Resume claims remain
declared evidence and do not determine an assessed category or grade.

PDFs without extractable text return `unsupported`; the source document remains
available and the candidate can complete the profile manually. No paid API,
GPU, raw extracted-text store, or automatic profile overwrite is required.
