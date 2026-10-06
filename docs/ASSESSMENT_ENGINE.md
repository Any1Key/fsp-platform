# Assessment engine

## Problem

The assessment must avoid three failure modes:
1. one fixed test whose questions/answers leak;
2. unconstrained per-candidate AI generation with incomparable difficulty;
3. an assessment that collapses most synthetic candidates to the same grade.

Use a calibrated, reproducible **test factory**.

## Competency blueprint

Every `(specialization, grade)` defines:
- competency domains and weights;
- target difficulty mix;
- critical-domain floors;
- allowed formats;
- approximate time budget;
- minimum template-family diversity.

Example Backend Middle:

| Domain | Weight |
|---|---:|
| Language/runtime | 20% |
| API/backend fundamentals | 20% |
| SQL/data modeling | 20% |
| Testing/debugging | 15% |
| Architecture/design | 15% |
| Security/operations | 10% |

## Item template families

A family defines a competency pattern. Concrete variants are generated from a secure seed.

Persist:
- family/template/version;
- competency/grade/difficulty;
- parameters/data/code fragment;
- prompt renderer;
- rubric/hidden checks;
- max score/estimated time;
- exposure count/status;
- attempt-specific seed.

The same family can measure the same competency without giving two candidates the same concrete task.

## Anchor/calibration items

Each form contains hidden calibrated anchors, but anchors themselves have equivalent surface variants. Use them to compare difficulty across forms. Never expose which items are anchors.

## Form assembly

1. choose template families by blueprint/domain weight;
2. satisfy target difficulty distribution;
3. insert anchor/calibration families;
4. exclude recently seen/overexposed families;
5. create session-specific variants using secure seed;
6. assert form uniqueness against recent attempts;
7. persist the complete immutable form before start.

Target: roughly 16–24 items and 45–60 minutes for the full base assessment, configurable by specialization/grade.

## Formats

- multiple/select;
- code reading/debugging;
- structured short answer;
- small design scenario;
- session-specific data/schema task;
- progressive follow-up after an initial answer.

A full untrusted code execution sandbox is optional for MVP; code tasks can use constrained inputs/hidden deterministic checks first.

## Scoring ownership

### Platform base grade test

System-owned and deterministic/calibrated. Free-text scoring uses explicit rubric dimensions. A local LLM may propose a secondary rubric score/explanation, but deterministic/domain scoring remains the source of truth for the global grade.

### Employer-authored task

Employer owns the final evaluation. System may provide deterministic checks and score suggestions. Store the result as employer-specific evidence; do not silently alter global verified grade.

## Grade decision

Initial configurable policy:
- `>=80` + critical floors: strong pass;
- `70–79`: pass;
- `55–69`: borderline / not confirmed;
- `<55`: not confirmed.

Rules:
- failed declared-grade test does not forcibly downgrade the declaration;
- **candidate remains discoverable** with a clear `grade not confirmed` marker;
- candidate can try a lower grade;
- strong pass can offer a higher-grade test;
- default grade-change/retest cooldown: 90 days;
- confirmed employer-facing grade uses the last valid platform result, while declared/unconfirmed state remains visible.

## Leakage resistance

- per-attempt unique form;
- parameterized variants;
- large template families;
- family exposure budget/cooldown;
- rotating versions;
- anchor surface variants;
- no answer keys/client-side rubric secrets before submission;
- server-side state/timer;
- delayed detailed canonical solutions while an item family is active;
- cross-submission similarity flags.

See `AI_ASSESSMENT_INTEGRITY.md`.

## AI resistance

Do not make a probabilistic “AI-generated text detector” a pass/fail gate. Prefer:
- unique artifacts;
- progressive follow-up tied to the candidate's own answer;
- hidden tests;
- micro-variations of constraints;
- rationale/explanation tied to submitted code/design;
- disclosed minimal integrity telemetry;
- similarity analysis.

Integrity signals are advisory and reviewable, never automatic accusations.

## Synthetic grade/discrimination validation

Generate labeled synthetic candidate abilities/responses across intended grades. Validate:
- grade agreement / macro-F1;
- confusion matrix;
- equivalent-form score difference;
- retest agreement;
- item difficulty/discrimination;
- critical-domain reliability;
- grade-collapse check (detect degenerate “almost everyone same grade”).

Never force quotas or curve candidates merely to produce varied grades.

## Regular employer challenges

Short employer task, roughly 5–20 minutes, rubric-based. It can update employer-specific/freshness evidence but does not silently replace the platform grade.

## AI use inside the product

Good uses:
- resume extraction assistance;
- free-text → canonical skill mapping with review;
- bounded wording variants under a fixed template/rubric;
- employer task/rubric drafting from approved prior examples;
- explanation drafting from computed facts.

Core grading and matching must work without external AI and without GPU.
