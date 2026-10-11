#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

load_env() {
  if [[ -f "$ROOT/.env.agent" ]]; then
    set -a
    source "$ROOT/.env.agent"
    set +a
  fi
  if [[ -f "$ROOT/.env" ]]; then
    set -a
    source "$ROOT/.env"
    set +a
  fi
  : "${MAX_AGENT_CYCLES:=80}"
  : "${MAX_REPAIR_ATTEMPTS:=5}"
  : "${AGENT_BRANCH:=agent/autonomous}"
  : "${AUTO_PUSH:=false}"
  : "${GIT_REMOTE:=origin}"
  : "${TELEGRAM_ENABLED:=false}"
  : "${TELEGRAM_VERBOSITY:=normal}"
  : "${HEALTH_TIMEOUT_SECONDS:=180}"
}

timestamp() { date '+%Y-%m-%dT%H:%M:%S%z'; }
run_id() { date '+%Y%m%d-%H%M%S'; }

log() { printf '[%s] %s\n' "$(timestamp)" "$*"; }

ensure_dirs() {
  mkdir -p "$ROOT/.agent/runs" "$ROOT/.agent/screenshots/latest" "$ROOT/.agent/plans"
}

safe_tail() {
  local f="$1"; local n="${2:-80}"
  [[ -f "$f" ]] && tail -n "$n" "$f" | sed -E \
    -e 's/(TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|OPENAI_API_KEY|GITHUB_TOKEN|DATABASE_URL|KEYCLOAK_DB_PASSWORD|KEYCLOAK_ADMIN_PASSWORD|POSTGRES_PASSWORD)=([^[:space:]]+)/\1=[REDACTED]/g' \
    -e 's/(Bearer )[A-Za-z0-9._-]+/\1[REDACTED]/g'
}
