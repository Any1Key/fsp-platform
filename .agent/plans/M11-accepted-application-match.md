# M11 — Accepted vacancy application creates a match

## Purpose / user value

Complete the vacancy hiring path: an employer can review applications received
for its own published vacancies, accept one, and immediately get the same
server-enforced matched communication boundary used by reverse recruitment.
Candidates see the accepted status and match state without exposing contacts
before the match exists.

## Requirement IDs

- `EMP-010` — publish/edit vacancies and receive/manage incoming applications.
- `CAND-009` — candidate sees the application status history, including accepted.
- `CHAT-002` — accepted hiring interaction creates a match and unlocks internal
  chat through the existing match boundary.

## Current behavior

Candidate applications persist only through `withdrawn`/`rejected`-style review
states. Employers cannot list or change applications. The existing
`talent_match` schema is invitation-backed, so application acceptance needs a
private application-sourced invitation bridge while keeping the invitation UI
reserved for direct reverse-recruitment offers.

## Design

- Extend application and status-history constraints with `accepted`.
- Add employer-scoped application listing and status-transition endpoints.
- Allow an employer to transition an owned application to `accepted`.
- In one transaction, create an internal accepted invitation bridge, the
  existing `talent_match`, contact-unlock and match events, conversation, and
  employer-task assignments. Repeated acceptance is idempotent.
- Hide the bridge from direct-invitation lists; the candidate sees the accepted
  application and its `match_id`.
- Add a focused employer review panel and candidate accepted/matched state.

## Files/modules

- `backend/alembic/versions/20261008_0024_application_acceptance.py`
- `backend/app/invitations.py`, `backend/app/vacancy_applications.py`,
  `backend/app/main.py`, `backend/app/errors.py`
- `backend/tests/test_candidate_vacancies.py`
- `frontend/src/components/employer-applications.tsx`,
  `frontend/src/components/candidate-vacancies.tsx`,
  `frontend/src/components/auth-status.tsx`, `frontend/src/app/globals.css`
- `docs/EMPLOYER_VACANCIES.md`, `docs/CANDIDATE_VACANCIES.md`,
  `docs/CHAT_AND_MATCHING.md`, `docs/REQUIREMENTS_MATRIX.md`,
  `.agent/BACKLOG.md`

## API/data changes

- `GET /api/v1/employer/applications`
- `PUT /api/v1/employer/applications/{application_id}` with review status
  `reviewing`, `shortlisted`, `rejected`, or `accepted`.
- `accepted` is an application terminal state and returns the created match ID.
- `invitation.source_application_id` privately links the match bridge to its
  originating application.

## Security/privacy

Employer reads and writes are constrained by `company.owner_identity_id`.
Responses contain only the candidate display name and vacancy/application
metadata; contacts and chat remain unavailable until the transaction creates
the match. Candidate application reads remain profile-scoped.

## Test plan

- migration upgrades application/status-history constraints and adds the
  private bridge link;
- employer receives only its own incoming applications;
- role and company isolation reject unauthorized reads/writes;
- accepted application creates exactly one match, unlock events,
  conversation, and candidate-visible accepted history;
- repeated acceptance is idempotent and rejected/accepted terminal transitions
  cannot be changed;
- focused/full backend tests, Ruff, and frontend typecheck/build.

## Progress / decisions

- 2026-10-08: selected as the highest-priority unfinished M11 work unit.
- 2026-10-08: the existing invitation-backed match schema is retained through
  an internal source-application bridge, avoiding a second chat authorization
  model and keeping direct invitation inboxes semantically separate.
- 2026-10-08: implemented migration, employer API/UI, candidate match state,
  atomic match side effects, deterministic status-history ordering, and focused
  integration evidence. External supervisor owns verification.
