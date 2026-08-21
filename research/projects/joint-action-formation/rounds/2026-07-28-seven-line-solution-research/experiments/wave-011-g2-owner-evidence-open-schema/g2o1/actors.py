"""Independent Principal actors and signed owner-evidence envelopes.

Only ``workers/owner_worker.py`` instantiates :class:`PrincipalActor` with a
private key.  The runner and method workers receive the returned public
envelopes and public keys, never the private key bytes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass
class PrincipalActor:
    principal_id: str
    actor_id: str
    local_view: dict[str, Any]
    _private_key: Ed25519PrivateKey

    @classmethod
    def create(
        cls,
        world_id: str,
        principal_id: str,
        local_view: dict[str, Any],
    ) -> "PrincipalActor":
        return cls(
            principal_id=principal_id,
            actor_id=f"actor:{world_id}:{principal_id}",
            local_view=local_view,
            # The key exists only in this actor subprocess.  It is deliberately
            # random: semantic reproducibility must not make owner credentials
            # reconstructible from parent-visible inputs.
            _private_key=Ed25519PrivateKey.generate(),
        )

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        ).hex()

    def sign(
        self,
        *,
        action: str,
        relation_version: str,
        version_digest: str,
        sequence: int,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            "domain": "G2-O1-OWNER-EVIDENCE-v1",
            "actor_id": self.actor_id,
            "principal_id": self.principal_id,
            "action": action,
            "relation_version": relation_version,
            "version_digest": version_digest,
            "sequence": sequence,
            "local_view_digest": digest(self.local_view),
            "body": body,
        }
        return {
            **payload,
            "payload_digest": digest(payload),
            "signature": self._private_key.sign(
                canonical_bytes(payload)
            ).hex(),
        }


def verify_event(event: dict[str, Any], public_key_hex: str) -> bool:
    try:
        payload = {
            key: event[key]
            for key in (
                "domain",
                "actor_id",
                "principal_id",
                "action",
                "relation_version",
                "version_digest",
                "sequence",
                "local_view_digest",
                "body",
            )
        }
        if (
            payload["domain"] != "G2-O1-OWNER-EVIDENCE-v1"
            or digest(payload) != event["payload_digest"]
        ):
            return False
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(public_key_hex)
        ).verify(
            bytes.fromhex(event["signature"]),
            canonical_bytes(payload),
        )
        return True
    except (InvalidSignature, KeyError, TypeError, ValueError):
        return False


def verified_events(
    events: Iterable[dict[str, Any]],
    public_keys: dict[str, str],
) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for event in events:
        actor_id = event.get("actor_id")
        key = (str(actor_id), event.get("sequence"))
        public_key = public_keys.get(str(actor_id))
        if (
            public_key
            and key not in seen
            and verify_event(event, public_key)
        ):
            valid.append(event)
            seen.add(key)
    return valid
