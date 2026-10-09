# Synthetic validation dataset

The repository owns a deterministic, PII-free fixture generator for validation
work. It is versioned separately from production candidate data and does not
seed the application database.

## Contract

`backend/app/validation_dataset.py` generates, from a fixed seed:

- 80 candidates across all eight taxonomy specializations and all three target
  grades;
- verified and unconfirmed grade states;
- partial skill evidence with fresh, expiring, and stale freshness states;
- candidates both with and without FSP history;
- an assessment response profile with a labeled target grade, bounded ability,
  and a per-candidate response seed; it contains no answer keys;
- 20 employer hiring needs with required and preferred skills; and
- one expected relevance label (`relevant`, `adjacent`, or `not_relevant`) for
  every candidate/need pair.

The labels are synthetic ground truth for later matching metric work. They do
not change Talent Radar ranking or production grade decisions. No personal
names, email addresses, passwords, tokens, or resume text are included.

## Reproduce

From `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.validation_dataset \
  --output /tmp/fsp-validation-dataset.json
```

The default seed is `fsp-validation-dataset-2026-10-09`. A different seed is
allowed for sensitivity checks, while the shape and taxonomy contract remain
fixed. The generator and JSON representation are covered by
`backend/tests/test_validation_dataset.py`.

This unit establishes `VAL-001`. Matching metrics, assessment metrics, load
testing, validation results, and a dashboard are separate M13 work units.
