"""Evaluator-private hidden-world primitives for the Wave 015 runner.

This module freezes private topology and scenario facts while constructing the
arm view from a positive allowlist.  It is runner foundation only: it does not
launch an arm, owner, target, or migration runtime.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from visibility import validate_arm_view

TOPOLOGY_FIELDS = (
    "owner_instance_id",
    "owner_role",
    "principal_id",
    "authority_locus",
    "resource_kind",
    "discoverability_condition",
    "current_head",
    "epoch",
)
FORBIDDEN_ARM_KEY_PARTS = (
    "scenario",
    "case_id",
    "expected",
    "candidate",
    "topology",
    "owner_registry",
    "alternative",
    "crash",
    "fault",
    "migration",
    "restart",
    "private",
    "receipt",
    "manifest_hash",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _opaque() -> str:
    return uuid.uuid4().hex


def _public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def _sign(private_key: Ed25519PrivateKey, value: Mapping[str, Any]) -> str:
    return private_key.sign(canonical_bytes(value)).hex()


def _verify(value: Mapping[str, Any], public_key_hex: str) -> bool:
    signature_hex = value.get("signature_hex")
    if not isinstance(signature_hex, str):
        return False
    unsigned = dict(value)
    unsigned.pop("signature_hex", None)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(signature_hex), canonical_bytes(unsigned)
        )
    except (ValueError, InvalidSignature):
        return False
    return True


def verify_private_packet(
    packet: Mapping[str, Any],
    *,
    expected_controller_instance_id: str,
    expected_controller_public_key_hex: str,
    expected_kind: str,
    expected_episode_binding: str,
    expected_public_view: Mapping[str, Any],
) -> bool:
    """Independently verify one persisted controller-private packet."""

    private_payload = packet.get("private_payload")
    receipt = packet.get("receipt")
    if not isinstance(private_payload, Mapping) or not isinstance(receipt, Mapping):
        return False
    if receipt.get("schema") != "HIDDEN_WORLD_PRIVATE_RECEIPT_V1":
        return False
    if receipt.get("kind") != expected_kind:
        return False
    if receipt.get("controller_instance_id") != expected_controller_instance_id:
        return False
    if (
        receipt.get("controller_public_key_hex")
        != expected_controller_public_key_hex
    ):
        return False
    if receipt.get("episode_binding") != expected_episode_binding:
        return False
    if receipt.get("public_view_sha256") != sha256_value(expected_public_view):
        return False
    if receipt.get("private_payload_sha256") != sha256_value(private_payload):
        return False
    return _verify(receipt, expected_controller_public_key_hex)


def alpha_shape(value: Any) -> Any:
    """Preserve public structure while renaming opaque/random scalar values."""
    if isinstance(value, Mapping):
        return {key: alpha_shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [alpha_shape(item) for item in value]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if value is None:
        return "null"
    if isinstance(value, str):
        return "str:%d" % len(value)
    return type(value).__name__


def arm_key_violations(value: Any, path: str = "$") -> List[str]:
    """Return private-looking key paths present on an arm-visible surface."""
    violations: List[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in FORBIDDEN_ARM_KEY_PARTS):
                violations.append("%s.%s" % (path, key))
            violations.extend(arm_key_violations(nested, "%s.%s" % (path, key)))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            violations.extend(
                arm_key_violations(nested, "%s[%d]" % (path, index))
            )
    return violations


class HiddenScenarioController:
    """Owns evaluator-private scenario facts and signs frozen receipts."""

    def __init__(self) -> None:
        self._private_key = Ed25519PrivateKey.generate()
        self.controller_instance_id = _opaque()
        self.public_key_hex = _public_key_hex(self._private_key)
        self._fired_schedule_receipts: set = set()

    def arm_view(
        self,
        base_arm_view: Mapping[str, Any],
    ) -> Dict[str, Any]:
        result = validate_arm_view(base_arm_view)
        violations = arm_key_violations(result)
        if violations:
            raise ValueError("private field on arm view: %s" % ", ".join(violations))
        return result

    def _private_packet(
        self,
        *,
        kind: str,
        episode_binding: str,
        public_view: Mapping[str, Any],
        private_payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        receipt = {
            "schema": "HIDDEN_WORLD_PRIVATE_RECEIPT_V1",
            "receipt_id": _opaque(),
            "kind": kind,
            "controller_instance_id": self.controller_instance_id,
            "controller_public_key_hex": self.public_key_hex,
            "episode_binding": episode_binding,
            "public_view_sha256": sha256_value(public_view),
            "private_payload_sha256": sha256_value(private_payload),
        }
        receipt["signature_hex"] = _sign(self._private_key, receipt)
        return {
            "private_payload": copy.deepcopy(private_payload),
            "receipt": receipt,
        }

    def verify_private_packet(
        self,
        packet: Mapping[str, Any],
        *,
        expected_kind: str,
        expected_episode_binding: str,
        expected_public_view: Mapping[str, Any],
    ) -> bool:
        return verify_private_packet(
            packet,
            expected_controller_instance_id=self.controller_instance_id,
            expected_controller_public_key_hex=self.public_key_hex,
            expected_kind=expected_kind,
            expected_episode_binding=expected_episode_binding,
            expected_public_view=expected_public_view,
        )

    def freeze_e3_pair(
        self,
        *,
        episode_binding: str,
        base_arm_view: Mapping[str, Any],
    ) -> Dict[str, Any]:
        base_view = self.arm_view(base_arm_view)
        # The first permitted semantic divergence is a later exact readback.
        public_prefix = [
            {
                "kind": "SUBMIT_RETURN",
                "status": "OUTCOME_UNCONFIRMED",
                "operation_handle": _opaque(),
            }
        ]
        shared_arm_view = copy.deepcopy(base_view)
        shared_pre_readback_public_view = {
            "startup_arm_view": copy.deepcopy(shared_arm_view),
            "public_prefix": copy.deepcopy(public_prefix),
        }
        private_forks = (
            {
                "scenario_label": "E3A-ACK-LOST-EFFECT",
                "submit_ack": "LOST",
                "target_commit_before_readback": True,
                "first_permitted_divergence": "EXACT_TARGET_READBACK",
            },
            {
                "scenario_label": "E3B-ACK-LOST-NO-EFFECT",
                "submit_ack": "LOST",
                "target_commit_before_readback": False,
                "first_permitted_divergence": "EXACT_TARGET_READBACK",
            },
        )
        forks = []
        for payload in private_forks:
            forks.append(
                {
                    "arm_view": copy.deepcopy(shared_arm_view),
                    "public_prefix": copy.deepcopy(public_prefix),
                    "private_packet": self._private_packet(
                        kind="E3_PAIRED_FORK",
                        episode_binding=episode_binding,
                        public_view=shared_pre_readback_public_view,
                        private_payload=payload,
                    ),
                }
            )
        pair_payload = {
            "fork_private_payload_sha256": [
                fork["private_packet"]["receipt"]["private_payload_sha256"]
                for fork in forks
            ],
            "shared_public_prefix_sha256": sha256_value(public_prefix),
            "first_permitted_divergence": "EXACT_TARGET_READBACK",
        }
        return {
            "forks": forks,
            "pair_private_packet": self._private_packet(
                kind="E3_PAIR_BINDING",
                episode_binding=episode_binding,
                public_view=shared_pre_readback_public_view,
                private_payload=pair_payload,
            ),
            "shared_pre_readback_public_view": shared_pre_readback_public_view,
            "raw_prefix_equal": canonical_bytes(
                {
                    "arm_view": forks[0]["arm_view"],
                    "public_prefix": forks[0]["public_prefix"],
                }
            )
            == canonical_bytes(
                {
                    "arm_view": forks[1]["arm_view"],
                    "public_prefix": forks[1]["public_prefix"],
                }
            ),
            "alpha_equivalent": alpha_shape(
                {
                    "arm_view": forks[0]["arm_view"],
                    "public_prefix": forks[0]["public_prefix"],
                }
            )
            == alpha_shape(
                {
                    "arm_view": forks[1]["arm_view"],
                    "public_prefix": forks[1]["public_prefix"],
                }
            ),
        }

    def freeze_e4(
        self,
        *,
        episode_binding: str,
        base_arm_view: Mapping[str, Any],
        broker: "OwnerTopologyBroker",
        topology: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        broker.freeze_topology(topology)
        arm_view = self.arm_view(base_arm_view)
        if arm_view["broker_surface"] != broker.public_surface():
            raise ValueError("arm view is not bound to this Broker surface")
        private_payload = {
            "scenario_label": "E4-REVOKE-WITH-ALTERNATIVE",
            "broker_instance_id": broker.broker_instance_id,
            "owner_topology": copy.deepcopy(list(topology)),
            "topology_sha256": sha256_value(list(topology)),
            "alternative_reveal_condition": "AFTER_PRIMARY_REVOKE_AND_DISCOVER",
        }
        packet = self._private_packet(
            kind="E4_HIDDEN_TOPOLOGY",
            episode_binding=episode_binding,
            public_view=arm_view,
            private_payload=private_payload,
        )
        broker.bind_controller_receipt(
            controller=self,
            episode_binding=episode_binding,
            public_view=arm_view,
            topology_packet=packet,
        )
        return {"arm_view": arm_view, "private_packet": packet}

    def freeze_e6(
        self,
        *,
        episode_binding: str,
        base_arm_view: Mapping[str, Any],
        schedule: Mapping[str, Any],
    ) -> Dict[str, Any]:
        required = (
            "trigger_event_sha256",
            "trigger_logical_minute",
            "crash_cut",
            "target_epoch",
            "old_runtime_restart_minute",
        )
        missing = [field for field in required if field not in schedule]
        if missing:
            raise ValueError("missing E6 schedule fields: %s" % ", ".join(missing))
        arm_view = self.arm_view(base_arm_view)
        private_payload = {
            "scenario_label": "E6-MIGRATION-REPLAY",
            "schedule": copy.deepcopy(dict(schedule)),
            "trigger_rule": "NATIVE_EVENT_HASH_AND_LOGICAL_MINUTE",
        }
        return {
            "arm_view": arm_view,
            "private_packet": self._private_packet(
                kind="E6_CRASH_SCHEDULE",
                episode_binding=episode_binding,
                public_view=arm_view,
                private_payload=private_payload,
            ),
        }

    def maybe_fire_e6(
        self,
        frozen: Mapping[str, Any],
        *,
        episode_binding: str,
        native_event_sha256: str,
        logical_minute: int,
    ) -> Optional[Dict[str, Any]]:
        arm_view = frozen["arm_view"]
        packet = frozen["private_packet"]
        if not self.verify_private_packet(
            packet,
            expected_kind="E6_CRASH_SCHEDULE",
            expected_episode_binding=episode_binding,
            expected_public_view=arm_view,
        ):
            raise ValueError("invalid frozen E6 private packet")
        schedule = packet["private_payload"]["schedule"]
        receipt_id = packet["receipt"]["receipt_id"]
        if receipt_id in self._fired_schedule_receipts:
            return None
        if schedule["trigger_event_sha256"] != native_event_sha256:
            return None
        if schedule["trigger_logical_minute"] != logical_minute:
            return None
        self._fired_schedule_receipts.add(receipt_id)
        event_payload = {
            "source_schedule_receipt_id": receipt_id,
            "observed_native_event_sha256": native_event_sha256,
            "observed_logical_minute": logical_minute,
            "crash_cut": schedule["crash_cut"],
            "target_epoch": schedule["target_epoch"],
            "old_runtime_restart_minute": schedule[
                "old_runtime_restart_minute"
            ],
        }
        return self._private_packet(
            kind="E6_TRIGGER_FIRED",
            episode_binding=episode_binding,
            public_view=arm_view,
            private_payload=event_payload,
        )


class OwnerTopologyBroker:
    """Fixed arm surface over an evaluator-private owner topology registry."""

    def __init__(self) -> None:
        self.broker_instance_id = _opaque()
        self._endpoint_handle = _opaque()
        self._topology: List[Dict[str, Any]] = []
        self._owner_handles: Dict[str, str] = {}
        self._resource_handles: Dict[str, str] = {}
        self._handle_to_owner: Dict[str, str] = {}
        self._primary_revoked = False
        self._epoch = 0
        self._controller_binding: Optional[Dict[str, Any]] = None
        self._private_route_packets: List[Dict[str, Any]] = []

    def public_surface(self) -> Dict[str, Any]:
        return {
            "endpoint_handle": self._endpoint_handle,
            "capabilities": ["DISCOVER", "REQUEST", "STATUS"],
            "surface_version": 1,
        }

    def freeze_topology(self, topology: Sequence[Mapping[str, Any]]) -> None:
        if self._topology:
            raise ValueError("topology already frozen")
        if not topology:
            raise ValueError("topology must not be empty")
        frozen: List[Dict[str, Any]] = []
        for entry in topology:
            missing = [field for field in TOPOLOGY_FIELDS if field not in entry]
            if missing:
                raise ValueError(
                    "topology entry missing fields: %s" % ", ".join(missing)
                )
            item = {field: copy.deepcopy(entry[field]) for field in TOPOLOGY_FIELDS}
            owner_id = item["owner_instance_id"]
            if owner_id in self._owner_handles:
                raise ValueError("duplicate owner instance")
            owner_handle = _opaque()
            resource_handle = _opaque()
            self._owner_handles[owner_id] = owner_handle
            self._resource_handles[owner_id] = resource_handle
            self._handle_to_owner[owner_handle] = owner_id
            self._handle_to_owner[resource_handle] = owner_id
            frozen.append(item)
        self._topology = frozen

    def bind_controller_receipt(
        self,
        *,
        controller: HiddenScenarioController,
        episode_binding: str,
        public_view: Mapping[str, Any],
        topology_packet: Mapping[str, Any],
    ) -> None:
        if not controller.verify_private_packet(
            topology_packet,
            expected_kind="E4_HIDDEN_TOPOLOGY",
            expected_episode_binding=episode_binding,
            expected_public_view=public_view,
        ):
            raise ValueError("invalid controller topology receipt")
        if (
            topology_packet["private_payload"]["broker_instance_id"]
            != self.broker_instance_id
        ):
            raise ValueError("topology receipt bound to another broker")
        self._controller_binding = {
            "controller": controller,
            "episode_binding": episode_binding,
            "public_view": copy.deepcopy(public_view),
            "topology_receipt_id": topology_packet["receipt"]["receipt_id"],
        }

    def _eligible(self, resource_kind: str) -> List[Dict[str, Any]]:
        phase = "AFTER_PRIMARY_REVOKE" if self._primary_revoked else "INITIAL"
        return [
            entry
            for entry in self._topology
            if entry["resource_kind"] == resource_kind
            and entry["discoverability_condition"] == phase
        ]

    def discover(self, resource_kind: str) -> Dict[str, Any]:
        if self._controller_binding is None:
            raise ValueError("broker has no verified controller binding")
        candidates = self._eligible(resource_kind)
        if not candidates:
            public_result = {
                "status": "NOT_FOUND",
                "owner_handle": None,
                "resource_handle": None,
            }
            selected_owner_id = None
        else:
            selected = candidates[0]
            selected_owner_id = selected["owner_instance_id"]
            public_result = {
                "status": "FOUND",
                "owner_handle": self._owner_handles[selected_owner_id],
                "resource_handle": self._resource_handles[selected_owner_id],
            }
        controller = self._controller_binding["controller"]
        private_payload = {
            "kind": "BROKER_DISCOVERY_ROUTE",
            "broker_instance_id": self.broker_instance_id,
            "broker_epoch": self._epoch,
            "resource_kind": resource_kind,
            "selected_owner_instance_id": selected_owner_id,
            "public_result_sha256": sha256_value(public_result),
        }
        packet = controller._private_packet(
            kind="E4_BROKER_ROUTE",
            episode_binding=self._controller_binding["episode_binding"],
            public_view=self._controller_binding["public_view"],
            private_payload=private_payload,
        )
        self._private_route_packets.append(packet)
        return public_result

    def revoke_primary(
        self, *, native_event_sha256: str, logical_minute: int
    ) -> Dict[str, Any]:
        if self._controller_binding is None:
            raise ValueError("broker has no verified controller binding")
        if self._primary_revoked:
            raise ValueError("primary already revoked")
        self._primary_revoked = True
        self._epoch += 1
        controller = self._controller_binding["controller"]
        payload = {
            "kind": "PRIMARY_REVOKED",
            "broker_instance_id": self.broker_instance_id,
            "broker_epoch": self._epoch,
            "native_event_sha256": native_event_sha256,
            "logical_minute": logical_minute,
            "source_topology_receipt_id": self._controller_binding[
                "topology_receipt_id"
            ],
        }
        return controller._private_packet(
            kind="E4_PRIMARY_REVOKE",
            episode_binding=self._controller_binding["episode_binding"],
            public_view=self._controller_binding["public_view"],
            private_payload=payload,
        )

    def resolve_private(self, opaque_handle: str) -> Optional[Dict[str, Any]]:
        owner_id = self._handle_to_owner.get(opaque_handle)
        if owner_id is None:
            return None
        for entry in self._topology:
            if entry["owner_instance_id"] == owner_id:
                return copy.deepcopy(entry)
        return None

    def private_route_packets(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._private_route_packets)
