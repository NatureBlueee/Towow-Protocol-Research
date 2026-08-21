#!/usr/bin/env python3
"""Independent JSON-lines owner process with its own store and Ed25519 key."""

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


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class Owner:
    def __init__(self, owner_id: str, store_path: Path, key_path: Path) -> None:
        self.owner_id = owner_id
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
            "mandate": "ACTIVE",
            "stance": "SUPPORT",
            "commitment": "READY_TO_SIGN",
            "outage": False,
            "fork_views": [],
            "reservation": None,
            "next_fence": 1,
            "held_by": None,
            "pending_mutations": [],
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

    def envelope(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "owner_id": self.owner_id,
            "owner_head": self.state["head"],
            "body": body,
        }
        signature = self.private_key.sign(canonical_bytes(payload))
        return {
            "payload": payload,
            "signature_ed25519_b64": base64.b64encode(signature).decode("ascii"),
            "public_key_ed25519_b64": self.public_key(),
        }

    def read(self) -> dict[str, Any]:
        if self.state["outage"]:
            return {"status": "OUTAGE", "owner_id": self.owner_id}
        return {
            "status": "OK",
            "envelope": self.envelope(
                {
                    "mandate": self.state["mandate"],
                    "stance": self.state["stance"],
                    "commitment": self.state["commitment"],
                    "fork_views": self.state["fork_views"],
                }
            ),
        }

    def sign(self, operation_hash: str, expected_head: int) -> dict[str, Any]:
        if self.state["outage"]:
            return {"status": "OUTAGE", "owner_id": self.owner_id}
        if expected_head != self.state["head"]:
            return {"status": "STALE_HEAD", "current_head": self.state["head"]}
        if self.state["mandate"] != "ACTIVE" or self.state["stance"] != "SUPPORT":
            return {"status": "REJECTED", "current_head": self.state["head"]}
        return {
            "status": "SIGNED",
            "envelope": self.envelope(
                {
                    "operation_hash": operation_hash,
                    "decision": "SUPPORT_EXACT_OPERATION",
                }
            ),
        }

    def reserve(self, slot: str, operation_hash: str) -> dict[str, Any]:
        if self.state["outage"]:
            return {"status": "OUTAGE", "owner_id": self.owner_id}
        current = self.state["reservation"]
        if current and current["slot"] == slot and current["operation_hash"] != operation_hash:
            return {"status": "RESERVATION_CONFLICT", "reservation": current}
        if current and current["slot"] == slot:
            return {"status": "IDEMPOTENT_REPLAY", "reservation": current}
        fence = self.state["next_fence"]
        self.state["next_fence"] += 1
        self.state["reservation"] = {
            "slot": slot,
            "operation_hash": operation_hash,
            "fence": fence,
        }
        self.state["history"].append({"event": "RESERVED", "fence": fence})
        self._save()
        return {
            "status": "RESERVED",
            "fence": fence,
            "envelope": self.envelope(self.state["reservation"]),
        }

    def mutate(self, command: dict[str, Any]) -> dict[str, Any]:
        kind = command["kind"]
        if self.state.get("held_by") and kind in {"REVOKE", "REJECT"}:
            self.state["pending_mutations"].append(command)
            self._save()
            return {
                "status": "DEFERRED_BY_HOLD",
                "kind": kind,
                "held_by": self.state["held_by"],
            }
        if kind == "REVOKE":
            self.state["head"] += 1
            self.state["mandate"] = "REVOKED"
            self.state["history"].append(
                {
                    "event": "REVOKED",
                    "effective_step": command.get("effective_step"),
                    "published_step": command.get("published_step"),
                }
            )
        elif kind == "REJECT":
            self.state["head"] += 1
            self.state["stance"] = "REJECT"
        elif kind == "OUTAGE":
            self.state["outage"] = True
        elif kind == "RECOVER":
            self.state["outage"] = False
        elif kind == "FORK":
            head = self.state["head"] + 1
            self.state["head"] = head
            self.state["fork_views"] = [
                {"head": head, "stance": "SUPPORT"},
                {"head": head, "stance": "REVOKED"},
            ]
        elif kind == "RESET":
            self.store_path.unlink(missing_ok=True)
            self.state = self._load_or_create_state()
            return {"status": "RESET", "head": self.state["head"]}
        else:
            return {"status": "UNKNOWN_MUTATION", "kind": kind}
        self._save()
        return {"status": "MUTATED", "kind": kind, "head": self.state["head"]}

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        op = command["op"]
        if op == "HELLO":
            return {
                "status": "READY",
                "owner_id": self.owner_id,
                "public_key_ed25519_b64": self.public_key(),
                "store": str(self.store_path),
            }
        if op == "READ":
            return self.read()
        if op == "SIGN":
            return self.sign(command["operation_hash"], int(command["expected_head"]))
        if op == "RESERVE":
            return self.reserve(command["slot"], command["operation_hash"])
        if op == "HOLD":
            if self.state.get("held_by") not in {None, command["hold_id"]}:
                return {"status": "HOLD_CONFLICT", "held_by": self.state["held_by"]}
            self.state["held_by"] = command["hold_id"]
            self._save()
            return {"status": "HELD", "hold_id": command["hold_id"]}
        if op == "RELEASE":
            if self.state.get("held_by") != command["hold_id"]:
                return {"status": "HOLD_NOT_OWNED"}
            self.state["held_by"] = None
            pending = list(self.state["pending_mutations"])
            self.state["pending_mutations"] = []
            self._save()
            applied = [self.mutate(item) for item in pending]
            return {"status": "RELEASED", "pending_applied": applied}
        if op == "MUTATE":
            return self.mutate(command)
        return {"status": "UNKNOWN_COMMAND", "op": op}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    args = parser.parse_args()
    owner = Owner(args.owner_id, args.store, args.key)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            response = owner.handle(json.loads(line))
        except Exception as exc:  # service boundary must return an explicit error
            response = {"status": "SERVICE_ERROR", "error": type(exc).__name__}
        sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
