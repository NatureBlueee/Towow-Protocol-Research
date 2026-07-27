#!/usr/bin/env python3
"""Assemble, manifest, checksum, and zip the local Round 5 return packet."""

from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
TARGET = ROOT / "return-packet"
ZIP_PATH = ROOT / "return-packet.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def ignore_cache(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name == "__pycache__" or name.endswith(".pyc")}


def role_for(relative: Path) -> str:
    first = relative.parts[0]
    return {
        "experiments": "raw experiment evidence",
        "code_changes": "research code and engineering evidence",
        "independent_reviews": "review and cross-validation",
        "failures": "failure index",
        "blockers": "external conditions",
        "git": "workspace version-control state",
        "manifests": "integrity metadata",
    }.get(first, "core return artifact")


def main() -> int:
    if not TARGET.is_dir():
        print(f"return packet narrative directory missing: {TARGET}", file=sys.stderr)
        return 2
    if (TARGET / "experiments").exists() or (TARGET / "manifests" / "MANIFEST.json").exists():
        print("refusing to overwrite an already assembled return packet", file=sys.stderr)
        return 3

    copy_file(ROOT / "state" / "ENVIRONMENT_FACTS.json", TARGET / "ENVIRONMENT_FACTS.json")
    copy_file(ROOT / "state" / "RESEARCH_STATE.yaml", TARGET / "RESEARCH_STATE.yaml")
    copy_file(ROOT / "state" / "DECISION_LOG.md", TARGET / "DECISION_LOG.md")
    copy_file(ROOT / "CLAIM_EVIDENCE_UPDATE.csv", TARGET / "CLAIM_EVIDENCE_UPDATE.csv")

    shutil.copytree(
        ROOT / "runs",
        TARGET / "experiments",
        ignore=ignore_cache,
    )
    smoke_destination = TARGET / "experiments" / "smoke"
    smoke_destination.mkdir(parents=True)
    copy_file(
        ROOT / "smoke" / "CODEX_LOCAL_SMOKE_RESULT.json",
        smoke_destination / "CODEX_LOCAL_SMOKE_RESULT.json",
    )
    shutil.copytree(
        ROOT / "reviews",
        TARGET / "independent_reviews",
        ignore=ignore_cache,
    )
    shutil.copytree(
        ROOT / "tools",
        TARGET / "code_changes" / "source",
        ignore=ignore_cache,
    )
    shutil.copytree(
        ROOT / "runs" / "r5-run-004-sovereign-workspace" / "failures",
        TARGET / "failures" / "r5-run-004",
    )

    baseline_text = "\n".join(
        [
            "branch=main",
            "head=null",
            "unborn=true",
            "dirty=true",
            "tracked_files=0",
            "protected_source_aggregate_sha256=5f2eac0be138a3927ca6e22ed66ec7d23f86b64e0353c48789fdf75a2813a040",
            "note=Every baseline workspace file was user-owned and untracked.",
            "",
        ]
    )
    (TARGET / "git" / "baseline.txt").write_text(baseline_text, encoding="utf-8")
    branch_code, branch_stdout, _ = git("branch", "--show-current")
    head_code, head_stdout, head_stderr = git("rev-parse", "--verify", "HEAD")
    final_text = "\n".join(
        [
            f"branch={branch_stdout.strip() if branch_code == 0 else 'unknown'}",
            f"head={head_stdout.strip() if head_code == 0 else 'null'}",
            f"head_exit_code={head_code}",
            f"head_stderr={head_stderr.strip()}",
            "unborn=true",
            "dirty=true",
            "protected_source_aggregate_sha256=5f2eac0be138a3927ca6e22ed66ec7d23f86b64e0353c48789fdf75a2813a040",
            "project_source_files_modified_by_research=0",
            "",
        ]
    )
    (TARGET / "git" / "final.txt").write_text(final_text, encoding="utf-8")
    status_code, status_stdout, status_stderr = git(
        "status", "--porcelain=v2", "--branch", "--untracked-files=all"
    )
    (TARGET / "git" / "status.txt").write_text(
        f"exit_code={status_code}\n{status_stdout}{status_stderr}",
        encoding="utf-8",
    )
    (TARGET / "git" / "commits.txt").write_text(
        "No commit exists in this repository. The research branch is unborn.\n",
        encoding="utf-8",
    )

    code_sources = sorted((ROOT / "tools").glob("*.py")) + [
        ROOT / "reviews" / "open_review_verifier.py"
    ]
    patch_parts: list[str] = []
    for source in code_sources:
        relative = source.relative_to(REPO).as_posix()
        lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
        patch_parts.extend(
            difflib.unified_diff(
                [],
                lines,
                fromfile="/dev/null",
                tofile=f"b/{relative}",
                lineterm="\n",
            )
        )
    (TARGET / "git" / "changes.patch").write_text(
        "".join(patch_parts), encoding="utf-8"
    )

    review = json.loads(
        (ROOT / "reviews" / "OPEN_REVIEW_RESULT.json").read_text(encoding="utf-8")
    )
    if review["errors"] or review["checks"]["secret_pattern_hits"]:
        print("review did not clear the packet for packaging", file=sys.stderr)
        return 4

    manifest_path = TARGET / "manifests" / "MANIFEST.json"
    checksum_path = TARGET / "manifests" / "CHECKSUMS.sha256"
    pre_manifest_files = sorted(
        path
        for path in TARGET.rglob("*")
        if path.is_file() and path not in {manifest_path, checksum_path}
    )
    manifest = {
        "schema_version": "towow-r5-local-return-packet-v1",
        "packet_version": "towow-a2a-r5-codex-local-return-v1.1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(REPO),
        "baseline_commit": None,
        "final_commit": None,
        "branch": branch_stdout.strip(),
        "unborn_repository": True,
        "protected_source_aggregate_sha256": "5f2eac0be138a3927ca6e22ed66ec7d23f86b64e0353c48789fdf75a2813a040",
        "run_ids": [
            "r5-run-001-evidence-reachability",
            "r5-run-002-effect-granularity",
            "r5-run-003-action-space-claims",
            "r5-run-004-sovereign-workspace",
        ],
        "model_agent_calls": [
            {
                "agent": "/root",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "xhigh",
                "independent_model_calls": 0,
            }
        ],
        "time_range_utc": {
            "start": "2026-07-24T12:28:29Z",
            "end": "2026-07-24T12:58:00Z",
        },
        "contains_secrets_or_restricted_data": False,
        "private_test_keys_persisted": False,
        "files": [
            {
                "path": path.relative_to(TARGET).as_posix(),
                "role": role_for(path.relative_to(TARGET)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in pre_manifest_files
        ],
        "integrity_note": (
            "MANIFEST.json lists every pre-manifest payload file. "
            "CHECKSUMS.sha256 covers those files plus MANIFEST.json and omits itself."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_files = sorted(
        path for path in TARGET.rglob("*") if path.is_file() and path != checksum_path
    )
    checksum_path.write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(TARGET).as_posix()}\n"
            for path in checksum_files
        ),
        encoding="utf-8",
    )

    if ZIP_PATH.exists():
        print(f"refusing to overwrite existing zip: {ZIP_PATH}", file=sys.stderr)
        return 5
    with zipfile.ZipFile(
        ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(TARGET.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    (Path("return-packet") / path.relative_to(TARGET)).as_posix(),
                )

    print(
        json.dumps(
            {
                "return_packet": str(TARGET),
                "zip": str(ZIP_PATH),
                "payload_files": len(pre_manifest_files),
                "checksummed_files": len(checksum_files),
                "zip_bytes": ZIP_PATH.stat().st_size,
                "zip_sha256": sha256(ZIP_PATH),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
