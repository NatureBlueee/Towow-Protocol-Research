"""Actual multi-process E4 common-world runtime primitives."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import multiprocessing
import os
import pathlib
import queue
import sys
import uuid
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


OWNER_IDS = (
    "RESOURCE_PRIMARY",
    "RESOURCE_ALTERNATIVE",
    "O_V",
    "O_S",
    "O_Q",
    "O_P",
)
PUBLIC_STARTUP_FIELDS = {
    "schema",
    "run_binding",
    "arm_binding_token",
    "q_version",
    "object_id",
    "operation_id",
    "deadline_minute",
    "broker_surface",
    "target_surface",
}
FORBIDDEN_STARTUP_TERMS = (
    "E4-REVOKE",
    "E4_REMOVE",
    "REMOVE_ALTERNATIVE",
    "alternative",
    "primary",
    "scenario",
    "expected",
    "topology",
    "candidate",
)

_WAVE015_LEDGER_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "wave-015-runner-foundation"
    / "target_ledger.py"
)
_LEDGER_SPEC = importlib.util.spec_from_file_location(
    "wave015_target_ledger_for_e4", _WAVE015_LEDGER_PATH
)
if _LEDGER_SPEC is None or _LEDGER_SPEC.loader is None:
    raise RuntimeError("Wave 015 TargetOperationLedger is unavailable")
_LEDGER_MODULE = importlib.util.module_from_spec(_LEDGER_SPEC)
_LEDGER_SPEC.loader.exec_module(_LEDGER_MODULE)
SQLiteTargetOperationLedger = _LEDGER_MODULE.TargetOperationLedger
LEDGER_COMMITTED = _LEDGER_MODULE.COMMITTED


def exact_c7_state() -> Dict[str, Any]:
    effect_start_minute = 10
    samples = [
        {
            "offset_minute": offset,
            "minute": effect_start_minute + offset,
            "power_kw": 3.0,
            "safety_ok": True,
            "noise_ok": True,
            "other_circuits_energized": [],
        }
        for offset in range(46)
    ]
    return {
        "energized": True,
        "power_kw": 3.0,
        "effect_start_minute": effect_start_minute,
        "effect_end_minute": effect_start_minute + 45,
        "required_duration_minutes": 45,
        "deadline_minute": 90,
        "samples": samples,
    }


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def sign_mapping(
    private_key: Ed25519PrivateKey, value: Mapping[str, Any]
) -> Dict[str, Any]:
    result = dict(value)
    result["signature_hex"] = private_key.sign(canonical_bytes(value)).hex()
    return result


def verify_signed(value: Mapping[str, Any], expected_public_key_hex: str) -> bool:
    signature_hex = value.get("signature_hex")
    if not isinstance(signature_hex, str):
        return False
    unsigned = dict(value)
    unsigned.pop("signature_hex", None)
    try:
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(expected_public_key_hex)
        ).verify(bytes.fromhex(signature_hex), canonical_bytes(unsigned))
    except (ValueError, InvalidSignature):
        return False
    return True


def make_endpoint(ctx: multiprocessing.context.BaseContext) -> Dict[str, Any]:
    return {
        "request": ctx.Queue(),
        "response": ctx.Queue(),
        "control": ctx.Queue(),
        "result": ctx.Queue(),
    }


def rpc(
    endpoint: Mapping[str, Any],
    action: str,
    *,
    arguments: Optional[Mapping[str, Any]] = None,
    timeout: float = 15,
) -> Dict[str, Any]:
    request = {
        "request_id": uuid.uuid4().hex,
        "action": action,
        "arguments": dict(arguments or {}),
    }
    endpoint["request"].put(request)
    response = endpoint["response"].get(timeout=timeout)
    if response.get("request_id") != request["request_id"]:
        raise RuntimeError("RPC response/request mismatch")
    return response


def validate_public_startup(startup: Mapping[str, Any]) -> Dict[str, Any]:
    if set(startup) != PUBLIC_STARTUP_FIELDS:
        unknown = set(startup) - PUBLIC_STARTUP_FIELDS
        missing = PUBLIC_STARTUP_FIELDS - set(startup)
        raise ValueError(
            "invalid public startup keys unknown=%s missing=%s"
            % (sorted(unknown), sorted(missing))
        )
    raw = canonical_bytes(startup).decode("utf-8").lower()
    for term in FORBIDDEN_STARTUP_TERMS:
        if term.lower() in raw:
            raise ValueError("private E4 material in public startup")
    if startup.get("schema") != "COMMON_ARM_PUBLIC_STARTUP_V1":
        raise ValueError("public startup schema mismatch")
    for surface in ("broker_surface", "target_surface"):
        candidate = startup[surface]
        if set(candidate) != {"endpoint_handle", "capabilities", "version"}:
            raise ValueError("invalid public surface")
        if not isinstance(candidate["endpoint_handle"], str) or len(
            candidate["endpoint_handle"]
        ) != 32:
            raise ValueError("surface handle is not opaque")
    return copy.deepcopy(dict(startup))


def _identity(
    private_key: Ed25519PrivateKey,
    service_id: str,
    principal_id: str,
    state_source_id: str,
) -> Dict[str, Any]:
    executable = pathlib.Path(__file__).resolve()
    return sign_mapping(
        private_key,
        {
            "schema": "E4_PROCESS_IDENTITY_V1",
            "service_id": service_id,
            "principal_id": principal_id,
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex(private_key),
            "state_source_id": state_source_id,
            "start_method": multiprocessing.get_start_method(),
            "executable_sha256": hashlib.sha256(
                executable.read_bytes()
            ).hexdigest(),
        },
    )


def _append_owner_receipt(
    *,
    private_key: Ed25519PrivateKey,
    log: list,
    state: Dict[str, Any],
    owner_id: str,
    principal_id: str,
    run_binding: str,
    object_id: str,
    operation_id: str,
    request_id: str,
    kind: str,
    payload: Mapping[str, Any],
    mutate_epoch: bool = False,
) -> Dict[str, Any]:
    before = state["head"]
    if mutate_epoch:
        state["epoch"] += 1
    base = {
        "schema": "E4_OWNER_NATIVE_RECEIPT_V1",
        "kind": kind,
        "owner_instance_id": owner_id,
        "principal_id": principal_id,
        "owner_public_key_hex": public_key_hex(private_key),
        "run_binding": run_binding,
        "object_id": object_id,
        "operation_id": operation_id,
        "request_id": request_id,
        "state_epoch": state["epoch"],
        "state_head_before": before,
        "append_index": len(log),
        "payload": dict(payload),
    }
    state["head"] = sha256_value(base)
    base["state_head_after"] = state["head"]
    receipt = sign_mapping(private_key, base)
    log.append(receipt)
    return receipt


def owner_worker(
    config: Mapping[str, Any],
    endpoint: Mapping[str, Any],
    ready_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    owner_id = config["owner_id"]
    principal_id = config["principal_id"]
    state = {
        "epoch": 1,
        "head": sha256_value(
            {
                "owner_id": owner_id,
                "principal_id": principal_id,
                "nonce": uuid.uuid4().hex,
            }
        ),
        "offered": False,
        "granted": False,
        "committed": False,
        "reserved": False,
        "revoked": False,
    }
    identity = _identity(
        private_key,
        owner_id,
        principal_id,
        "%s-%s" % (owner_id, uuid.uuid4().hex),
    )
    ready_queue.put({"service_id": owner_id, "identity": identity})
    log: list = []
    while True:
        try:
            control = endpoint["control"].get_nowait()
        except queue.Empty:
            control = None
        if control == "FREEZE":
            endpoint["result"].put(
                {
                    "identity": identity,
                    "entries": log,
                    "terminal_state": copy.deepcopy(state),
                }
            )
            return
        try:
            request = endpoint["request"].get(timeout=0.05)
        except queue.Empty:
            continue
        action = request["action"]
        args = request.get("arguments", {})
        kind = None
        payload: Dict[str, Any] = {}
        mutate_epoch = False

        if action == "STATUS":
            kind = "OWNER_CURRENT_STATUS"
            payload = {
                "observed_state_head": state["head"],
                "observed_epoch": state["epoch"],
                "current": not state["revoked"],
                "revoked": state["revoked"],
                "offered": state["offered"],
                "granted": state["granted"],
                "committed": state["committed"],
                "reserved": state["reserved"],
                "latest_native_kind": (
                    log[-1]["kind"] if log else "GENESIS"
                ),
            }
        elif owner_id in {"RESOURCE_PRIMARY", "RESOURCE_ALTERNATIVE"}:
            if action == "OFFER" and not state["revoked"]:
                state["offered"] = True
                kind = "RESOURCE_OFFER"
                payload = {
                    "resource_kind": "MOBILE_3KW_GENERATOR",
                    "power_kw": 3.0,
                    "purpose": "EXACT_C7_WINDOW",
                }
            elif action == "GRANT" and state["offered"] and not state["revoked"]:
                state["granted"] = True
                kind = "CURRENT_PURPOSE_GRANT"
                payload = {"offer_sha256": args["offer_sha256"], "current": True}
            elif (
                action == "COMMITMENT"
                and state["granted"]
                and not state["revoked"]
            ):
                state["committed"] = True
                kind = "CURRENT_COMMITMENT"
                payload = {
                    "grant_sha256": args["grant_sha256"],
                    "current": True,
                }
            elif (
                action == "RESERVE"
                and state["committed"]
                and not state["revoked"]
            ):
                state["reserved"] = True
                kind = "CURRENT_RESERVATION"
                payload = {
                    "commitment_sha256": args["commitment_sha256"],
                    "current": True,
                    "reserved_until_minute": 90,
                }
            elif (
                action == "PRE_EXECUTION_CHECK"
                and owner_id == "RESOURCE_PRIMARY"
                and state["reserved"]
                and not state["revoked"]
            ):
                state["revoked"] = True
                mutate_epoch = True
                kind = "OWNER_NATIVE_REVOKE"
                payload = {
                    "reservation_sha256": args["reservation_sha256"],
                    "current": True,
                    "reason": "RESOURCE_WITHDRAWN_BEFORE_EXECUTION",
                }
        elif owner_id == "O_V":
            if action == "REAPPROVE":
                kind = "VENUE_EXACT_REAPPROVAL"
                payload = {
                    "reservation_sha256": args["reservation_sha256"],
                    "resource_handle": args["resource_handle"],
                    "current": True,
                }
            elif action == "ACCEPT":
                kind = "VENUE_ACCEPTANCE"
                payload = {
                    "readback_sha256": args["readback_sha256"],
                    "resource_handle": args["resource_handle"],
                }
        elif owner_id == "O_S" and action == "REAPPROVE":
            kind = "SAFETY_EXACT_REAPPROVAL"
            payload = {
                "reservation_sha256": args["reservation_sha256"],
                "resource_handle": args["resource_handle"],
                "current": True,
            }
        elif owner_id == "O_Q" and action == "ACCEPT":
            kind = "OWNER_ACCEPTANCE"
            payload = {
                "readback_sha256": args["readback_sha256"],
                "resource_handle": args["resource_handle"],
            }
        elif owner_id == "O_P":
            if action == "CANCEL_PRIMARY":
                kind = "PRIMARY_CANCEL_COMPENSATION"
                payload = {
                    "primary_reservation_sha256": args[
                        "primary_reservation_sha256"
                    ],
                    "revoke_sha256": args["revoke_sha256"],
                    "compensated": True,
                }
            elif action == "BIND_ALTERNATIVE":
                kind = "ALTERNATIVE_OBLIGATION_BINDING"
                payload = {
                    "alternative_reservation_sha256": args[
                        "alternative_reservation_sha256"
                    ],
                    "resource_handle": args["resource_handle"],
                    "current": True,
                }
            elif action == "FINALITY":
                kind = "ALTERNATIVE_BOUND_FINALITY"
                payload = {
                    "acceptance_sha256": list(args["acceptance_sha256"]),
                    "alternative_binding_sha256": args[
                        "alternative_binding_sha256"
                    ],
                    "resource_handle": args["resource_handle"],
                }

        if kind is None:
            response = {
                "request_id": request["request_id"],
                "status": "REJECTED",
                "reason": "INVALID_OWNER_TRANSITION",
            }
        else:
            receipt = _append_owner_receipt(
                private_key=private_key,
                log=log,
                state=state,
                owner_id=owner_id,
                principal_id=principal_id,
                run_binding=config["run_binding"],
                object_id=config["object_id"],
                operation_id=config["operation_id"],
                request_id=request["request_id"],
                kind=kind,
                payload=payload,
                mutate_epoch=mutate_epoch,
            )
            response = {
                "request_id": request["request_id"],
                "status": "OK",
                "receipt": receipt,
            }
        endpoint["response"].put(response)


def broker_worker(
    config: Mapping[str, Any],
    owner_endpoints: Mapping[str, Mapping[str, Any]],
    endpoint: Mapping[str, Any],
    ready_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    identity = _identity(
        private_key,
        "BROKER",
        "BROKER_PRINCIPAL",
        "BROKER-%s" % uuid.uuid4().hex,
    )
    handles = {
        "RESOURCE_PRIMARY": uuid.uuid4().hex,
        "RESOURCE_ALTERNATIVE": uuid.uuid4().hex,
    }
    handle_to_owner = {value: key for key, value in handles.items()}
    ready_queue.put(
        {
            "service_id": "BROKER",
            "identity": identity,
            "private_handle_map": handles,
        }
    )
    primary_revoked = False
    revoke_receipt_sha256 = None
    query_index = 0
    public_log: list = []
    private_route_log: list = []

    def broker_receipt(kind: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        receipt = sign_mapping(
            private_key,
            {
                "schema": "E4_BROKER_RECEIPT_V1",
                "kind": kind,
                "broker_public_key_hex": public_key_hex(private_key),
                "run_binding": config["run_binding"],
                "object_id": config["object_id"],
                "operation_id": config["operation_id"],
                "append_index": len(public_log),
                "payload": dict(payload),
            },
        )
        public_log.append(receipt)
        return receipt

    while True:
        try:
            control = endpoint["control"].get_nowait()
        except queue.Empty:
            control = None
        if control == "FREEZE":
            endpoint["result"].put(
                {
                    "identity": identity,
                    "entries": public_log,
                    "private_route_log": private_route_log,
                    "private_handle_map": handles,
                    "primary_revoked": primary_revoked,
                    "alternative_enabled": config["alternative_enabled"],
                }
            )
            return
        try:
            request = endpoint["request"].get(timeout=0.05)
        except queue.Empty:
            continue
        action = request["action"]
        args = request.get("arguments", {})
        if action == "DISCOVER":
            query_index += 1
            if not primary_revoked:
                selected = "RESOURCE_PRIMARY"
                kind = "INITIAL_DISCOVERY"
            elif config["alternative_enabled"]:
                selected = "RESOURCE_ALTERNATIVE"
                kind = "DISCOVERY_AFTER_REVOKE"
            else:
                selected = None
                kind = "DISCOVERY_EXHAUSTED_AFTER_REVOKE"
            receipt = broker_receipt(
                kind,
                {
                    "query_index": query_index,
                    "resource_kind": args["resource_kind"],
                    "owner_handle": handles[selected] if selected else None,
                    "after_revoke_receipt_sha256": (
                        revoke_receipt_sha256 if primary_revoked else None
                    ),
                    "status": "FOUND" if selected else "NOT_FOUND",
                },
            )
            private_route_log.append(
                {
                    "query_index": query_index,
                    "selected_owner_instance_id": selected,
                    "receipt_sha256": sha256_value(receipt),
                }
            )
            response = {
                "request_id": request["request_id"],
                "status": "FOUND" if selected else "NOT_FOUND",
                "owner_handle": handles[selected] if selected else None,
                "discovery_receipt": receipt,
            }
        elif action == "OWNER_ACTION":
            handle = args.get("owner_handle")
            owner_id = handle_to_owner.get(handle)
            if owner_id is None:
                response = {
                    "request_id": request["request_id"],
                    "status": "REJECTED",
                    "reason": "UNKNOWN_OWNER_HANDLE",
                }
            else:
                routed = rpc(
                    owner_endpoints[owner_id],
                    args["owner_action"],
                    arguments=args.get("owner_arguments", {}),
                )
                if (
                    routed.get("status") == "OK"
                    and routed["receipt"]["kind"] == "OWNER_NATIVE_REVOKE"
                ):
                    primary_revoked = True
                    revoke_receipt_sha256 = sha256_value(routed["receipt"])
                response = {
                    "request_id": request["request_id"],
                    "status": routed["status"],
                    "receipt": routed.get("receipt"),
                    "reason": routed.get("reason"),
                }
                private_route_log.append(
                    {
                        "owner_handle": handle,
                        "owner_instance_id": owner_id,
                        "owner_action": args["owner_action"],
                        "owner_receipt_sha256": (
                            sha256_value(routed["receipt"])
                            if routed.get("receipt")
                            else None
                        ),
                    }
                )
        elif action == "BYPASS_REDISCOVERY":
            if primary_revoked and config["alternative_enabled"]:
                response = {
                    "request_id": request["request_id"],
                    "status": "FOUND_WITHOUT_DISCOVERY",
                    "owner_handle": handles["RESOURCE_ALTERNATIVE"],
                }
            else:
                response = {
                    "request_id": request["request_id"],
                    "status": "NOT_FOUND",
                }
        elif action == "ROLE_ACTION":
            role = args["role"]
            routed = rpc(
                owner_endpoints[role],
                args["owner_action"],
                arguments=args.get("owner_arguments", {}),
            )
            response = {
                "request_id": request["request_id"],
                "status": routed["status"],
                "receipt": routed.get("receipt"),
                "reason": routed.get("reason"),
            }
        else:
            response = {
                "request_id": request["request_id"],
                "status": "REJECTED",
                "reason": "UNKNOWN_BROKER_ACTION",
            }
        endpoint["response"].put(response)


def _verify_owner_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_owner_id: str,
    owner_registry: Mapping[str, Mapping[str, Any]],
    expected_kind: str,
    run_binding: str,
    object_id: str,
    operation_id: str,
) -> bool:
    identity = owner_registry[expected_owner_id]
    return (
        receipt.get("kind") == expected_kind
        and receipt.get("owner_instance_id") == expected_owner_id
        and receipt.get("principal_id") == identity["principal_id"]
        and receipt.get("owner_public_key_hex") == identity["public_key_hex"]
        and receipt.get("run_binding") == run_binding
        and receipt.get("object_id") == object_id
        and receipt.get("operation_id") == operation_id
        and verify_signed(receipt, identity["public_key_hex"])
    )


def target_worker(
    config: Mapping[str, Any],
    owner_endpoints: Mapping[str, Mapping[str, Any]],
    endpoint: Mapping[str, Any],
    ready_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    identity = _identity(
        private_key,
        "TARGET",
        "TARGET_TRUTH_OWNER",
        "TARGET-%s" % uuid.uuid4().hex,
    )
    ready_queue.put({"service_id": "TARGET", "identity": identity})
    exact_state = exact_c7_state()
    ledger = SQLiteTargetOperationLedger(
        config["database_path"],
        ledger_id=config["ledger_id"],
    )
    ledger.initialize_target(
        config["object_id"],
        {
            "energized": False,
            "power_kw": 0.0,
            "effect_start_minute": None,
            "effect_end_minute": None,
            "required_duration_minutes": 45,
            "deadline_minute": 90,
            "samples": [],
        },
    )
    ledger.issue_capability(
        capability_id=config["capability_id"],
        target_id=config["object_id"],
        actor_id="A4",
        allowed_state=exact_state,
    )
    occurrence: Optional[Dict[str, Any]] = None
    readback: Optional[Dict[str, Any]] = None
    log: list = []
    fresh_status_queries: list = []
    ledger_receipts: list = []
    ledger_readbacks: list = []
    owner_registry = config["owner_registry"]

    def reject(request_id: str, reason: str, request_sha256: str) -> Dict[str, Any]:
        record = sign_mapping(
            private_key,
            {
                "schema": "E4_TARGET_ATTEMPT_V1",
                "kind": "TARGET_COMMIT_REJECTED",
                "request_id": request_id,
                "request_sha256": request_sha256,
                "reason": reason,
                "version": ledger.current_state(config["object_id"])["version"],
                "append_index": len(log),
            },
        )
        log.append(record)
        return {
            "request_id": request_id,
            "status": "REJECTED",
            "reason": reason,
            "target_receipt": record,
        }

    while True:
        try:
            control = endpoint["control"].get_nowait()
        except queue.Empty:
            control = None
        if control == "FREEZE":
            endpoint["result"].put(
                {
                    "identity": identity,
                    "entries": log,
                    "occurrences": [occurrence] if occurrence is not None else [],
                    "readbacks": [readback] if readback is not None else [],
                    "ledger_receipts": ledger_receipts,
                    "ledger_readbacks": ledger_readbacks,
                    "fresh_status_queries": fresh_status_queries,
                    "current_state": ledger.current_state(config["object_id"]),
                    "ledger_id": ledger.ledger_id,
                    "capability_id": config["capability_id"],
                    "exact_state": exact_state,
                }
            )
            return
        try:
            request = endpoint["request"].get(timeout=0.05)
        except queue.Empty:
            continue
        if request["action"] != "COMMIT":
            endpoint["response"].put(
                {
                    "request_id": request["request_id"],
                    "status": "REJECTED",
                    "reason": "UNKNOWN_TARGET_ACTION",
                }
            )
            continue
        args = request["arguments"]
        request_sha = sha256_value(args)
        if occurrence is not None:
            try:
                replay_receipt = ledger.apply(
                    target_id=config["object_id"],
                    actor_id="A4",
                    request_id=args["semantic_request_id"],
                    capability_id=config["capability_id"],
                    expected_version=0,
                    desired_state=exact_state,
                )
            except (KeyError, TypeError, ValueError):
                endpoint["response"].put(
                    reject(
                        request["request_id"],
                        "DUPLICATE_REQUEST_NOT_IDENTICAL",
                        request_sha,
                    )
                )
                continue
            if not ledger_receipts or replay_receipt != ledger_receipts[0]:
                endpoint["response"].put(
                    reject(
                        request["request_id"],
                        "DUPLICATE_REQUEST_NOT_IDENTICAL",
                        request_sha,
                    )
                )
                continue
            duplicate = sign_mapping(
                private_key,
                {
                    "schema": "E4_TARGET_ATTEMPT_V1",
                    "kind": "ALREADY_COMMITTED",
                    "request_id": request["request_id"],
                    "request_sha256": request_sha,
                    "commit_id": occurrence["commit_id"],
                    "version": 1,
                    "append_index": len(log),
                },
            )
            log.append(duplicate)
            endpoint["response"].put(
                {
                    "request_id": request["request_id"],
                    "status": "ALREADY_COMMITTED",
                    "occurrence": occurrence,
                    "readback": readback,
                    "target_receipt": duplicate,
                }
            )
            continue

        reason = None
        submitted_chain = args.get("alternative_chain", {})
        if any(
            isinstance(receipt, Mapping)
            and receipt.get("owner_instance_id") == "RESOURCE_PRIMARY"
            for receipt in submitted_chain.values()
        ):
            reason = "STALE_PRIMARY_RECEIPTS"
        discovery = args.get("rediscovery_receipt")
        broker_key = config["broker_public_key_hex"]
        if reason is None and (
            not isinstance(discovery, Mapping)
            or not verify_signed(discovery, broker_key)
        ):
            reason = "NO_VALID_REDISCOVERY"
        elif reason is None and discovery.get("kind") != "DISCOVERY_AFTER_REVOKE":
            reason = "NO_VALID_REDISCOVERY"
        elif reason is None and (
            discovery.get("payload", {}).get("owner_handle")
            != config["alternative_handle"]
        ):
            reason = "WRONG_DISCOVERED_OWNER"
        elif reason is None and not config["alternative_enabled"]:
            reason = "ALTERNATIVE_REMOVED"

        chain = submitted_chain
        expected_chain = (
            ("offer", "RESOURCE_OFFER"),
            ("grant", "CURRENT_PURPOSE_GRANT"),
            ("commitment", "CURRENT_COMMITMENT"),
            ("reservation", "CURRENT_RESERVATION"),
        )
        if reason is None:
            for key, kind in expected_chain:
                receipt = chain.get(key)
                if not isinstance(receipt, Mapping) or not _verify_owner_receipt(
                    receipt,
                    expected_owner_id="RESOURCE_ALTERNATIVE",
                    owner_registry=owner_registry,
                    expected_kind=kind,
                    run_binding=config["run_binding"],
                    object_id=config["object_id"],
                    operation_id=config["operation_id"],
                ):
                    reason = "WRONG_OWNER_OR_KEY"
                    break
        if reason is None:
            offer = chain["offer"]
            grant = chain["grant"]
            commitment = chain["commitment"]
            reservation = chain["reservation"]
            if (
                grant["payload"].get("offer_sha256") != sha256_value(offer)
                or commitment["payload"].get("grant_sha256")
                != sha256_value(grant)
                or reservation["payload"].get("commitment_sha256")
                != sha256_value(commitment)
            ):
                reason = "BROKEN_ALTERNATIVE_CHAIN"

        for key, owner_id, kind in (
            ("venue_reapproval", "O_V", "VENUE_EXACT_REAPPROVAL"),
            ("safety_reapproval", "O_S", "SAFETY_EXACT_REAPPROVAL"),
            ("primary_compensation", "O_P", "PRIMARY_CANCEL_COMPENSATION"),
            (
                "alternative_binding",
                "O_P",
                "ALTERNATIVE_OBLIGATION_BINDING",
            ),
        ):
            if reason is not None:
                break
            receipt = args.get(key)
            if not isinstance(receipt, Mapping) or not _verify_owner_receipt(
                receipt,
                expected_owner_id=owner_id,
                owner_registry=owner_registry,
                expected_kind=kind,
                run_binding=config["run_binding"],
                object_id=config["object_id"],
                operation_id=config["operation_id"],
            ):
                reason = "MISSING_OR_INVALID_%s" % key.upper()

        if reason is None:
            primary_reservation = args.get("primary_reservation")
            primary_revoke = args.get("primary_revoke")
            if not isinstance(
                primary_reservation, Mapping
            ) or not _verify_owner_receipt(
                primary_reservation,
                expected_owner_id="RESOURCE_PRIMARY",
                owner_registry=owner_registry,
                expected_kind="CURRENT_RESERVATION",
                run_binding=config["run_binding"],
                object_id=config["object_id"],
                operation_id=config["operation_id"],
            ):
                reason = "MISSING_PRIMARY_RESERVATION"
            elif not isinstance(primary_revoke, Mapping) or not _verify_owner_receipt(
                primary_revoke,
                expected_owner_id="RESOURCE_PRIMARY",
                owner_registry=owner_registry,
                expected_kind="OWNER_NATIVE_REVOKE",
                run_binding=config["run_binding"],
                object_id=config["object_id"],
                operation_id=config["operation_id"],
            ):
                reason = "MISSING_CURRENT_PRIMARY_REVOKE"
            elif primary_revoke["payload"].get(
                "reservation_sha256"
            ) != sha256_value(primary_reservation):
                reason = "PRIMARY_REVOKE_DETACHED"

        if reason is None:
            alternative_reservation_sha = sha256_value(chain["reservation"])
            if (
                args["venue_reapproval"]["payload"].get(
                    "reservation_sha256"
                )
                != alternative_reservation_sha
                or args["safety_reapproval"]["payload"].get(
                    "reservation_sha256"
                )
                != alternative_reservation_sha
                or args["venue_reapproval"]["payload"].get("resource_handle")
                != config["alternative_handle"]
                or args["safety_reapproval"]["payload"].get("resource_handle")
                != config["alternative_handle"]
            ):
                reason = "REAPPROVAL_NOT_ALTERNATIVE_EXACT"
            elif (
                args["primary_compensation"]["payload"].get(
                    "primary_reservation_sha256"
                )
                != sha256_value(args["primary_reservation"])
                or args["primary_compensation"]["payload"].get(
                    "revoke_sha256"
                )
                != sha256_value(args["primary_revoke"])
            ):
                reason = "PRIMARY_COMPENSATION_DETACHED"
            elif (
                args["alternative_binding"]["payload"].get(
                    "alternative_reservation_sha256"
                )
                != alternative_reservation_sha
                or args["alternative_binding"]["payload"].get(
                    "resource_handle"
                )
                != config["alternative_handle"]
            ):
                reason = "ALTERNATIVE_BINDING_DETACHED"

        reopen = args.get("reopen_evidence", {})
        expected_affected = {
            "primary_offer",
            "primary_grant",
            "primary_commitment",
            "primary_reservation",
            "venue_approval",
            "safety_approval",
            "primary_obligation",
        }
        if reason is None and (
            not isinstance(reopen, Mapping)
            or reopen.get("kind") != "LOCAL_DESCENDANT_REOPEN"
            or not verify_signed(
                reopen, str(reopen.get("arm_public_key_hex", ""))
            )
            or set(reopen.get("payload", {}).get("invalidated", []))
            != expected_affected
            or set(reopen.get("payload", {}).get("preserved", []))
            != {"Q", "object_id", "deadline"}
            or reopen.get("payload", {}).get("revoke_sha256")
            != sha256_value(args["primary_revoke"])
            or reopen.get("payload", {}).get("revoke_state_head_after")
            != args["primary_revoke"].get("state_head_after")
        ):
            reason = "UNBOUNDED_OR_INCOMPLETE_REOPEN"

        if reason is None and (
            args["alternative_binding"].get("state_head_before")
            != args["primary_compensation"].get("state_head_after")
        ):
            reason = "OBLIGATION_CHAIN_NOT_CONTIGUOUS"

        current_requirements = (
            (
                "RESOURCE_ALTERNATIVE",
                chain["reservation"]["state_head_after"],
                {
                    "current": True,
                    "granted": True,
                    "committed": True,
                    "reserved": True,
                    "revoked": False,
                },
            ),
            (
                "O_V",
                args["venue_reapproval"]["state_head_after"],
                {"current": True, "revoked": False},
            ),
            (
                "O_S",
                args["safety_reapproval"]["state_head_after"],
                {"current": True, "revoked": False},
            ),
            (
                "RESOURCE_PRIMARY",
                args["primary_revoke"]["state_head_after"],
                {"current": False, "revoked": True},
            ),
            (
                "O_P",
                args["alternative_binding"]["state_head_after"],
                {"current": True, "revoked": False},
            ),
        )
        current_status_by_owner: Dict[str, Dict[str, Any]] = {}
        if reason is None:
            for owner_id, expected_head, expected_flags in current_requirements:
                status_response = rpc(owner_endpoints[owner_id], "STATUS")
                status = status_response.get("receipt")
                if (
                    status_response.get("status") != "OK"
                    or not isinstance(status, Mapping)
                    or not _verify_owner_receipt(
                        status,
                        expected_owner_id=owner_id,
                        owner_registry=owner_registry,
                        expected_kind="OWNER_CURRENT_STATUS",
                        run_binding=config["run_binding"],
                        object_id=config["object_id"],
                        operation_id=config["operation_id"],
                    )
                    or status.get("payload", {}).get("observed_state_head")
                    != expected_head
                    or any(
                        status.get("payload", {}).get(key) != value
                        for key, value in expected_flags.items()
                    )
                ):
                    reason = "FRESH_CURRENT_STATUS_FAILED_%s" % owner_id
                    break
                current_status_by_owner[owner_id] = dict(status)
                fresh_status_queries.append(dict(status))

        if reason is not None:
            endpoint["response"].put(
                reject(request["request_id"], reason, request_sha)
            )
            continue

        try:
            ledger_receipt = ledger.apply(
                target_id=config["object_id"],
                actor_id="A4",
                request_id=args["semantic_request_id"],
                capability_id=config["capability_id"],
                expected_version=0,
                desired_state=exact_state,
            )
        except (KeyError, TypeError, ValueError):
            endpoint["response"].put(
                reject(
                    request["request_id"],
                    "INVALID_LEDGER_MUTATION_REQUEST",
                    request_sha,
                )
            )
            continue
        if (
            ledger_receipt.get("decision") != LEDGER_COMMITTED
            or ledger_receipt.get("mutation_applied") is not True
            or ledger_receipt.get("post_state") != exact_state
        ):
            endpoint["response"].put(
                reject(
                    request["request_id"],
                    "DURABLE_LEDGER_DID_NOT_COMMIT_EXACT_STATE",
                    request_sha,
                )
            )
            continue
        ledger_readback = ledger.readback(ledger_receipt)
        if (
            not ledger.verify_receipt(ledger_receipt)
            or not ledger.verify_readback(ledger_readback, ledger_receipt)
        ):
            endpoint["response"].put(
                reject(
                    request["request_id"],
                    "DURABLE_LEDGER_READBACK_INVALID",
                    request_sha,
                )
            )
            continue
        ledger_receipts.append(ledger_receipt)
        ledger_readbacks.append(ledger_readback)
        status_hashes = {
            owner_id: sha256_value(status)
            for owner_id, status in current_status_by_owner.items()
        }
        occurrence = sign_mapping(
            private_key,
            {
                "schema": "E4_TARGET_OCCURRENCE_V1",
                "kind": "EXACT_C7_OCCURRENCE",
                "commit_id": ledger_receipt["commit_id"],
                "request_id": request["request_id"],
                "request_sha256": request_sha,
                "semantic_request_id": args["semantic_request_id"],
                "run_binding": config["run_binding"],
                "object_id": config["object_id"],
                "operation_id": config["operation_id"],
                "pre_version": ledger_receipt["pre_version"],
                "post_version": ledger_receipt["post_version"],
                "pre_state": ledger_receipt["pre_state"],
                "post_state": ledger_receipt["post_state"],
                "exact_state_sha256": sha256_value(exact_state),
                "ledger_receipt_sha256": sha256_value(ledger_receipt),
                "ledger_readback_sha256": sha256_value(ledger_readback),
                "authority_owner_instance_id": "RESOURCE_ALTERNATIVE",
                "authority_principal_id": owner_registry[
                    "RESOURCE_ALTERNATIVE"
                ]["principal_id"],
                "authority_reservation_sha256": sha256_value(
                    chain["reservation"]
                ),
                "rediscovery_receipt_sha256": sha256_value(discovery),
                "reopen_evidence_sha256": sha256_value(reopen),
                "fresh_status_sha256": status_hashes,
                "occurrence_index": 0,
            },
        )
        readback = sign_mapping(
            private_key,
            {
                "schema": "E4_TARGET_READBACK_V1",
                "kind": "EXACT_READBACK",
                "commit_id": occurrence["commit_id"],
                "occurrence_sha256": sha256_value(occurrence),
                "run_binding": config["run_binding"],
                "object_id": config["object_id"],
                "operation_id": config["operation_id"],
                "version": ledger_readback["observed_version"],
                "state": ledger_readback["observed_state"],
                "ledger_receipt_sha256": sha256_value(ledger_receipt),
                "ledger_readback_sha256": sha256_value(ledger_readback),
                "exact_state_sha256": sha256_value(exact_state),
            },
        )
        log.extend((occurrence, readback))
        endpoint["response"].put(
            {
                "request_id": request["request_id"],
                "status": "COMMITTED",
                "occurrence": occurrence,
                "readback": readback,
            }
        )


def _arm_sign(
    private_key: Ed25519PrivateKey,
    kind: str,
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    return sign_mapping(
        private_key,
        {
            "schema": "COMMON_ARM_EVIDENCE_V1",
            "kind": kind,
            "arm_public_key_hex": public_key_hex(private_key),
            "payload": dict(payload),
        },
    )


def arm_worker(
    startup: Mapping[str, Any],
    broker_endpoint: Mapping[str, Any],
    target_endpoint: Mapping[str, Any],
    result_queue: Any,
    strategy: str,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    startup = validate_public_startup(startup)
    transcript: list = [
        {
            "kind": "ARM_START",
            "argv": list(sys.argv),
            "cwd": os.getcwd(),
            "process_name": multiprocessing.current_process().name,
            "startup": startup,
        }
    ]

    def broker(action: str, arguments: Mapping[str, Any]) -> Dict[str, Any]:
        response = rpc(
            broker_endpoint, action, arguments=arguments
        )
        transcript.append(
            {
                "kind": "BROKER_INTERACTION",
                "action": action,
                "request_arguments": dict(arguments),
                "response": response,
            }
        )
        return response

    def owner_action(
        handle: str, action: str, arguments: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        return broker(
            "OWNER_ACTION",
            {
                "owner_handle": handle,
                "owner_action": action,
                "owner_arguments": dict(arguments or {}),
            },
        )

    initial = broker(
        "DISCOVER", {"resource_kind": "MOBILE_3KW_GENERATOR"}
    )
    primary_handle = initial["owner_handle"]
    primary_offer = owner_action(primary_handle, "OFFER")["receipt"]
    primary_grant = owner_action(
        primary_handle,
        "GRANT",
        {"offer_sha256": sha256_value(primary_offer)},
    )["receipt"]
    primary_commitment = owner_action(
        primary_handle,
        "COMMITMENT",
        {"grant_sha256": sha256_value(primary_grant)},
    )["receipt"]
    primary_reservation = owner_action(
        primary_handle,
        "RESERVE",
        {"commitment_sha256": sha256_value(primary_commitment)},
    )["receipt"]
    revoke = owner_action(
        primary_handle,
        "PRE_EXECUTION_CHECK",
        {"reservation_sha256": sha256_value(primary_reservation)},
    )["receipt"]

    invalidated = [
        "primary_offer",
        "primary_grant",
        "primary_commitment",
        "primary_reservation",
        "venue_approval",
        "safety_approval",
        "primary_obligation",
    ]
    preserved = ["Q", "object_id", "deadline"]
    if strategy == "UNBOUNDED_REOPEN":
        invalidated.append("Q")
        preserved.remove("Q")
    reopen_evidence = _arm_sign(
        private_key,
        "LOCAL_DESCENDANT_REOPEN",
        {
            "invalidated": invalidated,
            "preserved": preserved,
            "revoke_sha256": sha256_value(revoke),
            "revoke_state_head_after": revoke["state_head_after"],
        },
    )
    transcript.append({"kind": "REOPEN_EVIDENCE", "evidence": reopen_evidence})
    compensation = broker(
        "ROLE_ACTION",
        {
            "role": "O_P",
            "owner_action": "CANCEL_PRIMARY",
            "owner_arguments": {
                "primary_reservation_sha256": sha256_value(
                    primary_reservation
                ),
                "revoke_sha256": sha256_value(revoke),
            },
        },
    )["receipt"]

    if strategy == "STALE_PRIMARY":
        rediscovery = None
        selected_handle = primary_handle
        selected_chain = {
            "offer": primary_offer,
            "grant": primary_grant,
            "commitment": primary_commitment,
            "reservation": primary_reservation,
        }
    elif strategy == "NO_REDISCOVERY":
        bypass = broker("BYPASS_REDISCOVERY", {})
        rediscovery = None
        selected_handle = bypass.get("owner_handle")
        if selected_handle is None:
            result_queue.put(
                {
                    "identity": _identity(
                        private_key,
                        "ARM",
                        "ARM_PRINCIPAL",
                        "ARM-%s" % uuid.uuid4().hex,
                    ),
                    "transcript": transcript,
                    "disposition": "BOUNDED_REFUSAL_NO_ALTERNATIVE",
                    "primary": {
                        "offer": primary_offer,
                        "grant": primary_grant,
                        "commitment": primary_commitment,
                        "reservation": primary_reservation,
                        "revoke": revoke,
                        "compensation": compensation,
                    },
                    "target_response": None,
                }
            )
            return
        selected_chain = {}
    else:
        rediscovery_response = broker(
            "DISCOVER", {"resource_kind": "MOBILE_3KW_GENERATOR"}
        )
        if rediscovery_response["status"] == "NOT_FOUND":
            result_queue.put(
                {
                    "identity": _identity(
                        private_key,
                        "ARM",
                        "ARM_PRINCIPAL",
                        "ARM-%s" % uuid.uuid4().hex,
                    ),
                    "transcript": transcript,
                    "disposition": "BOUNDED_REFUSAL_NO_ALTERNATIVE",
                    "primary": {
                        "offer": primary_offer,
                        "grant": primary_grant,
                        "commitment": primary_commitment,
                        "reservation": primary_reservation,
                        "revoke": revoke,
                        "compensation": compensation,
                    },
                    "rediscovery": rediscovery_response,
                    "reopen_evidence": reopen_evidence,
                    "target_response": None,
                }
            )
            return
        rediscovery = rediscovery_response["discovery_receipt"]
        selected_handle = rediscovery_response["owner_handle"]
        selected_chain = {}

    if strategy != "STALE_PRIMARY":
        alt_offer = owner_action(selected_handle, "OFFER")["receipt"]
        alt_grant = owner_action(
            selected_handle,
            "GRANT",
            {"offer_sha256": sha256_value(alt_offer)},
        )["receipt"]
        alt_commitment = owner_action(
            selected_handle,
            "COMMITMENT",
            {"grant_sha256": sha256_value(alt_grant)},
        )["receipt"]
        alt_reservation = owner_action(
            selected_handle,
            "RESERVE",
            {"commitment_sha256": sha256_value(alt_commitment)},
        )["receipt"]
        selected_chain = {
            "offer": alt_offer,
            "grant": alt_grant,
            "commitment": alt_commitment,
            "reservation": alt_reservation,
        }

    venue = broker(
        "ROLE_ACTION",
        {
            "role": "O_V",
            "owner_action": "REAPPROVE",
            "owner_arguments": {
                "reservation_sha256": sha256_value(
                    selected_chain["reservation"]
                ),
                "resource_handle": selected_handle,
            },
        },
    )["receipt"]
    safety = broker(
        "ROLE_ACTION",
        {
            "role": "O_S",
            "owner_action": "REAPPROVE",
            "owner_arguments": {
                "reservation_sha256": sha256_value(
                    selected_chain["reservation"]
                ),
                "resource_handle": selected_handle,
            },
        },
    )["receipt"]
    alternative_binding = broker(
        "ROLE_ACTION",
        {
            "role": "O_P",
            "owner_action": "BIND_ALTERNATIVE",
            "owner_arguments": {
                "alternative_reservation_sha256": sha256_value(
                    selected_chain["reservation"]
                ),
                "resource_handle": selected_handle,
            },
        },
    )["receipt"]

    if strategy == "WRONG_OWNER_KEY":
        selected_chain = copy.deepcopy(selected_chain)
        selected_chain["grant"]["owner_public_key_hex"] = "0" * 64

    target_arguments = {
        "semantic_request_id": "semantic-" + startup["operation_id"],
        "rediscovery_receipt": rediscovery,
        "primary_reservation": primary_reservation,
        "primary_revoke": revoke,
        "alternative_chain": selected_chain,
        "venue_reapproval": venue,
        "safety_reapproval": safety,
        "primary_compensation": compensation,
        "alternative_binding": alternative_binding,
        "reopen_evidence": reopen_evidence,
    }
    target_response = rpc(
        target_endpoint, "COMMIT", arguments=target_arguments
    )
    transcript.append(
        {
            "kind": "TARGET_INTERACTION",
            "response": target_response,
        }
    )
    duplicate_response = None
    acceptances = []
    finality = None
    if target_response["status"] == "COMMITTED":
        duplicate_response = rpc(
            target_endpoint, "COMMIT", arguments=target_arguments
        )
        transcript.append(
            {
                "kind": "DUPLICATE_TARGET_PROBE",
                "response": duplicate_response,
            }
        )
        readback_sha = sha256_value(target_response["readback"])
        owner_acceptance = broker(
            "ROLE_ACTION",
            {
                "role": "O_Q",
                "owner_action": "ACCEPT",
                "owner_arguments": {
                    "readback_sha256": readback_sha,
                    "resource_handle": selected_handle,
                },
            },
        )["receipt"]
        venue_acceptance = broker(
            "ROLE_ACTION",
            {
                "role": "O_V",
                "owner_action": "ACCEPT",
                "owner_arguments": {
                    "readback_sha256": readback_sha,
                    "resource_handle": selected_handle,
                },
            },
        )["receipt"]
        acceptances = [owner_acceptance, venue_acceptance]
        finality = broker(
            "ROLE_ACTION",
            {
                "role": "O_P",
                "owner_action": "FINALITY",
                "owner_arguments": {
                    "acceptance_sha256": [
                        sha256_value(owner_acceptance),
                        sha256_value(venue_acceptance),
                    ],
                    "alternative_binding_sha256": sha256_value(
                        alternative_binding
                    ),
                    "resource_handle": selected_handle,
                },
            },
        )["receipt"]

    result_queue.put(
        {
            "identity": _identity(
                private_key,
                "ARM",
                "ARM_PRINCIPAL",
                "ARM-%s" % uuid.uuid4().hex,
            ),
            "transcript": transcript,
            "disposition": (
                "RECOVERED_VIA_LEGAL_ALTERNATIVE"
                if target_response["status"] == "COMMITTED"
                else "TARGET_REJECTED"
            ),
            "primary": {
                "offer": primary_offer,
                "grant": primary_grant,
                "commitment": primary_commitment,
                "reservation": primary_reservation,
                "revoke": revoke,
                "compensation": compensation,
            },
            "rediscovery_receipt": rediscovery,
            "selected_resource_handle": selected_handle,
            "selected_chain": selected_chain,
            "reopen_evidence": reopen_evidence,
            "venue_reapproval": venue,
            "safety_reapproval": safety,
            "alternative_binding": alternative_binding,
            "target_response": target_response,
            "duplicate_response": duplicate_response,
            "acceptances": acceptances,
            "finality": finality,
        }
    )
