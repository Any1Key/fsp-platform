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
    answers = {item.item_id: attempt.answer_keys[item.item_id] for item in attempt.items}
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


def test_career_graph_has_empty_self_scoped_state(auth_context):
    client, private_key, settings = auth_context
    candidate_a = f"graph-a-{uuid4().hex}"
    candidate_b = f"graph-b-{uuid4().hex}"
    headers_a = _headers(private_key, settings, sub=candidate_a)
    headers_b = _headers(private_key, settings, sub=candidate_b)

    response_a = client.get("/api/v1/candidate/career-graph", headers=headers_a)
    assert response_a.status_code == 200
    body_a = response_a.json()
    assert body_a["status"] == "not_started"
    assert body_a["current_position"] is None
    assert body_a["nodes"] == []
    assert body_a["paths"] == []
    assert body_a["summary"] == {
        "verified_skills": 0,
        "unconfirmed_skills": 0,
        "declared_skills": 0,
        "evidence_nodes": 0,
        "path_count": 0,
        "gap_count": 0,
    }
    assert "assessment" in body_a["next_step"].lower()

    _submit_correct_assessment(client, headers_a)
    no_fsp = client.get("/api/v1/candidate/career-graph", headers=headers_a)
    assert no_fsp.status_code == 200
    assert no_fsp.json()["status"] == "active"
    assert no_fsp.json()["paths"][0]["relation"] == "current"
    response_b = client.get("/api/v1/candidate/career-graph", headers=headers_b)
    assert response_b.status_code == 200
    assert response_b.json()["status"] == "not_started"
    assert response_b.json()["nodes"] == []


def test_career_graph_projects_evidence_and_adjacent_paths(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings, sub=f"graph-rich-{uuid4().hex}")
    _grant_processing_consent(client, headers)
    profile = client.patch(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"skills": ["Docker", "candidate-entered-skill"]},
    )
    assert profile.status_code == 200
    _submit_correct_assessment(client, headers)
    linked = client.post(
        "/api/v1/candidate/fsp-link",
        headers=headers,
        json={"fsp_id": "FSP-DEMO-001"},
    )
    assert linked.status_code == 201

    response = client.get("/api/v1/candidate/career-graph", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "career-graph-2026-10"
    assert body["status"] == "active"
    assert body["current_position"]["specialization"]["slug"] == "backend-engineering"
    assert body["current_position"]["grade"]["slug"] == "middle"
    assert body["current_position"]["grade_state"] == "verified"

    python = next(node for node in body["nodes"] if node["id"] == "skill:python")
    assert python["status"] == "verified"
    assert set(python["sources"]) == {"fsp", "platform_assessment"}
    declared = next(node for node in body["nodes"] if node["label"] == "candidate-entered-skill")
    assert declared["status"] == "declared"
    assert declared["confidence"] == 0.25

    assert any(
        path["relation"] == "next"
        and path["specialization"]["slug"] == "backend-engineering"
        and path["grade"]["slug"] == "senior"
        for path in body["paths"]
    )
    full_stack = next(
        path for path in body["paths"] if path["specialization"]["slug"] == "full-stack-engineering"
    )
    assert full_stack["relation"] == "adjacent"
    assert "TypeScript" in full_stack["gap_skills"]
    assert body["summary"]["declared_skills"] == 2
    assert "date_of_birth" not in body
    assert "answer_keys" not in body
    assert "integrity_signals" not in body


def test_career_graph_keeps_unconfirmed_grade_and_denies_employer(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = _headers(private_key, settings, sub=f"graph-unconfirmed-{uuid4().hex}")
    main.assessment_service.family_exposure.clear()
    created = client.post(
        "/api/v1/assessments/attempts",
        headers=candidate_headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Senior"},
    )
    assert created.status_code == 200
    attempt = main.assessment_service.attempts[created.json()["attempt_id"]]
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt.attempt_id}/submit",
        headers=candidate_headers,
        json={"answers": {item.item_id: 9 for item in attempt.items}},
    )
    assert submitted.status_code == 200

    response = client.get("/api/v1/candidate/career-graph", headers=candidate_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unconfirmed"
    assert body["current_position"]["grade"]["slug"] == "senior"
    assert body["current_position"]["grade_state"] == "not_confirmed"
    assert not any(path["relation"] == "next" for path in body["paths"])
    assert all(node["status"] != "verified" for node in body["nodes"] if node["kind"] == "skill")

    employer_headers = _headers(
        private_key,
        settings,
        sub=f"graph-employer-{uuid4().hex}",
        role="employer",
    )
    denied = client.get("/api/v1/candidate/career-graph", headers=employer_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"
