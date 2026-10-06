# ATS integration concept

## Goal

Let employers integrate internal ATS without coupling core domain to any vendor.

## Adapter/API boundary

Future outbound/inbound events:
- vacancy created/updated/closed;
- candidate invitation sent/viewed/accepted/declined;
- candidate application created/status changed;
- contact unlocked.

Use versioned webhooks and an ATS connector port.

## Security

- per-employer credentials;
- signed webhooks;
- replay protection;
- idempotency keys;
- retry with dead-letter visibility;
- no contact payload before unlock.

MVP may expose OpenAPI endpoints and document example webhook contracts without implementing vendor-specific connectors.
