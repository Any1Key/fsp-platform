#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${BASELINE_URL:=http://127.0.0.1:8000}"
: "${BASELINE_ITERATIONS:=20}"
: "${BASELINE_PAUSE_SECONDS:=0.05}"
: "${RUN_ID:=$(date -u '+%Y%m%d-%H%M%S')}"
: "${RESOURCE_BASELINE_OUTPUT_DIR:=$ROOT/.agent/runs/$RUN_ID/performance}"

CORE_SERVICES=(app-db keycloak-db mailpit keycloak backend frontend)
mkdir -p "$RESOURCE_BASELINE_OUTPUT_DIR"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 2
  }
}

for command_name in docker curl python3; do
  require_command "$command_name"
done

echo "FSP CPU-only resource baseline: $RUN_ID"
echo "output: $RESOURCE_BASELINE_OUTPUT_DIR"

# Rendered Compose is the source used for the actual deployment. Reject GPU
# settings there, rather than relying only on a review of docker-compose.yml.
compose_json="$(docker compose config --format json)"
if ! printf '%s' "$compose_json" | python3 -c '
import json
import sys

document = json.load(sys.stdin)
violations = []
for service_name, service in document.get("services", {}).items():
    if service.get("gpus"):
        violations.append(f"{service_name}.gpus")
    if str(service.get("runtime", "")).lower() in {"nvidia", "cuda"}:
        violations.append(f"{service_name}.runtime")
    if service.get("device_requests"):
        violations.append(f"{service_name}.device_requests")
    devices = service.get("deploy", {}).get("resources", {}).get("reservations", {}).get("devices", [])
    for index, device in enumerate(devices):
        capabilities = {str(value).lower() for value in device.get("capabilities", [])}
        if str(device.get("driver", "")).lower() == "nvidia" or "gpu" in capabilities:
            violations.append(f"{service_name}.deploy.resources.reservations.devices[{index}]")

if violations:
    print("GPU configuration found: " + ", ".join(violations), file=sys.stderr)
    raise SystemExit(1)
'; then
  exit 1
fi
echo "compose_cpu_policy=pass" > "$RESOURCE_BASELINE_OUTPUT_DIR/policy.txt"

{
  echo "run_id=$RUN_ID"
  echo "baseline_url=$BASELINE_URL"
  echo "iterations=$BASELINE_ITERATIONS"
  echo "pause_seconds=$BASELINE_PAUSE_SECONDS"
  echo "docker_server_version=$(docker info --format '{{.ServerVersion}}')"
  echo "docker_cpus=$(docker info --format '{{.NCPU}}')"
  echo "docker_memory_bytes=$(docker info --format '{{.MemTotal}}')"
  echo "host=$(uname -srmo)"
  echo "core_services=${CORE_SERVICES[*]}"
} > "$RESOURCE_BASELINE_OUTPUT_DIR/host-specs.txt"

capture_stats() {
  local phase="$1"
  local ids
  ids="$(docker compose ps -q "${CORE_SERVICES[@]}")"
  {
    echo -e "container\tcpu_percent\tmemory_usage\tmemory_percent"
    if [[ -n "$ids" ]]; then
      # shellcheck disable=SC2086 # ids is a whitespace-separated list from Docker.
      docker stats --no-stream --no-trunc --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}' $ids
    fi
  } > "$RESOURCE_BASELINE_OUTPUT_DIR/${phase}-docker-stats.tsv"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local attempt
  for attempt in $(seq 1 60); do
    if curl --fail --silent --show-error --max-time 3 -o /dev/null "$url"; then
      echo "$name=ready"
      return 0
    fi
    sleep 2
  done
  echo "$name=timeout" >&2
  return 1
}

echo "starting core services"
docker compose up -d --build "${CORE_SERVICES[@]}"
wait_for_http backend "$BASELINE_URL/health"
wait_for_http frontend "${BASELINE_FRONTEND_URL:-http://127.0.0.1:3000}/api/health"
docker compose ps > "$RESOURCE_BASELINE_OUTPUT_DIR/compose-before.txt"
capture_stats before

request() {
  local path="$1"
  local result
  local status="000"
  local seconds="0"

  result="$(curl --silent --show-error --max-time 10 -o /dev/null \
    -w '%{http_code}\t%{time_total}' "$BASELINE_URL$path" || true)"
  if [[ "$result" == *$'\t'* ]]; then
    status="${result%%$'\t'*}"
    seconds="${result#*$'\t'}"
  fi
  printf '%s\t%s\t%s\n' "$path" "$status" "$seconds" >> "$RESOURCE_BASELINE_OUTPUT_DIR/request-times.tsv"
}

echo -e "endpoint\tstatus\tseconds" > "$RESOURCE_BASELINE_OUTPUT_DIR/request-times.tsv"
probe() {
  local index
  for index in $(seq 1 "$BASELINE_ITERATIONS"); do
    request /health
    request /api/v1/system/info
    sleep "$BASELINE_PAUSE_SECONDS"
  done
}

probe &
probe_pid=$!
sleep 1
capture_stats during
wait "$probe_pid"
capture_stats after
docker compose ps > "$RESOURCE_BASELINE_OUTPUT_DIR/compose-after.txt"

python3 - "$RESOURCE_BASELINE_OUTPUT_DIR/request-times.tsv" "$RESOURCE_BASELINE_OUTPUT_DIR/summary.txt" <<'PY'
from __future__ import annotations

import math
import sys
from pathlib import Path

request_file = Path(sys.argv[1])
summary_file = Path(sys.argv[2])
rows = []
for line in request_file.read_text(encoding="utf-8").splitlines()[1:]:
    endpoint, status, seconds = line.split("\t")
    rows.append((endpoint, int(status), float(seconds)))

durations = sorted(row[2] for row in rows)


def percentile(value: float) -> float:
    if not durations:
        return 0.0
    return durations[max(0, math.ceil(value * len(durations)) - 1)]


errors = sum(status < 200 or status >= 300 for _, status, _ in rows)
lines = [
    f"request_count={len(rows)}",
    f"error_count={errors}",
    f"error_rate={errors / len(rows) if rows else 1.0:.4f}",
    f"p50_seconds={percentile(0.50):.6f}",
    f"p95_seconds={percentile(0.95):.6f}",
    f"p99_seconds={percentile(0.99):.6f}",
]
for endpoint in sorted({row[0] for row in rows}):
    endpoint_durations = sorted(row[2] for row in rows if row[0] == endpoint)
    endpoint_errors = sum(status < 200 or status >= 300 for path, status, _ in rows if path == endpoint)
    lines.append(f"{endpoint}.request_count={len(endpoint_durations)}")
    lines.append(f"{endpoint}.error_count={endpoint_errors}")
    lines.append(
        f"{endpoint}.p95_seconds={endpoint_durations[max(0, math.ceil(0.95 * len(endpoint_durations)) - 1)]:.6f}"
    )
summary_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(summary_file.read_text(encoding="utf-8"), end="")
if errors:
    raise SystemExit(1)
PY

echo "baseline complete: $RESOURCE_BASELINE_OUTPUT_DIR"
