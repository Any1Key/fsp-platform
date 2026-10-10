# Authenticated load tests

`run_load.py` is the reproducible core-profile runner for NFR-010. It uses
Python's standard library, so the load tool does not add a runtime dependency
or a GPU dependency. The timed workload exercises real authenticated candidate
and employer endpoints: profiles, candidate dashboard/invitations, employer
company/hiring need, Talent Radar, invitation-backed matched chat history and
messages.

The runner never creates fake bearer tokens. Supply one or more fresh Keycloak
access tokens per role in files (one token per line) or through the equivalent
comma-separated environment variables. Token files are operator input and are
never copied into the report.

## Prepare and run

The first run should prepare a normal accepted invitation and chat conversation
through the existing API. The candidate must already have a verified base
assessment because the invitation route correctly rejects unconfirmed grades.

```sh
FSP_LOAD_CANDIDATE_TOKEN_FILE=/secure/candidate.tokens \
FSP_LOAD_EMPLOYER_TOKEN_FILE=/secure/employer.tokens \
python3 qa/load/run_load.py --setup --run-id target-$(date -u +%Y%m%d-%H%M%S) \
  --fail-on-thresholds
```

Defaults are the documented target: 50 virtual users, a 60-second ramp and a
600-second timed run. Use `--users 10 --duration-seconds 120` for the smoke
profile. To reuse prepared data without setup, pass
`--candidate-profile-id` and `--conversation-id` instead.

The runner records `report.json`, `summary.txt`, `request-times.tsv`,
`host-specs.txt`, Compose state and Docker CPU/RAM snapshots under
`.agent/runs/<run-id>/performance/`. `--fail-on-thresholds` applies the
targets from `docs/PERFORMANCE_TESTING.md`; setup failures always exit 2.

```sh
python3 -m unittest discover -s qa/load -p 'test_*.py'
./agent/test-load-contract.sh
```

The bootstrap CPU-only resource baseline remains separate:
`scripts/resource-baseline.sh` probes public health/system endpoints and is not
evidence for the authenticated NFR-010 target run.
