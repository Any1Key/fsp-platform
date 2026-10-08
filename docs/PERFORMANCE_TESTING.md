# Performance and load testing

## Target host

The application must not require a GPU and should be demonstrable on approximately:
- 8 CPU cores;
- 32 GB RAM minimum target;
- 64 GB RAM comfortable target.

## Profiles

Measure the **core profile** separately from optional local-AI generation. Core includes frontend, backend, PostgreSQL, Keycloak and required supporting services.

The repository also defines an opt-in `local-ai` Compose profile. It is
CPU-bounded to four CPUs and 8 GiB by default, with one parallel request and
one loaded model. It is not started by `docker compose up` and is intentionally
excluded from `scripts/resource-baseline.sh`; use the local-AI runbook in
`docs/LOCAL_AI.md` and capture its container stats separately. A local-model
smoke run is operational evidence for the optional profile, not evidence that
the core system requires AI or a GPU.

## Load scenarios

### Smoke
- 10 concurrent users;
- 2–3 minutes;
- candidate profile reads, search, invitation list, basic writes.

### Target
- ramp to 50 concurrent users;
- hold 10 minutes;
- mixed candidate/employer traffic;
- include candidate search/matching, profile, invitation transitions and chat history/messages.

### Optional stress
- 100 concurrent users;
- identify saturation point; no release gate unless project time permits.

## Initial acceptance targets

These are project targets and may be tuned after measuring the real NAS:
- HTTP error rate < 1% in target scenario;
- common read p95 <= 1.0 s;
- search/matching p95 <= 2.0 s;
- ordinary write p95 <= 1.5 s;
- no unbounded memory growth;
- all services remain healthy after the run.

Keycloak login can be measured separately from already-authenticated application traffic.

## Tooling

Prefer a reproducible scripted tool such as Locust or k6. Keep scenarios and thresholds in the repository. Capture:
- request counts;
- error rate;
- p50/p95/p99;
- Docker CPU/RAM snapshot before/during/after;
- database slow-query observations.

Write actual results to `docs/VALIDATION_RESULTS.md` and keep raw reports under `.agent/runs/<run-id>/performance/`.

## Bootstrap CPU-only baseline

Before the final authenticated target-load suite exists, run the core-profile
baseline from the repository root:

```sh
BASELINE_ITERATIONS=20 ./scripts/resource-baseline.sh
```

The runner renders the effective Compose configuration and fails if a GPU
runtime, GPU device request, or CUDA/NVIDIA device reservation is present. It
then starts only the core services, probes real bootstrap API reads while
Compose readiness checks exercise the database-backed path, and records host
metadata, service health, request timings, and Docker CPU/RAM snapshots in
`.agent/runs/<run-id>/performance/`.

This bootstrap probe is resource evidence for NFR-011; it is deliberately not
the NFR-010 release load test. The latter must wait until authenticated
candidate/employer search, invitations, matching, and chat endpoints exist and
must exercise those representative journeys at the smoke and target
concurrency described above.
