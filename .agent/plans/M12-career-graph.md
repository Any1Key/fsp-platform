# M12 Career Graph

## Purpose / user value

Give a candidate a readable, evidence-first map of their current professional
position and plausible next paths. The graph turns the existing Verified Skill
Passport into a small decision aid: confirmed evidence is separated from
declared skills, adjacent taxonomy paths are explainable, and missing evidence
is shown as a gap instead of being treated as a rejection.

## Requirement IDs

- `INNOV-006` — Career Graph candidate UI.
- Supporting boundaries: `CAND-004` (candidate assessment/category view),
  `FSP-003` (bounded FSP evidence), `NFR-006` (self-scope/privacy).

## Current behavior

The candidate can view assessment and evidence cards in the Verified Skill
Passport, but there is no graph-like projection connecting those skills to the
active specialization/grade catalog or showing adjacent growth paths.

## Proposed design

Add `GET /api/v1/candidate/career-graph`, a candidate-role protected,
candidate-ID-free read endpoint. It composes the latest submitted assessment,
taxonomy skills, FSP-mapped evidence, and declared profile skills into:

- a current position node with grade state and assessment confidence;
- skill nodes marked `verified`, `unconfirmed`, or `declared`, with evidence
  counts and freshness;
- adjacent specialization/grade path nodes selected by taxonomy skill overlap
  and grade progression, with matched skills and explicit gaps;
- a summary of evidence/gaps and a stable graph version.

No path is presented as a hiring guarantee. Unconfirmed grades remain visible;
no-FSP candidates still receive a graph from platform/profile evidence.

## Files/modules

- `backend/app/career_graph.py` — read-time graph projection.
- `backend/app/main.py` — response models and candidate route.
- `backend/tests/test_career_graph.py` — API scope, evidence, gaps, and
  no-history integration tests.
- `frontend/src/components/candidate-career-graph.tsx` — responsive branded
  candidate graph UI with loading, error, empty, and unconfirmed states.
- `frontend/src/components/auth-status.tsx` and
  `frontend/src/app/globals.css` — mount and style the component.
- `docs/INNOVATIONS.md`, `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` —
  implementation evidence/status.

## Data/API changes

One read-only endpoint and Pydantic response models. No new tables, writes,
contact fields, DOB/minor data, assessment answer keys, or integrity telemetry.

## Security/privacy implications

The endpoint uses the existing candidate-role dependency and resolves all
inputs from the authenticated subject. It never accepts a candidate ID and
does not expose protected profile fields. Path suggestions use only active
taxonomy and candidate evidence, never age, location, name, or other protected
traits.

## Test plan

- Empty candidate receives a stable empty graph and next-step guidance.
- Assessed/FSP/profile candidate receives current, evidence, adjacent-path, and
  gap nodes with bounded statuses and no sensitive fields.
- Unconfirmed declared grade remains unconfirmed and does not become verified
  because of profile or FSP declarations.
- A second candidate cannot see the first candidate's graph; employers are
  denied.
- Frontend typecheck and production build.

## Demo/evidence

The candidate workspace shows Career Graph directly after the Verified Skill
Passport. The API contract and focused tests demonstrate end-to-end behavior;
external supervision owns verification.

## Progress / decisions / surprises

- 2026-10-09: selected as the first unfinished M12 backlog unit.
- 2026-10-09: chose a read-time projection so the graph cannot become a stale
  duplicate of assessment, FSP, or taxonomy data.
- 2026-10-09: focused Career Graph tests pass (3), adjacent passport/dashboard
  regressions pass (7), full backend suite passes (132), and frontend typecheck
  plus production build pass. External supervisor still owns verification.
