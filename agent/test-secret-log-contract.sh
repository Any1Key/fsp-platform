#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/agent/lib.sh"

fixture="$(mktemp)"
trap 'rm -f "$fixture"' EXIT
cat > "$fixture" <<'EOF'
DATABASE_URL=postgresql://fsp:synthetic-db-secret@app-db:5432/fsp
KEYCLOAK_ADMIN_PASSWORD=synthetic-keycloak-password
TELEGRAM_BOT_TOKEN=synthetic-telegram-token
Authorization: Bearer synthetic-access-token
EOF

redacted="$(safe_tail "$fixture")"
for value in synthetic-db-secret synthetic-keycloak-password synthetic-telegram-token synthetic-access-token; do
  if [[ "$redacted" == *"$value"* ]]; then
    printf 'secret/log contract leaked synthetic value: %s\n' "$value" >&2
    exit 1
  fi
done

grep -Fq 'DATABASE_URL=[REDACTED]' <<<"$redacted"
grep -Fq 'KEYCLOAK_ADMIN_PASSWORD=[REDACTED]' <<<"$redacted"
grep -Fq 'TELEGRAM_BOT_TOKEN=[REDACTED]' <<<"$redacted"
grep -Fq 'Bearer [REDACTED]' <<<"$redacted"
echo 'Secret/log contract OK (Python and supervisor boundaries use redaction tests)'
