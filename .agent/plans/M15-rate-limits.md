# M15 rate limits

## Purpose / user value

Protect the public registration probe and the highest-cost or privacy-sensitive
write endpoints from accidental bursts and simple abuse without rate-limiting
normal read traffic or replacing domain-specific business limits.

## Requirement IDs

- `NFR-006` — RBAC, secure tokens, consent/privacy; this slice adds a
  server-side abuse-control boundary around auth, assessment, upload, chat and
  privacy actions.
- `LEGAL-001` — 152-FZ-oriented data minimization, RBAC and audit controls;
  this slice limits repeated access to private-data mutation boundaries and
  does not add personal data to the limiter state.
- Supporting `NFR-010` — stable operation for concurrent users; the limiter
  has bounded in-process state and documented deployment scope.

## Current behavior

The API has an employer trust invitation quota and a database-backed optional
local-AI quota, but no shared HTTP protection for the public registration
check, assessments, private uploads, chat messages, or privacy requests.

## Proposed design

- Add a bounded, thread-safe fixed-window store with monotonic time.
- Match only explicit abuse-sensitive method/path policies; leave health,
  reads, browser preflight, and ordinary navigation unrestricted.
- Key unauthenticated requests by a one-way fingerprint of the accepted
  connection peer and
  authenticated requests by a SHA-256 fingerprint of the bearer value. The
  raw token, address and request body are never stored or logged.
- Return the common error envelope with `429`, `Retry-After`, and safe rate
  limit headers.
- Make limits and the store capacity configurable; document the process-local
  scope and the production gateway/shared-store follow-up.

## Files/modules

- `backend/app/rate_limit.py` — bounded store, policy table and middleware.
- `backend/app/config.py`, `backend/app/main.py` — configuration and wiring.
- `backend/app/errors.py` — public `RATE_LIMITED` error contract.
- `backend/tests/test_rate_limit.py`, `backend/tests/conftest.py` — deterministic
  store/middleware and API contract tests.
- `docs/SECURITY.md`, `docs/LEGAL_152FZ.md`, `docs/REQUIREMENTS_MATRIX.md`,
  `.agent/BACKLOG.md` — security scope and implemented evidence.

## Data/API changes

No database schema or business response changes. Limited responses use the
existing error envelope and add `Retry-After`, `X-RateLimit-Limit`, and
`X-RateLimit-Remaining` headers.

## Security/privacy implications

The limiter fails closed for configured policy matches, stores only short-lived
hash keys and counters, and never trusts a client-supplied forwarding header.
It is intentionally process-local; a multi-worker deployment must enforce the
same policy at a trusted ingress/shared store before claiming cluster-wide
coverage.

## Test plan

- Verify fixed-window allow/deny/retry behavior, stale-window cleanup and
  bounded key eviction with an injected clock.
- Verify registration is limited, normal health traffic is not, authenticated
  token fingerprints do not expose token material, and `429` responses carry
  the standard request-ID/error/header contract.
- Run the complete backend test suite.

## Demo/evidence

`backend/tests/test_rate_limit.py` demonstrates the policy boundary and the
safe client contract. Security and legal docs identify the limits and their
deployment scope; the backlog item is marked `IMPLEMENTED` only.

## Progress / decisions / surprises

- 2026-10-11: selected as the first unfinished M15 work unit under deadline
  mode.
- 2026-10-11: completed bounded middleware/store, API error/OpenAPI contract,
  documentation, and backend regression coverage; address and token values
  are represented only by one-way fingerprints.
