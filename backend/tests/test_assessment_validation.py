import json

from app.assessment_validation import (
    DEFAULT_SEED,
    GRADES,
    generate_synthetic_candidates,
    grade_collapse_details,
    grade_collapse_detected,
    run_validation,
    write_report,
)


def test_synthetic_validation_is_reproducible_and_reports_discrimination() -> None:
    first = run_validation(seed=DEFAULT_SEED, candidates_per_grade=12)
    second = run_validation(seed=DEFAULT_SEED, candidates_per_grade=12)

    assert first.to_dict() == second.to_dict()
    assert first.sample_size == 36
    assert set(first.confusion_matrix) == set(GRADES)
    assert all(set(row) == set(GRADES) for row in first.confusion_matrix.values())
    assert first.macro_f1 >= 0.75
    assert first.grade_agreement >= 0.75
    assert first.grade_collapse is False
    assert first.form_uniqueness_rate == 1.0
    assert first.equivalent_form_score_difference > 0
    assert first.retest_agreement >= 0.5
    assert 0 < first.positive_item_discrimination_rate <= 1
    assert first.mean_item_discrimination > 0
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

    details = grade_collapse_details(["Junior"] * 8 + ["Middle", "Senior"])
    assert details == {
        "collapsed": True,
        "dominant_grade": "Junior",
        "dominant_share": 0.8,
        "sample_size": 10,
        "threshold": 0.8,
    }
    assert grade_collapse_details(["Junior", "Middle", "Senior"])["collapsed"] is False


def test_grade_collapse_detector_validates_threshold_before_empty_sample() -> None:
    for threshold in (0, -0.1, 1.01):
        try:
            grade_collapse_detected([], threshold=threshold)
        except ValueError as exc:
            assert str(exc) == "grade-collapse threshold must be in (0, 1]"
        else:
            raise AssertionError("invalid grade-collapse threshold was accepted")


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


def test_validation_report_writer_persists_the_machine_readable_contract(tmp_path) -> None:
    report = run_validation(seed=DEFAULT_SEED, candidates_per_grade=4)
    output = tmp_path / "assessment-validation.json"

    write_report(report, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == report.to_dict()
    assert "synthetic-junior-000" not in output.read_text(encoding="utf-8")
    assert payload["grade_agreement"] == 0.6667
    assert payload["grade_collapse_dominant_grade"] == "Senior"
    assert payload["grade_collapse_share"] == 0.6667
    assert "mean_item_discrimination" in payload
    assert "positive_item_discrimination_rate" in payload
