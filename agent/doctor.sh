#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env
ensure_dirs

fail=0
check() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf 'OK   %s\n' "$label"
  else
    printf 'FAIL %s\n' "$label"
    fail=1
  fi
}

check "git" git --version
check "docker" docker --version
check "docker compose" docker compose version
check "codex" codex --version
check "curl" curl --version
check "repo writable" test -w "$ROOT"
check ".env exists" test -f "$ROOT/.env"
check ".env.agent exists" test -f "$ROOT/.env.agent"
check "compose config" docker compose config -q

echo
echo "Codex auth status:"
codex login status || true

echo
if [[ "${TELEGRAM_ENABLED,,}" == "true" ]]; then
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    echo "OK   Telegram variables present"
  else
    echo "FAIL Telegram enabled but token/chat id missing"
    fail=1
  fi
else
  echo "INFO Telegram disabled"
fi

exit "$fail"
