#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env

rid="${RUN_ID:-$(run_id)}"
rdir="$ROOT/.agent/runs/$rid"
mkdir -p "$rdir"
out="$rdir/requirements-audit.json"

args=(codex --ask-for-approval never exec --sandbox danger-full-access \
  --output-schema "$ROOT/agent/requirements-audit.schema.json" \
  --output-last-message "$out")
if [[ -n "${CODEX_MODEL:-}" ]]; then args+=(--model "$CODEX_MODEL"); fi
if [[ -n "${CODEX_REASONING_EFFORT:-}" ]]; then
  args+=(--config "model_reasoning_effort=${CODEX_REASONING_EFFORT}")
fi

cat > "$rdir/requirements-audit.prompt" <<PROMPT
Act as a conservative independent verifier. Do not edit files.

Inspect:
- docs/CONFERENCE_CLARIFICATIONS_2026-10-06.md
- docs/REQUIREMENTS_MATRIX.md
- relevant implementation/tests
- .agent/runs/$rid/verification.log
- .agent/runs/$rid/compose-ps.txt when present

For every requirement row that is already VERIFIED, or that is IMPLEMENTED and now has credible automated
or directly inspectable evidence, return a verdict.

Set verified=true only if the requirement is genuinely implemented end-to-end and evidence is specific.
A green global build alone is not enough. For privacy/security behavior require a targeted test.
For UI behavior require relevant E2E/component/screenshot evidence.
For documentation requirements inspect the actual docs.
For validation requirements require real measured results, not placeholders.

Use evidence paths such as backend/tests/..., qa/tests/..., docs/..., or .agent/runs/$rid/...
Be conservative.
PROMPT

"${args[@]}" - < "$rdir/requirements-audit.prompt" > "$rdir/requirements-audit.stdout" \
  2> "$rdir/requirements-audit.stderr"

python3 "$ROOT/agent/apply_requirement_audit.py" "$out"
