# M07 — Reverse-recruitment invitations and match transition

## Scope

Implement one coherent M07 slice: an employer can create a salary-bearing invitation
from Talent Radar without a vacancy; the candidate can view their own inbox and accept
or decline; acceptance creates the durable match/contact-unlock state and audit events.
The slice includes server-side ownership/privacy checks, API integration tests, and the
candidate/employer UI affordances needed to exercise the flow.

## Requirement IDs

- CORE-001 — employer initiates contact with a verified candidate.
- CAND-005, CAND-006 — candidate sees salary-bearing invitations and accepts/declines.
- EMP-007, EMP-008, EMP-009 — invitation without vacancy, mandatory salary, status tracking.
- PRIV-001 — employer cannot access candidate contacts before unlock.
- CHAT-002 — accepted invitation creates match and unlocks the private interaction state.
- DATA-002, DATA-003, DATA-004, DATA-005 — salary visibility, company/contact method,
  and relevant-side status visibility.

## Design decisions

- Invitation stores a company/contact snapshot so later employer edits do not rewrite the
  offer the candidate saw.
- Salary is an integer RUB range, both values are required, positive, and min <= max.
- Only the addressed candidate can read or transition an invitation; only its employer
  can list the sent invitations.
- Acceptance performs invitation transition, match creation, `MATCH_CREATED` and
  `CONTACT_UNLOCKED` audit writes in one transaction. No candidate email/phone is returned
  by invitation or discovery responses.
- Duplicate pending invitations for the same employer/candidate are rejected; terminal
  invitations may be sent again.
- The server rechecks discoverability, publication consent, and a confirmed platform grade;
  an unconfirmed Talent Radar candidate stays searchable but cannot receive this core offer.

## Work items

1. Add invitation/match schema and domain service.
2. Add role-protected create/list/read/respond API routes with normalized error responses.
3. Add backend regression tests for validation, authorization, state transition, idempotency,
   and contact privacy.
4. Add candidate inbox and employer invitation status UI, wire Talent Radar invitation button.
5. Document API/state behavior and mark only covered matrix/backlog items `IMPLEMENTED`.

## Verification

- Run focused M07 pytest coverage, then the complete backend test suite.
- Run frontend typecheck/build.
- Confirm no `VERIFIED` or readiness state is added by this work unit.
