#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

dockerfile_version="$(sed -n 's/^FROM mcr\.microsoft\.com\/playwright:v\([^ -]*\)-noble$/\1/p' "$ROOT/qa/Dockerfile")"
package_version="$(sed -n 's/.*"@playwright\/test": "\([^"]*\)".*/\1/p' "$ROOT/qa/package.json")"
lock_version="$(awk '
  /"node_modules\/@playwright\/test": \{/ { in_package = 1; next }
  in_package && /"version": / {
    gsub(/[",]/, "", $2)
    print $2
    exit
  }
' "$ROOT/qa/package-lock.json")"

if [[ -z "$dockerfile_version" || "$dockerfile_version" != "$package_version" || "$package_version" != "$lock_version" ]]; then
  printf 'QA Playwright versions must match: Dockerfile=%s package=%s lockfile=%s\n' \
    "${dockerfile_version:-missing}" "${package_version:-missing}" "${lock_version:-missing}" >&2
  exit 1
fi

if ! grep -Fqx 'docker compose --profile test build' <(sed -n '/^echo "=== build ==="$/,/^echo "=== up ==="$/p' "$ROOT/agent/verify.sh" | sed '/^echo/d' | sed '/^#/d' | sed '/^$/d'); then
  echo 'agent/verify.sh must build the test profile before running QA' >&2
  exit 1
fi

echo "QA contract OK (Playwright $package_version; test profile build enabled)"
