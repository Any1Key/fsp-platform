# M00 — Reproducible CI baseline

## Purpose / user value

Make every change pass the same minimum backend, frontend, QA-contract and
Compose configuration checks with the repository's committed dependency
lockfiles. This gives later feature work a repeatable regression gate without
claiming that CI itself is production verification.

## Requirement IDs

- NFR-013 — automated CI validates the locked backend/frontend/QA toolchain and
  Compose configuration.
- NFR-004 — the CI Compose configuration check protects reproducible startup
  inputs; existing external verification remains authoritative for runtime
  startup.

## Current behavior

`.github/workflows/ci.yml` runs backend tests/lint, frontend typecheck/build and
`docker compose config`, but installs Python and Node dependencies through
unlocked project resolution (`pip install -e "[dev]"` and `npm install`). The
QA Playwright version contract is checked only by the local verification path.

## Proposed design

- Install backend dependencies from `backend/requirements.lock`, then install
  the local package without dependency resolution.
- Use `npm ci` for frontend and QA lockfiles.
- Run the QA image/version contract in CI and add a small repository-owned
  contract test that prevents accidental regression to unlocked installs.
- Add workflow concurrency, least-privilege permissions and job timeouts.
- Document the CI entry points and its boundary with external Compose/E2E
  verification.

## Files/modules

- `.github/workflows/ci.yml` — reproducible CI jobs.
- `agent/test-ci-contract.sh` — static contract assertions used by CI and
  local verification.
- `docs/DEPLOYMENT.md` — CI/local quality-gate documentation.
- `docs/REQUIREMENTS_MATRIX.md` — NFR-013 evidence and `IMPLEMENTED` status.
- `.agent/BACKLOG.md` — mark only M00 CI baseline implemented.

## Data/API changes

None.

## Security/privacy implications

CI uses no application credentials or real data. Workflow permissions are
read-only by default, and the Compose check substitutes CI-only placeholder
passwords in a temporary `.env` file.

## Test plan

- Run the CI contract script locally.
- Run backend tests and Ruff from the locked Python environment.
- Run frontend `npm ci`, typecheck and build.
- Run `docker compose config -q` with CI-safe placeholders.

## Demo/evidence

`.github/workflows/ci.yml` plus `agent/test-ci-contract.sh` are the repeatable
implementation evidence. External supervisor owns workflow execution and any
`VERIFIED` status.

## Progress / decisions / surprises

- 2026-10-06: selected as the highest-priority unfinished M00 unit. The
  separate CPU-only resource baseline remains TODO for a later unit.
- 2026-10-06: implemented locked Python/Node CI jobs, QA and Compose profile
  checks, least-privilege workflow settings, and the local CI contract.
- 2026-10-06: `bash agent/test-ci-contract.sh`, frontend typecheck and
  `docker compose --env-file .env.example --profile test config -q` passed.
  The host Python environment has no `pytest`/`ruff`; the backend checks remain
  defined in CI and the external containerized verification path.
