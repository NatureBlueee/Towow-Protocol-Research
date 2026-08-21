from __future__ import annotations

"""Standalone discovery worker.

The controller copies this one file into a fresh temporary directory and
launches it with ``python -I -S``.  It has no package imports and receives only
the frozen interface plus verbatim owner responses over stdin.
"""

from collections import defaultdict
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import types
from typing import Any


INBOUND_RECEIPTS: list[dict[str, Any]] = []


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_message() -> dict[str, Any] | None:
    raw = sys.stdin.buffer.readline()
    if not raw:
        return None
    INBOUND_RECEIPTS.append(
        {
            "byte_length": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    return json.loads(raw)


def write_message(value: dict[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")
    sys.stdout.buffer.flush()


def proposal_id(fields: dict[str, Any]) -> str:
    return "g1p-" + digest(fields)[:16]


def _frames() -> list[Any]:
    frames: list[Any] = []
    frame = sys._getframe()
    while frame is not None:
        frames.append(frame)
        frame = frame.f_back
    return frames


def _malicious_runtime_scan(interface: dict[str, Any]) -> dict[str, Any]:
    """Bounded reflection/closure/gc scan of worker-reachable state.

    String values are returned only as hashes.  The controller can therefore
    test its private canary without transmitting that canary to this process.
    """

    marker_names = {
        "l_" + "benchmark",
        "d_" + "actual",
        "ex" + "pected",
        "or" + "acle",
        "final_" + "proposal",
    }
    reachable_string_hashes: set[str] = set()
    marker_key_hits: set[str] = set()
    bound_self_types: set[str] = set()
    closure_cell_types: set[str] = set()
    stack: list[tuple[Any, int]] = [
        (interface, 0),
        (dict(os.environ), 0),
        (list(sys.argv), 0),
        (list(sys.modules), 0),
    ]
    seen: set[int] = set()
    while stack:
        value, depth = stack.pop()
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        if isinstance(value, str):
            reachable_string_hashes.add(
                hashlib.sha256(value.encode("utf-8")).hexdigest()
            )
            if value.casefold() in marker_names:
                marker_key_hits.add(value.casefold())
            continue
        if depth >= 6:
            continue
        if isinstance(value, dict):
            stack.extend((key, depth + 1) for key in value)
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            stack.extend((item, depth + 1) for item in value)
    for value in globals().values():
        closure = value.__closure__ if isinstance(value, types.FunctionType) else None
        if closure is not None:
            for cell in closure:
                try:
                    cell_value = cell.cell_contents
                except ValueError:
                    continue
                closure_cell_types.add(
                    f"{type(cell_value).__module__}.{type(cell_value).__name__}"
                )
        bound_self = (
            value.__self__
            if isinstance(
                value,
                (types.MethodType, types.BuiltinMethodType),
            )
            else None
        )
        if bound_self is not None:
            bound_self_types.add(
                f"{type(bound_self).__module__}.{type(bound_self).__name__}"
            )
    gc_suspicious_module_hits = sorted(
        {
            type(value).__module__
            for value in gc.get_objects()
            if type(value).__module__.startswith("g1prov")
        }
    )
    return {
        "reachable_string_sha256s": sorted(reachable_string_hashes),
        "marker_key_hits": sorted(marker_key_hits),
        "bound_self_types": sorted(bound_self_types),
        "closure_cell_types": sorted(closure_cell_types),
        "gc_suspicious_module_hits": gc_suspicious_module_hits,
        "objects_scanned": len(seen),
        "frame_local_key_sets": [
            sorted(frame.f_locals)
            for frame in _frames()
        ],
        "global_keys": sorted(globals()),
    }


def runtime_attestation(
    interface: dict[str, Any],
    process_instance_id: str,
    failure_injection: str | None,
) -> dict[str, Any]:
    local_files = sorted(
        str(path.relative_to(Path.cwd()))
        for path in Path.cwd().rglob("*")
        if path.is_file()
    )
    return {
        "pid": (
            424242
            if failure_injection == "WORKER_PID_MISMATCH"
            else os.getpid()
        ),
        "process_instance_id": process_instance_id,
        "cwd": str(Path.cwd()),
        "isolated_flag": sys.flags.isolated,
        "no_site_flag": sys.flags.no_site,
        "sys_path": list(sys.path),
        "loaded_module_names": sorted(sys.modules),
        "global_names": sorted(globals()),
        "frame_module_names": [
            frame.f_globals.get("__name__", "")
            for frame in _frames()
        ],
        "environment_keys": sorted(os.environ),
        "argv": list(sys.argv),
        "input_top_level_keys": sorted(interface),
        "bounded_cwd_path_scan": local_files,
        "stdin_frame_receipts_at_ready": list(INBOUND_RECEIPTS),
        "malicious_runtime_scan": _malicious_runtime_scan(interface),
    }


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--probe-readable-path":
        target = Path(sys.argv[2])
        write_message(
            {
                "type": "PATH_PROBE_RESULT",
                "pid": os.getpid(),
                "target_exists": target.exists(),
                "target_readable": os.access(target, os.R_OK),
                "content_opened": False,
            }
        )
        return
    init = read_message()
    if init is None or init.get("type") != "WORKER_INIT":
        raise SystemExit("WORKER_INIT required")
    interface = init["interface"]
    process_instance_id = init["controller_assigned_process_instance_id"]
    failure_injection = init.get("boundary_test_injection")
    write_message(
        {
            "type": "WORKER_READY",
            "method": "EVIDENCE_FIRST_DISCOVERY_PROCESS",
            "attestation": runtime_attestation(
                interface,
                process_instance_id,
                failure_injection,
            ),
        }
    )
    worker_origin = {
        "pid": os.getpid(),
        "process_instance_id": process_instance_id,
    }
    if interface["boundary"] != "IntentAtCoordinationInterface":
        write_message(
            {
                "type": "WORKER_RESULT",
                "proposal": None,
                "notes": ["wrong_intent_boundary"],
                "stdin_frame_receipts": list(INBOUND_RECEIPTS),
                "worker_origin": worker_origin,
            }
        )
        return

    predicates = {
        "q_version": interface["q_version"],
        "object_id": interface["object_id"],
        "deadline": interface["constraints"]["deadline"],
        "power_kw": interface["constraints"]["power_kw"],
        "exact_target_only": interface["constraints"]["exact_target_only"],
    }
    by_candidate: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    saw_refusal = False
    for kind in interface["discovery_api"]["query_kinds"]:
        write_message(
            {
                "type": "DISCOVER",
                "kind": kind,
                "predicates": predicates,
                "worker_origin": worker_origin,
            }
        )
        response = read_message()
        if response is None or response.get("type") != "DISCOVERY_RESPONSE":
            raise SystemExit("DISCOVERY_RESPONSE required")
        saw_refusal = saw_refusal or bool(response.get("refusals"))
        for event in response.get("events", []):
            by_candidate[event["candidate_id"]][kind].append(event)

    complete_ids = sorted(
        candidate_id
        for candidate_id, by_kind in by_candidate.items()
        if all(by_kind.get(kind) for kind in ("candidate", "resource", "partner"))
    )
    if not complete_ids:
        write_message(
            {
                "type": "WORKER_RESULT",
                "proposal": None,
                "notes": [
                    "refused_or_unknown" if saw_refusal else "no_complete_candidate"
                ],
                "stdin_frame_receipts": list(INBOUND_RECEIPTS),
                "worker_origin": worker_origin,
            }
        )
        return

    candidate_id = complete_ids[0]
    by_kind = by_candidate[candidate_id]
    candidate_event = by_kind["candidate"][0]
    resource_event = by_kind["resource"][0]
    partner_event = by_kind["partner"][0]
    selected = [candidate_event, resource_event, partner_event]
    id_fields = {
        "episode_id": interface["episode_id"],
        "q_version": interface["q_version"],
        "object_id": interface["object_id"],
        "operation_id": interface["operation_id"],
        "candidate_id": candidate_id,
        "resource_id": resource_event["subject_id"],
        "partner_id": partner_event["subject_id"],
    }
    write_message(
        {
            "type": "WORKER_RESULT",
            "proposal": {
                **id_fields,
                "owner_ids": sorted({item["issuer_id"] for item in selected}),
                "evidence_ids": [item["evidence_id"] for item in selected],
                "status": "CANDIDATE_NOT_COMMITMENT",
                "proposal_id": proposal_id(id_fields),
            },
            "notes": [],
            "stdin_frame_receipts": list(INBOUND_RECEIPTS),
            "worker_origin": worker_origin,
        }
    )


if __name__ == "__main__":
    main()
