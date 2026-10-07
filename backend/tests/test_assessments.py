from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.assessments import AssessmentError, AssessmentService


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


def _headers(private_key, settings, *, sub: str, role: str = "candidate"):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": f"{sub}@team.ru",
            "email_verified": True,
            "realm_access": {"roles": [role]},
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "static"},
    )
    return {"Authorization": f"Bearer {token}"}


def test_api_does_not_expose_answer_keys_and_scores_submission(auth_context) -> None:
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"api-candidate-{uuid4().hex}")
    response = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Junior"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "answer_keys" not in body
    assert all("correct_option" not in item for item in body["items"])

    # The test uses the domain service's private key only to model a completed
    # client submission; the public API never returns it.
    from app.main import assessment_service

    attempt = assessment_service.attempts[body["attempt_id"]]
    submit = client.post(
        f"/api/v1/assessments/attempts/{body['attempt_id']}/submit",
        headers=headers,
        json={"answers": attempt.answer_keys},
    )
    assert submit.status_code == 200
    assert submit.json()["score"] is not None
    assert submit.json()["grade_state"] in {"verified", "not_confirmed"}


def test_api_assessment_is_self_scoped_and_rejects_identity_override(auth_context) -> None:
    client, private_key, settings = auth_context
    candidate_a = f"assessment-a-{uuid4().hex}"
    candidate_b = f"assessment-b-{uuid4().hex}"
    headers_a = _headers(private_key, settings, sub=candidate_a)
    headers_b = _headers(private_key, settings, sub=candidate_b)

    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers_a,
        json={"specialization": "Backend Engineering", "declared_grade": "Middle"},
    )
    assert created.status_code == 200
    attempt_id = created.json()["attempt_id"]

    override = client.post(
        "/api/v1/assessments/attempts",
        headers=headers_a,
        json={
            "candidate_id": candidate_b,
            "specialization": "Backend Engineering",
            "declared_grade": "Middle",
        },
    )
    assert override.status_code == 422
    assert override.json()["error"]["code"] == "VALIDATION_ERROR"

    for method, url, kwargs in (
        (client.get, f"/api/v1/assessments/attempts/{attempt_id}", {"headers": headers_b}),
        (
            client.post,
            f"/api/v1/assessments/attempts/{attempt_id}/submit",
            {"headers": headers_b, "json": {"answers": {}}},
        ),
    ):
        response = method(url, **kwargs)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ASSESSMENT_ATTEMPT_NOT_FOUND"

    employer_headers = _headers(private_key, settings, sub=f"assessment-employer-{uuid4().hex}", role="employer")
    denied = client.get(f"/api/v1/assessments/attempts/{attempt_id}", headers=employer_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"

    anonymous = client.post(
        "/api/v1/assessments/attempts",
        json={"specialization": "Backend Engineering", "declared_grade": "Junior"},
    )
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTHORIZATION_REQUIRED"
