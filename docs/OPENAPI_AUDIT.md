# OpenAPI audit — 2026-10-11

The FastAPI application is the source of truth. The generated contract was
loaded from `app.main:app.openapi()` using the repository backend environment.

- OpenAPI version: `3.1.0`
- HTTP paths: `71`
- Schemas: `129`
- Route implementation: `backend/app/main.py`
- Interactive contract: `/docs`
- Machine-readable contract: `/openapi.json`

The audit checked that all route decorators in `backend/app/main.py` are
included in the generated document, including health, candidate, employer,
chat, ATS, reviewer, taxonomy, and validation surfaces. No separate committed
JSON snapshot is maintained, avoiding drift between documentation and the
running API. `docs/API_GUIDELINES.md` documents the stable domain semantics,
privacy boundaries, and error envelope.

This is an implementation audit, not external acceptance: the supervisor must
still verify the live Compose endpoint and the complete authenticated E2E flow.
