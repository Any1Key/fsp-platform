#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env

pending="$(awk -F'|' '
  /^\| [A-Z0-9-]+ / {
    pri=$3; gsub(/^ +| +$/, "", pri);
    status=$6; gsub(/^ +| +$/, "", status);
    if ((pri=="P0" || pri=="P1") && status!="VERIFIED") print $2 ":" pri ":" status
  }' docs/REQUIREMENTS_MATRIX.md)"

if [[ -n "$pending" ]]; then
  echo "Not ready; pending P0/P1 requirements:"
  echo "$pending"
  exit 0
fi

if grep -q "NOT YET MEASURED" docs/VALIDATION_RESULTS.md; then
  echo "Not ready; validation results still placeholder"
  exit 0
fi

if grep -q "NOT YET MEASURED" docs/PERFORMANCE_RESULTS.md; then
  echo "Not ready; performance/load results still placeholder"
  exit 0
fi

rid="${RUN_ID:-$(run_id)}"
rdir="$ROOT/.agent/runs/$rid"
mkdir -p "$rdir"
out="$rdir/final-readiness.json"

args=(codex --ask-for-approval never exec --sandbox danger-full-access \
  --output-schema "$ROOT/agent/final-readiness.schema.json" \
  --output-last-message "$out")
if [[ -n "${CODEX_MODEL:-}" ]]; then args+=(--model "$CODEX_MODEL"); fi
if [[ -n "${CODEX_REASONING_EFFORT:-}" ]]; then
  args+=(--config "model_reasoning_effort=${CODEX_REASONING_EFFORT}")
fi

cat > "$rdir/final-readiness.prompt" <<PROMPT
Perform a final independent readiness review. Do not edit files.

All P0/P1 rows are currently VERIFIED by the requirement-audit mechanism and the current run passed the
external build/test/E2E supervisor.

Inspect:
- docs/ACCEPTANCE_CRITERIA.md
- docs/REQUIREMENTS_MATRIX.md
- docs/CONFERENCE_CLARIFICATIONS_2026-10-06.md
- docs/VALIDATION_RESULTS.md
- docs/PERFORMANCE_RESULTS.md
- docs/DEMO_SCENARIO.md
- current code/docs/tests
- .agent/runs/$rid/

Set ready=true only if there is no material P0/P1, security/privacy, deployment, validation or demo blocker.
Be conservative. Return explicit blockers otherwise.
PROMPT

"${args[@]}" - < "$rdir/final-readiness.prompt" > "$rdir/final-readiness.stdout" \
  2> "$rdir/final-readiness.stderr"

python3 - "$out" <<'PY'
import json, sys
from pathlib import Path
audit=json.loads(Path(sys.argv[1]).read_text())
state_path=Path(".agent/STATE.json")
state=json.loads(state_path.read_text())
if audit.get("ready"):
    state["phase"]="READY"
    state["ready"]=True
    state["last_verified_run"]=Path(sys.argv[1]).parent.name
    state["notes"]=audit.get("summary","Final independent review passed.")
else:
    state["phase"]="FINAL_AUDIT"
    state["ready"]=False
    state["notes"]="; ".join(audit.get("blockers", []))[:2000]
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2)+"\n")
print(json.dumps(audit, ensure_ascii=False, indent=2))
PY
