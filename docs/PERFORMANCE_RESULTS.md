# Performance / load-test results

Status: **BOOTSTRAP CPU-ONLY BASELINE RECORDED; TARGET LOAD NOT YET MEASURED**

## Bootstrap core-profile baseline

- Run ID: `20261006-m00-resource-baseline-rerun`
- Command: `BASELINE_ITERATIONS=20 ./scripts/resource-baseline.sh`
- Host: Docker Server 24.0.2; 4 CPUs; 33,544,966,144 bytes Docker memory
  (~31.24 GiB); Linux 4.4.302+ x86_64
- Services: app-db, keycloak-db, mailpit, keycloak, backend, frontend
- CPU policy: rendered Compose passed the no-GPU runtime/device check
- Requests: 40 total (`/health` and `/api/v1/system/info`, 20 each)
- HTTP errors: 0; error rate: 0.0000
- Overall p50/p95/p99: 0.002930 / 0.004331 / 0.005436 seconds
- Endpoint p95: `/health` 0.004331 seconds; `/api/v1/system/info`
  0.003707 seconds
- Docker snapshot memory: app-db 40.76 MiB during the sample; backend 108.9
  MiB; frontend 153.6 MiB; keycloak 977.2 MiB; keycloak-db 44.34 MiB;
  mailpit 20.73 MiB
- Raw report: `.agent/runs/20261006-m00-resource-baseline-rerun/performance/`

This is bootstrap resource evidence for NFR-011, not a pass for NFR-010. The
final target scenario still requires authenticated candidate/employer reads and
writes, matching/search, invitation transitions, chat history/messages, and
the 50-user workload described in `PERFORMANCE_TESTING.md`.
