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

## Keyword baseline

The conventional comparator is implemented in
`backend/app/keyword_baseline.py`. Because the synthetic fixture is
intentionally PII-free and does not contain resume text, candidate skill slugs
are used as the resume-keyword proxy. For each need, the baseline scores every
candidate with the unweighted Jaccard overlap of candidate skills and the
union of required and preferred need skills:

`score = |candidate keywords ∩ need keywords| / |candidate keywords ∪ need keywords|`

It ranks descending by score and then by synthetic candidate ID. It does not
read expected relevance labels, grade, specialization, FSP history or
freshness, and it does not affect production ProofMatch ranking.

Reproduce the label-free baseline artifact from `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.keyword_baseline \
  --output /tmp/fsp-keyword-baseline.json
```

The output contains 20 complete rankings of 80 synthetic candidates. It is
evaluated offline by `backend/app/matching_metrics.py`; it does not enter
production ProofMatch and does not claim production performance.

## Ranking metrics

The metric evaluator validates that the baseline contains exactly one complete
80-candidate ranking for each of the 20 needs before calculating results.
Precision@5 and Recall@10 use `relevant` and `adjacent` as positive retrieval
labels. nDCG@5 retains graded gains of 2 for `relevant`, 1 for `adjacent` and
0 for `not_relevant`. Reported aggregate values are macro averages across
needs and are rounded to six decimal places.

Reproduce the fixed-seed metric report from `backend/`:

```sh
PYTHONPATH=. .venv/bin/python -m app.matching_metrics \
  --output /tmp/fsp-matching-metrics.json
```

The 2026-10-09 default run is summarized in `docs/VALIDATION_RESULTS.md`.
Tests are in `backend/tests/test_matching_validation.py`,
`backend/tests/test_keyword_baseline.py` and
`backend/tests/test_matching_metrics.py`.
