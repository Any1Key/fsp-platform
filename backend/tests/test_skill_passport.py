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


def _grant_processing_consent(client, headers):
    response = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True},
    )
    assert response.status_code == 200


def _submit_correct_assessment(client, headers):
    main.assessment_service.family_exposure.clear()
    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Middle"},
    )
    assert created.status_code == 200
    attempt_id = created.json()["attempt_id"]
    attempt = main.assessment_service.attempts[attempt_id]
    answers = {
        item.item_id: attempt.answer_keys[item.item_id]
        for item in attempt.items
    }
    followups = {
        item.item_id: "the explanation follows the constraint in the task"
        for item in attempt.items
        if item.progressive
    }
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt_id}/submit",
        headers=headers,
        json={"answers": answers, "followups": followups},
    )
    assert submitted.status_code == 200
    return submitted.json()


def test_skill_passport_has_explicit_empty_state_and_is_self_scoped(auth_context):
    client, private_key, settings = auth_context
    candidate_a = f"passport-a-{uuid4().hex}"
    candidate_b = f"passport-b-{uuid4().hex}"
    headers_a = _headers(private_key, settings, sub=candidate_a)
    headers_b = _headers(private_key, settings, sub=candidate_b)

    response_a = client.get("/api/v1/candidate/skill-passport", headers=headers_a)
    assert response_a.status_code == 200
    body_a = response_a.json()
    assert body_a["status"] == "not_started"
    assert body_a["category"] is None
    assert body_a["fsp"] == {
        "status": "not_linked",
        "history_status": "no_history",
        "achievement_count": 0,
    }
    assert body_a["evidence"] == []
    assert body_a["freshness"] == {
        "fresh": 0,
        "aging": 0,
        "stale": 0,
        "future": 0,
        "not_available": 0,
    }

    response_b = client.get("/api/v1/candidate/skill-passport", headers=headers_b)
    assert response_b.status_code == 200
    assert response_b.json()["evidence"] == []


def test_skill_passport_projects_verified_fsp_and_declared_evidence(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"passport-rich-{uuid4().hex}")
    _grant_processing_consent(client, headers)
    profile = client.patch(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"skills": ["FastAPI", "candidate-entered-skill"]},
    )
    assert profile.status_code == 200
    _submit_correct_assessment(client, headers)
    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert linked.status_code == 201

    response = client.get("/api/v1/candidate/skill-passport", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified"
    assert body["category"]["specialization"] == "Backend Engineering"
    assert body["category"]["grade"] == "Middle"
    assert body["category"]["grade_state"] == "verified"
    assert body["fsp"]["history_status"] == "has_history"
    assert body["fsp"]["achievement_count"] == 2

    sources = {item["source"] for item in body["evidence"]}
    assert sources == {"platform_assessment", "fsp", "profile"}
    platform = next(item for item in body["evidence"] if item["source"] == "platform_assessment")
    assert platform["status"] == "verified"
    assert platform["confidence"] == 1
    assert "Python" in platform["skills"]
    fsp_items = [item for item in body["evidence"] if item["source"] == "fsp"]
    assert all(item["status"] == "verified" for item in fsp_items)
    assert any("REST APIs" in item["skills"] for item in fsp_items)
    declared = [item for item in body["evidence"] if item["source"] == "profile"]
    assert all(item["status"] == "declared" and item["confidence"] == 0.25 for item in declared)
    assert "date_of_birth" not in body
    assert "answer_keys" not in body
    assert "integrity_signals" not in body


def test_skill_passport_keeps_unconfirmed_grade_visible(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"passport-unconfirmed-{uuid4().hex}")
    main.assessment_service.family_exposure.clear()
    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Senior"},
    )
    assert created.status_code == 200
    attempt = main.assessment_service.attempts[created.json()["attempt_id"]]
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt.attempt_id}/submit",
        headers=headers,
        json={"answers": {item.item_id: 9 for item in attempt.items}},
    )
    assert submitted.status_code == 200

    response = client.get("/api/v1/candidate/skill-passport", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unconfirmed"
    assert body["category"]["declared_grade"] == "Senior"
    assert body["category"]["grade"] is None
    assert body["category"]["grade_state"] == "not_confirmed"
    assessment = next(item for item in body["evidence"] if item["source"] == "platform_assessment")
    assert assessment["status"] == "unconfirmed"
    assert assessment["confidence"] == 0.5


def test_employer_cannot_read_skill_passport(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"passport-employer-{uuid4().hex}", role="employer")

    response = client.get("/api/v1/candidate/skill-passport", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_REQUIRED"
