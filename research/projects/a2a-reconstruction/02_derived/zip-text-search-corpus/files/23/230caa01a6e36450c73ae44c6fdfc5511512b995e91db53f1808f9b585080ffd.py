#!/usr/bin/env python3
"""Extract exact and path-normalized candidate patches from frozen outputs."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "r5-4-run-001-source-identity"


def main() -> None:
    parsed = json.loads(
        (RUN / "traces/static/builder/parsed.json").read_text(encoding="utf-8")
    )
    patch = parsed["structured_output"]["unified_diff"]
    out = RUN / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "static-exact.patch").write_text(patch.rstrip() + "\n", encoding="utf-8")
    mapping = {
        "a/projection.py": "a/harness/src/towow/l0/projection/projection.py",
        "b/projection.py": "b/harness/src/towow/l0/projection/projection.py",
        "a/consensus_invalidation.py": "a/harness/src/towow/l1/consensus_invalidation.py",
        "b/consensus_invalidation.py": "b/harness/src/towow/l1/consensus_invalidation.py",
        "a/concept_retire_gate.py": "a/harness/src/towow/l0/commit_gate/concept_retire_gate.py",
        "b/concept_retire_gate.py": "b/harness/src/towow/l0/commit_gate/concept_retire_gate.py",
    }
    normalized = patch
    for source, target in mapping.items():
        normalized = normalized.replace(source, target)
    (out / "static-path-normalized.patch").write_text(
        normalized.rstrip() + "\n",
        encoding="utf-8",
    )
    metadata = {
        "source": "traces/static/builder/parsed.json#/structured_output/unified_diff",
        "exact_patch_preserved": True,
        "normalization": mapping,
        "semantic_changes": False,
        "classification": "mechanical target-path repair after exact-apply attempt",
    }
    (out / "static-patch-extraction.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
