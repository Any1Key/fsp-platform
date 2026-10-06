# M03/M04 — Calibrated assessment factory

## Purpose / user value

Provide a deterministic, auditable base assessment that gives each candidate a
different session form while preserving comparable difficulty. Make answer
sharing and outsourcing less useful through session-specific artifacts and
progressive follow-ups, without using an AI detector as a pass/fail gate.

## Requirement IDs

AST-003, AST-004, AST-005, AST-010, AST-012, AST-013, AST-015, AST-016.

## Current behavior

The backend is a health-check-only FastAPI skeleton. There is no assessment
model, API, persistence or test evidence.

## Proposed design

- Pure `assessments` domain module with calibrated blueprints, versioned item
  families and deterministic seeded parameter variants.
- Immutable in-memory assessment repository for the bootstrap slice; its
  interface keeps storage replaceable by PostgreSQL in M00/M03 follow-up.
- Attempt creation returns prompts and metadata only; correct answers and
  scoring rules stay server-side.
- Form uniqueness is asserted against the candidate's recent attempts and
  family exposure budgets/cooldowns are enforced.
- Submission computes deterministic score/grade, progressive follow-up scores,
  advisory integrity signals, and a configurable retest lock. Integrity signals
  never alter the deterministic grade.

## Files/modules

- `backend/app/assessments.py` — domain, factory, scoring and repository.
- `backend/app/main.py` — typed REST endpoints for create/get/submit.
- `backend/tests/test_assessments.py` — domain and API evidence.
- `docs/ASSESSMENT_ENGINE.md`, `docs/AI_ASSESSMENT_INTEGRITY.md` — already
  define the policy implemented here.

## Data/API changes

- `POST /api/v1/assessments/attempts`
- `GET /api/v1/assessments/attempts/{attempt_id}`
- `POST /api/v1/assessments/attempts/{attempt_id}/submit`

The bootstrap repository is process-local and explicitly not production
persistence. It is sufficient to prove the domain behavior before migrations.

## Security/privacy implications

No answer keys or rubric secrets are returned before submission. Candidate IDs
are accepted as opaque identifiers; no DOB, contact data or PII is used. The
integrity output is advisory and does not automatically reject a candidate.

## Test plan

- distinct forms for two candidates and repeated attempts;
- equivalent scoring on seeded variants;
- family cooldown/exposure and 90-day retest lock;
- declared grade remains unchanged after a failed result;
- progressive follow-up and session-specific artifact checks;
- integrity flags are advisory and AI detector is absent;
- API hides answer keys and returns grade/result data after submission.

## Demo/evidence

Pytest output and OpenAPI routes are the evidence for this slice. External
supervisor must run the suite and independently inspect the end-to-end flow;
this plan does not mark any requirement VERIFIED.

## Progress / decisions / surprises

- 2026-10-06: selected as the nearest coherent milestone because the repo is
  still bootstrap-only and assessment behavior is a prerequisite for matching.
- 2026-10-06: chose process-local repository temporarily; persistent storage is
  intentionally deferred to M00 migrations rather than faking database claims.
