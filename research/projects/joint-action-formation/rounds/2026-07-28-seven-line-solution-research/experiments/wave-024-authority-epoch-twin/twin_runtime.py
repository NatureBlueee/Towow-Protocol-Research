"""Wave 024 local synthetic Authority-epoch S/R twin.

The runner is intentionally narrow.  It composes mature process, SQLite,
fencing-token, signed-receipt and readback patterns to test QUESTION.md.  The
Target reference monitor owns one SQLite transaction in which it compares the
presented delegation epoch with its already-durable Authority fence and then
either appends one exact digital Effect or one stale-Authority refusal.

This is not legal Authority, physical power, production isolation, or an
A1--A5 comparison.  All processes run as the same local OS user.
"""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing as mp
import os
import pathlib
import queue
import signal
import sqlite3
import sys
import uuid
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


HERE = pathlib.Path(__file__).resolve().parent
TARGET_ID = "VenueV:CircuitC7"
OBJECT_ID = "PowerOccurrence:VenueV:CircuitC7"
OPERATION = "ENERGIZE_EXACTLY_ONCE_45_MINUTES"
ACTOR_ID = "CANDIDATE-A4-MATURE-COMPOSITION"
Q_VERSION = "Q@v1"
GENESIS = "0" * 64
SANITIZED_CANDIDATE_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "PYTHONHASHSEED": "0",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def without(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    excluded = set(keys)
    return {key: item for key, item in value.items() if key not in excluded}


def public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()

def sign_record(
    body: Mapping[str, Any],
    *,
    key: Ed25519PrivateKey,
    digest_field: str,
) -> dict[str, Any]:
    record = copy.deepcopy(dict(body))
    record[digest_field] = sha256_value(record)
    record["signature_hex"] = key.sign(canonical_bytes(record)).hex()
    return record


def verify_record(
    record: Mapping[str, Any],
    *,
    public_key: str,
    digest_field: str,
) -> bool:
    try:
        unsigned = without(record, "signature_hex")
        if unsigned.get(digest_field) != sha256_value(
            without(unsigned, digest_field)
        ):
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(str(record["signature_hex"])),
            canonical_bytes(unsigned),
        )
        return True
    except Exception:
        return False


def verify_authority_predecessor_receipt(
    receipt: Mapping[str, Any],
    *,
    pinned_lab_root_public_key_hex: str,
    prior_authority: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the Target-native S receipt before Authority signs its successor.

    The controller may transport the receipt, but it cannot choose an arbitrary
    predecessor digest.  The Authority process pins the lab root at startup and
    independently verifies the certificate, receipt signature, exact scope and
    the current Authority head consumed by the Target.
    """

    candidate = copy.deepcopy(dict(receipt))
    certificate = candidate.get("target_certificate")
    if not isinstance(certificate, Mapping):
        raise RuntimeError("Authority predecessor lacks Target certificate")
    if not verify_record(
        certificate,
        public_key=pinned_lab_root_public_key_hex,
        digest_field="certificate_sha256",
    ):
        raise RuntimeError("Authority rejected predecessor Target certificate")
    if not verify_record(
        candidate,
        public_key=str(certificate.get("target_public_key_hex", "")),
        digest_field="target_receipt_sha256",
    ):
        raise RuntimeError("Authority rejected predecessor Target receipt")

    expected = {
        "schema": "TARGET_EFFECT_OR_REFUSAL_RECEIPT_V1",
        "decision": "COMMITTED",
        "mutation_applied": True,
        "current_at_commit": True,
        "actor_id": prior_authority["actor_id"],
        "q_sha256": prior_authority["q_sha256"],
        "object_id": prior_authority["object_id"],
        "target_id": prior_authority["target_id"],
        "operation": prior_authority["operation"],
        "presented_epoch": prior_authority["epoch"],
        "presented_delegation_sha256": prior_authority[
            "authority_head_sha256"
        ],
        "durable_fence_epoch": prior_authority["epoch"],
        "durable_fence_head_sha256": prior_authority[
            "authority_head_sha256"
        ],
        "durable_fence_status": "CURRENT",
    }
    for field, value in expected.items():
        if candidate.get(field) != value:
            raise RuntimeError(
                f"Authority predecessor Target receipt scope mismatch: {field}"
            )
    if certificate.get("schema") != "LAB_SYNTHETIC_TARGET_CERTIFICATE_V1":
        raise RuntimeError("Authority predecessor Target certificate schema mismatch")
    if certificate.get("certificate_scope") != "LOCAL_SYNTHETIC_TARGET_ONLY":
        raise RuntimeError("Authority predecessor Target certificate scope mismatch")
    for field in ("target_id", "q_sha256"):
        if certificate.get(field) != prior_authority[field]:
            raise RuntimeError(
                f"Authority predecessor Target certificate mismatch: {field}"
            )
    if not candidate.get("effect_id"):
        raise RuntimeError("Authority predecessor committed receipt lacks Effect")
    return candidate


def exact_task() -> dict[str, Any]:
    return {
        "schema": "CE001_EXACT_TASK_V1",
        "q_version": Q_VERSION,
        "object_id": OBJECT_ID,
        "target_id": TARGET_ID,
        "operation": OPERATION,
        "deadline_minute": 90,
        "required_duration_minutes": 45,
        "required_power_kw": 3.0,
        "power_tolerance_percent": 5,
        "safety_required": True,
        "noise_required": True,
        "other_circuits_energized": [],
        "acceptance_owners": ["O_Q", "O_V"],
        "finality_owner": "O_P",
    }


def initial_target_state() -> dict[str, Any]:
    return {
        "target_id": TARGET_ID,
        "energized": False,
        "power_kw": 0.0,
        "duration_minutes": 0,
        "safety_ok": True,
        "noise_ok": True,
        "other_circuits_energized": [],
        "power_samples": [],
    }


def exact_target_state() -> dict[str, Any]:
    return {
        "target_id": TARGET_ID,
        "energized": True,
        "power_kw": 3.0,
        "duration_minutes": 45,
        "effect_start_minute": 0,
        "deadline_minute": 90,
        "safety_ok": True,
        "noise_ok": True,
        "other_circuits_energized": [],
        "power_samples": [
            {
                "offset_minute": minute,
                "observed_at_minute": minute,
                "target_id": TARGET_ID,
                "power_kw": 3.0,
                "safety_ok": True,
                "noise_ok": True,
                "other_circuits_energized": [],
            }
            for minute in range(46)
        ],
    }


def sqlite_connect(path: str | pathlib.Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def start_with_sanitized_environment(process: mp.Process) -> None:
    original = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(SANITIZED_CANDIDATE_ENVIRONMENT)
        process.start()
    finally:
        os.environ.clear()
        os.environ.update(original)


def _authority_worker(
    command_queue: Any,
    result_queue: Any,
    authority_store_path: str,
    pinned_lab_root_public_key_hex: str,
) -> None:
    """Independent synthetic Principal/Authority signing process."""

    key = Ed25519PrivateKey.generate()
    store = pathlib.Path(authority_store_path)
    connection = sqlite_connect(store)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.executescript(
            """
            CREATE TABLE authority_identity(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                principal_id TEXT NOT NULL,
                public_key_hex TEXT NOT NULL,
                process_id INTEGER NOT NULL
            );
            CREATE TABLE authority_records(
                sequence INTEGER PRIMARY KEY,
                head_sha256 TEXT NOT NULL UNIQUE,
                prev_head_sha256 TEXT NOT NULL,
                record_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO authority_identity VALUES(1, ?, ?, ?)",
            ("Principal:VenueV", public_key_hex(key), os.getpid()),
        )
        connection.commit()
    finally:
        connection.close()
    result_queue.put(
        {
            "status": "READY",
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex(key),
        }
    )
    while True:
        command = command_queue.get()
        if command["kind"] == "STOP":
            return
        if command["kind"] == "ISSUE_DELEGATION":
            body = copy.deepcopy(command["body"])
            body["issuer_process_id"] = os.getpid()
            result = sign_record(body, key=key, digest_field="authority_head_sha256")
        elif command["kind"] == "REVOKE":
            prior = command["prior"]
            predecessor = verify_authority_predecessor_receipt(
                command["experiment_predecessor_s_target_receipt"],
                pinned_lab_root_public_key_hex=pinned_lab_root_public_key_hex,
                prior_authority=prior,
            )
            predecessor_certificate = predecessor["target_certificate"]
            body = {
                "schema": "AUTHORITY_HEAD_V1",
                "delegation_id": prior["delegation_id"],
                "principal_id": prior["principal_id"],
                "actor_id": prior["actor_id"],
                "q_sha256": prior["q_sha256"],
                "object_id": prior["object_id"],
                "target_id": prior["target_id"],
                "operation": prior["operation"],
                "epoch": int(prior["epoch"]) + 1,
                "status": "REVOKED",
                "prev_authority_head_sha256": prior["authority_head_sha256"],
                "reason": "PRINCIPAL_REVOKED_BEFORE_TARGET_INGRESS",
                "experiment_predecessor_s_target_receipt_sha256": predecessor[
                    "target_receipt_sha256"
                ],
                "experiment_predecessor_s_target_certificate_sha256": (
                    predecessor_certificate["certificate_sha256"]
                ),
                "experiment_predecessor_s_request_sha256": predecessor[
                    "request_sha256"
                ],
                "experiment_predecessor_s_effect_id": predecessor["effect_id"],
                "experiment_predecessor_validation": (
                    "AUTHORITY_VERIFIED_PINNED_LAB_ROOT_TARGET_SIGNATURE_AND_EXACT_SCOPE"
                ),
                "issuer_process_id": os.getpid(),
            }
            result = sign_record(body, key=key, digest_field="authority_head_sha256")
        else:
            raise RuntimeError("unknown Authority command")
        connection = sqlite_connect(store)
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = connection.execute(
                "SELECT sequence, head_sha256 FROM authority_records "
                "ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if prior is None else int(prior["sequence"]) + 1
            prev = GENESIS if prior is None else str(prior["head_sha256"])
            if result["prev_authority_head_sha256"] != prev:
                raise RuntimeError("Authority append-only head mismatch")
            connection.execute(
                "INSERT INTO authority_records VALUES(?, ?, ?, ?)",
                (
                    sequence,
                    result["authority_head_sha256"],
                    prev,
                    canonical_bytes(result).decode("utf-8"),
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        result_queue.put({"process_id": os.getpid(), "record": result})


def _lab_registry_worker(
    command_queue: Any,
    result_queue: Any,
    registry_store_path: str,
) -> None:
    """Independent local synthetic trust-root process; parent never sees key."""

    key = Ed25519PrivateKey.generate()
    store = pathlib.Path(registry_store_path)
    connection = sqlite_connect(store)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.executescript(
            """
            CREATE TABLE registry_identity(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                public_key_hex TEXT NOT NULL,
                process_id INTEGER NOT NULL
            );
            CREATE TABLE certificates(
                certificate_sha256 TEXT PRIMARY KEY,
                certificate_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO registry_identity VALUES(1, ?, ?)",
            (public_key_hex(key), os.getpid()),
        )
        connection.commit()
    finally:
        connection.close()
    result_queue.put(
        {
            "status": "READY",
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex(key),
        }
    )
    while True:
        command = command_queue.get()
        if command["kind"] == "STOP":
            return
        if command["kind"] != "SIGN_TARGET_CERTIFICATE":
            raise RuntimeError("unknown registry command")
        certificate = sign_record(
            {
                "schema": "LAB_SYNTHETIC_TARGET_CERTIFICATE_V1",
                "target_id": TARGET_ID,
                "q_sha256": command["q_sha256"],
                "target_public_key_hex": command["target_public_key_hex"],
                "certificate_scope": "LOCAL_SYNTHETIC_TARGET_ONLY",
                "registry_process_id": os.getpid(),
            },
            key=key,
            digest_field="certificate_sha256",
        )
        connection = sqlite_connect(store)
        try:
            connection.execute(
                "INSERT INTO certificates VALUES(?, ?)",
                (
                    certificate["certificate_sha256"],
                    canonical_bytes(certificate).decode("utf-8"),
                ),
            )
            connection.commit()
        finally:
            connection.close()
        result_queue.put({"process_id": os.getpid(), "certificate": certificate})


def _initialize_target_db(
    path: pathlib.Path,
    *,
    target_certificate: Mapping[str, Any],
    initial_authority: Mapping[str, Any],
) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.executescript(
            """
            CREATE TABLE metadata(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                target_id TEXT NOT NULL,
                target_certificate_json TEXT NOT NULL
            );
            CREATE TABLE target_state(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                state_json TEXT NOT NULL,
                state_sha256 TEXT NOT NULL,
                version INTEGER NOT NULL,
                effect_count INTEGER NOT NULL,
                last_effect_id TEXT
            );
            CREATE TABLE authority_heads(
                sequence INTEGER PRIMARY KEY,
                epoch INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL,
                head_sha256 TEXT NOT NULL UNIQUE,
                record_json TEXT NOT NULL
            );
            CREATE TABLE native_events(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_sha256 TEXT NOT NULL UNIQUE,
                event_json TEXT NOT NULL
            );
            CREATE TABLE requests(
                request_id TEXT PRIMARY KEY,
                request_sha256 TEXT NOT NULL,
                decision TEXT NOT NULL,
                receipt_json TEXT NOT NULL
            );
            CREATE TABLE effects(
                effect_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL UNIQUE,
                state_sha256 TEXT NOT NULL,
                authority_head_sha256 TEXT NOT NULL
            );
            CREATE TABLE readbacks(
                readback_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                readback_json TEXT NOT NULL
            );
            """
        )
        state = initial_target_state()
        connection.execute(
            "INSERT INTO metadata VALUES(1, ?, ?)",
            (TARGET_ID, canonical_bytes(target_certificate).decode("utf-8")),
        )
        connection.execute(
            "INSERT INTO target_state VALUES(1, ?, ?, 0, 0, NULL)",
            (canonical_bytes(state).decode("utf-8"), sha256_value(state)),
        )
        connection.execute(
            "INSERT INTO authority_heads VALUES(1, ?, ?, ?, ?)",
            (
                initial_authority["epoch"],
                initial_authority["status"],
                initial_authority["authority_head_sha256"],
                canonical_bytes(initial_authority).decode("utf-8"),
            ),
        )
        event = {
            "event_type": "AUTHORITY_FENCE_BOOTSTRAPPED",
            "epoch": initial_authority["epoch"],
            "status": initial_authority["status"],
            "authority_head_sha256": initial_authority[
                "authority_head_sha256"
            ],
        }
        connection.execute(
            "INSERT INTO native_events(event_type, event_sha256, event_json) "
            "VALUES(?, ?, ?)",
            (
                event["event_type"],
                sha256_value(event),
                canonical_bytes(event).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _target_sign(
    body: Mapping[str, Any],
    *,
    target_key: Ed25519PrivateKey,
    target_certificate: Mapping[str, Any],
) -> dict[str, Any]:
    bound = copy.deepcopy(dict(body))
    bound["target_certificate"] = copy.deepcopy(dict(target_certificate))
    return sign_record(
        bound,
        key=target_key,
        digest_field="target_receipt_sha256",
    )


def _append_native_event(
    connection: sqlite3.Connection,
    event: Mapping[str, Any],
) -> int:
    event_hash = sha256_value(event)
    connection.execute(
        "INSERT INTO native_events(event_type, event_sha256, event_json) "
        "VALUES(?, ?, ?)",
        (
            event["event_type"],
            event_hash,
            canonical_bytes(event).decode("utf-8"),
        ),
    )
    return int(connection.execute("SELECT last_insert_rowid()").fetchone()[0])


def _apply_fence_record(
    path: pathlib.Path,
    *,
    record: Mapping[str, Any],
    authority_public_key_hex: str,
    target_key: Ed25519PrivateKey,
    target_certificate: Mapping[str, Any],
) -> dict[str, Any]:
    if not verify_record(
        record,
        public_key=authority_public_key_hex,
        digest_field="authority_head_sha256",
    ):
        raise RuntimeError("Authority head signature invalid")
    connection = sqlite_connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        prior = connection.execute(
            "SELECT * FROM authority_heads ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if prior is None:
            raise RuntimeError("Target authority fence missing")
        prior_record = json.loads(prior["record_json"])
        if record.get("schema") != "AUTHORITY_HEAD_V1":
            raise RuntimeError("superseding fence schema mismatch")
        if record.get("status") != "REVOKED":
            raise RuntimeError("superseding fence is not an exact revocation")
        for field in (
            "delegation_id",
            "principal_id",
            "actor_id",
            "q_sha256",
            "object_id",
            "target_id",
            "operation",
        ):
            if record.get(field) != prior_record.get(field):
                raise RuntimeError(f"superseding fence scope mismatch: {field}")
        if (
            record["object_id"] != OBJECT_ID
            or record["target_id"] != TARGET_ID
            or record["operation"] != OPERATION
        ):
            raise RuntimeError(
                "superseding fence exact object/Target/operation mismatch"
            )
        if int(record["epoch"]) != int(prior["epoch"]) + 1:
            raise RuntimeError("revocation epoch is not the next fence")
        if record["prev_authority_head_sha256"] != prior["head_sha256"]:
            raise RuntimeError("revocation is detached from current head")
        connection.execute(
            "INSERT INTO authority_heads VALUES(?, ?, ?, ?, ?)",
            (
                int(prior["sequence"]) + 1,
                record["epoch"],
                record["status"],
                record["authority_head_sha256"],
                canonical_bytes(record).decode("utf-8"),
            ),
        )
        event = {
            "event_type": "FENCE_ADVANCED",
            "epoch": record["epoch"],
            "status": record["status"],
            "authority_head_sha256": record["authority_head_sha256"],
            "target_process_id": os.getpid(),
        }
        event_sequence = _append_native_event(connection, event)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return _target_sign(
        {
            "schema": "TARGET_FENCE_ADVANCED_RECEIPT_V1",
            "decision": "FENCE_ADVANCED",
            "event_sequence": event_sequence,
            "epoch": record["epoch"],
            "status": record["status"],
            "authority_head_sha256": record["authority_head_sha256"],
            "target_process_id": os.getpid(),
        },
        target_key=target_key,
        target_certificate=target_certificate,
    )


def _target_execute(
    path: pathlib.Path,
    *,
    request: Mapping[str, Any],
    q_sha256: str,
    authority_public_key_hex: str,
    target_key: Ed25519PrivateKey,
    target_certificate: Mapping[str, Any],
) -> dict[str, Any]:
    """Linearization point: fence comparison and Effect/refusal are atomic."""

    delegation = request["delegation"]
    if not verify_record(
        delegation,
        public_key=authority_public_key_hex,
        digest_field="authority_head_sha256",
    ):
        raise RuntimeError("presented delegation signature invalid")
    expected = {
        "q_sha256": q_sha256,
        "object_id": OBJECT_ID,
        "target_id": TARGET_ID,
        "operation": OPERATION,
        "actor_id": ACTOR_ID,
    }
    for field, wanted in expected.items():
        if request.get(field) != wanted:
            raise RuntimeError(f"exact request/delegation binding failed: {field}")
        if delegation.get(field) != wanted:
            raise RuntimeError(f"exact delegation binding failed: {field}")
    if delegation.get("schema") != "AUTHORITY_DELEGATION_V1":
        raise RuntimeError("presented object is not a delegation")
    if delegation.get("status") != "CURRENT":
        raise RuntimeError("presented delegation is not a current grant record")
    if request.get("presented_epoch") != delegation.get("epoch"):
        raise RuntimeError("request epoch does not match delegation epoch")
    commit_minute = request.get("commit_logical_minute")
    if not isinstance(commit_minute, int):
        raise RuntimeError("commit logical minute missing")
    if not (
        int(delegation.get("valid_from_logical_minute", -1))
        <= commit_minute
        <= int(delegation.get("valid_until_logical_minute", -1))
    ):
        raise RuntimeError("delegation is outside its exact validity window")
    if request.get("desired_state") != exact_target_state():
        raise RuntimeError("request desired state is not exact CE-001 state")
    request_hash = sha256_value(request)
    connection = sqlite_connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        prior_request = connection.execute(
            "SELECT request_sha256, receipt_json FROM requests WHERE request_id=?",
            (request["request_id"],),
        ).fetchone()
        if prior_request is not None:
            if prior_request["request_sha256"] != request_hash:
                raise RuntimeError("request_id rebound")
            connection.commit()
            return json.loads(prior_request["receipt_json"])

        authority = connection.execute(
            "SELECT * FROM authority_heads ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        state = connection.execute("SELECT * FROM target_state WHERE singleton=1").fetchone()
        if authority is None or state is None:
            raise RuntimeError("Target reference-monitor state incomplete")
        ingress_event = {
            "event_type": "REQUEST_INGRESS",
            "request_id": request["request_id"],
            "request_sha256": request_hash,
            "presented_epoch": delegation["epoch"],
            "durable_fence_epoch": authority["epoch"],
            "durable_fence_status": authority["status"],
            "target_process_id": os.getpid(),
        }
        ingress_sequence = _append_native_event(connection, ingress_event)

        current = (
            int(delegation["epoch"]) == int(authority["epoch"])
            and delegation["authority_head_sha256"] == authority["head_sha256"]
            and authority["status"] == "CURRENT"
        )
        if current:
            if int(state["effect_count"]) != 0 or int(state["version"]) != 0:
                raise RuntimeError("exactly-once Target already changed before request")
            desired = request["desired_state"]
            effect_id = "effect-" + uuid.uuid4().hex
            connection.execute(
                "UPDATE target_state SET state_json=?, state_sha256=?, version=1, "
                "effect_count=1, last_effect_id=? WHERE singleton=1 AND version=0",
                (
                    canonical_bytes(desired).decode("utf-8"),
                    sha256_value(desired),
                    effect_id,
                ),
            )
            if connection.execute("SELECT changes()").fetchone()[0] != 1:
                raise RuntimeError("Target CAS failed")
            connection.execute(
                "INSERT INTO effects VALUES(?, ?, ?, ?)",
                (
                    effect_id,
                    request["request_id"],
                    sha256_value(desired),
                    authority["head_sha256"],
                ),
            )
            decision = "COMMITTED"
            reason = "CURRENT_AUTHORITY_AT_TARGET_LINEARIZATION_POINT"
            mutation_applied = True
        else:
            effect_id = None
            decision = "REJECTED_STALE_EPOCH"
            reason = "REVOKED/STALE_AUTHORITY"
            mutation_applied = False

        decision_event = {
            "event_type": "EFFECT_COMMITTED" if current else "AUTHORITY_REJECTED",
            "request_id": request["request_id"],
            "decision": decision,
            "effect_id": effect_id,
            "authority_head_sha256": authority["head_sha256"],
            "authority_epoch": authority["epoch"],
            "target_process_id": os.getpid(),
        }
        decision_sequence = _append_native_event(connection, decision_event)
        receipt = _target_sign(
            {
                "schema": "TARGET_EFFECT_OR_REFUSAL_RECEIPT_V1",
                "request_id": request["request_id"],
                "request_sha256": request_hash,
                "q_sha256": q_sha256,
                "object_id": request["object_id"],
                "target_id": request["target_id"],
                "operation": request["operation"],
                "actor_id": request["actor_id"],
                "presented_delegation_sha256": delegation[
                    "authority_head_sha256"
                ],
                "presented_epoch": delegation["epoch"],
                "durable_fence_head_sha256": authority["head_sha256"],
                "durable_fence_epoch": authority["epoch"],
                "durable_fence_status": authority["status"],
                "current_at_commit": current,
                "decision": decision,
                "reason": reason,
                "mutation_applied": mutation_applied,
                "effect_id": effect_id,
                "ingress_event_sequence": ingress_sequence,
                "decision_event_sequence": decision_sequence,
                "target_process_id": os.getpid(),
            },
            target_key=target_key,
            target_certificate=target_certificate,
        )
        connection.execute(
            "INSERT INTO requests VALUES(?, ?, ?, ?)",
            (
                request["request_id"],
                request_hash,
                decision,
                canonical_bytes(receipt).decode("utf-8"),
            ),
        )
        connection.commit()
        return receipt
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _target_status(
    path: pathlib.Path,
    *,
    request_id: str,
    target_key: Ed25519PrivateKey,
    target_certificate: Mapping[str, Any],
) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        connection.execute("BEGIN")
        request = connection.execute(
            "SELECT * FROM requests WHERE request_id=?", (request_id,)
        ).fetchone()
        state = connection.execute("SELECT * FROM target_state WHERE singleton=1").fetchone()
        authority = connection.execute(
            "SELECT * FROM authority_heads ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if request is None or state is None or authority is None:
            raise RuntimeError("Target status is incomplete")
        receipt = json.loads(request["receipt_json"])
        readback_id = "readback-" + uuid.uuid4().hex
        readback = _target_sign(
            {
                "schema": "TARGET_EXACT_STATUS_READBACK_V1",
                "readback_id": readback_id,
                "request_id": request_id,
                "request_sha256": request["request_sha256"],
                "receipt_sha256": receipt["target_receipt_sha256"],
                "decision": request["decision"],
                "target_id": TARGET_ID,
                "state": json.loads(state["state_json"]),
                "state_sha256": state["state_sha256"],
                "version": state["version"],
                "effect_count": state["effect_count"],
                "last_effect_id": state["last_effect_id"],
                "authority_epoch": authority["epoch"],
                "authority_status": authority["status"],
                "authority_head_sha256": authority["head_sha256"],
                "target_process_id": os.getpid(),
            },
            target_key=target_key,
            target_certificate=target_certificate,
        )
        connection.execute(
            "INSERT INTO readbacks VALUES(?, ?, ?)",
            (
                readback_id,
                request_id,
                canonical_bytes(readback).decode("utf-8"),
            ),
        )
        connection.commit()
        return {"receipt": receipt, "readback": readback}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _target_audit(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        state = connection.execute("SELECT * FROM target_state").fetchone()
        heads = [dict(row) for row in connection.execute("SELECT * FROM authority_heads ORDER BY sequence")]
        events = [dict(row) for row in connection.execute("SELECT * FROM native_events ORDER BY sequence")]
        return {
            "schema": "TARGET_NATIVE_AUDIT_V1",
            "state": json.loads(state["state_json"]),
            "state_sha256": state["state_sha256"],
            "version": state["version"],
            "effect_count": state["effect_count"],
            "last_effect_id": state["last_effect_id"],
            "request_count": connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
            "refusal_count": connection.execute(
                "SELECT COUNT(*) FROM requests WHERE decision='REJECTED_STALE_EPOCH'"
            ).fetchone()[0],
            "readback_count": connection.execute("SELECT COUNT(*) FROM readbacks").fetchone()[0],
            "authority_heads": [
                {
                    **without(row, "record_json"),
                    "record": json.loads(row["record_json"]),
                }
                for row in heads
            ],
            "native_events": [
                {
                    **without(row, "event_json"),
                    "event": json.loads(row["event_json"]),
                }
                for row in events
            ],
        }
    finally:
        connection.close()


def _target_worker(
    *,
    db_path: str,
    command_queue: Any,
    execute_result_queue: Any,
    status_response_queue: Any,
    control_response_queue: Any,
    ready_queue: Any,
    initial_authority: Mapping[str, Any],
    authority_public_key_hex: str,
    lab_root_public_key_hex: str,
    q_sha256: str,
) -> None:
    path = pathlib.Path(db_path)
    target_key = Ed25519PrivateKey.generate()
    ready_queue.put(
        {
            "target_process_id": os.getpid(),
            "status": "CERTIFICATE_REQUEST",
            "target_public_key_hex": public_key_hex(target_key),
        }
    )
    install = command_queue.get()
    if install.get("kind") != "INSTALL_CERTIFICATE":
        raise RuntimeError("Target certificate was not installed before startup")
    target_certificate = install["target_certificate"]
    if not verify_record(
        target_certificate,
        public_key=lab_root_public_key_hex,
        digest_field="certificate_sha256",
    ):
        raise RuntimeError("Target certificate trust-root signature invalid")
    if (
        target_certificate.get("target_public_key_hex") != public_key_hex(target_key)
        or target_certificate.get("target_id") != TARGET_ID
        or target_certificate.get("q_sha256") != q_sha256
    ):
        raise RuntimeError("Target certificate does not bind this process")
    _initialize_target_db(
        path,
        target_certificate=target_certificate,
        initial_authority=initial_authority,
    )
    ready_queue.put(
        {
            "target_process_id": os.getpid(),
            "status": "READY",
            "target_public_key_hex": public_key_hex(target_key),
            "target_certificate": target_certificate,
        }
    )
    while True:
        command = command_queue.get()
        kind = command["kind"]
        if kind == "STOP":
            control_response_queue.put({"status": "STOPPED", "process_id": os.getpid()})
            return
        if kind == "APPLY_AUTHORITY":
            receipt = _apply_fence_record(
                path,
                record=command["record"],
                authority_public_key_hex=authority_public_key_hex,
                target_key=target_key,
                target_certificate=target_certificate,
            )
            control_response_queue.put(receipt)
        elif kind == "EXECUTE":
            receipt = _target_execute(
                path,
                request=command["request"],
                q_sha256=q_sha256,
                authority_public_key_hex=authority_public_key_hex,
                target_key=target_key,
                target_certificate=target_certificate,
            )
            execute_result_queue.put(receipt)
            # Intentionally no candidate ACK: the source remains uncertain.
        elif kind == "STATUS":
            status_response_queue.put(
                _target_status(
                    path,
                    request_id=command["request_id"],
                    target_key=target_key,
                    target_certificate=target_certificate,
                )
            )
        elif kind == "AUDIT":
            control_response_queue.put(_target_audit(path))
        else:
            raise RuntimeError("unknown Target command")


def _initialize_source_state(path: pathlib.Path, payload: Mapping[str, Any]) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.executescript(
            """
            CREATE TABLE operation(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                payload_sha256 TEXT NOT NULL,
                request_json TEXT NOT NULL,
                request_sha256 TEXT NOT NULL,
                source_process_id INTEGER NOT NULL,
                phase TEXT NOT NULL,
                ack_received_count INTEGER NOT NULL,
                retry_execute_count INTEGER NOT NULL
            );
            CREATE TABLE runtime_startups(
                phase TEXT PRIMARY KEY,
                process_id INTEGER NOT NULL,
                visible_surface_json TEXT NOT NULL
            );
            """
        )
        request = payload["request"]
        connection.execute(
            "INSERT INTO operation VALUES(1, ?, ?, ?, ?, ?, 0, 0)",
            (
                sha256_value(payload),
                canonical_bytes(request).decode("utf-8"),
                sha256_value(request),
                os.getpid(),
                "PREPARED_BEFORE_INGRESS",
            ),
        )
        surface = {
            "candidate_artifact_sha256": payload["candidate_artifact_sha256"],
            "payload_sha256": sha256_value(payload),
            "process_name": mp.current_process().name,
            "argv": list(sys.argv),
            "cwd": os.getcwd(),
            "environment": dict(os.environ),
            "source_state_path": str(path),
        }
        connection.execute(
            "INSERT INTO runtime_startups VALUES('SOURCE', ?, ?)",
            (os.getpid(), canonical_bytes(surface).decode("utf-8")),
        )
        connection.commit()
    finally:
        connection.close()


def _validate_target_status_for_request(
    status: Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    request: Mapping[str, Any],
) -> str:
    """Validate exact recovery closure and return the bounded disposition."""

    target_certificate = status["receipt"]["target_certificate"]
    if not verify_record(
        target_certificate,
        public_key=payload["lab_root_public_key_hex"],
        digest_field="certificate_sha256",
    ):
        raise RuntimeError("Target certificate invalid")
    target_public_key = target_certificate["target_public_key_hex"]
    for record in (status["receipt"], status["readback"]):
        if not verify_record(
            record,
            public_key=target_public_key,
            digest_field="target_receipt_sha256",
        ):
            raise RuntimeError("Target status record invalid")
    receipt = status["receipt"]
    readback = status["readback"]
    request_sha256 = sha256_value(request)
    if (
        target_certificate.get("q_sha256") != payload["q_sha256"]
        or target_certificate.get("target_id") != request["target_id"]
        or readback.get("target_certificate") != target_certificate
        or receipt.get("request_id") != request["request_id"]
        or readback.get("request_id") != request["request_id"]
        or receipt.get("request_sha256") != request_sha256
        or readback.get("request_sha256") != request_sha256
        or readback.get("receipt_sha256")
        != receipt.get("target_receipt_sha256")
        or receipt.get("q_sha256") != payload["q_sha256"]
        or receipt.get("object_id") != request["object_id"]
        or receipt.get("target_id") != request["target_id"]
        or readback.get("target_id") != request["target_id"]
        or receipt.get("operation") != request["operation"]
        or receipt.get("actor_id") != request["actor_id"]
        or receipt.get("decision") != readback.get("decision")
    ):
        raise RuntimeError("Target status is detached from durable source request")
    if receipt["decision"] == "COMMITTED":
        if (
            readback["effect_count"] != 1
            or receipt.get("mutation_applied") is not True
            or not receipt.get("effect_id")
            or readback.get("last_effect_id") != receipt.get("effect_id")
            or readback.get("state") != exact_target_state()
            or readback.get("state_sha256") != sha256_value(exact_target_state())
        ):
            raise RuntimeError("committed recovery lacks one exact Effect")
        return "RECOVERED_COMMITTED_NO_REPLAY"
    if receipt["decision"] == "REJECTED_STALE_EPOCH":
        if (
            readback["effect_count"] != 0
            or receipt.get("mutation_applied") is not False
            or receipt.get("effect_id") is not None
            or readback.get("last_effect_id") is not None
            or readback.get("state") != initial_target_state()
            or readback.get("state_sha256") != sha256_value(initial_target_state())
            or readback.get("authority_epoch")
            != receipt.get("durable_fence_epoch")
            or readback.get("authority_head_sha256")
            != receipt.get("durable_fence_head_sha256")
        ):
            raise RuntimeError("stale Authority recovery observed an Effect")
        return "RECOVERED_REVOKED_NO_RETRY"
    raise RuntimeError("unsupported Target recovery disposition")


def _candidate_worker(
    *,
    phase: str,
    payload: Mapping[str, Any],
    source_state_path: str,
    command_queue: Any,
    status_response_queue: Any,
    candidate_ack_queue: Any,
    prepared_event: Any | None,
    release_event: Any | None,
    recovery_result_queue: Any | None,
) -> None:
    """One frozen candidate executable with source and recovery phases."""

    path = pathlib.Path(source_state_path)
    if phase == "SOURCE":
        _initialize_source_state(path, payload)
        prepared_event.set()
        if not release_event.wait(timeout=20):
            raise RuntimeError("controller did not release candidate ingress")
        connection = sqlite_connect(path)
        try:
            connection.execute(
                "UPDATE operation SET phase='WAITING_FOR_LOST_ACK' WHERE singleton=1"
            )
            connection.commit()
        finally:
            connection.close()
        command_queue.put({"kind": "EXECUTE", "request": payload["request"]})
        # An actual proxy-owned ACK channel exists, but the proxy durably drops
        # this receipt.  The parent externally terminates this blocked get.
        candidate_ack_queue.get()
        connection = sqlite_connect(path)
        try:
            connection.execute(
                "UPDATE operation SET ack_received_count=ack_received_count+1 "
                "WHERE singleton=1"
            )
            connection.commit()
        finally:
            connection.close()
        raise RuntimeError("ACK unexpectedly reached the source candidate")

    if phase != "RECOVERY":
        raise RuntimeError("unknown candidate phase")
    connection = sqlite_connect(path)
    try:
        row = connection.execute("SELECT * FROM operation WHERE singleton=1").fetchone()
        if row is None:
            raise RuntimeError("source durable state missing")
        request = json.loads(row["request_json"])
        if row["request_sha256"] != sha256_value(request):
            raise RuntimeError("source request durable state corrupted")
        surface = {
            "candidate_artifact_sha256": payload["candidate_artifact_sha256"],
            "payload_sha256": sha256_value(payload),
            "process_name": mp.current_process().name,
            "argv": list(sys.argv),
            "cwd": os.getcwd(),
            "environment": dict(os.environ),
            "source_state_path": str(path),
        }
        connection.execute(
            "INSERT INTO runtime_startups VALUES('RECOVERY', ?, ?)",
            (os.getpid(), canonical_bytes(surface).decode("utf-8")),
        )
        connection.execute(
            "UPDATE operation SET phase='RECOVERY_STATUS_QUERY' WHERE singleton=1"
        )
        connection.commit()
    finally:
        connection.close()
    command_queue.put({"kind": "STATUS", "request_id": request["request_id"]})
    try:
        status = status_response_queue.get(timeout=20)
    except queue.Empty as exc:
        raise RuntimeError("Target status timeout") from exc
    disposition = _validate_target_status_for_request(
        status,
        payload=payload,
        request=request,
    )
    connection = sqlite_connect(path)
    try:
        connection.execute(
            "UPDATE operation SET phase=?, retry_execute_count=0 WHERE singleton=1",
            (disposition,),
        )
        connection.commit()
    finally:
        connection.close()
    recovery_result_queue.put(
        {
            "schema": "CANDIDATE_RECOVERY_RESULT_V1",
            "candidate_process_id": os.getpid(),
            "disposition": disposition,
            "retry_execute_count": 0,
            "target_status": status,
        }
    )


def _verify_target_status_for_owner(
    status: Mapping[str, Any],
    *,
    lab_root_public_key_hex: str,
    q_sha256: str,
) -> bool:
    try:
        receipt = status["receipt"]
        readback = status["readback"]
        certificate = receipt["target_certificate"]
        if not verify_record(
            certificate,
            public_key=lab_root_public_key_hex,
            digest_field="certificate_sha256",
        ):
            return False
        target_key = certificate["target_public_key_hex"]
        if not all(
            verify_record(
                item,
                public_key=target_key,
                digest_field="target_receipt_sha256",
            )
            for item in (receipt, readback)
        ):
            return False
        if (
            certificate.get("q_sha256") != q_sha256
            or certificate.get("target_id") != TARGET_ID
            or receipt.get("q_sha256") != q_sha256
            or receipt.get("object_id") != OBJECT_ID
            or receipt.get("target_id") != TARGET_ID
            or receipt.get("operation") != OPERATION
            or receipt.get("actor_id") != ACTOR_ID
            or receipt.get("decision") != "COMMITTED"
            or receipt.get("mutation_applied") is not True
            or not receipt.get("effect_id")
        ):
            return False
        if (
            readback.get("target_id") != TARGET_ID
            or readback.get("request_id") != receipt.get("request_id")
            or readback.get("request_sha256") != receipt.get("request_sha256")
            or readback.get("receipt_sha256")
            != receipt.get("target_receipt_sha256")
            or readback.get("decision") != receipt.get("decision")
            or readback.get("effect_count") != 1
            or readback.get("last_effect_id") != receipt.get("effect_id")
            or readback.get("state") != exact_target_state()
            or readback.get("state_sha256") != sha256_value(exact_target_state())
        ):
            return False
        return True
    except Exception:
        return False


def _initialize_owner_store(
    path: pathlib.Path,
    *,
    owner_id: str,
    owner_public_key_hex: str,
    pinned_q_sha256: str,
    pinned_lab_root_public_key_hex: str | None,
    pinned_acceptance_keys: Mapping[str, str],
) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.executescript(
            """
            CREATE TABLE owner_identity(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                owner_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                public_key_hex TEXT NOT NULL,
                pinned_q_sha256 TEXT NOT NULL,
                pinned_lab_root_public_key_hex TEXT,
                pinned_acceptance_keys_json TEXT NOT NULL
            );
            CREATE TABLE owner_events(
                sequence INTEGER PRIMARY KEY,
                prev_event_sha256 TEXT NOT NULL,
                event_sha256 TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                record_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO owner_identity VALUES(1, ?, ?, ?, ?, ?, ?)",
            (
                owner_id,
                f"Principal:{owner_id}",
                owner_public_key_hex,
                pinned_q_sha256,
                pinned_lab_root_public_key_hex,
                canonical_bytes(dict(pinned_acceptance_keys)).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _append_owner_record(
    path: pathlib.Path,
    *,
    event_type: str,
    record: Mapping[str, Any],
) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        prior = connection.execute(
            "SELECT sequence, event_sha256 FROM owner_events "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = 1 if prior is None else int(prior["sequence"]) + 1
        prev = GENESIS if prior is None else str(prior["event_sha256"])
        event_body = {
            "sequence": sequence,
            "prev_event_sha256": prev,
            "event_type": event_type,
            "record_sha256": record["owner_receipt_sha256"],
        }
        connection.execute(
            "INSERT INTO owner_events VALUES(?, ?, ?, ?, ?)",
            (
                sequence,
                prev,
                sha256_value(event_body),
                event_type,
                canonical_bytes(record).decode("utf-8"),
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _owner_store_audit(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        identity = dict(connection.execute("SELECT * FROM owner_identity").fetchone())
        events = []
        for row in connection.execute("SELECT * FROM owner_events ORDER BY sequence"):
            events.append(
                {
                    **without(dict(row), "record_json"),
                    "record": json.loads(row["record_json"]),
                }
            )
        return {"identity": identity, "events": events, "event_count": len(events)}
    finally:
        connection.close()


def _owner_service_worker(
    *,
    owner_id: str,
    owner_store_path: str,
    pinned_q_sha256: str,
    pinned_lab_root_public_key_hex: str | None,
    pinned_acceptance_keys: Mapping[str, str],
    command_queue: Any,
    result_queue: Any,
) -> None:
    """Owner-native key generation, validation, append and signing boundary."""

    if owner_id not in {"O_Q", "O_V", "O_P"}:
        raise RuntimeError("invalid owner service")
    if owner_id in {"O_Q", "O_V"}:
        if not pinned_lab_root_public_key_hex or pinned_acceptance_keys:
            raise RuntimeError("Acceptance owner startup trust is incomplete")
    elif (
        pinned_lab_root_public_key_hex is not None
        or set(pinned_acceptance_keys) != {"O_Q", "O_V"}
    ):
        raise RuntimeError("finality owner startup trust is incomplete")
    key = Ed25519PrivateKey.generate()
    store = pathlib.Path(owner_store_path)
    _initialize_owner_store(
        store,
        owner_id=owner_id,
        owner_public_key_hex=public_key_hex(key),
        pinned_q_sha256=pinned_q_sha256,
        pinned_lab_root_public_key_hex=pinned_lab_root_public_key_hex,
        pinned_acceptance_keys=pinned_acceptance_keys,
    )
    result_queue.put(
        {
            "status": "READY",
            "owner_id": owner_id,
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex(key),
        }
    )
    while True:
        command = command_queue.get()
        if command["kind"] == "STOP":
            return
        if command["kind"] == "ACCEPT":
            if owner_id not in {"O_Q", "O_V"}:
                raise RuntimeError("finality owner cannot write Acceptance")
            status = command["target_status"]
            if not _verify_target_status_for_owner(
                status,
                lab_root_public_key_hex=str(pinned_lab_root_public_key_hex),
                q_sha256=pinned_q_sha256,
            ):
                raise RuntimeError("owner rejected Target evidence")
            receipt = status["receipt"]
            readback = status["readback"]
            if receipt["decision"] != "COMMITTED" or readback["effect_count"] != 1:
                raise RuntimeError("owner cannot accept missing Effect")
            record = sign_record(
                {
                    "schema": "OWNER_NATIVE_ACCEPTANCE_V1",
                    "owner_id": owner_id,
                    "principal_id": f"Principal:{owner_id}",
                    "q_sha256": pinned_q_sha256,
                    "target_receipt_sha256": receipt[
                        "target_receipt_sha256"
                    ],
                    "readback_sha256": readback["target_receipt_sha256"],
                    "effect_id": receipt["effect_id"],
                    "decision": "ACCEPTED_EXACT_EFFECT",
                    "owner_process_id": os.getpid(),
                },
                key=key,
                digest_field="owner_receipt_sha256",
            )
            _append_owner_record(
                store,
                event_type="ACCEPTANCE_APPENDED",
                record=record,
            )
            result_queue.put({"status": "APPENDED", "record": record})
            continue
        if command["kind"] == "FINALIZE":
            if owner_id != "O_P":
                raise RuntimeError("Acceptance owner cannot write finality")
            acceptances = command["acceptances"]
            if {item["owner_id"] for item in acceptances} != {"O_Q", "O_V"}:
                raise RuntimeError("finality requires two exact owners")
            for item in acceptances:
                if not verify_record(
                    item,
                    public_key=pinned_acceptance_keys[item["owner_id"]],
                    digest_field="owner_receipt_sha256",
                ):
                    raise RuntimeError("Acceptance signature invalid")
                if item["q_sha256"] != pinned_q_sha256:
                    raise RuntimeError("Acceptance detached from Q")
            if len({item["effect_id"] for item in acceptances}) != 1:
                raise RuntimeError("Acceptances do not bind one Effect")
            record = sign_record(
                {
                    "schema": "OWNER_NATIVE_FINALITY_V1",
                    "owner_id": "O_P",
                    "principal_id": "Principal:O_P",
                    "q_sha256": pinned_q_sha256,
                    "acceptance_hashes": sorted(
                        item["owner_receipt_sha256"] for item in acceptances
                    ),
                    "effect_id": acceptances[0]["effect_id"],
                    "decision": "FINALIZED_EXACTLY_ONCE",
                    "owner_process_id": os.getpid(),
                },
                key=key,
                digest_field="owner_receipt_sha256",
            )
            _append_owner_record(
                store,
                event_type="FINALITY_APPENDED",
                record=record,
            )
            result_queue.put({"status": "APPENDED", "record": record})
            continue
        raise RuntimeError("unknown owner service command")


def _source_state_audit(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        row = connection.execute("SELECT * FROM operation").fetchone()
        startups = [
            {
                "phase": item["phase"],
                "process_id": item["process_id"],
                "visible_surface": json.loads(item["visible_surface_json"]),
            }
            for item in connection.execute(
                "SELECT * FROM runtime_startups ORDER BY phase"
            )
        ]
        return {
            **dict(row),
            "request": json.loads(row["request_json"]),
            "runtime_startups": startups,
        }
    finally:
        connection.close()


def _ack_drop_proxy_worker(
    *,
    proxy_store_path: str,
    target_result_queue: Any,
    candidate_ack_queue: Any,
    controller_result_queue: Any,
    ready_queue: Any,
    lab_root_public_key_hex: str,
) -> None:
    """Independent proxy consumes Target ACK and durably drops candidate ACK."""

    key = Ed25519PrivateKey.generate()
    store = pathlib.Path(proxy_store_path)
    connection = sqlite_connect(store)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.executescript(
            """
            CREATE TABLE proxy_identity(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                public_key_hex TEXT NOT NULL,
                process_id INTEGER NOT NULL
            );
            CREATE TABLE ack_events(
                event_id TEXT PRIMARY KEY,
                target_receipt_sha256 TEXT NOT NULL UNIQUE,
                event_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO proxy_identity VALUES(1, ?, ?)",
            (public_key_hex(key), os.getpid()),
        )
        connection.commit()
    finally:
        connection.close()
    ready_queue.put(
        {
            "status": "READY",
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex(key),
        }
    )
    target_receipt = target_result_queue.get()
    certificate = target_receipt["target_certificate"]
    if not verify_record(
        certificate,
        public_key=lab_root_public_key_hex,
        digest_field="certificate_sha256",
    ):
        raise RuntimeError("proxy rejected Target certificate")
    if not verify_record(
        target_receipt,
        public_key=certificate["target_public_key_hex"],
        digest_field="target_receipt_sha256",
    ):
        raise RuntimeError("proxy rejected Target receipt")
    proxy_receipt = sign_record(
        {
            "schema": "ACK_DROP_PROXY_RECEIPT_V1",
            "event_id": "ack-drop-" + uuid.uuid4().hex,
            "target_receipt_sha256": target_receipt[
                "target_receipt_sha256"
            ],
            "target_decision": target_receipt["decision"],
            "candidate_ack_channel_configured": True,
            "candidate_ack_delivered": False,
            "proxy_process_id": os.getpid(),
        },
        key=key,
        digest_field="proxy_receipt_sha256",
    )
    connection = sqlite_connect(store)
    try:
        connection.execute(
            "INSERT INTO ack_events VALUES(?, ?, ?)",
            (
                proxy_receipt["event_id"],
                target_receipt["target_receipt_sha256"],
                canonical_bytes(proxy_receipt).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    # Deliberately do not put anything on candidate_ack_queue.
    controller_result_queue.put(
        {"target_receipt": target_receipt, "proxy_receipt": proxy_receipt}
    )


def _proxy_store_audit(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        identity = dict(connection.execute("SELECT * FROM proxy_identity").fetchone())
        rows = list(connection.execute("SELECT * FROM ack_events"))
        return {
            "identity": identity,
            "events": [json.loads(row["event_json"]) for row in rows],
            "event_count": len(rows),
        }
    finally:
        connection.close()


def run_world(
    *,
    role: str,
    world_dir: pathlib.Path,
    candidate_payload: Mapping[str, Any],
    initial_authority: Mapping[str, Any],
    revocation: Mapping[str, Any] | None,
    authority_public_key_hex: str,
    lab_root_public_key_hex: str,
    lab_registry_command_queue: Any,
    lab_registry_result_queue: Any,
    candidate_visible_state_path: pathlib.Path,
) -> dict[str, Any]:
    if role not in {"S", "R", "U"}:
        raise ValueError("role must be S, R or U")
    if role == "R" and revocation is None:
        raise ValueError("R requires an Authority revocation record")
    world_dir.mkdir(parents=True, exist_ok=False)
    context = mp.get_context("spawn")
    controller_key = Ed25519PrivateKey.generate()
    target_db = world_dir / "target-native.sqlite3"
    source_state = pathlib.Path(candidate_visible_state_path)
    source_state.parent.mkdir(parents=True, exist_ok=True)
    if source_state.exists():
        raise RuntimeError("candidate-visible state path was not isolated between twins")
    write_json(world_dir / "candidate-initial-payload.json", candidate_payload)

    command_queue = context.Queue()
    target_to_proxy_queue = context.Queue()
    status_response_queue = context.Queue()
    control_response_queue = context.Queue()
    ready_queue = context.Queue()
    target = context.Process(
        target=_target_worker,
        kwargs={
            "db_path": str(target_db),
            "command_queue": command_queue,
            "execute_result_queue": target_to_proxy_queue,
            "status_response_queue": status_response_queue,
            "control_response_queue": control_response_queue,
            "ready_queue": ready_queue,
            "initial_authority": initial_authority,
            "authority_public_key_hex": authority_public_key_hex,
            "lab_root_public_key_hex": lab_root_public_key_hex,
            "q_sha256": candidate_payload["q_sha256"],
        },
        name="target-reference-monitor-" + uuid.uuid4().hex[:12],
    )
    target.start()
    target_csr = ready_queue.get(timeout=20)
    if target_csr.get("status") != "CERTIFICATE_REQUEST":
        raise RuntimeError("Target did not generate its own key")
    lab_registry_command_queue.put(
        {
            "kind": "SIGN_TARGET_CERTIFICATE",
            "target_public_key_hex": target_csr["target_public_key_hex"],
            "q_sha256": candidate_payload["q_sha256"],
        }
    )
    target_certificate = lab_registry_result_queue.get(timeout=20)["certificate"]
    command_queue.put(
        {"kind": "INSTALL_CERTIFICATE", "target_certificate": target_certificate}
    )
    target_ready = ready_queue.get(timeout=20)
    if target_ready.get("status") != "READY":
        raise RuntimeError("Target did not initialize its native store")

    candidate_ack_queue = context.Queue()
    proxy_result_queue = context.Queue()
    proxy_ready_queue = context.Queue()
    proxy_store = world_dir / "ack-drop-proxy.sqlite3"
    proxy = context.Process(
        target=_ack_drop_proxy_worker,
        kwargs={
            "proxy_store_path": str(proxy_store),
            "target_result_queue": target_to_proxy_queue,
            "candidate_ack_queue": candidate_ack_queue,
            "controller_result_queue": proxy_result_queue,
            "ready_queue": proxy_ready_queue,
            "lab_root_public_key_hex": lab_root_public_key_hex,
        },
        name="independent-ack-drop-proxy",
    )
    proxy.start()
    proxy_ready = proxy_ready_queue.get(timeout=20)

    fence_receipt = None
    if role == "R":
        assert revocation is not None
        command_queue.put({"kind": "APPLY_AUTHORITY", "record": revocation})
        fence_receipt = control_response_queue.get(timeout=20)
        if fence_receipt["decision"] != "FENCE_ADVANCED":
            raise RuntimeError("Target did not durably advance revoked fence")

    prepared = context.Event()
    release = context.Event()
    source = context.Process(
        target=_candidate_worker,
        kwargs={
            "phase": "SOURCE",
            "payload": candidate_payload,
            "source_state_path": str(source_state),
            "command_queue": command_queue,
            "status_response_queue": status_response_queue,
            "candidate_ack_queue": candidate_ack_queue,
            "prepared_event": prepared,
            "release_event": release,
            "recovery_result_queue": None,
        },
        name="candidate-source-runtime",
    )
    start_with_sanitized_environment(source)
    if not prepared.wait(timeout=20):
        raise RuntimeError("candidate source did not reach prepared boundary")

    schedule = sign_record(
        {
            "schema": "CONTROLLER_PRIVATE_TWIN_SCHEDULE_V1",
            "role": role,
            "action_before_ingress": (
                "KEEP_TARGET_CONSUMED_FENCE"
                if role == "S"
                else (
                    "APPLY_SIGNED_REVOCATION_AND_WAIT_FOR_TARGET_ACK"
                    if role == "R"
                    else "AUTHORITY_REVOKED_TARGET_NOT_ACKED_NOT_SCORED"
                )
            ),
            "candidate_payload_sha256": sha256_value(candidate_payload),
            "request_sha256": sha256_value(candidate_payload["request"]),
            "controller_process_id": os.getpid(),
        },
        key=controller_key,
        digest_field="controller_receipt_sha256",
    )
    release.set()
    proxy_delivery = proxy_result_queue.get(timeout=20)
    execute_receipt = proxy_delivery["target_receipt"]
    ack_drop_receipt = proxy_delivery["proxy_receipt"]
    proxy.join(timeout=20)
    if proxy.exitcode != 0:
        raise RuntimeError("ACK-drop proxy failed")
    source.terminate()
    source.join(timeout=20)
    if source.is_alive():
        source.kill()
        source.join(timeout=5)
        raise RuntimeError("candidate source did not terminate")
    if source.exitcode != -signal.SIGTERM:
        raise RuntimeError(f"candidate source exit was not SIGTERM: {source.exitcode}")
    termination = sign_record(
        {
            "schema": "CONTROLLER_TERMINATION_RECEIPT_V1",
            "source_process_id": source.pid,
            "source_exitcode": source.exitcode,
            "signal": "SIGTERM",
            "ack_channel_present": True,
            "ack_drop_proxy_receipt_sha256": ack_drop_receipt[
                "proxy_receipt_sha256"
            ],
            "target_receipt_sha256": execute_receipt["target_receipt_sha256"],
            "controller_process_id": os.getpid(),
        },
        key=controller_key,
        digest_field="controller_receipt_sha256",
    )

    recovery_result_queue = context.Queue()
    recovery = context.Process(
        target=_candidate_worker,
        kwargs={
            "phase": "RECOVERY",
            "payload": candidate_payload,
            "source_state_path": str(source_state),
            "command_queue": command_queue,
            "status_response_queue": status_response_queue,
            "candidate_ack_queue": candidate_ack_queue,
            "prepared_event": None,
            "release_event": None,
            "recovery_result_queue": recovery_result_queue,
        },
        name="candidate-recovery-runtime",
    )
    start_with_sanitized_environment(recovery)
    recovery_result = recovery_result_queue.get(timeout=20)
    recovery.join(timeout=20)
    if recovery.exitcode != 0:
        raise RuntimeError("candidate recovery failed")

    acceptances: list[dict[str, Any]] = []
    finality: dict[str, Any] | None = None
    owner_process_ids: dict[str, int] = {}
    owner_public_keys: dict[str, str] = {}
    owner_dir = world_dir / "owners"
    owner_dir.mkdir()
    owner_paths = {
        owner: owner_dir / (owner.lower() + ".sqlite3")
        for owner in ("O_Q", "O_V", "O_P")
    }
    owner_services: dict[str, tuple[Any, Any, mp.Process]] = {}

    def start_owner(
        owner_id: str,
        *,
        pinned_lab_root: str | None,
        pinned_acceptance_keys: Mapping[str, str],
    ) -> None:
        path = owner_paths[owner_id]
        owner_command_queue = context.Queue()
        owner_result_queue = context.Queue()
        process = context.Process(
            target=_owner_service_worker,
            kwargs={
                "owner_id": owner_id,
                "owner_store_path": str(path),
                "pinned_q_sha256": candidate_payload["q_sha256"],
                "pinned_lab_root_public_key_hex": pinned_lab_root,
                "pinned_acceptance_keys": dict(pinned_acceptance_keys),
                "command_queue": owner_command_queue,
                "result_queue": owner_result_queue,
            },
            name="owner-native-service-" + owner_id,
        )
        process.start()
        ready = owner_result_queue.get(timeout=20)
        if ready.get("status") != "READY":
            raise RuntimeError(f"{owner_id} native service did not initialize")
        owner_process_ids[owner_id] = int(ready["process_id"])
        owner_public_keys[owner_id] = ready["public_key_hex"]
        owner_services[owner_id] = (
            owner_command_queue,
            owner_result_queue,
            process,
        )
    for owner_id in ("O_Q", "O_V"):
        start_owner(
            owner_id,
            pinned_lab_root=candidate_payload["lab_root_public_key_hex"],
            pinned_acceptance_keys={},
        )
    start_owner(
        "O_P",
        pinned_lab_root=None,
        pinned_acceptance_keys={
            owner: owner_public_keys[owner] for owner in ("O_Q", "O_V")
        },
    )
    if recovery_result["disposition"] == "RECOVERED_COMMITTED_NO_REPLAY":
        for owner_id in ("O_Q", "O_V"):
            owner_services[owner_id][0].put(
                {
                    "kind": "ACCEPT",
                    "target_status": recovery_result["target_status"],
                }
            )
        for owner_id in ("O_Q", "O_V"):
            response = owner_services[owner_id][1].get(timeout=20)
            if response.get("status") != "APPENDED":
                raise RuntimeError(f"{owner_id} did not append Acceptance")
            acceptances.append(response["record"])
        owner_services["O_P"][0].put(
            {
                "kind": "FINALIZE",
                "acceptances": acceptances,
            }
        )
        response = owner_services["O_P"][1].get(timeout=20)
        if response.get("status") != "APPENDED":
            raise RuntimeError("O_P did not append finality")
        finality = response["record"]
    for owner_id, (owner_command, _, process) in owner_services.items():
        owner_command.put({"kind": "STOP"})
        process.join(timeout=20)
        if process.exitcode != 0:
            raise RuntimeError(f"{owner_id} native service failed")

    command_queue.put({"kind": "AUDIT"})
    target_audit = control_response_queue.get(timeout=20)
    command_queue.put({"kind": "STOP"})
    control_response_queue.get(timeout=20)
    target.join(timeout=20)
    if target.exitcode != 0:
        raise RuntimeError("Target reference monitor failed")
    source_audit = _source_state_audit(source_state)
    source_state_artifact = world_dir / "candidate-source-state.sqlite3"
    source_state.replace(source_state_artifact)
    source_state = source_state_artifact
    owner_store_audits = {
        owner: _owner_store_audit(path) for owner, path in owner_paths.items()
    }
    world = {
        "schema": "AUTHORITY_EPOCH_WORLD_ARTIFACT_V1",
        "role": role,
        "candidate_payload": candidate_payload,
        "candidate_payload_sha256": sha256_value(candidate_payload),
        "request_sha256": sha256_value(candidate_payload["request"]),
        "target_certificate": target_certificate,
        "key_registry": {
            "authority_public_key_hex": authority_public_key_hex,
            "lab_root_public_key_hex": candidate_payload["lab_root_public_key_hex"],
            "target_public_key_hex": target_ready["target_public_key_hex"],
            "controller_public_key_hex": public_key_hex(controller_key),
            "proxy_public_key_hex": proxy_ready["public_key_hex"],
            "owner_public_keys": owner_public_keys,
        },
        "processes": {
            "target": target_ready["target_process_id"],
            "candidate_source": source.pid,
            "candidate_source_exitcode": source.exitcode,
            "candidate_recovery": recovery.pid,
            "candidate_recovery_exitcode": recovery.exitcode,
            "owners": owner_process_ids,
            "ack_drop_proxy": proxy_ready["process_id"],
        },
        "controller_schedule": schedule,
        "fence_advanced_receipt": fence_receipt,
        "target_execute_receipt": execute_receipt,
        "ack_drop_proxy_receipt": ack_drop_receipt,
        "controller_termination_receipt": termination,
        "candidate_recovery_result": recovery_result,
        "acceptances": sorted(acceptances, key=lambda item: item["owner_id"]),
        "finality": finality,
        "target_audit": target_audit,
        "owner_store_audits": owner_store_audits,
        "proxy_store_audit": _proxy_store_audit(proxy_store),
        "source_state_audit": source_audit,
        "files": {
            "target_db": target_db.name,
            "target_db_sha256": file_sha256(target_db),
            "proxy_db": proxy_store.name,
            "proxy_db_sha256": file_sha256(proxy_store),
            "source_state_db": source_state.name,
            "source_state_db_sha256": file_sha256(source_state),
            "owner_dbs": {
                owner: str(path.relative_to(world_dir))
                for owner, path in owner_paths.items()
            },
            "owner_db_sha256": {
                owner: file_sha256(path) for owner, path in owner_paths.items()
            },
        },
        "claim_boundary": "LOCAL_SYNTHETIC_AUTHORITY_EPOCH_DISCRIMINATOR",
    }
    world["world_artifact_sha256"] = sha256_value(world)
    write_json(world_dir / "WORLD-ARTIFACT.json", world)
    return world


def run_twin(output_root: pathlib.Path) -> dict[str, Any]:
    output_root = pathlib.Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / ("twin-" + uuid.uuid4().hex)
    run_dir.mkdir(parents=True, exist_ok=False)

    context = mp.get_context("spawn")
    authority_store = run_dir / "authority-native.sqlite3"
    lab_registry_store = run_dir / "lab-key-registry.sqlite3"
    lab_commands = context.Queue()
    lab_results = context.Queue()
    lab_registry = context.Process(
        target=_lab_registry_worker,
        args=(lab_commands, lab_results, str(lab_registry_store)),
        name="independent-lab-key-registry",
    )
    lab_registry.start()
    lab_ready = lab_results.get(timeout=20)
    if lab_ready.get("status") != "READY":
        raise RuntimeError("lab key registry did not initialize")
    lab_root_public_key = lab_ready["public_key_hex"]
    authority_commands = context.Queue()
    authority_results = context.Queue()
    authority = context.Process(
        target=_authority_worker,
        args=(
            authority_commands,
            authority_results,
            str(authority_store),
            lab_root_public_key,
        ),
        name="principal-authority-service",
    )
    authority.start()
    authority_ready = authority_results.get(timeout=20)
    if authority_ready.get("status") != "READY":
        raise RuntimeError("Principal/Authority service did not initialize")
    authority_public_key = authority_ready["public_key_hex"]
    task = exact_task()
    q_sha256 = sha256_value(task)
    delegation_body = {
        "schema": "AUTHORITY_DELEGATION_V1",
        "delegation_id": "delegation-ce001-authority-epoch-twin",
        "principal_id": "Principal:VenueV",
        "actor_id": ACTOR_ID,
        "q_sha256": q_sha256,
        "object_id": OBJECT_ID,
        "target_id": TARGET_ID,
        "operation": OPERATION,
        "epoch": 1,
        "status": "CURRENT",
        "valid_from_logical_minute": 0,
        "valid_until_logical_minute": 90,
        "prev_authority_head_sha256": GENESIS,
        "issuer_process_id": None,
    }
    authority_commands.put({"kind": "ISSUE_DELEGATION", "body": delegation_body})
    delegation_result = authority_results.get(timeout=20)
    initial_authority = delegation_result["record"]
    request = {
        "schema": "EXACT_EFFECT_REQUEST_V1",
        "request_id": "request-ce001-authority-epoch-twin",
        "q_sha256": q_sha256,
        "object_id": OBJECT_ID,
        "target_id": TARGET_ID,
        "operation": OPERATION,
        "actor_id": ACTOR_ID,
        "presented_epoch": 1,
        "commit_logical_minute": 10,
        "delegation": initial_authority,
        "desired_state": exact_target_state(),
    }
    candidate_payload = {
        "schema": "WAVE024_CANDIDATE_PUBLIC_INPUT_V1",
        "candidate_artifact": "twin_runtime.py",
        "candidate_artifact_sha256": file_sha256(HERE / "twin_runtime.py"),
        "task": task,
        "q_sha256": q_sha256,
        "authority_root_public_key_hex": authority_public_key,
        "lab_root_public_key_hex": lab_root_public_key,
        "request": request,
    }
    write_json(run_dir / "FROZEN-CANDIDATE-PAYLOAD.json", candidate_payload)
    write_json(run_dir / "AUTHORITY-DELEGATION.json", initial_authority)
    candidate_visible_state_path = (
        run_dir / "candidate-visible-sandbox" / "operation-state.sqlite3"
    )

    # S is completed while the Authority service still has only the current
    # delegation.  The signed revocation is created afterwards.  This keeps S
    # distinct from U instead of merely relabelling the same revoked-but-not-
    # consumed world.
    world_s = run_world(
        role="S",
        world_dir=run_dir / "world-s",
        candidate_payload=candidate_payload,
        initial_authority=initial_authority,
        revocation=None,
        authority_public_key_hex=authority_public_key,
        lab_root_public_key_hex=lab_root_public_key,
        lab_registry_command_queue=lab_commands,
        lab_registry_result_queue=lab_results,
        candidate_visible_state_path=candidate_visible_state_path,
    )
    authority_commands.put(
        {
            "kind": "REVOKE",
            "prior": initial_authority,
            "experiment_predecessor_s_target_receipt": world_s[
                "target_execute_receipt"
            ],
        }
    )
    revocation_result = authority_results.get(timeout=20)
    revocation = revocation_result["record"]
    write_json(run_dir / "AUTHORITY-REVOCATION.json", revocation)
    authority_commands.put({"kind": "STOP"})
    authority.join(timeout=20)
    if authority.exitcode != 0:
        raise RuntimeError("Principal/Authority process failed")
    world_r = run_world(
        role="R",
        world_dir=run_dir / "world-r",
        candidate_payload=candidate_payload,
        initial_authority=initial_authority,
        revocation=revocation,
        authority_public_key_hex=authority_public_key,
        lab_root_public_key_hex=lab_root_public_key,
        lab_registry_command_queue=lab_commands,
        lab_registry_result_queue=lab_results,
        candidate_visible_state_path=candidate_visible_state_path,
    )
    world_u = run_world(
        role="U",
        world_dir=run_dir / "world-u",
        candidate_payload=candidate_payload,
        initial_authority=initial_authority,
        revocation=revocation,
        authority_public_key_hex=authority_public_key,
        lab_root_public_key_hex=lab_root_public_key,
        lab_registry_command_queue=lab_commands,
        lab_registry_result_queue=lab_results,
        candidate_visible_state_path=candidate_visible_state_path,
    )
    candidate_visible_state_path.parent.rmdir()
    lab_commands.put({"kind": "STOP"})
    lab_registry.join(timeout=20)
    if lab_registry.exitcode != 0:
        raise RuntimeError("lab key registry failed")
    visible_s = [
        item["visible_surface"]
        for item in world_s["source_state_audit"]["runtime_startups"]
    ]
    visible_r = [
        item["visible_surface"]
        for item in world_r["source_state_audit"]["runtime_startups"]
    ]
    visible_u = [
        item["visible_surface"]
        for item in world_u["source_state_audit"]["runtime_startups"]
    ]
    twin = {
        "schema": "WAVE024_AUTHORITY_EPOCH_TWIN_ARTIFACT_V1",
        "status": "RUN_COMPLETED_PENDING_INDEPENDENT_EVALUATION",
        "run_dir": str(run_dir),
        "question": "QUESTION.md",
        "candidate_artifact_sha256": candidate_payload["candidate_artifact_sha256"],
        "authority_process": {
            "process_id": delegation_result["process_id"],
            "exitcode": authority.exitcode,
        },
        "lab_registry_process": {
            "process_id": lab_ready["process_id"],
            "exitcode": lab_registry.exitcode,
        },
        "authority_public_key_hex": authority_public_key,
        "lab_root_public_key_hex": lab_root_public_key,
        "authority_store": {
            "path": authority_store.name,
            "sha256": file_sha256(authority_store),
        },
        "lab_registry_store": {
            "path": lab_registry_store.name,
            "sha256": file_sha256(lab_registry_store),
        },
        "initial_authority": initial_authority,
        "revocation": revocation,
        "candidate_payload_sha256": sha256_value(candidate_payload),
        "request_sha256": sha256_value(request),
        "authority_timing": {
            "S": "COMPLETED_BEFORE_AUTHORITY_REVOCATION_RECORD",
            "R": "TARGET_ACKED_MATCHING_REVOCATION_BEFORE_INGRESS",
            "U": "AUTHORITY_REVOCATION_EXISTS_TARGET_NOT_ACKED_NOT_SCORED",
            "s_target_receipt_sha256": world_s["target_execute_receipt"][
                "target_receipt_sha256"
            ],
            "revocation_head_sha256": revocation["authority_head_sha256"],
        },
        "pre_response_isomorphism": {
            "candidate_payload_raw_equal": canonical_bytes(world_s["candidate_payload"])
            == canonical_bytes(world_r["candidate_payload"]),
            "request_raw_equal": canonical_bytes(
                world_s["candidate_payload"]["request"]
            )
            == canonical_bytes(world_r["candidate_payload"]["request"]),
            "recorded_candidate_startup_surface_equal_s_r": (
                canonical_bytes(visible_s) == canonical_bytes(visible_r)
            ),
            "recorded_candidate_startup_surface_equal_s_r_u": (
                canonical_bytes(visible_s)
                == canonical_bytes(visible_r)
                == canonical_bytes(visible_u)
            ),
            "first_candidate_visible_lawful_divergence": (
                "TARGET_STATUS_READBACK_AFTER_ACK_LOSS"
            ),
            "hostile_same_user_enumeration_resistance": "NOT_ESTABLISHED",
        },
        "worlds": {
            "S": "world-s/WORLD-ARTIFACT.json",
            "R": "world-r/WORLD-ARTIFACT.json",
            "U": "world-u/WORLD-ARTIFACT.json",
        },
        "world_artifact_sha256": {
            "S": world_s["world_artifact_sha256"],
            "R": world_r["world_artifact_sha256"],
            "U": world_u["world_artifact_sha256"],
        },
        "results": {
            "S": {
                "decision": world_s["target_execute_receipt"]["decision"],
                "effect_count": world_s["target_audit"]["effect_count"],
                "acceptance_count": len(world_s["acceptances"]),
                "finality_count": 1 if world_s["finality"] else 0,
                "retry_effect_count": world_s["source_state_audit"][
                    "retry_execute_count"
                ],
            },
            "R": {
                "decision": world_r["target_execute_receipt"]["decision"],
                "effect_count": world_r["target_audit"]["effect_count"],
                "acceptance_count": len(world_r["acceptances"]),
                "finality_count": 1 if world_r["finality"] else 0,
                "retry_effect_count": world_r["source_state_audit"][
                    "retry_execute_count"
                ],
                "authority_rejection_count": world_r["target_audit"][
                    "refusal_count"
                ],
            },
            "U": {
                "scoring_status": "CONCURRENT_OR_UNORDERED/NOT_SCORED",
                "target_raw_decision": world_u["target_execute_receipt"][
                    "decision"
                ],
                "target_consumed_matching_fence_before_ingress": False,
                "authority_revoke_record_exists": True,
                "target_matching_fence_ack_exists": False,
                "effect_count_not_used_for_s_or_r_inference": world_u[
                    "target_audit"
                ]["effect_count"],
            },
        },
        "claim_boundary": {
            "pending_independent_evaluation": [
                "CL-024-TARGET-CONSUMED-AUTHORITY-FENCE",
                "CL-024-EXACTLY-ONCE-RECOVERY",
                "CL-024-NATIVE-POSTCONDITIONS",
                "CL-024-ISOMORPHIC-BLINDNESS",
            ],
            "explicit_not_tested": [
                "CL-024-GLOBAL-AUTHORITY-CURRENTNESS",
                "TARGET_PROCESS_RESTART_PERSISTENCE",
                "HOSTILE_SAME_UID_BLINDNESS_AND_WRITE_RESISTANCE",
                "EXTERNAL_APPEND_ONLY_ROOT_ANCHOR",
            ],
            "not_claimed": [
                "LEGAL_AUTHORITY",
                "PHYSICAL_EFFECT",
                "HOSTILE_SAME_USER_RESISTANCE",
                "PRODUCTION_RELIABILITY",
                "A1_A5_COMPARISON_OR_WINNER",
                "V1_V2_COMPLETE_SOLUTION",
            ],
        },
        "artifact_hash_semantics": (
            "CANONICAL_JSON_SHA256_AFTER_REMOVING_TWIN_ARTIFACT_SHA256_FIELD"
        ),
    }
    twin["twin_artifact_sha256"] = sha256_value(twin)
    write_json(run_dir / "TWIN-ARTIFACT.json", twin)
    return twin


__all__ = [
    "canonical_bytes",
    "exact_target_state",
    "exact_task",
    "file_sha256",
    "run_twin",
    "sha256_value",
    "verify_record",
]
