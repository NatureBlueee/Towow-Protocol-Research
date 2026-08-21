#!/usr/bin/env python3
"""Owner-native Authority service for the CE-001 local component model.

The service owns its configured Authority truth, state, key, native outcome,
and resource fence counter. The coordinator can request an act; it cannot
choose the native outcome returned by this process.
"""

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

from ce001_g5.common import canonical_bytes
from ce001_g5.model import (
    frozen_operation_violation,
    material_operation_closure,
    material_projection,
)


class OwnerService:
    def __init__(self, config_path: Path, store_path: Path, key_path: Path) -> None:
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.expected = self.config["operation"]
        self.topology = self.config["topology"]
        self.owner_id = self.config["owner_id"]
        self.stratum = self.topology["derived_stratum"]
        self.store_path = store_path
        self.key_path = key_path
        self.private_key = self._load_or_create_key()
        self.state = self._load_or_create_state()

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

    def _load_or_create_state(self) -> dict[str, Any]:
        if self.store_path.exists():
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        state = {
            "owner_id": self.owner_id,
            "head": 1,
            "authority_status": "ACTIVE",
            "next_fence": 1,
            "reservations": {},
            "history": [],
        }
        self._save(state)
        return state

    def _save(self, state: dict[str, Any] | None = None) -> None:
        if state is not None:
            self.state = state
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def public_key(self) -> str:
        raw = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")

    def signed_native(
        self,
        *,
        phase: str,
        outcome: str,
        now: int,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        native = {
            "schema": "ce001.g5.owner-native-outcome.v1",
            "owner_id": self.owner_id,
            "stratum": self.stratum,
            "authority_claim": {
                "topology_id": self.topology["topology_id"],
                "topology_closure_sha256": self.topology[
                    "topology_closure_sha256"
                ],
                "closure_kind": self.topology["closure_kind"],
                "delegatee": self.topology["delegatee"],
                "role_owners": self.topology["role_owners"],
            },
            "phase": phase,
            "outcome": outcome,
            "owner_head": self.state["head"],
            "authority_status": self.state["authority_status"],
            "observed_at": now,
            "exact_binding": {
                **material_projection(self.expected),
                "material_closure_sha256": material_operation_closure(self.expected),
            },
            "detail": detail or {},
        }
        signature = self.private_key.sign(canonical_bytes(native))
        return {
            "native": native,
            "signature_ed25519_b64": base64.b64encode(signature).decode("ascii"),
            "public_key_ed25519_b64": self.public_key(),
        }

    def binding_outcome(self, operation: dict[str, Any], now: int) -> str | None:
        if operation.get("standing", {}).get("status") != "ADJUDICATED_CURRENT":
            return "STANDING_NOT_EXECUTION_ELIGIBLE"
        frozen_violation = frozen_operation_violation(operation)
        if frozen_violation:
            return frozen_violation
        if now > int(self.expected["expiry"]):
            return "EXPIRED"
        if self.state["authority_status"] != "ACTIVE":
            return "REVOKED"
        try:
            actual_projection = material_projection(operation)
            expected_projection = material_projection(self.expected)
            computed = material_operation_closure(operation)
        except (KeyError, TypeError, ValueError):
            return "BINDING_MALFORMED"
        if (
            actual_projection != expected_projection
            or computed != operation.get("material_closure_sha256")
            or computed != material_operation_closure(self.expected)
        ):
            return "BINDING_MISMATCH"
        return None

    def current_outcome(self, phase: str) -> str:
        if phase == "READ":
            return {
                "U": "UNIFIED_AUTHORITY_CURRENT",
                "D": "EXACT_DELEGATION_CURRENT",
                "P": "OWNER_AUTHORITY_CURRENT",
            }[self.stratum]
        return {
            "SIGN": "SIGNED_EXACT_OPERATION",
            "RESERVE_CHECK": "RESERVE_AUTHORITY_CURRENT",
            "EXECUTE_CHECK": "EXECUTE_AUTHORITY_CURRENT",
        }[phase]

    def check(
        self, *, phase: str, operation: dict[str, Any], expected_head: int | None, now: int
    ) -> dict[str, Any]:
        outcome = self.binding_outcome(operation, now)
        if outcome is None and expected_head is not None and expected_head != self.state["head"]:
            outcome = "STALE_OWNER_HEAD"
        outcome = outcome or self.current_outcome(phase)
        return self.signed_native(phase=phase, outcome=outcome, now=now)

    def reserve_resource(
        self, operation: dict[str, Any], expected_head: int, now: int
    ) -> dict[str, Any]:
        denied = self.binding_outcome(operation, now)
        if denied is None and expected_head != self.state["head"]:
            denied = "STALE_OWNER_HEAD"
        if denied:
            return self.signed_native(phase="RESERVE", outcome=denied, now=now)
        operation_id = operation["operation_id"]
        existing = self.state["reservations"].get(operation_id)
        if existing:
            return self.signed_native(
                phase="RESERVE",
                outcome="RESOURCE_RESERVATION_IDEMPOTENT",
                now=now,
                detail=existing,
            )
        fence = int(self.state["next_fence"])
        self.state["next_fence"] = fence + 1
        reservation = {
            "operation_id": operation_id,
            "q_id": operation["q_id"],
            "q_version": operation["q_version"],
            "object_id": operation["object_id"],
            "object_revision": operation["object_revision"],
            "scope": operation["scope"],
            "expiry": operation["expiry"],
            "material_closure_sha256": operation["material_closure_sha256"],
            "fence_epoch": fence,
        }
        self.state["reservations"][operation_id] = reservation
        self.state["history"].append({"event": "RESOURCE_RESERVED", **reservation})
        self._save()
        return self.signed_native(
            phase="RESERVE",
            outcome="RESOURCE_RESERVED_EXACT_OPERATION",
            now=now,
            detail=reservation,
        )

    def revoke(self, now: int, boundary: str) -> dict[str, Any]:
        self.state["head"] += 1
        self.state["authority_status"] = "REVOKED"
        self.state["history"].append(
            {"event": "AUTHORITY_REVOKED", "boundary": boundary, "at": now}
        )
        self._save()
        return self.signed_native(
            phase="REVOKE",
            outcome="REVOKED",
            now=now,
            detail={"boundary": boundary, "revocation_epoch": self.state["head"]},
        )

    def rotate_resource_fence(self, now: int) -> dict[str, Any]:
        fence = int(self.state["next_fence"])
        self.state["next_fence"] = fence + 1
        self.state["history"].append(
            {"event": "RESOURCE_FENCE_ADVANCED", "fence_epoch": fence, "at": now}
        )
        self._save()
        return self.signed_native(
            phase="FENCE",
            outcome="RESOURCE_FENCE_ADVANCED",
            now=now,
            detail={"fence_epoch": fence},
        )

    def renew_head(self, now: int) -> dict[str, Any]:
        self.state["head"] += 1
        self.state["history"].append(
            {"event": "AUTHORITY_HEAD_RENEWED", "head": self.state["head"], "at": now}
        )
        self._save()
        return self.signed_native(
            phase="RENEW",
            outcome="AUTHORITY_HEAD_RENEWED",
            now=now,
        )

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        op = command["op"]
        if op == "HELLO":
            return {
                "native": {
                    "schema": "ce001.g5.owner-hello.v1",
                    "owner_id": self.owner_id,
                    "stratum": self.stratum,
                    "service_pid": os.getpid(),
                    "store": str(self.store_path),
                },
                "public_key_ed25519_b64": self.public_key(),
            }
        if op in {"READ", "SIGN", "RESERVE_CHECK", "EXECUTE_CHECK"}:
            return self.check(
                phase=op,
                operation=command["operation"],
                expected_head=command.get("expected_head"),
                now=int(command["now"]),
            )
        if op == "RESERVE_RESOURCE":
            return self.reserve_resource(
                command["operation"],
                int(command["expected_head"]),
                int(command["now"]),
            )
        if op == "REVOKE":
            return self.revoke(int(command["now"]), command["boundary"])
        if op == "ROTATE_RESOURCE_FENCE":
            return self.rotate_resource_fence(int(command["now"]))
        if op == "RENEW_HEAD":
            return self.renew_head(int(command["now"]))
        if op == "READ_STATE":
            return {
                "native": {
                    "schema": "ce001.g5.owner-state.v1",
                    "owner_id": self.owner_id,
                    "state": self.state,
                }
            }
        return {"native": {"outcome": "UNKNOWN_COMMAND", "op": op}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    args = parser.parse_args()
    service = OwnerService(args.config, args.store, args.key)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = service.handle(json.loads(line))
        except Exception as exc:
            response = {
                "native": {
                    "schema": "ce001.g5.owner-service-error.v1",
                    "outcome": "SERVICE_ERROR",
                    "error_type": type(exc).__name__,
                }
            }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
