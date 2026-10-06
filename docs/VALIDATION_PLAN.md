# Validation plan

## Synthetic dataset

Generate deterministic versioned data with fixed RNG seed:
- 80 candidates across specializations and intended Junior/Middle/Senior abilities;
- verified and unconfirmed-grade cases;
- candidates with and without FSP history;
- varied verified skills/freshness;
- 20 employer needs;
- expected relevance labels;
- synthetic assessment-response profiles with known target grade/ability.

## Matching metrics

- Precision@5
- nDCG@5
- Recall@10
- category eligibility accuracy
- grade-state correctness
- explanation completeness
- no-FSP fairness sanity check

Baseline: simple resume keyword/Jaccard overlap.

## Assessment metrics

- grade agreement / macro-F1 against synthetic target labels;
- confusion matrix;
- equivalent-form score difference;
- repeated-attempt stability;
- item difficulty;
- item discrimination;
- critical-domain reliability;
- form uniqueness rate;
- grade-collapse check.

Never force a quota or curve simply to obtain diverse grade outputs.

## Integrity tests

Simulate:
- copied/near-identical submissions;
- large paste/focus anomalies;
- fast correct candidate;
- inconsistent anchors;
- progressive follow-up success/failure.

Validate that integrity flags are explainable/advisory and do not automatically alter grade.

## Employer pipeline validation

Verify:
- employer creates/versions/publishes task;
- matched candidate receives correct version;
- employer grades own task;
- another employer cannot grade it;
- result appears as employer-specific evidence only;
- local AI disabled path remains fully functional.

## Chat/privacy validation

Verify no chat before match, chat after accepted invitation, strict participant authorization and safe logging.

## UX validation

Playwright executes complete demo journeys and captures responsive screenshots with synthetic demo accounts.

## Load validation

Run repository-controlled scenarios from `PERFORMANCE_TESTING.md` on the target Synology or equivalent host. Record actual p50/p95/p99, error rate, CPU/RAM and service health.

## Results

Write actual results to `docs/VALIDATION_RESULTS.md`. Never invent metrics.
