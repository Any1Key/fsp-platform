# M04 — Synthetic grade/discrimination validation

## Purpose / user value

Provide a reproducible, CPU-only validation harness that demonstrates whether
the calibrated assessment separates intended Junior/Middle/Senior ability
profiles without forcing grade quotas or using an AI detector.

## Requirement IDs

- AST-014 — synthetic/labeled validation proves grade discrimination and detects
  grade collapse.
- AST-005 — comparable forms are measured through equivalent-form score
  difference and item-level difficulty/discrimination evidence.

## Current behavior

The assessment domain creates parameterized forms and scores submissions, but
there is no repository-controlled synthetic dataset, metric computation, or
grade-collapse report.

## Proposed design

- Add a standard-library-only validation module with a versioned seed and
  labeled candidate ability profiles across all three administered grades.
- Run those profiles through the real `AssessmentService` using deterministic
  form seeds and realistic probabilistic response generation.
- Report confusion matrix, macro-F1, equivalent-form score difference,
  retest agreement, item difficulty/discrimination, critical-domain reliability,
  form uniqueness, and grade-collapse detection.
- Treat score-to-grade bands as a validation calibration view only; the product
  continues to preserve the candidate's declared grade and only exposes its
  existing verified/not-confirmed state.

## Files/modules

- `backend/app/assessment_validation.py` — generator, runner, metrics, report.
- `backend/tests/test_assessment_validation.py` — deterministic and behavioral
  evidence for AST-014/AST-005.
- `docs/ASSESSMENT_VALIDATION.md` — procedure, metric definitions, and usage.
- `docs/REQUIREMENTS_MATRIX.md` / `.agent/BACKLOG.md` — mark only this unit
  `IMPLEMENTED` after tests pass.

## Data/API changes

No database schema or public API changes. The harness is an offline validation
boundary and invokes the existing domain service.

## Security/privacy implications

Synthetic identifiers and generated responses only; no candidate PII,
credentials, or external AI/runtime dependency. The harness must not be used
to rewrite production grades or introduce quotas/curving.

## Test plan

- Same seed produces byte-equivalent report data.
- Report contains labeled confusion matrix and macro-F1 for all grades.
- Grade-collapse check detects a deliberately degenerate prediction set.
- Form uniqueness and equivalent-form metrics are exercised through the real
  assessment factory.
- Item difficulty/discrimination and critical-domain metrics are populated.

## Demo/evidence

Run `python -m app.assessment_validation` from `backend/` for a JSON report.
Tests provide the checked-in evidence path; actual local output is recorded in
`docs/VALIDATION_RESULTS.md` only after running the harness.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished work unit in the highest-
  priority unfinished milestone, M04.
- The service has no product-level grade conversion, so grade-band prediction
  is explicitly scoped to validation calibration and does not downgrade a
  declared grade.
- 2026-10-07: implemented the deterministic runner, metric report, CLI,
  tests, and actual fixed-seed evidence. Low-observation template families and
  non-positive per-family discrimination remain visible for later calibration
  work rather than being hidden or corrected by quotas.
