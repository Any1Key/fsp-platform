# API guidelines

Base: `/api/v1`.

Use:
- resource-oriented URLs;
- typed Pydantic schemas;
- consistent pagination;
- stable error envelope with request ID;
- RFC3339 timestamps UTC;
- UUID identifiers;
- explicit state-transition endpoints for domain actions when CRUD would hide invariants.

Error shape target:
```json
{
  "error": {
    "code": "CONTACT_LOCKED",
    "message": "Candidate contact data is not available before unlock.",
    "request_id": "..."
  }
}
```

The implementation returns this envelope for HTTP errors, request validation
errors, unknown routes and unexpected server failures. Every response includes
the same value in `X-Request-ID`; callers may provide a safe identifier in that
header, otherwise the API generates a UUID. Public error codes are stable
identifiers such as `VALIDATION_ERROR`, `RESOURCE_NOT_FOUND`,
`ASSESSMENT_ATTEMPT_NOT_FOUND` and `DATABASE_UNAVAILABLE`; implementation
exception text is never returned.

Document 400/401/403/404/409/422 cases where relevant.
Do not leak protected resource existence across authorization boundaries.
