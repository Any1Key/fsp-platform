#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/qa/load/run_load.py"

test -f "$RUNNER"
python3 -m py_compile "$RUNNER"
grep -Fq 'FSP_LOAD_CANDIDATE_TOKEN_FILE' "$RUNNER"
grep -Fq 'FSP_LOAD_EMPLOYER_TOKEN_FILE' "$RUNNER"
grep -Fq '/api/v1/employer/talent-radar' "$RUNNER"
grep -Fq '/api/v1/chat/conversations' "$RUNNER"
grep -Fq 'docker stats --no-stream' "$RUNNER"
grep -Fq 'request-times.tsv' "$RUNNER"
grep -Fq 'NFR-010' "$ROOT/docs/PERFORMANCE_TESTING.md"

python3 -m unittest discover -s "$ROOT/qa/load" -p 'test_*.py'
echo 'Authenticated load-test contract OK'
