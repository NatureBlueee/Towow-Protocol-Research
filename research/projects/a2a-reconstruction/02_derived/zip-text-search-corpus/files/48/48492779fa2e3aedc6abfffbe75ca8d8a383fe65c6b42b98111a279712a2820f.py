#!/usr/bin/env python3
"""Build the R5.2 return manifest and checksum file without self-hash cycles."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path


MANIFEST = Path("manifests/MANIFEST.json")
CHECKSUMS = Path("manifests/CHECKSUMS.sha256")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def role_for(path: str) -> str:
    prefix = path.split("/", 1)[0]
    return {
        "experiments": "experiment_evidence",
        "real_tasks": "real_task_evidence",
        "code_changes": "code_change",
        "independent_reviews": "independent_review",
        "failures": "failure_record",
        "blockers": "blocker_record",
        "git": "git_provenance",
        "schemas": "schema",
        "tools": "replay_tool",
        "future_replication": "future_replication_handoff",
        "manifests": "manifest_attestation",
    }.get(prefix, "research_summary")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.packet).resolve()
    manifests = root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)

    payload_paths: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"symlink not allowed in return packet: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.name == ".DS_Store":
            continue
        if relative in {MANIFEST, CHECKSUMS}:
            continue
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit(f"non-portable path: {relative}")
        payload_paths.append(relative)

    relocation_path = root / "manifests" / "RELOCATION_TEST.json"
    relocation = {"performed": False, "passed": False}
    if relocation_path.exists():
        stored = json.loads(relocation_path.read_text(encoding="utf-8"))
        relocation = {
            "performed": bool(stored.get("performed")),
            "passed": bool(stored.get("passed")),
            "result_path": "manifests/RELOCATION_TEST.json",
        }

    files = []
    seen_ids: set[str] = set()
    for relative in payload_paths:
        full = root / relative
        path_text = relative.as_posix()
        artifact_id = "artifact-" + hashlib.sha256(path_text.encode()).hexdigest()[:16]
        if artifact_id in seen_ids:
            raise SystemExit(f"duplicate artifact id: {artifact_id}")
        seen_ids.add(artifact_id)
        mime, _ = mimetypes.guess_type(path_text)
        files.append(
            {
                "artifact_id": artifact_id,
                "path": path_text,
                "sha256": sha256(full),
                "bytes": full.stat().st_size,
                "role": role_for(path_text),
                "mime": mime or "application/octet-stream",
            }
        )

    manifest = {
        "schema_version": "towow-r5-return-packet-manifest-v1.2",
        "packet_id": "towow-a2a-r5-2-harness-reality-transfer",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": "d85412c98126ec3d37d887796b8a916b190ca567",
        "final_commit": "7690db92aee263f1918a54c58be16b271175ab4c",
        "contains_secrets": False,
        "contains_private_data": False,
        "workspace_kind": "canonical Harness local code/history; production-current unverified",
        "run_ids": [
            "r5-2-run-001-effect-reality",
            "r5-2-run-002-capability-holdout",
        ],
        "excluded_unexecuted_runs": 1,
        "agent_calls": [
            "primary Codex research agent",
            "context-separated effect matrix review",
            "context-separated return contract review",
            "GLM 5.2 future replication handoff",
        ],
        "external_effects": [],
        "files": files,
        "replay_entrypoints": [
            {
                "name": "recompute core research metrics",
                "command": "python3 tools/recompute_research_metrics.py .",
                "scope": "portable CSV and experiment evidence",
            },
            {
                "name": "verify return packet",
                "command": "python3 tools/portable_return_verifier.py .",
                "scope": "schemas, hashes, paths, disclosure scan, relocation flags",
            },
        ],
        "relocation_test": relocation,
    }
    manifest_path = root / MANIFEST
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checksum_targets = [
        path.relative_to(root)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.name != ".DS_Store"
        and path.relative_to(root) != CHECKSUMS
    ]
    checksum_text = "".join(
        f"{sha256(root / relative)}  {relative.as_posix()}\n"
        for relative in checksum_targets
    )
    (root / CHECKSUMS).write_text(checksum_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "packet": str(root),
                "manifest_files": len(files),
                "checksum_files": len(checksum_targets),
                "relocation": relocation,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
