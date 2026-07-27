#!/usr/bin/env python3
"""Build a stable payload manifest; manifest test outputs are excluded."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_root", type=Path)
    args = parser.parse_args()
    root = args.packet_root.resolve()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "manifests" in path.relative_to(root).parts:
            continue
        data = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest = {
        "packet_id": "towow-a2a-r5-4-return-packet",
        "schema_version": "towow-r5-return-manifest-v1",
        "files": files,
    }
    manifest_dir = root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (manifest_dir / "CHECKSUMS.sha256").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in files),
        encoding="utf-8",
    )
    print(json.dumps({"files": len(files)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
