#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/resource-baseline.sh"
COMPOSE="$ROOT/docker-compose.yml"

test -x "$SCRIPT"
grep -Fq 'docker compose config --format json' "$SCRIPT"
grep -Fq 'docker stats --no-stream' "$SCRIPT"
grep -Fq 'docker info --format' "$SCRIPT"
grep -Fq '/api/v1/system/info' "$SCRIPT"
grep -Fq 'request-times.tsv' "$SCRIPT"
grep -Fq 'NFR-011' "$ROOT/docs/PERFORMANCE_TESTING.md"

if rg -n '^[[:space:]]*(gpus|device_requests):|^[[:space:]]*runtime:[[:space:]]*(nvidia|cuda)[[:space:]]*$|nvidia.com/gpu' "$COMPOSE"; then
  echo 'Compose must remain CPU-only: GPU runtime/device configuration found.' >&2
  exit 1
fi

echo 'Resource baseline contract OK (CPU-only Compose, real API probe, resource artifacts)'
