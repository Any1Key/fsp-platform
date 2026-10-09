# M13 — Keyword baseline matcher

## Purpose / user value

Provide a reproducible conventional-search comparator for the matching
validation fixture. This gives later metric work a concrete baseline against
which ProofMatch can be evaluated without making resume-keyword search part of
the production Talent Radar ranking path.

## Requirement IDs

- `VAL-002` — own validation procedure and real results; this slice adds the
  baseline input/output contract, while metric execution remains a later M13
  unit.
- `MATCH-001` — matching validation must compare the category-first system
  with a simple keyword baseline; this comparator is offline evidence only.

## Current behavior

`backend/app/matching_validation.py` materializes 1,600 labeled
candidate/need cases, but there is no deterministic conventional baseline
ranking that consumes those cases. The validation plan names a simple
resume-keyword/Jaccard comparator but does not yet provide its output.

## Implementation

- Add `backend/app/keyword_baseline.py` with immutable JSON-safe ranking
  records and a CLI.
- Treat the fixture’s canonical candidate skill slugs as the available
  keyword set and the union of required/preferred need skills as the query
  keyword set. Score `|candidate ∩ need| / |candidate ∪ need|`.
- Rank every candidate for every need, sort by descending score and stable
  candidate ID, and include overlap details for later metric/explanation
  checks.
- Keep expected relevance labels and all protected/evidence dimensions out of
  the scoring function; do not import production discovery or the database.

## Test plan

- Same-seed generation is byte-for-byte stable and covers all 20 needs × 80
  candidates.
- Scores and overlap details follow the Jaccard contract, including empty
  sets and deterministic tie-breaking.
- Changing synthetic labels or non-keyword candidate dimensions does not
  change rankings.
- CLI output is JSON-safe and contains only synthetic IDs and keyword data.

## Documentation / status boundary

Update the matching validation and validation-plan docs with the baseline
contract and command. Mark only the `keyword baseline matcher` M13 backlog
item as `IMPLEMENTED`; leave ranking metrics, assessment metrics, load
validation, dashboard and actual validation results for later work.

## Progress / decisions / surprises

- 2026-10-09: selected as the highest-priority unfinished M13 work unit.
- 2026-10-09: used canonical synthetic skill slugs as the fixture’s
  resume-keyword proxy because the PII-free dataset intentionally contains no
  resume text.
- 2026-10-09: implemented the offline ranking artifact and CLI; focused tests
  (7), full backend tests (151), and targeted Ruff checks pass. The generated
  default artifact contains 20 rankings of 80 candidates and no relevance
  labels.
