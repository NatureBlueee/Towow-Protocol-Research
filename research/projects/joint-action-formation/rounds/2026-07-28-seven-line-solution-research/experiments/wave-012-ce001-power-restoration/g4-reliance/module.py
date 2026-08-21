#!/usr/bin/env python3
"""CE-001 G4 line-local reliance component.

G4 observes ordering, attempts, readback, reconciliation and owner-act closure.
It deliberately does not emit CE-001 contract conclusions.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


HERE = Path(__file__).resolve().parent
ACTOR_PROCESS = HERE / "actor_process.py"
PREDICTIONS = {"YES", "NO", "ABSTAIN"}
FORECAST_COORDINATES = (
    "first_attempt_target_record",
    "terminal_reconciliation",
    "owner_act_closure",
)
FORBIDDEN_RAW_KEYS = {
    "case_ref",
    "expected_label",
    "ground_truth",
    "safe_to_rely",
    "first_submit",
    "effect_on_retry",
    "acceptance_mutation",
    "resolution_terminal",
    "effect_mutation",
}


def canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def canonical_bytes(value: Any) -> bytes:
    return canonical(value).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        result = set(value)
        for child in value.values():
            result.update(_keys(child))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(_keys(child))
        return result
    return set()


def _b64decode(value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError("base64 field is not a string")
    return base64.b64decode(value.encode("ascii"), validate=True)


def explicit_object_adapter(episode: dict[str, Any]) -> dict[str, str]:
    """Validate and return the only admitted legacy-to-canonical mapping."""
    adapter = episode.get("object_adapter")
    if not isinstance(adapter, dict):
        raise ValueError("EXPLICIT_OBJECT_ADAPTER_MISSING")
    expected = {
        "adapter_id": "G4_LEGACY_TARGET_V1_TO_CE001_CANONICAL_V1",
        "adapter_version": "1",
        "source_object_id": "Venue-V/Circuit-C7",
        "canonical_object_id": "VenueV:CircuitC7",
    }
    if any(adapter.get(key) != value for key, value in expected.items()):
        raise ValueError("EXPLICIT_OBJECT_ADAPTER_MISMATCH")
    if episode.get("native_object_id") != expected["source_object_id"]:
        raise ValueError("ADAPTER_SOURCE_MISMATCH")
    if episode.get("object_id") != expected["canonical_object_id"]:
        raise ValueError("ADAPTER_TARGET_MISMATCH")
    mapping_hash = digest(expected)
    if adapter.get("mapping_sha256") != mapping_hash:
        raise ValueError("ADAPTER_MAPPING_DIGEST_MISMATCH")
    return copy.deepcopy(expected)


class ActorProcessClient:
    """Pinned actual-child identity plus exact transmitted-byte verification."""

    def __init__(
        self,
        role: str,
        episode: dict[str, Any],
        mutation: str = "NONE",
        oe_trust_binding: dict[str, Any] | None = None,
    ) -> None:
        self.role = role
        self.episode = copy.deepcopy(episode)
        self.mutation = mutation
        self.request_count = 0
        self.signed_response_count = 0
        self.transmitted: list[dict[str, str]] = []
        self._closed = False
        self.process = subprocess.Popen(
            ["python3", str(ACTOR_PROCESS), "--role", role],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(HERE),
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        init = {
            "type": "INIT",
            "episode": self.episode,
            "mutation": mutation,
            "oe_trust_binding": copy.deepcopy(oe_trust_binding or {}),
        }
        try:
            self._send_raw(canonical_bytes(init))
            ready_raw = self._read_raw()
            ready_envelope = self._parse_object(ready_raw)
        except BaseException:
            self.close(force=True)
            raise
        public_key_b64 = ready_envelope.get("public_key_b64")
        if not isinstance(public_key_b64, str):
            self.close(force=True)
            raise RuntimeError("child READY did not provide a public key")
        self.public_key_b64 = public_key_b64
        ready = self.verify_envelope(ready_envelope)
        expected_source_hash = digest_bytes(ACTOR_PROCESS.read_bytes())
        actual_pid = self.process.pid
        checks = {
            "role": role,
            "reported_pid": actual_pid,
            "executable_sha256": expected_source_hash,
        }
        if ready.get("kind") != "LOCAL_ACTOR_READY" or any(
            ready.get(key) != value for key, value in checks.items()
        ):
            self.close(force=True)
            raise RuntimeError("actual child identity binding failed")
        self.current_revision = int(ready["current_revision"])
        self.trust_binding = {
            "binding_kind": "LOCAL_PROCESS_INSTANCE_PINNED_ED25519",
            "role": role,
            "actual_child_pid": actual_pid,
            "reported_pid": ready["reported_pid"],
            "process_instance_id": ready["process_instance_id"],
            "service_id": ready["service_id"],
            "state_source_id": ready["state_source_id"],
            "act_source_id": ready["act_source_id"],
            "public_key_b64": public_key_b64,
            "executable_sha256": ready["executable_sha256"],
            "ready_payload_sha256": ready_envelope["payload_sha256"],
        }
        self.transmitted.append(
            {
                "direction": "CHILD_TO_CONTROLLER",
                "kind": "READY",
                "raw_sha256": digest_bytes(ready_raw),
            }
        )

    @staticmethod
    def _parse_object(raw: bytes) -> dict[str, Any]:
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("actor message must be an object")
        return value

    def _send_raw(self, raw: bytes) -> None:
        if self.process.stdin is None:
            raise RuntimeError("actor stdin unavailable")
        self.process.stdin.write(raw + b"\n")
        self.process.stdin.flush()

    def _read_raw(self) -> bytes:
        if self.process.stdout is None:
            raise RuntimeError("actor stdout unavailable")
        raw = self.process.stdout.readline()
        if not raw:
            stderr = (
                self.process.stderr.read().decode("utf-8", "replace")
                if self.process.stderr is not None
                else ""
            )
            raise RuntimeError(f"actor exited without response: {stderr}")
        return raw.rstrip(b"\n")

    def verify_envelope(self, envelope: dict[str, Any]) -> dict[str, Any]:
        if envelope.get("type") != "SIGNED_TRANSMITTED_BYTES":
            raise ValueError("response is not a signed-byte envelope")
        if envelope.get("public_key_b64") != self.public_key_b64:
            raise ValueError("response public key is not pinned")
        payload_bytes = _b64decode(envelope.get("payload_b64"))
        if digest_bytes(payload_bytes) != envelope.get("payload_sha256"):
            raise ValueError("payload digest mismatch")
        public_key = Ed25519PublicKey.from_public_bytes(
            _b64decode(self.public_key_b64)
        )
        try:
            public_key.verify(
                _b64decode(envelope.get("signature_b64")), payload_bytes
            )
        except InvalidSignature as exc:
            raise ValueError("signature is not from pinned actor") from exc
        payload = self._parse_object(payload_bytes)
        return payload

    def request(
        self, request: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], bytes, bytes]:
        request_raw = canonical_bytes(request)
        self.request_count += 1
        self._send_raw(request_raw)
        response_raw = self._read_raw()
        response = self._parse_object(response_raw)
        if response.get("type") == "REJECTED":
            self.transmitted.extend(
                [
                    {
                        "direction": "CONTROLLER_TO_CHILD",
                        "kind": str(request.get("type")),
                        "raw_sha256": digest_bytes(request_raw),
                    },
                    {
                        "direction": "CHILD_TO_CONTROLLER",
                        "kind": "REJECTED",
                        "raw_sha256": digest_bytes(response_raw),
                    },
                ]
            )
            return response, {}, request_raw, response_raw
        payload = self.verify_envelope(response)
        self.signed_response_count += 1
        self.transmitted.extend(
            [
                {
                    "direction": "CONTROLLER_TO_CHILD",
                    "kind": str(request.get("type")),
                    "raw_sha256": digest_bytes(request_raw),
                },
                {
                    "direction": "CHILD_TO_CONTROLLER",
                    "kind": str(payload.get("kind")),
                    "raw_sha256": digest_bytes(response_raw),
                },
            ]
        )
        return response, payload, request_raw, response_raw

    def close(self, force: bool = False) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if not force and self.process.poll() is None:
                self._send_raw(canonical_bytes({"type": "SHUTDOWN"}))
                self._read_raw()
        except (BrokenPipeError, RuntimeError):
            force = True
        if self.process.stdin is not None:
            self.process.stdin.close()
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.process.stderr is not None:
            self.process.stderr.close()
        if self.process.poll() is None:
            if force:
                self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)

    def __enter__(self) -> "ActorProcessClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


class OwnerTargetService:
    """Stateful local broker/target model for one private transition case."""

    def __init__(self, episode: dict[str, Any], private_case: dict[str, Any]) -> None:
        self.episode = copy.deepcopy(episode)
        self.config = copy.deepcopy(private_case)
        self.object_adapter = explicit_object_adapter(self.episode)
        self.tick = 0
        self.raw_trace: list[dict[str, Any]] = []
        self.hidden_trace: list[dict[str, Any]] = []
        self.reservation: dict[str, Any] | None = None
        self.commit_records: list[dict[str, Any]] | None = None
        self.target_record: dict[str, Any] | None = None
        self.target_envelope: dict[str, Any] | None = None
        self.owner_act_records: list[dict[str, Any]] = []
        self.attempt_count = 0
        self.target_delivery_count = 0
        self.occurrence_count = 0
        self.authorization_current_at_delivery = False
        self.first_attempt_target_record = False
        self.exact_reconciliation_observed = False
        self.exact_terminal_observed = False
        self.last_exact_reconciliation: dict[str, Any] | None = None
        self.revoked_terminal_observed = False
        self.wrong_object_returned = False
        self.submit_responses: list[dict[str, Any] | None] = []
        self.concurrent_barrier_parties = 0
        self._ledger: dict[str, dict[str, Any]] = {}
        self._target_lock = threading.Lock()
        self._actor_lock = threading.Lock()
        self._actors: dict[str, ActorProcessClient] = {}

    def close(self) -> None:
        for actor in list(self._actors.values()):
            actor.close()
        self._actors.clear()

    def __enter__(self) -> "OwnerTargetService":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def _ensure_actors(self) -> None:
        with self._actor_lock:
            if self._actors:
                return
            effect_actor = ActorProcessClient(
                "O_E",
                self.episode,
                str(self.config.get("effect_mutation", "NONE")),
            )
            mutation = str(self.config.get("acceptance_mutation", "NONE"))
            try:
                q_actor = ActorProcessClient(
                    "O_Q",
                    self.episode,
                    mutation,
                    effect_actor.trust_binding,
                )
                v_actor = ActorProcessClient(
                    "O_V",
                    self.episode,
                    mutation,
                    effect_actor.trust_binding,
                )
            except BaseException:
                effect_actor.close(force=True)
                raise
            self._actors = {
                "O_E": effect_actor,
                "O_Q": q_actor,
                "O_V": v_actor,
            }
            bindings = [actor.trust_binding for actor in self._actors.values()]
            for field in (
                "actual_child_pid",
                "process_instance_id",
                "service_id",
                "state_source_id",
                "act_source_id",
                "public_key_b64",
            ):
                values = [binding[field] for binding in bindings]
                if len(values) != len(set(values)):
                    self.close()
                    raise RuntimeError(f"actor trust bindings reuse {field}")

    def trust_bindings(self) -> dict[str, dict[str, Any]]:
        self._ensure_actors()
        return {
            role: copy.deepcopy(actor.trust_binding)
            for role, actor in sorted(self._actors.items())
        }

    def initial_truth(self) -> dict[str, bool]:
        return {
            "first_attempt_target_record": False,
            "terminal_reconciliation": bool(
                self.config.get("resolution_terminal", True)
            ),
            "owner_act_closure": False,
        }

    def p1_truth(self) -> dict[str, bool]:
        first_record = (
            self.config["first_submit"] == "EFFECT_ACK_LOST"
            and not self.config["revoke_after_reservation"]
        )
        eventual_record = first_record or (
            self.config["effect_on_retry"]
            and not self.config["revoke_after_reservation"]
        )
        return {
            "first_attempt_target_record": first_record,
            "terminal_reconciliation": bool(
                self.config.get("resolution_terminal", True)
            ),
            "owner_act_closure": (
                eventual_record
                and bool(self.config.get("resolution_terminal", True))
                and self.config.get("acceptance_mutation", "NONE") == "NONE"
                and self.config.get("effect_mutation", "NONE") == "NONE"
            ),
        }

    def _bound(self) -> dict[str, str]:
        return {
            "episode_id": self.episode["episode_id"],
            "Q_version": self.episode["Q_version"],
            "object_id": self.episode["object_id"],
            "operation_id": self.episode["operation_id"],
        }

    def call(self, action: str, args: dict[str, Any]) -> dict[str, Any] | None:
        handler = getattr(self, f"_do_{action}", None)
        if handler is None:
            raise ValueError(f"unknown action: {action}")
        self.tick += 1
        raw = handler(copy.deepcopy(args))
        if raw is not None:
            leaked = FORBIDDEN_RAW_KEYS & _keys(raw)
            if leaked:
                raise RuntimeError(f"private transition field leaked: {sorted(leaked)}")
        self.raw_trace.append(
            {
                "event": "RAW_CALL",
                "tick": self.tick,
                "action": action,
                "args": copy.deepcopy(args),
                "raw_response": copy.deepcopy(raw),
            }
        )
        if action in {"submit_operation", "retry_idempotent"}:
            self.submit_responses.append(copy.deepcopy(raw))
        return raw

    def _do_inspect_interfaces(self, args: dict[str, Any]) -> dict[str, Any]:
        del args
        return {
            "issuer": "O_E",
            "status_endpoint": "exact-operation-readback",
            "lookup_fields": ["operation_id", "object_id", "Q_version"],
            "object_adapter": copy.deepcopy(self.object_adapter),
            **self._bound(),
        }

    def _do_reserve(self, args: dict[str, Any]) -> dict[str, Any]:
        self._require_exact(args)
        self.reservation = {
            "issuer": "O_R",
            **self._bound(),
            "reservation_id": "reservation/CE-001/C7/41",
            "reservation_status": "RESERVED",
            "fence_epoch": 41,
            "resource_id": "battery-or-generator/slot-41",
            "expires_tick": 70,
        }
        if self.config["revoke_after_reservation"]:
            self.hidden_trace.append(
                {
                    "event": "OWNER_REVOCATION_AFTER_RESERVATION",
                    "owner_id": "O_R",
                    "revision": 8,
                }
            )
        return copy.deepcopy(self.reservation)

    def _do_read_commit_evidence(self, args: dict[str, Any]) -> dict[str, Any]:
        self._require_exact(args)
        if self.reservation is None:
            raise RuntimeError("commit evidence requested before reservation")
        decisions = {
            "O_Q": ("CURRENT", 7),
            "O_V": ("CURRENT", 7),
            "O_R": (
                "REVOKED" if self.config["revoke_after_reservation"] else "CURRENT",
                8 if self.config["revoke_after_reservation"] else 7,
            ),
            "O_S": ("CURRENT", 7),
        }
        self.commit_records = [
            {
                "issuer": owner,
                **self._bound(),
                "owner_decision": decision,
                "revision": revision,
                "valid_through_tick": 70,
                "evidence_hash": digest(
                    [owner, decision, revision, self._bound()]
                ),
            }
            for owner, (decision, revision) in decisions.items()
        ]
        self.revoked_terminal_observed = any(
            item["owner_decision"] == "REVOKED"
            for item in self.commit_records
        )
        return {"owner_records": copy.deepcopy(self.commit_records)}

    def _commit_current(self) -> bool:
        return bool(
            self.commit_records
            and all(
                record["owner_decision"] == "CURRENT"
                and self.tick <= record["valid_through_tick"]
                for record in self.commit_records
            )
        )

    def _valid_attempt(self, args: dict[str, Any]) -> bool:
        if self.reservation is None or not self._commit_current():
            return False
        if self.tick > self.reservation["expires_tick"]:
            return False
        if any(args.get(key) != value for key, value in self._bound().items()):
            return False
        if (
            args.get("reservation_id") != self.reservation["reservation_id"]
            or args.get("fence_epoch") != self.reservation["fence_epoch"]
        ):
            return False
        return args.get("commit_revisions") == {
            record["issuer"]: record["revision"]
            for record in self.commit_records or []
        }

    def _deliver_once(self) -> None:
        key = self.episode["idempotency_key"]
        with self._target_lock:
            self.target_delivery_count += 1
            if key in self._ledger:
                self.hidden_trace.append(
                    {
                        "event": "TARGET_DUPLICATE_SUPPRESSED",
                        "idempotency_key": key,
                    }
                )
                return
            self._ensure_actors()
            effect_actor = self._actors["O_E"]
            try:
                envelope, record, request_raw, response_raw = effect_actor.request(
                    {
                        "type": "ISSUE_TARGET_RECORD",
                        **self._bound(),
                        "completed_tick": self.tick,
                    }
                )
            except (TypeError, ValueError):
                self.hidden_trace.append(
                    {
                        "event": "TARGET_PROVENANCE_REJECTED",
                        "actor_role": "O_E",
                    }
                )
                return
            if not record:
                self.hidden_trace.append(
                    {
                        "event": "TARGET_RECORD_REJECTED",
                        "response_sha256": digest_bytes(response_raw),
                    }
                )
                return
            self.target_envelope = copy.deepcopy(envelope)
            self.target_record = copy.deepcopy(record)
            self._ledger[key] = copy.deepcopy(record)
            self.occurrence_count += 1
            self.hidden_trace.append(
                {
                    "event": "TARGET_NATIVE_SIGNED_BYTES_CONSUMED",
                    "request_sha256": digest_bytes(request_raw),
                    "response_sha256": digest_bytes(response_raw),
                }
            )

    def _deliver_concurrently(self) -> None:
        self._ensure_actors()
        barrier = threading.Barrier(2)
        self.concurrent_barrier_parties = barrier.parties
        failures: list[BaseException] = []

        def deliver() -> None:
            try:
                barrier.wait(timeout=2)
                self._deliver_once()
            except BaseException as exc:
                failures.append(exc)

        threads = [threading.Thread(target=deliver) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=4)
        if failures or any(thread.is_alive() for thread in threads):
            raise RuntimeError("concurrent duplicate-delivery pressure failed")

    def _do_submit_operation(self, args: dict[str, Any]) -> None:
        self.attempt_count += 1
        if not self._valid_attempt(args):
            return None
        if self.config["first_submit"] == "EFFECT_ACK_LOST":
            self.authorization_current_at_delivery = True
            if self.config["duplicate_delivery"]:
                self._deliver_concurrently()
            else:
                self._deliver_once()
            self.first_attempt_target_record = self.occurrence_count == 1
        return None

    def _do_readback_operation(self, args: dict[str, Any]) -> dict[str, Any]:
        del args
        if self.config["wrong_object_first"]:
            self.wrong_object_returned = True
            return {
                "issuer": "O_E",
                "Q_version": self.episode["Q_version"],
                "object_id": "VenueV:CircuitC9",
                "operation_id": "restore-power/OTHER/C9",
                "state": "SUCCEEDED",
                "effect_revision": 9,
            }
        return self._exact_readback()

    def _exact_readback(self) -> dict[str, Any]:
        if self.target_record is None:
            return {
                "issuer": "O_E",
                **self._bound(),
                "state": "NO_RECORD",
                "effect_revision": 0,
            }
        result = copy.deepcopy(self.target_record)
        result["oe_provenance"] = copy.deepcopy(self.target_envelope)
        if not self.config.get("resolution_terminal", True):
            result["state"] = "PENDING"
        return result

    def _do_reconcile_operation(self, args: dict[str, Any]) -> dict[str, Any]:
        self._require_exact(args)
        raw = self._exact_readback()
        exact_tuple = all(raw.get(key) == value for key, value in self._bound().items())
        self.exact_reconciliation_observed = exact_tuple
        self.exact_terminal_observed = exact_tuple and raw.get("state") in {
            "SUCCEEDED",
            "NO_RECORD",
        }
        self.last_exact_reconciliation = copy.deepcopy(raw)
        return raw

    def _do_retry_idempotent(self, args: dict[str, Any]) -> dict[str, Any]:
        self.attempt_count += 1
        if not self._valid_attempt(args):
            return {
                "issuer": "execution-provider",
                **self._bound(),
                "provider_result": "REJECTED_NO_TARGET_CHANGE",
            }
        if self.target_record is not None:
            return {
                "issuer": "execution-provider",
                **self._bound(),
                "provider_result": "DUPLICATE_SUPPRESSED",
            }
        if self.config["effect_on_retry"]:
            self.authorization_current_at_delivery = True
            self._deliver_once()
            return {
                "issuer": "execution-provider",
                **self._bound(),
                "provider_result": "COMPLETED",
            }
        return {
            "issuer": "execution-provider",
            **self._bound(),
            "provider_result": "REJECTED_NO_TARGET_CHANGE",
        }

    def _target_gate_failures(self, args: dict[str, Any]) -> list[str]:
        failures: list[str] = []
        if not self.exact_reconciliation_observed:
            failures.append("EXACT_RECONCILIATION_MISSING")
        reconciliation = self.last_exact_reconciliation
        if not isinstance(reconciliation, dict):
            failures.append("RECONCILIATION_MISSING")
        elif reconciliation.get("state") != "SUCCEEDED":
            failures.append("RECONCILIATION_NOT_SUCCEEDED")
        if self.target_record is None or self.target_envelope is None:
            failures.append("TARGET_RECORD_MISSING")
            return failures
        if reconciliation is not None:
            for field in (
                "effect_occurrence_id",
                "effect_revision",
                "circuit_id",
                "power_kw",
                "continuous_minutes",
                "other_circuits_energized",
            ):
                if reconciliation.get(field) != self.target_record.get(field):
                    failures.append(f"RECONCILIATION_TARGET_{field.upper()}_MISMATCH")
        for field, expected in self._bound().items():
            if self.target_record.get(field) != expected:
                failures.append(f"TARGET_WRONG_{field.upper()}")
        if self.target_record.get("issuer") != "O_E":
            failures.append("TARGET_WRONG_ISSUER")
        if self.target_record.get("state") != "SUCCEEDED":
            failures.append("TARGET_NOT_SUCCEEDED")
        if self.target_record.get("circuit_id") != "C7":
            failures.append("TARGET_WRONG_CIRCUIT")
        power = self.target_record.get("power_kw")
        if not isinstance(power, (int, float)) or not 2.85 <= float(power) <= 3.15:
            failures.append("TARGET_POWER_OUT_OF_RANGE")
        duration = self.target_record.get("continuous_minutes")
        if not isinstance(duration, (int, float)) or float(duration) < 45:
            failures.append("TARGET_DURATION_TOO_SHORT")
        if self.target_record.get("no_other_circuit") is not True:
            failures.append("TARGET_OTHER_CIRCUIT_FLAG")
        if self.target_record.get("other_circuits_energized") != []:
            failures.append("TARGET_OTHER_CIRCUIT_PRESENT")
        completed_tick = self.target_record.get("completed_tick")
        if (
            not isinstance(completed_tick, int)
            or completed_tick > int(self.episode["deadline_tick"])
            or self.tick > int(self.episode["deadline_tick"])
        ):
            failures.append("TARGET_DEADLINE_MISSED")
        if (
            args.get("effect_occurrence_id")
            != self.target_record.get("effect_occurrence_id")
            or args.get("effect_revision")
            != self.target_record.get("effect_revision")
        ):
            failures.append("TARGET_REQUEST_BINDING_MISMATCH")
        try:
            parsed = self._actors["O_E"].verify_envelope(self.target_envelope)
            if parsed != self.target_record:
                failures.append("O_E_TRANSMITTED_PAYLOAD_MISMATCH")
            oe_binding = self._actors["O_E"].trust_binding
            for field in (
                "service_id",
                "state_source_id",
                "act_source_id",
                "process_instance_id",
            ):
                if parsed.get(field) != oe_binding[field]:
                    failures.append(
                        f"O_E_{field.upper()}_BINDING_MISMATCH"
                    )
            if parsed.get("reported_pid") != oe_binding["actual_child_pid"]:
                failures.append("O_E_ACTUAL_CHILD_PID_MISMATCH")
        except (KeyError, TypeError, ValueError):
            failures.append("O_E_PROVENANCE_INVALID")
        return failures

    def _request_owner_act(
        self, owner_id: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        self._require_exact(args)
        self._ensure_actors()
        failures = self._target_gate_failures(args)
        if failures:
            return {
                "owner_id": owner_id,
                "status": "PRE_ACT_GATE_REJECTED",
                "gate_failures": failures,
                "owner_act": None,
            }
        assert self.target_envelope is not None
        assert self.last_exact_reconciliation is not None
        request = {
            "type": "ISSUE_OWNER_ACT",
            **self._bound(),
            "effect_occurrence_id": self.target_record["effect_occurrence_id"],
            "effect_revision": self.target_record["effect_revision"],
            "exact_reconciliation": self.exact_reconciliation_observed,
            "reconciliation_state": self.last_exact_reconciliation["state"],
            "target_payload_sha256": self.target_envelope["payload_sha256"],
            "target_envelope": copy.deepcopy(self.target_envelope),
        }
        actor = self._actors[owner_id]
        envelope, act, request_raw, response_raw = actor.request(request)
        if not act:
            return {
                "owner_id": owner_id,
                "status": "OWNER_PROCESS_REJECTED",
                "gate_failures": list(envelope.get("failures", [])),
                "owner_act": None,
            }
        self.owner_act_records.append(
            {
                "requested_owner": owner_id,
                "envelope": copy.deepcopy(envelope),
                "payload": copy.deepcopy(act),
                "request_sha256": digest_bytes(request_raw),
                "response_sha256": digest_bytes(response_raw),
            }
        )
        return {
            "owner_id": owner_id,
            "status": "OWNER_ACT_RECORDED",
            "owner_act": copy.deepcopy(act),
            "transmitted_response_sha256": digest_bytes(response_raw),
        }

    def _do_request_q_acceptance(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._request_owner_act(self.episode["owners"]["Q"], args)

    def _do_request_venue_acceptance(self, args: dict[str, Any]) -> dict[str, Any]:
        return self._request_owner_act(self.episode["owners"]["venue"], args)

    def _require_exact(self, args: dict[str, Any]) -> None:
        if any(args.get(key) != value for key, value in self._bound().items()):
            raise ValueError("action is not bound to exact CE-001 tuple")

    def _owner_act_closure(self) -> tuple[bool, list[str]]:
        failures: list[str] = []
        required = {
            self.episode["owners"]["Q"],
            self.episode["owners"]["venue"],
        }
        declared = list(self.episode["acceptance_owners"])
        if len(declared) != len(set(declared)) or set(declared) != required:
            failures.append("INVALID_REQUIRED_OWNER_DECLARATION")
        target_failures = self._target_gate_failures(
            {
                **self._bound(),
                "effect_occurrence_id": (
                    self.target_record or {}
                ).get("effect_occurrence_id"),
                "effect_revision": (
                    self.target_record or {}
                ).get("effect_revision"),
            }
        )
        failures.extend(target_failures)
        requested = [item["requested_owner"] for item in self.owner_act_records]
        if len(requested) != len(set(requested)):
            failures.append("DUPLICATE_REQUESTED_OWNER")
        if set(requested) != required or len(requested) != len(required):
            failures.append("OWNER_SET_NOT_EXACT")
        issuers = [
            item["payload"].get("issuer") for item in self.owner_act_records
        ]
        if len(issuers) != len(set(issuers)):
            failures.append("DUPLICATE_ISSUER")
        if set(issuers) != required or len(issuers) != len(required):
            failures.append("ISSUER_SET_NOT_EXACT")
        expected_bound = self._bound()
        for item in self.owner_act_records:
            owner_id = item["requested_owner"]
            payload = item["payload"]
            actor = self._actors.get(owner_id)
            if actor is None:
                failures.append(f"{owner_id}:OWNER_PROCESS_MISSING")
                continue
            try:
                verified = actor.verify_envelope(item["envelope"])
                if verified != payload:
                    failures.append(f"{owner_id}:TRANSMITTED_PAYLOAD_MISMATCH")
            except (TypeError, ValueError):
                failures.append(f"{owner_id}:SIGNATURE_INVALID")
            binding = actor.trust_binding
            for field in (
                "service_id",
                "state_source_id",
                "act_source_id",
                "process_instance_id",
            ):
                if payload.get(field) != binding[field]:
                    failures.append(
                        f"{owner_id}:{field.upper()}_BINDING_MISMATCH"
                    )
            if payload.get("reported_pid") != binding["actual_child_pid"]:
                failures.append(f"{owner_id}:ACTUAL_CHILD_PID_MISMATCH")
            if payload.get("issuer") != owner_id:
                failures.append(f"{owner_id}:WRONG_ISSUER")
            if payload.get("decision") != "ACCEPT":
                failures.append(f"{owner_id}:NOT_ACCEPT")
            for field, expected in expected_bound.items():
                if payload.get(field) != expected:
                    failures.append(f"{owner_id}:WRONG_{field.upper()}")
            if self.target_record is not None:
                for field in ("effect_occurrence_id", "effect_revision"):
                    if payload.get(field) != self.target_record.get(field):
                        failures.append(f"{owner_id}:WRONG_{field.upper()}")
                if payload.get("target_payload_sha256") != (
                    self.target_envelope or {}
                ).get("payload_sha256"):
                    failures.append(f"{owner_id}:WRONG_TARGET_BYTES")
            if payload.get("owner_revision") != actor.current_revision:
                failures.append(f"{owner_id}:STALE_OWNER_REVISION")
        return not failures, list(dict.fromkeys(failures))

    def observations(self, worker_result: dict[str, Any]) -> dict[str, Any]:
        del worker_result
        closure, closure_failures = self._owner_act_closure()
        wrong_without_exact = bool(
            self.wrong_object_returned and not self.exact_reconciliation_observed
        )
        return {
            "attempt": {
                "count": self.attempt_count,
                "target_delivery_count": self.target_delivery_count,
                "target_occurrence_count": self.occurrence_count,
                "first_attempt_target_record": self.first_attempt_target_record,
                "duplicate_target_occurrence": self.occurrence_count > 1,
                "authorization_current_at_delivery": (
                    self.authorization_current_at_delivery
                ),
                "concurrent_barrier_parties": self.concurrent_barrier_parties,
            },
            "readback": {
                "wrong_object_returned": self.wrong_object_returned,
                "wrong_object_without_exact_followup": wrong_without_exact,
            },
            "reconciliation": {
                "exact_observed": self.exact_reconciliation_observed,
                "terminal_observed": bool(
                    self.exact_terminal_observed
                    or (
                        self.revoked_terminal_observed
                        and self.attempt_count == 0
                    )
                ),
                "final_state": (
                    self.last_exact_reconciliation or {}
                ).get("state", "NOT_OBSERVED"),
                "target_record_without_terminal_reconciliation": bool(
                    self.occurrence_count and not self.exact_terminal_observed
                ),
            },
            "owner_act_closure": {
                "closed": closure,
                "record_count": len(self.owner_act_records),
                "requested_owners": [
                    item["requested_owner"] for item in self.owner_act_records
                ],
                "issuers": [
                    item["payload"].get("issuer")
                    for item in self.owner_act_records
                ],
                "failures": closure_failures,
                "signed_response_counts": {
                    role: actor.signed_response_count
                    for role, actor in sorted(self._actors.items())
                    if role in {"O_Q", "O_V"}
                },
            },
            "source_process_evidence": (
                self.trust_bindings() if self._actors else {}
            ),
        }


def confusion(
    rows: list[dict[str, Any]], stage: str, coordinate: str
) -> dict[str, int | float | None]:
    counts = {
        "TP": 0,
        "FP": 0,
        "TN": 0,
        "FN": 0,
        "ABSTAIN_TRUE": 0,
        "ABSTAIN_FALSE": 0,
    }
    for row in rows:
        prediction = row["predictions"][stage][coordinate]
        truth = bool(row["truth"][stage][coordinate])
        if prediction not in PREDICTIONS:
            raise ValueError(f"invalid prediction: {prediction}")
        if prediction == "ABSTAIN":
            counts["ABSTAIN_TRUE" if truth else "ABSTAIN_FALSE"] += 1
        elif prediction == "YES":
            counts["TP" if truth else "FP"] += 1
        else:
            counts["FN" if truth else "TN"] += 1
    rely = counts["TP"] + counts["FP"]
    return {
        **counts,
        "false_reliance_conditional": counts["FP"] / rely if rely else None,
        "selective_coverage": (
            (counts["TP"] + counts["FP"] + counts["TN"] + counts["FN"])
            / len(rows)
            if rows
            else None
        ),
    }


def score(rows: list[dict[str, Any]], baseline_occurrences: int) -> dict[str, Any]:
    eligible = [
        row for row in rows if row["case_ref"] != "PRESSURE-REVOKE-AFTER-RESERVE"
    ]
    return {
        "reliance_calibration": {
            stage: {
                coordinate: confusion(rows, stage, coordinate)
                for coordinate in FORECAST_COORDINATES
            }
            for stage in ("P0", "P1")
        },
        "attempt_readback_evidence": {
            "causal_status": "LOCAL_STATE_MACHINE_NECESSARY_CONDITION_ONLY",
            "eligible_target_record_coverage": {
                "numerator": sum(
                    bool(
                        row["observations"]["attempt"][
                            "target_occurrence_count"
                        ]
                    )
                    for row in eligible
                ),
                "denominator": len(eligible),
            },
            "matched_no_interaction_target_occurrences": baseline_occurrences,
            "matched_no_interaction_coverage": {
                "numerator": baseline_occurrences,
                "denominator": len(eligible),
            },
            "necessary_precondition_observation": (
                "Within this local state machine, submit without reservation "
                "and current commit evidence cannot produce a target record. "
                "This is not a method advantage or an open-world causal claim."
            ),
            "duplicate_target_occurrence_cases": sum(
                bool(
                    row["observations"]["attempt"][
                        "duplicate_target_occurrence"
                    ]
                )
                for row in rows
            ),
            "attempt_authorization_violation_cases": sum(
                bool(
                    row["observations"]["attempt"]["target_occurrence_count"]
                    and not row["observations"]["attempt"][
                        "authorization_current_at_delivery"
                    ]
                )
                for row in rows
            ),
            "wrong_object_without_exact_followup_cases": sum(
                bool(
                    row["observations"]["readback"][
                        "wrong_object_without_exact_followup"
                    ]
                )
                for row in rows
            ),
            "target_record_without_terminal_reconciliation_cases": sum(
                bool(
                    row["observations"]["reconciliation"][
                        "target_record_without_terminal_reconciliation"
                    ]
                )
                for row in rows
            ),
        },
    }


def _args(service: OwnerTargetService) -> dict[str, Any]:
    return service._bound()


def _transcript(
    episode: dict[str, Any], config: dict[str, Any], plan: tuple[str, ...]
) -> list[Any]:
    with OwnerTargetService(episode, config) as service:
        args = _args(service)
        output: list[Any] = []
        for action in plan:
            raw = service.call(action, args)
            output.append(raw)
            if action == "reserve" and isinstance(raw, dict):
                args["reservation_id"] = raw["reservation_id"]
                args["fence_epoch"] = raw["fence_epoch"]
            elif action == "read_commit_evidence" and isinstance(raw, dict):
                args["commit_revisions"] = {
                    item["issuer"]: item["revision"]
                    for item in raw["owner_records"]
                }
        return output


def audit_e3_pair(
    episode: dict[str, Any],
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    plans = [
        tuple(),
        ("inspect_interfaces",),
        ("inspect_interfaces", "reserve"),
        ("inspect_interfaces", "reserve", "read_commit_evidence"),
        (
            "inspect_interfaces",
            "reserve",
            "read_commit_evidence",
            "submit_operation",
        ),
        (
            "inspect_interfaces",
            "reserve",
            "read_commit_evidence",
            "submit_operation",
            "readback_operation",
        ),
        (
            "inspect_interfaces",
            "reserve",
            "read_commit_evidence",
            "submit_operation",
            "readback_operation",
            "reconcile_operation",
        ),
    ]
    comparisons = []
    for plan in plans:
        a = _transcript(episode, left, plan)
        b = _transcript(episode, right, plan)
        comparisons.append((plan, canonical(a) == canonical(b)))
    distinguishing = [
        list(plan) for plan, equivalent in comparisons if not equivalent
    ]
    pre_attempt = [
        equivalent
        for plan, equivalent in comparisons
        if "submit_operation" not in plan
    ]
    return {
        "pair_ref": "CE-001-E3-ACK-LOSS",
        "classification": "ACTIVE",
        "passive": {"initial_packet_equivalent": True},
        "active": {
            "pre_attempt_isomorphic": all(pre_attempt),
            "distinguishing_witness_exists": bool(distinguishing),
        },
        "full_interaction": {
            "plans_enumerated": len(plans),
            "interaction_equivalent": not distinguishing,
            "distinguishing_plans": distinguishing,
        },
    }
