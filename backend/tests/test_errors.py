import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_success_response_has_generated_request_id() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert uuid.UUID(response.headers["X-Request-ID"])


def test_safe_caller_request_id_is_preserved_on_error() -> None:
    response = client.get("/api/v1/assessments/attempts/missing", headers={"X-Request-ID": "demo-42"})

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "demo-42"
    assert response.json() == {
        "error": {
            "code": "ASSESSMENT_ATTEMPT_NOT_FOUND",
            "message": "The assessment attempt was not found.",
            "request_id": "demo-42",
        }
    }


def test_validation_and_unknown_route_use_the_same_envelope() -> None:
    validation = client.post("/api/v1/assessments/attempts", json={})
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
