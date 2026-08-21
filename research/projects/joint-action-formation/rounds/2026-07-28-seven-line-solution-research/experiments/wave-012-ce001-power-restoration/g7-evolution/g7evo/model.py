"""Small semantic primitives for CE-001 G7 evolution.

There is no arm selector or expected-label lookup in this module.  The
implementation consumes owner-native observations and authoritative target
readback, while contract checks derive from exact identifiers and state.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


OWNER_TRUST_ANCHORS = {
    "O_Q": "anchor:requester:q:v1",
    "O_V": "anchor:venue:v:v1",
    "O_P": "anchor:payment:p:v1",
    "O_R": "anchor:resource:r:v1",
    "O_S": "anchor:safety:s:v1",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def owner_signature(owner_id: str, payload: Mapping[str, Any]) -> str:
    """Small local trust-anchor signature used by the synthetic workers.

    This is deliberately scoped to ordinary pipeline mutation detection.  It
    is not presented as a legal signature or protection from a same-user
    process that can read this source tree.
    """

    return digest(
        {
            "owner_id": owner_id,
            "trust_anchor": OWNER_TRUST_ANCHORS[owner_id],
            "payload": dict(payload),
        }
    )


def issue_current_receipt_set(
    operation: Mapping[str, Any],
    *,
    episode_id: str,
    at_epoch: int,
) -> list[dict[str, Any]]:
    """Issue the two exact current frames consumed by the local target."""

    receipts: list[dict[str, Any]] = []
    for owner_id, role in (("O_R", "RESOURCE"), ("O_S", "SAFETY")):
        payload = {
            "owner_id": owner_id,
            "role": role,
            "episode_id": episode_id,
            "q_version": operation["q_version"],
            "object_id": operation["object_id"],
            "operation_id": operation["operation_id"],
            "target_id": operation["object_id"],
            "semantic_effect_key": operation["semantic_effect_key"],
            "state_head": f"{owner_id}:head:{at_epoch}",
            "issued_epoch": at_epoch,
            "expires_epoch": at_epoch + 2,
            "current": True,
        }
        signature = owner_signature(owner_id, payload)
        frame = {**payload, "signature": signature}
        frame["receipt_hash"] = digest(frame)
        receipts.append(frame)
    return receipts


@dataclass
class AppendOnlyHistory:
    """Hash-linked history whose imported prefix cannot be rewritten."""

    owner: str
    records: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "index": len(self.records),
            "owner": self.owner,
            "event": event,
            "payload": deepcopy(dict(payload or {})),
            "previous_hash": self.root,
        }
        record["record_hash"] = digest(record)
        self.records.append(record)
        return deepcopy(record)

    @property
    def root(self) -> str:
        return self.records[-1]["record_hash"] if self.records else "GENESIS"

    def snapshot(self) -> list[dict[str, Any]]:
        return deepcopy(self.records)

    @classmethod
    def import_verified(
        cls, owner: str, records: Iterable[Mapping[str, Any]], claimed_root: str
    ) -> "AppendOnlyHistory":
        history = cls(owner)
        for expected_index, raw in enumerate(records):
            record = deepcopy(dict(raw))
            if record.get("index") != expected_index:
                raise ValueError(f"history index mismatch at {expected_index}")
            if record.get("previous_hash") != history.root:
                raise ValueError(f"history previous_hash mismatch at {expected_index}")
            supplied_hash = record.pop("record_hash", None)
            computed_hash = digest(record)
            if supplied_hash != computed_hash:
                raise ValueError(f"history record hash mismatch at {expected_index}")
            record["record_hash"] = supplied_hash
            history.records.append(record)
        if history.root != claimed_root:
            raise ValueError("history root mismatch")
        return history

    def prefix_preserved(self, prefix: Iterable[Mapping[str, Any]]) -> bool:
        frozen = [deepcopy(dict(item)) for item in prefix]
        return self.records[: len(frozen)] == frozen


def causal_closure(
    changed_nodes: Iterable[str],
    edges: Iterable[Iterable[str]],
) -> list[str]:
    """Return changed nodes and all transitively dependent nodes."""

    adjacency: dict[str, set[str]] = {}
    for raw in edges:
        pair = list(raw)
        if len(pair) != 2:
            raise ValueError("dependency edge must contain exactly two nodes")
        adjacency.setdefault(str(pair[0]), set()).add(str(pair[1]))
    seen = {str(node) for node in changed_nodes}
    queue = list(seen)
    while queue:
        node = queue.pop(0)
        for child in sorted(adjacency.get(node, ())):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return sorted(seen)


@dataclass
class DurableFenceAuthority:
    """Target-side epoch owner shared independently of runtime instances."""

    required_epochs: dict[str, int] = field(default_factory=dict)
    history: AppendOnlyHistory = field(
        default_factory=lambda: AppendOnlyHistory("durable-fence-authority")
    )

    def install(self, target_key: str, epoch: int) -> dict[str, Any]:
        previous = self.required_epochs.get(target_key, 1)
        if epoch < previous:
            raise ValueError("external fence epoch cannot move backwards")
        self.required_epochs[target_key] = max(previous, epoch)
        return self.history.append(
            "FENCE_INSTALLED",
            {
                "target_key": target_key,
                "previous_epoch": previous,
                "required_epoch": self.required_epochs[target_key],
            },
        )

    def required_epoch(self, target_key: str) -> int:
        return self.required_epochs.get(target_key, 1)


@dataclass
class EffectTarget:
    """Target-native Effect owner with semantic idempotency and epoch fencing."""

    owner_id: str
    current_epoch: int = 1
    fence_authority: DurableFenceAuthority = field(
        default_factory=DurableFenceAuthority
    )
    fence_key: str | None = None
    effects: dict[str, dict[str, Any]] = field(default_factory=dict)
    history: AppendOnlyHistory = field(init=False)

    def __post_init__(self) -> None:
        self.history = AppendOnlyHistory(self.owner_id)
        if self.fence_key is None:
            self.fence_key = self.owner_id

    def advance_epoch(self, epoch: int) -> None:
        if epoch <= self.current_epoch:
            raise ValueError("takeover epoch must advance")
        previous = self.current_epoch
        self.current_epoch = epoch
        self.history.append(
            "TARGET_EPOCH_ADVANCED",
            {"previous_epoch": previous, "current_epoch": epoch},
        )

    def install_external_fence(self, epoch: int) -> None:
        """Persist target-side fencing outside coordinator runtime memory."""

        receipt = self.fence_authority.install(str(self.fence_key), epoch)
        self.history.append(
            "DURABLE_EXTERNAL_FENCE_INSTALLED",
            {
                "fence_epoch": epoch,
                "fence_key": self.fence_key,
                "authority_record_hash": receipt["record_hash"],
            },
        )

    def dispatch(
        self,
        *,
        operation: Mapping[str, Any],
        coordinator_epoch: int,
        current_receipt_set: Iterable[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        key = str(operation["semantic_effect_key"])
        required_epoch = max(
            self.current_epoch,
            self.fence_authority.required_epoch(str(self.fence_key)),
        )
        receipts = [deepcopy(dict(item)) for item in (current_receipt_set or ())]
        receipt_owners = [str(item.get("owner_id")) for item in receipts]
        receipt_hashes = [str(item.get("receipt_hash")) for item in receipts]
        exact_receipts = (
            len(receipts) == 2
            and set(receipt_owners) == {"O_R", "O_S"}
            and len(receipt_owners) == len(set(receipt_owners))
            and len(receipt_hashes) == len(set(receipt_hashes))
            and all(
                item.get("current") is True
                and item.get("q_version") == operation.get("q_version")
                and item.get("object_id") == operation.get("object_id")
                and item.get("operation_id") == operation.get("operation_id")
                and item.get("target_id") == operation.get("object_id")
                and item.get("semantic_effect_key")
                == operation.get("semantic_effect_key")
                and item.get("issued_epoch", coordinator_epoch)
                <= coordinator_epoch
                <= item.get("expires_epoch", -1)
                and item.get("signature")
                == owner_signature(
                    str(item.get("owner_id")),
                    {
                        key: value
                        for key, value in item.items()
                        if key not in {"signature", "receipt_hash"}
                    },
                )
                and item.get("receipt_hash")
                == digest(
                    {
                        key: value
                        for key, value in item.items()
                        if key != "receipt_hash"
                    }
                )
                for item in receipts
                if item.get("owner_id") in OWNER_TRUST_ANCHORS
            )
        )
        consumption = {
            "consumer": "TARGET_NATIVE",
            "consumed_receipt_hashes": receipt_hashes if exact_receipts else [],
            "decision": "ALLOW" if exact_receipts else "REJECT_RECEIPT_SET",
            "coordinator_epoch": coordinator_epoch,
            "required_epoch": required_epoch,
            "semantic_effect_key": key,
        }
        self.history.append("TARGET_RECEIPT_SET_CONSUMED", consumption)
        if not exact_receipts or coordinator_epoch < required_epoch:
            outcome = {
                "outcome": "FENCED_OR_DENIED",
                "committed": False,
                "duplicate_suppressed": False,
                "semantic_effect_key": key,
                "coordinator_epoch": coordinator_epoch,
                "required_epoch": required_epoch,
            }
            self.history.append("EFFECT_ATTEMPT_DENIED", outcome)
            return outcome
        if key in self.effects:
            outcome = {
                "outcome": "DEDUPLICATED",
                "committed": True,
                "duplicate_suppressed": True,
                "semantic_effect_key": key,
                "coordinator_epoch": coordinator_epoch,
            }
            self.history.append("EFFECT_ATTEMPT_DEDUPLICATED", outcome)
            return outcome
        effect = {
            "semantic_effect_key": key,
            "operation_id": operation["operation_id"],
            "operation_version": operation["operation_version"],
            "object_id": operation["object_id"],
            "q_version": operation["q_version"],
            "delivered_kw": operation["delivered_kw"],
            "duration_minutes": operation["duration_minutes"],
            "origin_resource_id": operation.get("origin_resource_id"),
            "reservation_ref": operation.get("reservation_ref"),
            "lease_commitment_evidence_hash": operation.get(
                "lease_commitment_evidence_hash"
            ),
            "coordinator_epoch": coordinator_epoch,
            "required_epoch": required_epoch,
            "sequence": len(self.effects) + 1,
        }
        self.effects[key] = effect
        outcome = {
            "outcome": "COMMITTED",
            "committed": True,
            "duplicate_suppressed": False,
            "semantic_effect_key": key,
            "coordinator_epoch": coordinator_epoch,
            "required_epoch": required_epoch,
        }
        self.history.append("EFFECT_COMMITTED", {"effect": effect, "receipt": outcome})
        return outcome

    def readback(self, semantic_effect_key: str) -> dict[str, Any]:
        effect = deepcopy(self.effects.get(semantic_effect_key))
        receipt = {
            "owner_id": self.owner_id,
            "semantic_effect_key": semantic_effect_key,
            "status": "CONFIRMED" if effect else "NOT_FOUND",
            "effect": effect,
        }
        receipt["evidence_hash"] = digest(receipt)
        self.history.append("EFFECT_READBACK", receipt)
        return receipt


@dataclass
class AcceptanceOwner:
    """O_Q/O_V exact-binding Acceptance and O_P settlement model."""

    owner_id: str
    expected_q_version: str
    expected_object_id: str
    expected_operation_id: str
    expected_semantic_effect_key: str
    history: AppendOnlyHistory = field(init=False)

    def __post_init__(self) -> None:
        self.history = AppendOnlyHistory(self.owner_id)

    def accept(
        self,
        *,
        q_version: str,
        object_id: str,
        operation_id: str,
        semantic_effect_key: str,
        effect_readback: Mapping[str, Any],
    ) -> dict[str, Any]:
        effect = effect_readback.get("effect") or {}
        exact = (
            effect_readback.get("status") == "CONFIRMED"
            and q_version == self.expected_q_version
            and object_id == self.expected_object_id
            and operation_id == self.expected_operation_id
            and semantic_effect_key == self.expected_semantic_effect_key
            and effect.get("q_version") == q_version
            and effect.get("object_id") == object_id
            and effect.get("operation_id") == operation_id
            and effect.get("semantic_effect_key") == semantic_effect_key
        )
        receipt = {
            "owner_id": self.owner_id,
            "act_source_id": f"act-source:{self.owner_id}",
            "trust_anchor_id": OWNER_TRUST_ANCHORS[self.owner_id],
            "q_version": q_version,
            "object_id": object_id,
            "operation_id": operation_id,
            "semantic_effect_key": semantic_effect_key,
            "decision": "ACCEPTED" if exact else "REFUSED_WRONG_BINDING",
        }
        receipt["signature"] = owner_signature(self.owner_id, receipt)
        receipt["evidence_hash"] = digest(receipt)
        self.history.append("ACCEPTANCE_DECIDED", receipt)
        return receipt


@dataclass
class SettlementOwner:
    """O_P advances only from distinct O_Q and O_V exact Acceptance receipts."""

    owner_id: str = "O_P"
    history: AppendOnlyHistory = field(init=False)

    def __post_init__(self) -> None:
        self.history = AppendOnlyHistory(self.owner_id)

    def settle(
        self, acceptances: Iterable[Mapping[str, Any]]
    ) -> dict[str, Any]:
        receipts = [deepcopy(dict(item)) for item in acceptances]
        by_owner = {str(item.get("owner_id")): item for item in receipts}
        required = {"O_Q", "O_V"}
        exact_bindings = {
            (
                item.get("q_version"),
                item.get("object_id"),
                item.get("operation_id"),
                item.get("semantic_effect_key"),
            )
            for item in receipts
        }
        provenance_valid = (
            len(receipts) == 2
            and len(by_owner) == 2
            and all(
                item.get("act_source_id") == f"act-source:{owner}"
                and item.get("trust_anchor_id") == OWNER_TRUST_ANCHORS[owner]
                and item.get("signature")
                == owner_signature(
                    owner,
                    {
                        key: value
                        for key, value in item.items()
                        if key not in {"signature", "evidence_hash"}
                    },
                )
                and item.get("evidence_hash")
                == digest(
                    {
                        key: value
                        for key, value in item.items()
                        if key != "evidence_hash"
                    }
                )
                for owner, item in by_owner.items()
                if owner in required
            )
        )
        settled = (
            required <= set(by_owner)
            and provenance_valid
            and all(by_owner[owner].get("decision") == "ACCEPTED" for owner in required)
            and len(exact_bindings) == 1
        )
        receipt = {
            "owner_id": self.owner_id,
            "acceptance_evidence_hashes": sorted(
                by_owner[owner].get("evidence_hash") for owner in required if owner in by_owner
            ),
            "status": "SETTLED" if settled else "NOT_SETTLED",
        }
        receipt["evidence_hash"] = digest(receipt)
        self.history.append("SETTLEMENT_DECIDED", receipt)
        return receipt
