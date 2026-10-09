# M12 — Blind Discovery

## Purpose / user value

Let an employer discover verified evidence and send a salary-bearing reverse-
recruitment invitation without exposing a candidate's name, headline, or
location before the candidate chooses to accept. This gives the Talent Radar a
privacy-preserving discovery mode while keeping the existing match/contact
boundary intact.

## Requirement IDs

- `INNOV-003` — Blind Discovery.
- Supporting privacy boundary: `PRIV-001` — employer cannot receive candidate
  contacts before unlock.

## Current behavior

Talent Radar always returns candidate display name, headline, and location. An
invitation can be created from a radar candidate, but its employer response and
employer invitation list immediately include the candidate display name.

## Proposed design

- Add a `blind` query option to the employer Talent Radar endpoint.
- In blind mode, filter/search/rank using the same evidence graph, but omit
  candidate name, headline, and location from the response and use a generated
  anonymous label. The opaque profile ID remains an action handle and is never
  rendered as identity data.
- Add a `blind_discovery` flag to invitation creation. The flag is persisted so
  server-side employer invitation responses/lists mask the candidate while the
  invitation is pending or declined. Acceptance reveals the candidate in the
  employer's matched invitation view; the candidate's own inbox remains
  unchanged.
- Make the UI switch between normal and blind radar modes and clearly explain
  that evidence, category, score, gaps, and salary remain visible while identity
  is withheld until acceptance.

## Files/modules

- `backend/alembic/versions/20261008_0027_blind_discovery.py` — invitation mode.
- `backend/app/discovery.py`, `backend/app/main.py` — filter and response.
- `backend/app/invitations.py` — persistence and role-scoped masking.
- `backend/tests/test_talent_radar.py`, `backend/tests/test_invitations.py` —
  privacy and lifecycle regression coverage.
- `frontend/src/components/employer-talent-radar.tsx` and
  `frontend/src/app/globals.css` — responsive mode control/cards.
- `docs/INVITATIONS.md`, `docs/INNOVATIONS.md` — API and privacy contract.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — `IMPLEMENTED` evidence.

## Data/API changes

Add nullable-free `invitation.blind_discovery BOOLEAN NOT NULL DEFAULT FALSE`.
`GET /api/v1/employer/talent-radar?blind=true` returns an anonymized projection;
`POST /api/v1/employer/invitations` accepts `blind_discovery`. The response
contains `blind_discovery` and masks the candidate only for employer views until
the invitation is accepted.

## Security/privacy implications

Masking is performed in the backend, not only in React. Blind mode never uses
name/headline/location in its free-text query matching and never returns those
fields. Candidate contact, DOB, documents, and email remain outside the radar
and invitation contracts. Existing acceptance and chat authorization is
unchanged.

## Test plan

- Blind radar returns matching evidence and categories without raw candidate
  identity fields, including when the query is used.
- Blind invitation creation persists the mode and masks the employer response
  and pending employer list.
- Candidate receives the normal safe offer and can accept; after acceptance the
  employer sees the candidate identity and match ID.
- Existing non-blind invitation behavior remains unchanged.
- Run focused backend tests, full backend suite, frontend typecheck, and build.

## Demo/evidence

The employer Talent Radar mode switch demonstrates anonymous evidence-first
discovery, invitation creation, and the post-acceptance reveal boundary. The
matrix records `INNOV-003` as `IMPLEMENTED`; external supervision owns
verification and readiness.

## Progress / decisions / surprises

- 2026-10-08: selected as the first unfinished M12 unit.
- 2026-10-08: chose invitation-backed reveal rather than a UI-only blur so the
  privacy promise is enforced for direct API consumers and persisted employer
  invitation views.
- 2026-10-08: focused and full backend suites pass (9 focused, 128 full), Ruff
  passes, and frontend typecheck/production build pass.
