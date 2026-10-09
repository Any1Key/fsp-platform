# Validation plan

## Synthetic dataset

The versioned, deterministic fixture contract is implemented in
`backend/app/validation_dataset.py` and documented in
`docs/VALIDATION_DATASET.md`. It generates the following with a fixed RNG
seed:

- 80 candidates across all specializations and intended Junior/Middle/Senior abilities;
- verified and unconfirmed-grade cases;
- candidates with and without FSP history;
- varied skill evidence and freshness states;
- 20 employer needs; and
- one expected relevance label per candidate/need pair plus synthetic
  assessment-response profiles with known target grade/ability.

This establishes the fixture for later validation units; it does not claim
that the matching or load metrics below have been run.

The complete candidate/need relevance labels are materialized into a stable
offline case artifact by `backend/app/matching_validation.py`, documented in
`docs/MATCHING_VALIDATION.md`. This validates label and state coverage only;
the keyword baseline and ranking metrics remain separate validation units.

## Matching metrics

- Precision@5
- nDCG@5
- Recall@10
- category eligibility accuracy
- grade-state correctness
- explanation completeness
- no-FSP fairness sanity check

Baseline: implemented offline in `backend/app/keyword_baseline.py` as a
simple skill-keyword/Jaccard overlap comparator over the PII-free fixture;
candidate skill slugs are the resume-keyword proxy. The baseline output is
label-free and does not enter production ProofMatch. Reproduce it with:

```sh
PYTHONPATH=. .venv/bin/python -m app.keyword_baseline \
  --output /tmp/fsp-keyword-baseline.json
```

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
