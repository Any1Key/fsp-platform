import pytest
from pydantic import ValidationError

from app.config import Settings
from app.security import response_security_headers


def test_security_headers_cover_api_success_and_error(auth_context):
    client, _, _ = auth_context

    success = client.get("/health")
    missing = client.get("/does-not-exist")

    expected = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin",
        "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
    }
    for response in (success, missing):
        assert response.status_code in {200, 404}
        for name, value in expected.items():
            assert response.headers[name] == value
        assert "strict-transport-security" not in response.headers


def test_production_security_policy_adds_hsts_without_changing_other_headers():
    headers = response_security_headers("production")

    assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert headers["X-Frame-Options"] == "DENY"


def test_delete_is_an_explicitly_allowed_cross_origin_method(auth_context):
    client, _, _ = auth_context

    response = client.options(
        "/api/v1/candidate/fsp-link",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "DELETE" in response.headers["access-control-allow-methods"]
    assert response.headers["x-content-type-options"] == "nosniff"

    actual = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert actual.headers["access-control-expose-headers"] == "X-Request-ID"


def test_unconfigured_origin_is_not_granted_cors_access(auth_context):
    client, _, _ = auth_context

    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_configuration_rejects_wildcards_and_paths():
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="*")
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins="https://frontend.example/app")

    settings = Settings(cors_allowed_origins="https://frontend.example/")
    assert settings.cors_origins == ["https://frontend.example"]
