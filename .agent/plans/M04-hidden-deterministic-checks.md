# M04 — Hidden deterministic assessment checks

## Purpose / user value

Make the progressive parts of the base assessment verify understanding with a
small deterministic, server-side rubric. A non-empty explanation alone must
not receive follow-up credit, while a failed check remains a reviewable signal
and never becomes an automatic integrity rejection.

## Requirement IDs

AST-013, AST-015.

The backlog unit is M04 “hidden deterministic checks where applicable”. The
implementation applies to the existing progressive assessment families; the
assessment engine explicitly allows constrained deterministic checks for the
MVP without introducing an untrusted code sandbox.

## Current behavior

Progressive items require a non-empty follow-up, but every non-empty response
receives follow-up points. No hidden deterministic rubric is stored on the
attempt or applied during scoring.

## Design

- Add server-only concept groups to applicable progressive template families.
- Persist the selected check with the attempt in the process-local bootstrap
  repository, but never serialize its terms or rule metadata.
- Normalize submitted rationale text and require every concept group to be
  represented by at least one configured term.
- Award progressive points only when the hidden check passes; report a stable
  `hidden_check_review` advisory signal when a supplied rationale fails.
- Keep the platform grade deterministic and keep integrity signals advisory;
  no AI detector or automatic candidate rejection is introduced.

## Files/modules

- `backend/app/assessments.py` — hidden-check definitions, evaluator and
  deterministic scoring.
- `backend/tests/test_assessments.py` — domain/API evidence that checks are
  applied and not exposed.
- `docs/ASSESSMENT_ENGINE.md`, `docs/AI_ASSESSMENT_INTEGRITY.md` — behavior
  and review-signal documentation.
- `docs/REQUIREMENTS_MATRIX.md`, `.agent/BACKLOG.md` — mark only this slice as
  `IMPLEMENTED`; external supervisor owns verification.

## Test plan

- A valid rationale for every progressive item receives follow-up credit.
- A non-empty but concept-free rationale does not receive that credit and
  produces only the advisory review signal.
- Public create/get responses do not expose hidden-check terms or rubric
  internals.
- Existing authorization, answer-key secrecy, uniqueness and advisory
  telemetry tests remain green.

## Progress / decisions / surprises

- 2026-10-07: selected as the first unfinished M04 backlog unit, after
  confirming M04 is the highest-priority unfinished milestone.
- 2026-10-07: limited scope to deterministic checks on existing progressive
  families; full code execution and similarity analysis remain separate
  backlog units.
