# Dependency policy

- Prefer maintained permissive open source.
- Pin container images to explicit versions.
- Lock app dependency versions once first stable build exists.
- Record final versions in `docs/COMPONENTS.md`.
- Run security/dependency checks where practical.
- Avoid heavy services when a library suffices.

## Submission audit — 2026-10-11

Backend dependencies are pinned in `backend/requirements.lock` and installed
with `pip --requirement`; frontend and QA use `npm ci` with committed lockfiles.
Compose images are versioned in `docker-compose.yml`. The recorded versions are
summarized in `docs/COMPONENTS.md`; no GPU dependency is present in the core
profile. Updating versions is intentionally deferred after the freeze unless a
security blocker is identified.
