# M13 — Labeled matching relevance

## Purpose / user value

Give matching validation work a stable, inspectable relevance-label artifact
that can be consumed by the later keyword baseline and ranking-metric units.
The labels remain synthetic ground truth and never enter production Talent
Radar scoring.

## Requirement IDs

- `VAL-001` — own candidate/vacancy dataset (consume the versioned fixture).
- `VAL-002` — own validation procedure + real results (this slice establishes
  the labeled matching input/procedure only; metric results remain later M13
  work).

## Current behavior

`backend/app/validation_dataset.py` generates a complete expected-relevance
matrix, but consumers must know the fixture internals and independently join
candidate/need records to labels. There is no stable matching-validation
artifact or coverage validator.

## Proposed design

- Add `backend/app/matching_validation.py` with immutable, JSON-safe labeled
  cases, deterministic materialization from the validation dataset, and a
  coverage report.
- Preserve the candidate/need evidence dimensions needed by matching review:
  specialization, target grade, grade state, skills, FSP-history state and
  evidence freshness.
- Add an offline CLI that writes the artifact or prints it to stdout. It uses
  no database, network, production candidate data, or answer keys.
- Keep metric calculations, the keyword baseline, load testing, dashboard and
  `VALIDATION_RESULTS.md` outside this work unit.

## Security/privacy implications

The artifact contains synthetic IDs and taxonomy/evidence labels only. It
must not contain emails, names, tokens, passwords, resume text, protected
attributes or raw assessment answers. Synthetic labels are explicitly kept
out of production routes and database seeding.

## Test plan

- Repeated generation with the same seed is byte-for-byte stable.
- Every candidate/need pair occurs exactly once and all relevance labels are
  in the approved vocabulary.
- Cases preserve the fixture's specialization, grade, grade-state, FSP and
  freshness coverage, including unconfirmed and no-history states.
- JSON round-tripping and CLI output are deterministic and PII-free.
- Existing backend tests remain green.

## Demo/evidence

Run from `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.matching_validation \
  --output /tmp/fsp-matching-relevance.json
```

The artifact contract and downstream boundaries are documented in
`docs/MATCHING_VALIDATION.md`. Only the first M13 backlog item is marked
`IMPLEMENTED`; external supervision owns verification and READY state.

## Progress / decisions / surprises

- 2026-10-09: selected as the highest-priority unfinished M13 work unit.
- 2026-10-09: chose an offline materialized label artifact rather than a
  production API so synthetic ground truth cannot influence candidate search.
- 2026-10-09: implemented the artifact, coverage checks, CLI and documentation;
  focused tests pass and lint passes with a task-local cache directory.
