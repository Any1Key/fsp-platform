# Documentation audit

Audit date: 2026-10-11

The audit compares `docs/source/TZ_EXTRACTED.txt`, the requirements matrix,
the implementation on `agent/autonomous`, the production Compose override and
the deployment configuration.

## Configuration contract

The repository is domain-neutral. Public values are supplied by `.env` and
are consumed by `compose.prod.yml`:

- `APP_BASE_URL` — browser application URL;
- `NEXT_PUBLIC_API_URL` — browser API URL;
- `NEXT_PUBLIC_KEYCLOAK_URL` — browser Keycloak base URL;
- `KEYCLOAK_PUBLIC_URL` — public Keycloak URL used by the server and proxy;
- `KEYCLOAK_ISSUER` — exact JWT issuer;
- `CORS_ALLOWED_ORIGINS` — allowed browser origins;
- `PROXY_NETWORK` — external Docker network shared with the TLS proxy.

The current VPS values are deployment data and do not belong in repository
Compose files or source code.

## Requirement coverage

The matrix contains 96 `VERIFIED` rows, 15 `IMPLEMENTED` rows and one `TODO`
row. The implemented product areas cover the mandatory candidate and employer
cabinet paths, category-first matching, salary-bearing invitations, privacy
boundaries, FSP synthetic integration, internal chat, employer stages/tasks,
OpenAPI, Docker and responsive UI.

## Remaining work before a strict final READY claim

1. Complete one authenticated Playwright scenario for `DEMO-001`: registration,
   verification, candidate onboarding and assessment, employer need and Talent
   Radar, invitation, acceptance, chat, employer task, submission and
   evaluation.
2. Run the authenticated target load profile on the deployment host and save
   the actual report. The runner and report format already exist.
3. Export the final presentation as PDF or PPTX and provide its submission
   link. `docs/PRESENTATION_OUTLINE.md` is only the source outline.

## Deliberate scope boundaries

- The FSP provider is synthetic and replaceable because the real FSP API and
  schema were not provided by the task.
- Validation metrics are deterministic synthetic evidence, not a claim about
  production hiring quality.
- Local AI is optional and disabled in the default deployment; manual task
  authoring remains the deterministic fallback.
- The 152-FZ material is an engineering control set and requires legal and
  operational review before treating it as legal certification.
- Mailpit is a demo SMTP sink; production email delivery requires real SMTP.

## Evidence locations

- Requirements: `docs/REQUIREMENTS_MATRIX.md`.
- Original task: `docs/source/TZ_EXTRACTED.txt` and `docs/source/TZ_2026.pdf`.
- Demo: `docs/DEMO_SCENARIO.md`.
- Deployment/OIDC: `docs/DEPLOYMENT.md`, `compose.prod.yml`.
- Validation: `docs/VALIDATION_RESULTS.md` and `docs/VALIDATION_RESULTS.json`.
- Load testing: `docs/PERFORMANCE_TESTING.md` and
  `docs/PERFORMANCE_RESULTS.md`.
- Chat and match: `docs/CHAT_AND_MATCHING.md`.
