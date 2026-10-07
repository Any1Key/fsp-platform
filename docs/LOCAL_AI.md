# Local AI strategy — CPU-only

## Constraint

The deployable system must not require a GPU. Target environment is approximately 8 CPU and 32–64 GB RAM. Core candidate assessment, scoring, matching, authentication and chat must work with AI disabled.

## Recommended role of local AI

Use local AI as an **assistant**, not a source of truth:
- propose employer task drafts;
- propose wording variants for calibrated item templates;
- extract structured fields from resume text after deterministic parsing;
- map free-form employer wording to canonical skills with human confirmation;
- draft human-readable matching explanations from already-computed score components.

Never make the local model the sole grader for the platform-wide grade.

## Employer task generation: retrieval before fine-tuning

“Learning from the employer's previous tasks” should be implemented first as retrieval + preference memory:

1. Employer creates/edits/approves tasks.
2. Store task metadata: specialization, grade, skills, format, difficulty, rubric, accepted/rejected status and employer edits.
3. Index approved examples locally.
4. When the employer creates a new vacancy/need, retrieve the most relevant prior approved tasks.
5. Give those examples plus the current need and a strict JSON schema to the local model.
6. Generate a **draft**, rubric and difficulty rationale.
7. Validate schema/constraints.
8. Employer reviews and explicitly publishes.

This gives organization-specific behavior without expensive fine-tuning and works on CPU.

## Runtime architecture

The backend now exposes an async `LocalAiPort` in `backend/app/local_ai.py`.
The current deployment constructs `DisabledLocalAiAdapter`, which returns the
same explicit `disabled` result for every request and never emits a task draft.
Employer task authoring probes this boundary through
`POST /api/v1/employer/tasks/draft-suggestion`; the response is employer-scoped
and manual authoring remains available. Possible future adapters:
- local OpenAI-compatible HTTP endpoint;
- llama.cpp/Ollama-style local runtime.

The exact runtime/model is replaceable. Prefer a small quantized instruction model (roughly 3B–8B class) if acceptable on the actual Synology CPU. Model inference is asynchronous and rate-limited.

Do not block core HTTP requests waiting indefinitely for generation. Use a PostgreSQL-backed job table or equivalent simple queue for MVP.

## Fallback behavior

If the local model is absent, slow or fails:
- employer can author tasks manually;
- template-based suggestions continue to work;
- resume parsing falls back to deterministic extraction/manual review;
- matching/scoring remains fully operational.

## Resource budget

Core profile should stay comfortably within the target host. AI is a separate optional profile/worker with configurable model memory and one inference worker by default. The load test must report core service performance separately from AI generation latency.

## Safety/privacy

No candidate resume, chat or real personal data is sent to an external AI API by default. If any external provider is ever enabled, it requires an explicit separate privacy/legal decision and configuration.
