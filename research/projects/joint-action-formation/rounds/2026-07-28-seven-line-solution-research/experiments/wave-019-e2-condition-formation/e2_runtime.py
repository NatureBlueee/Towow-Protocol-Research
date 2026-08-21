"""Executable local-synthetic E2 condition-formation worlds.

Five owner processes hold independent keys and SQLite state.  The broker only
routes bytes and invokes the mature Target ledger after owner-native formation
and commit-time revalidation.  It never signs owner facts.

This experiment models digital state only.  It does not establish legal
Authority, a physical electrical Effect, or production reliability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import os
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


ARM_ID = "MATURE-WORKFLOW-HITL-FORMATION"
TARGET_ID = "VenueV:CircuitC7"
OBJECT_ID = TARGET_ID
INITIAL_TARGET_STATE = {"occurrences": []}
RESPONSE_ROLES = ("O_Q", "O_V", "O_R", "O_S")
ALL_OWNER_ROLES = ("O_Q", "O_V", "O_R", "O_S", "O_P")
ROLE_FACTS = {
    "O_Q": ("PURPOSE_TOKEN",),
    "O_V": ("C7_SHORT_DELEGATION",),
    "O_R": ("RESOURCE_COMMITMENT", "RESOURCE_RESERVATION"),
    "O_S": ("SAFETY_APPROVAL",),
    "O_P": ("PAYMENT_FINALITY",),
}
ROLE_PRINCIPALS = {
    "O_Q": "PRINCIPAL_REQUESTER_Q",
    "O_V": "PRINCIPAL_VENUE_V",
    "O_R": "PRINCIPAL_RESOURCE_R",
    "O_S": "PRINCIPAL_SAFETY_S",
    "O_P": "PRINCIPAL_SETTLEMENT_P",
}

BASELINE = "BASELINE_COUNTER_SUCCESS"
REMOVE = "REMOVE_FORMATION_OPERATOR"
REFUSE = "OWNER_REFUSE"


def _without(value: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    excluded = set(keys)
    return {key: item for key, item in value.items() if key not in excluded}


def _public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def _sign_owner(
    private_key: Ed25519PrivateKey,
    value: MutableMapping[str, Any],
) -> Dict[str, Any]:
    signed = copy.deepcopy(dict(value))
    signed["owner_public_key_hex"] = _public_key_hex(private_key)
    signed["signature_hex"] = private_key.sign(
        canonical_bytes(_without(signed, "signature_hex"))
    ).hex()
    return signed


def verify_owner_signature(
    value: Mapping[str, Any],
    expected_public_key_hex: str | None = None,
) -> bool:
    try:
        if (
            expected_public_key_hex is not None
            and value.get("owner_public_key_hex") != expected_public_key_hex
        ):
            return False
        key = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(str(value["owner_public_key_hex"]))
        )
        key.verify(
            bytes.fromhex(str(value["signature_hex"])),
            canonical_bytes(_without(value, "signature_hex")),
        )
        return True
    except Exception:
        return False


def _scope(view: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
        "purpose": "TEMPORARY_C7_3KW_45MIN",
        "required_power_kw": view["required_power_kw"],
        "required_duration_minutes": view["required_duration_minutes"],
        "deadline_minute": view["deadline_minute"],
    }


def _proposal(view: Mapping[str, Any]) -> Dict[str, Any]:
    scope = _scope(view)
    return {
        "schema": "E2_EXACT_FORMATION_PROPOSAL_V1",
        **scope,
        "scope_sha256": sha256_value(scope),
        "requested_expiry_minute": view["deadline_minute"],
        "owner_request_nonces": {
            role: "nonce-" + sha256_value({"view": view, "role": role})[:32]
            for role in RESPONSE_ROLES
        },
        "terms": {
            "relation_duration": "ONE_OPERATION_ONLY",
            "delegation_scope": TARGET_ID,
            "resource": {"power_kw": 3.0, "duration_minutes": 45},
            "safety_profile": "LOCAL_SYNTHETIC_C7_PROFILE_V1",
        },
    }


def _target_desired_state(view: Mapping[str, Any], proposal_hash: str) -> Dict[str, Any]:
    start = 5
    samples = [
        {
            "offset_minute": offset,
            "observed_at_minute": start + offset,
            "target_id": view["target_id"],
            "power_kw": 3.0,
            "safety_ok": True,
            "noise_ok": True,
            "other_circuits_energized": [],
            "source": "LOCAL_SYNTHETIC",
        }
        for offset in range(46)
    ]
    occurrence = {
        "occurrence_id": "occurrence-" + proposal_hash[:32],
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
        "proposal_sha256": proposal_hash,
        "effect_start_minute": start,
        "effect_end_minute": start + 45,
        "duration_minutes": 45,
        "deadline_minute": view["deadline_minute"],
        "required_power_kw": view["required_power_kw"],
        "power_tolerance_percent": view["power_tolerance_percent"],
        "power_min_kw": 2.85,
        "power_max_kw": 3.15,
        "other_circuits_energized": [],
        "samples": samples,
        "synthetic": True,
    }
    return {"occurrences": [occurrence]}


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


def build_shared_views() -> Dict[str, Dict[str, Any]]:
    factory = ArmViewFactory(
        arm_id=ARM_ID,
        broker_capabilities=(
            "ACCEPTANCE",
            "FORMATION_MATERIALIZE",
            "FORMATION_PROPOSE",
            "TARGET_EXECUTE",
        ),
    )
    baseline = factory.build(_public_input())
    remove = copy.deepcopy(baseline)
    remove["broker_surface"]["capabilities"] = [
        item
        for item in remove["broker_surface"]["capabilities"]
        if item not in {"FORMATION_MATERIALIZE", "FORMATION_PROPOSE"}
    ]
    return {
        BASELINE: copy.deepcopy(baseline),
        REFUSE: copy.deepcopy(baseline),
        REMOVE: remove,
    }


def _owner_connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def _owner_initialize(
    db_path: Path,
    *,
    owner_id: str,
    role: str,
    principal_id: str,
    public_key_hex: str,
) -> None:
    with _owner_connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                owner_id TEXT NOT NULL,
                owner_role TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                public_key_hex TEXT NOT NULL
            );
            CREATE TABLE facts(
                fact_kind TEXT PRIMARY KEY,
                scope_sha256 TEXT NOT NULL,
                proposal_sha256 TEXT NOT NULL,
                expiry_minute INTEGER NOT NULL,
                value_json TEXT NOT NULL
            );
            CREATE TABLE events(
                event_index INTEGER PRIMARY KEY AUTOINCREMENT,
                event_kind TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO metadata VALUES(1,?,?,?,?)",
            (owner_id, role, principal_id, public_key_hex),
        )


def _owner_facts(connection: sqlite3.Connection) -> list:
    return [
        {
            "fact_kind": row["fact_kind"],
            "scope_sha256": row["scope_sha256"],
            "proposal_sha256": row["proposal_sha256"],
            "expiry_minute": row["expiry_minute"],
            "value": json.loads(row["value_json"]),
        }
        for row in connection.execute(
            "SELECT * FROM facts ORDER BY fact_kind"
        )
    ]


def _owner_head(
    connection: sqlite3.Connection,
    *,
    owner_id: str,
    role: str,
    principal_id: str,
) -> str:
    return sha256_value(
        {
            "owner_id": owner_id,
            "owner_role": role,
            "principal_id": principal_id,
            "facts": _owner_facts(connection),
        }
    )


def _owner_event(
    connection: sqlite3.Connection,
    kind: str,
    payload: Mapping[str, Any],
) -> None:
    connection.execute(
        "INSERT INTO events(event_kind,payload_sha256) VALUES(?,?)",
        (kind, sha256_value(payload)),
    )


def owner_process(
    config: Mapping[str, Any],
    command_queue: Any,
    response_queue: Any,
) -> None:
    """Independent owner state/key/principal process."""

    role = config["owner_role"]
    principal_id = config["principal_id"]
    owner_id = config["owner_id"]
    private_key = Ed25519PrivateKey.generate()
    public_key_hex = _public_key_hex(private_key)
    db_path = Path(config["db_path"])
    _owner_initialize(
        db_path,
        owner_id=owner_id,
        role=role,
        principal_id=principal_id,
        public_key_hex=public_key_hex,
    )
    connection = _owner_connect(db_path)
    scope = config["scope"]
    frozen_policy = {
        "decision_family": [config["decision"]],
        "budget": {
            "max_power_kw": 3.0,
            "max_duration_minutes": 45,
        },
        "horizon_minute": 90,
        "exogenous_schedule": {
            "response_available": True,
            "materialize_after_response_only": True,
            "resource_window_start_minute": 5,
        },
    }
    policy_head = sha256_value(frozen_policy)
    s0_head = _owner_head(
        connection,
        owner_id=owner_id,
        role=role,
        principal_id=principal_id,
    )
    s0 = _sign_owner(
        private_key,
        {
            "schema": "E2_OWNER_S0_ABSENCE_V1",
            "owner_id": owner_id,
            "owner_role": role,
            "principal_id": principal_id,
            "process_id": os.getpid(),
            "scope": scope,
            "scope_sha256": sha256_value(scope),
            "owner_head": s0_head,
            "frozen_policy": frozen_policy,
            "policy_head": policy_head,
            "status": "ABSENT",
            "absent_fact_kinds": list(ROLE_FACTS[role]),
        },
    )
    response_queue.put(
        {
            "schema": "E2_OWNER_READY_V1",
            "owner_id": owner_id,
            "owner_role": role,
            "principal_id": principal_id,
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex,
            "db_path": str(db_path),
            "s0_absence": s0,
        }
    )
    last_response = None
    try:
        while True:
            command = command_queue.get(timeout=40)
            kind = command["kind"]
            if kind == "STOP":
                response_queue.put(
                    {
                        "schema": "E2_OWNER_AUDIT_V1",
                        "owner_id": owner_id,
                        "owner_role": role,
                        "principal_id": principal_id,
                        "process_id": os.getpid(),
                        "public_key_hex": public_key_hex,
                        "facts": _owner_facts(connection),
                        "event_count": connection.execute(
                            "SELECT COUNT(*) FROM events"
                        ).fetchone()[0],
                        "final_head": _owner_head(
                            connection,
                            owner_id=owner_id,
                            role=role,
                            principal_id=principal_id,
                        ),
                    }
                )
                break
            if kind == "EVALUATE_PROPOSAL":
                proposal = json.loads(command["proposal_bytes"])
                if canonical_bytes(proposal).decode("utf-8") != command[
                    "proposal_bytes"
                ]:
                    raise RuntimeError("proposal bytes are not canonical")
                proposal_hash = hashlib.sha256(
                    command["proposal_bytes"].encode("utf-8")
                ).hexdigest()
                decision = config["decision"]
                counter = None
                if decision == "COUNTER":
                    counter = {
                        "effective_expiry_minute": 85,
                        "resource_window_start_minute": 5,
                        "resource_window_end_minute": 50,
                    }
                head = _owner_head(
                    connection,
                    owner_id=owner_id,
                    role=role,
                    principal_id=principal_id,
                )
                last_response = _sign_owner(
                    private_key,
                    {
                        "schema": "E2_OWNER_PROPOSAL_RESPONSE_V1",
                        "owner_id": owner_id,
                        "owner_role": role,
                        "principal_id": principal_id,
                        "process_id": os.getpid(),
                        "proposal_sha256": proposal_hash,
                        "owner_head": head,
                        "policy_head": policy_head,
                        "scope_sha256": proposal["scope_sha256"],
                        "expiry_minute": proposal["requested_expiry_minute"],
                        "request_nonce": proposal["owner_request_nonces"][role],
                        "decision": decision,
                        "counter": counter,
                    },
                )
                _owner_event(connection, "PROPOSAL_RESPONSE", last_response)
                response_queue.put(last_response)
                continue
            if kind == "MATERIALIZE":
                if last_response is None:
                    raise RuntimeError("materialize before response")
                if last_response["decision"] not in {"APPROVE", "COUNTER"}:
                    raise RuntimeError("refusing owner cannot materialize")
                if command["response_sha256"] != sha256_value(last_response):
                    raise RuntimeError("materialize response hash mismatch")
                if (
                    last_response["decision"] == "COUNTER"
                    and command.get("counter_accepted") is not True
                ):
                    raise RuntimeError("counter not accepted")
                pre_head = _owner_head(
                    connection,
                    owner_id=owner_id,
                    role=role,
                    principal_id=principal_id,
                )
                proposal_hash = last_response["proposal_sha256"]
                expiry = (
                    85
                    if last_response["decision"] == "COUNTER"
                    else last_response["expiry_minute"]
                )
                created = []
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for fact_kind in ROLE_FACTS[role]:
                        if role == "O_P":
                            continue
                        value = {
                            "owner_id": owner_id,
                            "owner_role": role,
                            "principal_id": principal_id,
                            "fact_kind": fact_kind,
                            "scope_sha256": last_response["scope_sha256"],
                            "proposal_sha256": proposal_hash,
                            "expiry_minute": expiry,
                        }
                        connection.execute(
                            "INSERT INTO facts VALUES(?,?,?,?,?)",
                            (
                                fact_kind,
                                last_response["scope_sha256"],
                                proposal_hash,
                                expiry,
                                canonical_bytes(value).decode("utf-8"),
                            ),
                        )
                        created.append(fact_kind)
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                post_head = _owner_head(
                    connection,
                    owner_id=owner_id,
                    role=role,
                    principal_id=principal_id,
                )
                act = _sign_owner(
                    private_key,
                    {
                        "schema": "E2_OWNER_FORMATION_ACT_V1",
                        "owner_id": owner_id,
                        "owner_role": role,
                        "principal_id": principal_id,
                        "process_id": os.getpid(),
                        "proposal_sha256": proposal_hash,
                        "response_sha256": sha256_value(last_response),
                        "scope_sha256": last_response["scope_sha256"],
                        "expiry_minute": expiry,
                        "pre_head": pre_head,
                        "post_head": post_head,
                        "created_fact_kinds": created,
                    },
                )
                _owner_event(connection, "FORMATION_ACT", act)
                response_queue.put(act)
                continue
            if kind == "REVALIDATE":
                facts = _owner_facts(connection)
                expected = set(ROLE_FACTS[role])
                actual = {item["fact_kind"] for item in facts}
                current = expected.issubset(actual) and all(
                    item["proposal_sha256"] == command["proposal_sha256"]
                    and item["scope_sha256"] == command["scope_sha256"]
                    and item["expiry_minute"] >= command["execute_minute"]
                    for item in facts
                    if item["fact_kind"] in expected
                )
                record = _sign_owner(
                    private_key,
                    {
                        "schema": "E2_OWNER_COMMIT_REVALIDATION_V1",
                        "owner_id": owner_id,
                        "owner_role": role,
                        "principal_id": principal_id,
                        "process_id": os.getpid(),
                        "proposal_sha256": command["proposal_sha256"],
                        "scope_sha256": command["scope_sha256"],
                        "execute_minute": command["execute_minute"],
                        "owner_head": _owner_head(
                            connection,
                            owner_id=owner_id,
                            role=role,
                            principal_id=principal_id,
                        ),
                        "required_fact_kinds": sorted(expected),
                        "status": "CURRENT" if current else "STALE_OR_MISSING",
                    },
                )
                _owner_event(connection, "COMMIT_REVALIDATION", record)
                response_queue.put(record)
                continue
            if kind == "ACCEPT":
                if role not in {"O_Q", "O_V"}:
                    raise RuntimeError("owner is not an Acceptance role")
                value = {
                    "readback_sha256": command["readback_sha256"],
                    "receipt_sha256": command["receipt_sha256"],
                    "proposal_sha256": command["proposal_sha256"],
                }
                connection.execute(
                    "INSERT INTO facts VALUES(?,?,?,?,?)",
                    (
                        "ACCEPTANCE",
                        command["scope_sha256"],
                        command["proposal_sha256"],
                        90,
                        canonical_bytes(value).decode("utf-8"),
                    ),
                )
                acceptance = _sign_owner(
                    private_key,
                    {
                        "schema": "E2_OWNER_ACCEPTANCE_V1",
                        "owner_id": owner_id,
                        "owner_role": role,
                        "principal_id": principal_id,
                        "process_id": os.getpid(),
                        "scope_sha256": command["scope_sha256"],
                        "proposal_sha256": command["proposal_sha256"],
                        **value,
                        "owner_head": _owner_head(
                            connection,
                            owner_id=owner_id,
                            role=role,
                            principal_id=principal_id,
                        ),
                        "status": "ACCEPTED",
                    },
                )
                _owner_event(connection, "ACCEPTANCE", acceptance)
                response_queue.put(acceptance)
                continue
            if kind == "FINALITY":
                if role != "O_P":
                    raise RuntimeError("only O_P can finalize")
                value = {
                    "acceptance_sha256": command["acceptance_sha256"],
                    "receipt_sha256": command["receipt_sha256"],
                    "proposal_sha256": command["proposal_sha256"],
                }
                connection.execute(
                    "INSERT INTO facts VALUES(?,?,?,?,?)",
                    (
                        "PAYMENT_FINALITY",
                        command["scope_sha256"],
                        command["proposal_sha256"],
                        90,
                        canonical_bytes(value).decode("utf-8"),
                    ),
                )
                finality = _sign_owner(
                    private_key,
                    {
                        "schema": "E2_OWNER_FINALITY_V1",
                        "owner_id": owner_id,
                        "owner_role": role,
                        "principal_id": principal_id,
                        "process_id": os.getpid(),
                        "scope_sha256": command["scope_sha256"],
                        "proposal_sha256": command["proposal_sha256"],
                        **value,
                        "owner_head": _owner_head(
                            connection,
                            owner_id=owner_id,
                            role=role,
                            principal_id=principal_id,
                        ),
                        "status": "FINAL",
                    },
                )
                _owner_event(connection, "FINALITY", finality)
                response_queue.put(finality)
                continue
            raise RuntimeError("unsupported owner command")
    finally:
        connection.close()


def _arm_exchange(
    request_queue: Any,
    response_queue: Any,
    request: Mapping[str, Any],
    transcript: list,
) -> Dict[str, Any]:
    sent = copy.deepcopy(dict(request))
    transcript.append({"direction": "ARM_TO_BROKER", "message": sent})
    request_queue.put(sent)
    try:
        response = response_queue.get(timeout=25)
    except queue.Empty as exc:
        raise RuntimeError("broker timeout") from exc
    response = copy.deepcopy(dict(response))
    transcript.append({"direction": "BROKER_TO_ARM", "message": response})
    if response.get("schema") == "E2_BROKER_ERROR_V1":
        raise RuntimeError("broker failed closed")
    return response


def arm_worker(
    view: Mapping[str, Any],
    request_queue: Any,
    response_queue: Any,
) -> Dict[str, Any]:
    """Scenario-blind mature workflow/HITL arm."""

    transcript = []
    capabilities = set(view["broker_surface"]["capabilities"])
    if "FORMATION_PROPOSE" not in capabilities:
        return {
            "schema": "E2_ARM_RESULT_V1",
            "disposition": "BOUNDED_UNAVAILABLE_NO_FORMATION_OPERATOR",
            "proposal_sent": False,
            "target_submit_sent": False,
            "transcript": [],
            "transcript_sha256": sha256_value([]),
        }

    proposal = _proposal(view)
    proposal_bytes = canonical_bytes(proposal).decode("utf-8")
    proposal_hash = hashlib.sha256(proposal_bytes.encode("utf-8")).hexdigest()
    response = _arm_exchange(
        request_queue,
        response_queue,
        {
            "schema": "E2_BROKER_PROPOSAL_REQUEST_V1",
            "proposal_bytes": proposal_bytes,
            "proposal_sha256": proposal_hash,
        },
        transcript,
    )
    owner_responses = response["owner_responses"]
    if len(owner_responses) != 4:
        raise RuntimeError("owner response set incomplete")
    decisions = {}
    for item in owner_responses:
        if not verify_owner_signature(item):
            raise RuntimeError("owner response signature invalid")
        if item["proposal_sha256"] != proposal_hash:
            raise RuntimeError("owner response proposal mismatch")
        if item["scope_sha256"] != proposal["scope_sha256"]:
            raise RuntimeError("owner response scope mismatch")
        expected_nonce = proposal["owner_request_nonces"][item["owner_role"]]
        if item["request_nonce"] != expected_nonce:
            raise RuntimeError("owner response nonce mismatch")
        decisions[item["owner_role"]] = item["decision"]

    if "REFUSE" in decisions.values():
        request_queue.put({"schema": "E2_BROKER_STOP_V1"})
        return {
            "schema": "E2_ARM_RESULT_V1",
            "disposition": "BOUNDED_REFUSAL_OWNER_SIGNED",
            "proposal_sent": True,
            "target_submit_sent": False,
            "proposal": proposal,
            "proposal_bytes": proposal_bytes,
            "owner_responses": owner_responses,
            "transcript": transcript,
            "transcript_sha256": sha256_value(transcript),
        }
    if "DEFER" in decisions.values():
        request_queue.put({"schema": "E2_BROKER_STOP_V1"})
        return {
            "schema": "E2_ARM_RESULT_V1",
            "disposition": "BOUNDED_UNKNOWN_OWNER_DEFER",
            "proposal_sent": True,
            "target_submit_sent": False,
            "proposal": proposal,
            "proposal_bytes": proposal_bytes,
            "owner_responses": owner_responses,
            "transcript": transcript,
            "transcript_sha256": sha256_value(transcript),
        }

    materialize = _arm_exchange(
        request_queue,
        response_queue,
        {
            "schema": "E2_BROKER_MATERIALIZE_REQUEST_V1",
            "proposal_sha256": proposal_hash,
            "scope_sha256": proposal["scope_sha256"],
            "accepted_response_sha256": {
                item["owner_role"]: sha256_value(item)
                for item in owner_responses
            },
            "accepted_counter_roles": sorted(
                role for role, decision in decisions.items() if decision == "COUNTER"
            ),
        },
        transcript,
    )
    acts = materialize["owner_acts"]
    if len(acts) != 4:
        raise RuntimeError("formation act set incomplete")
    for act in acts:
        if not verify_owner_signature(act):
            raise RuntimeError("owner act signature invalid")
        if act["proposal_sha256"] != proposal_hash:
            raise RuntimeError("owner act proposal mismatch")

    execute = _arm_exchange(
        request_queue,
        response_queue,
        {
            "schema": "E2_BROKER_TARGET_EXECUTE_REQUEST_V1",
            "proposal_sha256": proposal_hash,
            "scope_sha256": proposal["scope_sha256"],
            "execute_minute": 5,
            "owner_act_sha256": {
                item["owner_role"]: sha256_value(item) for item in acts
            },
        },
        transcript,
    )
    if execute["receipt"]["decision"] != COMMITTED:
        raise RuntimeError("Target did not commit")
    if execute["readback"]["observed_state"] != _target_desired_state(
        view, proposal_hash
    ):
        raise RuntimeError("Target readback mismatch")

    acceptance = _arm_exchange(
        request_queue,
        response_queue,
        {
            "schema": "E2_BROKER_ACCEPTANCE_REQUEST_V1",
            "proposal_sha256": proposal_hash,
            "scope_sha256": proposal["scope_sha256"],
            "receipt_sha256": execute["receipt"]["receipt_sha256"],
            "readback_sha256": execute["readback"]["readback_sha256"],
        },
        transcript,
    )
    for item in acceptance["acceptances"]:
        if not verify_owner_signature(item) or item["status"] != "ACCEPTED":
            raise RuntimeError("Acceptance invalid")
    if (
        not verify_owner_signature(acceptance["finality"])
        or acceptance["finality"]["status"] != "FINAL"
    ):
        raise RuntimeError("finality invalid")
    request_queue.put({"schema": "E2_BROKER_STOP_V1"})
    return {
        "schema": "E2_ARM_RESULT_V1",
        "disposition": "SUCCEEDED_AFTER_FORMATION",
        "proposal_sent": True,
        "target_submit_sent": True,
        "proposal": proposal,
        "proposal_bytes": proposal_bytes,
        "owner_responses": owner_responses,
        "owner_acts": acts,
        "commit_revalidations": execute["commit_revalidations"],
        "receipt": execute["receipt"],
        "readback": execute["readback"],
        "acceptances": acceptance["acceptances"],
        "finality": acceptance["finality"],
        "transcript": transcript,
        "transcript_sha256": sha256_value(transcript),
    }


def broker_process(
    config: Mapping[str, Any],
    owner_commands: Mapping[str, Any],
    owner_responses: Mapping[str, Any],
    arm_requests: Any,
    arm_responses: Any,
    result_queue: Any,
) -> None:
    """Unsigned router plus Target commit-time gate."""

    transcript = []
    stored_responses = {}
    stored_acts = {}
    ledger = TargetOperationLedger(
        config["target_db_path"],
        ledger_id=config["target_ledger_id"],
    )
    view = config["view"]
    try:
        while True:
            request = arm_requests.get(timeout=40)
            if request.get("schema") == "E2_BROKER_STOP_V1":
                break
            transcript.append(
                {"direction": "ARM_TO_BROKER", "message": copy.deepcopy(request)}
            )
            schema = request["schema"]
            if schema == "E2_BROKER_PROPOSAL_REQUEST_V1":
                proposal_bytes = request["proposal_bytes"]
                if hashlib.sha256(proposal_bytes.encode("utf-8")).hexdigest() != request[
                    "proposal_sha256"
                ]:
                    raise RuntimeError("proposal hash mismatch")
                proposal = json.loads(proposal_bytes)
                if canonical_bytes(proposal).decode("utf-8") != proposal_bytes:
                    raise RuntimeError("proposal not canonical")
                responses = []
                for role in RESPONSE_ROLES:
                    owner_commands[role].put(
                        {
                            "kind": "EVALUATE_PROPOSAL",
                            "proposal_bytes": proposal_bytes,
                        }
                    )
                for role in RESPONSE_ROLES:
                    item = owner_responses[role].get(timeout=20)
                    stored_responses[role] = item
                    responses.append(item)
                response = {
                    "schema": "E2_BROKER_PROPOSAL_RESULT_V1",
                    "proposal_sha256": request["proposal_sha256"],
                    "owner_responses": responses,
                }
            elif schema == "E2_BROKER_MATERIALIZE_REQUEST_V1":
                if set(stored_responses) != set(RESPONSE_ROLES):
                    raise RuntimeError("materialize before complete response")
                for role in RESPONSE_ROLES:
                    decision = stored_responses[role]["decision"]
                    if decision not in {"APPROVE", "COUNTER"}:
                        raise RuntimeError("non-consenting response")
                    owner_commands[role].put(
                        {
                            "kind": "MATERIALIZE",
                            "response_sha256": request[
                                "accepted_response_sha256"
                            ][role],
                            "counter_accepted": role
                            in request["accepted_counter_roles"],
                        }
                    )
                acts = []
                for role in RESPONSE_ROLES:
                    item = owner_responses[role].get(timeout=20)
                    stored_acts[role] = item
                    acts.append(item)
                response = {
                    "schema": "E2_BROKER_MATERIALIZE_RESULT_V1",
                    "owner_acts": acts,
                }
            elif schema == "E2_BROKER_TARGET_EXECUTE_REQUEST_V1":
                if set(stored_acts) != set(RESPONSE_ROLES):
                    raise RuntimeError("Target execute before formation closure")
                for role in RESPONSE_ROLES:
                    if request["owner_act_sha256"][role] != sha256_value(
                        stored_acts[role]
                    ):
                        raise RuntimeError("Target execute act mismatch")
                    owner_commands[role].put(
                        {
                            "kind": "REVALIDATE",
                            "proposal_sha256": request["proposal_sha256"],
                            "scope_sha256": request["scope_sha256"],
                            "execute_minute": request["execute_minute"],
                        }
                    )
                revalidations = [
                    owner_responses[role].get(timeout=20)
                    for role in RESPONSE_ROLES
                ]
                if any(item["status"] != "CURRENT" for item in revalidations):
                    raise RuntimeError("commit-time owner state stale")
                desired = _target_desired_state(view, request["proposal_sha256"])
                receipt = ledger.apply(
                    target_id=TARGET_ID,
                    actor_id=ARM_ID,
                    request_id="target-" + request["proposal_sha256"][:32],
                    capability_id=config["target_capability_id"],
                    expected_version=0,
                    desired_state=desired,
                )
                if receipt["decision"] != COMMITTED:
                    raise RuntimeError("Target ledger rejected exact occurrence")
                readback = ledger.readback(receipt)
                response = {
                    "schema": "E2_BROKER_TARGET_EXECUTE_RESULT_V1",
                    "commit_revalidations": revalidations,
                    "receipt": receipt,
                    "readback": readback,
                }
            elif schema == "E2_BROKER_ACCEPTANCE_REQUEST_V1":
                acceptances = []
                for role in ("O_Q", "O_V"):
                    owner_commands[role].put(
                        {
                            "kind": "ACCEPT",
                            "scope_sha256": request["scope_sha256"],
                            "proposal_sha256": request["proposal_sha256"],
                            "receipt_sha256": request["receipt_sha256"],
                            "readback_sha256": request["readback_sha256"],
                        }
                    )
                for role in ("O_Q", "O_V"):
                    acceptances.append(owner_responses[role].get(timeout=20))
                owner_commands["O_P"].put(
                    {
                        "kind": "FINALITY",
                        "scope_sha256": request["scope_sha256"],
                        "proposal_sha256": request["proposal_sha256"],
                        "receipt_sha256": request["receipt_sha256"],
                        "acceptance_sha256": sha256_value(acceptances),
                    }
                )
                finality = owner_responses["O_P"].get(timeout=20)
                response = {
                    "schema": "E2_BROKER_ACCEPTANCE_RESULT_V1",
                    "acceptances": acceptances,
                    "finality": finality,
                }
            else:
                raise RuntimeError("unsupported broker request")
            arm_responses.put(copy.deepcopy(response))
            transcript.append(
                {"direction": "BROKER_TO_ARM", "message": copy.deepcopy(response)}
            )
        result_queue.put(
            {
                "schema": "E2_BROKER_RESULT_V1",
                "status": "COMPLETED",
                "transcript": transcript,
                "transcript_sha256": sha256_value(transcript),
                "controller_signed_owner_fact_count": 0,
            }
        )
    except BaseException as exc:
        arm_responses.put(
            {"schema": "E2_BROKER_ERROR_V1", "error_type": type(exc).__name__}
        )
        result_queue.put(
            {
                "schema": "E2_BROKER_RESULT_V1",
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "transcript": transcript,
            }
        )
        raise


def target_audit(db_path: Path) -> Dict[str, Any]:
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        targets = [dict(row) for row in connection.execute("SELECT * FROM targets")]
        events = [
            dict(row) for row in connection.execute("SELECT * FROM commit_events")
        ]
        receipts = [
            dict(row) for row in connection.execute("SELECT * FROM receipts")
        ]
        return {
            "schema": "E2_TARGET_AUDIT_V1",
            "targets": targets,
            "commit_events": events,
            "receipts": receipts,
            "mutation_count": len(events),
        }
    finally:
        connection.close()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _run_case(
    case_dir: Path,
    *,
    mode: str,
    view: Mapping[str, Any],
) -> Dict[str, Any]:
    case_dir.mkdir(parents=True, exist_ok=False)
    owners_dir = case_dir / "owners"
    owners_dir.mkdir()
    context = multiprocessing.get_context("spawn")
    owner_commands = {}
    owner_responses = {}
    owner_processes = {}
    owner_ready = {}
    decisions = {
        "O_Q": "APPROVE",
        "O_V": "APPROVE",
        "O_R": "COUNTER",
        "O_S": "APPROVE",
        "O_P": "NOT_APPLICABLE",
    }
    if mode == REFUSE:
        decisions["O_R"] = "REFUSE"
    for role in ALL_OWNER_ROLES:
        command_queue = context.Queue()
        response_queue = context.Queue()
        owner_commands[role] = command_queue
        owner_responses[role] = response_queue
        config = {
            "owner_id": "owner-" + role.lower() + "-" + uuid.uuid4().hex,
            "owner_role": role,
            "principal_id": ROLE_PRINCIPALS[role],
            "db_path": str(owners_dir / (role.lower() + ".sqlite3")),
            "scope": _scope(view),
            "decision": decisions[role],
        }
        process = context.Process(
            target=owner_process,
            name="e2-owner-" + role.lower() + "-" + uuid.uuid4().hex[:8],
            args=(config, command_queue, response_queue),
        )
        process.start()
        owner_processes[role] = process
    for role in ALL_OWNER_ROLES:
        owner_ready[role] = owner_responses[role].get(timeout=20)

    target_db = case_dir / "target-ledger.sqlite3"
    target_ledger_id = "e2-target-" + mode.lower() + "-" + uuid.uuid4().hex
    target_capability_id = "e2-capability-" + mode.lower() + "-" + uuid.uuid4().hex
    ledger = TargetOperationLedger(target_db, ledger_id=target_ledger_id)
    ledger.initialize_target(TARGET_ID, INITIAL_TARGET_STATE)
    ledger.issue_capability(
        capability_id=target_capability_id,
        target_id=TARGET_ID,
        actor_id=ARM_ID,
        allowed_state=_target_desired_state(view, sha256_value(_proposal(view))),
    )

    arm_requests = context.Queue()
    arm_responses = context.Queue()
    broker_result_queue = context.Queue()
    broker_config = {
        "target_db_path": str(target_db),
        "target_ledger_id": target_ledger_id,
        "target_capability_id": target_capability_id,
        "view": copy.deepcopy(dict(view)),
    }
    broker = context.Process(
        target=broker_process,
        name="e2-broker-" + uuid.uuid4().hex[:12],
        args=(
            broker_config,
            owner_commands,
            owner_responses,
            arm_requests,
            arm_responses,
            broker_result_queue,
        ),
    )
    broker.start()
    worker = partial(
        arm_worker,
        request_queue=arm_requests,
        response_queue=arm_responses,
    )
    launch = BlindProcessLauncher(timeout_seconds=45).launch(
        view,
        private_materials=(mode, decisions),
        worker=worker,
    )
    if mode == REMOVE:
        arm_requests.put({"schema": "E2_BROKER_STOP_V1"})
    broker_result = broker_result_queue.get(timeout=30)
    broker.join(timeout=20)
    if broker.is_alive():
        broker.terminate()
        broker.join(timeout=5)
        raise RuntimeError("broker timeout")
    if broker.exitcode != 0 or broker_result["status"] != "COMPLETED":
        raise RuntimeError("broker failed")

    owner_audits = {}
    for role in ALL_OWNER_ROLES:
        owner_commands[role].put({"kind": "STOP"})
    for role in ALL_OWNER_ROLES:
        owner_audits[role] = owner_responses[role].get(timeout=20)
        process = owner_processes[role]
        process.join(timeout=20)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            raise RuntimeError("owner timeout")
        if process.exitcode != 0:
            raise RuntimeError("owner failed")

    arm_result = launch.worker_result
    audit = target_audit(target_db)
    expected_mutations = 1 if mode == BASELINE else 0
    if audit["mutation_count"] != expected_mutations:
        raise RuntimeError("unexpected Target mutation count")
    _write_json(case_dir / "view.json", view)
    _write_json(case_dir / "owner-ready.json", owner_ready)
    _write_json(case_dir / "arm-launch.json", launch.as_dict())
    _write_json(case_dir / "arm-result.json", arm_result)
    _write_json(case_dir / "broker-result.json", broker_result)
    _write_json(case_dir / "owner-audits.json", owner_audits)
    _write_json(case_dir / "target-audit.json", audit)
    return {
        "mode": mode,
        "view": view,
        "owner_ready": owner_ready,
        "arm_launch": launch.as_dict(),
        "arm_result": arm_result,
        "broker_result": broker_result,
        "owner_audits": owner_audits,
        "target_audit": audit,
    }


def run_suite(output_root: Path) -> Dict[str, Any]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    suite_dir = output_root / ("suite-" + uuid.uuid4().hex)
    suite_dir.mkdir()
    views = build_shared_views()
    _write_json(suite_dir / "shared-views.json", views)
    cases = {
        "baseline": _run_case(
            suite_dir / "baseline",
            mode=BASELINE,
            view=views[BASELINE],
        ),
        "remove": _run_case(
            suite_dir / "remove",
            mode=REMOVE,
            view=views[REMOVE],
        ),
        "refuse": _run_case(
            suite_dir / "refuse",
            mode=REFUSE,
            view=views[REFUSE],
        ),
    }
    result = {
        "schema": "E2_FORMATION_SUITE_RESULT_V1",
        "status": "RUN_COMPLETED",
        "suite_dir": str(suite_dir),
        "cases": {
            name: {
                "mode": case["mode"],
                "disposition": case["arm_result"]["disposition"],
                "target_mutation_count": case["target_audit"]["mutation_count"],
            }
            for name, case in cases.items()
        },
        "boundaries": {
            "accepted_candidate_scope": "LOCAL_SYNTHETIC_E2_MATURE_WORKFLOW_HITL",
            "no_legal_authority_claim": True,
            "no_physical_effect_claim": True,
            "no_controller_signed_owner_fact": True,
        },
    }
    _write_json(suite_dir / "suite-result.json", result)
    return {**result, "case_results": cases}


__all__ = [
    "BASELINE",
    "REMOVE",
    "REFUSE",
    "ROLE_FACTS",
    "run_suite",
    "verify_owner_signature",
]
