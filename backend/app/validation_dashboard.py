"""Aggregate, PII-free projection for the validation demo dashboard.

The dashboard deliberately consumes the offline validation engines instead of
reading production candidate data. Its output is safe to expose as aggregate
synthetic evidence, while the detailed artifacts remain an engineering
validation concern.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .assessment_validation import DEFAULT_SEED as ASSESSMENT_DEFAULT_SEED, run_validation
from .matching_metrics import build_matching_metrics

DASHBOARD_VERSION = "2026-10-10"


@lru_cache(maxsize=4)
def build_validation_dashboard(*, seed: str = ASSESSMENT_DEFAULT_SEED) -> dict[str, Any]:
    """Build the stable aggregate used by the read-only dashboard endpoint."""

    matching = build_matching_metrics(seed=seed)
    assessment = run_validation(seed=seed)
    return {
        "dashboard_version": DASHBOARD_VERSION,
        "dataset": {
            "version": matching.dataset_version,
            "seed": matching.seed,
            "candidate_count": matching.candidate_count,
            "need_count": matching.need_count,
        },
        "matching": {
            "matching_metrics_version": matching.matching_metrics_version,
            "keyword_baseline_version": matching.keyword_baseline_version,
            "matching_validation_version": matching.matching_validation_version,
            "precision_at_5": matching.macro_precision_at_5,
            "ndcg_at_5": matching.macro_ndcg_at_5,
            "recall_at_10": matching.macro_recall_at_10,
            "ranking_count": len(matching.rankings),
        },
        "assessment": {
            "validation_version": assessment.validation_version,
            "specialization": assessment.specialization,
            "candidates_per_grade": assessment.candidates_per_grade,
            "sample_size": assessment.sample_size,
            "macro_f1": assessment.macro_f1,
            "grade_agreement": assessment.grade_agreement,
            "confusion_matrix": assessment.confusion_matrix,
            "predicted_distribution": assessment.predicted_distribution,
            "grade_collapse": assessment.grade_collapse,
            "grade_collapse_threshold": assessment.grade_collapse_threshold,
            "grade_collapse_dominant_grade": assessment.grade_collapse_dominant_grade,
            "grade_collapse_share": assessment.grade_collapse_share,
            "equivalent_form_score_difference": assessment.equivalent_form_score_difference,
            "retest_agreement": assessment.retest_agreement,
            "mean_item_discrimination": assessment.mean_item_discrimination,
            "positive_item_discrimination_rate": assessment.positive_item_discrimination_rate,
            "critical_domain_reliability": assessment.critical_domain_reliability,
            "form_uniqueness_rate": assessment.form_uniqueness_rate,
            "item_metrics": assessment.item_metrics,
        },
    }

