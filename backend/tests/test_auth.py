from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, text

from app.config import Settings


def _token(private_key, settings: Settings, *, email="candidate@team.ru", role="candidate", **overrides):
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


def test_registration_check_enforces_exact_ru_domain(auth_context):
    client, _, _ = auth_context

    allowed = client.post(
        "/api/v1/auth/registration/check",
        json={"email": " Person@Company.RU ", "role": "candidate"},
    )
    assert allowed.status_code == 200
    assert allowed.json() == {"allowed": True, "email": "person@company.ru", "role": "candidate"}

    for email in ("person@example.com", "person@ru", "person@company.ru.example", "@company.ru"):
        rejected = client.post(
            "/api/v1/auth/registration/check",
            json={"email": email, "role": "employer"},
        )
        assert rejected.status_code == 403
        assert rejected.json()["error"]["code"] == "REGISTRATION_DOMAIN_NOT_ALLOWED"


def test_frontend_origin_can_preflight_bearer_session_request(auth_context):
    client, _, _ = auth_context

    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_valid_keycloak_token_provisions_identity_once_and_returns_session(auth_context):
    client, private_key, settings = auth_context
    headers = {"Authorization": f"Bearer {_token(private_key, settings)}"}

    first = client.get("/api/v1/auth/me", headers=headers)
    second = client.get("/api/v1/auth/me", headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json()["email"] == "candidate@team.ru"
    assert first.json()["role"] == "candidate"
    assert first.json()["identity_id"] == second.json()["identity_id"]


def test_verified_no_role_account_can_complete_one_time_role_onboarding(auth_context):
    client, private_key, settings = auth_context
    token = _token(
        private_key,
        settings,
        sub="kc-onboarding-candidate",
        email="new-candidate@team.ru",
        realm_access={"roles": []},
    )
    headers = {"Authorization": f"Bearer {token}"}

    pending = client.get("/api/v1/auth/me", headers=headers)
    assert pending.status_code == 200
    assert pending.json() == {
        "identity_id": None,
        "keycloak_sub": "kc-onboarding-candidate",
        "email": "new-candidate@team.ru",
        "role": "pending",
        "email_verified": True,
        "onboarding_required": True,
    }
    assert client.get("/api/v1/candidate/context", headers=headers).status_code == 403
    assert client.get("/api/v1/employer/context", headers=headers).status_code == 403

    completed = client.post("/api/v1/auth/onboarding/role", headers=headers, json={"role": "candidate"})
    assert completed.status_code == 200
    assert completed.json()["role"] == "candidate"
    assert completed.json()["onboarding_required"] is False
    identity_id = completed.json()["identity_id"]

    # The same request is safe to replay, but switching the bound role is not.
    replay = client.post("/api/v1/auth/onboarding/role", headers=headers, json={"role": "candidate"})
    assert replay.status_code == 200
    assert replay.json()["identity_id"] == identity_id
    switched = client.post("/api/v1/auth/onboarding/role", headers=headers, json={"role": "employer"})
    assert switched.status_code == 409
    assert switched.json()["error"]["code"] == "IDENTITY_ROLE_CONFLICT"

    resolved = client.get("/api/v1/auth/me", headers=headers)
    assert resolved.status_code == 200
    assert resolved.json()["role"] == "candidate"
    assert client.get("/api/v1/candidate/context", headers=headers).status_code == 200
    assert client.get("/api/v1/employer/context", headers=headers).status_code == 403

    conflicting_keycloak_role = _token(
        private_key,
        settings,
        sub="kc-onboarding-candidate",
        email="new-candidate@team.ru",
        role="employer",
    )
    conflict = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {conflicting_keycloak_role}"},
    )
    assert conflict.status_code == 403
    assert conflict.json()["error"]["code"] == "IDENTITY_ROLE_CONFLICT"


def test_missing_or_invalid_token_is_rejected_without_leaking_claims(auth_context):
    client, private_key, settings = auth_context

    missing = client.get("/api/v1/auth/me")
    assert missing.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"
    assert missing.json()["error"]["code"] == "AUTHORIZATION_REQUIRED"

    invalid = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"

    expired = _token(
        private_key,
        settings,
        iat=int((datetime.now(UTC) - timedelta(minutes=10)).timestamp()),
        exp=int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"

    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad_signature = _token(wrong_key, settings)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_signature}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"


def test_issuer_audience_email_and_role_claims_are_enforced(auth_context):
    client, private_key, settings = auth_context

    cases = (
        ({"iss": "https://other.test/realms/fsp"}, "INVALID_ACCESS_TOKEN", 401),
        ({"aud": "other-client"}, "INVALID_ACCESS_TOKEN", 401),
        ({"email_verified": False}, "EMAIL_NOT_VERIFIED", 403),
        ({"email": "candidate@example.com"}, "REGISTRATION_DOMAIN_NOT_ALLOWED", 403),
        ({"realm_access": {"roles": ["candidate", "employer"]}}, "UNSUPPORTED_ROLE", 403),
        ({"realm_access": {"roles": ["unknown"]}}, "UNSUPPORTED_ROLE", 403),
    )
    for overrides, code, status_code in cases:
        token = _token(private_key, settings, **overrides)
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status_code
        assert response.json()["error"]["code"] == code


def test_role_contexts_are_server_side_and_do_not_cross_access(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = {"Authorization": f"Bearer {_token(private_key, settings)}"}
    employer_headers = {
        "Authorization": f"Bearer {_token(private_key, settings, sub='kc-employer-1', email='employer@company.ru', role='employer')}"
    }

    assert client.get("/api/v1/candidate/context", headers=candidate_headers).status_code == 200
    assert client.get("/api/v1/employer/context", headers=employer_headers).status_code == 200
    denied = client.get("/api/v1/employer/context", headers=candidate_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"

    client_role_token = _token(
        private_key,
        settings,
        sub="kc-client-role-1",
        email="client-role@company.ru",
        realm_access={"roles": []},
        resource_access={"fsp-web": {"roles": ["employer"]}},
    )
    client_role = client.get(
        "/api/v1/employer/context",
        headers={"Authorization": f"Bearer {client_role_token}"},
    )
    assert client_role.status_code == 200

    engine = create_engine(auth_context[2].database_url)
    try:
        with engine.connect() as connection:
            identities = connection.execute(text("SELECT email, role FROM user_identity ORDER BY email")).all()
    finally:
        engine.dispose()
    assert identities == [
        ("candidate@team.ru", "candidate"),
        ("client-role@company.ru", "employer"),
        ("employer@company.ru", "employer"),
    ]


def test_candidate_privacy_requires_consent_and_records_safe_audit(auth_context):
    client, private_key, settings = auth_context
    headers = {"Authorization": f"Bearer {_token(private_key, settings)}"}

    initial = client.get("/api/v1/candidate/privacy", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "processing_consent": False,
        "processing_consent_version": None,
        "processing_consent_at": None,
        "publication_consent": False,
        "publication_consent_version": None,
        "publication_consent_at": None,
        "discoverable": False,
    }

    publication_without_processing = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"publication_consent": True},
    )
    assert publication_without_processing.status_code == 409
    assert publication_without_processing.json()["error"]["code"] == "PROCESSING_CONSENT_REQUIRED"

    granted = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": True, "publication_consent": True, "discoverable": True},
    )
    assert granted.status_code == 200
    assert granted.json()["processing_consent"] is True
    assert granted.json()["publication_consent"] is True
    assert granted.json()["discoverable"] is True
    assert granted.json()["processing_consent_version"] == "2026-10-06"
    assert granted.json()["publication_consent_version"] == "2026-10-06"
    assert granted.json()["processing_consent_at"]
    assert granted.json()["publication_consent_at"]
    unchanged_consent = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"discoverable": True},
    )
    assert unchanged_consent.status_code == 200
    assert unchanged_consent.json()["processing_consent_at"] == granted.json()["processing_consent_at"]
    assert unchanged_consent.json()["publication_consent_at"] == granted.json()["publication_consent_at"]

    export = client.post("/api/v1/candidate/privacy/export", headers=headers)
    assert export.status_code == 202
    assert export.json()["request_type"] == "export"
    assert export.json()["status"] == "requested"

    withdrawn = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"processing_consent": False},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["processing_consent"] is False
    assert withdrawn.json()["publication_consent"] is False
    assert withdrawn.json()["discoverable"] is False

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            audit = connection.execute(
                text("SELECT event_type, details FROM audit_event ORDER BY occurred_at, id")
            ).all()
            privacy_requests = connection.execute(
                text("SELECT request_type, status FROM privacy_request")
            ).all()
    finally:
        engine.dispose()
    assert sorted(event[0] for event in audit) == sorted([
        "processing_consent_granted",
        "publication_consent_granted",
        "discoverability_changed",
        "privacy_export_requested",
        "processing_consent_withdrawn",
        "publication_consent_withdrawn",
        "discoverability_changed",
    ])
    assert all("candidate@team.ru" not in event[1] for event in audit)
    assert privacy_requests == [("export", "requested")]


def test_candidate_privacy_requests_are_scoped_idempotent_and_deletion_withdraws_immediately(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = {"Authorization": f"Bearer {_token(private_key, settings)}"}

    granted = client.patch(
        "/api/v1/candidate/privacy",
        headers=candidate_headers,
        json={"processing_consent": True, "publication_consent": True, "discoverable": True},
    )
    assert granted.status_code == 200

    initial = client.get("/api/v1/candidate/privacy/requests", headers=candidate_headers)
    assert initial.status_code == 200
    assert initial.json() == {"requests": []}

    first_export = client.post("/api/v1/candidate/privacy/export", headers=candidate_headers)
    retry_export = client.post("/api/v1/candidate/privacy/export", headers=candidate_headers)
    assert first_export.status_code == retry_export.status_code == 202
    assert first_export.json() == retry_export.json()
    assert first_export.json()["scheduled_for"]

    deletion = client.post("/api/v1/candidate/privacy/delete", headers=candidate_headers)
    retry_deletion = client.post("/api/v1/candidate/privacy/delete", headers=candidate_headers)
    assert deletion.status_code == retry_deletion.status_code == 202
    assert deletion.json() == retry_deletion.json()
    assert deletion.json()["request_type"] == "deletion"
    assert deletion.json()["scheduled_for"]

    withdrawn = client.get("/api/v1/candidate/privacy", headers=candidate_headers)
    assert withdrawn.status_code == 200
    assert withdrawn.json()["processing_consent"] is False
    assert withdrawn.json()["publication_consent"] is False
    assert withdrawn.json()["discoverable"] is False

    requests = client.get("/api/v1/candidate/privacy/requests", headers=candidate_headers)
    assert requests.status_code == 200
    assert {item["request_type"] for item in requests.json()["requests"]} == {"export", "deletion"}
    assert all(item["status"] == "requested" for item in requests.json()["requests"])

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            audit = connection.execute(
                text("SELECT event_type, details FROM audit_event ORDER BY occurred_at, id")
            ).all()
    finally:
        engine.dispose()
    event_types = [event[0] for event in audit]
    assert event_types.count("privacy_export_requested") == 1
    assert event_types.count("privacy_deletion_requested") == 1
    assert event_types.count("processing_consent_withdrawn") == 1
    assert event_types.count("publication_consent_withdrawn") == 1
    assert event_types.count("discoverability_changed") == 2
    assert all("candidate@team.ru" not in event[1] for event in audit)


def test_employer_cannot_read_or_create_privacy_requests(auth_context):
    client, private_key, settings = auth_context
    headers = {
        "Authorization": f"Bearer {_token(private_key, settings, sub='kc-employer-lifecycle', email='employer@company.ru', role='employer')}"
    }

    for method, path in (
        ("get", "/api/v1/candidate/privacy/requests"),
        ("post", "/api/v1/candidate/privacy/delete"),
    ):
        response = getattr(client, method)(path, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_REQUIRED"


def test_employer_cannot_read_or_change_candidate_privacy(auth_context):
    client, private_key, settings = auth_context
    headers = {
        "Authorization": f"Bearer {_token(private_key, settings, sub='kc-employer-privacy', email='employer@company.ru', role='employer')}"
    }

    for method, path in (("get", "/api/v1/candidate/privacy"), ("post", "/api/v1/candidate/privacy/export")):
        response = getattr(client, method)(path, headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_REQUIRED"

    response = client.patch(
        "/api/v1/candidate/privacy",
        headers=headers,
        json={"discoverable": True},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_REQUIRED"
