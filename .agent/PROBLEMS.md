# Problems / blockers

## 2026-10-07 — M05 branded FSP UI local validation

- The frontend production build completed successfully.
- Host-side backend test execution is unavailable because `pytest` is not installed in the
  workspace shell; the Docker/locked environment remains the execution path for backend tests.
- Host-side Playwright execution is unavailable because the Chromium binary is not installed,
  and the Compose service hostnames (`frontend`, `backend`) are not resolvable outside Compose.
- These are validation-environment limits, not implementation blockers; the external supervisor
  owns the Compose/E2E verification pass.
