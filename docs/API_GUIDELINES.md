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

## Candidate privacy

`GET /api/v1/candidate/privacy` returns only the authenticated candidate's
processing consent, publication consent, policy version/timestamps and
discoverability state. `PATCH` accepts one or more boolean state changes; the
server supplies the configured policy version and records a non-PII audit
event. Publication requires processing consent, and discoverability requires
publication consent. Withdrawing a parent consent cascades to dependent
settings.

`POST /api/v1/candidate/privacy/export` records an authenticated export
request and returns `202` with a request ID and `requested` status. It is an
MVP request concept; fulfillment is intentionally delegated to a future
privacy worker and legal-reviewed retention policy.

## Candidate profile

`GET /api/v1/candidate/profile` returns only the authenticated candidate's
professional self-description. `PATCH` saves the editable display name,
headline, location, summary, structured experience, skills, and work
preferences after processing consent is granted. The profile endpoint never
returns identity email, contacts, DOB/minor state, resume documents, consent
metadata, or assessment results. Employers receive `ROLE_REQUIRED` and cannot
use this self-scoped resource.
