# M13 — Matching ranking metrics

## Purpose / user value

Measure the deterministic keyword comparator against the versioned synthetic
candidate/need relevance labels so the project has a reproducible baseline for
matching-quality review. The report is offline evidence only; it must never
feed candidate discovery or production ProofMatch scores.

## Requirement IDs

- `VAL-002` — own validation procedure and real results; this slice adds the
  ranking-metric evaluator and a measured fixed-seed report.
- `MATCH-004` — matching validation must support explainable, reviewable
  ranking evidence; this slice validates ranking output, not production
  explanation quality.

## Current behavior

`backend/app/matching_validation.py` provides a complete labeled matrix and
`backend/app/keyword_baseline.py` produces a complete label-free ranking, but
the repository has no evaluator for Precision@5, nDCG@5 or Recall@10.

## Implementation

- Add `backend/app/matching_metrics.py` with immutable JSON-safe per-need and
  macro-averaged metrics.
- Treat `relevant` and `adjacent` as retrieved-positive labels for Precision
  and Recall; retain the graded `relevant=2`, `adjacent=1`,
  `not_relevant=0` gains for nDCG.
- Validate that the supplied baseline is complete, has no duplicate candidates
  or needs, and matches the labeled artifact before calculating metrics.
- Add a fixed-seed CLI and write the measured report into
  `docs/VALIDATION_RESULTS.md`.

## Test plan

- Verify exact Precision@5, nDCG@5 and Recall@10 values on a small handcrafted
  ranking, including deterministic tie/order behavior.
- Verify the default 20 × 80 evaluation is reproducible and complete.
- Reject duplicate/missing ranking entries and mismatched labeled artifacts.
- Verify JSON output is deterministic and contains only synthetic IDs and
  metric data.

## Documentation / status boundary

Update the matching validation and validation-plan docs with metric semantics
and the reproducible command. Mark only the M13 ranking-metrics item as
`IMPLEMENTED`; leave assessment metrics, load validation, dashboard and final
validation readiness for later work. Never mark `VERIFIED` or set READY.

## Progress / decisions / surprises

- 2026-10-09: selected as the highest-priority unfinished M13 work unit.
- 2026-10-09: used `relevant` and `adjacent` as positive retrieval labels so
  the metric reflects the fixture's explicit near-fit class; nDCG preserves
  the distinction through graded gains.
- 2026-10-09: implemented the evaluator and fixed-seed CLI; focused tests
  (4), full backend tests, lint and deterministic report generation pass.
