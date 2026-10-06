#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env
ensure_dirs

rid="${RUN_ID:-$(run_id)}"
rdir="$ROOT/.agent/runs/$rid"
mkdir -p "$rdir"

exec > >(tee "$rdir/verification.log") 2>&1

echo "=== FSP verification $rid ==="
date
git status --short || true

echo "=== compose config ==="
docker compose config -q

echo "=== build ==="
docker compose build

echo "=== up ==="
docker compose up -d

echo "=== wait backend ==="
"$ROOT/agent/wait-http.sh" "${BACKEND_URL}/health" "$HEALTH_TIMEOUT_SECONDS"

echo "=== wait frontend ==="
"$ROOT/agent/wait-http.sh" "${FRONTEND_URL}/api/health" "$HEALTH_TIMEOUT_SECONDS"

echo "=== backend tests ==="
docker compose exec -T backend pytest -q

echo "=== frontend typecheck ==="
docker compose exec -T frontend npm run typecheck

echo "=== e2e ==="
docker compose --profile test run --rm qa npm test

echo "=== service state ==="
docker compose ps | tee "$rdir/compose-ps.txt"

echo "=== logs snapshot ==="
docker compose logs --no-color --tail=250 > "$rdir/compose.log" 2>&1 || true

echo "VERIFICATION_PASS"
