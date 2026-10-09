# M12 — Talent Radar polish

## Purpose / user value

Make the employer discovery surface feel like evidence-first Talent Radar
rather than a resume list. Employers should understand category supply, why a
candidate fits, what is missing, and which actions are available before
sending a salary-bearing invitation.

## Requirement IDs

- `INNOV-004` — Talent Radar employer UI.
- Supporting UI evidence: `EMP-003`, `EMP-004`, `EMP-005`, `EMP-006`,
  `MATCH-004`, and the responsive/empty/loading criteria in `docs/UI_ACCEPTANCE_CRITERIA.md`.

## Current behavior

The employer Radar renders filters, a three-cell summary, and two-column
candidate cards. Cards show a numeric ProofMatch score, a few reasons, and an
invitation action, but do not show category supply, a human-friendly fit band,
the score component breakdown, or a profile/evidence detail interaction. The
backend already returns the required score components, evidence edges,
confidence, reasons, gaps, and category counts.

## Proposed design

- Add a category supply strip showing category, total candidates, verified
  count, and unconfirmed count.
- Add a human-readable fit band derived from the server score and explicitly
  label unconfirmed candidates.
- Add a `View proof` action that opens an accessible dialog with score
  breakdown, confidence dimensions, verified evidence provenance, and gaps.
- Preserve the existing invitation form and server-side blind/privacy boundary;
  the dialog must never render contacts, DOB, documents, or opaque IDs.
- Add active-filter summary/reset affordances and responsive styles so the
  Radar remains usable at mobile widths.

## Files/modules

- `frontend/src/components/employer-talent-radar.tsx`
- `frontend/src/app/globals.css`
- `qa/tests/talent-radar-ui.spec.ts`
- `backend/tests/test_talent_radar.py`
- `docs/MATCHING_ENGINE.md`, `docs/API_GUIDELINES.md`
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md`

## Data/API changes

Add a derived `fit_band` field to each Radar candidate response. It is a
presentation label derived from the existing score/state and is not a hiring
decision or ranking gate. No new personal data is added.

## Security/privacy implications

The detail dialog is populated only from the existing employer-safe Radar
projection. Blind mode continues to receive masked identity. The UI must not
reconstruct identity from `candidate_id` or expose contact/protected data.

## Test plan

- Backend Radar integration test asserts fit-band output for verified and
  unconfirmed candidates and preserves the existing safe projection.
- Opt-in Playwright UI test runs with an externally supplied authenticated
  employer storage state, verifies category supply, proof dialog content,
  invitation entry point, and no horizontal overflow at mobile.
- Run focused backend tests, full backend suite, frontend typecheck/build, and
  the focused QA test when the Compose QA profile is available.

## Demo/evidence

An employer can open Talent Radar, see supply by category, filter the current
snapshot, inspect a candidate's ProofMatch explanation, and start a
salary-bearing invitation without contacts becoming visible before match.

## Progress / decisions / surprises

- 2026-10-09: selected as the highest-priority unfinished work unit in M12.
- 2026-10-09: kept score calculation and invitation authorization unchanged;
  this slice improves the employer projection and explanation surface.
- 2026-10-09: focused and full backend suites pass (3 focused, 129 full),
  Ruff passes, and frontend typecheck/production build pass. The Playwright
  coverage is opt-in because this workspace has no running Compose QA session;
  test discovery was checked across all five required viewports.
