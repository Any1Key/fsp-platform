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

### Implemented approved-task memory slice

Published employer task versions are immutable approved examples. Publication
writes a company-scoped `employer_task_example` index row containing only the
need specialization/grade, target skills, duration/deadline metadata and audit
reference; the task version remains the source for the full prompt context.
Existing published/retired versions are indexed during migration as approved
history.

`POST /api/v1/employer/tasks/draft-suggestion` retrieves at most five approved
examples for the authenticated employer. Retrieval is deterministic and
explainable: matching specialization, grade, required skills and preferred
skills contribute to the ranking, with approval time and ID as stable
tie-breakers. The response exposes only the employer's own metadata and
relevance matches, while the replaceable `LocalAiPort` receives the sanitized
full examples as bounded generation context.

The current deployment still uses `DisabledLocalAiAdapter`, so retrieval does
not pretend to generate a draft and manual authoring remains available. An
explicit opt-in local runtime can now generate a constrained JSON draft from
that context. The server validates the returned title, instructions, current
grade, current-need skills, time limits, rubric and difficulty rationale before
returning it. The employer can apply the suggestion to the editable form, but
the draft is never persisted or published automatically. The authoring panel
records an explicit employer decision as `approved`, `edited`, or `rejected`.
Approved and edited decisions retain the need-validated reviewed draft and an
optional bounded note; rejected decisions retain only the decision/note. This
feedback is company-scoped review history and does not enter approved-task
generation memory until the employer separately saves and publishes a task
version.

### Constrained draft generation

Set `LOCAL_AI_ENABLED=true` and provide `LOCAL_AI_MODEL` to enable the
OpenAI-compatible adapter. `LOCAL_AI_BASE_URL` defaults to
`http://local-ai:11434` and the adapter calls `/v1/chat/completions` with JSON
mode and a bounded timeout from `LOCAL_AI_TIMEOUT_SECONDS`. The default remains
AI-off. A missing model, transport/timeout error, malformed JSON or schema/
constraint violation returns an explicit failed suggestion and leaves manual
authoring available.

The generated contract is intentionally narrower than the task-version model:
it includes `title`, `instructions`, `target_skills`, `expected_grade`,
`estimated_minutes`, `deadline_hours`, `rubric`, and advisory
`difficulty_rationale`. Required skills must be included, target skills must
come from the current need, and the grade must match the need. Human review and
explicit publication remain mandatory. Generation is now a separate durable
job path: when an optional adapter is enabled,
`POST /api/v1/employer/tasks/draft-suggestion` stores a sanitized
company-scoped job and returns `202` with a job ID; the employer polls
`GET /api/v1/employer/tasks/draft-suggestion/jobs/{job_id}`. A single optional
CPU-local worker claims jobs from the table, applies the configured timeout,
and persists either the validated draft or a safe failure reason. The request
thread never waits for model inference. Disabled mode remains an immediate
deterministic response.

The queue enforces both a per-company active-job limit and a rolling request
limit (`LOCAL_AI_MAX_ACTIVE_JOBS_PER_COMPANY` and
`LOCAL_AI_RATE_LIMIT_PER_MINUTE`). A limit returns `429` with `Retry-After`;
it never blocks manual task authoring. Jobs and polling are company-scoped, so
one employer cannot inspect another employer's generation context or result.

## Runtime architecture

The backend exposes an async `LocalAiPort` in `backend/app/local_ai.py` and a
PostgreSQL-backed `employer_task_draft_job` queue. The current deployment
constructs `DisabledLocalAiAdapter`, which returns the same explicit `disabled`
result for every request and never emits a task draft. Employer task authoring
probes this boundary through `POST /api/v1/employer/tasks/draft-suggestion`;
enabled generation is polled through the job endpoint and manual authoring
remains available. Possible future adapters:
- local OpenAI-compatible HTTP endpoint;
- llama.cpp/Ollama-style local runtime.

The exact runtime/model is replaceable. Prefer a small quantized instruction model (roughly 3B–8B class) if acceptable on the actual Synology CPU. Model inference is asynchronous, single-worker, rate-limited, and timeout-bounded.

The AI-off fallback is an end-to-end manual path, not only a status message:
the disabled suggestion response is immediate, has `status=disabled`,
`draft=null`, and no `job_id`; it does not enqueue a local-AI job. The employer
can then create, save, and explicitly publish a task through the normal
employer-task API/UI. This path is covered by
`test_ai_off_fallback_keeps_manual_task_authoring_available_without_queueing`.

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
