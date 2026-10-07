from app.assessment_validation import (
    DEFAULT_SEED,
    GRADES,
    generate_synthetic_candidates,
    grade_collapse_detected,
    run_validation,
)


def test_synthetic_validation_is_reproducible_and_reports_discrimination() -> None:
    first = run_validation(seed=DEFAULT_SEED, candidates_per_grade=12)
    second = run_validation(seed=DEFAULT_SEED, candidates_per_grade=12)

    assert first.to_dict() == second.to_dict()
    assert first.sample_size == 36
    assert set(first.confusion_matrix) == set(GRADES)
    assert all(set(row) == set(GRADES) for row in first.confusion_matrix.values())
    assert first.macro_f1 >= 0.75
    assert first.grade_collapse is False
    assert first.form_uniqueness_rate == 1.0
    assert first.equivalent_form_score_difference > 0
    assert first.retest_agreement >= 0.5
    assert set(first.critical_domain_reliability) == {
        "api_fundamentals",
        "security_operations",
    }
    assert len(first.item_metrics) == 12
    assert sum(
        metric["discrimination"] > 0 for metric in first.item_metrics.values()
    ) >= 9


def test_grade_collapse_detector_catches_degenerate_predictions() -> None:
    assert grade_collapse_detected(["Junior"] * 8 + ["Middle", "Senior"])
    assert not grade_collapse_detected(["Junior", "Middle", "Senior"] * 4)
    assert grade_collapse_detected([])


def test_synthetic_profiles_are_labeled_without_personal_data() -> None:
    candidates = generate_synthetic_candidates(seed=DEFAULT_SEED, candidates_per_grade=4)

    assert len(candidates) == 12
    assert {candidate.target_grade for candidate in candidates} == set(GRADES)
    assert all(candidate.candidate_id.startswith("synthetic-") for candidate in candidates)
    assert all(0.05 <= candidate.ability <= 0.99 for candidate in candidates)
    assert (
        sum(candidate.ability for candidate in candidates if candidate.target_grade == "Junior")
        < sum(candidate.ability for candidate in candidates if candidate.target_grade == "Middle")
        < sum(candidate.ability for candidate in candidates if candidate.target_grade == "Senior")
    )
