# Validation Dashboard

The employer demo workspace includes a read-only **Validation Dashboard**.
It is a compact view of the repository-owned synthetic validation evidence:

- matching `Precision@5`, `nDCG@5`, and `Recall@10` from the fixed-seed
  label-free keyword baseline;
- assessment macro-F1, grade agreement, form uniqueness, retest agreement,
  and the actual grade confusion matrix;
- item-family discrimination bars, including non-positive signals that need
  calibration follow-up; and
- the grade-collapse check and its explicit threshold.

The backend projection is `GET /api/v1/validation/dashboard`. It requires a
validated employer, reviewer, or admin role. Candidate roles are rejected.
The response contains aggregate synthetic evidence only: no candidate
profiles, emails, raw relevance labels, assessment prompts, answer keys,
submission text, or production database rows are returned.

The projection is cached in-process because its source reports are
deterministic and CPU-only. `dashboard_version`, dataset seed/version, and
source report versions are returned for auditability. Dashboard values are
calibration evidence, not production hiring decisions, external verification,
or a grade quota/curve.

Evidence: `backend/tests/test_validation_dashboard.py`,
`frontend/src/components/validation-dashboard.tsx`, and the opt-in responsive
scenario in `qa/tests/validation-dashboard-ui.spec.ts`.
