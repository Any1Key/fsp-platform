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

The wrapper enforces a transport boundary:
- messages must match a known supervisor event and are converted to a fixed
  status summary; arbitrary text is rejected before `curl` runs;
- photos must be regular files with a PNG signature under
  `.agent/screenshots/latest` and use a fixed caption; that directory is
  populated by the synthetic QA screenshot workflow;
- document uploads are disabled, so resumes, chats, minor-consent documents
  and other private files remain in local evidence storage;
- disabled Telegram mode prints only the fixed safe summary, never the caller's
  original text.

Never send secrets or raw `.env`. Full evidence stays in `.agent/runs/` and is
not a Telegram transport input.

Privacy rule: never send real candidate PII, resume text, chat content or minor-consent documents. Screenshots must use deterministic synthetic/demo accounts or redaction.
