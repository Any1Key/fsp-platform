# ATS integration contract

## Goal and boundary

Employers can connect an internal ATS without coupling the FSP core domain to
a vendor. The executable contract is exposed at
`GET /api/v1/integrations/ats/v1/contract` and is also included in generated
OpenAPI. It returns schemas and security policy only; it never returns employer
credentials or candidate data.

The platform owns the versioned event envelope and match/contact boundary. A
future employer-specific connector implements `AtsConnectorPort` in
`backend/app/ats.py`. Vendor HTTP clients, credential storage, durable delivery
state, retries, and dead-letter storage remain outside the core domain.

## Event catalog

The contract supports these event types:

| Event | Aggregate | Directions | Meaning |
|---|---|---|---|
| `vacancy.created` | `vacancy` | platform ↔ ATS | Vacancy created or imported |
| `vacancy.updated` | `vacancy` | platform ↔ ATS | Vacancy fields changed |
| `vacancy.closed` | `vacancy` | platform ↔ ATS | Vacancy no longer accepts applications |
| `invitation.sent` | `invitation` | platform → ATS | Salary-bearing reverse invitation sent |
| `invitation.viewed` | `invitation` | platform → ATS | Candidate viewed the invitation |
| `invitation.accepted` | `invitation` | platform → ATS | Invitation accepted; match created |
| `invitation.declined` | `invitation` | platform → ATS | Invitation declined |
| `application.created` | `application` | platform ↔ ATS | Application created or imported |
| `application.status_changed` | `application` | platform ↔ ATS | Employer-owned status changed |
| `contact.unlocked` | `talent_match` | platform → ATS | Accepted match authorizes contact flow |

The direction is part of the envelope. An inbound webhook must use
`ats_to_platform`; an outbound connector event uses `platform_to_ats`.

## Event envelope

```json
{
  "schema": "fsp.ats.event.v1",
  "event_id": "evt-01H...",
  "event_type": "invitation.sent",
  "direction": "platform_to_ats",
  "employer_id": "employer-opaque-id",
  "aggregate": {"type": "invitation", "id": "invitation-opaque-id"},
  "occurred_at": "2026-10-09T10:00:00Z",
  "idempotency_key": "evt-01H...",
  "data": {
    "salary_min_rub": 180000,
    "salary_max_rub": 260000,
    "status": "pending"
  }
}
```

`event_id`, `employer_id`, aggregate IDs, and idempotency keys are opaque
identifiers. The event builder removes candidate contact fields recursively
until an accepted invitation creates a match and emits `contact.unlocked`.
Before that boundary, `email`, `phone`, `contact`, `contacts`, Telegram,
WhatsApp, and candidate-specific variants are not contract-safe payload keys.
Age, date of birth, minor documents, access tokens, passwords, and raw OIDC
subjects are never part of this contract.

## Webhook authentication and delivery

Each employer connector has its own secret stored by the future integration
adapter. It is never serialized in an event. The receiver signs the exact raw
UTF-8 request bytes using HMAC-SHA256:

```text
X-FSP-Signature: t=1791530400,v1=<hex HMAC-SHA256(secret, "1791530400." + raw_body)>
Idempotency-Key: delivery-opaque-id
```

The platform verifies the timestamp within a five-minute replay window before
parsing JSON. It then validates the `fsp.ats.event.v1` envelope, requires the
`Idempotency-Key` header to equal the envelope key, and records the key through
the connector's replay store. A duplicate delivery is acknowledged as
`duplicate` and must not apply side effects twice. The in-process
`AtsReplayGuard` is a deterministic contract/test implementation; production
deployment must replace it with shared durable storage.

Inbound events must not unlock contact or bypass the existing match state
machine. Only platform-side acceptance of an invitation creates the match and
the `CONTACT_UNLOCKED` domain event; an ATS status update is evidence for the
employer-owned workflow, not authorization to disclose candidate contact.

Outbound delivery should retry `408`, `425`, `429`, `500`, `502`, `503`, and
`504` with bounded exponential backoff and jitter. The connector must expose
dead-letter metadata to the employer integration operator without logging
secrets or copying unnecessary PII.

## Implementation status

This is a vendor-neutral concept, not a claim that a production ATS connector
exists. The typed contract, OpenAPI discovery endpoint, HMAC verification,
replay/idempotency classification, and contact-redaction rules are implemented
and tested in `backend/app/ats.py` and `backend/tests/test_ats.py`.
