from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
errors=[]
for row in manifest["files"]:
    p=ROOT/row["path"]
    if not p.exists():
        errors.append(f"missing: {row['path']}")
        continue
    data=p.read_bytes()
    sha=hashlib.sha256(data).hexdigest()
    if sha != row["sha256"]:
        errors.append(f"sha mismatch: {row['path']}")
    if len(data) != row["bytes"]:
        errors.append(f"size mismatch: {row['path']}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"verified {len(manifest['files'])} files")
