# Conference Q&A clarifications — 2026-10-06

## Source status

This document records live conference Q&A notes supplied by the project owner on 2026-10-06.
It is a **working clarification source**, not a verbatim organizer transcript. The original 2026 technical specification remains the baseline.
Where these notes clarify an ambiguous part of the specification, implement the clarification. Where an apparent conflict exists, record it in `.agent/DECISIONS.md` and make the safest demo-capable choice without silently deleting an original requirement.

## Organizer clarifications reported by the project owner

1. Candidate assessments must be resistant to sharing of tasks and answers between participants.
2. Different candidates must not receive identical tests.
3. It is desirable to add protection against use of generative AI during assessment.
4. Synthetic tests/data will be used to check that the assessment does not collapse to the same grade for everyone.
5. The platform evaluates the base grade assessment itself.
6. If an assessment/task is authored by an employer, the employer evaluates that task.
7. Employers should be able to add extra tests or additional hiring stages for candidates.
8. A 16-year-old candidate must have a workflow to attach the required parent/legal-representative permission/consent documentation.
9. Production/demo infrastructure should not require a GPU. Target host: about 8 CPU and 32–64 GB RAM.
10. A candidate who did not confirm the declared grade must not be hidden from employer search; the UI should clearly mark the grade as not confirmed.
11. Grade-change/retest frequency must be limited.
12. Keycloak integration should be demonstrated and preferably operate in the prototype.
13. Registration by email is limited to addresses whose domain ends in `.ru`.
14. FSP ID linking should be demonstrated. Synthetic FSP achievements may be used in the hackathon and should affect employer ranking as a bounded positive signal.
15. The matching mechanism should be distinctive, not a conventional resume-keyword search.
16. The solution is expected to be designed within the requirements of Russian Federal Law 152-FZ on personal data.
17. The finished service must be load-tested.
18. After a successful match, employer and candidate should be able to communicate inside the platform and exchange contacts. Before the match, neither side can message the other.

## Product decisions adopted for the project

### Assessment leak resistance

Use a calibrated test factory, not a fixed question set:
- competency blueprints per specialization/grade;
- large template families;
- per-attempt secure seed and parameterized variants;
- exposure budgets and template-family cooldowns;
- hidden anchor/calibration items;
- server-side timing/state and no answer keys before completion;
- delayed detailed answer review until the exposure window closes;
- answer/code similarity checks across attempts as advisory integrity evidence.

### AI-resistant assessment

Do **not** rely on an “AI detector” as a decisive gate. Such detectors are not sufficiently reliable for a hiring decision. Instead make the test harder to outsource:
- unique session-specific code/data/schema fragments;
- progressive questions where later prompts depend on the candidate's previous answer;
- short “change one constraint” follow-ups;
- hidden tests for code/debugging tasks;
- explanation/rationale fields tied to the submitted solution;
- limited-time micro-tasks;
- optional copy/paste, focus-loss and abnormal-timing telemetry only as disclosed, advisory integrity signals;
- normalized AST/text similarity checks for copied solutions;
- integrity score shown as “signals requiring review”, never automatic guilt.

No webcam, keystroke biometrics or invasive proctoring is required for the MVP.

### Synthetic grade validation

Never force a grade distribution or introduce quotas just to make grades different. Generate labeled synthetic candidate abilities/responses across Junior/Middle/Senior and verify that the grading pipeline reproduces the expected distinctions. Track confusion matrix, macro-F1/grade agreement, retest stability and a grade-collapse check.

### Employer-authored assessments

Provide an employer “Hiring Pipeline” with ordered stages. Employer task stages are authored and graded by the employer. System assistance may propose a rubric and task draft, but the employer is the authority for employer-authored stages. Results are employer-specific evidence and do not silently overwrite the platform-wide verified grade.

### Local AI assistance

Core functionality must work without any external LLM and without GPU. Optional local AI runs asynchronously on CPU through a replaceable adapter. Prefer retrieval from the employer's own previous approved tasks plus constrained generation over fine-tuning on the production host.

### Minor candidate flow

Store age/date-of-birth only in the private profile and never use it in matching. For candidates below the configured adult threshold, provide private upload/status of parent/legal-representative consent documents. Exact legal wording/document requirements must remain configurable and subject to legal review.

### Match and chat

For reverse recruitment, a **match** is created when the candidate accepts an employer invitation (or an equivalent candidate-initiated application reaches the accepted/matched state). Only then is internal messaging enabled. Chat and contact-unlock authorization must be enforced server-side.

## Open questions to confirm with organizers if possible

- Does `.ru` mean any address ending in `.ru`, or only corporate domains? Is `.рф` intentionally excluded?
- For minors, which exact document/consent wording and age threshold should be required?
- Should employer-authored assessment results ever influence the global verified grade, or only employer-specific evidence? Project default: employer-specific only.
- Is chat unlocked strictly after candidate accepts the invitation? Project default: yes.
- Should detailed solutions to base tests ever be shown to candidates? Project default: only after the item family/exposure window is retired, while score/rubric feedback may be shown earlier.
