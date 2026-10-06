Perform an independent final audit.

First pass: do not edit code.
Compare against:
- `docs/REQUIREMENTS_MATRIX.md`
- `docs/ACCEPTANCE_CRITERIA.md`
- original `docs/source/TZ_2026.pdf`

Create `.agent/FINAL_AUDIT.md` with:
- P0 defects
- P1 defects
- P2 improvements
- requirements lacking evidence
- security/privacy issues
- demo blockers
- documentation gaps

Then fix all P0/P1, add regression tests, and update remediation status.
Do not fabricate validation results.
External supervisor still owns final verification/READY.

Also treat `docs/CONFERENCE_CLARIFICATIONS_2026-10-06.md` as a working clarification source and explicitly audit the new conference-derived requirements: unique assessments, anti-AI-by-design, employer task grading/pipeline, minor consent, `.ru` registration, Keycloak demo, FSP ranking evidence, unconfirmed-grade discoverability, post-match chat, CPU/no-GPU operation and load testing.
