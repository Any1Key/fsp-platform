#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW="$ROOT/.github/workflows/ci.yml"

require_workflow_text() {
  local expected="$1"
  if ! grep -Fq "$expected" "$WORKFLOW"; then
    printf 'CI workflow is missing required contract: %s\n' "$expected" >&2
    exit 1
  fi
}

require_workflow_text 'permissions:'
require_workflow_text 'contents: read'
require_workflow_text 'cancel-in-progress: true'
require_workflow_text 'python -m pip install --requirement requirements.lock'
require_workflow_text 'python -m pip install --no-deps --editable .'
require_workflow_text 'npm ci'
require_workflow_text 'docker compose --profile test config -q'

if grep -Fq 'pip install -e "[dev]"' "$WORKFLOW"; then
  echo 'CI must not resolve backend dependencies from pyproject extras' >&2
  exit 1
fi

if grep -Fq 'npm install' "$WORKFLOW"; then
  echo 'CI must use npm ci, not npm install' >&2
  exit 1
fi

bash "$ROOT/agent/test-qa-contract.sh"
bash "$ROOT/agent/test-resource-baseline-contract.sh"
bash "$ROOT/agent/test-local-ai-profile-contract.sh"
echo 'CI contract OK (locked Python/Node installs, QA contract, Compose config)'
