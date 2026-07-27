#!/usr/bin/env python3
"""Check provenance and navigation integrity for the derived A2A research view."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "Towow_Complete_Research_Archive_v1.2_2026-07-27"
PROJECT_ROOT = ROOT / "research" / "projects" / "a2a-reconstruction"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    required = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "00_orientation" / "CURRENT_GLOBAL_VIEW.md",
        PROJECT_ROOT / "01_catalog" / "physical_files.csv",
        PROJECT_ROOT / "01_catalog" / "zip_members.csv",
        PROJECT_ROOT / "01_catalog" / "markdown_sections.csv",
        PROJECT_ROOT / "01_catalog" / "catalog_summary.json",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing: {path.relative_to(ROOT)}")

    physical_catalog = PROJECT_ROOT / "01_catalog" / "physical_files.csv"
    if physical_catalog.is_file():
        catalog_paths: set[str] = set()
        with physical_catalog.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                catalog_paths.add(row["relative_path"])
                target = SOURCE_ROOT / row["relative_path"]
                if not target.is_file():
                    errors.append(f"catalog target missing: {row['relative_path']}")
                    continue
                if target.stat().st_size != int(row["size_bytes"]):
                    errors.append(f"catalog size drift: {row['relative_path']}")
        actual_paths = {
            path.relative_to(SOURCE_ROOT).as_posix()
            for path in SOURCE_ROOT.rglob("*")
            if path.is_file()
        }
        missing_from_catalog = sorted(actual_paths - catalog_paths)
        stale_catalog_rows = sorted(catalog_paths - actual_paths)
        for relative in missing_from_catalog:
            errors.append(f"physical file missing from catalog: {relative}")
        for relative in stale_catalog_rows:
            errors.append(f"stale physical catalog row: {relative}")

    for path in (PROJECT_ROOT / "02_derived" / "large-docs").glob("*/*.md"):
        if path.name == "INDEX.md":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        match_path = re.search(r"^source_path:\s*(.+)$", text, re.MULTILINE)
        match_sha = re.search(r"^source_sha256:\s*([0-9a-f]{64})$", text, re.MULTILINE)
        if not match_path or not match_sha:
            errors.append(f"missing provenance header: {path.relative_to(ROOT)}")
            continue
        source = ROOT / match_path.group(1).strip()
        if not source.is_file():
            errors.append(f"derived source missing: {source}")
        elif sha256(source) != match_sha.group(1):
            errors.append(f"derived source hash drift: {path.relative_to(ROOT)}")

    for split_root in (PROJECT_ROOT / "02_derived" / "large-docs").glob("*"):
        if not split_root.is_dir():
            continue
        fragments = sorted(
            path for path in split_root.glob("*.md") if path.name != "INDEX.md"
        )
        if not fragments:
            continue
        reconstructed: list[str] = []
        expected_start = 1
        source_path: Path | None = None
        for fragment in fragments:
            text = fragment.read_text(encoding="utf-8", errors="replace")
            match_source = re.search(r"^source_path:\s*(.+)$", text, re.MULTILINE)
            match_start = re.search(r"^source_line_start:\s*(\d+)$", text, re.MULTILINE)
            match_end = re.search(r"^source_line_end:\s*(\d+)$", text, re.MULTILINE)
            marker = (
                "> 本文件是导航用派生视图。原始文本未改动；"
                "引用研究证据时应回到上列源文件与行号。\n\n"
            )
            if not match_source or not match_start or not match_end or marker not in text:
                errors.append(f"invalid split fragment: {fragment.relative_to(ROOT)}")
                continue
            start = int(match_start.group(1))
            end = int(match_end.group(1))
            if start != expected_start:
                errors.append(
                    f"split coverage gap/overlap in {split_root.relative_to(ROOT)}: "
                    f"expected {expected_start}, got {start}"
                )
            expected_start = end + 1
            current_source = ROOT / match_source.group(1).strip()
            if source_path is None:
                source_path = current_source
            elif source_path != current_source:
                errors.append(
                    f"multiple sources in split directory: {split_root.relative_to(ROOT)}"
                )
            reconstructed.append(text.split(marker, 1)[1])
        if source_path and source_path.is_file():
            original = source_path.read_text(encoding="utf-8-sig", errors="replace")
            if "".join(reconstructed) != original:
                errors.append(
                    f"split reconstruction mismatch: {split_root.relative_to(ROOT)}"
                )

    for path in PROJECT_ROOT.rglob("*.json"):
        if "zip-text-search-corpus" in path.parts:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")

    authored_markdown = [PROJECT_ROOT / "README.md"]
    authored_markdown.extend((PROJECT_ROOT / "00_orientation").glob("*.md"))
    authored_markdown.extend((PROJECT_ROOT / "01_catalog").glob("*.md"))
    authored_markdown.extend((PROJECT_ROOT / "03_views").glob("*.md"))
    authored_markdown.extend(
        (PROJECT_ROOT / "02_derived" / "large-docs").glob("*/INDEX.md")
    )
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in authored_markdown:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for raw_target in link_pattern.findall(text):
            target = raw_target.strip()
            if (
                not target
                or target.startswith(("http://", "https://", "#", "mailto:"))
            ):
                continue
            target = unquote(target.split("#", 1)[0])
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(
                    f"broken local link in {path.relative_to(ROOT)}: {raw_target}"
                )

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        print(f"\nA2A research view check failed: {len(errors)} error(s).")
        return 1
    print("[OK] latest v1.2 source package remains addressable")
    print("[OK] physical catalog is complete; targets exist and sizes match")
    print("[OK] derived document provenance hashes match source files")
    print("[OK] all split fragments reconstruct their source documents exactly")
    print("[OK] generated JSON parses")
    print("[OK] authored navigation links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
