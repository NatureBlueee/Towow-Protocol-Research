"""Atomic target mutation ledger for the Wave 015 runner foundation.

The ledger is deliberately small and uses mature SQLite transactions.  It is
the sole mutation path for its authoritative *digital* target state.  A
receipt proves what this ledger committed under its trust boundary; it does
not prove a physical effect, legal authority, or resistance to an attacker
that can rewrite the database and its embedded authentication key.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Mapping


COMMITTED = "COMMITTED"
CONFLICT = "CONFLICT"
ALREADY_SATISFIED = "ALREADY_SATISFIED"
REPLAY_REJECTED = "REPLAY_REJECTED"

_TERMINAL_DECISIONS = {
    COMMITTED,
    CONFLICT,
    ALREADY_SATISFIED,
    REPLAY_REJECTED,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _without(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    excluded = set(keys)
    return {key: item for key, item in value.items() if key not in excluded}


class TargetOperationLedger:
    """Single-writer contract implemented with serializable SQLite writes.

    Every public method opens its own connection.  ``BEGIN IMMEDIATE`` makes
    the state check, one-shot capability consumption, mutation, provenance
    event, and receipt insertion one atomic write transaction.
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        ledger_id: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.db_path = Path(db_path)
        self.timeout_seconds = timeout_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize(ledger_id)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self, requested_ledger_id: str | None) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    ledger_id TEXT NOT NULL UNIQUE,
                    authentication_key_hex TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS targets (
                    target_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    state_sha256 TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    last_commit_id TEXT NOT NULL,
                    last_commit_actor_id TEXT NOT NULL,
                    last_request_sha256 TEXT
                );

                CREATE TABLE IF NOT EXISTS capabilities (
                    capability_id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    allowed_state_sha256 TEXT NOT NULL,
                    consumed_by_request_id TEXT,
                    consumed_by_receipt_id TEXT,
                    FOREIGN KEY (target_id) REFERENCES targets(target_id)
                );

                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    request_sha256 TEXT NOT NULL,
                    receipt_id TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    receipt_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commit_events (
                    commit_id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    pre_version INTEGER NOT NULL,
                    post_version INTEGER NOT NULL,
                    pre_state_sha256 TEXT NOT NULL,
                    post_state_sha256 TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS readbacks (
                    readback_id TEXT PRIMARY KEY,
                    receipt_id TEXT NOT NULL,
                    readback_json TEXT NOT NULL
                );
                """
            )
            row = connection.execute(
                "SELECT ledger_id, authentication_key_hex FROM metadata "
                "WHERE singleton = 1"
            ).fetchone()
            if row is None:
                chosen_id = requested_ledger_id or f"target-ledger-{uuid.uuid4().hex}"
                connection.execute(
                    "INSERT INTO metadata(singleton, ledger_id, "
                    "authentication_key_hex) VALUES (1, ?, ?)",
                    (chosen_id, secrets.token_hex(32)),
                )
            elif requested_ledger_id is not None and row["ledger_id"] != requested_ledger_id:
                raise ValueError("database already belongs to a different ledger_id")

    def _metadata(self, connection: sqlite3.Connection) -> tuple[str, bytes]:
        row = connection.execute(
            "SELECT ledger_id, authentication_key_hex FROM metadata "
            "WHERE singleton = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("ledger metadata missing")
        return row["ledger_id"], bytes.fromhex(row["authentication_key_hex"])

    @property
    def ledger_id(self) -> str:
        with self._connect() as connection:
            ledger_id, _ = self._metadata(connection)
            return ledger_id

    def initialize_target(self, target_id: str, initial_state: Any) -> dict[str, Any]:
        """Create the authoritative target at version zero."""

        state_json = _canonical_bytes(initial_state).decode("utf-8")
        state_hash = _sha256(initial_state)
        genesis_id = f"genesis-{uuid.uuid4().hex}"
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO targets(
                        target_id, state_json, state_sha256, version,
                        last_commit_id, last_commit_actor_id, last_request_sha256
                    ) VALUES (?, ?, ?, 0, ?, 'SYSTEM_GENESIS', NULL)
                    """,
                    (target_id, state_json, state_hash, genesis_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {
            "target_id": target_id,
            "state": initial_state,
            "state_sha256": state_hash,
            "version": 0,
            "last_commit_id": genesis_id,
            "last_commit_actor_id": "SYSTEM_GENESIS",
        }

    def issue_capability(
        self,
        *,
        capability_id: str,
        target_id: str,
        actor_id: str,
        allowed_state: Any,
        operation: str = "SET_STATE",
    ) -> dict[str, Any]:
        """Provision an exact-target, exact-actor, exact-state one-shot grant.

        Capability issuance is a trusted setup act in this foundation.  This
        class does not decide whether the issuer had legal authority.
        """

        allowed_hash = _sha256(allowed_state)
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                target = connection.execute(
                    "SELECT target_id FROM targets WHERE target_id = ?",
                    (target_id,),
                ).fetchone()
                if target is None:
                    raise KeyError(f"unknown target: {target_id}")
                connection.execute(
                    """
                    INSERT INTO capabilities(
                        capability_id, target_id, actor_id, operation,
                        allowed_state_sha256
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        capability_id,
                        target_id,
                        actor_id,
                        operation,
                        allowed_hash,
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {
            "capability_id": capability_id,
            "target_id": target_id,
            "actor_id": actor_id,
            "operation": operation,
            "allowed_state_sha256": allowed_hash,
            "one_shot": True,
        }

    def _request_body(
        self,
        *,
        ledger_id: str,
        target_id: str,
        actor_id: str,
        request_id: str,
        capability_id: str,
        expected_version: int,
        desired_state: Any,
    ) -> dict[str, Any]:
        return {
            "schema": "TARGET_MUTATION_REQUEST_V1",
            "ledger_id": ledger_id,
            "target_id": target_id,
            "actor_id": actor_id,
            "request_id": request_id,
            "capability_id": capability_id,
            "operation": "SET_STATE",
            "expected_version": expected_version,
            "desired_state": desired_state,
            "desired_state_sha256": _sha256(desired_state),
        }

    def _authenticate(
        self,
        value: Mapping[str, Any],
        key: bytes,
        *,
        excluded_field: str,
    ) -> str:
        return hmac.new(
            key,
            _canonical_bytes(_without(value, excluded_field)),
            hashlib.sha256,
        ).hexdigest()

    def _new_receipt(
        self,
        *,
        ledger_id: str,
        authentication_key: bytes,
        request: Mapping[str, Any],
        state: sqlite3.Row,
        decision: str,
        reason: str,
        receipt_id: str,
        mutation_applied: bool,
        post_state: Any | None = None,
        post_state_sha256: str | None = None,
        post_version: int | None = None,
        commit_id: str | None = None,
        commit_actor_id: str | None = None,
    ) -> dict[str, Any]:
        if decision not in _TERMINAL_DECISIONS:
            raise ValueError(f"unsupported decision: {decision}")
        pre_state = json.loads(state["state_json"])
        receipt = {
            "schema": "TARGET_MUTATION_RECEIPT_V1",
            "ledger_id": ledger_id,
            "receipt_id": receipt_id,
            "decision": decision,
            "reason": reason,
            "mutation_applied": mutation_applied,
            "request_id": request["request_id"],
            "request_sha256": _sha256(request),
            "actor_id": request["actor_id"],
            "capability_id": request["capability_id"],
            "target_id": request["target_id"],
            "operation": request["operation"],
            "expected_version": request["expected_version"],
            "pre_state": pre_state,
            "pre_state_sha256": state["state_sha256"],
            "pre_version": state["version"],
            "post_state": pre_state if post_state is None else post_state,
            "post_state_sha256": (
                state["state_sha256"]
                if post_state_sha256 is None
                else post_state_sha256
            ),
            "post_version": (
                state["version"] if post_version is None else post_version
            ),
            # For a non-mutating result this identifies the commit that
            # already owns the observed state; it is never attributed to the
            # current actor because mutation_applied is false.
            "commit_id": state["last_commit_id"] if commit_id is None else commit_id,
            "commit_actor_id": (
                state["last_commit_actor_id"]
                if commit_actor_id is None
                else commit_actor_id
            ),
        }
        receipt["receipt_sha256"] = _sha256(receipt)
        receipt["receipt_auth_hex"] = self._authenticate(
            receipt,
            authentication_key,
            excluded_field="receipt_auth_hex",
        )
        return receipt

    def apply(
        self,
        *,
        target_id: str,
        actor_id: str,
        request_id: str,
        capability_id: str,
        expected_version: int,
        desired_state: Any,
    ) -> dict[str, Any]:
        """Attempt an exact mutation and return an authenticated receipt."""

        if expected_version < 0:
            raise ValueError("expected_version must be non-negative")

        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                ledger_id, key = self._metadata(connection)
                request = self._request_body(
                    ledger_id=ledger_id,
                    target_id=target_id,
                    actor_id=actor_id,
                    request_id=request_id,
                    capability_id=capability_id,
                    expected_version=expected_version,
                    desired_state=desired_state,
                )
                request_hash = _sha256(request)
                prior = connection.execute(
                    "SELECT request_sha256, receipt_id FROM requests "
                    "WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if prior is not None and prior["request_sha256"] == request_hash:
                    stored = connection.execute(
                        "SELECT receipt_json FROM receipts WHERE receipt_id = ?",
                        (prior["receipt_id"],),
                    ).fetchone()
                    if stored is None:
                        raise RuntimeError("idempotency record detached from receipt")
                    connection.commit()
                    return json.loads(stored["receipt_json"])

                state = connection.execute(
                    "SELECT * FROM targets WHERE target_id = ?",
                    (target_id,),
                ).fetchone()
                if state is None:
                    raise KeyError(f"unknown target: {target_id}")

                receipt_id = f"receipt-{uuid.uuid4().hex}"
                if prior is not None:
                    receipt = self._new_receipt(
                        ledger_id=ledger_id,
                        authentication_key=key,
                        request=request,
                        state=state,
                        decision=REPLAY_REJECTED,
                        reason="REQUEST_ID_REBOUND",
                        receipt_id=receipt_id,
                        mutation_applied=False,
                    )
                    self._insert_receipt(connection, receipt)
                    connection.commit()
                    return receipt

                capability = connection.execute(
                    "SELECT * FROM capabilities WHERE capability_id = ?",
                    (capability_id,),
                ).fetchone()
                capability_reason: str | None = None
                if capability is None:
                    capability_reason = "CAPABILITY_UNKNOWN"
                elif capability["target_id"] != target_id:
                    capability_reason = "CAPABILITY_TARGET_MISMATCH"
                elif capability["actor_id"] != actor_id:
                    capability_reason = "CAPABILITY_ACTOR_MISMATCH"
                elif capability["operation"] != "SET_STATE":
                    capability_reason = "CAPABILITY_OPERATION_MISMATCH"
                elif capability["allowed_state_sha256"] != request[
                    "desired_state_sha256"
                ]:
                    capability_reason = "CAPABILITY_STATE_MISMATCH"
                elif capability["consumed_by_request_id"] is not None:
                    capability_reason = "CAPABILITY_ALREADY_CONSUMED"

                if capability_reason is not None:
                    receipt = self._new_receipt(
                        ledger_id=ledger_id,
                        authentication_key=key,
                        request=request,
                        state=state,
                        decision=REPLAY_REJECTED,
                        reason=capability_reason,
                        receipt_id=receipt_id,
                        mutation_applied=False,
                    )
                    self._insert_request_and_receipt(
                        connection, request_id, request_hash, receipt
                    )
                    connection.commit()
                    return receipt

                desired_hash = request["desired_state_sha256"]
                if state["state_sha256"] == desired_hash:
                    receipt = self._new_receipt(
                        ledger_id=ledger_id,
                        authentication_key=key,
                        request=request,
                        state=state,
                        decision=ALREADY_SATISFIED,
                        reason="TARGET_ALREADY_IN_DESIRED_STATE",
                        receipt_id=receipt_id,
                        mutation_applied=False,
                    )
                    self._consume_capability(
                        connection, capability_id, request_id, receipt_id
                    )
                    self._insert_request_and_receipt(
                        connection, request_id, request_hash, receipt
                    )
                    connection.commit()
                    return receipt

                if state["version"] != expected_version:
                    receipt = self._new_receipt(
                        ledger_id=ledger_id,
                        authentication_key=key,
                        request=request,
                        state=state,
                        decision=CONFLICT,
                        reason="EXPECTED_VERSION_MISMATCH",
                        receipt_id=receipt_id,
                        mutation_applied=False,
                    )
                    self._insert_request_and_receipt(
                        connection, request_id, request_hash, receipt
                    )
                    connection.commit()
                    return receipt

                post_version = state["version"] + 1
                post_state_json = _canonical_bytes(desired_state).decode("utf-8")
                commit_id = f"commit-{uuid.uuid4().hex}"
                connection.execute(
                    """
                    UPDATE targets
                    SET state_json = ?, state_sha256 = ?, version = ?,
                        last_commit_id = ?, last_commit_actor_id = ?,
                        last_request_sha256 = ?
                    WHERE target_id = ? AND version = ?
                    """,
                    (
                        post_state_json,
                        desired_hash,
                        post_version,
                        commit_id,
                        actor_id,
                        request_hash,
                        target_id,
                        expected_version,
                    ),
                )
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    raise RuntimeError("CAS lost inside serialized transaction")
                receipt = self._new_receipt(
                    ledger_id=ledger_id,
                    authentication_key=key,
                    request=request,
                    state=state,
                    decision=COMMITTED,
                    reason="TARGET_MUTATION_COMMITTED",
                    receipt_id=receipt_id,
                    mutation_applied=True,
                    post_state=desired_state,
                    post_state_sha256=desired_hash,
                    post_version=post_version,
                    commit_id=commit_id,
                    commit_actor_id=actor_id,
                )
                connection.execute(
                    """
                    INSERT INTO commit_events(
                        commit_id, target_id, actor_id, request_id,
                        request_sha256, capability_id, pre_version,
                        post_version, pre_state_sha256, post_state_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        commit_id,
                        target_id,
                        actor_id,
                        request_id,
                        request_hash,
                        capability_id,
                        state["version"],
                        post_version,
                        state["state_sha256"],
                        desired_hash,
                    ),
                )
                self._consume_capability(
                    connection, capability_id, request_id, receipt_id
                )
                self._insert_request_and_receipt(
                    connection, request_id, request_hash, receipt
                )
                connection.commit()
                return receipt
            except Exception:
                connection.rollback()
                raise

    def _consume_capability(
        self,
        connection: sqlite3.Connection,
        capability_id: str,
        request_id: str,
        receipt_id: str,
    ) -> None:
        connection.execute(
            """
            UPDATE capabilities
            SET consumed_by_request_id = ?, consumed_by_receipt_id = ?
            WHERE capability_id = ? AND consumed_by_request_id IS NULL
            """,
            (request_id, receipt_id, capability_id),
        )
        if connection.execute("SELECT changes()").fetchone()[0] != 1:
            raise RuntimeError("one-shot capability consumption lost")

    def _insert_receipt(
        self,
        connection: sqlite3.Connection,
        receipt: Mapping[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO receipts(
                receipt_id, request_id, target_id, decision, receipt_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                receipt["receipt_id"],
                receipt["request_id"],
                receipt["target_id"],
                receipt["decision"],
                _canonical_bytes(receipt).decode("utf-8"),
            ),
        )

    def _insert_request_and_receipt(
        self,
        connection: sqlite3.Connection,
        request_id: str,
        request_hash: str,
        receipt: Mapping[str, Any],
    ) -> None:
        self._insert_receipt(connection, receipt)
        connection.execute(
            "INSERT INTO requests(request_id, request_sha256, receipt_id) "
            "VALUES (?, ?, ?)",
            (request_id, request_hash, receipt["receipt_id"]),
        )

    def verify_receipt(self, receipt: Mapping[str, Any]) -> bool:
        """Verify ledger origin, content integrity, and stored receipt identity."""

        try:
            with self._connect() as connection:
                ledger_id, key = self._metadata(connection)
                if receipt.get("ledger_id") != ledger_id:
                    return False
                expected_sha = _sha256(
                    _without(receipt, "receipt_sha256", "receipt_auth_hex")
                )
                if receipt.get("receipt_sha256") != expected_sha:
                    return False
                expected_auth = self._authenticate(
                    receipt,
                    key,
                    excluded_field="receipt_auth_hex",
                )
                if not hmac.compare_digest(
                    str(receipt.get("receipt_auth_hex", "")),
                    expected_auth,
                ):
                    return False
                row = connection.execute(
                    "SELECT receipt_json FROM receipts WHERE receipt_id = ?",
                    (receipt.get("receipt_id"),),
                ).fetchone()
                return row is not None and json.loads(row["receipt_json"]) == dict(
                    receipt
                )
        except (KeyError, TypeError, ValueError):
            return False

    def readback(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        """Return an authenticated state observation attached to one receipt."""

        if not self.verify_receipt(receipt):
            raise ValueError("receipt is not authentic for this ledger")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN")
                ledger_id, key = self._metadata(connection)
                state = connection.execute(
                    "SELECT * FROM targets WHERE target_id = ?",
                    (receipt["target_id"],),
                ).fetchone()
                if state is None:
                    raise KeyError(f"unknown target: {receipt['target_id']}")
                readback = {
                    "schema": "TARGET_READBACK_V1",
                    "ledger_id": ledger_id,
                    "readback_id": f"readback-{uuid.uuid4().hex}",
                    "receipt_id": receipt["receipt_id"],
                    "receipt_sha256": receipt["receipt_sha256"],
                    "request_id": receipt["request_id"],
                    "request_sha256": receipt["request_sha256"],
                    "actor_id": receipt["actor_id"],
                    "capability_id": receipt["capability_id"],
                    "target_id": receipt["target_id"],
                    "receipt_decision": receipt["decision"],
                    "receipt_mutation_applied": receipt["mutation_applied"],
                    "receipt_commit_id": receipt["commit_id"],
                    "receipt_post_version": receipt["post_version"],
                    "observed_state": json.loads(state["state_json"]),
                    "observed_state_sha256": state["state_sha256"],
                    "observed_version": state["version"],
                    "observed_commit_id": state["last_commit_id"],
                    "observed_commit_actor_id": state["last_commit_actor_id"],
                    "attached_to_receipt_commit": (
                        receipt["commit_id"] == state["last_commit_id"]
                        and receipt["post_version"] == state["version"]
                        and receipt["post_state_sha256"] == state["state_sha256"]
                    ),
                }
                readback["readback_sha256"] = _sha256(readback)
                readback["readback_auth_hex"] = self._authenticate(
                    readback,
                    key,
                    excluded_field="readback_auth_hex",
                )
                connection.execute(
                    "INSERT INTO readbacks(readback_id, receipt_id, readback_json) "
                    "VALUES (?, ?, ?)",
                    (
                        readback["readback_id"],
                        receipt["receipt_id"],
                        _canonical_bytes(readback).decode("utf-8"),
                    ),
                )
                connection.commit()
                return readback
            except Exception:
                connection.rollback()
                raise

    def verify_readback(
        self,
        readback: Mapping[str, Any],
        receipt: Mapping[str, Any],
        *,
        require_attached: bool = True,
    ) -> bool:
        """Verify origin and exact receipt attachment of a readback."""

        try:
            if not self.verify_receipt(receipt):
                return False
            with self._connect() as connection:
                ledger_id, key = self._metadata(connection)
                if readback.get("ledger_id") != ledger_id:
                    return False
                expected_sha = _sha256(
                    _without(readback, "readback_sha256", "readback_auth_hex")
                )
                if readback.get("readback_sha256") != expected_sha:
                    return False
                expected_auth = self._authenticate(
                    readback,
                    key,
                    excluded_field="readback_auth_hex",
                )
                if not hmac.compare_digest(
                    str(readback.get("readback_auth_hex", "")),
                    expected_auth,
                ):
                    return False
                bindings = {
                    "receipt_id": "receipt_id",
                    "receipt_sha256": "receipt_sha256",
                    "request_id": "request_id",
                    "request_sha256": "request_sha256",
                    "actor_id": "actor_id",
                    "capability_id": "capability_id",
                    "target_id": "target_id",
                    "receipt_decision": "decision",
                    "receipt_mutation_applied": "mutation_applied",
                    "receipt_commit_id": "commit_id",
                    "receipt_post_version": "post_version",
                }
                for readback_field, receipt_field in bindings.items():
                    if readback.get(readback_field) != receipt.get(receipt_field):
                        return False
                if require_attached and readback.get("attached_to_receipt_commit") is not True:
                    return False
                row = connection.execute(
                    "SELECT receipt_id, readback_json FROM readbacks "
                    "WHERE readback_id = ?",
                    (readback.get("readback_id"),),
                ).fetchone()
                return (
                    row is not None
                    and row["receipt_id"] == receipt["receipt_id"]
                    and json.loads(row["readback_json"]) == dict(readback)
                )
        except (KeyError, TypeError, ValueError):
            return False

    def current_state(self, target_id: str) -> dict[str, Any]:
        """Read the authoritative current state for diagnostics and tests."""

        with self._connect() as connection:
            state = connection.execute(
                "SELECT * FROM targets WHERE target_id = ?",
                (target_id,),
            ).fetchone()
            if state is None:
                raise KeyError(f"unknown target: {target_id}")
            return {
                "target_id": target_id,
                "state": json.loads(state["state_json"]),
                "state_sha256": state["state_sha256"],
                "version": state["version"],
                "last_commit_id": state["last_commit_id"],
                "last_commit_actor_id": state["last_commit_actor_id"],
                "last_request_sha256": state["last_request_sha256"],
            }
