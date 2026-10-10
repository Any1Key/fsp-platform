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

The repository's reproducible runner is `qa/load/run_load.py`; it uses only
Python's standard library and is intentionally independent of optional local
AI. Keep scenarios and thresholds in the repository. Capture:
- request counts;
- error rate;
- p50/p95/p99;
- Docker CPU/RAM snapshot before/during/after, summarized in the report's
  `resources` section and retained as raw `*-docker-stats.tsv` files;
- database slow-query observations.

Write actual load results to `docs/PERFORMANCE_RESULTS.md` and keep raw
reports under `.agent/runs/<run-id>/performance/`.

The authenticated runner's `report.json` is the canonical machine-readable
report. Its `metrics` object contains request/error and latency percentiles;
its `thresholds` object records the four NFR-010 checks; and its `resources`
object contains per-phase container rows, `available`, `peak_cpu_percent` and
`peak_memory_used_bytes`. A missing Docker stats command is explicit in that
object and must not be interpreted as measured zero resource use.

The authenticated runner accepts operator-supplied Keycloak access-token files
(one token per line), performs an explicit setup flow for a verified candidate,
employer need and accepted invitation (including the invitation transition),
then runs the timed mixed workload. It does not print or persist tokens. See
`qa/load/README.md` for the target and smoke commands. A load harness or
fake-server test is implementation evidence; NFR-010 is only externally
verified after a real target run on the core profile.

## Bootstrap CPU-only baseline

For a quick CPU-policy and service-startup check independent of authenticated
target traffic, run the core-profile baseline from the repository root:

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
the NFR-010 release load test. The authenticated runner exercises the
candidate/employer search, invitations, matching-backed chat and profile
journeys at the smoke and target concurrency described above.
