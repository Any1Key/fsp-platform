#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dst="$root/frontend/public/brand/official"
mkdir -p "$dst"

base="https://fsp-russia.ru/completed_pages/images"
curl -fL "$base/face1.png" -o "$dst/face1.png"
curl -fL "$base/map1.png" -o "$dst/map1.png"
curl -fL "$base/lineline1.png" -o "$dst/lineline1.png"

echo "Fetched official FSP graphic elements to $dst"
