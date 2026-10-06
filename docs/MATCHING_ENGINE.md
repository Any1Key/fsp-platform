# ProofMatch — Evidence-Graph Reverse Matching

## Product idea

Do not present a flat resume search as the primary experience. Employer starts from a hiring need and sees a **Talent Radar** of candidate categories, then drills into an explainable candidate ranking.

The system matches **proof of capability**, not merely keyword overlap.

## Candidate state model

Employer-visible candidate can be:
- `verified` — specialization + grade confirmed by platform assessment;
- `declared_unverified` / `not_confirmed` — remains searchable but visibly marked;
- temporarily `retest_locked` while still searchable according to privacy settings.

Unconfirmed grade is never silently presented as verified.

## Layer 0 — eligibility

Require:
- publication/discoverability consent;
- valid candidate profile;
- specialization relevance / employer filters.

Do **not** exclude solely because:
- no FSP history;
- declared grade is unconfirmed.

Minor consent status must gate publication/discoverability when required, but age itself never ranks candidates.

## Layer 1 — category / confidence

Compute category fit from specialization + grade state. Verified grade has higher evidence confidence than an unconfirmed declaration. The employer can include/exclude unconfirmed candidates explicitly.

## Layer 2 — evidence graph

Represent each required/preferred skill as a node with evidence edges:
- platform assessment;
- FSP achievement;
- employer-specific task/challenge;
- resume declaration.

Each edge has relevance, confidence, recency and provenance. Aggregate without hiding the sources.

## Layer 3 — need-specific rank

Initial transparent score for **verified** candidates:

| Component | Weight |
|---|---:|
| specialization/category fit | 20 |
| verified grade fit | 15 |
| required skill evidence coverage | 25 |
| preferred skill evidence coverage | 10 |
| assessment strength | 15 |
| evidence confidence/freshness | 5 |
| FSP relevant achievement bonus | 10 |

Weights are configurable/versioned and must be validated.

For unconfirmed-grade candidates, calculate fit but expose lower grade-confidence separately rather than using a hidden punitive constant. UI should show `Potential fit — grade not confirmed`.

## FSP evidence score

FSP is a **bounded positive bonus** only. Suggested components:
- relevance of achievement discipline/event to the need;
- event level/importance from synthetic registry data;
- placement/result;
- recency;
- verification provenance.

Cap the total FSP contribution at the configured ranking weight. Missing FSP = zero bonus, never a penalty. A strong non-FSP candidate must be able to outrank an FSP candidate.

## Employer-specific evidence

After a match, employer tasks can add a separate `opportunity_fit` component visible for that employer/hiring need. By default it does not mutate the platform-wide verified grade.

## Explainability contract

Every result returns:
- overall fit score/band;
- verified/unconfirmed grade state;
- component scores;
- evidence confidence;
- positive reasons;
- gaps;
- stale evidence;
- FSP contribution;
- employer-specific stage result when applicable.

Example:
```json
{
  "fit_band": "ready_now",
  "match_score": 91,
  "grade_state": "verified",
  "reasons": [
    "Backend / Middle verified",
    "4 of 5 required skills have verified evidence",
    "Assessment 87/100",
    "2 relevant verified FSP achievements"
  ],
  "gaps": ["Docker evidence is stale"],
  "confidence": 0.89
}
```

Never show a percentage without an explanation.

## Talent Radar

Before candidate cards, show category-level supply such as:
- specialization;
- grade state;
- number of discoverable candidates;
- number with high-confidence verified evidence;
- FSP-history count;
- freshness distribution.

This makes reverse discovery visibly different from a normal resume board.

## Result bands

Use human-friendly bands in addition to numeric score:
- `Ready now` — strong verified fit;
- `Strong fit`;
- `Potential fit` — meaningful gaps or unconfirmed grade;
- `Explore` — broader discovery.

No automatic hiring/rejection decision is made.

## Refinement

Use a `matching_snapshot` preserving candidate IDs, scoring version, evidence version and need version. Filter/sort the snapshot unless employer explicitly recomputes.

## Validation

Build at least:
- 80 synthetic candidates;
- 20 employer needs;
- expected relevance labels, including verified/unconfirmed and FSP/no-FSP cases.

Metrics:
- Precision@5;
- Recall@10;
- nDCG@5;
- category eligibility accuracy;
- explanation completeness;
- fairness sanity check: no-FSP candidates are not excluded;
- grade-state correctness.

Compare against a simple resume keyword baseline.

## Prohibited features

No ranking by sex/gender, race/ethnicity, religion, health, political views, age/year of birth or other protected/sensitive traits.
