# M13 — Versioned synthetic validation dataset

## Scope

Implement the first unfinished M13 work unit: a deterministic, versioned,
PII-free fixture generator for validation. The fixture will cover candidates,
employer hiring needs, expected relevance labels, and assessment response
profiles so later matching and assessment metric units can consume the same
dataset.

## Requirement IDs

- `VAL-001` — own candidate/vacancy dataset.

The dataset will support later `VAL-002` and metric/load units, but this slice
does not calculate or claim matching metrics, load results, or dashboard
completion.

## Design

- Add `backend/app/validation_dataset.py` with frozen dataclasses and a fixed
  seed/version contract.
- Generate 80 candidates across all catalog specializations and Junior/Middle/
  Senior target grades, including verified and unconfirmed grade states, FSP
  history/no-history, varied skill evidence, and fresh/expiring/stale evidence.
- Generate 20 employer needs with required/preferred skills and deterministic
  expected relevance labels for every candidate/need pair.
- Attach an assessment response profile containing target grade, ability, and
  response seed; do not store answer keys or personal data.
- Provide JSON-safe serialization and a CLI for writing a fixture artifact;
  generation remains offline and standard-library-only.

## Verification

- Unit tests prove repeatability, counts, complete specialization/grade and
  evidence-state coverage, valid taxonomy references, label completeness, and
  JSON round-trip stability.
- Update validation documentation with the dataset contract and command.
- Mark only `VAL-001` and its first M13 backlog item `IMPLEMENTED`; leave all
  other validation, readiness, and verification statuses untouched.

## Implementation notes

- Added `backend/app/validation_dataset.py` with immutable fixture records,
  deterministic JSON serialization, and an offline CLI.
- Added `backend/tests/test_validation_dataset.py` covering repeatability,
  shape/state coverage, taxonomy references, complete relevance labels, and
  PII/answer-key absence.
- Added `docs/VALIDATION_DATASET.md` and linked the fixture from the validation
  plan and requirements evidence.
- Focused tests: 7 passed; full backend suite: 144 passed.

## Change log

- 2026-10-09: selected as the highest-priority unfinished backlog unit.
