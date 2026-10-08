# M10 — Optional CPU-local runtime profile

## Purpose / user value

Make the already-tested optional local-AI adapter runnable on a CPU-only host
without changing the core profile. An operator can start a bounded local
runtime, load an explicitly selected model, and use the existing asynchronous
employer task-draft queue while candidate data and core services remain
independent of the model.

## Requirement IDs

- `EMP-014` — local CPU AI can propose employer task/rubric drafts from the
  current need and approved task history.
- `NFR-011` — core system requires no GPU and targets approximately 8 CPU /
  32–64 GB RAM.
- `NFR-012` — optional local AI is isolated, asynchronous and has a
  deterministic fallback.

## Current behavior

The backend has a replaceable OpenAI-compatible `LocalAiPort`, a durable
company-scoped queue, and an AI-off fallback, but Compose does not provide a
runtime service or a repeatable model bootstrap path. `LOCAL_AI_BASE_URL`
already points at the intended service name, so enabling the adapter without a
matching service produces failed jobs.

## Proposed design

- Add a Compose `local-ai` profile using the pinned CPU-capable Ollama image.
- Apply explicit CPU, memory, one-model and one-parallel-request bounds; do not
  add GPU/device settings or make the core services depend on this profile.
- Add a safe bootstrap script that starts the core plus local-AI service,
  requires `LOCAL_AI_ENABLED=true` and a non-empty `LOCAL_AI_MODEL`, pulls only
  that configured model, and restarts the backend with the configured adapter.
- Add a Compose contract test proving profile isolation, resource bounds and
  no GPU configuration, plus documentation for enabling, disabling and
  measuring the optional profile separately.

## Files/modules

- `docker-compose.yml`
- `.env.example`
- `scripts/local-ai-profile.sh`
- `agent/test-local-ai-profile-contract.sh`
- `agent/test-ci-contract.sh`
- `Makefile`
- `docs/LOCAL_AI.md`
- `docs/PERFORMANCE_TESTING.md`
- `docs/REQUIREMENTS_MATRIX.md`
- `.agent/BACKLOG.md`

## Data/API changes

None. The existing local-AI HTTP adapter and async polling API are used as-is.

## Security/privacy implications

The profile is opt-in and local-only. It accepts no candidate resume, chat,
contact or minor-document data. The model volume is separate from core data,
the service is not exposed by default, and the backend keeps its existing
sanitized employer-task context boundary.

## Test plan

- Render the default and `local-ai` Compose profiles and inspect service,
  profile, CPU/memory, and GPU/device fields.
- Run the repository CI contract suite.
- Run focused local-AI tests and the full backend suite where the locked
  environment is available.

## Demo/evidence

The runbook documents setting `LOCAL_AI_ENABLED=true` and
`LOCAL_AI_MODEL=<model>` in `.env`, then running `make local-ai-up`;
`docker compose --profile local-ai ps` and
`docker stats` provide runtime evidence. Core resource-baseline runs continue
to exclude the optional service.

## Progress / decisions / surprises

- Plan created before implementation.
- The current host exposes 4 CPUs and about 31 GiB RAM, so the profile is
  bounded to 4 CPUs and 8 GiB by default and remains optional.
- Implemented the opt-in Compose service, model bootstrap helper, Make target,
  Compose contract test, runbook updates and `IMPLEMENTED` evidence updates.
- Focused M10/migration tests pass (16), the full backend suite passes (108),
  frontend typecheck passes, and the CI/resource/Compose contracts pass.
- No model was pulled during repository verification; the optional runtime
  remains an operator-started profile and external supervisor owns runtime
  verification.
