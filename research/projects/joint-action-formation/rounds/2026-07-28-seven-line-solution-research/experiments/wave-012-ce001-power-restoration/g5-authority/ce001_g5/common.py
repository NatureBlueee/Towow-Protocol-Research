from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_signed_native(receipt: dict[str, Any]) -> bool:
    try:
        key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(receipt["public_key_ed25519_b64"])
        )
        key.verify(
            base64.b64decode(receipt["signature_ed25519_b64"]),
            canonical_bytes(receipt["native"]),
        )
        return True
    except (KeyError, ValueError, TypeError):
        return False
    except Exception:
        return False


def verify_signed_native_with_key(
    receipt: dict[str, Any], trusted_public_key_b64: str
) -> bool:
    """Verify against an out-of-band trust anchor, not a receipt-carried key."""
    if receipt.get("public_key_ed25519_b64") != trusted_public_key_b64:
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(trusted_public_key_b64)
        )
        key.verify(
            base64.b64decode(receipt["signature_ed25519_b64"]),
            canonical_bytes(receipt["native"]),
        )
        return True
    except (KeyError, ValueError, TypeError):
        return False
    except Exception:
        return False
