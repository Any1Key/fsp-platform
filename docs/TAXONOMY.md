# Taxonomy catalog

The taxonomy is the shared vocabulary for candidate onboarding, platform
assessment and employer discovery. It is data-driven and persisted in
PostgreSQL (SQLite is used by the automated migration/API tests).

The initial catalog contains:

- eight specializations: Backend Engineering, Frontend Engineering, Full-stack
  Engineering, QA / Test Automation, DevOps / SRE, Data Engineering, Data
  Science / ML, and Mobile Engineering;
- three ordered grades: Junior, Middle, Senior;
- active skills mapped to specializations through `specialization_skill`, with
  an `is_core` flag for the first two skills in each seeded mapping.

`GET /api/v1/taxonomy` returns the active catalog and explicit category keys in
the form `specialization-slug:grade-slug`. The endpoint is read-only and
contains no candidate or protected data, so it is available before sign-in for
onboarding forms.

The category vocabulary does not itself verify a candidate. A candidate's
declared grade remains separate from the employer-visible state; the platform
assessment service must produce a verified grade before a candidate is shown
as belonging to a verified specialization/grade category. Unconfirmed grades
remain a separate valid state for later discovery work.

## Ownership and extension

The migration owns the initial seed vocabulary. Candidate profile selection,
assessment result persistence, employer taxonomy administration, and matching
filters are separate work units. Future administrative tooling must preserve
stable slugs and use foreign-key-safe changes to specialization-skill mappings.
