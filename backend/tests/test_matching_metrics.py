import json
from dataclasses import replace

import pytest

from app.keyword_baseline import (
    KeywordBaselineArtifact,
    KeywordBaselineCandidate,
    KeywordBaselineNeedRanking,
)
from app.matching_metrics import (
    MATCHING_METRICS_VERSION,
    build_matching_metrics,
    evaluate_keyword_baseline,
    write_matching_metrics,
)
from app.matching_validation import build_matching_relevance
from app.validation_dataset import DEFAULT_SEED


def test_matching_metrics_are_reproducible_complete_and_use_explicit_grade_semantics() -> None:
    first = build_matching_metrics(seed=DEFAULT_SEED)
    second = build_matching_metrics(seed=DEFAULT_SEED)

    assert first == second
    assert first.to_json() == second.to_json()
    assert first.matching_metrics_version == MATCHING_METRICS_VERSION
    assert first.positive_labels == ("relevant", "adjacent")
    assert first.relevance_gains == {"relevant": 2.0, "adjacent": 1.0, "not_relevant": 0.0}
    assert len(first.rankings) == 20
    assert all(len(ranking.top_5_candidate_ids) == 5 for ranking in first.rankings)
    assert 0.0 <= first.macro_precision_at_5 <= 1.0
    assert 0.0 <= first.macro_ndcg_at_5 <= 1.0
    assert 0.0 <= first.macro_recall_at_10 <= 1.0


def test_matching_metrics_follow_precision_ndcg_and_recall_contract() -> None:
    matching = build_matching_relevance()
    baseline = _small_baseline(matching)

    report = evaluate_keyword_baseline(baseline, matching)
    metrics = report.rankings[0]

    assert metrics.need_id == "synthetic-need-000"
    assert metrics.positive_label_count == 16
    assert metrics.top_5_positive_count == 3
    assert metrics.top_10_positive_count == 7
    assert metrics.precision_at_5 == 0.6
    assert metrics.recall_at_10 == round(7 / 16, 6)
    assert metrics.ndcg_at_5 == 0.740613


def test_matching_metrics_reject_incomplete_duplicate_or_misaligned_rankings() -> None:
    matching = build_matching_relevance()
    baseline = _small_baseline(matching)
    first_ranking = baseline.rankings[0]
    duplicate_result = replace(
        first_ranking,
        results=(first_ranking.results[0], first_ranking.results[0], *first_ranking.results[2:]),
    )
    with pytest.raises(ValueError, match="duplicate candidates"):
        evaluate_keyword_baseline(replace(baseline, rankings=(duplicate_result, *baseline.rankings[1:])), matching)

    with pytest.raises(ValueError, match="same dataset version"):
        evaluate_keyword_baseline(replace(baseline, seed="other-seed"), matching)


def test_matching_metrics_artifact_is_json_safe_and_pii_free(tmp_path) -> None:
    output = tmp_path / "matching-metrics.json"
    write_matching_metrics(output)

    document = json.loads(output.read_text(encoding="utf-8"))
    serialized = output.read_text(encoding="utf-8")
    assert document["seed"] == DEFAULT_SEED
    assert document["ranking_count"] == 20
    assert "expected_relevance" not in serialized
    assert "@" not in serialized
    assert "password" not in serialized
    assert all(
        candidate_id.startswith("synthetic-")
        for ranking in document["rankings"]
        for candidate_id in ranking["top_5_candidate_ids"]
    )


def _small_baseline(matching):
    candidate_ids = tuple(
        case.candidate_id for case in matching.cases if case.need_id == "synthetic-need-000"
    )
    # Deliberately put a known mix of graded labels in the top ten. The rest
    # remains a complete candidate set so the production evaluator's shape
    # checks are exercised as well.
    labels = {
        case.candidate_id: case.expected_relevance
        for case in matching.cases
        if case.need_id == "synthetic-need-000"
    }
    relevant = [candidate_id for candidate_id in candidate_ids if labels[candidate_id] == "relevant"]
    adjacent = [candidate_id for candidate_id in candidate_ids if labels[candidate_id] == "adjacent"]
    not_relevant = [
        candidate_id for candidate_id in candidate_ids if labels[candidate_id] == "not_relevant"
    ]
    prefix = relevant[:2] + adjacent[:1] + not_relevant[:2] + adjacent[1:5]
    ordered_ids = tuple(
        prefix + [candidate_id for candidate_id in candidate_ids if candidate_id not in prefix]
    )
    results = tuple(
        KeywordBaselineCandidate(
            candidate_id=candidate_id,
            score=0.0,
            matched_keywords=(),
            candidate_keyword_count=0,
            need_keyword_count=0,
        )
        for candidate_id in ordered_ids
    )
    return KeywordBaselineArtifact(
        keyword_baseline_version="test",
        matching_validation_version=matching.matching_validation_version,
        dataset_version=matching.dataset_version,
        seed=matching.seed,
        candidate_count=matching.candidate_count,
        need_count=matching.need_count,
        rankings=tuple(
            KeywordBaselineNeedRanking(
                need_id=need_id,
                results=results,
            )
            for need_id in sorted({case.need_id for case in matching.cases})
        ),
    )
