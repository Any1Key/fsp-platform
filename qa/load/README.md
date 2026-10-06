# Load tests

Codex must implement a reproducible Locust or k6 suite here once real application endpoints exist.
Required target scenario is defined in `docs/PERFORMANCE_TESTING.md`.

Do not fake application load against `/health` only. The final suite must exercise representative authenticated candidate/employer reads/writes, matching/search, invitations and chat.
