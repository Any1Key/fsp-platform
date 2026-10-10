# M13 — CPU/RAM and latency/error report

## Purpose / user value

Make each authenticated core-profile load run produce one auditable report
containing request latency/error thresholds and Docker CPU/RAM observations.
The report must distinguish missing resource telemetry from a measured zero and
must not imply that a real target run happened when credentials or a deployed
core profile were not supplied.

## Requirement IDs

- NFR-010 — stable for tens of concurrent users with a reproducible load test;
  report request count, error rate, p50/p95/p99 and threshold decisions.
- NFR-011 — core system requires no GPU and targets approximately 8 CPU /
  32–64 GB RAM; include CPU/RAM snapshots from the core Compose services.

## Current behavior

`qa/load/run_load.py` already executes the authenticated workload and writes
raw Docker stats before and after the run, but `report.json` only contains HTTP
metrics. The timed run also has no in-run resource snapshot, so CPU/RAM
evidence is difficult to consume consistently.

## Implementation

- Capture a `during` Docker stats snapshot halfway through the timed workload.
- Parse Docker's human-readable CPU and memory fields without adding runtime
  dependencies; retain the original display values for auditability.
- Add a `resources` report section with per-phase rows, availability, and peak
  CPU/memory values. Missing Docker telemetry is explicit and does not become a
  false zero.
- Keep the existing request threshold semantics and add unit coverage for
  resource parsing, aggregation, and report-safe missing-data behavior.
- Document the report schema and mark only the implementation as complete;
  external target measurement remains pending and no READY/VERIFIED state is
  changed.

## Files/modules

- `qa/load/run_load.py` — snapshot scheduling, parsing, aggregation and JSON
  report output.
- `qa/load/test_run_load.py` — deterministic parser/aggregation tests.
- `qa/load/README.md` / `docs/PERFORMANCE_TESTING.md` — operator report
  contract.
- `docs/PERFORMANCE_RESULTS.md` — evidence boundary and implemented report
  fields.
- `docs/REQUIREMENTS_MATRIX.md` / `.agent/BACKLOG.md` — implementation status
  only.

## Security/privacy implications

Only container names, CPU percentages, memory usage and route/timing metadata
are persisted. Bearer tokens remain excluded from report and snapshot files.

## Test plan

- Run the load-runner unit tests and shell contract test.
- Run the repository verification checks that cover the changed contract.
- Do not start a target load run without operator-supplied credentials.

## Evidence boundary

The report writer is implementation evidence for NFR-010/NFR-011. A real
authenticated 50-user target report still requires the external supervisor to
provide valid tokens and run the core Compose profile; it is not claimed by
this work unit.

## Progress

- 2026-10-10: implemented before/during/after Docker snapshot reporting,
  normalized CPU/RAM aggregation, latency/error report documentation and unit
  coverage. NFR-010 remains `IMPLEMENTED`; no verification or READY state was
  changed.
