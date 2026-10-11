"""HTTP security boundary shared by API responses."""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def response_security_headers(app_env: str) -> dict[str, str]:
    """Return safe browser defaults without forcing local HTTP to HTTPS."""

    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    }
    if app_env.lower() == "production":
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply the API browser policy to normal, error, and preflight responses."""

    def __init__(self, app: Callable[..., Awaitable[Response]], *, app_env: str) -> None:
        super().__init__(app)
        self._headers = response_security_headers(app_env)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        for name, value in self._headers.items():
            response.headers[name] = value
        return response
