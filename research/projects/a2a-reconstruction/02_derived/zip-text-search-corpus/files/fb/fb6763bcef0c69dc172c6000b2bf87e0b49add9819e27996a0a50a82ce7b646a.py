#!/usr/bin/env python3
"""Independent mechanical checks over the Round 5 local evidence tree.

This intentionally does not import the experiment helper modules.
"""

from __future__ import annotations

import base64
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
RUN_SCHEMA = (
    REPO
    / "towow_a2a_round5_codex_local_research_packet_v1.1"
    / "schemas"
    / "experiment_record.schema.json"
)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def verify_signature(public_path: Path, value_path: Path, signature_path: Path) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(public_path.read_bytes())
        value = json.loads(value_path.read_text(encoding="utf-8"))
        signature = base64.b64decode(signature_path.read_text(encoding="ascii").strip())
        key.verify(signature, canonical(value))
        return True
    except Exception:
        return False


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    json_files = sorted(ROOT.rglob("*.json"))
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    checks["json_files_parsed"] = len(json_files)

    try:
        yaml.safe_load((ROOT / "state" / "RESEARCH_STATE.yaml").read_text())
        checks["research_state_yaml"] = "valid"
    except Exception as exc:
        errors.append(f"invalid RESEARCH_STATE.yaml: {exc}")

    schema = json.loads(RUN_SCHEMA.read_text(encoding="utf-8"))
    run_files = sorted((ROOT / "runs").glob("*/run.json"))
    for path in run_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validate(payload, schema)
            run_dir = path.parent
            for relative in payload.get("evidence_paths", []):
                if not (run_dir / relative).exists():
                    errors.append(
                        f"missing run evidence {path.parent.name}: {relative}"
                    )
        except Exception as exc:
            errors.append(f"run validation failed {path.relative_to(ROOT)}: {exc}")
    checks["run_json_schema_validated"] = len(run_files)

    claim_rows = list(
        csv.DictReader(
            (ROOT / "CLAIM_EVIDENCE_UPDATE.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )
    for row in claim_rows:
        evidence = [item.strip() for item in row["evidence_paths"].split(";") if item.strip()]
        if not evidence:
            errors.append(f"claim {row['claim_id']} has no evidence path")
        for relative in evidence:
            if not (ROOT / relative).exists():
                errors.append(f"claim {row['claim_id']} missing evidence: {relative}")
    checks["claim_rows_checked"] = len(claim_rows)

    private_key_files = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
        and (
            path.name.endswith(".private")
            or path.suffix in {".pem", ".key", ".p12", ".pfx"}
        )
    ]
    if private_key_files:
        errors.append(f"private key-like files persisted: {private_key_files}")
    checks["private_key_like_files"] = private_key_files

    secret_patterns = {
        "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
        "private_key_block": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    }
    text_suffixes = {
        ".json",
        ".jsonl",
        ".md",
        ".csv",
        ".yaml",
        ".yml",
        ".py",
        ".log",
        ".txt",
        ".sig",
    }
    secret_hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in secret_patterns.items():
            if pattern.search(text):
                secret_hits.append(f"{path.relative_to(ROOT)}:{name}")
    if secret_hits:
        errors.append(f"secret-like content found: {secret_hits}")
    checks["secret_pattern_hits"] = secret_hits

    effect_events = json.loads(
        (
            ROOT
            / "runs"
            / "r5-run-002-effect-granularity"
            / "outputs"
            / "events.json"
        ).read_text()
    )
    checks["effect_metrics_recomputed"] = {
        "n": len(effect_events),
        "stdout_correct": sum(
            row["stdout_language_acceptance"] == row["ground_truth_acceptance"]
            for row in effect_events
        ),
        "outer_exit_correct": sum(
            row["outer_exit_acceptance"] == row["ground_truth_acceptance"]
            for row in effect_events
        ),
        "minimal_contract_correct": sum(
            row["minimal_contract_acceptance"] == row["ground_truth_acceptance"]
            for row in effect_events
        ),
    }
    if checks["effect_metrics_recomputed"] != {
        "n": 9,
        "stdout_correct": 4,
        "outer_exit_correct": 4,
        "minimal_contract_correct": 9,
    }:
        errors.append(
            f"effect metrics mismatch: {checks['effect_metrics_recomputed']}"
        )

    action_cases = json.loads(
        (
            ROOT
            / "runs"
            / "r5-run-003-action-space-claims"
            / "outputs"
            / "cases.json"
        ).read_text()
    )
    holdouts = [case for case in action_cases if case["partition"] == "holdout"]
    checks["action_holdout_recomputed"] = {
        "n": len(holdouts),
        "static_correct": sum(
            case["static_profile_prediction"] == case["actual"] for case in holdouts
        ),
        "scoped_unknown": sum(
            case["scoped_claim_prediction"] == "unknown" for case in holdouts
        ),
    }
    if checks["action_holdout_recomputed"] != {
        "n": 3,
        "static_correct": 0,
        "scoped_unknown": 3,
    }:
        errors.append(
            f"action holdout mismatch: {checks['action_holdout_recomputed']}"
        )

    run4 = ROOT / "runs" / "r5-run-004-sovereign-workspace"
    summaries = {
        "attempt1": json.loads((run4 / "outputs" / "summary.json").read_text()),
        "attempt2": json.loads(
            (run4 / "attempt2-literal-deny" / "outputs" / "summary.json").read_text()
        ),
        "attempt3": json.loads(
            (run4 / "attempt3-canonical-path" / "outputs" / "summary.json").read_text()
        ),
    }
    checks["boundary_attempts_recomputed"] = {
        name: summary["sovereign_honest"][
            "coordinator_private_or_packet_read_allowed"
        ]
        for name, summary in summaries.items()
    }
    if checks["boundary_attempts_recomputed"] != {
        "attempt1": True,
        "attempt2": True,
        "attempt3": False,
    }:
        errors.append(
            f"boundary attempt mismatch: {checks['boundary_attempts_recomputed']}"
        )

    honest = run4 / "attempt3-canonical-path" / "outputs" / "honest_public"
    tampered = run4 / "attempt3-canonical-path" / "outputs" / "tampered_public"
    checks["signature_recheck"] = {
        "honest_report": verify_signature(
            honest / "producer.ed25519.public",
            honest / "report.json",
            honest / "report.sig",
        ),
        "honest_verdict": verify_signature(
            honest / "validator.ed25519.public",
            honest / "verdict.json",
            honest / "verdict.sig",
        ),
        "tampered_report": verify_signature(
            tampered / "producer.ed25519.public",
            tampered / "report.json",
            tampered / "report.sig",
        ),
        "tampered_verdict": verify_signature(
            tampered / "validator.ed25519.public",
            tampered / "verdict.json",
            tampered / "verdict.sig",
        ),
    }
    if checks["signature_recheck"] != {
        "honest_report": True,
        "honest_verdict": True,
        "tampered_report": False,
        "tampered_verdict": True,
    }:
        errors.append(f"signature mismatch: {checks['signature_recheck']}")

    if summaries["attempt3"]["classification"].startswith("sovereign_a2a"):
        correction = run4 / "outputs" / "observed_cost_and_classification_correction.json"
        if correction.is_file():
            warnings.append(
                "raw attempt3 summary overstates classification; correction and run.json downgrade it to partial_sovereign"
            )
        else:
            errors.append("raw attempt3 sovereignty overclaim has no correction")

    payload = {
        "status": "failed" if errors else "passed_with_warnings" if warnings else "passed",
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "independence": {
            "implementation_path": "standalone verifier; does not import experiment helpers",
            "model_or_reviewer_independence": False,
            "codexpro_open_scan_warnings": 0,
            "codexpro_open_scan_limits": "257 inventory files; 8 analyzed source files; no entrypoints or relationships",
        },
    }
    output = ROOT / "reviews" / "OPEN_REVIEW_RESULT.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
