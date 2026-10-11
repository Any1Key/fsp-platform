# Repository operating contract

You are developing the FSP Talent Platform from the supplied 2026 technical specification plus the 2026-10-06 conference Q&A working clarifications.

## Source of truth

Use these documents when relevant:
- `docs/CONFERENCE_CLARIFICATIONS_2026-10-06.md` — latest working Q&A clarifications supplied by owner;
- `docs/REQUIREMENTS_MATRIX.md` — scope and evidence;
- `docs/PRODUCT_SPEC.md` — behavior and journeys;
- `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md` — boundaries/storage;
- `docs/ASSESSMENT_ENGINE.md`, `docs/AI_ASSESSMENT_INTEGRITY.md` — assessment/anti-leak/anti-AI design;
- `docs/EMPLOYER_ASSESSMENTS.md` — employer hiring pipeline/tasks;
- `docs/MATCHING_ENGINE.md`, `docs/CHAT_AND_MATCHING.md` — ProofMatch, match lifecycle and chat;
- `docs/LOCAL_AI.md` — CPU-only optional AI strategy;
- `docs/BRAND_GUIDE.md`, `docs/DESIGN_SYSTEM.md`, `docs/UI_ACCEPTANCE_CRITERIA.md` — UI;
- `docs/SECURITY.md`, `docs/LEGAL_152FZ.md` — security/privacy engineering;
- `docs/PERFORMANCE_TESTING.md` — load/resource validation;
- `.agent/PLANS.md` — substantial feature planning;
- `docs/source/TZ_2026.pdf` — original source specification.

If a conference clarification appears to conflict with the original source, preserve the original requirement, record the conflict/decision in `.agent/DECISIONS.md`, and implement the safest latest working interpretation unless owner confirmation is required.

## Product priorities

1. Reverse recruitment is the core: employer discovers candidates and initiates a salary-bearing invitation.
2. Base assessment/category assignment must be objective, comparable, unique per candidate/attempt and resistant to leaked answers.
3. Do not use an unreliable AI-content detector as a pass/fail gate; use AI-resistant assessment design and advisory integrity signals.
4. Matching must use verified evidence, show confidence/gaps and be explainable; no-FSP and unconfirmed-grade candidates remain valid searchable states.
5. Candidate contacts and chat stay locked before match; accepted invitation creates match and unlocks internal communication.
6. Employers can configure additional stages and grade their own tasks; those results do not silently overwrite global grade.
7. Working Keycloak/OIDC and `.ru` registration restriction are demo requirements.
8. FSP history is a bounded positive evidence source, never a prerequisite.
9. Core must run without GPU on ~8 CPU / 32–64 GB RAM and must be load-tested.
10. Complete candidate/employer journeys must work end-to-end with responsive branded UI.

## Work protocol

For substantial work:
1. identify exact requirement IDs;
2. inspect relevant docs/code;
3. create/update an ExecPlan in `.agent/plans/`;
4. implement the smallest coherent end-to-end slice;
5. add/modify automated tests;
6. update docs and evidence;
7. mark at most `IMPLEMENTED`; external supervisor owns `VERIFIED`.

For a small fix, an ExecPlan is optional.

## Definition of done

A UI alone, endpoint alone, model alone, mock alone, AI-generated draft, or successful build alone is not done.
A feature is done only when its end-to-end behavior is tested against requirement evidence.

Never weaken/delete valid tests merely to get green status.

## Architecture

Prefer a modular monolith:
- Next.js frontend;
- FastAPI backend;
- PostgreSQL;
- Keycloak/OIDC;
- REST + WebSocket where justified;
- external integrations behind adapters;
- optional CPU-local AI worker behind an adapter, never required for core operation.

Keep explicit module boundaries and dependency direction.

## UI

Build a production-quality responsive SaaS interface, not a generic admin template.
Follow official FSP visual identity and brand assets.
Required quality: desktop, laptop, tablet and mobile.
Implement loading, empty, error, success, disabled and unconfirmed-grade states.
The employer experience should visibly emphasize Talent Radar / verified evidence / ProofMatch rather than a conventional resume feed.

## Assessment

Do not use either of these as the primary mechanism:
- one fixed question bank/form;
- unconstrained “LLM invents and grades a unique test”.

Use calibrated blueprints, template families, per-attempt parameterization, anchor variants, exposure control, progressive follow-ups and deterministic rubrics. Ensure different candidates do not receive identical forms. Validate grade discrimination with labeled synthetic data; never force grade quotas.

## Employer tasks

Employer-authored stages/tasks are employer-owned and employer-graded. Local AI may draft based on approved employer history, but employer must review/publish. Employer-specific evidence does not silently change platform-wide grade.

## Matching

Implement ProofMatch / Evidence-Graph Reverse Matching. Never rank on protected/sensitive personal traits. Age is never a ranking feature. Do not use FSP history as a hard gate. Keep unconfirmed-grade candidates searchable with an explicit label. Return score breakdown, confidence and human-readable reasons/gaps.

## Chat

No direct messaging before a valid match. Enforce server-side. Accepted reverse-recruitment invitation creates match and unlocks authorized conversation/contact flow.

## Security/privacy

Never commit secrets or send real PII/chat/minor documents to Telegram. Do not log passwords/tokens or unnecessary PII. Use server-side role checks and preserve contact/chat unlock rules with integration tests. Treat 152-FZ controls as engineering requirements without claiming legal certification.

## Resource policy

Do not introduce GPU dependencies. Optional local AI must degrade gracefully when disabled and must not block core flows. Measure the actual target load and resource use.

## Git

Use the configured agent branch. Keep commits scoped. Never force-push/rewrite shared history. Supervisor may checkpoint only after verification.

## Stop conditions

Continue autonomously unless:
- a required external credential is missing;
- the source requirement is materially ambiguous and cannot be safely defaulted;
- recovery reaches configured retry limit;
- proceeding requires destructive host-level actions.

Record blockers in `.agent/PROBLEMS.md`.

## DEADLINE MODE — 2026-10-11

Hard submission deadline: 2026-10-11 23:59 MSK.

If a coherent work unit is already in progress, finish it without broadening its scope.
For all subsequent work units, optimize for submission readiness and minimize the
number of remaining autonomous cycles.

Rules:
- Do not start optional product features.
- Do not perform cosmetic polish unless it blocks jury acceptance or a requirement.
- Batch closely related unfinished backlog items from the same milestone into one
  coherent work unit where this can be done safely.
- Preserve all existing verification, regression, recovery and external-supervisor gates.
- Never weaken or delete valid tests merely to save time.
- P0 and P1 defects must be fixed.
- P2 defects may be documented and deferred when they do not block requirements,
  the jury demo, security, deployment, or acceptance.
- Do not deliberately consume all remaining cycles.

Priority:
1. Finish all remaining submission-blocking M15 security/privacy work.
2. Complete M16: OpenAPI/docs/dependency audit, deterministic demo reset,
   clean-clone deployment and complete jury E2E.
3. Complete M17: requirements audit, P0/P1/P2 triage and P0/P1 fixes.
4. Run final CPU-only deployment, load validation and responsive screenshot evidence.
5. Set READY only through the existing external acceptance mechanism.

The objective is a complete, demonstrable, deployable submission before the deadline,
not maximum feature count.
