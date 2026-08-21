"""Owner-native readback services for the Wave 011 G6 discriminator.

The services deliberately do not import, open, or derive data from
``private_oracle``.  Each service reads only its own native source file.  The
claim-head ledger is a carrier for claims/current heads; target state,
occurrences, institutional acts and obligations come from separate sources.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: top-level JSON must be an object")
    return value


def public_world_token(world_id: str) -> str:
    return "world-" + hashlib.sha256(
        f"wave-011-g6-public:{world_id}".encode("utf-8")
    ).hexdigest()[:20]


_RELATIONAL_ID_KEYS = {
    "id",
    "occurrence",
    "occurrence_id",
    "operation_id",
    "source_effect",
    "claim_id",
    "cut_id",
}


def _opaque_relational_ids(value: Any, world_id: str, key: str | None = None) -> Any:
    """Remove pair/side labels while preserving cross-owner referential equality."""

    if isinstance(value, dict):
        return {
            item_key: _opaque_relational_ids(item_value, world_id, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_opaque_relational_ids(item, world_id, key) for item in value]
    if isinstance(value, str) and key in _RELATIONAL_ID_KEYS:
        return "id-" + hashlib.sha256(
            f"{world_id}:{value}".encode("utf-8")
        ).hexdigest()[:20]
    return value


@dataclass(frozen=True)
class OwnerResponse:
    owner_id: str
    source_identity: str
    source_hash: str
    observed_at: int
    latency_ms: int
    disclosure_units: int
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        body = {
            "owner_id": self.owner_id,
            "source_identity": self.source_identity,
            "source_hash": self.source_hash,
            "observed_at": self.observed_at,
            "latency_ms": self.latency_ms,
            "disclosure_units": self.disclosure_units,
            "payload": self.payload,
        }
        body["receipt_hash"] = hashlib.sha256(_canonical_bytes(body)).hexdigest()
        return body


class NativeOwnerService:
    """Read one owner's native store without access to grader expectations."""

    filename: str
    owner_id: str
    source_identity: str
    base_latency_ms: int

    def __init__(
        self,
        filename: str,
        owner_id: str,
        source_identity: str,
        base_latency_ms: int,
    ) -> None:
        self.filename = filename
        self.owner_id = owner_id
        self.source_identity = source_identity
        self.base_latency_ms = base_latency_ms
        self.path = FIXTURES / filename
        self.store = _load(self.path)
        rows = self.store.get("worlds")
        if not isinstance(rows, dict):
            raise ValueError(f"{filename}: missing worlds object")

    def read(self, world_id: str) -> OwnerResponse:
        row = self.store["worlds"].get(world_id)
        if not isinstance(row, dict):
            raise KeyError(f"{self.filename}: no row for {world_id}")
        observed_at = int(row.get("observed_at", 100))
        latency = int(row.get("latency_ms", self.base_latency_ms))
        disclosure = int(row.get("disclosure_units", 1))
        payload = _opaque_relational_ids({
            key: value
            for key, value in row.items()
            if key not in {"observed_at", "latency_ms", "disclosure_units"}
        }, world_id)
        return OwnerResponse(
            owner_id=self.owner_id,
            source_identity=self.source_identity,
            source_hash=sha256_file(self.path),
            observed_at=observed_at,
            latency_ms=latency,
            disclosure_units=disclosure,
            payload=payload,
        )


class AuthorityService(NativeOwnerService):
    """Return current mandates/delegations for one Authority stratum."""

    def read_for_stratum(self, world_id: str, stratum: str) -> OwnerResponse:
        row = self.store["worlds"].get(world_id)
        if not isinstance(row, dict):
            raise KeyError(f"{self.filename}: no row for {world_id}")
        defaults = self.store.get("strata_defaults")
        if not isinstance(defaults, dict) or not isinstance(defaults.get(stratum), dict):
            raise KeyError(f"{self.filename}: no default for {stratum}")
        payload = dict(defaults[stratum])
        strata = row.get("strata", {})
        if not isinstance(strata, dict):
            raise ValueError(f"{self.filename}: malformed strata for {world_id}")
        override = strata.get(stratum, {})
        if not isinstance(override, dict):
            raise ValueError(f"{self.filename}: malformed {stratum} for {world_id}")
        payload.update(override)
        payload["authority_stratum"] = stratum
        observed_at = int(row.get("observed_at", 100))
        body = OwnerResponse(
            owner_id=self.owner_id,
            source_identity=f"{self.source_identity}:{stratum}",
            source_hash=sha256_file(self.path),
            observed_at=observed_at,
            latency_ms=int(row.get("latency_ms", self.base_latency_ms)),
            disclosure_units=int(row.get("disclosure_units", 2)),
            payload=payload,
        )
        return body


def services() -> dict[str, NativeOwnerService]:
    return {
        "claim_head": NativeOwnerService(
            "claim_heads.json",
            "claim-registry-owner",
            "append-only-claim-head-ledger-v1",
            2,
        ),
        "execution": NativeOwnerService(
            "execution_sensor.json",
            "execution-domain-owner",
            "execution-boundary-audit-sensor-v1",
            4,
        ),
        "target": NativeOwnerService(
            "target_store.json",
            "target-domain-owner",
            "target-transition-store-v1",
            7,
        ),
        "adoption": NativeOwnerService(
            "adoption_store.json",
            "adopter-domain-owner",
            "operational-use-store-v1",
            6,
        ),
        "acceptance": NativeOwnerService(
            "acceptance_acts.json",
            "acceptance-institution-owner",
            "institutional-act-register-v1",
            12,
        ),
        "settlement": NativeOwnerService(
            "obligation_store.json",
            "settlement-scheme-owner",
            "obligation-scheme-ledger-v1",
            9,
        ),
        "cut": NativeOwnerService(
            "cut_store.json",
            "observation-cut-owner",
            "owner-head-vector-register-v1",
            3,
        ),
    }


def authority_service() -> AuthorityService:
    return AuthorityService(
        "authority_store.json",
        "authority-registry-owner",
        "mandate-delegation-current-head-v1",
        5,
    )


def build_owner_observations(world_id: str, stratum: str) -> dict[str, Any]:
    """Query independent sources and return only method-visible observations."""

    registry = services()
    observations = {name: service.read(world_id).as_dict() for name, service in registry.items()}
    observations["authority"] = authority_service().read_for_stratum(world_id, stratum).as_dict()
    costs = {
        "latency_ms": sum(int(item["latency_ms"]) for item in observations.values()),
        "disclosure_units": sum(
            int(item["disclosure_units"]) for item in observations.values()
        ),
        "query_count": len(observations),
    }
    trace_refs = {
        name: {
            "source_identity": item["source_identity"],
            "receipt_hash": item["receipt_hash"],
            "observed_at": item["observed_at"],
        }
        for name, item in observations.items()
    }
    return {
        "world_token": public_world_token(world_id),
        "authority_stratum": stratum,
        "observations": observations,
        "owner_query_cost": costs,
        "trace_refs": trace_refs,
    }


def owner_source_manifest() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, service in services().items():
        result[name] = {
            "owner_id": service.owner_id,
            "source_identity": service.source_identity,
            "path": f"fixtures/{service.filename}",
            "sha256": sha256_file(service.path),
        }
    auth = authority_service()
    result["authority"] = {
        "owner_id": auth.owner_id,
        "source_identity": auth.source_identity,
        "path": f"fixtures/{auth.filename}",
        "sha256": sha256_file(auth.path),
    }
    return result
