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


def _candidate(client, private_key, settings, *, sub: str, skills: list[str], assessed: str | None = None):
    headers = _headers(private_key, settings, sub=sub)
    privacy = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True, "publication_consent": True, "discoverable": True},
    )
    assert privacy.status_code == 200
    profile = client.patch(
        "/api/v1/candidate/profile",
        headers=headers,
        json={"display_name": sub, "headline": "Backend engineer", "skills": skills},
    )
    assert profile.status_code == 200
    if assessed is None:
        return headers

    created = client.post(
        "/api/v1/assessments/attempts",
        headers=headers,
        json={"specialization": "Backend Engineering", "declared_grade": "Middle"},
    )
    assert created.status_code == 200
    attempt = main.assessment_service.attempts[created.json()["attempt_id"]]
    answers = {
        item.item_id: attempt.answer_keys[item.item_id] if assessed == "verified" else 9
        for item in attempt.items
    }
    submitted = client.post(
        f"/api/v1/assessments/attempts/{attempt.attempt_id}/submit",
        headers=headers,
        json={"answers": answers},
    )
    assert submitted.status_code == 200
    return headers


def _employer_need(client, private_key, settings, *, sub: str):
    headers = _headers(private_key, settings, sub=sub, role="employer")
    response = client.post(
        "/api/v1/employer/hiring-need",
        headers=headers,
        json={
            "team": "Platform engineering",
            "role": "Backend engineer",
            "specialization": "backend-engineering",
            "grade": "middle",
            "required_skills": ["python", "rest-apis"],
            "preferred_skills": ["docker"],
        },
    )
    assert response.status_code == 201
    return headers


def test_talent_radar_projects_categories_scores_evidence_and_gaps(auth_context):
    client, private_key, settings = auth_context
    main.assessment_service.attempts.clear()
    main.assessment_service.history.clear()
    main.assessment_service.family_exposure.clear()

    verified_id = f"radar-verified-{uuid4().hex}"
    unconfirmed_id = f"radar-unconfirmed-{uuid4().hex}"
    hidden_id = f"radar-hidden-{uuid4().hex}"
    _candidate(client, private_key, settings, sub=verified_id, skills=["Python"], assessed="verified")
    _candidate(client, private_key, settings, sub=unconfirmed_id, skills=["Python", "REST APIs"], assessed="unconfirmed")
    hidden_headers = _headers(private_key, settings, sub=hidden_id)
    assert client.patch(
        "/api/v1/candidate/privacy",
        headers=hidden_headers,
        json={"processing_consent": True},
    ).status_code == 200
    assert client.patch(
        "/api/v1/candidate/profile",
        headers=hidden_headers,
        json={"display_name": hidden_id, "skills": ["Python", "REST APIs"]},
    ).status_code == 200

    employer = _employer_need(client, private_key, settings, sub=f"radar-employer-{uuid4().hex}")
    response = client.get("/api/v1/employer/talent-radar", headers=employer)

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot"]["id"]
    assert body["snapshot"]["filters"]["include_unconfirmed"] is True
    assert {candidate["display_name"] for candidate in body["candidates"]} == {verified_id, unconfirmed_id}
    assert body["total_candidates"] == 2
    verified = next(candidate for candidate in body["candidates"] if candidate["display_name"] == verified_id)
    unconfirmed = next(candidate for candidate in body["candidates"] if candidate["display_name"] == unconfirmed_id)
    assert verified["eligibility"] == "verified"
    assert verified["category"]["label"] == "Backend Engineering · Middle"
    assert verified["score_breakdown"]["specialization_fit"] == 20.0
    assert verified["score_breakdown"]["fsp_bonus"] == 0
    assert verified["fsp"]["history_status"] == "no_history"
    assert verified["evidence"]["required"][0]["skill"] == "python"
    assert verified["evidence"]["required"][0]["present"] is True
    assert verified["evidence"]["required"][1]["skill"] == "rest-apis"
    assert verified["evidence"]["required"][1]["present"] is False
    assert any("rest-apis" in gap for gap in verified["gaps"])
    assert unconfirmed["eligibility"] == "unconfirmed"
    assert unconfirmed["category"]["state"] == "not_confirmed"
    assert unconfirmed["confidence"]["grade"] < verified["confidence"]["grade"]
    assert "email" not in verified
    assert "date_of_birth" not in verified
    assert "participant_id" not in verified

    category = next(item for item in body["categories"] if item["key"] == "Backend Engineering · Middle")
    assert category["candidate_count"] == 2
    assert category["verified_count"] == 1
    assert category["unconfirmed_count"] == 1


def test_talent_radar_filters_and_role_need_boundaries(auth_context):
    client, private_key, settings = auth_context
    main.assessment_service.attempts.clear()
    main.assessment_service.history.clear()
    main.assessment_service.family_exposure.clear()
    verified_id = f"radar-filter-verified-{uuid4().hex}"
    unconfirmed_id = f"radar-filter-unconfirmed-{uuid4().hex}"
    _candidate(client, private_key, settings, sub=verified_id, skills=["Python"], assessed="verified")
    _candidate(client, private_key, settings, sub=unconfirmed_id, skills=["Python", "REST APIs"], assessed="unconfirmed")
    employer = _employer_need(client, private_key, settings, sub=f"radar-filter-employer-{uuid4().hex}")

    verified_only = client.get(
        "/api/v1/employer/talent-radar?include_unconfirmed=false",
        headers=employer,
    )
    assert verified_only.status_code == 200
    assert [item["display_name"] for item in verified_only.json()["candidates"]] == [verified_id]

    by_skill = client.get("/api/v1/employer/talent-radar?skill=REST%20APIs", headers=employer)
    assert by_skill.status_code == 200
    assert [item["display_name"] for item in by_skill.json()["candidates"]] == [unconfirmed_id]
    assert by_skill.json()["snapshot"]["filters"]["skill"] == "rest-apis"
    without_fsp = client.get("/api/v1/employer/talent-radar?fsp=without_history", headers=employer)
    assert without_fsp.status_code == 200
    assert without_fsp.json()["snapshot"]["filters"]["fsp"] == "without_history"
    assert len(without_fsp.json()["candidates"]) == 2
    assert without_fsp.json()["snapshot"]["candidate_ids"]

    candidate_attempt = client.get(
        "/api/v1/employer/talent-radar",
        headers=_headers(private_key, settings, sub=f"radar-candidate-{uuid4().hex}"),
    )
    assert candidate_attempt.status_code == 403
    assert candidate_attempt.json()["error"]["code"] == "ROLE_REQUIRED"

    no_need = _headers(private_key, settings, sub=f"radar-no-need-{uuid4().hex}", role="employer")
    missing_need = client.get("/api/v1/employer/talent-radar", headers=no_need)
    assert missing_need.status_code == 409
    assert missing_need.json()["error"]["code"] == "HIRING_NEED_REQUIRED_FOR_TALENT_RADAR"
