import json
from datetime import UTC, datetime, timedelta

import jwt

from app.validation_dashboard import build_validation_dashboard


def _token(private_key, settings, *, role: str, sub: str, email: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
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
    )


def test_validation_dashboard_is_stable_aggregate_and_does_not_contain_pii() -> None:
    first = build_validation_dashboard()
    second = build_validation_dashboard()

    assert first == second
    assert first["dataset"]["candidate_count"] == 80
    assert first["dataset"]["need_count"] == 20
    assert first["matching"]["ranking_count"] == 20
    assert set(first["assessment"]["confusion_matrix"]) == {"Junior", "Middle", "Senior"}
    assert first["assessment"]["form_uniqueness_rate"] == 1.0
    assert first["assessment"]["grade_collapse"] is False

    serialized = json.dumps(first, ensure_ascii=False)
    assert "@" not in serialized
    assert "answer_keys" not in serialized
    assert "expected_relevance" not in serialized
    assert "synthetic-junior-000" not in serialized


def test_validation_dashboard_endpoint_is_employer_visible_and_candidate_forbidden(auth_context) -> None:
    client, private_key, settings = auth_context
    employer_headers = {
        "Authorization": f"Bearer {_token(private_key, settings, role='employer', sub='validation-employer', email='validation@company.ru')}"
    }
    candidate_headers = {
        "Authorization": f"Bearer {_token(private_key, settings, role='candidate', sub='validation-candidate', email='validation@team.ru')}"
    }

    allowed = client.get("/api/v1/validation/dashboard", headers=employer_headers)
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload["dashboard_version"] == "2026-10-10"
    assert payload["matching"]["precision_at_5"] >= 0
    assert payload["assessment"]["confusion_matrix"]["Senior"]["Senior"] >= 0
    assert payload["assessment"]["item_metrics"]

    denied = client.get("/api/v1/validation/dashboard", headers=candidate_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ROLE_REQUIRED"


def test_validation_dashboard_requires_authentication(auth_context) -> None:
    client, _, _ = auth_context

    response = client.get("/api/v1/validation/dashboard")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHORIZATION_REQUIRED"
