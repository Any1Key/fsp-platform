from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import create_engine, text


def _token(private_key, settings, *, email="candidate@team.ru", role="candidate", **overrides):
    now = datetime.now(UTC)
    claims = {
        "iss": settings.keycloak_issuer,
        "aud": settings.keycloak_client_id,
        "sub": "kc-protected-candidate",
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


def test_candidate_can_manage_private_dob_and_server_derived_minor_state(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings)

    initial = client.get("/api/v1/candidate/protected-profile", headers=headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "date_of_birth": None,
        "minor_state": "not_set",
        "adult_age_years": 18,
    }
    assert "date_of_birth" not in client.get("/api/v1/candidate/profile", headers=headers).json()

    blocked = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "2010-10-07"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "PROCESSING_CONSENT_REQUIRED"

    _grant_processing_consent(client, headers)
    minor = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "2010-10-07"},
    )
    assert minor.status_code == 200
    assert minor.json()["date_of_birth"] == "2010-10-07"
    assert minor.json()["minor_state"] == "minor"

    adult = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "1990-10-07"},
    )
    assert adult.status_code == 200
    assert adult.json()["minor_state"] == "adult"

    cleared = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["minor_state"] == "not_set"


def test_protected_dob_validates_without_partial_update_and_audits_only_state(auth_context):
    client, private_key, settings = auth_context
    headers = _headers(private_key, settings)
    _grant_processing_consent(client, headers)
    saved = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": "2010-10-07"},
    )
    assert saved.status_code == 200

    future = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    invalid = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=headers,
        json={"date_of_birth": future},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "DATE_OF_BIRTH_IN_FUTURE"
    assert client.get("/api/v1/candidate/protected-profile", headers=headers).json()["date_of_birth"] == "2010-10-07"

    missing = client.patch("/api/v1/candidate/protected-profile", headers=headers, json={})
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "VALIDATION_ERROR"

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            audit = connection.execute(
                text("SELECT event_type, details FROM audit_event ORDER BY occurred_at, id")
            ).all()
    finally:
        engine.dispose()
    age_state_events = [event for event in audit if event[0] == "protected_age_state_changed"]
    assert len(age_state_events) == 1
    assert '"from":"not_set"' in age_state_events[0][1]
    assert '"to":"minor"' in age_state_events[0][1]
    assert "2010-10-07" not in age_state_events[0][1]
    assert "candidate@team.ru" not in age_state_events[0][1]


def test_protected_dob_is_self_scoped_and_employer_forbidden(auth_context):
    client, private_key, settings = auth_context
    candidate_headers = _headers(private_key, settings)
    _grant_processing_consent(client, candidate_headers)
    saved = client.patch(
        "/api/v1/candidate/protected-profile",
        headers=candidate_headers,
        json={"date_of_birth": "2010-10-07"},
    )
    assert saved.status_code == 200

    other = client.get(
        "/api/v1/candidate/protected-profile",
        headers=_headers(private_key, settings, sub="kc-other-protected", email="other@team.ru"),
    )
    assert other.status_code == 200
    assert other.json()["date_of_birth"] is None

    employer_headers = _headers(
        private_key,
        settings,
        sub="kc-protected-employer",
        email="employer@company.ru",
        role="employer",
    )
    for method in ("get", "patch"):
        response = getattr(client, method)(
            "/api/v1/candidate/protected-profile",
            headers=employer_headers,
            **({"json": {"date_of_birth": "2010-10-07"}} if method == "patch" else {}),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_REQUIRED"
