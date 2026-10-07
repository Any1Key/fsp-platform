# Validation results

Status: **MEASURED — local synthetic assessment run**

Command, run from `backend/` on 2026-10-07:

```sh
PYTHONPATH=. .venv/bin/python -m app.assessment_validation
```

This is the actual JSON output from the fixed-seed default run. It is synthetic
domain evidence only; it is not external supervisor verification and does not
represent production candidate outcomes.

```json
{
  "candidates_per_grade": 24,
  "confusion_matrix": {
    "Junior": {"Junior": 22, "Middle": 2, "Senior": 0},
    "Middle": {"Junior": 2, "Middle": 19, "Senior": 3},
    "Senior": {"Junior": 0, "Middle": 2, "Senior": 22}
  },
  "critical_domain_reliability": {
    "api_fundamentals": 0.6806,
    "security_operations": 0.6058
  },
  "equivalent_form_score_difference": 12.8965,
  "form_uniqueness_rate": 1.0,
  "grade_collapse": false,
  "grade_collapse_threshold": 0.8,
  "item_metrics": {
    "api-1": {"difficulty": 0.3235, "discrimination": 0.6232, "observations": 68, "pass_rate": 0.6765},
    "api-2": {"difficulty": 0.25, "discrimination": -0.6736, "observations": 4, "pass_rate": 0.75},
    "arch-1": {"difficulty": 0.3281, "discrimination": 0.6498, "observations": 64, "pass_rate": 0.6719},
    "arch-2": {"difficulty": 0.375, "discrimination": 0.7945, "observations": 8, "pass_rate": 0.625},
    "runtime-1": {"difficulty": 0.4127, "discrimination": 0.5549, "observations": 63, "pass_rate": 0.5873},
    "runtime-2": {"difficulty": 0.2222, "discrimination": -0.0185, "observations": 9, "pass_rate": 0.7778},
    "sec-1": {"difficulty": 0.3077, "discrimination": 0.6988, "observations": 65, "pass_rate": 0.6923},
    "sec-2": {"difficulty": 0.4722, "discrimination": 0.6238, "observations": 72, "pass_rate": 0.5278},
    "sql-1": {"difficulty": 0.2727, "discrimination": 0.7183, "observations": 66, "pass_rate": 0.7273},
    "sql-2": {"difficulty": 0.375, "discrimination": 0.6435, "observations": 72, "pass_rate": 0.625},
    "test-1": {"difficulty": 0.3788, "discrimination": 0.7212, "observations": 66, "pass_rate": 0.6212},
    "test-2": {"difficulty": 0.1667, "discrimination": 0.0638, "observations": 6, "pass_rate": 0.8333}
  },
  "macro_f1": 0.8744,
  "predicted_distribution": {"Junior": 24, "Middle": 23, "Senior": 25},
  "retest_agreement": 0.7083,
  "sample_size": 72,
  "seed": "fsp-assessment-calibration-2026-10-07",
  "specialization": "Backend Engineering",
  "validation_version": "2026-10-07"
}
```

The low-observation families and the two non-positive discrimination values
are intentionally visible in this report. They identify calibration follow-up
work for the current eight-item form; this unit does not hide or curve those
results.
