from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.assessments import AssessmentError, AssessmentService
from app.main import app


def test_forms_are_unique_and_keep_same_competency_shape() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    first = service.create_attempt("candidate-a", "Backend Engineering", "Middle")
    service.now += timedelta(days=91)
    second = service.create_attempt("candidate-a", "Backend Engineering", "Middle")

    assert first.attempt_id != second.attempt_id
    assert {item.domain for item in first.items} == {item.domain for item in second.items}
    assert {item.artifact for item in first.items}.isdisjoint({item.artifact for item in second.items})
    assert any(a.prompt != b.prompt for a, b in zip(first.items, second.items))


def test_retest_is_locked_and_failed_declared_grade_is_not_downgraded() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    attempt = service.create_attempt("candidate-b", "Backend Engineering", "Senior")
    result = service.submit(attempt.attempt_id, {item.item_id: 9 for item in attempt.items})

    assert result.grade_state == "not_confirmed"
    assert result.declared_grade == "Senior"
    with pytest.raises(AssessmentError, match="retest_locked"):
        service.create_attempt("candidate-b", "Backend Engineering", "Senior")


def test_progressive_followup_and_integrity_signal_are_advisory() -> None:
    service = AssessmentService(now=datetime(2026, 10, 6, tzinfo=UTC))
    attempt = service.create_attempt("candidate-c", "Backend Engineering", "Middle")
    answers = attempt.answer_keys.copy()
    followups = {item.item_id: "candidate rationale" for item in attempt.items if item.progressive}
    result = service.submit(attempt.attempt_id, answers, followups, telemetry={"paste_chars": 2000})

    assert result.score > 70
    assert result.grade_state == "verified"
    assert result.integrity_signals == ["large_paste_review"]


def test_api_does_not_expose_answer_keys_and_scores_submission() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/assessments/attempts", json={"candidate_id": "api-candidate", "specialization": "Backend Engineering", "declared_grade": "Junior"})
    assert response.status_code == 200
    body = response.json()
    assert "answer_keys" not in body
    assert all("correct_option" not in item for item in body["items"])

    # The test uses the domain service's private key only to model a completed
    # client submission; the public API never returns it.
    from app.main import assessment_service

    attempt = assessment_service.attempts[body["attempt_id"]]
    submit = client.post(f"/api/v1/assessments/attempts/{body['attempt_id']}/submit", json={"answers": attempt.answer_keys})
    assert submit.status_code == 200
    assert submit.json()["score"] is not None
    assert submit.json()["grade_state"] in {"verified", "not_confirmed"}
