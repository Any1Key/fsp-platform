import json

from app.matching_validation import (
    MATCHING_VALIDATION_VERSION,
    build_matching_relevance,
    write_matching_relevance,
)
from app.validation_dataset import DEFAULT_SEED, RELEVANCE_LABELS


def test_labeled_matching_relevance_is_reproducible_and_complete() -> None:
    first = build_matching_relevance(seed=DEFAULT_SEED)
    second = build_matching_relevance(seed=DEFAULT_SEED)

    assert first == second
    assert first.to_json() == second.to_json()
    assert first.matching_validation_version == MATCHING_VALIDATION_VERSION
    assert first.candidate_count == 80
    assert first.need_count == 20
    assert first.case_count == 1_600
    assert len({(case.candidate_id, case.need_id) for case in first.cases}) == first.case_count
    assert set(first.coverage["label_counts"]) == set(RELEVANCE_LABELS)
    assert first.coverage["actual_pair_count"] == first.coverage["expected_pair_count"]


def test_labeled_cases_preserve_matching_evidence_dimensions() -> None:
    artifact = build_matching_relevance()

    assert set(artifact.coverage["candidate_grade_states"]) == {"verified", "unconfirmed"}
    assert artifact.coverage["candidate_fsp_history"]["without_history"] > 0
    assert set(artifact.coverage["candidate_evidence_freshness"]) == {
        "fresh",
        "expiring",
        "stale",
    }
    assert all(case.required_skills for case in artifact.cases)
    assert all(case.need_specialization for case in artifact.cases)
    assert all(case.expected_relevance in RELEVANCE_LABELS for case in artifact.cases)
    assert any(case.candidate_grade_state == "unconfirmed" for case in artifact.cases)
    assert any(not case.candidate_has_fsp_history for case in artifact.cases)


def test_matching_relevance_artifact_is_json_safe_and_pii_free(tmp_path) -> None:
    output = tmp_path / "matching-relevance.json"
    write_matching_relevance(output)

    document = json.loads(output.read_text(encoding="utf-8"))
    serialized = output.read_text(encoding="utf-8")
    assert document["seed"] == DEFAULT_SEED
    assert document["case_count"] == 1_600
    assert "@" not in serialized
    assert "password" not in serialized
    assert "answer_key" not in serialized
    assert all(case["candidate_id"].startswith("synthetic-") for case in document["cases"])
