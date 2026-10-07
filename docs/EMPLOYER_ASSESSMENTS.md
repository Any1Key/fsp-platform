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
Detailed employer task authoring and candidate assignment remain subsequent
M09 units.

## Employer task authoring

Employer can:
- write a task manually;
- choose target skills and expected grade;
- set estimated duration/deadline;
- add rubric dimensions/points;
- attach safe supporting files later if needed;
- request a local-AI draft based on the hiring need and previously approved employer tasks;
- edit everything before publishing.

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
