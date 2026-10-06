# M03 — Data-driven taxonomy catalog

## Purpose / user value

Provide one authoritative, database-backed catalog of specializations, grades,
and specialization skills so candidate onboarding and later ProofMatch flows
can use stable taxonomy identifiers instead of hard-coded labels.

## Requirement IDs

- CORE-002 — taxonomy is the basis for the employer-visible category; this
  slice provides the stable specialization/grade/category vocabulary, while
  assessed candidate wiring remains unfinished.
- AST-001 / AST-002 — expose the specialization and declared-grade choices
  needed by onboarding; the authenticated onboarding journey remains a later
  unit.
- AST-003 — preserve the data-model boundary for specialization/grade
  assessment blueprints; assessment-to-profile persistence remains later work.

## Current behavior

The foundation migration creates empty `specialization`, `grade`, and
`assessment_blueprint` tables. There is no `skill`/`specialization_skill`
relationship, no initial catalog, and no API for clients to discover the
taxonomy. The assessment domain accepts one hard-coded specialization.

## Proposed design

- Add `skill` and `specialization_skill` tables with foreign keys, uniqueness,
  active flags, and deterministic seed records for the eight product
  specializations, three initial grades, and representative skills.
- Add a read-only `GET /api/v1/taxonomy` endpoint backed by SQL queries. It
  returns IDs/slugs/names, specialization skill mappings, and the explicit
  specialization×grade category keys used by future matching.
- Keep this catalog read-only in this work unit. Candidate profile selection,
  assessment result persistence, employer discovery, and taxonomy administration
  are separate backlog units.

## Files/modules

- `backend/alembic/versions/20261007_0008_taxonomy_catalog.py`
- `backend/app/taxonomy.py`
- `backend/app/main.py`
- `backend/tests/test_taxonomy.py`
- `backend/tests/test_migrations.py`
- `docs/TAXONOMY.md`, `docs/API_GUIDELINES.md`, `docs/DATA_MODEL.md`,
  `docs/ARCHITECTURE.md`

## Data/API changes

- `skill(id, slug, name, active, created_at)`
- `specialization_skill(specialization_id, skill_id, is_core, created_at)`
- `GET /api/v1/taxonomy`

The endpoint is intentionally public because the catalog contains no personal
or protected data and is required to render pre-authentication onboarding
choices. It does not expose candidate grades, assessment results, or profile
data.

## Security/privacy implications

Only non-sensitive catalog metadata is returned. The API has no write path,
does not accept arbitrary IDs from a caller, and does not use protected
candidate attributes. Foreign keys prevent orphaned mappings.

## Test plan

- migrate a clean SQLite database and assert catalog tables, seed counts,
  foreign keys, and specialization-skill uniqueness;
- call the API and verify all eight specializations, three grades, mapped
  skills, and 24 explicit category keys are returned from the database;
- verify category keys are composed from specialization and grade slugs.

## Demo/evidence

Pytest migration/API output and the OpenAPI route are evidence for this slice.
The external supervisor must independently verify the full candidate journey;
this plan does not mark CORE-002, AST-001, AST-002, or AST-003 as verified.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished M03 unit. Existing assessment
  behavior is process-local; this slice deliberately establishes the shared
  taxonomy boundary without claiming assessment persistence or employer search.
- 2026-10-07: implemented migration `20261007_0008`, typed public catalog API,
  migration/API tests, and taxonomy documentation. CORE-002/AST-001/AST-002/
  AST-003 remain broader requirements and were not marked IMPLEMENTED here.
