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
publication consent. A minor also requires a current submitted/approved
representative consent document before publication; the server withdraws
publication and discoverability if an existing profile becomes minor without
one. Withdrawing processing consent cascades to dependent settings.

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

## Candidate dashboard

`GET /api/v1/candidate/dashboard` returns the authenticated candidate's safe
assessment overview. Ownership is derived from the verified principal subject;
the route accepts no candidate ID. The response includes profile display
fields, the latest submitted category/grade result, retest availability and
recent-first attempt history. `current_assessment` is `null` until an attempt
is submitted. An unconfirmed result remains visible with its declared grade,
`verified_grade: null` and `grade_state: not_confirmed`.

The route does not return answer keys, prompts, integrity telemetry, email,
contacts, protected DOB/minor state or consent metadata. Employers receive
`ROLE_REQUIRED`. See `docs/CANDIDATE_DASHBOARD.md` for the bootstrap storage
boundary and UI states.

## Candidate resume upload

`GET /api/v1/candidate/resume` returns the authenticated candidate's latest
private resume metadata or `document: null`. `POST /api/v1/candidate/resume`
accepts one multipart `resume` part. Processing consent is required. The
server validates the `.pdf` filename, `application/pdf` MIME type, `%PDF-`
signature, and configured size limit before writing the bytes under a UUID
storage key with private permissions. A successful replacement marks the
previous current document `replaced` and returns `201` with safe metadata only:
ID, display filename, type, size, status and upload time. Storage keys, hashes,
file bytes and parsed resume text are never returned. Parser extraction and
candidate review are a subsequent workflow.

## Protected candidate identity data

`GET /api/v1/candidate/protected-profile` and
`PATCH /api/v1/candidate/protected-profile` are candidate-only endpoints for
the private date of birth. The response derives `minor_state` on the server as
`not_set`, `minor`, or `adult` using the configured adult-age threshold. The
client cannot submit an age or state. Writes require processing consent, and a
future date is rejected. The endpoint is separate from the professional
profile and never exposes the value to employers or matching code. The
parent/legal-representative document is handled by the separate protected
workflow below.

## Minor consent document

`GET /api/v1/candidate/minor-consent-document` returns only the authenticated
candidate's derived minor state, requirement flag, policy version and safe
metadata for the latest document. `POST` accepts one multipart `document` PDF,
validates its type/signature and configured size limit, and returns `201` with
metadata/status only. The PDF bytes stay under the configured private storage
directory and are never returned by the API. Upload requires processing consent
and a server-derived minor state; a replacement marks the previous record
`replaced` while retaining protected storage for retention handling. Employers
receive `ROLE_REQUIRED` for both routes.
