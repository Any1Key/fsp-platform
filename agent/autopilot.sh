#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env
ensure_dirs

LOCK="$ROOT/.agent/autopilot.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "autopilot already running or stale lock exists: $LOCK" >&2
  exit 2
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM

"$ROOT/agent/doctor.sh"

branch="$(git branch --show-current 2>/dev/null || true)"
if [[ "$branch" != "$AGENT_BRANCH" ]]; then
  git checkout -B "$AGENT_BRANCH"
fi

"$ROOT/agent/telegram.sh" message "🤖 FSP Codex supervisor started
Branch: $AGENT_BRANCH
Max cycles: $MAX_AGENT_CYCLES
Repair limit: $MAX_REPAIR_ATTEMPTS" || true

codex_args=(codex --ask-for-approval never exec --sandbox danger-full-access)
if [[ -n "${CODEX_MODEL:-}" ]]; then
  codex_args+=(--model "$CODEX_MODEL")
fi
if [[ -n "${CODEX_REASONING_EFFORT:-}" ]]; then
  codex_args+=(--config "model_reasoning_effort=${CODEX_REASONING_EFFORT}")
fi

for cycle in $(seq 1 "$MAX_AGENT_CYCLES"); do
  if python3 - <<'PY'
import json
from pathlib import Path
try:
    d=json.loads(Path(".agent/STATE.json").read_text())
    raise SystemExit(0 if d.get("ready") else 1)
except Exception:
    raise SystemExit(1)
PY
  then
    "$ROOT/agent/telegram.sh" message "🏁 FSP Platform state is READY. Supervisor stopping." || true
    exit 0
  fi

  rid="$(run_id)-c$(printf '%03d' "$cycle")"
  rdir="$ROOT/.agent/runs/$rid"
  mkdir -p "$rdir"
  export RUN_ID="$rid"

  "$ROOT/agent/telegram.sh" message "▶️ FSP agent cycle $cycle/$MAX_AGENT_CYCLES
Run: $rid
Implementing the highest-priority coherent work unit." || true

  cat > "$rdir/implement.prompt" <<'PROMPT'
Follow AGENTS.md.

Act as the implementation agent for exactly one coherent work unit from the highest-priority unfinished
milestone in .agent/BACKLOG.md.

Before editing:
- identify requirement IDs;
- inspect relevant docs/code;
- create/update an ExecPlan if substantial.

Implement end-to-end, including tests and documentation.
Update BACKLOG and REQUIREMENTS_MATRIX only to IMPLEMENTED semantics.
Never mark VERIFIED and never set STATE ready=true; external supervisor owns those.
Do not merely explain. Make repository changes.
Do not run destructive host-level commands.
PROMPT

  set +e
  "${codex_args[@]}" \
    --output-last-message "$rdir/codex-last.txt" \
    - < "$rdir/implement.prompt" \
    > "$rdir/codex.stdout" 2> "$rdir/codex.stderr"
  codex_rc=$?
  set -e

  if (( codex_rc != 0 )); then
    tailmsg="$(safe_tail "$rdir/codex.stderr" 50)"
    "$ROOT/agent/telegram.sh" message "🔴 Codex execution failed
Run: $rid
Exit: $codex_rc

${tailmsg:0:3000}" || true

    {
      echo
      echo "## $(timestamp) — Codex execution failed $rid"
      echo "Exit code: $codex_rc"
      echo "See: .agent/runs/$rid/codex.stderr"
    } >> "$ROOT/.agent/PROBLEMS.md"

    exit "$codex_rc"
  fi

  verified=false
  attempt=0
  while (( attempt <= MAX_REPAIR_ATTEMPTS )); do
    set +e
    "$ROOT/agent/verify.sh"
    verify_rc=$?
    set -e

    if (( verify_rc == 0 )); then
      verified=true
      break
    fi

    if (( attempt == MAX_REPAIR_ATTEMPTS )); then
      break
    fi

    attempt=$((attempt+1))
    "$ROOT/agent/telegram.sh" message "🛠 FSP recovery
Run: $rid
Repair attempt: $attempt/$MAX_REPAIR_ATTEMPTS
Verification failed; Codex is applying a focused fix." || true

    docker compose logs --no-color --tail=300 > "$rdir/compose.log" 2>&1 || true

    cat > "$rdir/repair-$attempt.prompt" <<PROMPT
Follow AGENTS.md. This is repair attempt $attempt for run $rid.

External verification failed.
Read:
- $rdir/verification.log
- $rdir/compose.log
- $rdir/codex-last.txt if present

Find root cause, implement the smallest correct fix, and add/improve a regression test where appropriate.
Do not weaken requirements or delete valid tests.
Do not mark VERIFIED.
Do not only explain: modify the repository.
PROMPT

    set +e
    "${codex_args[@]}" \
      --output-last-message "$rdir/repair-$attempt-last.txt" \
      - < "$rdir/repair-$attempt.prompt" \
      > "$rdir/repair-$attempt.stdout" 2> "$rdir/repair-$attempt.stderr"
    set -e
  done

  if [[ "$verified" != "true" ]]; then
    {
      echo
      echo "## $(timestamp) — supervisor blocker $rid"
      echo "Verification failed after $MAX_REPAIR_ATTEMPTS repair attempts."
      echo "See: .agent/runs/$rid/"
    } >> "$ROOT/.agent/PROBLEMS.md"

    excerpt="$(safe_tail "$rdir/verification.log" 60)"
    "$ROOT/agent/telegram.sh" message "⛔ FSP agent BLOCKED
Run: $rid
Verification still failing after $MAX_REPAIR_ATTEMPTS repair attempts.
Logs: .agent/runs/$rid/

${excerpt:0:3000}" || true
    exit 1
  fi

  "$ROOT/agent/audit-requirements.sh" > "$rdir/requirements-audit-run.log" 2>&1 || true
  "$ROOT/agent/maybe-ready.sh" > "$rdir/readiness.log" 2>&1 || true
  "$ROOT/agent/capture-screenshots.sh" > "$rdir/screenshots.log" 2>&1 || true
  "$ROOT/agent/git-checkpoint.sh" "verified cycle $cycle ($rid)" > "$rdir/git.log" 2>&1 || true
  commit="$(git rev-parse --short HEAD 2>/dev/null || echo n/a)"

  "$ROOT/agent/telegram.sh" message "✅ FSP cycle verified
Run: $rid
Cycle: $cycle/$MAX_AGENT_CYCLES
Build/services/tests/E2E: PASS
Commit: $commit
Next: continue highest-priority unfinished work." || true
done

"$ROOT/agent/telegram.sh" message "⚠️ Supervisor reached MAX_AGENT_CYCLES=$MAX_AGENT_CYCLES without READY." || true
exit 2
