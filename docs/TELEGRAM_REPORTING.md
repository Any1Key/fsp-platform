# Telegram reporting protocol

Telegram is telemetry, not the source of truth. Full evidence stays in `.agent/runs/`.

Events:
- `run_start`
- `verification_failed`
- `recovery_attempt`
- `recovered`
- `verified`
- `screenshots`
- `blocked`

Normal verbosity sends start, failure/recovery, verified, screenshots and blocker.
Verbose additionally sends repair-stage updates.

Never send secrets or raw `.env`.

Privacy rule: never send real candidate PII, resume text, chat content or minor-consent documents. Screenshots must use deterministic synthetic/demo accounts or redaction.
