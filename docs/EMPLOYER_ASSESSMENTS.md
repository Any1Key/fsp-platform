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
task content remains employer-only until the later candidate-assignment unit.

## Employer task authoring

Employer can:
- write a task manually;
- choose target skills and expected grade;
- set estimated duration/deadline;
- add rubric dimensions/points;
- attach safe supporting files later if needed;
- request a local-AI draft based on the hiring need and previously approved employer tasks;
- edit everything before publishing.

The current authoring slice validates target skills against the active
taxonomy, expected grade, estimated duration, deadline policy, and rubric
dimensions/points. It records the authenticated employer identity on the task
and each version. Candidate assignment, submission, and employer evaluation
are separate M09 units and are not implied by publication.

The product must clearly show when a task is employer-authored rather than part of the platform-wide grade assessment.

## Grading authority

- Platform base grade assessment: system-owned deterministic grading/calibration.
- Employer-authored task: employer-owned grading.
- System may calculate deterministic subchecks or suggest a rubric score, but employer confirms the final employer-stage result.

Employer results are stored as employer-specific evidence. They do not silently modify the global verified grade.

## Candidate experience

Before accepting an invitation, candidate can see that additional stages are expected and their approximate format/time. Detailed employer tasks become available according to the pipeline policy after the match/acceptance event.

Candidate sees:
- stage status;
- task/deadline;
- submission history;
- employer evaluation/feedback if released;
- next step.

## Audit

Record who created/edited/published/graded a task and when. Preserve the task version assigned to each candidate.
