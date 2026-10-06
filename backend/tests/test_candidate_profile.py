from datetime import UTC, datetime, timedelta
from io import BytesIO

import jwt
from pypdf import PdfReader


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


def test_candidate_can_download_standardized_profile_pdf_without_protected_data(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = _headers(private_key, settings)
    _grant_processing_consent(client, candidate_headers)
    saved = client.patch(
        "/api/v1/candidate/profile",
        headers=candidate_headers,
        json={
            "display_name": "Alex Иванов",
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
            "work_preferences": {"work_mode": "hybrid", "availability": "Через месяц"},
        },
    )
    assert saved.status_code == 200

    response = client.get("/api/v1/candidate/profile/pdf", headers=candidate_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="fsp-standardized-profile.pdf"'
    assert response.content.startswith(b"%PDF-1.4")
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Alex Иванов" in text
    assert "Backend engineer" in text
    assert "Example Lab" in text
    assert "Python" in text
    assert "candidate@team.ru" not in text
    assert "assessment" in text.lower()
    assert "date of birth" not in text.lower()


def test_profile_pdf_is_candidate_scoped_and_empty_profiles_still_have_artifact(auth_context):
    client, private_key, settings = auth_context
    first_headers = _headers(private_key, settings)
    _grant_processing_consent(client, first_headers)
    client.patch(
        "/api/v1/candidate/profile",
        headers=first_headers,
        json={"display_name": "Private Candidate"},
    )

    other_headers = _headers(
        private_key,
        settings,
        sub="kc-pdf-other-candidate",
        email="other@team.ru",
    )
    other_response = client.get("/api/v1/candidate/profile/pdf", headers=other_headers)
    assert other_response.status_code == 200
    other_text = (PdfReader(BytesIO(other_response.content)).pages[0].extract_text() or "")
    assert "Private Candidate" not in other_text
    assert "Unnamed candidate" in other_text

    employer_headers = _headers(
        private_key,
        settings,
        sub="kc-pdf-employer",
        email="employer@company.ru",
        role="employer",
    )
    employer_response = client.get("/api/v1/candidate/profile/pdf", headers=employer_headers)
    assert employer_response.status_code == 403
    assert employer_response.json()["error"]["code"] == "ROLE_REQUIRED"


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
