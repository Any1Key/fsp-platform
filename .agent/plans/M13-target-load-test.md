# M13 — Reproducible authenticated target load test

## Purpose / user value

Provide the reproducible target workload required to measure the core platform
with real authenticated candidate/employer traffic, including Talent Radar,
profiles, invitations, matching-backed chat history and chat messages.

## Requirement IDs

- NFR-010 — stable for tens of concurrent users with a reproducible load test.
- NFR-011 — keep the target run scoped to the CPU-only core profile; optional
  local AI is not part of this workload.

## Current behavior

`docs/PERFORMANCE_TESTING.md` defines smoke and target scenarios, while
`scripts/resource-baseline.sh` only probes public bootstrap endpoints. The
`qa/load/` directory has no authenticated runner, artifact contract, or
threshold evaluation.

## Proposed design

- Add a dependency-free threaded Python runner with deterministic seeded virtual
  user assignment and a 50-user/10-minute target default.
- Accept short-lived Keycloak bearer tokens through command-line files or
  environment variables; never print or persist token values.
- Run a one-time authenticated setup that verifies candidate publication and
  verified-grade eligibility, prepares the employer need/company, creates or
  reuses one accepted invitation, and resolves a matched conversation.
- During the timed run, mix candidate and employer reads plus ordinary profile
  writes, Talent Radar/search, invitation lists, chat history and messages.
- Capture JSON, TSV, text summary, host metadata, Compose service state and
  Docker CPU/RAM snapshots under `.agent/runs/<run-id>/performance/`.
- Keep threshold evaluation explicit and fail only the target command when the
  measured run breaches NFR-010 targets; unit/contract tests use a fake HTTP
  server and do not require Docker or credentials.

## Files/modules

- `qa/load/run_load.py` — runner, setup flow, workload, metrics and artifacts.
- `qa/load/test_run_load.py` — deterministic metric/planning and fake-server
  tests.
- `qa/load/README.md` — token preparation, setup, target/smoke commands and
  artifact contract.
- `agent/test-load-contract.sh` — clean-checkout contract test.
- `Makefile` — `load-test` convenience target.
- `docs/PERFORMANCE_TESTING.md` / `docs/PERFORMANCE_RESULTS.md` — operational
  target-load contract and current evidence boundary.
- `docs/REQUIREMENTS_MATRIX.md` / `.agent/BACKLOG.md` — mark this unit and
  NFR-010 `IMPLEMENTED`; never mark `VERIFIED`.

## Data/API changes

None. Setup uses existing authenticated REST endpoints and creates only normal
demo data through those APIs. No schema, production route, or auth behavior is
changed.

## Security/privacy implications

Tokens are read from operator-provided files/environment and only sent as
Bearer headers. They are not included in logs, JSON artifacts, TSV rows, or
exception text. The runner records status/timing and route names only.

## Test plan

- Verify deterministic virtual-user role assignment and percentile calculation.
- Verify request metrics aggregate successes/errors and threshold decisions.
- Verify fake HTTP setup resolves a profile and conversation without external
  services.
- Run shell contract, Python load-runner tests, backend tests and Ruff.

## Demo/evidence

```sh
FSP_LOAD_CANDIDATE_TOKEN_FILE=/secure/candidate.tokens \
FSP_LOAD_EMPLOYER_TOKEN_FILE=/secure/employer.tokens \
python3 qa/load/run_load.py --setup --run-id target-demo
```

The default target command is documented but intentionally not executed by
unit tests. A real report requires valid Keycloak tokens and a deployed core
profile; until those are supplied, `docs/PERFORMANCE_RESULTS.md` explicitly
retains the measured-results boundary.

## Progress / decisions / surprises

- 2026-10-10: selected as the first unfinished M13 unit. Authenticated setup
  is explicit because the API correctly does not expose synthetic answer keys
  or bypasses for a production load run.
- 2026-10-10: implemented the standard-library runner, deterministic workload,
  report/artifact contract, fake-server tests and shell contract. NFR-010 is
  `IMPLEMENTED`; the external supervisor still owns the real target run and
  all verification state.
