from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.main import app as api_app
from app.rate_limit import (
    InMemoryRateLimitStore,
    RateLimitMiddleware,
    RateLimitPolicy,
    _request_identity,
)


def test_fixed_window_store_expires_hits_and_returns_retry_after():
    now = [100.0]
    store = InMemoryRateLimitStore(clock=lambda: now[0])

    assert store.consume("key", limit=2, window_seconds=10).remaining == 1
    assert store.consume("key", limit=2, window_seconds=10).remaining == 0
    blocked = store.consume("key", limit=2, window_seconds=10)
    assert not blocked.allowed
    assert blocked.retry_after_seconds == 10

    now[0] += 10
    assert store.consume("key", limit=2, window_seconds=10).allowed


def test_store_key_bound_is_enforced():
    store = InMemoryRateLimitStore(max_keys=2)

    for key in ("one", "two", "three", "four"):
        assert store.consume(key, limit=1, window_seconds=60).allowed

    assert len(store._hits) <= 2


def test_bearer_identity_is_a_non_reversible_fingerprint():
    app = FastAPI()

    @app.post("/limited")
    async def limited(request: Request):
        return {"identity": _request_identity(request)}

    with TestClient(app) as client:
        response = client.post("/limited", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    identity = response.json()["identity"]
    assert identity.startswith("token:")
    assert "secret-token" not in identity
    assert len(identity) == len("token:") + 64


def test_peer_identity_is_a_non_reversible_fingerprint():
    app = FastAPI()

    @app.post("/limited")
    async def limited(request: Request):
        return {"identity": _request_identity(request)}

    with TestClient(app) as client:
        response = client.post("/limited")

    assert response.status_code == 200
    identity = response.json()["identity"]
    assert identity.startswith("peer:")
    assert "testclient" not in identity
    assert len(identity) == len("peer:") + 64


def test_middleware_returns_common_429_contract_and_does_not_limit_other_routes():
    app = FastAPI()
    store = InMemoryRateLimitStore()
    policy = RateLimitPolicy("test", "POST", "/limited", 1, 60)
    app.add_middleware(RateLimitMiddleware, policies=(policy,), store=store)

    @app.post("/limited")
    async def limited():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    with TestClient(app) as client:
        first = client.post("/limited", headers={"X-Request-ID": "rate-test"})
        second = client.post("/limited", headers={"X-Request-ID": "rate-test"})
        health = client.get("/health")

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "1"
    assert first.headers["X-RateLimit-Remaining"] == "0"
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
    assert second.headers["X-Request-ID"]
    assert second.json() == {
        "error": {
            "code": "RATE_LIMITED",
            "message": "Request rate limit exceeded. Retry later.",
            "request_id": second.headers["X-Request-ID"],
        }
    }
    assert health.status_code == 200


def test_registration_probe_is_limited_without_affecting_health(auth_context):
    client, _, _ = auth_context

    responses = [
        client.post(
            "/api/v1/auth/registration/check",
            json={"email": "candidate@team.ru", "role": "candidate"},
        )
        for _ in range(11)
    ]

    assert [response.status_code for response in responses[:10]] == [200] * 10
    limited = responses[-1]
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert limited.json()["error"]["request_id"] == limited.headers["X-Request-ID"]
    assert client.get("/health").status_code == 200


def test_rate_limited_routes_publish_429_in_openapi():
    schema = TestClient(api_app).get("/openapi.json").json()

    for path, method in (
        ("/api/v1/auth/registration/check", "post"),
        ("/api/v1/candidate/resume", "post"),
        ("/api/v1/employer/invitations", "post"),
        ("/api/v1/chat/conversations/{conversation_id}/messages", "post"),
        ("/api/v1/candidate/privacy/export", "post"),
        ("/api/v1/candidate/privacy/delete", "post"),
        ("/api/v1/assessments/attempts", "post"),
        ("/api/v1/assessments/attempts/{attempt_id}/submit", "post"),
    ):
        assert "429" in schema["paths"][path][method]["responses"]
