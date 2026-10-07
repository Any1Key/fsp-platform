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


def test_employer_company_profile_is_owned_editable_and_persisted(auth_context):
    client, private_key, settings = auth_context
    employer_headers = _headers(
        private_key,
        settings,
        sub="kc-company-owner",
        email="owner@company.ru",
        role="employer",
    )

    initial = client.get("/api/v1/employer/company", headers=employer_headers)
    assert initial.status_code == 200
    assert initial.json()["name"] is None
    assert initial.json()["public_contact_method"] is None
    company_id = initial.json()["id"]

    saved = client.patch(
        "/api/v1/employer/company",
        headers=employer_headers,
        json={
            "name": "North Star Labs",
            "description": "Product engineering for resilient services.",
            "industry": "Software development",
            "website": "https://northstar.example.ru",
            "location": "Москва",
            "public_contact_method": "Hiring team · @northstar_hiring",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["id"] == company_id
    assert saved.json()["name"] == "North Star Labs"

    partial = client.patch(
        "/api/v1/employer/company",
        headers=employer_headers,
        json={"description": "Updated description"},
    )
    assert partial.status_code == 200
    assert partial.json()["name"] == "North Star Labs"
    assert partial.json()["description"] == "Updated description"

    reloaded = client.get("/api/v1/employer/company", headers=employer_headers)
    assert reloaded.status_code == 200
    assert reloaded.json()["website"] == "https://northstar.example.ru"
    assert reloaded.json()["location"] == "Москва"


def test_company_profile_requires_name_and_rejects_invalid_input_without_partial_update(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(
        private_key,
        settings,
        sub="kc-company-validation",
        email="validation@company.ru",
        role="employer",
    )

    missing_name = client.patch(
        "/api/v1/employer/company",
        headers=headers,
        json={"industry": "Software"},
    )
    assert missing_name.status_code == 422
    assert missing_name.json()["error"]["code"] == "COMPANY_NAME_REQUIRED"

    invalid_website = client.patch(
        "/api/v1/employer/company",
        headers=headers,
        json={"name": "Valid name", "website": "javascript:alert(1)"},
    )
    assert invalid_website.status_code == 422
    assert invalid_website.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/api/v1/employer/company", headers=headers).json()["name"] is None

    empty_update = client.patch("/api/v1/employer/company", headers=headers, json={})
    assert empty_update.status_code == 422
    assert empty_update.json()["error"]["code"] == "COMPANY_PROFILE_UPDATE_REQUIRED"


def test_company_profile_is_role_and_identity_scoped(auth_context):
    client, private_key, settings = auth_context
    first = _headers(
        private_key,
        settings,
        sub="kc-company-first",
        email="first@company.ru",
        role="employer",
    )
    second = _headers(
        private_key,
        settings,
        sub="kc-company-second",
        email="second@company.ru",
        role="employer",
    )
    candidate = _headers(
        private_key,
        settings,
        sub="kc-company-candidate",
        email="candidate@team.ru",
        role="candidate",
    )

    assert client.patch(
        "/api/v1/employer/company",
        headers=first,
        json={"name": "First company"},
    ).status_code == 200
    assert client.get("/api/v1/employer/company", headers=second).json()["name"] is None

    denied_get = client.get("/api/v1/employer/company", headers=candidate)
    assert denied_get.status_code == 403
    assert denied_get.json()["error"]["code"] == "ROLE_REQUIRED"
    denied_patch = client.patch(
        "/api/v1/employer/company",
        headers=candidate,
        json={"name": "No access"},
    )
    assert denied_patch.status_code == 403
    assert denied_patch.json()["error"]["code"] == "ROLE_REQUIRED"
