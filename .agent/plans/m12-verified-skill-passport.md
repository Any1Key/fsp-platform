# M12 Verified Skill Passport

## Purpose / user value

Give a candidate one self-scoped view of the evidence that forms their Verified
Skill Passport. The view combines the system-scored platform assessment, mapped
FSP achievements, and clearly low-trust declared profile skills. It keeps
unconfirmed and no-FSP states visible rather than treating missing evidence as
failure.

## Requirement IDs

- `INNOV-001` — Verified Skill Passport.
- `CAND-004` — candidate sees category/grade and assessment history.
- `FSP-001` — no-FSP-history is a supported state.
- `FSP-003` — FSP achievements remain bounded positive evidence.
- `NFR-006` — self-scope and protected-data boundaries.

## Current behavior

The candidate dashboard exposes assessment category/history, while a separate
FSP panel exposes link and achievement details. There is no single evidence
contract or freshness/status presentation for the candidate.

## Proposed design

Add a derived `GET /api/v1/candidate/skill-passport` endpoint. It reuses the
existing candidate dashboard, taxonomy, and FSP boundaries and returns:

- current category/grade state and assessment freshness;
- evidence cards for platform-assessment skills, FSP-mapped skills, and profile
  declarations with source, confidence, provenance, and freshness state;
- explicit FSP link/history state and freshness counts;
- safe candidate profile display fields only.

No new database table is required: evidence is a read-time projection of
existing system-scored assessment state and persisted FSP snapshots. Assessment
freshness uses a documented 365/730-day display policy; FSP uses its existing
recency mapping; declarations are marked `not_available` for freshness.

## Files/modules

- `backend/app/skill_passport.py` — projection and evidence normalization.
- `backend/app/main.py` — response models and candidate route.
- `backend/tests/test_skill_passport.py` — candidate/employer scope and evidence tests.
- `frontend/src/components/candidate-skill-passport.tsx` — responsive passport UI.
- `frontend/src/components/auth-status.tsx` — mount the passport for candidates.
- `frontend/src/app/globals.css` — branded responsive passport styles.
- `docs/INNOVATIONS.md` — API/UI behavior and freshness policy.
- `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` — mark only implemented scope.

## Data/API changes

New read-only candidate endpoint and Pydantic response models. No migrations,
writes, contact fields, DOB, minor-document data, answer keys, or integrity
signals are included.

## Security/privacy implications

The route uses the existing candidate-role dependency and resolves all source
data from the authenticated subject. It does not accept a candidate ID and
never returns protected profile fields or assessment scoring internals.

## Test plan

- Empty/self-scoped candidate passport with explicit no-history state.
- Verified platform assessment plus FSP and declared evidence projection.
- Unconfirmed assessment remains visible and is not upgraded by declaration.
- Employer role is denied; answer keys/protected fields are absent.
- Frontend typecheck and production build.

## Demo/evidence

The candidate landing workspace shows the passport before the detailed FSP
link-management panel. The API contract and tests provide implementation
evidence; external supervisor owns verification.

## Progress / decisions / surprises

- 2026-10-08: selected as the first unfinished M12 work unit because it is the
  first backlog item and composes already implemented assessment/FSP evidence.
- 2026-10-08: chose a read-time projection to avoid duplicating evidence or
  creating a stale persisted mirror.
