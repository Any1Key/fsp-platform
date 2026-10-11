# M15 Telegram no-PII reporting boundary

## Purpose / user value

Keep optional Telegram telemetry useful for supervisor lifecycle events while
making it impossible for the reporting wrapper to forward arbitrary candidate
data, chat text, secrets, or private documents.

## Requirement IDs

- `LEGAL-003` — Telegram agent reporting never sends real PII, chat, or minor
  documents.
- Supporting `LEGAL-001` — data minimization and audit boundary for the
  external reporting adapter.

## Current behavior

`agent/telegram.sh` forwards arbitrary message text, image captions, and any
local document path to Telegram. The documentation says those values must be
safe, but the wrapper did not enforce that rule.

## Design

- Map the known supervisor event templates to fixed, non-identifying status
  messages. Reject unknown message text before invoking `curl`.
- Accept photos only when they resolve to a regular PNG below
  `.agent/screenshots/latest`; ignore caller captions and send a fixed caption.
  This directory is populated by the synthetic QA screenshot workflow.
- Reject the `document` operation unconditionally. Resume, chat, consent and
  other documents remain in local evidence storage and are never a Telegram
  transport input.
- When Telegram is disabled, print only the fixed safe event summary rather
  than the caller's original message.
- Add a shell contract test using a temporary fixture and fake `curl`; prove
  sensitive/unknown messages and documents do not reach transport, while
  approved synthetic status/photo events do.

## Files/modules

- `agent/telegram.sh` — enforced transport boundary.
- `agent/test-telegram-contract.sh` — no-PII transport contract.
- `agent/test-ci-contract.sh` — include the contract in the locked checks.
- `docs/TELEGRAM_REPORTING.md`, `docs/SECURITY.md`, `docs/LEGAL_152FZ.md` —
  operational privacy contract.
- `.agent/BACKLOG.md`, `docs/REQUIREMENTS_MATRIX.md` — mark this slice
  `IMPLEMENTED` only.

## Test plan

- Run `bash agent/test-telegram-contract.sh`.
- Run `bash agent/test-ci-contract.sh` to ensure the contract is wired into
  the repository checks.
- Run `bash -n` on the changed shell scripts.

## Progress / decisions

- 2026-10-11: selected as one coherent M15 P0 work unit for the unfinished
  `LEGAL-003` requirement. External supervisor verification remains separate.
- 2026-10-11: implemented the safe event classifier, screenshot path/signature
  boundary, document rejection, and isolated fake-transport contract test.
- 2026-10-11: `bash -n` and `bash agent/test-telegram-contract.sh` passed;
  `bash agent/test-ci-contract.sh` also passed. No Telegram network call was
  made during testing.
