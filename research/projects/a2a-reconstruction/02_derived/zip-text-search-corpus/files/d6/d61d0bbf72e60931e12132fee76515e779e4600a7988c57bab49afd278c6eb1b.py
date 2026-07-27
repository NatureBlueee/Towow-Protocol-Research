#!/usr/bin/env python3
"""Verify integrity, reachability, parsing, schemas, and basic secret hygiene."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import jsonschema
import yaml


LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SECRET_PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "anthropic_key": re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}"),
    "github_token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refs(cell: str) -> list[str]:
    return [part.strip() for part in cell.split(";") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_root", type=Path)
    args = parser.parse_args()
    root = args.packet_root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest_path = root / "manifests/MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    jsonschema.validate(
        manifest,
        json.loads((root / "schemas/manifest.schema.json").read_text(encoding="utf-8")),
    )
    listed = {item["path"] for item in manifest["files"]}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "manifests" not in path.relative_to(root).parts
    }
    for missing in sorted(listed - actual):
        errors.append(f"manifest missing file: {missing}")
    for unlisted in sorted(actual - listed):
        errors.append(f"manifest unlisted file: {unlisted}")
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.is_file():
            continue
        if path.stat().st_size != item["size"]:
            errors.append(f"size mismatch: {item['path']}")
        if _hash(path) != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")

    checksum_lines = (root / "manifests/CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
    expected_lines = [f"{item['sha256']}  {item['path']}" for item in manifest["files"]]
    if checksum_lines != expected_lines:
        errors.append("CHECKSUMS.sha256 differs from MANIFEST.json")

    for path in sorted(root.rglob("*.json")):
        if "manifests" in path.relative_to(root).parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip() and path.name == "stdout.json":
                warnings.append(f"empty raw stdout: {path.relative_to(root)}")
                continue
            json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"JSON parse: {path.relative_to(root)}: {exc}")
    for path in sorted(root.rglob("*.yaml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"YAML parse: {path.relative_to(root)}: {exc}")
    for path in sorted(root.rglob("*.csv")):
        try:
            list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
        except Exception as exc:
            errors.append(f"CSV parse: {path.relative_to(root)}: {exc}")

    jsonschema.validate(
        json.loads((root / "experiments/r5-4-run-001-source-identity/experiment_record.json").read_text()),
        json.loads((root / "schemas/experiment_record.schema.json").read_text()),
    )
    jsonschema.validate(
        json.loads((root / "experiments/r5-4-run-001-source-identity/formation_episode.json").read_text()),
        json.loads((root / "schemas/formation_episode.schema.json").read_text()),
    )

    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in LINK.findall(text):
            clean = target.strip("<>")
            if clean.startswith(("http://", "https://", "#")):
                continue
            if clean.startswith("/"):
                errors.append(f"absolute markdown link: {path.relative_to(root)} -> {clean}")
                continue
            clean = clean.split("#", 1)[0]
            if clean and not (path.parent / clean).exists():
                errors.append(f"broken markdown link: {path.relative_to(root)} -> {clean}")

    for csv_name in ("CLAIM_EVIDENCE_UPDATE.csv", "RESULT_CLASSIFICATION.csv"):
        with (root / csv_name).open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                for field in ("evidence_paths", "counterevidence_paths", "supporting_paths"):
                    if field not in row:
                        continue
                    for ref in _refs(row[field] or ""):
                        if not (root / ref).exists():
                            errors.append(f"broken {csv_name} {field}: {ref}")

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix == ".enc":
            continue
        data = path.read_bytes()
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"secret pattern {name}: {path.relative_to(root)}")

    result = {
        "packet_root": str(root),
        "manifest_files": len(manifest["files"]),
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
