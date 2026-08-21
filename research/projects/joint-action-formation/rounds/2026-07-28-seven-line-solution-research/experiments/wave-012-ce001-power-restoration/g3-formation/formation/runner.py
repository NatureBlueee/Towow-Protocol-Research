from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .canonical import sha256
from .models import RunRecord
from .protocol import (
    raw_line_sha256,
    read_message,
    read_raw_message,
    write_message,
    write_raw_message,
)


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CASES = ROOT / "fixtures" / "public_cases.json"
PRIVATE_TRUTH = ROOT / "private" / "owner_truth.json"
OUTPUTS = ROOT / "outputs"

E2_INTERVENTIONS = [
    "REMOVE_FORMATION_OPERATOR",
    "REVERSE_OWNER_DECISION@read",
    "REVERSE_OWNER_DECISION@sign",
    "REVERSE_OWNER_DECISION@reserve",
    "REVERSE_OWNER_DECISION@execute",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def worker_command() -> list[str]:
    return [
        sys.executable,
        str(ROOT / "worker_capsule.py"),
    ]


def worker_environment() -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for key in ("LANG", "LC_ALL", "LC_CTYPE"):
        if os.environ.get(key):
            environment[key] = os.environ[key]
    return environment


def _popen(
    module: str, owner_private_path: Path | None = None
) -> subprocess.Popen[str]:
    command = [sys.executable, "-m", module]
    if module == "formation.owner_endpoint":
        command.extend(
            ["--private", str(owner_private_path or PRIVATE_TRUTH)]
        )
    elif module == "formation.worker_process":
        command = worker_command()
    environment = (
        worker_environment()
        if module == "formation.worker_process"
        else {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT),
            **{
                key: os.environ[key]
                for key in ("LANG", "LC_ALL", "LC_CTYPE")
                if os.environ.get(key)
            },
        }
    )
    return subprocess.Popen(
        command,
        cwd=Path("/private/tmp") if module == "formation.worker_process" else ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def _record(value: dict[str, Any]) -> RunRecord:
    return RunRecord(**value)


def execute_one(
    public_case: dict[str, Any],
    case_truth: dict[str, Any] | None = None,
    intervention: str = "NONE",
    *,
    response_fault: str | None = None,
) -> RunRecord:
    """Run a public worker and private owner endpoint behind a byte broker.

    ``case_truth`` remains as a compatibility argument for the original risk
    tests. It is intentionally ignored: the worker cannot receive caller-held
    private truth or use it as an answer path.
    """

    private_override: tempfile.NamedTemporaryFile[str] | None = None
    owner_private_path = PRIVATE_TRUTH
    if case_truth is not None:
        private_override = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="ce001-g3-owner-fixture-",
            encoding="utf-8",
        )
        json.dump(
            {
                "owner_endpoint_signing_seed": load_json(PRIVATE_TRUTH)[
                    "owner_endpoint_signing_seed"
                ],
                "manifest": {public_case["case_handle"]: "TEST_CASE"},
                "cases": {"TEST_CASE": case_truth},
            },
            private_override,
            ensure_ascii=False,
        )
        private_override.flush()
        owner_private_path = Path(private_override.name)
    owner = _popen("formation.owner_endpoint", owner_private_path)
    worker = _popen("formation.worker_process")
    assert owner.stdin and owner.stdout and owner.stderr
    assert worker.stdin and worker.stdout and worker.stderr
    write_message(
        owner.stdin,
        {
            "case_handle": public_case["case_handle"],
            "intervention": intervention,
            "response_fault": response_fault,
        },
    )
    ready = read_message(owner.stdout)
    if ready.get("type") != "OWNER_ENDPOINT_READY":
        raise RuntimeError(f"owner endpoint failed to initialize: {ready}")
    write_message(
        worker.stdin,
        {
            "type": "START",
            "public_case": public_case,
            "intervention": intervention,
        },
    )
    result: RunRecord | None = None
    owner_emitted_wire_hashes: list[str] = []
    broker_forwarded_wire_hashes: list[str] = []
    owner_wire_variant_observed: list[bool] = []
    while result is None:
        message = read_message(worker.stdout)
        if message.get("type") == "OWNER_REQUEST":
            write_message(
                owner.stdin,
                {"type": "OWNER_REQUEST", "request": message["request"]},
            )
            owner_raw_line, owner_message = read_raw_message(owner.stdout)
            owner_emitted_wire_hashes.append(
                raw_line_sha256(owner_raw_line)
            )
            owner_wire_variant_observed.append(
                owner_raw_line
                != (
                    json.dumps(
                        owner_message,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
            )
            if response_fault in {"TAMPER", "TAMPER_REHASH"} and (
                owner_message.get("response", {})
                .get("payload", {})
                .get("phase")
                == "sign"
            ):
                owner_message["response"]["object_id"] = "Venue-V:C8"
                if response_fault == "TAMPER_REHASH":
                    body = dict(owner_message["response"])
                    body.pop("owner_authenticator", None)
                    body.pop("response_sha256", None)
                    owner_message["response"]["response_sha256"] = sha256(body)
                forwarded_raw_line = (
                    json.dumps(
                        owner_message,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
            else:
                forwarded_raw_line = owner_raw_line
            broker_forwarded_wire_hashes.append(
                raw_line_sha256(forwarded_raw_line)
            )
            write_raw_message(worker.stdin, forwarded_raw_line)
        elif message.get("type") == "WORKER_RESULT":
            result = _record(message["record"])
        else:
            raise RuntimeError(f"unexpected worker message: {message}")
    worker_observation = next(
        item
        for item in result.trace
        if item["type"] == "PROCESS_BOUNDARY_OBSERVATION"
    )
    owner_emitted_stream_sha256 = sha256(owner_emitted_wire_hashes)
    forwarded_stream_sha256 = sha256(broker_forwarded_wire_hashes)
    result.append(
        {
            "type": "PROCESS_TOPOLOGY_OBSERVATION",
            "runner_pid": os.getpid(),
            "worker_pid": worker.pid,
            "owner_endpoint_pid": owner.pid,
            "worker_owner_process_distinct": worker.pid != owner.pid,
            "owner_emitted_wire_line_sha256": owner_emitted_wire_hashes,
            "broker_forwarded_wire_line_sha256": broker_forwarded_wire_hashes,
            "worker_consumed_wire_line_sha256": worker_observation[
                "owner_response_wire_line_sha256"
            ],
            "owner_emitted_wire_stream_sha256": owner_emitted_stream_sha256,
            "broker_forwarded_wire_stream_sha256": forwarded_stream_sha256,
            "owner_transmitted_bytes_sha256": forwarded_stream_sha256,
            "worker_consumed_bytes_sha256": worker_observation[
                "owner_response_stream_sha256"
            ],
            "owner_emitted_equals_forwarded": (
                owner_emitted_wire_hashes == broker_forwarded_wire_hashes
            ),
            "owner_wire_variant_observed": owner_wire_variant_observed,
            "transmitted_equals_consumed": (
                broker_forwarded_wire_hashes
                == worker_observation["owner_response_wire_line_sha256"]
                and forwarded_stream_sha256
                == worker_observation["owner_response_stream_sha256"]
            ),
        }
    )
    write_message(owner.stdin, {"type": "STOP"})
    owner.stdin.close()
    worker.stdin.close()
    worker_rc = worker.wait(timeout=10)
    owner_rc = owner.wait(timeout=10)
    worker_error = worker.stderr.read()
    owner_error = owner.stderr.read()
    owner.stdout.close()
    owner.stderr.close()
    worker.stdout.close()
    worker.stderr.close()
    if worker_rc or owner_rc:
        raise RuntimeError(
            "subprocess failure "
            f"worker={worker_rc}:{worker_error} owner={owner_rc}:{owner_error}"
        )
    if private_override is not None:
        private_override.close()
    result.trace[-1]["worker_exit_code_before_return"] = worker_rc
    result.trace[-1]["owner_exit_code_before_return"] = owner_rc
    return result


def score_one(
    public_case: dict[str, Any],
    case_truth: dict[str, Any],
    semantic_case_id: str,
    run: RunRecord,
    counterfactuals: list[RunRecord] | None = None,
) -> dict[str, Any]:
    counterfactuals = counterfactuals or []
    transcript_frozen_sha256 = sha256(
        {
            "run": run.body(),
            "counterfactuals": [item.body() for item in counterfactuals],
        }
    )
    grader_input = {
        "type": "GRADE_FROZEN_TRANSCRIPT",
        "public_case": public_case,
        "case_truth": case_truth,
        "semantic_case_id": semantic_case_id,
        "run": run.body(),
        "counterfactuals": [item.body() for item in counterfactuals],
        "transcript_frozen_sha256": transcript_frozen_sha256,
    }
    completed = subprocess.run(
        [sys.executable, "-m", "formation.grader_process"],
        cwd=ROOT,
        input=json.dumps(grader_input, ensure_ascii=False) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT),
        },
        timeout=20,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"grader failed {completed.returncode}: {completed.stderr}"
        )
    message = json.loads(completed.stdout)
    receipt = message["receipt"]
    receipt["process_boundary"] = {
        "grader_pid": message["grader_pid"],
        "runner_pid": os.getpid(),
        "transcript_frozen_before_grading": True,
        "transcript_frozen_sha256": transcript_frozen_sha256,
        "grader_output_cannot_reenter_worker_or_owner": True,
        "worker_terminated_before_grader_start": (
            next(
                item
                for item in reversed(run.trace)
                if item["type"] == "PROCESS_TOPOLOGY_OBSERVATION"
            ).get("worker_exit_code_before_return")
            == 0
        ),
        "owner_endpoint_terminated_before_grader_start": (
            next(
                item
                for item in reversed(run.trace)
                if item["type"] == "PROCESS_TOPOLOGY_OBSERVATION"
            ).get("owner_exit_code_before_return")
            == 0
        ),
    }
    return receipt


def run_experiment(write_outputs: bool = True) -> dict[str, Any]:
    public = load_json(PUBLIC_CASES)
    private = load_json(PRIVATE_TRUTH)
    public_cases = [
        {
            **item,
            "task": json.loads(json.dumps(public["task"])),
            "owner_endpoint_verification_key": public[
                "owner_endpoint_verification_key"
            ],
        }
        for item in public["cases"]
    ]
    results: list[dict[str, Any]] = []
    raw_runs: list[dict[str, Any]] = []

    for public_case in public_cases:
        case_handle = public_case["case_handle"]
        case_id = private["manifest"][case_handle]
        case_truth = private["cases"][case_id]
        baseline = execute_one(public_case)
        counterfactual_runs = []
        if case_id == "E2-CONDITION-FORMATION":
            counterfactual_runs = [
                execute_one(public_case, intervention=intervention)
                for intervention in E2_INTERVENTIONS
            ]
        receipt = score_one(
            public_case,
            case_truth,
            case_id,
            baseline,
            counterfactual_runs,
        )
        results.append(receipt)
        raw_runs.append(baseline.body())
        raw_runs.extend(item.body() for item in counterfactual_runs)

    e2_case = next(
        item
        for item in public_cases
        if private["manifest"][item["case_handle"]]
        == "E2-CONDITION-FORMATION"
    )
    e2_truth = private["cases"]["E2-CONDITION-FORMATION"]
    task_change_run = execute_one(
        e2_case, intervention="MATERIAL_Q_CHANGE_BY_CONTROLLER"
    )
    task_change_receipt = score_one(
        e2_case,
        e2_truth,
        "E2-CONDITION-FORMATION",
        task_change_run,
    )
    results.append(task_change_receipt)
    raw_runs.append(task_change_run.body())

    report_body = {
        "schema_version": "ce001-g3-line-envelope-v2",
        "namespace": "G3",
        "qualification": "QUALIFIED_COMPONENT_OUTPUT",
        "evidence_level": "LOCAL_SYNTHETIC_COMPONENT_MODEL",
        "product_run_status": "NOT_RUN",
        "public_packet_sha256": sha256(public),
        "private_grader_input_sha256": sha256(private),
        "case_result_count": len(results),
        "raw_run_count": len(raw_runs),
        "line_evidence": results,
        "separation": {
            "worker_private_input_observed": False,
            "public_packet_contains_expected_label": False,
            "public_packet_contains_operator_proposal": False,
            "public_packet_uses_opaque_case_handles": True,
            "owner_worker_grader_process_boundary": True,
            "grader_runs_after_transcript_freeze": True,
            "arm_comparison_implemented": False,
        },
    }
    report = {"body": report_body, "body_sha256": sha256(report_body)}
    if write_outputs:
        OUTPUTS.mkdir(parents=True, exist_ok=True)
        (OUTPUTS / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with (OUTPUTS / "traces.jsonl").open("w", encoding="utf-8") as stream:
            for item in raw_runs:
                stream.write(json.dumps(item, ensure_ascii=False, sort_keys=True))
                stream.write("\n")
    return report
