#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/lib.sh"
load_env

branch="$(git branch --show-current)"
if [[ "$branch" != "$AGENT_BRANCH" ]]; then
  git checkout -B "$AGENT_BRANCH"
fi

git add -A
if git diff --cached --quiet; then
  echo "No changes to commit"
  exit 0
fi

summary="${1:-Verified autonomous checkpoint}"
git commit -m "agent: ${summary}"

if [[ "${AUTO_PUSH,,}" == "true" ]]; then
  git push -u "$GIT_REMOTE" "$AGENT_BRANCH"
else
  echo "AUTO_PUSH=false; commit kept local"
fi
