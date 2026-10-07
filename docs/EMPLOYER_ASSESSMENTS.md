# Employer assessments and hiring pipeline

## Purpose

In addition to the platform-wide verified grade, an employer can run job-specific stages for matched candidates.

## Hiring pipeline

A hiring need/vacancy can define ordered stages such as:
1. FSP/platform verified-profile review;
2. employer task;
3. questionnaire;
4. portfolio/code review;
5. interview/custom stage;
6. final decision.

Stages can be optional/required and reordered before candidates enter them.

The current implementation exposes this configuration through the employer
Hiring Pipeline builder. It persists a one-to-one pipeline for the hiring need,
keeps the platform-review and final-decision boundary stages, and supports up
to twelve ordered stages. New salary-bearing invitations receive a safe stage
snapshot, which is shown to the candidate before the accept/decline decision.
Employer task authoring is now available for `employer_task` stages. The
employer creates a private draft, edits its content, and explicitly publishes
an immutable version. Editing a published task creates the next draft version;
task content remains employer-only until the candidate-assignment unit runs.
After match, the candidate-assignment unit exposes only the assigned published
version's task instructions and safe metadata.

## Employer task authoring

Employer can:
- write a task manually;
- choose target skills and expected grade;
- set estimated duration/deadline;
- add rubric dimensions/points;
- attach safe supporting files later if needed;
- request a local-AI draft based on the hiring need and previously approved employer tasks;
- edit everything before publishing.

The current M10 foundation exposes the optional adapter boundary and an explicit
AI-off state in the authoring panel. Published versions are recorded as
company-scoped approved examples and the draft-suggestion probe retrieves a
bounded, relevance-ranked set for the optional adapter. The authoring panel
shows the retrieved example metadata. When the adapter is disabled, no draft is
pretended or persisted; the employer continues with the manual editor. Enabled
generation, feedback memory, and background jobs are separate follow-up units.

The current authoring slice validates target skills against the active
taxonomy, expected grade, estimated duration, deadline policy, and rubric
dimensions/points. It records the authenticated employer identity on the task
and each version. Candidate assignment and submission are match-bound. The
candidate assignment/submission unit is now implemented: accepting an invitation creates
match-bound assignments for published task versions, and the candidate can
submit numbered response revisions until the server-derived deadline. A later
publication is reconciled to existing matches only when no assignment exists;
an existing candidate assignment never changes its preserved version.
The employer can review matched submissions and grade them in the separate
employer evaluation unit described below.

The product must clearly show when a task is employer-authored rather than part of the platform-wide grade assessment.

## Grading authority

- Platform base grade assessment: system-owned deterministic grading/calibration.
- Employer-authored task: employer-owned grading.
- System may calculate deterministic subchecks or suggest a rubric score, but employer confirms the final employer-stage result.

Employer results are stored as employer-specific evidence. They do not silently modify the global verified grade.

## Employer evaluation

The employer-only `GET /api/v1/employer/task-assignments` route lists matched
assignments belonging to the employer's company, including the preserved task
version, rubric and candidate submission history. `PUT
/api/v1/employer/task-assignments/{assignment_id}/evaluation` validates every
rubric dimension against that immutable assigned version, derives a 0–100
score from awarded points, and upserts the employer's final evaluation. A
candidate submission is required before grading. The employer may keep the
evaluation as a draft or explicitly release score and feedback to the
candidate.

The database stores one evaluation per assignment with the grading employer,
rubric awards, score, feedback, release state and timestamps. Ownership is
checked through the matched employer and company/hiring need. Candidate
responses expose only released score/feedback; they never expose the employer
rubric or unreleased evaluation. The write path does not read or update the
platform assessment result, so employer evidence remains job-specific.

## Candidate experience

Before accepting an invitation, candidate can see that additional stages are expected and their approximate format/time. Detailed employer tasks become available according to the pipeline policy after the match/acceptance event.

Candidate sees:
- stage status;
- task/deadline;
- submission history;
- employer evaluation/feedback if released;
- next step.

The candidate task panel exposes the assigned stage/status, task/deadline and
the candidate's own submission history. Once the employer explicitly releases
an evaluation, the panel shows its score and feedback; rubric details and
unreleased evaluations remain employer-only.

## Audit

Record who created/edited/published/graded a task and when. Preserve the task version assigned to each candidate.
