"""A4 deterministic mature composition.

The child receives only the frozen public manifest and IPC endpoints.  It
cannot receive or import the private case truth.
"""

from __future__ import annotations

import multiprocessing
import os
import pathlib
import sys
from typing import Any, Mapping

from services import make_request, rpc


def _call(
    transcript: dict[str, Any],
    endpoints: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
    service_id: str,
    action: str,
    minute: int,
    arguments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    request = make_request(
        owner_id=service_id,
        action=action,
        manifest=manifest,
        observed_at_minute=minute,
        arguments=arguments,
    )
    request_log_key = "target_requests" if service_id == "TARGET" else "requests"
    transcript[request_log_key].append(
        {
            "request_id": request["request_id"],
            "request_nonce": request["request_nonce"],
            "request_bytes": request["request_bytes"],
            "request_sha256": request["request_sha256"],
            "owner_id": service_id,
            "payload": request["payload"],
        }
    )
    response = rpc(endpoints[service_id], request)
    transcript["events"].append(
        {
            "kind": "SERVICE_RETURN",
            "service_id": service_id,
            "request_id": request["request_id"],
            "response": response,
        }
    )
    return response


def arm_process(
    start_payload: Mapping[str, Any],
    owner_endpoints: Mapping[str, Mapping[str, Any]],
    target_endpoint: Mapping[str, Any],
    result_queue: Any,
) -> None:
    runtime_policy = start_payload["runtime_policy"]
    os.chdir(runtime_policy["cwd"])
    os.environ.clear()
    os.environ.update(runtime_policy["minimal_environment"])
    fd_root = pathlib.Path("/dev/fd")
    inherited_fds = sorted(
        entry.name for entry in fd_root.iterdir()
    ) if fd_root.exists() else []
    manifest = start_payload["episode_manifest"]
    transcript: dict[str, Any] = {
        "arm_id": manifest["arm_id"],
        "process_id": os.getpid(),
        "run_id": manifest["run_id"],
        "arm_binding_token": manifest["arm_binding_token"],
        "requests": [],
        "target_requests": [],
        "events": [
            {
                "kind": "RUNTIME_VISIBILITY_OBSERVATION",
                "cwd": os.getcwd(),
                "argv": list(sys.argv),
                "process_name": multiprocessing.current_process().name,
                "environment_keys": sorted(os.environ),
                "inherited_file_descriptors": inherited_fds,
                "network_allowlist": runtime_policy["network_allowlist"],
                "file_allowlist": runtime_policy["file_allowlist"],
                "enforcement_boundary": runtime_policy["enforcement_boundary"],
            }
        ],
    }
    endpoints = dict(owner_endpoints)
    endpoints["TARGET"] = target_endpoint
    _call(transcript, endpoints, manifest, "O_R", "DISCOVER", 0)
    venue_authority = _call(
        transcript, endpoints, manifest, "O_V", "AUTHORITY", 0
    )
    venue_payload = venue_authority.get("payload", {})
    if (
        venue_payload.get("decision") in {"REFUSE", "REFUSED", "DENY", "DENIED"}
        and venue_payload.get("non_delegable") is True
    ):
        transcript["events"].append(
            {
                "kind": "BOUNDED_STOP",
                "basis_response_sha256": venue_authority["response_sha256"],
                "observed_decision": venue_payload["decision"],
            }
        )
        transcript["events"].append(
            {
                "kind": "TERMINAL",
                "minute": 1,
                "disposition": "BOUNDED_REFUSAL",
                "basis_response_sha256": venue_authority["response_sha256"],
            }
        )
        transcript["terminal_disposition"] = "BOUNDED_REFUSAL"
    elif venue_payload.get("decision") in {
        "ALLOW",
        "AUTHORIZED",
        "APPROVE",
        "APPROVED",
    }:
        authority = {"O_V": venue_authority}
        authority.update(
            {
                owner_id: _call(
                    transcript, endpoints, manifest, owner_id, "AUTHORITY", 0
                )
                for owner_id in ("O_R", "O_S")
            }
        )
        execution = _call(
            transcript,
            endpoints,
            manifest,
            "TARGET",
            "EXECUTE",
            0,
            {"authority_receipts": list(authority.values())},
        )
        if runtime_policy.get("duplicate_execute_probe") is True:
            replay = _call(
                transcript,
                endpoints,
                manifest,
                "TARGET",
                "EXECUTE",
                1,
                {"authority_receipts": list(authority.values())},
            )
            transcript["events"].append(
                {
                    "kind": "IDEMPOTENCY_PROBE",
                    "first_occurrence_event_sha256": execution["payload"][
                        "occurrence_event_sha256"
                    ],
                    "replay_decision": replay["payload"]["decision"],
                    "replay_occurrence_event_sha256": replay["payload"][
                        "occurrence_event_sha256"
                    ],
                }
            )
        readback = _call(
            transcript, endpoints, manifest, "TARGET", "READBACK", 46
        )
        effect_digest = readback["payload"]["effect_digest"]
        readback_event_sha256 = readback["payload"]["readback_event_sha256"]
        _call(
            transcript,
            endpoints,
            manifest,
            "O_E",
            "OBSERVE_EFFECT",
            46,
            {
                "effect_digest": effect_digest,
                "readback_event_sha256": readback_event_sha256,
            },
        )
        accept_q = _call(
            transcript,
            endpoints,
            manifest,
            "O_Q",
            "ACCEPT",
            46,
            {
                "effect_digest": effect_digest,
                "readback_event_sha256": readback_event_sha256,
            },
        )
        accept_v = _call(
            transcript,
            endpoints,
            manifest,
            "O_V",
            "ACCEPT",
            46,
            {
                "effect_digest": effect_digest,
                "readback_event_sha256": readback_event_sha256,
            },
        )
        _call(
            transcript,
            endpoints,
            manifest,
            "O_P",
            "FINALIZE",
            47,
            {
                "acceptance_hashes": [
                    accept_q["response_sha256"],
                    accept_v["response_sha256"],
                ]
            },
        )
        transcript["terminal_disposition"] = "COMPOSITION_COMPLETED"
    else:
        transcript["events"].append(
            {
                "kind": "TERMINAL",
                "minute": 1,
                "disposition": "UNKNOWN_AUTHORITY_STATE",
                "basis_response_sha256": venue_authority["response_sha256"],
            }
        )
        transcript["terminal_disposition"] = "UNKNOWN_AUTHORITY_STATE"
    result_queue.put(transcript)
