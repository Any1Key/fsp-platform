#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

readarray -t runtime_settings < <(
  docker compose config --format json | python3 -c '
import json
import sys

environment = json.load(sys.stdin)["services"]["backend"]["environment"]
print(environment.get("LOCAL_AI_ENABLED", "false"))
print(environment.get("LOCAL_AI_MODEL", ""))
'
)
local_ai_enabled="${runtime_settings[0]:-false}"
local_ai_model="${runtime_settings[1]:-}"

if [[ "$local_ai_enabled" != "true" ]]; then
  echo "LOCAL_AI_ENABLED must be true for the optional local-AI profile" >&2
  exit 2
fi
if [[ -z "$local_ai_model" ]]; then
  echo "LOCAL_AI_MODEL must not be empty for the optional local-AI profile" >&2
  exit 2
fi

echo "Starting core services and the optional CPU-local AI service"
docker compose up -d app-db keycloak-db mailpit keycloak backend frontend
docker compose --profile local-ai up -d local-ai

echo "Pulling configured local model: $local_ai_model"
docker compose --profile local-ai exec -T local-ai ollama pull "$local_ai_model"

# The backend may have started before the model pull. Restart only the backend
# so its already-configured adapter can begin accepting queued draft jobs.
docker compose restart backend
docker compose --profile local-ai ps local-ai
