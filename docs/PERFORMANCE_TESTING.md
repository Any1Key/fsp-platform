# Performance and load testing

## Target host

The application must not require a GPU and should be demonstrable on approximately:
- 8 CPU cores;
- 32 GB RAM minimum target;
- 64 GB RAM comfortable target.

## Profiles

Measure the **core profile** separately from optional local-AI generation. Core includes frontend, backend, PostgreSQL, Keycloak and required supporting services.

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
