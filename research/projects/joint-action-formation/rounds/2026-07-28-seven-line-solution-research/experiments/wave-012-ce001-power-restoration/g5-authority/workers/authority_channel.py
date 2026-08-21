#!/usr/bin/env python3
"""Signed owner/authority head channel consumed by the CE-001 target."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce001_g5.common import canonical_bytes, sha256, verify_signed_native
from ce001_g5.model import material_operation_closure, material_projection


class AuthorityChannel:
    def __init__(self, config_path: Path, store_path: Path, key_path: Path) -> None:
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.operation = self.config["operation"]
        self.topology = self.config["topology"]
        self.trusted_owner_keys = self.config["trusted_owner_keys"]
        self.store_path = store_path
        self.key_path = key_path
        self.private_key = self._load_or_create_key()
        if store_path.exists():
            self.state = json.loads(store_path.read_text(encoding="utf-8"))
        else:
            self.state = {
                "owner_heads": {},
                "owner_status": {},
                "latest_receipt_hashes": {},
                "resource_fence": 0,
                "resource_fence_receipt_hash": None,
                "sequence": 0,
                "coordinator_epoch": 1,
                "latest_takeover_lease_sha256": None,
            }
            self._save()

    def _load_or_create_key(self) -> Ed25519PrivateKey:
        if self.key_path.exists():
            return serialization.load_pem_private_key(
                self.key_path.read_bytes(), password=None
            )
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = Ed25519PrivateKey.generate()
        self.key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        os.chmod(self.key_path, 0o600)
        return key

    def public_key(self) -> str:
        raw = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def response(self, outcome: str, **detail: Any) -> dict[str, Any]:
        return {
            "native": {
                "schema": "ce001.g5.authority-channel-outcome.v1",
                "outcome": outcome,
                "channel_pid": os.getpid(),
                **detail,
            }
        }

    def validate_owner_receipt(self, receipt: dict[str, Any]) -> str | None:
        try:
            native = receipt["native"]
            owner_id = native["owner_id"]
            if owner_id not in self.topology["required_owners"]:
                return "UNTRUSTED_OWNER"
            if receipt["public_key_ed25519_b64"] != self.trusted_owner_keys[owner_id]:
                return "WRONG_OWNER_KEY"
            if not verify_signed_native(receipt):
                return "FORGED_OWNER_RECEIPT"
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
            binding = native["exact_binding"]
            expected = {
                **material_projection(self.operation),
                "material_closure_sha256": material_operation_closure(self.operation),
            }
            if binding != expected:
                return "OWNER_BINDING_MISMATCH"
        except (KeyError, TypeError, ValueError):
            return "MALFORMED_OWNER_RECEIPT"
        return None

    def ingest(self, receipt: dict[str, Any]) -> dict[str, Any]:
        failure = self.validate_owner_receipt(receipt)
        if failure:
            return self.response(failure)
        native = receipt["native"]
        owner_id = native["owner_id"]
        head = int(native["owner_head"])
        prior = int(self.state["owner_heads"].get(owner_id, 0))
        if head < prior:
            return self.response(
                "STALE_OWNER_HEAD_REJECTED",
                owner_id=owner_id,
                supplied_head=head,
                current_head=prior,
            )
        self.state["owner_heads"][owner_id] = head
        self.state["owner_status"][owner_id] = native["authority_status"]
        receipt_hash = sha256(receipt)
        # Resource-fence currentness has its own receipt namespace. Advancing it
        # must not overwrite the latest Authority-act receipt at the same head.
        if native["phase"] != "FENCE":
            self.state["latest_receipt_hashes"][owner_id] = receipt_hash
        if (
            owner_id == self.topology["role_owners"]["RESOURCE"]
            and native["phase"] in {"RESERVE", "FENCE"}
            and native["outcome"]
            in {
                "RESOURCE_RESERVED_EXACT_OPERATION",
                "RESOURCE_RESERVATION_IDEMPOTENT",
                "RESOURCE_FENCE_ADVANCED",
            }
        ):
            fence = int(native["detail"]["fence_epoch"])
            if fence < int(self.state["resource_fence"]):
                return self.response("STALE_RESOURCE_FENCE_REJECTED")
            self.state["resource_fence"] = fence
            self.state["resource_fence_receipt_hash"] = receipt_hash
        self.state["sequence"] += 1
        self._save()
        return self.response(
            "OWNER_RECEIPT_INGESTED",
            owner_id=owner_id,
            owner_head=head,
            authority_status=native["authority_status"],
            resource_fence=self.state["resource_fence"],
            channel_sequence=self.state["sequence"],
        )

    def snapshot(self) -> dict[str, Any]:
        native = {
            "schema": "ce001.g5.authority-channel-snapshot.v1",
            "channel_pid": os.getpid(),
            "topology": self.topology,
            "operation_closure_sha256": material_operation_closure(self.operation),
            "owner_heads": self.state["owner_heads"],
            "owner_status": self.state["owner_status"],
            "latest_receipt_hashes": self.state["latest_receipt_hashes"],
            "resource_fence": self.state["resource_fence"],
            "resource_fence_receipt_hash": self.state[
                "resource_fence_receipt_hash"
            ],
            "channel_sequence": self.state["sequence"],
            "coordinator_epoch": self.state["coordinator_epoch"],
            "latest_takeover_lease_sha256": self.state[
                "latest_takeover_lease_sha256"
            ],
        }
        signature = self.private_key.sign(canonical_bytes(native))
        return {
            "native": native,
            "signature_ed25519_b64": base64.b64encode(signature).decode("ascii"),
            "public_key_ed25519_b64": self.public_key(),
        }

    def issue_takeover_lease(self, command: dict[str, Any]) -> dict[str, Any]:
        current_epoch = int(self.state["coordinator_epoch"])
        requested_epoch = int(command.get("requested_epoch", current_epoch + 1))
        if requested_epoch != current_epoch + 1:
            return self.response(
                "TAKEOVER_EPOCH_NOT_NEXT",
                current_coordinator_epoch=current_epoch,
                requested_epoch=requested_epoch,
            )
        source_state_hash = command.get("source_target_state_sha256")
        authority_snapshot_hash = command.get("authority_snapshot_sha256")
        if not (
            isinstance(source_state_hash, str)
            and len(source_state_hash) == 64
            and isinstance(authority_snapshot_hash, str)
            and len(authority_snapshot_hash) == 64
        ):
            return self.response("TAKEOVER_BINDING_MALFORMED")
        if command.get("runtime_scope") != "SHARED_DURABLE_STORE_PROCESS_RESTART":
            return self.response("TAKEOVER_RUNTIME_SCOPE_REJECTED")
        if command.get("acceptance_status") != "PENDING_OUTSIDE_G5":
            return self.response("TAKEOVER_ACCEPTANCE_REJECTED")
        capsule = {
            "schema": "ce001.g5.migration-capsule.v3",
            "operation": self.operation,
            "operation_sha256": sha256(self.operation),
            "topology_closure_sha256": self.topology[
                "topology_closure_sha256"
            ],
            "authority_snapshot_sha256": authority_snapshot_hash,
            "source_target_state_sha256": source_state_hash,
            "previous_coordinator_epoch": current_epoch,
            "coordinator_epoch": requested_epoch,
            "acceptance_status": "PENDING_OUTSIDE_G5",
            "runtime_scope": "SHARED_DURABLE_STORE_PROCESS_RESTART",
        }
        native = {
            "schema": "ce001.g5.takeover-lease.v1",
            "channel_pid": os.getpid(),
            "issued_from_channel_sequence": self.state["sequence"],
            "capsule": capsule,
        }
        signature = self.private_key.sign(canonical_bytes(native))
        lease = {
            "native": native,
            "signature_ed25519_b64": base64.b64encode(signature).decode("ascii"),
            "public_key_ed25519_b64": self.public_key(),
        }
        self.state["coordinator_epoch"] = requested_epoch
        self.state["latest_takeover_lease_sha256"] = sha256(lease)
        self.state["sequence"] += 1
        self._save()
        return lease

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        if command["op"] == "HELLO":
            return self.response(
                "AUTHORITY_CHANNEL_READY",
                public_key_ed25519_b64=self.public_key(),
                topology_closure_sha256=self.topology[
                    "topology_closure_sha256"
                ],
                store=str(self.store_path),
            )
        if command["op"] == "INGEST_OWNER_RECEIPT":
            return self.ingest(command["receipt"])
        if command["op"] == "SNAPSHOT":
            return self.snapshot()
        if command["op"] == "ISSUE_TAKEOVER_LEASE":
            return self.issue_takeover_lease(command)
        return self.response("UNKNOWN_COMMAND")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    args = parser.parse_args()
    channel = AuthorityChannel(args.config, args.store, args.key)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = channel.handle(json.loads(line))
        except Exception as exc:
            response = {
                "native": {
                    "schema": "ce001.g5.authority-channel-error.v1",
                    "outcome": "SERVICE_ERROR",
                    "error_type": type(exc).__name__,
                }
            }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
