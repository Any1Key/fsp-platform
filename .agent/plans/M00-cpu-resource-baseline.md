# M00 — CPU-only core resource baseline

## Purpose / user value

Provide repeatable evidence that the bootstrap core profile can start and serve
real API traffic on a CPU-only host, with host and container resource snapshots
available for later performance comparison.

## Requirement IDs

- NFR-011 — core system requires no GPU and targets approximately 8 CPU / 32–64
  GB RAM.
- M00 — CPU-only resource baseline.
- NFR-010 — supported by a reproducible measurement harness, but the final
  tens-of-concurrent-users target remains a later validation unit.

## Current behavior

The Compose graph has no GPU service configuration, but the repository has no
executable resource baseline or captured bootstrap resource evidence. The
performance docs only contain targets and a not-measured placeholder.

## Proposed design

- Add a shell harness under `scripts/` that renders Compose as JSON and rejects
  GPU runtime/device declarations before starting the core services.
- Probe `/health` and `/api/v1/system/info` repeatedly, while the Compose
  health checks exercise the database-backed readiness path. Record request
  timings/statuses without storing response bodies or environment secrets.
- Capture Docker host information, service health, and before/during/after
  container CPU/RAM snapshots under `.agent/runs/<run-id>/performance/`.
- Keep the bootstrap probe explicitly separate from the later authenticated
  candidate/employer target load scenario.

## Files/modules

- `scripts/resource-baseline.sh` — reproducible CPU-only baseline runner.
- `agent/test-resource-baseline-contract.sh` — static contract test for the
  runner and Compose CPU-only policy.
- `.github/workflows/ci.yml`, `agent/test-ci-contract.sh` — run the contract in
  CI.
- `docs/PERFORMANCE_TESTING.md`, `docs/PERFORMANCE_RESULTS.md` — procedure,
  scope, and measured baseline evidence.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — implementation status.

## Data/API changes

No application API or persistence changes. The runner uses existing bootstrap
endpoints and writes only raw measurement artifacts in `.agent/runs/`.

## Security/privacy implications

The runner never serializes Compose configuration (which could contain
passwords), API response bodies, tokens, or chat/profile data into the report.
Docker service logs are outside this unit’s evidence output.

## Test plan

- Run the resource-baseline contract locally and in CI.
- Run the baseline on the available Docker host and inspect generated evidence.
- Run the backend test suite and Compose configuration validation.

## Demo/evidence

The baseline report is raw evidence, not a claim that the final NFR-010 target
load has passed. NFR-011 can be marked IMPLEMENTED after the harness and a real
CPU-only run are present; external supervision owns VERIFIED status.

## Progress / decisions / surprises

- 2026-10-06: selected as the first unfinished work unit in M00.
- 2026-10-06: kept the probe small and unauthenticated because identity,
  matching, invitation, and chat endpoints are not implemented yet; those
  representative target-load requests belong to the later completed modules.
- 2026-10-06: removed repeated assessment creation after the first run showed
  that the assessment exposure budget correctly returns 409 for excess writes;
  the baseline now measures stable core reads and remains rerunnable.
- 2026-10-06: recorded a clean rerun on Docker 24.0.2 with 4 CPUs and 31.24
  GiB exposed memory: 40 requests, 0 errors, and overall p95 0.004331 s.
