#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

test -x "$ROOT/scripts/local-ai-profile.sh"
grep -Fq 'profiles: ["local-ai"]' "$ROOT/docker-compose.yml"
grep -Fq 'LOCAL_AI_ENABLED' "$ROOT/scripts/local-ai-profile.sh"
grep -Fq 'LOCAL_AI_MODEL' "$ROOT/scripts/local-ai-profile.sh"
grep -Fq 'ollama pull' "$ROOT/scripts/local-ai-profile.sh"

core_json="$(docker compose config --format json)"
profile_json="$(docker compose --profile local-ai config --format json)"
export CORE_JSON="$core_json"
export PROFILE_JSON="$profile_json"
python3 <<'PY'
import json
import os

core = json.loads(os.environ["CORE_JSON"])
profile = json.loads(os.environ["PROFILE_JSON"])
core_services = core["services"]
profile_services = profile["services"]

assert "local-ai" not in core_services, "local-AI must stay out of the core profile"
service = profile_services["local-ai"]
assert service["profiles"] == ["local-ai"]
assert service["image"].startswith("ollama/ollama:")
assert service["cpus"] == 4.0
assert service["mem_limit"] == str(8 * 1024**3)
assert service["environment"]["OLLAMA_NUM_PARALLEL"] == "1"
assert service["environment"]["OLLAMA_MAX_LOADED_MODELS"] == "1"
assert not service.get("gpus")
assert not service.get("device_requests")
assert service.get("runtime") not in {"nvidia", "cuda"}
devices = service.get("deploy", {}).get("resources", {}).get("reservations", {}).get("devices", [])
assert not devices
print("Local-AI Compose profile contract OK (optional, CPU-bounded, no GPU)")
PY
