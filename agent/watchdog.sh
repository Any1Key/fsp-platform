#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env
ensure_dirs

interval="${WATCHDOG_INTERVAL_SECONDS:-60}"
"$ROOT/agent/telegram.sh" message "👀 FSP runtime watchdog started; interval ${interval}s" || true

while true; do
  ok=true
  curl -fsS --max-time 5 "${BACKEND_URL}/health" >/dev/null 2>&1 || ok=false
  curl -fsS --max-time 5 "${FRONTEND_URL}/api/health" >/dev/null 2>&1 || ok=false

  if [[ "$ok" != "true" ]]; then
    rid="$(run_id)-watchdog"
    rdir="$ROOT/.agent/runs/$rid"
    mkdir -p "$rdir"
    export RUN_ID="$rid"
    docker compose ps > "$rdir/compose-ps.txt" 2>&1 || true
    docker compose logs --no-color --tail=400 > "$rdir/compose.log" 2>&1 || true

    "$ROOT/agent/telegram.sh" message "🚨 FSP runtime health failure
Run: $rid
Watchdog is attempting recovery." || true

    recovered=false
    for attempt in $(seq 1 "$MAX_REPAIR_ATTEMPTS"); do
      cat > "$rdir/watchdog-repair-$attempt.prompt" <<PROMPT
Follow AGENTS.md. Runtime watchdog detected unhealthy frontend/backend.

Read:
- $rdir/compose-ps.txt
- $rdir/compose.log

Diagnose the application/configuration root cause and implement the smallest safe repository fix.
Do not perform destructive host operations. Add a regression test when relevant.
PROMPT
      args=(exec --sandbox workspace-write --ask-for-approval never)
      [[ -n "${CODEX_MODEL:-}" ]] && args+=(--model "$CODEX_MODEL")
      [[ -n "${CODEX_REASONING_EFFORT:-}" ]] && args+=(--config "model_reasoning_effort=${CODEX_REASONING_EFFORT}")

      set +e
      "${args[@]}" --output-last-message "$rdir/watchdog-$attempt-last.txt" - \
        < "$rdir/watchdog-repair-$attempt.prompt" \
        > "$rdir/watchdog-$attempt.stdout" 2> "$rdir/watchdog-$attempt.stderr"
      "$ROOT/agent/verify.sh"
      rc=$?
      set -e
      if (( rc == 0 )); then
        recovered=true
        break
      fi
    done

    if [[ "$recovered" == "true" ]]; then
      "$ROOT/agent/telegram.sh" message "🟢 FSP runtime recovered
Run: $rid
Full verification PASS." || true
    else
      "$ROOT/agent/telegram.sh" message "⛔ FSP runtime watchdog BLOCKED
Run: $rid
Recovery limit exhausted." || true
      exit 1
    fi
  fi
  sleep "$interval"
done
