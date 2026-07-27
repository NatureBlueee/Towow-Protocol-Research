#!/usr/bin/env python3
"""Lightweight integrity checks for the research workspace.

This deliberately checks the environment, not the quality or shape of research.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
SEED_PACKET = ROOT / "towow_a2a_round5_codex_local_research_packet_v1.1"
CURRENT_ARCHIVE = ROOT / "Towow_Complete_Research_Archive_v1.2_2026-07-27"
IGNORED_DIRS = {
    ".git",
    ".ai-bridge",
    ".ai-research",
    "towow_a2a_round5_codexpro_local_research_packet_v1.0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def active_instruction_files() -> Iterable[Path]:
    names = {"AGENTS.md", "AGENT.md", "agent.md", "CLAUDE.md", "GEMINI.md"}
    for current, dirs, files in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in IGNORED_DIRS]
        base = Path(current)
        for name in files:
            path = base / name
            if name in names or path.relative_to(ROOT).as_posix() == ".github/copilot-instructions.md":
                yield path


def check_packet() -> Tuple[List[str], int, bool]:
    errors: List[str] = []
    checked = 0
    if not SEED_PACKET.exists():
        return errors, checked, False

    checksum_file = SEED_PACKET / "CHECKSUMS.sha256"
    if not checksum_file.is_file():
        return [f"seed packet is missing its checksum: {checksum_file.relative_to(ROOT)}"], checked, True

    for line_number, raw in enumerate(checksum_file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            errors.append(f"invalid checksum line {line_number}")
            continue
        expected, relative = parts
        relative = relative.lstrip("*")
        target = SEED_PACKET / relative
        if not target.is_file():
            errors.append(f"packet file missing: {relative}")
            continue
        actual = sha256(target)
        checked += 1
        if actual != expected:
            errors.append(f"packet checksum mismatch: {relative}")
    return errors, checked, True


def check_current_archive() -> Tuple[List[str], int]:
    errors: List[str] = []
    checked = 0
    manifest_path = CURRENT_ARCHIVE / "MANIFEST.json"
    if not CURRENT_ARCHIVE.is_dir():
        return [f"current archive missing: {CURRENT_ARCHIVE.relative_to(ROOT)}"], checked
    if not manifest_path.is_file():
        return [f"current archive manifest missing: {manifest_path.relative_to(ROOT)}"], checked
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"invalid current archive manifest: {exc}"], checked
    for item in manifest:
        archive_path = str(item.get("archive_path", ""))
        expected_size = int(item.get("size_bytes", -1))
        expected_sha = str(item.get("sha256", ""))
        target = ROOT / archive_path
        if not target.is_file():
            errors.append(f"current archive file missing: {archive_path}")
            continue
        if target.stat().st_size != expected_size:
            errors.append(f"current archive size mismatch: {archive_path}")
            continue
        if sha256(target) != expected_sha:
            errors.append(f"current archive checksum mismatch: {archive_path}")
            continue
        checked += 1
    return errors, checked


def check_json() -> List[str]:
    errors: List[str] = []
    roots = [SEED_PACKET, CURRENT_ARCHIVE, ROOT / "research"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*.json"):
            if "zip-text-search-corpus" in path.parts:
                # Byte-preserving search copies may include empty or intentionally
                # malformed JSON evidence. Validate them only in their source context.
                continue
            try:
                json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    return errors


def main() -> int:
    errors: List[str] = []
    required = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "docs/RESEARCH_PLAYBOOK.md",
        ROOT / "research/README.md",
        ROOT / "research/NOW.md",
        ROOT / "research/DECISIONS.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing workspace file: {path.relative_to(ROOT)}")

    instructions = sorted(path.relative_to(ROOT).as_posix() for path in active_instruction_files())
    if instructions != ["AGENTS.md"]:
        errors.append(
            "expected exactly one active Agent instruction (AGENTS.md), found: "
            + ", ".join(instructions)
        )

    packet_errors, packet_files, packet_present = check_packet()
    errors.extend(packet_errors)
    archive_errors, archive_files = check_current_archive()
    errors.extend(archive_errors)
    errors.extend(check_json())

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        print(f"\nWorkspace check failed with {len(errors)} error(s).")
        return 1

    print("[OK] one active Agent instruction: AGENTS.md")
    if packet_present:
        print(f"[OK] optional v1.1 seed packet: {packet_files} checksums verified")
    else:
        print("[OK] no optional seed packet present")
    print(f"[OK] current v1.2 archive: {archive_files} manifest entries verified")
    print("[OK] JSON artifacts parse")
    print("[OK] long-term research workspace is ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
