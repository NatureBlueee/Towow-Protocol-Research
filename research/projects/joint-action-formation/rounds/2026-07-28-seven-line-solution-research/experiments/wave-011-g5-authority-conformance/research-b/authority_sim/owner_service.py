#!/usr/bin/env python3
"""Independent synthetic Authority owner process.

This service intentionally uses a small textbook-RSA signer implemented with the
Python standard library.  It is sufficient to demonstrate that the coordinator
does not possess the owner private key.  It is not production cryptography.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def atomic_json_write(path: Path, value: Any, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_bytes(canonical_bytes(value) + b"\n")
    os.chmod(temp, 0o600 if private else 0o644)
    os.replace(temp, path)


def is_probable_prime(number: int, rounds: int = 12) -> bool:
    if number < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small_primes:
        if number == prime:
            return True
        if number % prime == 0:
            return False
    divisor = number - 1
    exponent = 0
    while divisor % 2 == 0:
        exponent += 1
        divisor //= 2
    for _ in range(rounds):
        base = secrets.randbelow(number - 3) + 2
        witness = pow(base, divisor, number)
        if witness in (1, number - 1):
            continue
        for _ in range(exponent - 1):
            witness = pow(witness, 2, number)
            if witness == number - 1:
                break
        else:
            return False
    return True


def generate_prime(bits: int) -> int:
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if is_probable_prime(candidate):
            return candidate


def load_or_create_key(private_path: Path, public_path: Path) -> dict[str, int]:
    if private_path.exists() and public_path.exists():
        return json.loads(private_path.read_text(encoding="utf-8"))
    # A roughly 544-bit modulus is larger than a SHA-256 digest.  This signer is a
    # simulation authenticity primitive, not a replacement for Ed25519/RSA-PSS.
    public_exponent = 65537
    while True:
        p = generate_prime(272)
        q = generate_prime(272)
        if p == q:
            continue
        phi = (p - 1) * (q - 1)
        if phi % public_exponent != 0:
            break
    modulus = p * q
    private_exponent = pow(public_exponent, -1, phi)
    private_key = {"n": modulus, "e": public_exponent, "d": private_exponent}
    public_key = {"n": modulus, "e": public_exponent}
    atomic_json_write(private_path, private_key, private=True)
    atomic_json_write(public_path, public_key)
    return private_key


def sign_payload(payload: dict[str, Any], key: dict[str, int]) -> str:
    digest = int.from_bytes(hashlib.sha256(canonical_bytes(payload)).digest(), "big")
    return format(pow(digest, key["d"], key["n"]), "x")


def initial_state(owner_id: str) -> dict[str, Any]:
    return {
        "owner_id": owner_id,
        "head": 1,
        "native_outcome": "ACTIVE",
        "native_error": None,
        "model_version": "owner-native-v1",
        "effective_at_ns": time.time_ns(),
        "outage": False,
        "fork": None,
        "fork_read_counter": 0,
        "consent_lease_until_ns": 0,
        "consent_lease_tx": None,
        "prepared": {},
        "pending_revocation": False,
        "reservation_epoch": 0,
        "reservation": None,
        "commitments": {},
        "command_index": 0,
    }


class OwnerService:
    def __init__(
        self,
        owner_id: str,
        store_path: Path,
        private_key_path: Path,
        public_key_path: Path,
    ) -> None:
        self.owner_id = owner_id
        self.store_path = store_path
        self.private_key = load_or_create_key(private_key_path, public_key_path)
        if store_path.exists():
            self.state = json.loads(store_path.read_text(encoding="utf-8"))
        else:
            self.state = initial_state(owner_id)
            self.save()

    def save(self) -> None:
        atomic_json_write(self.store_path, self.state, private=True)

    def signed(self, result: dict[str, Any]) -> dict[str, Any]:
        envelope = {
            "owner_id": self.owner_id,
            "process_id": os.getpid(),
            "result": result,
        }
        envelope["signature"] = sign_payload(envelope, self.private_key)
        return envelope

    def snapshot(self, requested_branch: str | None = None) -> dict[str, Any]:
        if self.state["fork"]:
            branches = self.state["fork"]
            branch = requested_branch
            if branch not in branches:
                branch = ("left", "right")[self.state["fork_read_counter"] % 2]
                self.state["fork_read_counter"] += 1
            view = dict(branches[branch])
            view["branch"] = branch
            return view
        return {
            "head": self.state["head"],
            "native_outcome": self.state["native_outcome"],
            "native_error": self.state["native_error"],
            "model_version": self.state["model_version"],
            "effective_at_ns": self.state["effective_at_ns"],
            "branch": "main",
        }

    def active_holds(self) -> list[str]:
        now = time.time_ns()
        return [
            txid
            for txid, hold in self.state["prepared"].items()
            if hold["expires_at_ns"] > now and hold["state"] == "PREPARED"
        ]

    def apply_pending_revocation_if_possible(self) -> None:
        if not self.state["pending_revocation"]:
            return
        now = time.time_ns()
        if self.active_holds() or self.state["consent_lease_until_ns"] > now:
            return
        self.state["pending_revocation"] = False
        self.state["head"] += 1
        self.state["native_outcome"] = "REVOKED"
        self.state["effective_at_ns"] = now

    def read_result(self, request: dict[str, Any]) -> dict[str, Any]:
        self.apply_pending_revocation_if_possible()
        if self.state["outage"]:
            return {
                "ok": False,
                "native_outcome": None,
                "native_error": "SERVICE_UNAVAILABLE",
                "model_version": self.state["model_version"],
                "freshness_ns": None,
            }
        snapshot = self.snapshot(request.get("branch"))
        return {
            "ok": True,
            **snapshot,
            "freshness_ns": max(0, time.time_ns() - snapshot["effective_at_ns"]),
        }

    def mutate(self, action: str) -> dict[str, Any]:
        now = time.time_ns()
        if action in {"revoke", "reject"}:
            if self.active_holds() or self.state["consent_lease_until_ns"] > now:
                self.state["pending_revocation"] = True
                self.save()
                return {
                    "ok": True,
                    "native_outcome": "DEFERRED_BY_OWNER_PROMISE",
                    "native_error": None,
                    "effective": False,
                    "active_holds": self.active_holds(),
                    "lease_until_ns": self.state["consent_lease_until_ns"],
                }
            self.state["head"] += 1
            self.state["native_outcome"] = (
                "REVOKED" if action == "revoke" else "EXPLICIT_REJECT"
            )
            self.state["effective_at_ns"] = now
            self.state["fork"] = None
            self.save()
            return {
                "ok": True,
                "native_outcome": self.state["native_outcome"],
                "native_error": None,
                "effective": True,
                "head": self.state["head"],
            }
        if action == "outage":
            self.state["outage"] = True
            self.save()
            return {
                "ok": True,
                "native_outcome": None,
                "native_error": "SERVICE_UNAVAILABLE",
                "effective": True,
            }
        if action == "recover":
            self.state["outage"] = False
            self.save()
            return {
                "ok": True,
                "native_outcome": self.state["native_outcome"],
                "native_error": None,
                "effective": True,
            }
        if action == "fork":
            main = self.snapshot("main")
            right = dict(main)
            right["head"] = main["head"] + 1
            right["native_outcome"] = "REVOKED"
            right["effective_at_ns"] = now
            self.state["fork"] = {"left": main, "right": right}
            self.state["fork_read_counter"] = 0
            self.save()
            return {
                "ok": True,
                "native_outcome": "FORKED_SIGNED_HEADS",
                "native_error": None,
                "effective": True,
                "heads": [main["head"], right["head"]],
            }
        raise ValueError(f"unsupported mutation: {action}")

    def sign(self, request: dict[str, Any]) -> dict[str, Any]:
        read = self.read_result({})
        if not read["ok"]:
            return read
        if read["native_outcome"] != "ACTIVE":
            return {**read, "ok": False}
        if request.get("expected_head") != read["head"]:
            return {
                **read,
                "ok": False,
                "native_error": "HEAD_MISMATCH",
            }
        lease_ms = int(request.get("stability_lease_ms", 0))
        if lease_ms:
            self.state["consent_lease_until_ns"] = time.time_ns() + lease_ms * 1_000_000
            self.state["consent_lease_tx"] = request["txid"]
        commitment = {
            "txid": request["txid"],
            "operation_digest": request["operation_digest"],
            "head": read["head"],
            "branch": read["branch"],
            "lease_until_ns": self.state["consent_lease_until_ns"],
        }
        self.state["commitments"][request["txid"]] = commitment
        self.save()
        return {
            "ok": True,
            "native_outcome": "SIGNED_COMMITMENT",
            "native_error": None,
            "model_version": self.state["model_version"],
            "head": read["head"],
            "freshness_ns": read["freshness_ns"],
            "commitment": commitment,
        }

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        read = self.read_result({})
        if not read["ok"] or read["native_outcome"] != "ACTIVE":
            return {**read, "ok": False}
        if request["txid"] not in self.state["commitments"]:
            return {
                **read,
                "ok": False,
                "native_error": "MISSING_COMMITMENT",
            }
        if request.get("expected_head") != read["head"]:
            return {
                **read,
                "ok": False,
                "native_error": "HEAD_MISMATCH",
            }
        hold_ms = int(request["hold_ms"])
        self.state["prepared"][request["txid"]] = {
            "state": "PREPARED",
            "head": read["head"],
            "operation_digest": request["operation_digest"],
            "expires_at_ns": time.time_ns() + hold_ms * 1_000_000,
        }
        self.save()
        return {
            "ok": True,
            "native_outcome": "PREPARED_HOLD",
            "native_error": None,
            "head": read["head"],
            "expires_at_ns": self.state["prepared"][request["txid"]][
                "expires_at_ns"
            ],
        }

    def confirm(self, request: dict[str, Any]) -> dict[str, Any]:
        hold = self.state["prepared"].get(request["txid"])
        if not hold:
            return {
                "ok": False,
                "native_outcome": None,
                "native_error": "NO_PREPARED_HOLD",
            }
        if hold["state"] != "PREPARED" or hold["expires_at_ns"] <= time.time_ns():
            return {
                "ok": False,
                "native_outcome": None,
                "native_error": "HOLD_EXPIRED_OR_RESOLVED",
            }
        return {
            "ok": True,
            "native_outcome": "HOLD_CURRENT",
            "native_error": None,
            "head": hold["head"],
            "expires_at_ns": hold["expires_at_ns"],
        }

    def resolve(self, request: dict[str, Any], state: str) -> dict[str, Any]:
        hold = self.state["prepared"].get(request["txid"])
        if hold:
            hold["state"] = state
        if request["txid"] == self.state["consent_lease_tx"]:
            self.state["consent_lease_until_ns"] = 0
            self.state["consent_lease_tx"] = None
        self.apply_pending_revocation_if_possible()
        self.save()
        return {
            "ok": True,
            "native_outcome": state,
            "native_error": None,
            "pending_revocation": self.state["pending_revocation"],
        }

    def reserve(self, request: dict[str, Any]) -> dict[str, Any]:
        read = self.read_result({})
        if not read["ok"] or read["native_outcome"] != "ACTIVE":
            return {**read, "ok": False}
        existing = self.state["reservation"]
        if existing and existing["state"] == "HELD":
            if existing["txid"] == request["txid"]:
                return {
                    "ok": True,
                    "native_outcome": "IDEMPOTENT_RESERVATION",
                    "native_error": None,
                    "reservation": existing,
                }
            return {
                "ok": False,
                "native_outcome": "RESERVATION_CONFLICT",
                "native_error": None,
                "reservation": existing,
            }
        self.state["reservation_epoch"] += 1
        self.state["reservation"] = {
            "state": "HELD",
            "txid": request["txid"],
            "operation_digest": request["operation_digest"],
            "epoch": self.state["reservation_epoch"],
            "expires_at_ns": time.time_ns()
            + int(request.get("lease_ms", 5_000)) * 1_000_000,
        }
        self.save()
        return {
            "ok": True,
            "native_outcome": "RESERVED",
            "native_error": None,
            "reservation": self.state["reservation"],
        }

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        self.state["command_index"] += 1
        command = request["command"]
        if command == "read":
            result = self.read_result(request)
        elif command == "mutate":
            result = self.mutate(request["action"])
        elif command == "sign":
            result = self.sign(request)
        elif command == "prepare":
            result = self.prepare(request)
        elif command == "confirm":
            result = self.confirm(request)
        elif command == "commit":
            result = self.resolve(request, "COMMITTED")
        elif command == "abort":
            result = self.resolve(request, "ABORTED")
        elif command == "reserve":
            result = self.reserve(request)
        elif command == "shutdown":
            result = {"ok": True, "native_outcome": "SHUTDOWN", "native_error": None}
        else:
            result = {
                "ok": False,
                "native_outcome": None,
                "native_error": f"UNKNOWN_COMMAND:{command}",
            }
        self.save()
        return self.signed(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    service = OwnerService(
        args.owner_id, args.store, args.private_key, args.public_key
    )
    print(
        json.dumps(
            {
                "ready": True,
                "owner_id": args.owner_id,
                "process_id": os.getpid(),
                "public_key": str(args.public_key),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = service.dispatch(request)
        except Exception as exc:  # pragma: no cover - defensive service boundary
            response = service.signed(
                {
                    "ok": False,
                    "native_outcome": None,
                    "native_error": f"SERVICE_EXCEPTION:{type(exc).__name__}:{exc}",
                }
            )
        print(json.dumps(response, sort_keys=True), flush=True)
        if request.get("command") == "shutdown":
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
