#!/usr/bin/env bash
set -Eeuo pipefail
url="${1:?url}"
timeout="${2:-180}"
start="$(date +%s)"
until curl -fsS --max-time 5 "$url" >/dev/null 2>&1; do
  now="$(date +%s)"
  if (( now - start >= timeout )); then
    echo "timeout waiting for $url" >&2
    exit 1
  fi
  sleep 3
done
echo "ready: $url"
