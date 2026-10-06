from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app import main


def _headers(private_key, settings, *, sub: str, role: str = "candidate"):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": f"{sub}@team.ru" if role == "candidate" else f"{sub}@company.ru",
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


def _create_and_submit(client, candidate_id: str, *, correct: bool):
    created = client.post(
        "/api/v1/assessments/attempts",
        json={
            "candidate_id": candidate_id,
            "specialization": "Backend Engineering",
            "declared_grade": "Middle",
        },
    )
    assert created.status_code == 200
    attempt_id = created.json()["attempt_id"]
    attempt = main.assessment_service.attempts[attempt_id]
    answers = {
        item.item_id: attempt.answer_keys[item.item_id] if correct else 9
        for item in attempt.items
    }
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/submit",
        json={"answers": answers},
    )
    assert submitted.status_code == 200
    return submitted.json()


def test_candidate_dashboard_has_empty_state_and_is_self_scoped(auth_context):
    client, private_key, settings = auth_context
    candidate_a = f"dashboard-a-{uuid4().hex}"
    candidate_b = f"dashboard-b-{uuid4().hex}"
    headers_a = _headers(private_key, settings, sub=candidate_a)
    headers_b = _headers(private_key, settings, sub=candidate_b)

    _create_and_submit(client, candidate_a, correct=True)

    dashboard_a = client.get("/api/v1/candidate/dashboard", headers=headers_a)
    assert dashboard_a.status_code == 200
    body_a = dashboard_a.json()
    assert body_a["current_assessment"]["specialization"] == "Backend Engineering"
    assert body_a["current_assessment"]["declared_grade"] == "Middle"
    assert body_a["current_assessment"]["verified_grade"] == "Middle"
    assert body_a["current_assessment"]["grade_state"] == "verified"
    assert body_a["current_assessment"]["score"] >= 70
    assert len(body_a["attempt_history"]) == 1
    assert body_a["attempt_history"][0]["status"] == "submitted"
    assert body_a["attempt_history"][0]["score"] == body_a["current_assessment"]["score"]
    assert body_a["attempt_history"][0]["created_at"]
    assert "answer_keys" not in body_a
    assert "integrity_signals" not in body_a

    dashboard_b = client.get("/api/v1/candidate/dashboard", headers=headers_b)
    assert dashboard_b.status_code == 200
    assert dashboard_b.json()["current_assessment"] is None
    assert dashboard_b.json()["attempt_history"] == []


def test_candidate_dashboard_marks_unconfirmed_grade_without_downgrading_declaration(auth_context):
    client, private_key, settings = auth_context
    candidate_id = f"dashboard-unconfirmed-{uuid4().hex}"
    headers = _headers(private_key, settings, sub=candidate_id)
    _create_and_submit(client, candidate_id, correct=False)

    response = client.get("/api/v1/candidate/dashboard", headers=headers)
    assert response.status_code == 200
    current = response.json()["current_assessment"]
    assert current["declared_grade"] == "Middle"
    assert current["verified_grade"] is None
    assert current["grade_state"] == "not_confirmed"
    assert current["score"] < 70


def test_employer_cannot_read_candidate_dashboard(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"dashboard-employer-{uuid4().hex}", role="employer")

    response = client.get("/api/v1/candidate/dashboard", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_REQUIRED"
