import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(private_key, settings):
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.keycloak_issuer,
            "aud": settings.keycloak_client_id,
            "sub": "error-test-candidate",
            "email": "error-test@team.ru",
            "email_verified": True,
            "realm_access": {"roles": ["candidate"]},
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "static"},
    )
    return {"Authorization": f"Bearer {token}"}


def test_success_response_has_generated_request_id() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert uuid.UUID(response.headers["X-Request-ID"])


def test_safe_caller_request_id_is_preserved_on_error(auth_context) -> None:
    request_headers = _headers(auth_context[1], auth_context[2])
    request_headers["X-Request-ID"] = "demo-42"
    response = auth_context[0].get("/api/v1/assessments/attempts/missing", headers=request_headers)

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "demo-42"
    assert response.json() == {
        "error": {
            "code": "ASSESSMENT_ATTEMPT_NOT_FOUND",
            "message": "The assessment attempt was not found.",
            "request_id": "demo-42",
        }
    }


def test_validation_and_unknown_route_use_the_same_envelope(auth_context) -> None:
    headers = _headers(auth_context[1], auth_context[2])
    validation = auth_context[0].post("/api/v1/assessments/attempts", headers=headers, json={})
    unknown = client.get("/api/v1/does-not-exist")

    assert validation.status_code == 422
    assert validation.json()["error"]["code"] == "VALIDATION_ERROR"
    assert validation.json()["error"]["request_id"] == validation.headers["X-Request-ID"]
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert unknown.json()["error"]["request_id"] == unknown.headers["X-Request-ID"]


def test_invalid_request_id_is_replaced() -> None:
    response = client.get("/health", headers={"X-Request-ID": "bad id with spaces"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad id with spaces"
    assert uuid.UUID(response.headers["X-Request-ID"])


def test_openapi_documents_shared_error_schema_and_route_statuses() -> None:
    schema = client.get("/openapi.json").json()

    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert error_schema["required"] == ["error"]
    assert schema["paths"]["/api/v1/assessments/attempts"]["post"]["responses"]["409"]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/ErrorResponse"
    assert "422" in schema["paths"]["/api/v1/assessments/attempts"]["post"]["responses"]
    assert "503" in schema["paths"]["/health/ready"]["get"]["responses"]
