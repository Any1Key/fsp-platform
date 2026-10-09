# Labeled matching relevance

The repository has an offline, deterministic relevance-label artifact for
matching validation. It is built from the versioned synthetic fixture and is
not seeded into PostgreSQL or exposed by Talent Radar.

## Contract

`backend/app/matching_validation.py` materializes one case for every
candidate/need pair. Each case contains:

- synthetic candidate and need IDs;
- expected relevance: `relevant`, `adjacent`, or `not_relevant`;
- candidate specialization, target grade, grade state, skills, evidence
  freshness and FSP-history state; and
- need specialization, grade, required skills and preferred skills.

The artifact also reports structural coverage counts: pair completeness,
label vocabulary, grade states, FSP-history states, freshness states, grades
and specializations. These are fixture checks, not ranking-quality metrics.

## Reproduce

From `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.matching_validation \
  --output /tmp/fsp-matching-relevance.json
```

The default fixed seed is `fsp-validation-dataset-2026-10-09`. Passing another
seed is supported for sensitivity checks; the case shape and taxonomy
vocabulary remain fixed.

The output contains 80 synthetic candidates × 20 synthetic needs = 1,600
complete labeled cases. It contains no names, email addresses, passwords,
tokens, resume text, protected attributes or assessment answer keys.

## Default-run evidence

The fixed-seed run on 2026-10-09 produced 1,600/1,600 expected pairs:

| Label/state | Count |
|---|---:|
| `relevant` | 45 |
| `adjacent` | 175 |
| `not_relevant` | 1,380 |
| verified candidates | 64 |
| unconfirmed candidates | 16 |
| candidates with FSP history | 53 |
| candidates without FSP history | 27 |

Freshness coverage was 27 fresh, 27 expiring and 26 stale candidates. These
are deterministic fixture counts, not claims about production match quality.

## Boundary

This unit provides labeled inputs for the later keyword baseline and
Precision@5/nDCG@5/Recall@10 work. It does not calculate those metrics, change
production ProofMatch ranking, create a validation endpoint, or claim actual
production performance. Tests are in
`backend/tests/test_matching_validation.py`.
