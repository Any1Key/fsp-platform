#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if [[ "${DEMO_RESET_CONFIRM:-}" != "YES" ]]; then
  read -r -p "This destroys FSP compose demo database volumes. Type RESET-FSP-DEMO: " ans
  [[ "$ans" == "RESET-FSP-DEMO" ]] || { echo "cancelled"; exit 1; }
fi

docker compose down -v
docker compose up -d --build

wait_http() {
  local url="$1" timeout_seconds="${2:-240}" start now
  start="$(date +%s)"
  while true; do
    if curl --fail --silent --show-error "$url" >/dev/null; then return 0; fi
    now="$(date +%s)"
    (( now - start >= timeout_seconds )) && { echo "Timed out waiting for $url" >&2; return 1; }
    sleep 2
  done
}

wait_http "${BACKEND_URL:-http://127.0.0.1:8000}/health" 240
wait_http "${FRONTEND_URL:-http://127.0.0.1:3000}/api/health" 240

docker compose exec -T backend python -m app.seed_demo
