#!/usr/bin/env python3
"""Target-native Authority, fence, transition, restore, and readback gate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce001_g5.common import sha256, verify_signed_native_with_key
from ce001_g5.model import (
    build_topology,
    frozen_operation_violation,
    material_operation_closure,
    material_projection,
    resource_owner_for_topology,
)


class TargetService:
    def __init__(self, config: Path, store: Path, mode: str) -> None:
        trust = json.loads(config.read_text(encoding="utf-8"))
        self.expected = trust["operation"]
        self.topology = trust["topology"]
        self.trusted_owner_keys = trust["trusted_owner_keys"]
        self.trusted_channel_key = trust["trusted_channel_key"]
        self.runtime_id = trust["runtime_id"]
        try:
            canonical_topology = build_topology(self.topology["derived_stratum"])
            self.bootstrap_failure = (
                None
                if self.topology == canonical_topology
                else "NON_CANONICAL_TRUSTED_TOPOLOGY"
            )
        except (KeyError, TypeError, ValueError):
            self.bootstrap_failure = "MALFORMED_TRUSTED_TOPOLOGY"
        self.store = store
        self.mode = mode
        self.lost_fence_after_restart = False
        if store.exists():
            self.state = json.loads(store.read_text(encoding="utf-8"))
        else:
            self.state = {
                "object_id": self.expected["object_id"],
                "object_revision": self.expected["object_revision"],
                "power_state": "OFF",
                "max_resource_fence": 0,
                "authority_channel_sequence": 0,
                "authority_snapshot": None,
                "authority_snapshot_sha256": None,
                "min_coordinator_epoch": 1,
                "transitions": [],
                "idempotency": {},
            }
            self._save()

    def _save(self) -> None:
        self.store.parent.mkdir(parents=True, exist_ok=True)
        self.store.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def native(self, outcome: str, **detail: Any) -> dict[str, Any]:
        return {
            "native": {
                "schema": "ce001.g5.target-native-outcome.v2",
                "target_service_pid": os.getpid(),
                "runtime_id": self.runtime_id,
                "mode": self.mode,
                "outcome": outcome,
                "object_id": self.state["object_id"],
                "object_revision": self.state["object_revision"],
                "power_state": self.state["power_state"],
                "max_resource_fence": self.state["max_resource_fence"],
                "authority_channel_sequence": self.state[
                    "authority_channel_sequence"
                ],
                "min_coordinator_epoch": self.state["min_coordinator_epoch"],
                **detail,
            }
        }

    def binding_failure(self, operation: dict[str, Any], now: int) -> str | None:
        if operation.get("standing", {}).get("status") != "ADJUDICATED_CURRENT":
            return "TARGET_REJECTED_STANDING"
        frozen_violation = frozen_operation_violation(operation)
        if frozen_violation:
            return "TARGET_REJECTED_SUBSTITUTION_INVALID_FROZEN_Q"
        if now > int(self.expected["expiry"]):
            return "TARGET_REJECTED_EXPIRED"
        try:
            actual_projection = material_projection(operation)
            expected_projection = material_projection(self.expected)
            computed = material_operation_closure(operation)
        except (KeyError, TypeError, ValueError):
            return "TARGET_REJECTED_MALFORMED_BINDING"
        if (
            actual_projection != expected_projection
            or computed != operation.get("material_closure_sha256")
            or computed != material_operation_closure(self.expected)
        ):
            return "TARGET_REJECTED_BINDING_MISMATCH"
        return None

    def sync_authority(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        if self.bootstrap_failure:
            return self.native(
                "TARGET_REJECTED_TRUST_BOOTSTRAP",
                bootstrap_failure=self.bootstrap_failure,
            )
        if not verify_signed_native_with_key(snapshot, self.trusted_channel_key):
            return self.native("TARGET_REJECTED_FORGED_AUTHORITY_SNAPSHOT")
        try:
            native = snapshot["native"]
            if native["schema"] != "ce001.g5.authority-channel-snapshot.v1":
                return self.native("TARGET_REJECTED_AUTHORITY_SNAPSHOT_SCHEMA")
            if native["topology"] != self.topology:
                return self.native("TARGET_REJECTED_TOPOLOGY_MISMATCH")
            if native["operation_closure_sha256"] != material_operation_closure(
                self.expected
            ):
                return self.native("TARGET_REJECTED_AUTHORITY_OPERATION_MISMATCH")
            sequence = int(native["channel_sequence"])
            if sequence < int(self.state["authority_channel_sequence"]):
                return self.native("TARGET_REJECTED_STALE_AUTHORITY_SNAPSHOT")
            if set(native["owner_heads"]) != set(self.topology["required_owners"]):
                return self.native("TARGET_REJECTED_INCOMPLETE_OWNER_HEAD_SET")
            if set(native["owner_status"]) != set(self.topology["required_owners"]):
                return self.native("TARGET_REJECTED_INCOMPLETE_OWNER_STATUS_SET")
        except (KeyError, TypeError, ValueError):
            return self.native("TARGET_REJECTED_MALFORMED_AUTHORITY_SNAPSHOT")
        self.state["authority_channel_sequence"] = sequence
        self.state["authority_snapshot"] = native
        self.state["authority_snapshot_sha256"] = sha256(snapshot)
        if not (
            self.mode == "restart_loses_fence" and self.lost_fence_after_restart
        ):
            self.state["max_resource_fence"] = max(
                int(self.state["max_resource_fence"]),
                int(native["resource_fence"]),
            )
        self._save()
        return self.native(
            "AUTHORITY_SNAPSHOT_SYNCED",
            derived_stratum=self.topology["derived_stratum"],
            owner_heads=native["owner_heads"],
            resource_fence=native["resource_fence"],
        )

    def validate_owner_receipt(
        self,
        receipt: dict[str, Any],
        *,
        owner_id: str,
        phase: str,
        expected_outcomes: set[str],
        require_channel_latest: bool = True,
    ) -> str | None:
        try:
            if receipt["native"]["owner_id"] != owner_id:
                return "WRONG_OWNER"
            if not verify_signed_native_with_key(
                receipt, self.trusted_owner_keys[owner_id]
            ):
                return "FORGED_RECEIPT"
            native = receipt["native"]
            claim = native["authority_claim"]
            if (
                claim["topology_id"] != self.topology["topology_id"]
                or claim["topology_closure_sha256"]
                != self.topology["topology_closure_sha256"]
                or claim["closure_kind"] != self.topology["closure_kind"]
                or claim["delegatee"] != self.topology["delegatee"]
                or claim["role_owners"] != self.topology["role_owners"]
            ):
                return "TOPOLOGY_CLAIM_MISMATCH"
            if native["phase"] != phase or native["outcome"] not in expected_outcomes:
                return "OWNER_NATIVE_OUTCOME_NOT_ELIGIBLE"
            snapshot = self.state["authority_snapshot"]
            if snapshot is None:
                return "MISSING_AUTHORITY_SNAPSHOT"
            if native["authority_status"] != "ACTIVE":
                return "OWNER_NOT_ACTIVE"
            if int(native["owner_head"]) != int(snapshot["owner_heads"][owner_id]):
                return "STALE_OWNER_HEAD"
            if (
                require_channel_latest
                and sha256(receipt)
                != snapshot["latest_receipt_hashes"].get(owner_id)
            ):
                return "OWNER_RECEIPT_NOT_CHANNEL_CURRENT"
            expected_binding = {
                **material_projection(self.expected),
                "material_closure_sha256": material_operation_closure(self.expected),
            }
            if native["exact_binding"] != expected_binding:
                return "OWNER_BINDING_MISMATCH"
        except (KeyError, TypeError, ValueError):
            return "MALFORMED_OWNER_RECEIPT"
        return None

    def execution_authority_failure(self, command: dict[str, Any]) -> str | None:
        snapshot = self.state["authority_snapshot"]
        if snapshot is None:
            return "TARGET_REJECTED_MISSING_AUTHORITY_SNAPSHOT"
        required = set(self.topology["required_owners"])
        receipts = command.get("owner_execute_receipts")
        if not isinstance(receipts, dict) or set(receipts) != required:
            return "TARGET_REJECTED_REQUIRED_OWNER_SET"
        if any(snapshot["owner_status"].get(owner) != "ACTIVE" for owner in required):
            return "TARGET_REJECTED_OWNER_NOT_CURRENT"
        if int(snapshot["coordinator_epoch"]) != int(
            self.state["min_coordinator_epoch"]
        ):
            return "TARGET_REJECTED_STALE_COORDINATOR_SNAPSHOT"
        for owner_id in sorted(required):
            failure = self.validate_owner_receipt(
                receipts[owner_id],
                owner_id=owner_id,
                phase="EXECUTE_CHECK",
                expected_outcomes={"EXECUTE_AUTHORITY_CURRENT"},
            )
            if failure:
                return f"TARGET_REJECTED_{failure}"
        reservation = command.get("reservation_receipt")
        resource_owner = resource_owner_for_topology(self.topology)
        failure = self.validate_owner_receipt(
            reservation,
            owner_id=resource_owner,
            phase="RESERVE",
            expected_outcomes={
                "RESOURCE_RESERVED_EXACT_OPERATION",
                "RESOURCE_RESERVATION_IDEMPOTENT",
            },
            require_channel_latest=False,
        )
        if failure:
            return f"TARGET_REJECTED_RESERVATION_{failure}"
        if (
            self.mode == "strict"
            and sha256(reservation) != snapshot["resource_fence_receipt_hash"]
        ):
            return "TARGET_REJECTED_STALE_RESOURCE_FENCE_RECEIPT"
        return None

    def execute(self, command: dict[str, Any]) -> dict[str, Any]:
        operation = command["operation"]
        failure = self.binding_failure(operation, int(command["now"]))
        if failure:
            return self.native(failure)
        action = command["action"]
        operation_id = command["target_operation_id"]
        caused_by = command.get("caused_by_operation_id")
        if action == "ENERGIZE":
            authority_failure = self.execution_authority_failure(command)
            if authority_failure:
                return self.native(authority_failure)
            if operation_id != self.expected["operation_id"]:
                return self.native("TARGET_REJECTED_OPERATION_ID")
            reservation = command["reservation_receipt"]
            fence = int(reservation["native"]["detail"]["fence_epoch"])
            snapshot_fence = int(
                self.state["authority_snapshot"]["resource_fence"]
            )
            required_fence = max(
                int(self.state["max_resource_fence"]), snapshot_fence
            )
            if self.mode == "restart_loses_fence" and self.lost_fence_after_restart:
                required_fence = int(self.state["max_resource_fence"])
            if self.mode != "ignore_fence" and fence < required_fence:
                return self.native(
                    "STALE_FENCE_REJECTED",
                    supplied_resource_fence=fence,
                    required_resource_fence=required_fence,
                )
        elif action == "DEENERGIZE":
            if self.state["authority_snapshot"] is None:
                return self.native("TARGET_REJECTED_MISSING_AUTHORITY_SNAPSHOT")
            if all(
                status == "ACTIVE"
                for status in self.state["authority_snapshot"][
                    "owner_status"
                ].values()
            ):
                return self.native(
                    "TARGET_REJECTED_COMPENSATION_WITHOUT_AUTHORITY_LOSS"
                )
            if operation["scope"]["compensation"] != "DEENERGIZE_ON_AUTHORITY_LOSS":
                return self.native("TARGET_REJECTED_COMPENSATION_SCOPE")
            if caused_by != self.expected["operation_id"]:
                return self.native("TARGET_REJECTED_COMPENSATION_CAUSE")
            fence = int(self.state["authority_snapshot"]["resource_fence"])
            required_fence = fence
        else:
            return self.native("TARGET_REJECTED_UNKNOWN_ACTION")
        coordinator_epoch = int(command.get("coordinator_epoch", 1))
        current_coordinator_epoch = int(self.state["min_coordinator_epoch"])
        if coordinator_epoch < current_coordinator_epoch:
            return self.native(
                "STALE_COORDINATOR_EPOCH_REJECTED",
                supplied_coordinator_epoch=coordinator_epoch,
                required_coordinator_epoch=current_coordinator_epoch,
            )
        if coordinator_epoch > current_coordinator_epoch:
            return self.native(
                "UNISSUED_COORDINATOR_EPOCH_REJECTED",
                supplied_coordinator_epoch=coordinator_epoch,
                required_coordinator_epoch=current_coordinator_epoch,
            )
        idempotency_key = f"{action}:{operation_id}"
        if idempotency_key in self.state["idempotency"]:
            return self.native(
                "IDEMPOTENT_REPLAY",
                prior_transition=self.state["idempotency"][idempotency_key],
            )
        previous = self.state["power_state"]
        next_state = "ENERGIZED" if action == "ENERGIZE" else "OFF"
        transition = {
            "sequence": len(self.state["transitions"]) + 1,
            "target_operation_id": operation_id,
            "caused_by_operation_id": caused_by,
            "action": action,
            "from": previous,
            "to": next_state,
            "resource_fence": fence,
            "required_resource_fence_at_arrival": required_fence,
            "stale_fence_accepted": fence < required_fence,
            "coordinator_epoch": coordinator_epoch,
            "authority_snapshot_sha256": self.state[
                "authority_snapshot_sha256"
            ],
            "material_closure_sha256": operation["material_closure_sha256"],
        }
        self.state["power_state"] = next_state
        self.state["max_resource_fence"] = max(
            int(self.state["max_resource_fence"]), fence
        )
        self.state["transitions"].append(transition)
        self.state["idempotency"][idempotency_key] = transition
        self._save()
        return self.native(
            "ENERGIZED" if action == "ENERGIZE" else "DEENERGIZED",
            transition=transition,
        )

    def restore(self, takeover_lease: dict[str, Any]) -> dict[str, Any]:
        if not verify_signed_native_with_key(
            takeover_lease, self.trusted_channel_key
        ):
            return self.native("TARGET_REJECTED_FORGED_TAKEOVER_LEASE")
        try:
            lease_native = takeover_lease["native"]
            if lease_native["schema"] != "ce001.g5.takeover-lease.v1":
                return self.native("TARGET_REJECTED_TAKEOVER_LEASE_SCHEMA")
            capsule = lease_native["capsule"]
        except (KeyError, TypeError):
            return self.native("TARGET_REJECTED_MALFORMED_TAKEOVER_LEASE")
        mismatches: list[str] = []
        required = {
            "schema",
            "operation",
            "operation_sha256",
            "topology_closure_sha256",
            "authority_snapshot_sha256",
            "source_target_state_sha256",
            "previous_coordinator_epoch",
            "coordinator_epoch",
            "acceptance_status",
            "runtime_scope",
        }
        missing = sorted(required - set(capsule))
        if not missing:
            if capsule["schema"] != "ce001.g5.migration-capsule.v3":
                mismatches.append("schema")
            if capsule["operation"] != self.expected:
                mismatches.append("exact_operation")
            if capsule["operation_sha256"] != sha256(capsule["operation"]):
                mismatches.append("operation_sha256")
            if (
                capsule["topology_closure_sha256"]
                != self.topology["topology_closure_sha256"]
            ):
                mismatches.append("topology_closure_sha256")
            if (
                capsule["authority_snapshot_sha256"]
                != self.state["authority_snapshot_sha256"]
            ):
                mismatches.append("authority_snapshot_sha256")
            if capsule["source_target_state_sha256"] != sha256(self.state):
                mismatches.append("source_target_state_sha256")
            if capsule["acceptance_status"] != "PENDING_OUTSIDE_G5":
                mismatches.append("acceptance_status")
            if capsule["runtime_scope"] != "SHARED_DURABLE_STORE_PROCESS_RESTART":
                mismatches.append("runtime_scope")
            if int(capsule["previous_coordinator_epoch"]) != int(
                self.state["min_coordinator_epoch"]
            ):
                mismatches.append("previous_coordinator_epoch")
            if int(capsule["coordinator_epoch"]) != int(
                capsule["previous_coordinator_epoch"]
            ) + 1:
                mismatches.append("non_monotonic_coordinator_epoch")
            if int(capsule["coordinator_epoch"]) <= int(
                self.state["min_coordinator_epoch"]
            ):
                mismatches.append("stale_coordinator_epoch")
        if missing or mismatches:
            outcome = (
                "STALE_MIGRATION_CAPSULE_REJECTED"
                if mismatches == ["stale_coordinator_epoch"]
                else "MIGRATION_LOSS_DETECTED"
            )
            return self.native(
                outcome, missing_fields=missing, mismatched_fields=mismatches
            )
        self.state["min_coordinator_epoch"] = int(capsule["coordinator_epoch"])
        self._save()
        return self.native(
            "MIGRATION_PROCESS_RESTART_RESTORED",
            runtime_scope=capsule["runtime_scope"],
        )

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        op = command["op"]
        if op == "HELLO":
            return self.native(
                "TARGET_READY" if not self.bootstrap_failure else "TARGET_BOOTSTRAP_INVALID",
                store=str(self.store),
                bootstrap_failure=self.bootstrap_failure,
                trusted_topology_closure_sha256=self.topology[
                    "topology_closure_sha256"
                ],
            )
        if op == "SYNC_AUTHORITY":
            return self.sync_authority(command["authority_snapshot"])
        if op == "ADVANCE_FENCE":
            return self.native("TARGET_REJECTED_NAKED_FENCE_INJECTION")
        if op == "ADVANCE_COORDINATOR_EPOCH":
            return self.native("TARGET_REJECTED_NAKED_COORDINATOR_EPOCH")
        if op == "EXECUTE":
            return self.execute(command)
        if op == "RESTORE":
            return self.restore(command["takeover_lease"])
        if op == "READBACK":
            return self.native("READBACK", target_state=self.state)
        if op == "RESTART":
            if self.mode == "restart_loses_fence":
                self.state["max_resource_fence"] = 0
                self.lost_fence_after_restart = True
                self._save()
            return self.native("TARGET_RESTARTED")
        return self.native("UNKNOWN_COMMAND", op=op)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=["strict", "ignore_fence", "restart_loses_fence"],
        required=True,
    )
    args = parser.parse_args()
    service = TargetService(args.config, args.store, args.mode)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = service.handle(json.loads(line))
        except Exception as exc:
            response = {
                "native": {
                    "schema": "ce001.g5.target-service-error.v1",
                    "outcome": "SERVICE_ERROR",
                    "error_type": type(exc).__name__,
                }
            }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
