"""Reproducible aggregate report for offline validation evidence.

The report deliberately composes the existing synthetic validation engines
without importing the database, HTTP layer, or production discovery code. It
is the machine-readable source for ``docs/VALIDATION_RESULTS.md`` and contains
only aggregate counts and metric values.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .assessment_validation import DEFAULT_SEED as DEFAULT_ASSESSMENT_SEED
from .assessment_validation import run_validation
from .matching_metrics import build_matching_metrics
from .matching_validation import build_matching_relevance
from .validation_dataset import DEFAULT_SEED as DEFAULT_DATASET_SEED

VALIDATION_REPORT_VERSION = "2026-10-10"


@dataclass(frozen=True)
class ValidationReport:
    """Aggregate, PII-free output of the local synthetic validation run."""

    report_version: str
    status: str
    dataset: dict[str, Any]
    matching: dict[str, Any]
    assessment: dict[str, Any]
    evidence_boundary: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_boundary"] = list(self.evidence_boundary)
        return payload

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True) + "\n"


def build_validation_report(
    *,
    dataset_seed: str = DEFAULT_DATASET_SEED,
    assessment_seed: str = DEFAULT_ASSESSMENT_SEED,
) -> ValidationReport:
    """Run and compose the fixed-seed synthetic validation evidence."""

    relevance = build_matching_relevance(seed=dataset_seed)
    matching = build_matching_metrics(seed=dataset_seed)
    assessment = run_validation(seed=assessment_seed)

    return ValidationReport(
        report_version=VALIDATION_REPORT_VERSION,
        status="MEASURED_SYNTHETIC",
        dataset={
            "version": relevance.dataset_version,
            "seed": relevance.seed,
            "candidate_count": relevance.candidate_count,
            "need_count": relevance.need_count,
            "labeled_pair_count": relevance.case_count,
            "coverage": relevance.coverage,
        },
        matching={
            "matching_metrics_version": matching.matching_metrics_version,
            "keyword_baseline_version": matching.keyword_baseline_version,
            "matching_validation_version": matching.matching_validation_version,
            "seed": matching.seed,
            "candidate_count": matching.candidate_count,
            "need_count": matching.need_count,
            "ranking_count": len(matching.rankings),
            "precision_at_5": matching.macro_precision_at_5,
            "ndcg_at_5": matching.macro_ndcg_at_5,
            "recall_at_10": matching.macro_recall_at_10,
        },
        assessment={
            "validation_version": assessment.validation_version,
            "seed": assessment.seed,
            "specialization": assessment.specialization,
            "candidates_per_grade": assessment.candidates_per_grade,
            "sample_size": assessment.sample_size,
            "confusion_matrix": assessment.confusion_matrix,
            "macro_f1": assessment.macro_f1,
            "grade_agreement": assessment.grade_agreement,
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
        evidence_boundary=(
            "Synthetic fixtures and labels only",
            "Offline CPU-only evaluation; no production database or API access",
            "Not a production hiring-quality claim or external supervisor verification",
            "Authenticated target load measurement is reported separately",
        ),
    )


def write_validation_report(
    path: str | Path,
    *,
    dataset_seed: str = DEFAULT_DATASET_SEED,
    assessment_seed: str = DEFAULT_ASSESSMENT_SEED,
) -> None:
    """Write one deterministic aggregate report to ``path``."""

    Path(path).write_text(
        build_validation_report(
            dataset_seed=dataset_seed,
            assessment_seed=assessment_seed,
        ).to_json(),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Write aggregate offline validation results")
    parser.add_argument("--output", type=Path, help="JSON output path; stdout when omitted")
    parser.add_argument("--dataset-seed", default=DEFAULT_DATASET_SEED)
    parser.add_argument("--assessment-seed", default=DEFAULT_ASSESSMENT_SEED)
    args = parser.parse_args()
    report = build_validation_report(
        dataset_seed=args.dataset_seed,
        assessment_seed=args.assessment_seed,
    )
    if args.output:
        args.output.write_text(report.to_json(), encoding="utf-8")
    else:
        print(report.to_json(indent=None), end="")


if __name__ == "__main__":
    main()
