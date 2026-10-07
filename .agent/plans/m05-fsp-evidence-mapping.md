# M05 FSP evidence mapping

## Purpose / user value

Give FSP achievements a stable, explainable evidence shape that later ProofMatch
ranking can consume: canonical specialization/skill mappings, deterministic
result strength, and a current recency band. Candidates can see how registry
records are normalized without treating FSP history as a requirement.

## Requirement IDs

- M05: relevance/recency/result mapping
- FSP-001: no-history remains a valid state
- FSP-003: this slice covers the evidence mapping/display prerequisite only;
  bounded ranking contribution remains a separate work unit
- DOC-005: FSP integration scheme documentation

## Current behavior

`fsp_achievement` stores raw synthetic achievement fields and the candidate API
returns them. The adapter has no canonical skill mapping or result-strength
normalization, and recency is not exposed. `docs/FSP_INTEGRATION.md` describes
these as future matching inputs.

## Proposed design

- Add deterministic canonical mapping fields to the snapshot table.
- Map the synthetic Backend Engineering discipline to the existing taxonomy
  specialization and skills; unknown future disciplines remain unmapped rather
  than being guessed.
- Normalize result strength from achievement type and placement into a bounded
  0–100 score plus a human-readable label.
- Derive recency from event date and an explicit `as_of` date at response time;
  future dates are not rewarded and old evidence is labeled rather than
  discarded.
- Return mapping, result, and recency metadata through the candidate-owned API
  and show concise mapping evidence in the branded candidate panel.

## Files/modules

- `backend/app/fsp.py`
- `backend/app/main.py`
- `backend/alembic/versions/20261007_0010_fsp_evidence_mapping.py`
- `backend/tests/test_fsp.py`
- `backend/tests/test_migrations.py`
- `frontend/src/components/candidate-fsp.tsx`
- `frontend/src/app/globals.css`
- `docs/FSP_INTEGRATION.md`
- `docs/DATA_MODEL.md`
- `.agent/BACKLOG.md`

## Data/API changes

Add canonical specialization, canonical skill slugs, result score/label to the
achievement snapshot. Add `mapped_specialization`, `mapped_skills`,
`result_score`, `result_label`, `recency_score`, and `recency_label` to the
candidate FSP response. No employer-facing ranking endpoint is added here.

## Security/privacy implications

Mapping remains candidate-scoped and uses no protected attributes. No new
external data or contacts are exposed. Unknown mappings are explicit and do
not exclude candidates.

## Test plan

- unit-test mapping for placement/result precedence, unknown result, recency
  boundaries, future dates, and unknown disciplines;
- integration-test persisted mapped fields and API response;
- retain no-history, consent, candidate-scope, and unlink coverage;
- verify the migration creates the new columns and downgrades cleanly;
- run backend tests, Ruff, and frontend type/build checks.

## Demo/evidence

Candidate FSP panel shows mapped skills, result strength, and recency for the
synthetic record, while the no-history state remains explicit. The requirement
matrix is not marked for bounded ranking until employer discovery consumes this
mapping.

## Progress / decisions / surprises

- 2026-10-07: plan created from the highest-priority unfinished M05 item.
- Deliberately deferred bounded FSP ranking contribution to keep this work
  unit limited to evidence normalization and presentation.
- 2026-10-07: implemented with migration `20261007_0010`, candidate API/UI
  fields, focused mapping/integration tests, and full backend/frontend checks.
