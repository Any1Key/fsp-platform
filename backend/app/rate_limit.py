"""Small, explicit HTTP rate-limit boundary for abuse-sensitive operations.

The store is deliberately bounded and process-local. Deployments with more
than one API worker must enforce the same policies at a trusted ingress or
replace this store with a shared implementation before relying on cluster-wide
quotas.
"""

from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from math import ceil
from typing import Any
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class RateLimitPolicy:
    """A method/path-specific fixed-window policy."""

    name: str
    method: str
    path: str | re.Pattern[str]
    limit: int
    window_seconds: int

    def matches(self, method: str, path: str) -> bool:
        if method.upper() != self.method:
            return False
        if isinstance(self.path, str):
            return path == self.path
        return self.path.fullmatch(path) is not None


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimitStore:
    """Thread-safe bounded fixed-window counters.

    Monotonic timestamps prevent wall-clock changes from extending or skipping
    a window. The ordered key bound prevents an attacker from growing process
    memory indefinitely by presenting many source identities.
    """

    def __init__(self, *, max_keys: int = 10_000, clock: Callable[[], float] = time.monotonic) -> None:
        if max_keys < 1:
            raise ValueError("max_keys_must_be_positive")
        self._max_keys = max_keys
        self._clock = clock
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def clear(self) -> None:
        """Clear counters, primarily for deterministic tests and demo reset."""

        with self._lock:
            self._hits.clear()

    def consume(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        if limit < 1 or window_seconds < 1:
            raise ValueError("rate_limit_parameters_must_be_positive")

        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits.get(key)
            if bucket is None:
                bucket = deque()
                self._hits[key] = bucket
            else:
                self._hits.move_to_end(key)

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if not bucket and len(self._hits) > self._max_keys:
                self._hits.popitem(last=False)

            if len(bucket) >= limit:
                retry_after = max(1, ceil(window_seconds - (now - bucket[0])))
                return RateLimitDecision(False, 0, retry_after)

            bucket.append(now)
            return RateLimitDecision(True, max(0, limit - len(bucket)), 0)


def _peer_identity(request: Request) -> str:
    """Return a one-way, non-forwarded connection identity."""

    peer = request.client.host if request.client is not None else "unknown"
    fingerprint = hashlib.sha256(peer.encode("utf-8")).hexdigest()
    return f"peer:{fingerprint}"


def _request_identity(request: Request) -> str:
    """Use a token fingerprint when present, otherwise the connection peer."""

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"token:{fingerprint}"
    return _peer_identity(request)


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return str(uuid4())


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply explicit rate limits before request bodies and dependencies run."""

    def __init__(
        self,
        app: Callable[..., Awaitable[Response]],
        *,
        policies: Iterable[RateLimitPolicy],
        store: InMemoryRateLimitStore,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self._policies = tuple(policies)
        self._store = store
        self._enabled = enabled

    def _policy_for(self, request: Request) -> RateLimitPolicy | None:
        return next(
            (
                policy
                for policy in self._policies
                if policy.matches(request.method, request.url.path)
            ),
            None,
        )

    @staticmethod
    def _headers(policy: RateLimitPolicy, remaining: int) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": str(policy.limit),
            "X-RateLimit-Remaining": str(max(0, remaining)),
        }

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not self._enabled or request.method == "OPTIONS":
            return await call_next(request)

        policy = self._policy_for(request)
        if policy is None:
            return await call_next(request)

        decision = self._store.consume(
            f"{policy.name}:{_request_identity(request)}",
            limit=policy.limit,
            window_seconds=policy.window_seconds,
        )
        headers = self._headers(policy, decision.remaining)
        if not decision.allowed:
            request_id = _request_id(request)
            headers.update(
                {
                    "Retry-After": str(decision.retry_after_seconds),
                    "X-Request-ID": request_id,
                }
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Request rate limit exceeded. Retry later.",
                        "request_id": request_id,
                    }
                },
                headers=headers,
            )

        response = await call_next(request)
        for name, value in headers.items():
            response.headers[name] = value
        return response


def build_rate_limit_policies(settings: Any) -> tuple[RateLimitPolicy, ...]:
    """Build the intentionally small policy table from runtime settings."""

    return (
        RateLimitPolicy(
            "registration-check",
            "POST",
            "/api/v1/auth/registration/check",
            settings.rate_limit_registration_per_minute,
            60,
        ),
        RateLimitPolicy(
            "assessment-create",
            "POST",
            "/api/v1/assessments/attempts",
            settings.rate_limit_assessment_per_hour,
            3600,
        ),
        RateLimitPolicy(
            "assessment-submit",
            "POST",
            re.compile(r"/api/v1/assessments/attempts/[^/]+/submit"),
            settings.rate_limit_assessment_per_hour,
            3600,
        ),
        RateLimitPolicy(
            "private-upload",
            "POST",
            re.compile(r"/api/v1/candidate/(?:resume|minor-consent-document)"),
            settings.rate_limit_uploads_per_hour,
            3600,
        ),
        RateLimitPolicy(
            "employer-invitation",
            "POST",
            "/api/v1/employer/invitations",
            settings.rate_limit_invitations_per_minute,
            60,
        ),
        RateLimitPolicy(
            "chat-message",
            "POST",
            re.compile(r"/api/v1/chat/conversations/[^/]+/messages"),
            settings.rate_limit_chat_messages_per_minute,
            60,
        ),
        RateLimitPolicy(
            "privacy-request",
            "POST",
            re.compile(r"/api/v1/candidate/privacy/(?:export|delete)"),
            settings.rate_limit_privacy_requests_per_hour,
            3600,
        ),
    )
