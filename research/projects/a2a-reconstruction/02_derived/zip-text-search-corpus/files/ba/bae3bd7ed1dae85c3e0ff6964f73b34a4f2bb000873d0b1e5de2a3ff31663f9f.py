#!/usr/bin/env python3
"""Audit whether baseline claim artifacts are reachable from the local packet.

This checks path reachability and hashes only. It does not judge whether a
reachable artifact actually proves its claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_candidate(root: Path, artifact: str) -> Path | None:
    candidate = (root / artifact).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packet = args.packet.resolve()
    repo = args.repo.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    baseline = packet / "baseline" / "CLAIM_EVIDENCE_BASELINE_R5.csv"
    manifest = packet / "07_MANIFEST.json"
    manifest_data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    manifest_paths = {
        item.get("path")
        for item in manifest_data.get("files", [])
        if isinstance(item, dict) and item.get("path")
    }

    results: list[dict[str, object]] = []
    with baseline.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            artifact = (row.get("artifact") or "").strip()
            candidates: list[Path] = []
            for root in (packet, repo):
                candidate = safe_candidate(root, artifact)
                if candidate is not None and candidate not in candidates:
                    candidates.append(candidate)
            existing = [path for path in candidates if path.is_file()]
            chosen = existing[0] if existing else None
            packet_relative = None
            if chosen is not None:
                try:
                    packet_relative = chosen.relative_to(packet).as_posix()
                except ValueError:
                    packet_relative = None
            results.append(
                {
                    "claim_id": row["claim_id"],
                    "claim": row["claim"],
                    "artifact": artifact,
                    "reachable": chosen is not None,
                    "resolved_path": str(chosen) if chosen else None,
                    "sha256": sha256(chosen) if chosen else None,
                    "listed_in_packet_manifest": (
                        packet_relative in manifest_paths if packet_relative else False
                    ),
                    "candidates_checked": [str(path) for path in candidates],
                    "evidence_strength_source_statement": row.get("strength"),
                    "source_limits": row.get("limits"),
                }
            )

    reachable = sum(bool(item["reachable"]) for item in results)
    missing = len(results) - reachable
    payload = {
        "schema_version": "towow-r5-evidence-reachability-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet": str(packet),
        "baseline": str(baseline),
        "manifest": str(manifest),
        "method": (
            "Resolve each baseline CSV artifact path under the packet root and "
            "repository root; require a regular file; hash reachable files."
        ),
        "scope_limit": (
            "Reachability does not validate semantic sufficiency, provenance, "
            "independence, or the reported experiment."
        ),
        "summary": {
            "claims": len(results),
            "artifact_paths_reachable": reachable,
            "artifact_paths_missing": missing,
            "reachability_rate": reachable / len(results) if results else 0.0,
            "manifest_file_count": len(manifest_paths),
        },
        "results": results,
    }
    (output / "reachability.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output / "reachability.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "claim_id",
                "artifact",
                "reachable",
                "resolved_path",
                "sha256",
                "listed_in_packet_manifest",
            ],
        )
        writer.writeheader()
        for item in results:
            writer.writerow({key: item[key] for key in writer.fieldnames})

    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
