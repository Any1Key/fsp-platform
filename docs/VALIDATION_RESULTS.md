# Validation results

Status: **MEASURED — local synthetic matching and assessment runs**

## Matching ranking baseline

Command, run from `backend/` on 2026-10-09:

```sh
PYTHONPATH=. .venv/bin/python -m app.matching_metrics \
  --output /tmp/fsp-matching-metrics.json
```

This compares the label-free skill/Jaccard baseline with the fixed-seed,
synthetic relevance matrix. `relevant` and `adjacent` count as positive for
Precision@5 and Recall@10; nDCG@5 uses graded gains
(`relevant=2`, `adjacent=1`, `not_relevant=0`). Values below are macro averages
over 20 needs and 80 candidates per ranking.

| Metric | Result |
|---|---:|
| Precision@5 | 0.620000 |
| nDCG@5 | 0.506438 |
| Recall@10 | 0.699386 |

The run evaluated 20 complete rankings and 1,600 candidate/need labels. These
are deterministic synthetic baseline results, not production performance or
external supervisor verification. Per-need values are included in the JSON
output produced by the command above. The implementation and tests are in
`backend/app/matching_metrics.py` and `backend/tests/test_matching_metrics.py`.

Command, run from `backend/` on 2026-10-09:

```sh
PYTHONPATH=. .venv/bin/python -m app.assessment_validation \
  --output /tmp/fsp-assessment-validation.json
```

This is the actual JSON output from the fixed-seed default run. It is synthetic
domain evidence only; it is not external supervisor verification and does not
represent production candidate outcomes.

```json
{
  "candidates_per_grade": 24,
  "confusion_matrix": {
    "Junior": {"Junior": 20, "Middle": 4, "Senior": 0},
    "Middle": {"Junior": 0, "Middle": 10, "Senior": 14},
    "Senior": {"Junior": 0, "Middle": 0, "Senior": 24}
  },
  "critical_domain_reliability": {
    "api_fundamentals": 0.6806,
    "security_operations": 0.6058
  },
  "equivalent_form_score_difference": 15.3753,
  "form_uniqueness_rate": 1.0,
  "grade_agreement": 0.75,
  "grade_collapse": false,
  "grade_collapse_threshold": 0.8,
  "item_metrics": {
    "api-1": {"difficulty": 0.3235, "discrimination": 0.6213, "observations": 68, "pass_rate": 0.6765},
    "api-2": {"difficulty": 0.25, "discrimination": -0.6736, "observations": 4, "pass_rate": 0.75},
    "arch-1": {"difficulty": 0.3281, "discrimination": 0.6543, "observations": 64, "pass_rate": 0.6719},
    "arch-2": {"difficulty": 0.375, "discrimination": 0.7946, "observations": 8, "pass_rate": 0.625},
    "runtime-1": {"difficulty": 0.4127, "discrimination": 0.5582, "observations": 63, "pass_rate": 0.5873},
    "runtime-2": {"difficulty": 0.2222, "discrimination": -0.0185, "observations": 9, "pass_rate": 0.7778},
    "sec-1": {"difficulty": 0.3077, "discrimination": 0.7105, "observations": 65, "pass_rate": 0.6923},
    "sec-2": {"difficulty": 0.4722, "discrimination": 0.6222, "observations": 72, "pass_rate": 0.5278},
    "sql-1": {"difficulty": 0.2727, "discrimination": 0.7154, "observations": 66, "pass_rate": 0.7273},
    "sql-2": {"difficulty": 0.375, "discrimination": 0.6451, "observations": 72, "pass_rate": 0.625},
    "test-1": {"difficulty": 0.3788, "discrimination": 0.7153, "observations": 66, "pass_rate": 0.6212},
    "test-2": {"difficulty": 0.1667, "discrimination": 0.0638, "observations": 6, "pass_rate": 0.8333}
  },
  "macro_f1": 0.7365,
  "mean_item_discrimination": 0.4507,
  "positive_item_discrimination_rate": 0.8333,
  "predicted_distribution": {"Junior": 20, "Middle": 14, "Senior": 38},
  "retest_agreement": 0.625,
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
