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

FSP is a **bounded positive bonus** only. The M05 service in
`backend/app/fsp.py` calculates relevance from specialization/skill overlap, then
weights result strength (40%), event level (20%), recency (20%) and verification
provenance (20%). The three strongest relevant achievements are aggregated at
70%/20%/10% and capped at the configured 10-point ranking weight. It returns the
contributing achievement IDs, matched skills, component scores and reasons for
explainability.

Missing FSP = zero bonus, never a penalty. A strong non-FSP candidate must be able
to outrank an FSP candidate. M06 employer discovery is responsible for composing
this contribution with the remaining ProofMatch components and rendering it.

The employer need input boundary is implemented separately at
`/api/v1/employer/hiring-need`. It persists the team/role context, target
specialization and grade, and normalized required/preferred skill sets. This
structured input is consumed by the M06 Talent Radar projection below.

## Implemented M06 Talent Radar projection

`GET /api/v1/employer/talent-radar` composes the current need with candidates
who have both publication consent and discoverability enabled. It projects the
latest submitted assessment from the existing assessment boundary, so a
verified category is specialization plus confirmed grade. A failed or missing
submission remains visible as `not_confirmed` or `not_assessed` rather than
being silently removed. The route never reads protected age/minor data or
exposes contact data.

The implemented score uses the documented weights: specialization (20), grade
fit (15), required skill coverage (25), preferred skill coverage (10),
assessment strength (15), evidence confidence/freshness (5), and the bounded
FSP bonus (10). Every component is returned in `score_breakdown`. Profile
declarations and FSP achievements are separate evidence edges; the response
also returns category state, assessment state, confidence dimensions, reasons,
and missing required skills. No-FSP candidates receive a zero bonus and remain
eligible.

The response includes category-level verified/unconfirmed counts and supports
search, specialization/grade/skill/FSP filters, explicit unconfirmed inclusion,
and a snapshot containing selected candidate IDs, filter values, scoring and
evidence versions, and the hiring-need version. This is the read-only discovery
slice; salary-bearing invitations and contact unlock remain M07.

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
