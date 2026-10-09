"""Offline ranking metrics for the deterministic matching validation fixture.

This module evaluates a label-free ranking artifact against synthetic labels.
It is intentionally separate from production discovery and has no database,
HTTP, or network dependency.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from .keyword_baseline import (
    KeywordBaselineArtifact,
    build_keyword_baseline,
)
from .matching_validation import MatchingRelevanceArtifact, build_matching_relevance
from .validation_dataset import DEFAULT_SEED

MATCHING_METRICS_VERSION = "2026-10-09"
POSITIVE_LABELS = ("relevant", "adjacent")
GRADE_GAINS = {"relevant": 2.0, "adjacent": 1.0, "not_relevant": 0.0}


@dataclass(frozen=True)
class MatchingNeedMetrics:
    """Metrics for one employer need's complete candidate ranking."""

    need_id: str
    positive_label_count: int
    precision_at_5: float
    ndcg_at_5: float
    recall_at_10: float
    top_5_candidate_ids: tuple[str, ...]
    top_5_positive_count: int
    top_10_positive_count: int


@dataclass(frozen=True)
class MatchingMetricsArtifact:
    """Stable report for macro-averaged matching ranking metrics."""

    matching_metrics_version: str
    keyword_baseline_version: str
    matching_validation_version: str
    dataset_version: str
    seed: str
    candidate_count: int
    need_count: int
    positive_labels: tuple[str, ...]
    relevance_gains: dict[str, float]
    rankings: tuple[MatchingNeedMetrics, ...]
    macro_precision_at_5: float
    macro_ndcg_at_5: float
    macro_recall_at_10: float

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ranking_count"] = len(self.rankings)
        return payload

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True) + "\n"


def build_matching_metrics(*, seed: str = DEFAULT_SEED) -> MatchingMetricsArtifact:
    """Build a fixed-seed keyword-baseline metric report."""

    matching = build_matching_relevance(seed=seed)
    baseline = build_keyword_baseline(seed=seed)
    return evaluate_keyword_baseline(baseline, matching)


def evaluate_keyword_baseline(
    baseline: KeywordBaselineArtifact,
    matching: MatchingRelevanceArtifact,
) -> MatchingMetricsArtifact:
    """Evaluate a complete baseline ranking against synthetic relevance labels.

    Precision and Recall use ``relevant`` or ``adjacent`` as positive labels.
    nDCG uses graded gains: relevant=2, adjacent=1, not_relevant=0.
    """

    _validate_artifact_alignment(baseline, matching)
    labels_by_need = _labels_by_need(matching)
    metrics = tuple(
        _need_metrics(ranking.need_id, tuple(result.candidate_id for result in ranking.results), labels)
        for ranking, labels in (
            (ranking, labels_by_need[ranking.need_id]) for ranking in baseline.rankings
        )
    )
    return MatchingMetricsArtifact(
        matching_metrics_version=MATCHING_METRICS_VERSION,
        keyword_baseline_version=baseline.keyword_baseline_version,
        matching_validation_version=matching.matching_validation_version,
        dataset_version=matching.dataset_version,
        seed=matching.seed,
        candidate_count=matching.candidate_count,
        need_count=matching.need_count,
        positive_labels=POSITIVE_LABELS,
        relevance_gains=GRADE_GAINS.copy(),
        rankings=metrics,
        macro_precision_at_5=_macro(metric.precision_at_5 for metric in metrics),
        macro_ndcg_at_5=_macro(metric.ndcg_at_5 for metric in metrics),
        macro_recall_at_10=_macro(metric.recall_at_10 for metric in metrics),
    )


def _validate_artifact_alignment(
    baseline: KeywordBaselineArtifact,
    matching: MatchingRelevanceArtifact,
) -> None:
    if baseline.matching_validation_version != matching.matching_validation_version:
        raise ValueError("keyword baseline and labels use different matching-validation versions")
    if baseline.dataset_version != matching.dataset_version or baseline.seed != matching.seed:
        raise ValueError("keyword baseline and labels must use the same dataset version and seed")
    if baseline.candidate_count != matching.candidate_count:
        raise ValueError("keyword baseline and labels have different candidate counts")
    if baseline.need_count != matching.need_count:
        raise ValueError("keyword baseline and labels have different need counts")

    expected_need_ids = {case.need_id for case in matching.cases}
    actual_need_ids = {ranking.need_id for ranking in baseline.rankings}
    if actual_need_ids != expected_need_ids:
        raise ValueError("keyword baseline does not contain exactly one ranking for every need")
    expected_candidate_ids = {case.candidate_id for case in matching.cases}
    for ranking in baseline.rankings:
        candidate_ids = [result.candidate_id for result in ranking.results]
        if len(candidate_ids) != matching.candidate_count:
            raise ValueError(f"ranking {ranking.need_id} is not complete")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"ranking {ranking.need_id} contains duplicate candidates")
        if set(candidate_ids) != expected_candidate_ids:
            raise ValueError(f"ranking {ranking.need_id} has the wrong candidate set")


def _labels_by_need(matching: MatchingRelevanceArtifact) -> dict[str, dict[str, str]]:
    labels: dict[str, dict[str, str]] = {}
    for case in matching.cases:
        need_labels = labels.setdefault(case.need_id, {})
        if case.candidate_id in need_labels:
            raise ValueError(f"duplicate label for {case.need_id}/{case.candidate_id}")
        need_labels[case.candidate_id] = case.expected_relevance
    return labels


def _need_metrics(
    need_id: str,
    candidate_ids: tuple[str, ...],
    labels: dict[str, str],
) -> MatchingNeedMetrics:
    positive_label_count = sum(label in POSITIVE_LABELS for label in labels.values())
    top_5 = candidate_ids[:5]
    top_10 = candidate_ids[:10]
    top_5_positive_count = sum(labels[candidate_id] in POSITIVE_LABELS for candidate_id in top_5)
    top_10_positive_count = sum(labels[candidate_id] in POSITIVE_LABELS for candidate_id in top_10)
    precision_at_5 = top_5_positive_count / 5
    recall_at_10 = top_10_positive_count / positive_label_count if positive_label_count else 0.0
    return MatchingNeedMetrics(
        need_id=need_id,
        positive_label_count=positive_label_count,
        precision_at_5=_round_metric(precision_at_5),
        ndcg_at_5=_round_metric(_ndcg(top_5, labels)),
        recall_at_10=_round_metric(recall_at_10),
        top_5_candidate_ids=top_5,
        top_5_positive_count=top_5_positive_count,
        top_10_positive_count=top_10_positive_count,
    )


def _ndcg(candidate_ids: tuple[str, ...], labels: dict[str, str], *, k: int = 5) -> float:
    ranked_gains = [GRADE_GAINS[labels[candidate_id]] for candidate_id in candidate_ids[:k]]
    ideal_gains = sorted((GRADE_GAINS[label] for label in labels.values()), reverse=True)[:k]
    dcg = sum(gain / math.log2(position + 2) for position, gain in enumerate(ranked_gains))
    ideal_dcg = sum(gain / math.log2(position + 2) for position, gain in enumerate(ideal_gains))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def _macro(values: Iterable[float]) -> float:
    values = tuple(values)
    return _round_metric(sum(values) / len(values) if values else 0.0)


def _round_metric(value: float) -> float:
    return round(value, 6)


def write_matching_metrics(path: str | Path, *, seed: str = DEFAULT_SEED) -> None:
    """Write one deterministic matching metric report."""

    Path(path).write_text(build_matching_metrics(seed=seed).to_json(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write offline matching ranking metrics")
    parser.add_argument("--output", type=Path, help="JSON output path; stdout when omitted")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    args = parser.parse_args()
    report = build_matching_metrics(seed=args.seed)
    if args.output:
        args.output.write_text(report.to_json(), encoding="utf-8")
    else:
        print(report.to_json(indent=None), end="")


if __name__ == "__main__":
    main()
