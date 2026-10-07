from datetime import UTC, datetime, timedelta

import jwt


def _headers(private_key, settings, *, sub, email, role):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": sub,
            "email": email,
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


def test_employer_can_create_read_and_partially_update_current_hiring_need(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(
        private_key,
        settings,
        sub="kc-need-owner",
        email="hiring@company.ru",
        role="employer",
    )

    assert client.get("/api/v1/employer/hiring-need", headers=headers).json() is None

    created = client.post(
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
    assert created.status_code == 201
    body = created.json()
    assert body["team"] == "Platform engineering"
    assert body["specialization"] == {"slug": "backend-engineering", "name": "Backend Engineering"}
    assert body["grade"]["slug"] == "middle"
    assert {skill["slug"] for skill in body["required_skills"]} == {"python", "rest-apis"}
    assert [skill["slug"] for skill in body["preferred_skills"]] == ["docker"]

    duplicate = client.post(
        "/api/v1/employer/hiring-need",
        headers=headers,
        json={
            "team": "Other",
            "role": "Other",
            "specialization": "backend-engineering",
            "grade": "junior",
            "required_skills": ["python"],
            "preferred_skills": ["sql"],
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "HIRING_NEED_ALREADY_EXISTS"

    updated = client.patch(
        "/api/v1/employer/hiring-need",
        headers=headers,
        json={"grade": "senior", "preferred_skills": ["sql", "docker"]},
    )
    assert updated.status_code == 200
    assert updated.json()["team"] == "Platform engineering"
    assert updated.json()["grade"]["slug"] == "senior"
    assert {skill["slug"] for skill in updated.json()["preferred_skills"]} == {"sql", "docker"}

    reloaded = client.get("/api/v1/employer/hiring-need", headers=headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["role"] == "Backend engineer"


def test_hiring_need_validates_catalog_and_preference_groups_without_partial_update(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(
        private_key,
        settings,
        sub="kc-need-validation",
        email="validation@company.ru",
        role="employer",
    )
    valid = {
        "team": "Data platform",
        "role": "Data engineer",
        "specialization": "data-engineering",
        "grade": "junior",
        "required_skills": ["python"],
        "preferred_skills": ["sql"],
    }
    assert client.post("/api/v1/employer/hiring-need", headers=headers, json=valid).status_code == 201

    duplicate_skill = client.patch(
        "/api/v1/employer/hiring-need",
        headers=headers,
        json={"required_skills": ["python"], "preferred_skills": ["python"]},
    )
    assert duplicate_skill.status_code == 422
    assert duplicate_skill.json()["error"]["code"] == "HIRING_NEED_DUPLICATE_SKILL"

    unavailable_skill = client.patch(
        "/api/v1/employer/hiring-need",
        headers=headers,
        json={"required_skills": ["not-a-skill"]},
    )
    assert unavailable_skill.status_code == 422
    assert unavailable_skill.json()["error"]["code"] == "HIRING_NEED_SKILL_NOT_AVAILABLE"

    invalid_taxonomy = client.patch(
        "/api/v1/employer/hiring-need",
        headers=headers,
        json={"specialization": "not-a-specialization"},
    )
    assert invalid_taxonomy.status_code == 422
    assert invalid_taxonomy.json()["error"]["code"] == "HIRING_NEED_TAXONOMY_INVALID"

    unchanged = client.get("/api/v1/employer/hiring-need", headers=headers).json()
    assert unchanged["specialization"]["slug"] == "data-engineering"
    assert [skill["slug"] for skill in unchanged["required_skills"]] == ["python"]


def test_hiring_need_is_employer_owned_and_role_protected(auth_context):
    client, private_key, settings = auth_context
    first = _headers(private_key, settings, sub="kc-need-first", email="first@company.ru", role="employer")
    second = _headers(private_key, settings, sub="kc-need-second", email="second@company.ru", role="employer")
    candidate = _headers(private_key, settings, sub="kc-need-candidate", email="candidate@team.ru", role="candidate")

    payload = {
        "team": "Core",
        "role": "Backend engineer",
        "specialization": "backend-engineering",
        "grade": "middle",
        "required_skills": ["python"],
        "preferred_skills": ["sql"],
    }
    assert client.post("/api/v1/employer/hiring-need", headers=first, json=payload).status_code == 201
    assert client.get("/api/v1/employer/hiring-need", headers=second).json() is None

    denied_get = client.get("/api/v1/employer/hiring-need", headers=candidate)
    assert denied_get.status_code == 403
    assert denied_get.json()["error"]["code"] == "ROLE_REQUIRED"
    denied_post = client.post("/api/v1/employer/hiring-need", headers=candidate, json=payload)
    assert denied_post.status_code == 403
    assert denied_post.json()["error"]["code"] == "ROLE_REQUIRED"
