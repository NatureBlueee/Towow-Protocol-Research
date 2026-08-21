from __future__ import annotations

"""Controller-side byte relay for the G1 owner/worker process boundary."""

import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import uuid

from .fixtures import World
from .model import (
    CandidateProposal,
    Cost,
    EvidenceEvent,
    OperatorEvent,
    Trace,
    SYNTHETIC_OWNER_SOURCE,
    canonical_bytes,
    digest,
)


PRIVATE_INPUT_CANARY = "ce001-private-input-canary:24f515593f3344bb"
FORBIDDEN_WORKER_MARKERS = (
    b'"l_benchmark"',
    b'"d_actual"',
    b'"expected"',
    b'"oracle"',
    b'"final_proposal"',
    PRIVATE_INPUT_CANARY.encode("utf-8"),
)
HERE = Path(__file__).resolve().parent
WORKER_SOURCE = HERE / "worker_process.py"
OWNER_SOURCE = HERE / "owner_process.py"


class ProcessBoundaryViolation(RuntimeError):
    """A child identity/source claim did not match controller observation."""

    def __init__(
        self,
        code: str,
        *,
        claimed: Any,
        expected: Any,
        frames: list[dict[str, Any]],
        actual_worker_pid: int,
        actual_owner_pid: int,
        owner_launch_binding: dict[str, str],
        worker_process_instance_id: str,
    ) -> None:
        self.code = code
        self.receipt = {
            "status": "FAIL_CLOSED",
            "reason": code,
            "claimed": claimed,
            "expected": expected,
            "controller_observed": {
                "controller_pid": os.getpid(),
                "worker_popen_pid": actual_worker_pid,
                "owner_popen_pid": actual_owner_pid,
            },
            "controller_assigned": {
                "owner_launch_binding": deepcopy(owner_launch_binding),
                "worker_process_instance_id": worker_process_instance_id,
            },
            "raw_boundary_trace": deepcopy(frames),
            "raw_boundary_trace_sha256": digest(frames),
            "same_user_hostile_os_isolation": "RED_NOT_ISOLATED",
        }
        super().__init__(
            f"{code}: claimed={claimed!r} expected={expected!r}"
        )


def _new_instance_id(role: str) -> str:
    return f"G1-{role}-{uuid.uuid4().hex}"


def _raise_boundary_violation(
    code: str,
    *,
    claimed: Any,
    expected: Any,
    frames: list[dict[str, Any]],
    worker: subprocess.Popen[bytes],
    owner: subprocess.Popen[bytes],
    owner_launch_binding: dict[str, str],
    worker_process_instance_id: str,
) -> None:
    raise ProcessBoundaryViolation(
        code,
        claimed=claimed,
        expected=expected,
        frames=frames,
        actual_worker_pid=worker.pid,
        actual_owner_pid=owner.pid,
        owner_launch_binding=owner_launch_binding,
        worker_process_instance_id=worker_process_instance_id,
    )


def _validate_owner_ready(
    ready: dict[str, Any],
    *,
    frames: list[dict[str, Any]],
    worker: subprocess.Popen[bytes],
    owner: subprocess.Popen[bytes],
    owner_launch_binding: dict[str, str],
    worker_process_instance_id: str,
) -> None:
    checks = {
        "OWNER_READY_PID_MISMATCH": (
            ready.get("pid"),
            owner.pid,
        ),
        "OWNER_READY_SOURCE_TYPE_MISMATCH": (
            ready.get("source_type"),
            owner_launch_binding["source_type"],
        ),
        "OWNER_READY_SOURCE_INSTANCE_MISMATCH": (
            ready.get("source_instance_id"),
            owner_launch_binding["source_instance_id"],
        ),
        "OWNER_READY_STATE_INSTANCE_MISMATCH": (
            ready.get("state_instance_id"),
            owner_launch_binding["state_instance_id"],
        ),
        "OWNER_READY_PROCESS_INSTANCE_MISMATCH": (
            ready.get("process_instance_id"),
            owner_launch_binding["process_instance_id"],
        ),
    }
    for code, (claimed, expected) in checks.items():
        if claimed != expected:
            _raise_boundary_violation(
                code,
                claimed=claimed,
                expected=expected,
                frames=frames,
                worker=worker,
                owner=owner,
                owner_launch_binding=owner_launch_binding,
                worker_process_instance_id=worker_process_instance_id,
            )


def _validate_worker_claim(
    claim: dict[str, Any],
    *,
    phase: str,
    frames: list[dict[str, Any]],
    worker: subprocess.Popen[bytes],
    owner: subprocess.Popen[bytes],
    owner_launch_binding: dict[str, str],
    worker_process_instance_id: str,
) -> None:
    checks = {
        f"{phase}_PID_MISMATCH": (claim.get("pid"), worker.pid),
        f"{phase}_PROCESS_INSTANCE_MISMATCH": (
            claim.get("process_instance_id"),
            worker_process_instance_id,
        ),
    }
    for code, (claimed, expected) in checks.items():
        if claimed != expected:
            _raise_boundary_violation(
                code,
                claimed=claimed,
                expected=expected,
                frames=frames,
                worker=worker,
                owner=owner,
                owner_launch_binding=owner_launch_binding,
                worker_process_instance_id=worker_process_instance_id,
            )


def _validate_owner_response_origin(
    response: dict[str, Any],
    *,
    phase: str,
    frames: list[dict[str, Any]],
    worker: subprocess.Popen[bytes],
    owner: subprocess.Popen[bytes],
    owner_launch_binding: dict[str, str],
    worker_process_instance_id: str,
) -> None:
    origin = response.get("origin_attestation")
    if not isinstance(origin, dict):
        _raise_boundary_violation(
            f"{phase}_ORIGIN_ATTESTATION_MISSING",
            claimed=origin,
            expected="controller-bound owner origin",
            frames=frames,
            worker=worker,
            owner=owner,
            owner_launch_binding=owner_launch_binding,
            worker_process_instance_id=worker_process_instance_id,
        )
    checks = {
        f"{phase}_ORIGIN_PID_MISMATCH": (origin.get("pid"), owner.pid),
        f"{phase}_SOURCE_TYPE_MISMATCH": (
            origin.get("source_type"),
            owner_launch_binding["source_type"],
        ),
        f"{phase}_SOURCE_INSTANCE_MISMATCH": (
            origin.get("source_instance_id"),
            owner_launch_binding["source_instance_id"],
        ),
        f"{phase}_STATE_INSTANCE_MISMATCH": (
            origin.get("state_instance_id"),
            owner_launch_binding["state_instance_id"],
        ),
        f"{phase}_PROCESS_INSTANCE_MISMATCH": (
            origin.get("process_instance_id"),
            owner_launch_binding["process_instance_id"],
        ),
    }
    for code, (claimed, expected) in checks.items():
        if claimed != expected:
            _raise_boundary_violation(
                code,
                claimed=claimed,
                expected=expected,
                frames=frames,
                worker=worker,
                owner=owner,
                owner_launch_binding=owner_launch_binding,
                worker_process_instance_id=worker_process_instance_id,
            )
    for event in response.get("events", []):
        event_checks = {
            "OWNER_EVENT_ORIGIN_PID_MISMATCH": (
                event.get("origin_process_id"),
                owner.pid,
            ),
            "OWNER_EVENT_SOURCE_TYPE_MISMATCH": (
                event.get("owner_source_type"),
                owner_launch_binding["source_type"],
            ),
            "OWNER_EVENT_SOURCE_INSTANCE_MISMATCH": (
                event.get("owner_source_instance_id"),
                owner_launch_binding["source_instance_id"],
            ),
            "OWNER_EVENT_STATE_INSTANCE_MISMATCH": (
                event.get("owner_state_instance_id"),
                owner_launch_binding["state_instance_id"],
            ),
            "OWNER_EVENT_PROCESS_INSTANCE_MISMATCH": (
                event.get("owner_process_instance_id"),
                owner_launch_binding["process_instance_id"],
            ),
            "OWNER_EVENT_STATE_VERSION_MISMATCH": (
                event.get("owner_state_version"),
                origin.get("owner_state_version"),
            ),
        }
        for code, (claimed, expected) in event_checks.items():
            if claimed != expected:
                _raise_boundary_violation(
                    code,
                    claimed={
                        "evidence_id": event.get("evidence_id"),
                        "value": claimed,
                    },
                    expected=expected,
                    frames=frames,
                    worker=worker,
                    owner=owner,
                    owner_launch_binding=owner_launch_binding,
                    worker_process_instance_id=worker_process_instance_id,
                )


def _wire_bytes(value: dict[str, Any]) -> bytes:
    return canonical_bytes(value) + b"\n"


def _record_frame(
    frames: list[dict[str, Any]],
    *,
    sender: str,
    recipient: str,
    wire: bytes,
) -> None:
    frames.append(
        {
            "sequence": len(frames),
            "sender": sender,
            "recipient": recipient,
            "byte_length": len(wire),
            "sha256": hashlib.sha256(wire).hexdigest(),
            "wire_b64": base64.b64encode(wire).decode("ascii"),
        }
    )


def _send(
    process: subprocess.Popen[bytes],
    frames: list[dict[str, Any]],
    *,
    sender: str,
    recipient: str,
    wire: bytes,
) -> None:
    if process.stdin is None:
        raise RuntimeError(f"{recipient} stdin unavailable")
    process.stdin.write(wire)
    process.stdin.flush()
    _record_frame(frames, sender=sender, recipient=recipient, wire=wire)


def _receive(
    process: subprocess.Popen[bytes],
    frames: list[dict[str, Any]],
    *,
    sender: str,
    recipient: str,
) -> tuple[bytes, dict[str, Any]]:
    if process.stdout is None:
        raise RuntimeError(f"{sender} stdout unavailable")
    readable, _, _ = select.select([process.stdout], [], [], 45)
    if not readable:
        exit_status = process.poll()
        stderr = ""
        if exit_status is not None and process.stderr is not None:
            stderr = process.stderr.read().decode("utf-8", errors="replace")
        raise TimeoutError(
            "protocol receive timeout "
            f"sender={sender} recipient={recipient} pid={process.pid} "
            f"exit_status={exit_status} stderr={stderr!r}"
        )
    wire = process.stdout.readline()
    if not wire:
        stderr = (
            process.stderr.read().decode("utf-8", errors="replace")
            if process.stderr is not None
            else ""
        )
        raise RuntimeError(f"{sender} closed protocol stream: {stderr}")
    _record_frame(frames, sender=sender, recipient=recipient, wire=wire)
    return wire, json.loads(wire)


def _isolated_env() -> dict[str, str]:
    return {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
    }


def _spawn(script: Path, cwd: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-I", "-S", str(script)],
        cwd=cwd,
        env=_isolated_env(),
        # _receive() uses select() on the pipe descriptor.  BufferedReader
        # read-ahead can otherwise consume the next JSONL frame into Python's
        # user-space buffer, leaving the descriptor non-readable and causing
        # a false protocol timeout.
        bufsize=0,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _event_from_wire(value: dict[str, Any]) -> EvidenceEvent:
    return EvidenceEvent(**value)


def _proposal_from_wire(value: dict[str, Any] | None) -> CandidateProposal | None:
    if value is None:
        return None
    return CandidateProposal(
        **{
            **value,
            "owner_ids": tuple(value["owner_ids"]),
            "evidence_ids": tuple(value["evidence_ids"]),
        }
    )


def run_process_episode(
    world: World,
    *,
    intervention: str,
    removed_operator: str | None,
    reversed_operator: str | None,
    failure_injection: str | None,
) -> tuple[Trace, dict[str, Any]]:
    private_runtime_input_bytes = canonical_bytes(
        {
            "expected": world.expected,
            "L_benchmark": world.l_benchmark,
            "D_actual": world.d_actual,
            "oracle_roots": {
                "source_aliases": world.source_aliases,
                "authority_aliases": world.authority_aliases,
                "min_unique_sources": world.min_unique_sources,
            },
            "private_canary": PRIVATE_INPUT_CANARY,
        }
    )
    frames: list[dict[str, Any]] = []
    worker_queries: list[dict[str, Any]] = []
    owner_responses: list[dict[str, Any]] = []
    operator_events: list[OperatorEvent] = []
    operator_notes: list[str] = []
    worker_attestation: dict[str, Any] = {}
    worker_result: dict[str, Any] | None = None
    owner_launch_binding = {
        "source_type": SYNTHETIC_OWNER_SOURCE,
        "source_instance_id": _new_instance_id("OWNER-SOURCE"),
        "state_instance_id": _new_instance_id("OWNER-STATE"),
        "process_instance_id": _new_instance_id("OWNER-PROCESS"),
    }
    worker_process_instance_id = _new_instance_id("WORKER-PROCESS")

    with tempfile.TemporaryDirectory(prefix="g1-worker-") as worker_tmp_name, (
        tempfile.TemporaryDirectory(prefix="g1-owner-")
    ) as owner_tmp_name:
        worker_tmp = Path(worker_tmp_name)
        owner_tmp = Path(owner_tmp_name)
        copied_worker = worker_tmp / "worker_process.py"
        copied_owner = owner_tmp / "owner_process.py"
        shutil.copy2(WORKER_SOURCE, copied_worker)
        shutil.copy2(OWNER_SOURCE, copied_owner)
        worker = _spawn(copied_worker, worker_tmp)
        owner = _spawn(copied_owner, owner_tmp)
        try:
            owner_init = {
                "type": "OWNER_INIT",
                "interface": deepcopy(world.interface),
                "records": deepcopy(world.records),
                "operators": deepcopy(world.operators),
                "allow_t0_queries": True,
                "allow_operators": (
                    intervention == "FULL_ACTUAL_TRACE"
                    or failure_injection == "POST_TREATMENT_T0"
                ),
                "removed_operator": removed_operator,
                "reversed_operator": reversed_operator,
                "failure_injection": failure_injection,
                "controller_assigned_launch_binding": owner_launch_binding,
            }
            _send(
                owner,
                frames,
                sender="controller",
                recipient="owner",
                wire=_wire_bytes(owner_init),
            )
            _, owner_ready = _receive(
                owner,
                frames,
                sender="owner",
                recipient="controller",
            )
            if owner_ready.get("type") != "OWNER_READY":
                raise RuntimeError(f"unexpected owner ready: {owner_ready}")
            _validate_owner_ready(
                owner_ready,
                frames=frames,
                worker=worker,
                owner=owner,
                owner_launch_binding=owner_launch_binding,
                worker_process_instance_id=worker_process_instance_id,
            )

            if (
                intervention == "FULL_ACTUAL_TRACE"
                or failure_injection == "POST_TREATMENT_T0"
            ):
                for spec in world.operators:
                    operator_request = _wire_bytes(
                        {
                            "type": "APPLY_OPERATOR",
                            "operator_id": spec["operator_id"],
                        }
                    )
                    _send(
                        owner,
                        frames,
                        sender="controller",
                        recipient="owner",
                        wire=operator_request,
                    )
                    _, response = _receive(
                        owner,
                        frames,
                        sender="owner",
                        recipient="controller",
                    )
                    _validate_owner_response_origin(
                        response,
                        phase="OWNER_OPERATOR_RESPONSE",
                        frames=frames,
                        worker=worker,
                        owner=owner,
                        owner_launch_binding=owner_launch_binding,
                        worker_process_instance_id=worker_process_instance_id,
                    )
                    status = response["status"]
                    if status == "REMOVED":
                        operator_notes.append(
                            f"operator_removed:{spec['operator_id']}"
                        )
                    if response.get("operator_event"):
                        event = response["operator_event"]
                        operator_events.append(
                            OperatorEvent(
                                **{
                                    **event,
                                    "created_evidence_ids": tuple(
                                        event["created_evidence_ids"]
                                    ),
                                }
                            )
                        )

            worker_init = {
                "type": "WORKER_INIT",
                "interface": deepcopy(world.interface),
                "controller_assigned_process_instance_id": (
                    worker_process_instance_id
                ),
            }
            # Only the worker's own PID-attestation injection must reach the
            # worker.  Semantic owner/evaluator failure labels remain outside
            # method-visible bytes so a worker cannot special-case the attack.
            if failure_injection == "WORKER_PID_MISMATCH":
                worker_init["boundary_test_injection"] = failure_injection
            worker_init_wire = _wire_bytes(worker_init)
            _send(
                worker,
                frames,
                sender="controller",
                recipient="worker",
                wire=worker_init_wire,
            )
            _, ready = _receive(
                worker,
                frames,
                sender="worker",
                recipient="controller",
            )
            if ready.get("type") != "WORKER_READY":
                raise RuntimeError(f"unexpected worker ready: {ready}")
            worker_attestation = ready["attestation"]
            _validate_worker_claim(
                worker_attestation,
                phase="WORKER_READY",
                frames=frames,
                worker=worker,
                owner=owner,
                owner_launch_binding=owner_launch_binding,
                worker_process_instance_id=worker_process_instance_id,
            )

            while True:
                worker_wire, request = _receive(
                    worker,
                    frames,
                    sender="worker",
                    recipient="controller",
                )
                if request.get("type") == "WORKER_RESULT":
                    _validate_worker_claim(
                        request.get("worker_origin", {}),
                        phase="WORKER_RESULT",
                        frames=frames,
                        worker=worker,
                        owner=owner,
                        owner_launch_binding=owner_launch_binding,
                        worker_process_instance_id=worker_process_instance_id,
                    )
                    worker_result = request
                    break
                if request.get("type") != "DISCOVER":
                    raise RuntimeError(f"unexpected worker message: {request}")
                _validate_worker_claim(
                    request.get("worker_origin", {}),
                    phase="WORKER_DISCOVER",
                    frames=frames,
                    worker=worker,
                    owner=owner,
                    owner_launch_binding=owner_launch_binding,
                    worker_process_instance_id=worker_process_instance_id,
                )
                worker_queries.append(
                    {
                        "kind": request["kind"],
                        "predicates": deepcopy(request["predicates"]),
                    }
                )
                # This is a byte-for-byte relay: the controller neither
                # creates nor rewrites an owner request or response.
                _send(
                    owner,
                    frames,
                    sender="controller",
                    recipient="owner",
                    wire=worker_wire,
                )
                owner_wire, response = _receive(
                    owner,
                    frames,
                    sender="owner",
                    recipient="controller",
                )
                _validate_owner_response_origin(
                    response,
                    phase="OWNER_DISCOVERY_RESPONSE",
                    frames=frames,
                    worker=worker,
                    owner=owner,
                    owner_launch_binding=owner_launch_binding,
                    worker_process_instance_id=worker_process_instance_id,
                )
                owner_responses.append(response)
                _send(
                    worker,
                    frames,
                    sender="controller",
                    recipient="worker",
                    wire=owner_wire,
                )

            stop_wire = _wire_bytes({"type": "STOP"})
            _send(
                owner,
                frames,
                sender="controller",
                recipient="owner",
                wire=stop_wire,
            )
            _, owner_stopped = _receive(
                owner,
                frames,
                sender="owner",
                recipient="controller",
            )
            _validate_owner_response_origin(
                owner_stopped,
                phase="OWNER_STOPPED",
                frames=frames,
                worker=worker,
                owner=owner,
                owner_launch_binding=owner_launch_binding,
                worker_process_instance_id=worker_process_instance_id,
            )
            worker.wait(timeout=10)
            owner.wait(timeout=10)
            if worker.returncode != 0 or owner.returncode != 0:
                raise RuntimeError(
                    f"process exit worker={worker.returncode} owner={owner.returncode}"
                )
        finally:
            for process in (worker, owner):
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=3)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()

    if worker_result is None:
        raise RuntimeError("worker produced no result")
    evidence = [
        _event_from_wire(event)
        for response in owner_responses
        for event in response.get("events", [])
    ]
    refusals = [
        refusal
        for response in owner_responses
        for refusal in response.get("refusals", [])
    ]
    trace = Trace(
        episode_id=world.interface["episode_id"],
        intervention=intervention,
        method="EVIDENCE_FIRST_DISCOVERY_PROCESS",
        intent_boundary=world.interface["boundary"],
        prelude_receipt_hash=world.interface[
            "clarification_prelude_receipt_hash"
        ],
        queries=worker_queries,
        evidence=evidence,
        refusals=refusals,
        operators=operator_events,
        proposal=_proposal_from_wire(worker_result.get("proposal")),
        notes=operator_notes + list(worker_result.get("notes", [])),
        cost=Cost(
            interface_reads=1,
            owner_queries=len(worker_queries),
            evidence_items=len(evidence),
            disclosure_units=len(evidence),
        ),
    )

    worker_inbound_frames = [
        frame
        for frame in frames
        if frame["recipient"] == "worker"
    ]
    worker_inbound_bytes = b"".join(
        base64.b64decode(frame["wire_b64"])
        for frame in worker_inbound_frames
    )
    worker_reported_inbound = worker_result.get("stdin_frame_receipts", [])
    controller_recorded_worker_inbound = [
        {
            "byte_length": frame["byte_length"],
            "sha256": frame["sha256"],
        }
        for frame in worker_inbound_frames
    ]
    owner_pid = owner.pid
    discover_request_hashes = {
        frame["sha256"]
        for frame in frames
        if frame["sender"] == "worker"
        and frame["recipient"] == "controller"
        and json.loads(base64.b64decode(frame["wire_b64"])).get("type")
        == "DISCOVER"
    }
    owner_origin_checks = [
        {
            "evidence_id": event.evidence_id,
            "origin_pid_matches_actual_popen": event.origin_process_id == owner_pid,
            "source_type_matches_controller_assignment": (
                event.owner_source_type == SYNTHETIC_OWNER_SOURCE
            ),
            "source_instance_matches_controller_assignment": (
                event.owner_source_instance_id
                == owner_launch_binding["source_instance_id"]
            ),
            "state_instance_matches_controller_assignment": (
                event.owner_state_instance_id
                == owner_launch_binding["state_instance_id"]
            ),
            "process_instance_matches_controller_assignment": (
                event.owner_process_instance_id
                == owner_launch_binding["process_instance_id"]
            ),
            "request_hash_matches_relay": event.request_hash
            in discover_request_hashes,
            "positive_state_version": event.owner_state_version > 0,
        }
        for event in evidence
    ]
    forwarding_checks: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        if frame["sender"] == "worker" and frame["recipient"] == "controller":
            if json.loads(base64.b64decode(frame["wire_b64"])).get("type") != "DISCOVER":
                continue
            forwarded = frames[index + 1]
            forwarding_checks.append(
                {
                    "direction": "worker_to_owner",
                    "source_sha256": frame["sha256"],
                    "forwarded_sha256": forwarded["sha256"],
                    "exact_bytes_equal": (
                        frame["wire_b64"] == forwarded["wire_b64"]
                    ),
                }
            )
        if frame["sender"] == "owner" and frame["recipient"] == "controller":
            payload = json.loads(base64.b64decode(frame["wire_b64"]))
            if payload.get("type") != "DISCOVERY_RESPONSE":
                continue
            forwarded = frames[index + 1]
            forwarding_checks.append(
                {
                    "direction": "owner_to_worker",
                    "source_sha256": frame["sha256"],
                    "forwarded_sha256": forwarded["sha256"],
                    "exact_bytes_equal": (
                        frame["wire_b64"] == forwarded["wire_b64"]
                    ),
                }
            )
    source_entries = []
    for path in (WORKER_SOURCE, OWNER_SOURCE, Path(__file__).resolve()):
        raw = path.read_bytes()
        source_entries.append(
            {
                "name": path.name,
                "byte_length": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    worker_source_bytes = WORKER_SOURCE.read_bytes()
    malicious_scan = worker_attestation["malicious_runtime_scan"]
    private_canary_value_sha256 = hashlib.sha256(
        PRIVATE_INPUT_CANARY.encode("utf-8")
    ).hexdigest()
    receipt = {
        "controller_pid": os.getpid(),
        "worker_pid": worker.pid,
        "owner_pid": owner_pid,
        "distinct_processes": len(
            {os.getpid(), worker.pid, owner_pid}
        )
        == 3,
        "worker_runtime_attestation": worker_attestation,
        "malicious_worker_scan": {
            "private_canary_value_sha256": private_canary_value_sha256,
            "private_canary_hash_absent_from_reachable_strings": (
                private_canary_value_sha256
                not in malicious_scan["reachable_string_sha256s"]
            ),
            "private_field_name_hits": malicious_scan["marker_key_hits"],
            "controller_fixture_module_hits": malicious_scan[
                "gc_suspicious_module_hits"
            ],
            "bound_self_types": malicious_scan["bound_self_types"],
            "closure_cell_types": malicious_scan["closure_cell_types"],
            "objects_scanned": malicious_scan["objects_scanned"],
        },
        "owner_state_contract": owner_ready["state_contract"],
        "owner_source_boundary": {
            "source_type": SYNTHETIC_OWNER_SOURCE,
            "independent_owner_truth": "NOT_ESTABLISHED",
            "independent_owner_origin": "NOT_ESTABLISHED",
            "controller_assigned_launch_binding": owner_launch_binding,
            "controller_observed_popen_pid": owner.pid,
        },
        "process_identity_binding": {
            "controller_observed": {
                "worker_popen_pid": worker.pid,
                "owner_popen_pid": owner.pid,
            },
            "controller_assigned": {
                "worker_process_instance_id": worker_process_instance_id,
                "owner_launch_binding": owner_launch_binding,
            },
            "owner_ready_bound": True,
            "worker_ready_bound": True,
            "worker_result_bound": True,
        },
        "controller_evaluator_private_input": {
            "byte_length": len(private_runtime_input_bytes),
            "sha256": hashlib.sha256(
                private_runtime_input_bytes
            ).hexdigest(),
            "canary_present_in_private_input": (
                PRIVATE_INPUT_CANARY.encode("utf-8")
                in private_runtime_input_bytes
            ),
        },
        "worker_inbound_scan": {
            "byte_length": len(worker_inbound_bytes),
            "sha256": hashlib.sha256(worker_inbound_bytes).hexdigest(),
            "forbidden_marker_hits": [
                marker.decode("utf-8")
                for marker in FORBIDDEN_WORKER_MARKERS
                if marker in worker_inbound_bytes
            ],
            "private_canary_absent": (
                PRIVATE_INPUT_CANARY.encode("utf-8") not in worker_inbound_bytes
            ),
            "worker_reported_frame_receipts": worker_reported_inbound,
            "controller_recorded_frame_receipts": (
                controller_recorded_worker_inbound
            ),
            "worker_report_matches_controller": (
                worker_reported_inbound
                == controller_recorded_worker_inbound
            ),
            "worker_source_forbidden_marker_hits": [
                marker.decode("utf-8")
                for marker in FORBIDDEN_WORKER_MARKERS
                if marker in worker_source_bytes
            ],
        },
        "controller_raw_forwarding": {
            "checks": forwarding_checks,
            "all_exact_bytes_equal": bool(forwarding_checks)
            and all(item["exact_bytes_equal"] for item in forwarding_checks),
        },
        "owner_event_origin": {
            "checks": owner_origin_checks,
            "all_owner_generated_and_request_bound": bool(owner_origin_checks)
            and all(
                item["origin_pid_matches_actual_popen"]
                and item["source_type_matches_controller_assignment"]
                and item["source_instance_matches_controller_assignment"]
                and item["state_instance_matches_controller_assignment"]
                and item["process_instance_matches_controller_assignment"]
                and item["request_hash_matches_relay"]
                and item["positive_state_version"]
                for item in owner_origin_checks
            ),
        },
        "source_artifacts": source_entries,
        "raw_boundary_trace": frames,
        "raw_boundary_trace_sha256": digest(frames),
        "same_user_hostile_os_isolation": "RED_NOT_ISOLATED",
    }
    return trace, receipt


def run_same_user_path_probe() -> dict[str, Any]:
    """Executable red: same-UID filesystem readability is not sandboxing.

    The probe checks metadata/access only and does not open or return contents.
    It is an adversarial boundary run, not the evaluated discovery worker.
    """

    with tempfile.TemporaryDirectory(prefix="g1-path-probe-") as temporary_name:
        temporary = Path(temporary_name)
        copied_worker = temporary / "worker_process.py"
        shutil.copy2(WORKER_SOURCE, copied_worker)
        target = HERE / "fixtures.py"
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                str(copied_worker),
                "--probe-readable-path",
                str(target),
            ],
            cwd=temporary,
            env=_isolated_env(),
            input=b"",
            capture_output=True,
            check=False,
            timeout=10,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode("utf-8", errors="replace"))
        probe = json.loads(completed.stdout)
    return {
        "attack": "SAME_USER_ABSOLUTE_PATH_READABILITY",
        "status": (
            "RED_NOT_ISOLATED"
            if probe["target_readable"]
            else "NOT_REPRODUCED"
        ),
        "probe": probe,
        "interpretation": (
            "Process separation and sanitized cwd do not block a same-user "
            "hostile process that already knows an absolute repository path."
        ),
    }
