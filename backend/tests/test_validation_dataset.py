import json

from app.validation_dataset import (
    DEFAULT_SEED,
    EXPECTED_CANDIDATE_COUNT,
    EXPECTED_NEED_COUNT,
    FRESHNESS_STATES,
    GRADE_STATES,
    GRADES,
    RELEVANCE_LABELS,
    SPECIALIZATION_SKILLS,
    generate_validation_dataset,
)


def test_validation_dataset_is_versioned_reproducible_and_json_safe() -> None:
    first = generate_validation_dataset(seed=DEFAULT_SEED)
    second = generate_validation_dataset(seed=DEFAULT_SEED)

    assert first == second
    assert first.to_json() == second.to_json()
    document = json.loads(first.to_json())
    assert document["dataset_version"] == "2026-10-09"
    assert document["candidate_count"] == EXPECTED_CANDIDATE_COUNT
    assert document["need_count"] == EXPECTED_NEED_COUNT
    assert document["relevance_label_count"] == EXPECTED_CANDIDATE_COUNT * EXPECTED_NEED_COUNT


def test_dataset_covers_required_candidate_and_evidence_states() -> None:
    dataset = generate_validation_dataset()

    assert len(dataset.candidates) == EXPECTED_CANDIDATE_COUNT
    assert len(dataset.needs) == EXPECTED_NEED_COUNT
    assert {candidate.specialization for candidate in dataset.candidates} == set(SPECIALIZATION_SKILLS)
    assert {candidate.target_grade for candidate in dataset.candidates} == set(GRADES)
    assert {candidate.grade_state for candidate in dataset.candidates} == set(GRADE_STATES)
    assert {candidate.evidence_freshness for candidate in dataset.candidates} == set(FRESHNESS_STATES)
    assert {candidate.has_fsp_history for candidate in dataset.candidates} == {True, False}
    assert all(candidate.assessment.target_grade == candidate.target_grade for candidate in dataset.candidates)
    assert all(0.05 <= candidate.assessment.ability <= 0.99 for candidate in dataset.candidates)


def test_dataset_needs_and_relevance_labels_reference_only_known_taxonomy() -> None:
    dataset = generate_validation_dataset()
    candidate_ids = {candidate.candidate_id for candidate in dataset.candidates}
    need_ids = {need.need_id for need in dataset.needs}

    assert all(need.specialization in SPECIALIZATION_SKILLS for need in dataset.needs)
    assert all(need.grade in GRADES for need in dataset.needs)
    assert all(set(need.required_skills).issubset(SPECIALIZATION_SKILLS[need.specialization]) for need in dataset.needs)
    assert all(set(need.preferred_skills).issubset(SPECIALIZATION_SKILLS[need.specialization]) for need in dataset.needs)
    assert {(label.candidate_id, label.need_id) for label in dataset.expected_relevance} == {
        (candidate_id, need_id) for need_id in need_ids for candidate_id in candidate_ids
    }
    assert {label.label for label in dataset.expected_relevance} == set(RELEVANCE_LABELS)


def test_dataset_contains_no_personal_data_or_answer_keys() -> None:
    dataset = generate_validation_dataset()
    document = dataset.to_json()

    assert "@" not in document
    assert "answer_key" not in document
    assert "password" not in document
    assert all(candidate.candidate_id.startswith("synthetic-") for candidate in dataset.candidates)
