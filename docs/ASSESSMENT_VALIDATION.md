# Synthetic assessment validation

This validation harness checks grade discrimination and equivalent-form
behavior using the real calibrated assessment service. It is offline,
standard-library-only, and uses synthetic labels and responses; it does not
read candidate data, call an AI service, curve results, or modify production
grades.

## Run

From `backend/` with the project virtual environment:

```sh
PYTHONPATH=. .venv/bin/python -m app.assessment_validation \
  --output /tmp/fsp-assessment-validation.json
```

The JSON report uses the fixed seed `fsp-assessment-calibration-2026-10-07`
and 24 labeled profiles per intended grade by default. Tests can pass another
seed or sample size through `run_validation()`. `--output` writes the same
machine-readable payload that is printed to stdout.

## What is measured

- `confusion_matrix`, `grade_agreement`, and `macro_f1`: validation-band
  agreement for the synthetic Junior/Middle/Senior labels. Grade agreement is
  the diagonal accuracy; macro-F1 averages one-vs-rest F1 across grades.
- `equivalent_form_score_difference`: mean absolute score difference between
  two independently parameterized forms for each profile.
- `retest_agreement`: fraction of those paired forms that produce the same
  validation band.
- `item_metrics`: observed pass rate, difficulty (`1 - pass_rate`), and
  point-biserial discrimination by template family. The observation count is
  included because uncommon families need more labeled runs before calibration
  decisions are made.
- `mean_item_discrimination` and `positive_item_discrimination_rate`:
  descriptive aggregates over the family metrics. Negative or low-observation
  families remain visible instead of being hidden or corrected by quotas.
- `critical_domain_reliability`: observed correct-response rate for the API
  and security domains used as critical-domain signals in this harness.
- `form_uniqueness_rate`: distinct family/variant signatures across primary and
  paired forms.
- `grade_collapse`: true when at least 80% of predictions fall into one grade.
  `grade_collapse_dominant_grade` and `grade_collapse_share` identify the
  observed concentration, while `grade_collapse_threshold` records the rule
  used for the run. An empty sample is conservatively collapsed with a zero
  dominant share because it provides no grade-coverage evidence. The detector
  is unit-tested with deliberately degenerate, boundary, empty, and invalid-
  threshold inputs.

The validation-only score bands are `<40` Junior, `40–64.99` Middle, and
`>=65` Senior. They are a calibration view, not a new product rule: the
assessment service still preserves the candidate's declared grade and uses its
existing `verified` / `not_confirmed` state.

The synthetic generator samples ability around fixed grade centers and produces
responses with a difficulty adjustment. The labeled distribution is a test
design choice; predicted outputs are never quota-filled. A report is evidence
for calibration review, not external verification.

## Evidence

- Domain and metric tests: `backend/tests/test_assessment_validation.py`.
- Assessment integration tests: `backend/tests/test_assessments.py`.
- Actual local output from the default run: `docs/VALIDATION_RESULTS.md`.
