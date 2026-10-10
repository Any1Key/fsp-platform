# M13 — Reproducible validation results artifact

## Purpose / user value

Make `docs/VALIDATION_RESULTS.md` auditable instead of relying on separately
copied snippets from the matching and assessment harnesses. One deterministic,
PII-free artifact will tie the published result summary to the current fixture
and both offline evaluators.

## Requirement IDs

- `VAL-002` — own validation procedure and real synthetic results; this slice
  publishes a single reproducible result artifact without changing its existing
  verification state.
- `DOC-004` — validation procedure/results documentation.

## Current behavior

`docs/VALIDATION_RESULTS.md` records matching and assessment values, but there
is no aggregate writer or committed machine-readable artifact that tests those
values against the current generators. The load-test document correctly keeps
authenticated target measurements pending and is not part of this slice.

## Proposed design

- Add an offline `app.validation_report` module that composes the fixed-seed
  dataset coverage, matching metrics, and assessment validation summaries.
- Keep the report aggregate-only: no candidate IDs, labels, prompts, answers,
  or production database/API access.
- Add a CLI and committed `docs/VALIDATION_RESULTS.json` generated from it.
- Test deterministic output, source-version alignment, metric completeness,
  and PII/answer-key exclusion; link the JSON artifact from the markdown.

## Files/modules

- `backend/app/validation_report.py` — aggregate report and CLI.
- `backend/tests/test_validation_report.py` — reproducibility/privacy/artifact
  contract tests.
- `docs/VALIDATION_RESULTS.json` — generated fixed-seed evidence.
- `docs/VALIDATION_RESULTS.md` — procedure, summary, and evidence boundary.
- `docs/VALIDATION_PLAN.md` — report reproduction command and artifact link.
- `docs/REQUIREMENTS_MATRIX.md` / `.agent/BACKLOG.md` — mark only this unit
  `IMPLEMENTED`; never mark `VERIFIED` or change readiness state.

## Data/API changes

None. This is an offline standard-library report and does not touch PostgreSQL,
HTTP routes, production ranking, grades, or dashboard behavior.

## Security/privacy implications

The committed artifact contains only counts, version identifiers, and metric
aggregates. Tests reject email-like strings, candidate IDs, expected labels,
answer-key fields, and production identity data.

## Test plan

- Build the report twice and assert identical dataclasses/JSON.
- Assert fixed dataset/matching/assessment counts and metric values agree with
  the individual engines.
- Write/read the artifact and assert JSON round-trip equality and privacy.
- Run focused tests, the full backend suite, and Ruff.

## Demo/evidence

From `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.validation_report \
  --output ../docs/VALIDATION_RESULTS.json
```

The markdown summary remains the human-readable review surface. The JSON file
is local synthetic evidence only; authenticated production load measurement and
external supervisor verification remain separate.

## Progress / decisions / surprises

- 2026-10-10: selected as the highest-priority unfinished M13 backlog unit.
- 2026-10-10: implemented the aggregate report generator, committed the
  fixed-seed JSON artifact, refreshed the summary/procedure docs, and added
  reproducibility/privacy tests. `DOC-004` is `IMPLEMENTED`; external
  verification and readiness remain untouched.
