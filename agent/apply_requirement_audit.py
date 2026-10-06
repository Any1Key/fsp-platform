from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_requirement_audit.py audit.json")

audit_path = Path(sys.argv[1])
matrix_path = Path("docs/REQUIREMENTS_MATRIX.md")
data = json.loads(audit_path.read_text(encoding="utf-8"))
verdicts = {x["id"]: x for x in data.get("requirements", []) if x.get("verified")}

lines = matrix_path.read_text(encoding="utf-8").splitlines()
out: list[str] = []

for line in lines:
    if not line.startswith("| "):
        out.append(line)
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != 6:
        out.append(line)
        continue
    rid = cells[0]
    verdict = verdicts.get(rid)
    if verdict:
        cells[4] = "VERIFIED"
        evidence = verdict.get("evidence", "").replace("|", "/").strip()
        if evidence:
            cells[5] = evidence
        line = "| " + " | ".join(cells) + " |"
    out.append(line)

matrix_path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"promoted {len(verdicts)} requirement verdicts where IDs exist")
