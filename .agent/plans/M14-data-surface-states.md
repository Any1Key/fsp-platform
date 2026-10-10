# M14 data-surface states

## Purpose / user value

Make asynchronous FSP Talent surfaces understandable while data is loading, unavailable, empty,
or not yet confirmed. A candidate must be able to distinguish an empty passport from a failed
request, and an employer must be able to see that an unconfirmed candidate is still searchable
without mistaking the state for a verified grade.

## Requirement IDs

- CAND-004 — candidate category/grade and assessment history, including an explicit unconfirmed state.
- MATCH-006 — an unconfirmed candidate remains searchable with a clear marker.
- INNOV-007 — Validation Dashboard loading/error states.
- UI-002 — shared loading, empty, error and unconfirmed-grade states across data-driven surfaces.
- UI acceptance criteria — error/empty/loading states and visually distinct declared vs verified evidence.

## Current behavior

The authenticated shell and data-driven components implement local loading/error/empty strings,
but each uses different markup and retry behavior. Unconfirmed-grade labels are also repeated in
the candidate passport and Talent Radar. This makes state semantics and accessible announcements
inconsistent across journeys.

## Proposed design

- Add small presentational `LoadingState`, `ErrorState`, `EmptyState`, and
  `UnconfirmedGradeBadge` components with stable `data-ui-state` hooks and accessible roles.
- Use the components in the candidate Skill Passport, employer Talent Radar, Validation Dashboard,
  and Keycloak session panel. Keep domain-specific empty copy and actions at each call site.
- Preserve existing API contracts, privacy boundaries, ranking behavior, and unconfirmed candidate
  eligibility; this is a presentation/state-contract slice only.

## Files/modules

- `frontend/src/components/ui-state.tsx`
- `frontend/src/components/auth-status.tsx`
- `frontend/src/components/candidate-skill-passport.tsx`
- `frontend/src/components/employer-talent-radar.tsx`
- `frontend/src/components/validation-dashboard.tsx`
- `frontend/src/app/globals.css`
- `qa/tests/ui-states-contract.spec.ts`
- `docs/UI_STATES.md`
- `.agent/BACKLOG.md`
- `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

None. State components consume existing responses and do not change request, response, scoring,
or authorization contracts.

## Security/privacy implications

None beyond making failure copy safer and more consistent. API payloads, candidate contact
unlock, unconfirmed-candidate visibility, and role boundaries are unchanged.

## Test plan

- Frontend TypeScript check and production build.
- Playwright source contract verifies the shared state vocabulary and adoption points.
- Existing responsive/accessibility contracts remain unchanged and should continue to pass.

## Demo/evidence

The UI-state source contract is `qa/tests/ui-states-contract.spec.ts`; external supervision owns
authenticated visual screenshots and final `VERIFIED` status.

## Progress / decisions / surprises

- 2026-10-10: selected as the highest-priority unfinished backlog work unit. Existing related
  requirements remain `VERIFIED`; the new UI-002 evidence is marked only `IMPLEMENTED`.
- 2026-10-10: frontend typecheck, production build, QA contract, and the new Playwright contract
  passed. The optional public browser pass could not start because this host has no installed
  Playwright Chromium executable; no browser binaries were installed or changed.
