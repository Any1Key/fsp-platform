# M13 — Assessment confusion, stability, and discrimination validation

## Purpose / user value

Make the synthetic assessment evidence operationally consumable: one fixed-seed
run must expose labeled grade agreement, confusion/macro-F1, repeated-form
stability, and item discrimination without changing production grades or
introducing quotas.

## Requirement IDs

- AST-005 — different forms have comparable difficulty.
- AST-014 — synthetic/labeled validation proves grade discrimination and
  detects grade collapse (the separate backlog grade-collapse item remains a
  follow-up status unit).

## Current behavior

`app.assessment_validation` already runs synthetic profiles through the real
assessment service and reports several metrics, but its report has no explicit
grade-agreement or aggregate discrimination fields and its CLI only streams
JSON to stdout. The M13 backlog does not identify a stable artifact contract.

## Proposed design

- Add grade agreement as the diagonal accuracy of the labeled confusion matrix.
- Add aggregate item discrimination summaries while retaining each family's
  pass rate, difficulty, and point-biserial value, including negative values.
- Preserve equivalent-form score difference and retest agreement as the
  comparability/stability measures.
- Add an explicit `--output PATH` CLI option and a small writer function so a
  fixed-seed report can be captured without including synthetic candidate IDs.
- Keep validation-only score bands separate from production grade state; no
  quotas, curves, database/API changes, or AI dependency.

The follow-up grade-collapse unit makes the existing boolean check auditable:
the report also records the dominant predicted grade and its observed share.
Threshold validation happens before empty-input handling so malformed
validation configuration cannot be silently accepted.

## Files/modules

- `backend/app/assessment_validation.py` — report fields, aggregate metrics,
  and JSON artifact writer/CLI.
- `backend/tests/test_assessment_validation.py` — report contract and output
  artifact tests.
- `docs/ASSESSMENT_VALIDATION.md` — metric and CLI contract.
- `docs/VALIDATION_RESULTS.md` — refreshed fixed-seed assessment evidence.
- `docs/REQUIREMENTS_MATRIX.md` / `.agent/BACKLOG.md` — mark only this unit
  `IMPLEMENTED`; never mark `VERIFIED`.

## Data/API changes

None. The output is an offline validation artifact and the assessment API is
unchanged.

## Security/privacy implications

Only synthetic labels/responses are used. The report must not serialize
candidate IDs, answers, answer keys, or production database data.

## Test plan

- Same seed and sample size produce equal report dictionaries.
- Confusion matrix, grade agreement, macro-F1, retest stability, equivalent
  form difference, and aggregate/item discrimination are populated.
- The explicit output writer produces JSON equivalent to `to_dict()`.
- Grade-collapse behavior reports the dominant grade/share, covers the exact
  threshold boundary and rejects invalid thresholds; it is not used to alter
  scores.

## Demo/evidence

From `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.assessment_validation \
  --output /tmp/fsp-assessment-validation.json
```

The fixed-seed output is copied into `docs/VALIDATION_RESULTS.md` as measured
synthetic evidence; external supervisor verification remains separate.

## Progress / decisions / surprises

- 2026-10-09: selected as the first unfinished unit in M13. Existing M04
  validation code is reused and hardened rather than duplicating the runner.
- 2026-10-09: aggregate discrimination is descriptive evidence; non-positive
  family values remain visible for calibration follow-up.
- 2026-10-09: implemented report fields/writer, CLI output option, tests, and
  refreshed fixed-seed evidence. Backend suite: 156 passed; Ruff and diff
  checks passed. Supervisor verification remains pending.
- 2026-10-10: completed the separate grade-collapse unit with auditable
  dominant-grade/share fields and strict threshold validation.
