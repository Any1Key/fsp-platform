from datetime import UTC, datetime, timedelta

import jwt


def _token(private_key, settings, *, email="candidate@team.ru", role="candidate", **overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": settings.keycloak_issuer,
        "aud": settings.keycloak_client_id,
        "sub": "kc-candidate-1",
        "email": email,
        "email_verified": True,
        "realm_access": {"roles": [role]},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "static"})


def _headers(private_key, settings, **overrides):
    return {"Authorization": f"Bearer {_token(private_key, settings, **overrides)}"}


def _grant_processing_consent(client, headers):
    response = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True},
    )
    assert response.status_code == 200


def test_candidate_profile_is_private_and_editable_after_processing_consent(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = _headers(private_key, settings)

    initial = client.get("/api/v1/candidate/profile", headers=candidate_headers)
    assert initial.status_code == 200
    assert initial.json()["display_name"] is None
    assert initial.json()["experience"] == []
    assert initial.json()["skills"] == []
    assert "email" not in initial.json()

    blocked = client.patch(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"display_name": "Иван Петров"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PROCESSING_CONSENT_REQUIRED"

    _grant_processing_consent(client, candidate_headers)
    saved = client.patch(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={
            "display_name": "Иван Петров",
            "headline": "Backend engineer",
            "location": "Москва",
            "summary": "Создаю надежные API для продуктовых команд.",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience": [
                {
                    "role": "Backend engineer",
                    "company": "Example Lab",
                    "started_on": "2023-02",
                    "ended_on": "present",
                    "description": "Разрабатывал сервисы и интеграции.",
                    "technologies": ["Python", "FastAPI"],
                }
            ],
            "work_preferences": {
                "work_mode": "hybrid",
                "employment_type": "full_time",
                "availability": "Через месяц",
            },
        },
    )
    assert saved.status_code == 200
    assert saved.json()["display_name"] == "Иван Петров"
    assert saved.json()["experience"][0]["company"] == "Example Lab"
    assert saved.json()["work_preferences"]["work_mode"] == "hybrid"
    assert saved.json()["updated_at"]

    reloaded = client.get("/api/v1/candidate/profile", headers=candidate_headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["skills"] == ["Python", "FastAPI", "PostgreSQL"]
    assert reloaded.json()["summary"] == "Создаю надежные API для продуктовых команд."


def test_profile_validation_does_not_partially_update_and_other_candidate_has_empty_scope(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = _headers(private_key, settings)
    _grant_processing_consent(client, candidate_headers)
    valid = client.patch(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"display_name": "Original"},
    )
    assert valid.status_code == 200

    invalid = client.patch(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={
            "display_name": "Should not save",
            "experience": [{"role": "Broken", "company": "Lab", "started_on": "2026-13"}],
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/api/v1/candidate/profile", headers=candidate_headers).json()["display_name"] == "Original"

    protected_field = client.patch(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={"email": "leak@example.ru"},
    )
    assert protected_field.status_code == 422
    assert protected_field.json()["error"]["code"] == "VALIDATION_ERROR"

    other_candidate = client.get(
        "/api/v1/candidate/profile",
        headers=_headers(
            private_key,
            settings,
            sub="kc-other-candidate",
            email="other@team.ru",
        ),
    )
    assert other_candidate.status_code == 200
    assert other_candidate.json()["display_name"] is None


def test_employer_cannot_read_or_update_candidate_profile(auth_context):
    client, private_key, settings = auth_context
    employer_headers = _headers(
        private_key,
        settings,
        sub="kc-profile-employer",
        email="employer@company.ru",
        role="employer",
    )
    for method, path in (
        ("get", "/api/v1/candidate/profile"),
        ("patch", "/api/v1/candidate/profile"),
    ):
        if method == "get":
            response = client.get(path, headers=employer_headers)
        else:
            response = client.patch(path, headers=employer_headers, json={"display_name": "No access"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_REQUIRED"
