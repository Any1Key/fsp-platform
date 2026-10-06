# Load tests

The current bootstrap CPU-only resource baseline is implemented by
`scripts/resource-baseline.sh`. It is intentionally small and uses the stable
API endpoints that exist today; its artifacts belong under
`.agent/runs/<run-id>/performance/`.

Codex must implement a reproducible Locust or k6 suite here once real application endpoints exist.
Required target scenario is defined in `docs/PERFORMANCE_TESTING.md`.

Do not fake application load against `/health` only. The final suite must exercise representative authenticated candidate/employer reads/writes, matching/search, invitations and chat.
