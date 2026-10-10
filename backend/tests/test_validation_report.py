import json
from pathlib import Path

from app.assessment_validation import run_validation
from app.matching_metrics import build_matching_metrics
from app.validation_dataset import DEFAULT_SEED as DEFAULT_DATASET_SEED
from app.validation_report import (
    VALIDATION_REPORT_VERSION,
    build_validation_report,
    write_validation_report,
)


def test_validation_report_is_reproducible_complete_and_aggregate_only() -> None:
    first = build_validation_report()
    second = build_validation_report()

    assert first == second
    assert first.to_json() == second.to_json()
    assert first.report_version == VALIDATION_REPORT_VERSION
    assert first.status == "MEASURED_SYNTHETIC"
    assert first.dataset["seed"] == DEFAULT_DATASET_SEED
    assert first.dataset["labeled_pair_count"] == 1_600
    assert first.matching["precision_at_5"] == build_matching_metrics().macro_precision_at_5
    assert first.assessment["macro_f1"] == run_validation().macro_f1
    assert first.assessment["sample_size"] == 72
    assert first.assessment["grade_collapse"] is False

    serialized = first.to_json()
    assert "@" not in serialized
    assert "synthetic-candidate-" not in serialized
    assert "synthetic-junior-" not in serialized
    assert "expected_relevance" not in serialized
    assert "answer_key" not in serialized
    assert "submission_text" not in serialized


def test_validation_report_writer_round_trips_machine_readable_evidence(tmp_path) -> None:
    output = tmp_path / "validation-results.json"

    write_validation_report(output)

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document == build_validation_report().to_dict()
    assert document["dataset"]["coverage"]["actual_pair_count"] == 1_600
    assert document["matching"]["ranking_count"] == 20
    assert set(document["assessment"]["confusion_matrix"]) == {
        "Junior",
        "Middle",
        "Senior",
    }
    assert document["evidence_boundary"]


def test_committed_validation_results_match_the_current_generator() -> None:
    # The host checkout has ``backend/tests`` below the repository root, while
    # the backend image has ``tests`` directly below its /app workdir. Keep
    # this contract valid in both layouts instead of silently testing a path
    # that only exists on the host.
    test_file = Path(__file__).resolve()
    candidates = (
        test_file.parents[2] / "docs" / "VALIDATION_RESULTS.json",
        test_file.parents[1] / "docs" / "VALIDATION_RESULTS.json",
    )
    artifact = next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    assert artifact.exists()
    assert json.loads(artifact.read_text(encoding="utf-8")) == build_validation_report().to_dict()


def test_validation_report_can_use_separate_sensitivity_seeds() -> None:
    report = build_validation_report(
        dataset_seed="validation-sensitivity-dataset",
        assessment_seed="validation-sensitivity-assessment",
    )

    assert report.dataset["seed"] == "validation-sensitivity-dataset"
    assert report.matching["seed"] == "validation-sensitivity-dataset"
    assert report.assessment["seed"] == "validation-sensitivity-assessment"
    assert report.dataset["labeled_pair_count"] == 1_600
