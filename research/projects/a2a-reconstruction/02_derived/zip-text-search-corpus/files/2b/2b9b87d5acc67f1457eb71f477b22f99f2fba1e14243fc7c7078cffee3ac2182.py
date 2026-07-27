#!/usr/bin/env python3
"""Run bounded local capability probes against preregistered predictions."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run(command: list[str], timeout: int = 10) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env={"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        }


def metrics(cases: list[dict[str, Any]], prediction_key: str) -> dict[str, Any]:
    asserted = [case for case in cases if case[prediction_key] != "unknown"]
    correct = sum(case[prediction_key] == case["actual"] for case in asserted)
    false_assertions = len(asserted) - correct
    return {
        "total_cases": len(cases),
        "asserted_cases": len(asserted),
        "coverage": len(asserted) / len(cases) if cases else 0.0,
        "asserted_accuracy": correct / len(asserted) if asserted else None,
        "false_assertions": false_assertions,
        "false_assertion_rate_all_cases": (
            false_assertions / len(cases) if cases else 0.0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registered = json.loads(args.predictions.read_text(encoding="utf-8"))
    output = args.output.resolve()
    logs = output / "logs"
    outputs = output / "outputs"
    logs.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)

    probes: dict[str, dict[str, Any]] = {}
    probes["docker_daemon_query"] = run(
        ["/usr/local/bin/docker", "info", "--format", "{{.ServerVersion}}"]
    )
    probes["docker_daemon_query"]["actual"] = (
        probes["docker_daemon_query"]["exit_code"] == 0
        and bool(probes["docker_daemon_query"]["stdout"].strip())
    )
    probes["docker_daemon_query"]["postcondition"] = (
        "exit 0 and a non-empty local daemon server version"
    )

    permissive_profile = "(version 1)\n(allow default)"
    probes["sandbox_exec_allow_true"] = run(
        ["/usr/bin/sandbox-exec", "-p", permissive_profile, "/usr/bin/true"]
    )
    probes["sandbox_exec_allow_true"]["actual"] = (
        probes["sandbox_exec_allow_true"]["exit_code"] == 0
    )
    probes["sandbox_exec_allow_true"]["postcondition"] = (
        "sandbox-exec applies the profile and the child exits 0"
    )

    with tempfile.TemporaryDirectory(prefix="towow-r5-canary-") as temp_root:
        canary = Path(temp_root) / "private_canary.txt"
        canary_value = "synthetic-canary-r5"
        canary.write_text(canary_value, encoding="utf-8")
        parent_read_ok = canary.read_text(encoding="utf-8") == canary_value
        deny_profile = (
            "(version 1)\n"
            "(allow default)\n"
            f'(deny file-read* (literal "{canary}"))'
        )
        denied = run(
            ["/usr/bin/sandbox-exec", "-p", deny_profile, "/bin/cat", str(canary)]
        )
        profile_apply_error = "sandbox_apply" in denied["stderr"].lower()
        denied["actual"] = (
            parent_read_ok
            and probes["sandbox_exec_allow_true"]["actual"]
            and denied["exit_code"] != 0
            and canary_value not in denied["stdout"]
            and not profile_apply_error
        )
        denied["postcondition"] = (
            "parent reads synthetic canary; sandboxed child is denied; profile "
            "application itself succeeds"
        )
        denied["parent_read_ok"] = parent_read_ok
        denied["profile_apply_error"] = profile_apply_error
        denied["canary_value_sha256"] = __import__("hashlib").sha256(
            canary_value.encode()
        ).hexdigest()
        probes["sandbox_exec_deny_canary"] = denied

    retrospective = {
        "git_branch_default_seatbelt": {
            "actual": False,
            "evidence": "Observed HEAD.lock failure and unchanged branch postcondition.",
        },
        "git_branch_approved_route": {
            "actual": True,
            "evidence": "Approved git checkout -b route followed by verified branch read-back.",
        },
        "codexpro_remote_agent_execution": {
            "actual": False,
            "evidence": "CodexPro self-test terms_boundary remote_agent_execution=false.",
        },
    }

    cases: list[dict[str, Any]] = []
    for registered_case in registered["cases"]:
        case = dict(registered_case)
        case_id = case["case_id"]
        actual_record = probes.get(case_id) or retrospective[case_id]
        case["actual"] = bool(actual_record["actual"])
        case["actual_evidence"] = actual_record
        cases.append(case)

    holdouts = [case for case in cases if case["partition"] == "holdout"]
    calibration = [
        case for case in cases if case["partition"] == "retrospective_calibration"
    ]
    summary = {
        "schema_version": "towow-r5-action-space-probe-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "registered_at_utc": registered["registered_at_utc"],
        "holdout": {
            "static_profile": metrics(holdouts, "static_profile_prediction"),
            "scoped_claim": metrics(holdouts, "scoped_claim_prediction"),
        },
        "all_cases_including_retrospective_calibration": {
            "static_profile": metrics(cases, "static_profile_prediction"),
            "scoped_claim": metrics(cases, "scoped_claim_prediction"),
        },
        "holdout_actuals": {
            case["case_id"]: case["actual"] for case in holdouts
        },
        "boundary_mechanism_available": next(
            case["actual"]
            for case in cases
            if case["case_id"] == "sandbox_exec_deny_canary"
        ),
        "docker_daemon_available": next(
            case["actual"]
            for case in cases
            if case["case_id"] == "docker_daemon_query"
        ),
        "scope_limit": (
            "Three functional holdouts and three retrospective calibration cases "
            "do not establish population-level predictive accuracy."
        ),
    }
    for case_id, result in probes.items():
        (logs / f"{case_id}.stdout.log").write_text(
            result["stdout"], encoding="utf-8"
        )
        (logs / f"{case_id}.stderr.log").write_text(
            result["stderr"], encoding="utf-8"
        )
    (outputs / "cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (outputs / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
