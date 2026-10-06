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

Document 400/401/403/404/409/422 cases where relevant.
Do not leak protected resource existence across authorization boundaries.
