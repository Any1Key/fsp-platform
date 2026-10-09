import json
from dataclasses import replace

from app.keyword_baseline import (
    KEYWORD_BASELINE_VERSION,
    build_keyword_baseline,
    rank_keyword_baseline,
    write_keyword_baseline,
)
from app.matching_validation import build_matching_relevance
from app.validation_dataset import DEFAULT_SEED


def test_keyword_baseline_is_reproducible_and_complete() -> None:
    first = build_keyword_baseline(seed=DEFAULT_SEED)
    second = build_keyword_baseline(seed=DEFAULT_SEED)

    assert first == second
    assert first.to_json() == second.to_json()
    assert first.keyword_baseline_version == KEYWORD_BASELINE_VERSION
    assert first.candidate_count == 80
    assert first.need_count == 20
    assert len(first.rankings) == 20
    assert all(len(ranking.results) == 80 for ranking in first.rankings)
    assert all(
        (-left.score, left.candidate_id) <= (-right.score, right.candidate_id)
        for ranking in first.rankings
        for left, right in zip(ranking.results, ranking.results[1:])
    )


def test_keyword_baseline_uses_skill_jaccard_and_stable_ties() -> None:
    artifact = build_matching_relevance()
    ranking = next(
        item for item in rank_keyword_baseline(artifact).rankings if item.need_id == "synthetic-need-000"
    )
    by_id = {result.candidate_id: result for result in ranking.results}

    # Candidate 000 has three of the four keywords for the backend need.
    assert by_id["synthetic-candidate-000"].matched_keywords == ("python", "rest-apis", "sql")
    assert by_id["synthetic-candidate-000"].score == 0.75
    assert by_id["synthetic-candidate-000"].candidate_keyword_count == 3
    assert by_id["synthetic-candidate-000"].need_keyword_count == 4

    zero_score_ids = [result.candidate_id for result in ranking.results if result.score == 0]
    assert zero_score_ids == sorted(zero_score_ids)


def test_keyword_baseline_does_not_consume_labels_or_evidence_dimensions() -> None:
    artifact = build_matching_relevance()
    changed_cases = tuple(
        replace(
            case,
            expected_relevance="relevant" if case.expected_relevance == "not_relevant" else "not_relevant",
            candidate_grade="Senior",
            candidate_grade_state="verified",
            candidate_evidence_freshness="fresh",
            candidate_has_fsp_history=not case.candidate_has_fsp_history,
            candidate_specialization="backend-engineering",
        )
        for case in artifact.cases
    )
    changed_artifact = replace(artifact, cases=changed_cases)

    assert rank_keyword_baseline(artifact) == rank_keyword_baseline(changed_artifact)


def test_keyword_baseline_artifact_is_json_safe_and_pii_free(tmp_path) -> None:
    output = tmp_path / "keyword-baseline.json"
    write_keyword_baseline(output)

    document = json.loads(output.read_text(encoding="utf-8"))
    serialized = output.read_text(encoding="utf-8")
    assert document["seed"] == DEFAULT_SEED
    assert document["ranking_count"] == 20
    assert len(document["rankings"]) == 20
    assert "expected_relevance" not in serialized
    assert "@" not in serialized
    assert "password" not in serialized
    assert all(
        result["candidate_id"].startswith("synthetic-")
        for ranking in document["rankings"]
        for result in ranking["results"]
    )
