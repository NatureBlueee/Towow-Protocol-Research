"""Executable E3 acknowledgement-loss paired world.

This module composes two Wave 015 foundation primitives without modifying
them:

* ``BlindProcessLauncher`` is the actual arm process boundary.
* ``TargetOperationLedger`` is the only authoritative mutation path.

The two arms receive the same byte-for-byte startup view and emit the same
submit/status-query prefix.  The broker-private worlds differ only in whether
the first submit reached the Target ledger before the public outcome became
unconfirmed.  The first arm-visible semantic difference is the Target-signed
exact status response.

This is a local digital experiment.  It does not establish a physical Effect,
legal Authority, independent Principal identity, or production suitability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import queue
import sqlite3
import sys
import uuid
from functools import partial
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


HERE = Path(__file__).resolve().parent
WAVE015 = HERE.parent / "wave-015-runner-foundation"
if str(WAVE015) not in sys.path:
    sys.path.insert(0, str(WAVE015))

from target_ledger import COMMITTED, TargetOperationLedger  # noqa: E402
from visibility import (  # noqa: E402
    PUBLIC_INPUT_SCHEMA,
    ArmViewFactory,
    BlindProcessLauncher,
    canonical_bytes,
    sha256_value,
)


ARM_ID = "A4-MATURE-ACK-RECONCILIATION"
OBJECT_ID = "VenueV:CircuitC7"
TARGET_ID = "VenueV:CircuitC7"
DECOY_OBJECT_ID = "VenueV:CircuitC8"
INITIAL_STATE = {"energized": False, "power_kw": 0.0}
DESIRED_STATE = {"energized": True, "power_kw": 3.0}

OUTCOME_UNCONFIRMED = "OUTCOME_UNCONFIRMED"
RECOVERED_EXISTING_EFFECT_NO_REPLAY = "RECOVERED_EXISTING_EFFECT_NO_REPLAY"
RECOVERED_NO_EFFECT_SAFE_RETRY = "RECOVERED_NO_EFFECT_SAFE_RETRY"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _without(value: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    excluded = set(keys)
    return {key: item for key, item in value.items() if key not in excluded}


def _private_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()


def _public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def _sign_record(
    private_key: Ed25519PrivateKey,
    value: MutableMapping[str, Any],
) -> Dict[str, Any]:
    signed = copy.deepcopy(dict(value))
    signed["target_public_key_hex"] = _public_key_hex(private_key)
    signed["signature_hex"] = private_key.sign(
        canonical_bytes(_without(signed, "signature_hex"))
    ).hex()
    return signed


def verify_target_signature(
    value: Mapping[str, Any],
    expected_public_key_hex: str | None = None,
) -> bool:
    """Verify self-contained Target-service signature integrity.

    The key is transported in the signed response.  The fixed broker endpoint
    is the trust boundary in this local experiment; no external PKI claim is
    made.
    """

    try:
        if (
            expected_public_key_hex is not None
            and value.get("target_public_key_hex") != expected_public_key_hex
        ):
            return False
        public_key = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(str(value["target_public_key_hex"]))
        )
        public_key.verify(
            bytes.fromhex(str(value["signature_hex"])),
            canonical_bytes(_without(value, "signature_hex")),
        )
        return True
    except (KeyError, TypeError, ValueError):
        return False
    except Exception:
        return False


def _public_input() -> Dict[str, Any]:
    return {
        "schema": PUBLIC_INPUT_SCHEMA,
        "task": {
            "q_version": "Q@v1",
            "object_id": OBJECT_ID,
            "target_id": TARGET_ID,
            "deadline_minute": 90,
            "required_duration_minutes": 45,
            "required_power_kw": 3.0,
            "power_tolerance_percent": 5,
        },
    }


def build_shared_arm_view() -> Dict[str, Any]:
    """Build one view object which is reused unchanged by both arm launches."""

    return ArmViewFactory(arm_id=ARM_ID).build(_public_input())


def _operation_handle(view: Mapping[str, Any]) -> str:
    return "handle-" + sha256_value(
        {
            "public_run_id": view["public_run_id"],
            "episode_instance_id": view["episode_instance_id"],
            "operation_id": view["operation_id"],
        }
    )[:32]


def _submit_request(view: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "BROKER_SUBMIT_REQUEST_V1",
        "endpoint_handle": view["broker_surface"]["endpoint_handle"],
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
        "request_id": "request-" + sha256_value(view)[:32],
        "operation": "SET_STATE",
        "expected_version": 0,
        "desired_state": copy.deepcopy(DESIRED_STATE),
    }


def _status_query(
    view: Mapping[str, Any],
    submit: Mapping[str, Any],
    operation_handle: str,
) -> Dict[str, Any]:
    return {
        "schema": "BROKER_EXACT_STATUS_QUERY_V1",
        "endpoint_handle": view["broker_surface"]["endpoint_handle"],
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
        "operation_handle": operation_handle,
        "request_id": submit["request_id"],
    }


def _exchange(
    request_queue: Any,
    response_queue: Any,
    request: Mapping[str, Any],
    transcript: list,
) -> Dict[str, Any]:
    message = copy.deepcopy(dict(request))
    transcript.append({"direction": "ARM_TO_BROKER", "message": message})
    request_queue.put(message)
    try:
        response = response_queue.get(timeout=15)
    except queue.Empty as exc:
        raise RuntimeError("broker response timeout") from exc
    if not isinstance(response, Mapping):
        raise RuntimeError("broker response is not an object")
    response_dict = copy.deepcopy(dict(response))
    transcript.append({"direction": "BROKER_TO_ARM", "message": response_dict})
    if response_dict.get("schema") == "BROKER_ERROR_V1":
        raise RuntimeError("broker failed closed")
    return response_dict


def _assert_exact_binding(
    value: Mapping[str, Any],
    view: Mapping[str, Any],
) -> None:
    expected = {
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
    }
    for field, wanted in expected.items():
        if value.get(field) != wanted:
            raise RuntimeError("exact binding failed for %s" % field)


def _validate_status_envelope(
    envelope: Mapping[str, Any],
    query_request: Mapping[str, Any],
    view: Mapping[str, Any],
) -> None:
    if envelope.get("schema") != "TARGET_OPERATION_STATUS_V1":
        raise RuntimeError("unexpected status envelope schema")
    if not verify_target_signature(envelope):
        raise RuntimeError("Target status signature invalid")
    _assert_exact_binding(envelope, view)
    expected_query_bytes = canonical_bytes(query_request).decode("utf-8")
    if envelope.get("query_request_bytes") != expected_query_bytes:
        raise RuntimeError("status response changed exact query bytes")
    if envelope.get("query_request_sha256") != _sha256_bytes(
        expected_query_bytes.encode("utf-8")
    ):
        raise RuntimeError("status response query hash mismatch")
    coverage = envelope.get("covered_ledger_range")
    if not isinstance(coverage, Mapping):
        raise RuntimeError("missing ledger coverage")
    if coverage.get("through_version") != envelope.get("observed_version"):
        raise RuntimeError("ledger coverage is not current-head bound")
    if coverage.get("current_head") != envelope.get("current_head"):
        raise RuntimeError("coverage head and observed head differ")


def _decoy_exclusions(
    decoys: Sequence[Mapping[str, Any]],
    view: Mapping[str, Any],
) -> list:
    exclusions = []
    for item in decoys:
        reasons = []
        if not verify_target_signature(item):
            reasons.append("SIGNATURE_INVALID")
        for field, expected in (
            ("public_run_id", view["public_run_id"]),
            ("world_id", view["episode_instance_id"]),
            ("object_id", view["object_id"]),
            ("target_id", view["target_id"]),
            ("operation_id", view["operation_id"]),
        ):
            if item.get(field) != expected:
                reasons.append(field.upper() + "_MISMATCH")
        if not reasons:
            raise RuntimeError("a decoy unexpectedly satisfies the exact query")
        exclusions.append(
            {
                "record_sha256": sha256_value(item),
                "excluded": True,
                "reasons": reasons,
            }
        )
    return exclusions


def arm_worker(
    view: Mapping[str, Any],
    request_queue: Any,
    response_queue: Any,
) -> Dict[str, Any]:
    """Scenario-agnostic arm algorithm executed inside the blind child."""

    transcript = []
    submit = _submit_request(view)
    ack = _exchange(request_queue, response_queue, submit, transcript)
    if ack != {
        "schema": "BROKER_SUBMIT_RESULT_V1",
        "status": OUTCOME_UNCONFIRMED,
        "operation_handle": _operation_handle(view),
    }:
        raise RuntimeError("the submit result was not the fixed unconfirmed outcome")

    query_request = _status_query(view, submit, ack["operation_handle"])
    status_response = _exchange(
        request_queue,
        response_queue,
        query_request,
        transcript,
    )
    envelope = status_response.get("status_envelope")
    if not isinstance(envelope, Mapping):
        raise RuntimeError("missing Target status envelope")
    _validate_status_envelope(envelope, query_request, view)
    decoys = status_response.get("nearby_decoys", [])
    if not isinstance(decoys, list):
        raise RuntimeError("nearby decoys must be a list")
    decoy_exclusions = _decoy_exclusions(decoys, view)

    if envelope["status"] == COMMITTED:
        receipt = status_response.get("ledger_receipt")
        readback = status_response.get("ledger_readback")
        if not isinstance(receipt, Mapping) or not isinstance(readback, Mapping):
            raise RuntimeError("committed status lacks ledger evidence")
        if receipt.get("request_id") != submit["request_id"]:
            raise RuntimeError("committed receipt is not for the submitted request")
        if receipt.get("target_id") != view["target_id"]:
            raise RuntimeError("committed receipt targets a different object")
        if readback.get("observed_state") != DESIRED_STATE:
            raise RuntimeError("committed readback does not show desired state")
        disposition = RECOVERED_EXISTING_EFFECT_NO_REPLAY
        retry_performed = False
        final_receipt = copy.deepcopy(dict(receipt))
        final_readback = copy.deepcopy(dict(readback))
        freshness_response = None
    elif envelope["status"] in {"NOT_COMMITTED", "NOT_FOUND"}:
        if envelope.get("matching_occurrence_hashes") != []:
            raise RuntimeError("negative status contains matching occurrences")
        freshness_request = {
            "schema": "BROKER_CAPABILITY_FRESHNESS_QUERY_V1",
            "endpoint_handle": view["broker_surface"]["endpoint_handle"],
            "public_run_id": view["public_run_id"],
            "world_id": view["episode_instance_id"],
            "q_version": view["q_version"],
            "object_id": view["object_id"],
            "target_id": view["target_id"],
            "operation_id": view["operation_id"],
            "request_id": submit["request_id"],
            "observed_negative_head": envelope["current_head"],
        }
        freshness_response = _exchange(
            request_queue,
            response_queue,
            freshness_request,
            transcript,
        )
        freshness = freshness_response.get("capability_freshness")
        if not isinstance(freshness, Mapping):
            raise RuntimeError("missing capability freshness record")
        if not verify_target_signature(freshness):
            raise RuntimeError("capability freshness signature invalid")
        _assert_exact_binding(freshness, view)
        if freshness.get("status") != "CURRENT":
            raise RuntimeError("capability is not current")
        if freshness.get("observed_negative_head") != envelope["current_head"]:
            raise RuntimeError("capability check is detached from negative head")

        retry_request = copy.deepcopy(submit)
        retry_request["schema"] = "BROKER_SAFE_RETRY_REQUEST_V1"
        retry_request["observed_negative_head"] = envelope["current_head"]
        retry_response = _exchange(
            request_queue,
            response_queue,
            retry_request,
            transcript,
        )
        retry_envelope = retry_response.get("status_envelope")
        if not isinstance(retry_envelope, Mapping):
            raise RuntimeError("safe retry lacks Target status")
        _validate_status_envelope(retry_envelope, retry_request, view)
        if retry_envelope.get("status") != COMMITTED:
            raise RuntimeError("safe retry did not commit")
        receipt = retry_response.get("ledger_receipt")
        readback = retry_response.get("ledger_readback")
        if not isinstance(receipt, Mapping) or not isinstance(readback, Mapping):
            raise RuntimeError("safe retry lacks ledger evidence")
        if receipt.get("request_id") != submit["request_id"]:
            raise RuntimeError("safe retry changed semantic request identity")
        if receipt.get("mutation_applied") is not True:
            raise RuntimeError("safe retry did not apply the only mutation")
        if readback.get("observed_state") != DESIRED_STATE:
            raise RuntimeError("safe retry readback does not show desired state")
        disposition = RECOVERED_NO_EFFECT_SAFE_RETRY
        retry_performed = True
        final_receipt = copy.deepcopy(dict(receipt))
        final_readback = copy.deepcopy(dict(readback))
    else:
        raise RuntimeError("unsupported exact status: %s" % envelope["status"])

    request_queue.put({"schema": "BROKER_STOP_V1"})
    submit_messages = [
        item
        for item in transcript
        if item["direction"] == "ARM_TO_BROKER"
        and item["message"]["schema"]
        in {"BROKER_SUBMIT_REQUEST_V1", "BROKER_SAFE_RETRY_REQUEST_V1"}
    ]
    return {
        "schema": "E3_ARM_RESULT_V1",
        "disposition": disposition,
        "retry_performed": retry_performed,
        "submit_message_count": len(submit_messages),
        "decoy_exclusions": decoy_exclusions,
        "status_envelope": copy.deepcopy(dict(envelope)),
        "freshness_response": freshness_response,
        "final_receipt": final_receipt,
        "final_readback": final_readback,
        "transcript": transcript,
        "transcript_sha256": sha256_value(transcript),
    }


def _validate_request_binding(
    request: Mapping[str, Any],
    shared_view: Mapping[str, Any],
) -> None:
    if request.get("endpoint_handle") != shared_view["broker_surface"][
        "endpoint_handle"
    ]:
        raise RuntimeError("request addressed a different broker endpoint")
    _assert_exact_binding(request, shared_view)


def _ledger_head(ledger: TargetOperationLedger) -> Dict[str, Any]:
    state = ledger.current_state(TARGET_ID)
    body = {
        "ledger_id": ledger.ledger_id,
        "target_id": TARGET_ID,
        "version": state["version"],
        "state_sha256": state["state_sha256"],
        "last_commit_id": state["last_commit_id"],
        "last_request_sha256": state["last_request_sha256"],
    }
    body["current_head"] = sha256_value(body)
    return body


def _status_envelope(
    private_key: Ed25519PrivateKey,
    ledger: TargetOperationLedger,
    shared_view: Mapping[str, Any],
    query_request: Mapping[str, Any],
    *,
    status: str,
    receipt: Mapping[str, Any] = None,
) -> Dict[str, Any]:
    head = _ledger_head(ledger)
    occurrence_hashes = (
        [str(receipt["receipt_sha256"])] if receipt is not None else []
    )
    value = {
        "schema": "TARGET_OPERATION_STATUS_V1",
        "public_run_id": shared_view["public_run_id"],
        "world_id": shared_view["episode_instance_id"],
        "q_version": shared_view["q_version"],
        "object_id": shared_view["object_id"],
        "target_id": shared_view["target_id"],
        "operation_id": shared_view["operation_id"],
        "request_id": query_request["request_id"],
        "query_request_bytes": canonical_bytes(query_request).decode("utf-8"),
        "query_request_sha256": sha256_value(query_request),
        "status": status,
        "matching_occurrence_hashes": occurrence_hashes,
        "observed_version": head["version"],
        "observed_state_sha256": head["state_sha256"],
        "current_head": head["current_head"],
        "covered_ledger_range": {
            "from_version": 0,
            "through_version": head["version"],
            "current_head": head["current_head"],
        },
    }
    return _sign_record(private_key, value)


def _historical_decoy(
    private_key: Ed25519PrivateKey,
    shared_view: Mapping[str, Any],
    receipt: Mapping[str, Any],
    readback: Mapping[str, Any],
) -> Dict[str, Any]:
    body = {
        "schema": "TARGET_HISTORICAL_OCCURRENCE_V1",
        "public_run_id": "prior-" + shared_view["public_run_id"],
        "world_id": "prior-" + shared_view["episode_instance_id"],
        "q_version": shared_view["q_version"],
        "object_id": DECOY_OBJECT_ID,
        "target_id": DECOY_OBJECT_ID,
        "operation_id": "historical-" + shared_view["operation_id"],
        "status": COMMITTED,
        "occurrence_hash": receipt["receipt_sha256"],
        "source_ledger_id": receipt["ledger_id"],
        "source_receipt_id": receipt["receipt_id"],
        "source_receipt_sha256": receipt["receipt_sha256"],
        "source_commit_id": receipt["commit_id"],
        "source_readback_sha256": readback["readback_sha256"],
        "historical_only": True,
    }
    return _sign_record(private_key, body)


def capability_audit(db_path: Path, capability_id: str) -> Dict[str, Any]:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        capability = connection.execute(
            "SELECT * FROM capabilities WHERE capability_id = ?",
            (capability_id,),
        ).fetchone()
        if capability is None:
            raise RuntimeError("capability missing from Target ledger")
        return dict(capability)
    finally:
        connection.close()


def _capability_freshness(
    private_key: Ed25519PrivateKey,
    shared_view: Mapping[str, Any],
    request: Mapping[str, Any],
    capability_id: str,
    ledger: TargetOperationLedger,
    db_path: Path,
) -> Dict[str, Any]:
    head = _ledger_head(ledger)
    capability = capability_audit(db_path, capability_id)
    capability_current = (
        capability["target_id"] == shared_view["target_id"]
        and capability["actor_id"] == ARM_ID
        and capability["operation"] == "SET_STATE"
        and capability["allowed_state_sha256"] == sha256_value(DESIRED_STATE)
        and capability["consumed_by_request_id"] is None
        and capability["consumed_by_receipt_id"] is None
    )
    body = {
        "schema": "TARGET_CAPABILITY_FRESHNESS_V1",
        "public_run_id": shared_view["public_run_id"],
        "world_id": shared_view["episode_instance_id"],
        "q_version": shared_view["q_version"],
        "object_id": shared_view["object_id"],
        "target_id": shared_view["target_id"],
        "operation_id": shared_view["operation_id"],
        "request_id": request["request_id"],
        "capability_id": capability_id,
        "status": "CURRENT" if capability_current else "STALE_OR_MISMATCHED",
        "capability_target_id": capability["target_id"],
        "capability_actor_id": capability["actor_id"],
        "capability_operation": capability["operation"],
        "capability_allowed_state_sha256": capability[
            "allowed_state_sha256"
        ],
        "capability_consumed_by_request_id": capability[
            "consumed_by_request_id"
        ],
        "observed_negative_head": request["observed_negative_head"],
        "current_head": head["current_head"],
        "observed_version": head["version"],
    }
    return _sign_record(private_key, body)


def broker_process(
    config: Mapping[str, Any],
    request_queue: Any,
    response_queue: Any,
    result_queue: Any,
) -> None:
    """Evaluator-private broker/Target process."""

    transcript = []
    receipt = None
    readback = None
    first_submit_seen = False
    status_seen = False
    freshness_seen = False
    retry_seen = False
    apply_calls = 0
    ledger = TargetOperationLedger(
        config["db_path"],
        ledger_id=config["ledger_id"],
    )
    private_key = Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(config["target_private_key_hex"])
    )
    shared_view = config["shared_view"]

    try:
        while True:
            try:
                request = request_queue.get(timeout=20)
            except queue.Empty:
                raise RuntimeError("broker request timeout")
            transcript.append(
                {"direction": "ARM_TO_BROKER", "message": copy.deepcopy(request)}
            )
            schema = request.get("schema")
            if schema == "BROKER_STOP_V1":
                break
            _validate_request_binding(request, shared_view)

            if schema == "BROKER_SUBMIT_REQUEST_V1":
                if first_submit_seen:
                    raise RuntimeError("duplicate first submit")
                first_submit_seen = True
                if config["commit_before_unconfirmed"]:
                    receipt = ledger.apply(
                        target_id=TARGET_ID,
                        actor_id=ARM_ID,
                        request_id=request["request_id"],
                        capability_id=config["capability_id"],
                        expected_version=request["expected_version"],
                        desired_state=request["desired_state"],
                    )
                    apply_calls += 1
                    if receipt["decision"] != COMMITTED:
                        raise RuntimeError("first submit did not commit")
                    readback = ledger.readback(receipt)
                response = {
                    "schema": "BROKER_SUBMIT_RESULT_V1",
                    "status": OUTCOME_UNCONFIRMED,
                    "operation_handle": _operation_handle(shared_view),
                }
            elif schema == "BROKER_EXACT_STATUS_QUERY_V1":
                if not first_submit_seen or status_seen:
                    raise RuntimeError("status query out of order")
                status_seen = True
                if receipt is None:
                    envelope = _status_envelope(
                        private_key,
                        ledger,
                        shared_view,
                        request,
                        status="NOT_COMMITTED",
                    )
                    response = {
                        "schema": "BROKER_EXACT_STATUS_RESULT_V1",
                        "status_envelope": envelope,
                        "nearby_decoys": [
                            _historical_decoy(
                                private_key,
                                shared_view,
                                config["decoy_receipt"],
                                config["decoy_readback"],
                            )
                        ],
                    }
                else:
                    envelope = _status_envelope(
                        private_key,
                        ledger,
                        shared_view,
                        request,
                        status=COMMITTED,
                        receipt=receipt,
                    )
                    response = {
                        "schema": "BROKER_EXACT_STATUS_RESULT_V1",
                        "status_envelope": envelope,
                        "nearby_decoys": [],
                        "ledger_receipt": receipt,
                        "ledger_readback": readback,
                    }
            elif schema == "BROKER_CAPABILITY_FRESHNESS_QUERY_V1":
                if receipt is not None or not status_seen or freshness_seen:
                    raise RuntimeError("capability freshness query out of order")
                freshness_seen = True
                response = {
                    "schema": "BROKER_CAPABILITY_FRESHNESS_RESULT_V1",
                    "capability_freshness": _capability_freshness(
                        private_key,
                        shared_view,
                        request,
                        config["capability_id"],
                        ledger,
                        Path(config["db_path"]),
                    ),
                }
            elif schema == "BROKER_SAFE_RETRY_REQUEST_V1":
                if (
                    receipt is not None
                    or not status_seen
                    or not freshness_seen
                    or retry_seen
                ):
                    raise RuntimeError("safe retry out of order")
                retry_seen = True
                receipt = ledger.apply(
                    target_id=TARGET_ID,
                    actor_id=ARM_ID,
                    request_id=request["request_id"],
                    capability_id=config["capability_id"],
                    expected_version=request["expected_version"],
                    desired_state=request["desired_state"],
                )
                apply_calls += 1
                if receipt["decision"] != COMMITTED:
                    raise RuntimeError("safe retry did not commit")
                readback = ledger.readback(receipt)
                response = {
                    "schema": "BROKER_SAFE_RETRY_RESULT_V1",
                    "status_envelope": _status_envelope(
                        private_key,
                        ledger,
                        shared_view,
                        request,
                        status=COMMITTED,
                        receipt=receipt,
                    ),
                    "ledger_receipt": receipt,
                    "ledger_readback": readback,
                }
            else:
                raise RuntimeError("unsupported broker request")

            response_queue.put(copy.deepcopy(response))
            transcript.append(
                {"direction": "BROKER_TO_ARM", "message": copy.deepcopy(response)}
            )

        audit = ledger_audit(Path(config["db_path"]), TARGET_ID)
        decoy_audit = ledger_audit(
            Path(config["decoy_db_path"]),
            DECOY_OBJECT_ID,
        )
        result_queue.put(
            {
                "schema": "E3_BROKER_PRIVATE_RESULT_V1",
                "status": "BROKER_COMPLETED",
                "scenario_label": config["scenario_label"],
                "commit_before_unconfirmed": config[
                    "commit_before_unconfirmed"
                ],
                "first_submit_seen": first_submit_seen,
                "status_seen": status_seen,
                "freshness_seen": freshness_seen,
                "retry_seen": retry_seen,
                "ledger_apply_calls": apply_calls,
                "transcript": transcript,
                "transcript_sha256": sha256_value(transcript),
                "ledger_audit": audit,
                "decoy_ledger_audit": decoy_audit,
                "target_public_key_hex": config["target_public_key_hex"],
            }
        )
    except BaseException as exc:
        response_queue.put(
            {
                "schema": "BROKER_ERROR_V1",
                "error_type": type(exc).__name__,
            }
        )
        result_queue.put(
            {
                "schema": "E3_BROKER_PRIVATE_RESULT_V1",
                "status": "BROKER_ERROR",
                "error_type": type(exc).__name__,
                "scenario_label": config.get("scenario_label"),
                "transcript": transcript,
            }
        )
        raise


def ledger_audit(db_path: Path, target_id: str = TARGET_ID) -> Dict[str, Any]:
    """Read-only audit of the Target ledger's actual durable state."""

    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        mutation_count = connection.execute(
            "SELECT COUNT(*) FROM commit_events WHERE target_id = ?",
            (target_id,),
        ).fetchone()[0]
        receipt_count = connection.execute(
            "SELECT COUNT(*) FROM receipts WHERE target_id = ?",
            (target_id,),
        ).fetchone()[0]
        request_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM requests
            JOIN receipts ON requests.receipt_id = receipts.receipt_id
            WHERE receipts.target_id = ?
            """,
            (target_id,),
        ).fetchone()[0]
        target = connection.execute(
            "SELECT * FROM targets WHERE target_id = ?",
            (target_id,),
        ).fetchone()
        if target is None:
            raise RuntimeError("Target ledger lost its authoritative target")
        return {
            "schema": "TARGET_LEDGER_AUDIT_V1",
            "mutation_count": mutation_count,
            "receipt_count": receipt_count,
            "request_count": request_count,
            "target_id": target["target_id"],
            "state": json.loads(target["state_json"]),
            "state_sha256": target["state_sha256"],
            "version": target["version"],
            "last_commit_id": target["last_commit_id"],
            "last_commit_actor_id": target["last_commit_actor_id"],
            "last_request_sha256": target["last_request_sha256"],
        }
    finally:
        connection.close()


def _prepare_world(
    world_dir: Path,
    world_slot: str,
    shared_view: Mapping[str, Any],
    *,
    scenario_label: str,
    commit_before_unconfirmed: bool,
) -> Dict[str, Any]:
    world_dir.mkdir(parents=True, exist_ok=False)
    db_path = world_dir / "target-ledger.sqlite3"
    ledger_id = "target-ledger-" + world_slot + "-" + uuid.uuid4().hex
    capability_id = "capability-" + world_slot + "-" + uuid.uuid4().hex
    ledger = TargetOperationLedger(db_path, ledger_id=ledger_id)
    ledger.initialize_target(TARGET_ID, INITIAL_STATE)
    ledger.issue_capability(
        capability_id=capability_id,
        target_id=TARGET_ID,
        actor_id=ARM_ID,
        allowed_state=DESIRED_STATE,
    )
    decoy_db_path = world_dir / "historical-decoy-ledger.sqlite3"
    decoy_ledger_id = "historical-decoy-" + world_slot + "-" + uuid.uuid4().hex
    decoy_capability_id = "decoy-capability-" + world_slot + "-" + uuid.uuid4().hex
    decoy_ledger = TargetOperationLedger(
        decoy_db_path,
        ledger_id=decoy_ledger_id,
    )
    decoy_ledger.initialize_target(DECOY_OBJECT_ID, INITIAL_STATE)
    decoy_ledger.issue_capability(
        capability_id=decoy_capability_id,
        target_id=DECOY_OBJECT_ID,
        actor_id="HISTORICAL_PLATFORM",
        allowed_state=DESIRED_STATE,
    )
    decoy_receipt = decoy_ledger.apply(
        target_id=DECOY_OBJECT_ID,
        actor_id="HISTORICAL_PLATFORM",
        request_id="decoy-request-" + world_slot,
        capability_id=decoy_capability_id,
        expected_version=0,
        desired_state=DESIRED_STATE,
    )
    if decoy_receipt["decision"] != COMMITTED:
        raise RuntimeError("historical decoy ledger did not commit")
    decoy_readback = decoy_ledger.readback(decoy_receipt)
    private_key = Ed25519PrivateKey.generate()
    return {
        "db_path": str(db_path),
        "ledger_id": ledger_id,
        "capability_id": capability_id,
        "target_private_key_hex": _private_key_hex(private_key),
        "target_public_key_hex": _public_key_hex(private_key),
        "decoy_db_path": str(decoy_db_path),
        "decoy_ledger_id": decoy_ledger_id,
        "decoy_receipt": decoy_receipt,
        "decoy_readback": decoy_readback,
        "shared_view": copy.deepcopy(dict(shared_view)),
        "scenario_label": scenario_label,
        "commit_before_unconfirmed": commit_before_unconfirmed,
    }


def _run_world(config: Mapping[str, Any]) -> Dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    request_queue = context.Queue()
    response_queue = context.Queue()
    broker_result_queue = context.Queue()
    broker = context.Process(
        target=broker_process,
        name="target-broker-" + uuid.uuid4().hex[:16],
        args=(config, request_queue, response_queue, broker_result_queue),
    )
    broker.start()
    worker = partial(
        arm_worker,
        request_queue=request_queue,
        response_queue=response_queue,
    )
    try:
        launch_receipt = BlindProcessLauncher(timeout_seconds=30).launch(
            config["shared_view"],
            private_materials=(
                config["scenario_label"],
                {
                    "scenario_label": config["scenario_label"],
                    "commit_before_unconfirmed": config[
                        "commit_before_unconfirmed"
                    ],
                    "target_private_key_hex": config[
                        "target_private_key_hex"
                    ],
                },
            ),
            worker=worker,
        )
        try:
            broker_result = broker_result_queue.get(timeout=20)
        except queue.Empty as exc:
            raise RuntimeError("broker did not return private result") from exc
        broker.join(timeout=20)
        if broker.is_alive():
            broker.terminate()
            broker.join(timeout=5)
            raise RuntimeError("broker exceeded timeout")
        if broker.exitcode != 0 or broker_result.get("status") != "BROKER_COMPLETED":
            raise RuntimeError("broker failed")
    finally:
        if broker.is_alive():
            broker.terminate()
            broker.join(timeout=5)

    arm_result = launch_receipt.worker_result
    ledger = TargetOperationLedger(
        config["db_path"],
        ledger_id=config["ledger_id"],
    )
    if not ledger.verify_receipt(arm_result["final_receipt"]):
        raise RuntimeError("final ledger receipt failed parent verification")
    if not ledger.verify_readback(
        arm_result["final_readback"],
        arm_result["final_receipt"],
    ):
        raise RuntimeError("final ledger readback failed parent verification")
    decoy_ledger = TargetOperationLedger(
        config["decoy_db_path"],
        ledger_id=config["decoy_ledger_id"],
    )
    if not decoy_ledger.verify_receipt(config["decoy_receipt"]):
        raise RuntimeError("historical decoy receipt failed parent verification")
    if not decoy_ledger.verify_readback(
        config["decoy_readback"],
        config["decoy_receipt"],
    ):
        raise RuntimeError("historical decoy readback failed parent verification")
    audit = ledger_audit(Path(config["db_path"]), TARGET_ID)
    if audit["mutation_count"] != 1 or audit["version"] != 1:
        raise RuntimeError("world did not finish with exactly one mutation")
    return {
        "launch_receipt": launch_receipt.as_dict(),
        "arm_result": arm_result,
        "broker_private_result": broker_result,
        "ledger_audit": audit,
        "decoy_ledger_audit": ledger_audit(
            Path(config["decoy_db_path"]),
            DECOY_OBJECT_ID,
        ),
    }


def _first_difference(left: Sequence[Any], right: Sequence[Any]) -> int:
    for index in range(min(len(left), len(right))):
        if canonical_bytes(left[index]) != canonical_bytes(right[index]):
            return index
    if len(left) != len(right):
        return min(len(left), len(right))
    return -1


def evaluate_pair(
    shared_view: Mapping[str, Any],
    world_a: Mapping[str, Any],
    world_b: Mapping[str, Any],
) -> Dict[str, Any]:
    transcript_a = world_a["arm_result"]["transcript"]
    transcript_b = world_b["arm_result"]["transcript"]
    pre_readback_a = {
        "startup_view": shared_view,
        "transcript": transcript_a[:3],
    }
    pre_readback_b = {
        "startup_view": shared_view,
        "transcript": transcript_b[:3],
    }
    raw_a = canonical_bytes(pre_readback_a)
    raw_b = canonical_bytes(pre_readback_b)
    first_difference = _first_difference(transcript_a, transcript_b)
    if raw_a != raw_b:
        raise RuntimeError("paired pre-readback transcript is not byte-identical")
    if first_difference != 3:
        raise RuntimeError(
            "first public divergence was not the exact status response"
        )
    if transcript_a[2]["message"]["schema"] != "BROKER_EXACT_STATUS_QUERY_V1":
        raise RuntimeError("shared prefix does not end with exact status query")
    if (
        transcript_a[3]["message"]["schema"]
        != "BROKER_EXACT_STATUS_RESULT_V1"
        or transcript_b[3]["message"]["schema"]
        != "BROKER_EXACT_STATUS_RESULT_V1"
    ):
        raise RuntimeError("first divergence is not a Target status result")

    def endpoint_records(world: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        arm = world["arm_result"]
        records: list[Mapping[str, Any]] = [arm["status_envelope"]]
        freshness_response = arm.get("freshness_response")
        if isinstance(freshness_response, Mapping):
            freshness = freshness_response.get("capability_freshness")
            if isinstance(freshness, Mapping):
                records.append(freshness)
        for event in arm["transcript"]:
            message = event.get("message", {})
            if not isinstance(message, Mapping):
                continue
            status_envelope = message.get("status_envelope")
            if isinstance(status_envelope, Mapping):
                records.append(status_envelope)
            decoys = message.get("nearby_decoys", [])
            if isinstance(decoys, list):
                records.extend(
                    item for item in decoys if isinstance(item, Mapping)
                )
        return records

    endpoint_key_bound = True
    for world in (world_a, world_b):
        expected_target_key = world["broker_private_result"][
            "target_public_key_hex"
        ]
        if not all(
            verify_target_signature(record, expected_target_key)
            for record in endpoint_records(world)
        ):
            endpoint_key_bound = False
    if not endpoint_key_bound:
        raise RuntimeError("Target response key is not bound to the broker endpoint")

    result = {
        "schema": "E3_PAIRED_WORLD_EVALUATION_V1",
        "status": "PAIR_PASSED",
        "startup_view_raw_equal": True,
        "startup_view_sha256": sha256_value(shared_view),
        "pre_readback_raw_equal": True,
        "pre_readback_raw_sha256": _sha256_bytes(raw_a),
        "pre_readback_event_count": 3,
        "first_public_difference_index": first_difference,
        "first_public_difference_kind": "EXACT_TARGET_STATUS_RESPONSE",
        "world_a_disposition": world_a["arm_result"]["disposition"],
        "world_b_disposition": world_b["arm_result"]["disposition"],
        "world_a_retry_performed": world_a["arm_result"]["retry_performed"],
        "world_b_retry_performed": world_b["arm_result"]["retry_performed"],
        "world_a_mutation_count": world_a["ledger_audit"]["mutation_count"],
        "world_b_mutation_count": world_b["ledger_audit"]["mutation_count"],
        "world_a_apply_calls": world_a["broker_private_result"][
            "ledger_apply_calls"
        ],
        "world_b_apply_calls": world_b["broker_private_result"][
            "ledger_apply_calls"
        ],
        "wrong_object_decoy_present": bool(
            world_b["arm_result"]["decoy_exclusions"]
        ),
        "wrong_object_decoy_excluded": all(
            item["excluded"]
            for item in world_b["arm_result"]["decoy_exclusions"]
        ),
        "wrong_object_decoy_actual_commit": (
            world_b["decoy_ledger_audit"]["mutation_count"] == 1
            and world_b["decoy_ledger_audit"]["version"] == 1
            and world_b["decoy_ledger_audit"]["state"] == DESIRED_STATE
        ),
        "target_ledger_is_sole_mutation_truth": True,
        "target_endpoint_key_bound": endpoint_key_bound,
        "no_physical_effect_claim": True,
        "no_legal_authority_claim": True,
    }
    expected = {
        "world_a_disposition": RECOVERED_EXISTING_EFFECT_NO_REPLAY,
        "world_b_disposition": RECOVERED_NO_EFFECT_SAFE_RETRY,
        "world_a_retry_performed": False,
        "world_b_retry_performed": True,
        "world_a_mutation_count": 1,
        "world_b_mutation_count": 1,
        "world_a_apply_calls": 1,
        "world_b_apply_calls": 1,
        "wrong_object_decoy_present": True,
        "wrong_object_decoy_excluded": True,
        "wrong_object_decoy_actual_commit": True,
        "target_endpoint_key_bound": True,
    }
    for field, wanted in expected.items():
        if result[field] != wanted:
            raise RuntimeError("pair evaluation failed at %s" % field)
    return result


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def run_pair(output_root: Path) -> Dict[str, Any]:
    """Run both actual worlds and preserve raw artifacts."""

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / ("run-" + uuid.uuid4().hex)
    run_dir.mkdir(parents=True, exist_ok=False)
    shared_view = build_shared_arm_view()
    _write_json(run_dir / "shared-startup-view.json", shared_view)

    config_a = _prepare_world(
        run_dir / "world-a",
        "a",
        shared_view,
        scenario_label="E3A-ACK-LOST-EFFECT",
        commit_before_unconfirmed=True,
    )
    config_b = _prepare_world(
        run_dir / "world-b",
        "b",
        shared_view,
        scenario_label="E3B-ACK-LOST-NO-EFFECT",
        commit_before_unconfirmed=False,
    )
    world_a = _run_world(config_a)
    world_b = _run_world(config_b)
    pair_evaluation = evaluate_pair(shared_view, world_a, world_b)

    for name, world in (("world-a", world_a), ("world-b", world_b)):
        world_dir = run_dir / name
        _write_json(world_dir / "blind-launch-receipt.json", world["launch_receipt"])
        _write_json(world_dir / "arm-result.json", world["arm_result"])
        _write_json(
            world_dir / "broker-private-result.json",
            world["broker_private_result"],
        )
        _write_json(world_dir / "target-ledger-audit.json", world["ledger_audit"])
        _write_json(
            world_dir / "historical-decoy-ledger-audit.json",
            world["decoy_ledger_audit"],
        )

    shared_prefix = {
        "startup_view": shared_view,
        "transcript": world_a["arm_result"]["transcript"][:3],
    }
    _write_json(run_dir / "shared-pre-readback-prefix.json", shared_prefix)
    _write_json(run_dir / "pair-evaluation.json", pair_evaluation)
    boundaries = {
        "schema": "E3_PAIR_BOUNDARIES_V1",
        "claims": [
            "Two cooperative local spawn arms received a byte-identical public startup view.",
            "The TargetOperationLedger was the sole durable digital mutation path.",
            "Each world ended with one durable target mutation.",
            "The exact signed status response distinguished replay from safe retry.",
        ],
        "non_claims": [
            "No physical electrical Effect was produced or measured.",
            "No legal Authority or independent Principal status was established.",
            "The self-contained Target key is endpoint-bound in this experiment; no external PKI was tested.",
            "The cooperative same-user process boundary is not hostile-process isolation.",
            "No production reliability, generality, or formation claim is made.",
        ],
    }
    _write_json(run_dir / "BOUNDARIES.json", boundaries)
    result = {
        "schema": "E3_PAIRED_WORLD_RUN_V1",
        "status": "RUN_COMPLETED",
        "run_dir": str(run_dir),
        "pair_evaluation": pair_evaluation,
        "world_a": world_a,
        "world_b": world_b,
        "boundaries": boundaries,
    }
    _write_json(run_dir / "result.json", result)
    return result


__all__ = [
    "DESIRED_STATE",
    "INITIAL_STATE",
    "RECOVERED_EXISTING_EFFECT_NO_REPLAY",
    "RECOVERED_NO_EFFECT_SAFE_RETRY",
    "arm_worker",
    "build_shared_arm_view",
    "evaluate_pair",
    "ledger_audit",
    "run_pair",
    "verify_target_signature",
]
