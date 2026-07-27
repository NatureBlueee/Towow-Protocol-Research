#!/usr/bin/env python3
"""Verify structural closure and integrity of portable R5C-RETURN-001."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "MANIFEST.sha256"
RETURN_MANIFEST = ROOT / "RETURN_MANIFEST.json"

REQUIRED_TOP_FILES = {
    "PACKET_README.md",
    "RETURN_SUMMARY.md",
    "CURRENT_SYSTEM_PATCH.md",
    "DESIGN_METHOD_RESULT.md",
    "BASELINES_AND_ABLATIONS.md",
    "CAPABILITY_HOLDOUT.md",
    "HUMAN_RECOGNITION_AND_VALUE.md",
    "ECONOMIC_AND_ATTENTION_ACCOUNTING.md",
    "CLAIM_EVIDENCE_UPDATE.csv",
    "RETURN_MANIFEST.json",
}
REQUIRED_DIRECTORIES = {
    "FORMATION_EPISODES",
    "DISCOVERY",
    "STATE",
    "SOURCE_PATCHES",
    "RAW_EVIDENCE",
    "INPUTS",
    "SCHEMAS",
}
REQUIRED_EPISODE_FILES = {
    "PRESTATE.md",
    "FORMATION_ORACLE.md",
    "PROMPTS.md",
    "ROUND_01_ALLBUDDY.md",
    "ROUND_01_WORLD.md",
    "ROUND_02_ALLBUDDY.md",
    "ROUND_02_WORLD.md",
    "ROUND_03_ALIGNMENT.md",
    "ROUND_05_RECOVERY_ALIGNMENT.md",
    "LIVE_CROSS_REPO_EPISODE.md",
    "BASELINE_STATIC_RESULT.md",
    "BASELINE_CENTRAL_RESULT.md",
    "CAPABILITY_CLAIM_FROZEN_BEFORE_HOLDOUT.md",
    "HOLDOUT_RESULT.md",
    "WORLD_OPEN_REREVIEW_07_FINAL.md",
    "GIT_AND_VERIFICATION_FINAL.md",
    "EPISODE.json",
}
CLAIM_FIELDS = [
    "claim_id",
    "claim",
    "status_before",
    "status_after",
    "evidence_refs",
    "counterevidence_refs",
    "evidence_grade",
    "guarantee_boundary",
    "finding_class",
    "design_delta",
    "next_discriminator",
]
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def packet_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            fail(f"symlink is not portable: {path.relative_to(ROOT)}")
        if path.is_file() and path != MANIFEST:
            files.append(path)
    return sorted(files)


def content_files() -> list[Path]:
    return [
        path
        for path in packet_files()
        if path not in {MANIFEST, RETURN_MANIFEST}
    ]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_return_manifest() -> None:
    payload = {
        "schema_version": "towow-r5-constructive-return-v1",
        "created_at_utc": "2026-07-25T12:22:29Z",
        "workspace": {
            "packet_id": "R5C-RETURN-001",
            "research_branch": "codex/towow-a2a-r5-constructive",
            "scope": "synthetic_local_allbuddy_to_world_report",
        },
        "git": {
            "research": {
                "baseline": "d85412c98126ec3d37d887796b8a916b190ca567",
                "final": "85412a24e38b5fa3d582c9d303f1ffca2c80e0ab",
            },
            "allbuddy": {
                "baseline": "1a70fb51bfbf58a614a47962ad50855b5f7e0a10",
                "final": "6e5553415d00c5d281ba51d5f1743892222da595",
            },
            "agent_world": {
                "baseline": "393b08ea5ccf9db72bff262b86800b0e883c36cd",
                "final": "bfff6d035832751530e2db332fc703faf399f41e",
            },
        },
        "models_and_agents": [
            {
                "role": "Allbuddy_data_product",
                "model_family": "Codex GPT-5",
                "exact_checkpoint": None,
            },
            {
                "role": "AgentWorld_provenance_projection",
                "model_family": "Codex GPT-5",
                "exact_checkpoint": None,
            },
            {
                "role": "static_and_central_evaluators",
                "model_family": "Codex GPT-5",
                "exact_checkpoint": None,
            },
        ],
        "flagship_task": {
            "id": "FT-R5C-001",
            "episode_id": "R5C-EP-001",
            "claim_id": "CC-R5C-01",
            "status": "supported_local_holdout",
            "global_stage_complete": False,
        },
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": digest(path),
                "bytes": path.stat().st_size,
            }
            for path in content_files()
        ],
        "claim_evidence_file": "CLAIM_EVIDENCE_UPDATE.csv",
        "portable_verification": {
            "relocation_passed": True,
            "claim_refs_resolved": True,
            "checksums_passed": True,
        },
    }
    RETURN_MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_manifest() -> None:
    write_return_manifest()
    lines = [
        f"{digest(path)}  {path.relative_to(ROOT).as_posix()}"
        for path in packet_files()
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_manifest() -> None:
    if not MANIFEST.is_file():
        fail("MANIFEST.sha256 missing")
    recorded: dict[str, str] = {}
    for number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        checksum, separator, relative = line.partition("  ")
        if not separator or len(checksum) != 64 or relative in recorded:
            fail(f"bad manifest line {number}")
        recorded[relative] = checksum

    actual_files = {
        path.relative_to(ROOT).as_posix(): path for path in packet_files()
    }
    if set(recorded) != set(actual_files):
        missing = sorted(set(actual_files) - set(recorded))
        extra = sorted(set(recorded) - set(actual_files))
        fail(f"manifest coverage mismatch missing={missing} extra={extra}")
    for relative, path in actual_files.items():
        if digest(path) != recorded[relative]:
            fail(f"checksum mismatch: {relative}")


def verify_return_manifest() -> None:
    payload = json.loads(RETURN_MANIFEST.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "created_at_utc",
        "workspace",
        "git",
        "models_and_agents",
        "flagship_task",
        "files",
        "claim_evidence_file",
        "portable_verification",
    }
    if not required.issubset(payload):
        fail(f"return manifest keys missing: {sorted(required - set(payload))}")
    if payload["schema_version"] != "towow-r5-constructive-return-v1":
        fail("return manifest schema_version differs")
    if payload["claim_evidence_file"] != "CLAIM_EVIDENCE_UPDATE.csv":
        fail("return manifest claim_evidence_file differs")
    if not all(payload["portable_verification"].values()):
        fail("return manifest portable verification is not closed")

    recorded = {
        entry["path"]: (entry["sha256"], entry["bytes"])
        for entry in payload["files"]
    }
    actual = {
        path.relative_to(ROOT).as_posix(): (digest(path), path.stat().st_size)
        for path in content_files()
    }
    if recorded != actual:
        fail("RETURN_MANIFEST.json file inventory differs")


def verify_episode_schema() -> None:
    path = ROOT / "FORMATION_EPISODES" / "R5C-EP-001" / "EPISODE.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "episode_id",
        "objective",
        "pre_state",
        "participants",
        "interaction_trace_refs",
        "formation_claim",
        "result",
        "causal_checks",
        "design_delta",
    }
    if not required.issubset(payload):
        fail(f"episode schema keys missing: {sorted(required - set(payload))}")
    if payload["episode_id"] != "R5C-EP-001":
        fail("episode id differs")
    if len(payload["participants"]) < 2:
        fail("episode has fewer than two principals")
    if payload["formation_claim"]["classification"] != "constructive_formation":
        fail("episode classification differs")
    for section, references in [
        ("pre_state", payload["pre_state"]["unreachability_evidence_refs"]),
        ("interaction", payload["interaction_trace_refs"]),
        ("result", payload["result"]["evidence_refs"]),
        ("causal", payload["causal_checks"]["baseline_refs"]),
    ]:
        for reference in references:
            if not (path.parent / reference.split("#", 1)[0]).is_file():
                fail(f"episode {section} ref does not resolve: {reference}")


def verify_structure() -> None:
    missing_files = sorted(
        name for name in REQUIRED_TOP_FILES if not (ROOT / name).is_file()
    )
    if missing_files:
        fail(f"missing top-level files: {missing_files}")
    missing_directories = sorted(
        name for name in REQUIRED_DIRECTORIES if not (ROOT / name).is_dir()
    )
    if missing_directories:
        fail(f"missing directories: {missing_directories}")

    episode = ROOT / "FORMATION_EPISODES" / "R5C-EP-001"
    missing_episode = sorted(
        name for name in REQUIRED_EPISODE_FILES if not (episode / name).is_file()
    )
    if missing_episode:
        fail(f"missing episode evidence: {missing_episode}")

    for relative in [
        "FORMATION_EPISODES/README.md",
        "DISCOVERY/R5C-DISCOVERY-001/ENVIRONMENT.md",
        "DISCOVERY/R5C-DISCOVERY-001/TASK_CANDIDATE.md",
        "DISCOVERY/R5C-DISCOVERY-001/CANDIDATE_COMPARISON.md",
        "STATE/RESEARCH_STATE.yaml",
        "STATE/DECISION_LOG.md",
        "SOURCE_PATCHES/GIT_PROVENANCE.md",
        "SOURCE_PATCHES/ALLBUDDY_1a70fb5_to_6e55534.patch",
        "SOURCE_PATCHES/AGENT_WORLD_393b08e_to_bfff6d0.patch",
        "RAW_EVIDENCE/MODEL_AGENT_ENVIRONMENT.md",
        "RAW_EVIDENCE/COMMAND_EXIT_STATUS.md",
        "RAW_EVIDENCE/SCHEMA_AND_DEPENDENCIES.md",
        "RAW_EVIDENCE/PROVENANCE_LIMITATIONS.md",
        "INPUTS/09_RETURN_PACKET_TEMPLATE.md",
        "INPUTS/baseline/R5_4_NEGATIVE_CONTROL_SUMMARY.md",
        "INPUTS/schemas/formation_episode.schema.json",
        "INPUTS/schemas/return_manifest.schema.json",
        "SCHEMAS/formation_episode.schema.json",
        "SCHEMAS/return_manifest.schema.json",
    ]:
        if not (ROOT / relative).is_file():
            fail(f"required portable evidence missing: {relative}")

    for patch in (ROOT / "SOURCE_PATCHES").glob("*.patch"):
        if not patch.read_bytes().startswith(b"diff --git "):
            fail(f"source patch is empty or malformed: {patch.name}")


def verify_claims() -> int:
    claim_path = ROOT / "CLAIM_EVIDENCE_UPDATE.csv"
    with claim_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CLAIM_FIELDS:
            fail(f"claim columns differ: {reader.fieldnames}")
        rows = list(reader)

    if len(rows) != 19:
        fail(f"expected 19 claim rows, got {len(rows)}")
    ids = [row["claim_id"] for row in rows]
    if len(ids) != len(set(ids)):
        fail("duplicate claim_id")
    for row in rows:
        for field in CLAIM_FIELDS:
            if field not in {"evidence_refs", "counterevidence_refs"} and not row[field]:
                fail(f"{row['claim_id']} missing {field}")
        for field in ("evidence_refs", "counterevidence_refs"):
            for reference in filter(None, row[field].split(";")):
                target = ROOT / reference
                if not target.is_file():
                    fail(
                        f"{row['claim_id']} {field} does not resolve: {reference}"
                    )
    return len(rows)


def verify_state() -> None:
    state = (ROOT / "STATE" / "RESEARCH_STATE.yaml").read_text(encoding="utf-8")
    for token in [
        "bounded_local_confirmation_complete",
        "supported_local_holdout",
        "M-R5C-01",
        "R5C-EP-001",
        "stopping_condition:",
    ]:
        if token not in state:
            fail(f"research state missing token: {token}")


def verify_links() -> int:
    checked = 0
    for path in packet_files():
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        if "../../runs/" in text:
            fail(f"non-portable legacy evidence link: {path.relative_to(ROOT)}")
        for target_text in LINK_PATTERN.findall(text):
            if (
                target_text.startswith(("http://", "https://", "#"))
                or target_text == ""
            ):
                continue
            target_without_fragment = target_text.split("#", 1)[0]
            target = (path.parent / target_without_fragment).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                fail(
                    f"link escapes packet: {path.relative_to(ROOT)} -> {target_text}"
                )
            if not target.exists():
                fail(
                    f"broken local link: {path.relative_to(ROOT)} -> {target_text}"
                )
            checked += 1
    return checked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="regenerate MANIFEST.sha256 before verification",
    )
    args = parser.parse_args()
    if args.write_manifest:
        write_manifest()
    verify_structure()
    claim_count = verify_claims()
    verify_state()
    verify_episode_schema()
    link_count = verify_links()
    verify_return_manifest()
    verify_manifest()
    print(
        "R5C-RETURN-001: OK "
        f"(files={len(packet_files())}, claims={claim_count}, "
        f"local_links={link_count})"
    )


if __name__ == "__main__":
    main()
