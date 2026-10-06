#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env
ensure_dirs

rm -rf "$ROOT/.agent/screenshots/latest"
mkdir -p "$ROOT/.agent/screenshots/latest"

docker compose --profile test run --rm \
  -e SCREENSHOT_OUTPUT=/workspace/screenshots \
  qa npm run screenshots

count=0
while IFS= read -r -d '' f; do
  count=$((count+1))
  "$ROOT/agent/telegram.sh" photo "$f" "📸 FSP UI — $(basename "$f")" || true
done < <(find "$ROOT/.agent/screenshots/latest" -type f -name '*.png' -print0 | sort -z)

echo "screenshots: $count"
