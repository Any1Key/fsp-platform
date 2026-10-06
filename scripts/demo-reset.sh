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
"$root/agent/wait-http.sh" "${BACKEND_URL:-http://127.0.0.1:8000}/health" 240
"$root/agent/wait-http.sh" "${FRONTEND_URL:-http://127.0.0.1:3000}/api/health" 240

docker compose exec -T backend python -m app.seed_demo
