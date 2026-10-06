# M00 — API error envelope and request IDs

## Purpose / user value

Give API consumers one safe, machine-readable error contract and a request ID
that can be used to correlate a failed request with operational evidence.

## Requirement IDs

- NFR-005 — OpenAPI documents API/errors.
- DOC-006 — API description.
- M00 — API error envelope/request IDs.

## Current behavior

FastAPI emits its default `{"detail": ...}` body for HTTP and validation
errors. Successful responses do not carry a request ID, and route-level
OpenAPI metadata does not describe the shared error shape.

## Proposed design

- Add a typed `ErrorResponse`/`ErrorBody` schema matching
  `docs/API_GUIDELINES.md`.
- Generate or accept a safe `X-Request-ID` per request and return it on every
  response.
- Normalize route errors, unknown routes, request validation failures, and
  unexpected server failures into the same envelope without exposing internal
  exception text.
- Declare the relevant 404/409/422/503 error responses in generated OpenAPI.

## Files/modules

- `backend/app/errors.py` — shared error schemas and response helpers.
- `backend/app/main.py` — request-ID middleware, exception handlers, and
  documented route responses.
- `backend/tests/test_errors.py` — envelope, request-ID, and OpenAPI evidence.
- `docs/API_GUIDELINES.md` — concrete contract and code mapping.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — implementation status.

## Data/API changes

Error responses use:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "request_id": "..."
  }
}
```

Every HTTP response also includes `X-Request-ID`. A caller-provided ID is
preserved only when it contains safe identifier characters and is within the
configured length limit; otherwise a UUID is generated.

## Security/privacy implications

Validation and unexpected exception details are not returned. Request IDs do
not contain user data by default and are not used as authentication. The
unexpected-error handler returns a generic message so secrets, SQL, tokens,
and protected resource details cannot escape through error serialization.

## Test plan

- Verify generated and accepted request IDs on successful and error responses.
- Verify HTTP, validation, unknown-route, and unexpected-error envelopes.
- Verify assessment-specific conflict/not-found codes remain stable.
- Verify OpenAPI exposes the shared error schema and documented status codes.
- Run the complete backend suite and Ruff.

## Demo/evidence

`backend/tests/test_errors.py` is repeatable API/OpenAPI evidence. External
supervisor owns verification; this plan does not mark requirements VERIFIED.

## Progress / decisions / surprises

- 2026-10-06: selected as the first unfinished backlog unit after the
  foundation/session work, because all later API modules depend on a stable
  error contract.
- 2026-10-06: implemented shared HTTP/validation/unexpected-error handlers,
  request-ID middleware, route-level OpenAPI error responses, and 13-test
  backend evidence. NFR-005 and DOC-006 are `IMPLEMENTED`; external
  supervisor owns verification.
