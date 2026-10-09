# M12 — ATS integration contract

## Purpose / user value

Give employers a stable, vendor-neutral contract for connecting an internal
ATS while keeping vendor credentials and transport details outside the core
domain. The contract must be safe to implement later: outbound events are
versioned, inbound webhooks are signed and replay/idempotency aware, and
candidate contact is never included before the platform match unlock.

## Requirement IDs

- `BONUS-002` — ATS integration concept.
- Supporting boundaries: `PRIV-001`, `CHAT-002`, `DOC-006`, `NFR-006`.

## Current behavior

`docs/ATS_INTEGRATION.md` describes a future adapter boundary, but the
contract is not represented in the API, there is no executable event schema,
and signature/replay/contact-redaction invariants are not tested.

## Proposed design

- Add `backend/app/ats.py` with a versioned event envelope, event catalog,
  connector protocol, contact-redaction helper, HMAC signing/verification,
  and bounded replay/idempotency guard.
- Add a read-only `GET /api/v1/integrations/ats/v1/contract` endpoint. It is
  safe to expose without authentication because it returns schemas and policy,
  never employer credentials or candidate data.
- Keep vendor HTTP clients, per-employer secret storage, durable delivery,
  retries, and dead-letter storage behind the connector port. This slice does
  not claim a production connector exists.
- Update ATS/API/architecture docs with the JSON envelope, headers, event
  catalog, contact boundary, and delivery responsibilities.

## Security/privacy implications

- Webhook signatures use the raw request bytes plus a timestamp and a
  per-employer secret; stale signatures and malformed signatures fail closed.
- A replay guard rejects a previously accepted idempotency key inside the
  configured retention window. Production adapters must back this with durable
  storage shared by all workers.
- Candidate contact keys are removed from outbound event data until an
  accepted invitation has created a match and unlocked contact. The redaction
  is in the contract helper, not only in a UI.
- The contract contains no age, DOB, minor-document, token, password, or raw
  OIDC data.

## Test plan

- Contract endpoint and OpenAPI expose the version, supported events, headers,
  retry policy, and contact-unlock rule.
- Event envelopes validate the event catalog and redact candidate contact
  before unlock while preserving it after unlock.
- Signature verification accepts the exact signed payload, rejects tampering
  and stale timestamps, and the replay/idempotency guard rejects duplicates.
- Existing backend tests remain green; no vendor connector or database secret
  is introduced.

## Demo/evidence

The contract endpoint is available in Swagger/OpenAPI and the documentation
contains copyable request/response examples. `backend/tests/test_ats.py`
provides executable evidence for the envelope, signature, replay, and contact
privacy rules. The matrix records `BONUS-002` as `IMPLEMENTED`; external
supervision owns verification and readiness.

## Progress / decisions / surprises

- 2026-10-09: selected as the first unfinished item in M12.
- 2026-10-09: chose an executable contract and replaceable connector port
  rather than a vendor-specific integration or an unscoped credential store.
