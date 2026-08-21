"""Owner and migration adapters with deliberately different interfaces."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .model import AppendOnlyHistory, digest


class LeaseRegistryAdapter:
    """Resource owner adapter.

    Native interface: ``fetch_lease(reservation_ref, if_revision=...)`` and a
    nested lease-registry document.
    """

    def __init__(self, native_documents: Mapping[str, Mapping[str, Any]]):
        self._documents = deepcopy(dict(native_documents))
        self.query_count = 0

    def fetch_lease(
        self, reservation_ref: str, *, if_revision: int | None = None
    ) -> dict[str, Any]:
        self.query_count += 1
        native = deepcopy(self._documents[reservation_ref])
        lease = native["leaseRecord"]
        observation = {
            "adapter_id": "lease-registry-v1",
            "owner_id": native["registryOwner"],
            "reservation_ref": reservation_ref,
            "resource_id": lease["resourceRef"],
            "revision": lease["revision"],
            "current": lease["state"] == "ACTIVE",
            "revoked": lease["state"] == "REVOKED",
            "replacement_refs": list(native.get("replacementRefs", [])),
            "scope": {
                "q_version": lease["scope"]["qVersion"],
                "object_id": lease["scope"]["objectRef"],
                "operation_id": lease["scope"]["operationRef"],
                "expires_epoch": lease["scope"]["expiresEpoch"],
            },
            "if_revision": if_revision,
            "native_hash": digest(native),
        }
        observation["evidence_hash"] = digest(observation)
        return observation

    def bind_commitment(
        self,
        reservation_ref: str,
        operation: Mapping[str, Any],
        *,
        at_epoch: int,
    ) -> dict[str, Any]:
        """Ask O_R to bind its active lease to the exact task operation."""

        lease = self.fetch_lease(reservation_ref)
        scope = lease["scope"]
        exact_scope = (
            lease["current"]
            and scope["q_version"] == operation["q_version"]
            and scope["object_id"] == operation["object_id"]
            and scope["operation_id"] == operation["operation_id"]
            and at_epoch <= scope["expires_epoch"]
        )
        commitment = {
            "adapter_id": "lease-registry-v1",
            "owner_id": lease["owner_id"],
            "reservation_ref": reservation_ref,
            "resource_id": lease["resource_id"],
            "q_version": operation["q_version"],
            "object_id": operation["object_id"],
            "operation_id": operation["operation_id"],
            "semantic_effect_key": operation["semantic_effect_key"],
            "lease_revision": lease["revision"],
            "decision": "COMMITTED_EXACT_SCOPE" if exact_scope else "REFUSED_SCOPE_MISMATCH",
            "lease_evidence_hash": lease["evidence_hash"],
        }
        commitment["evidence_hash"] = digest(commitment)
        return commitment


class SafetyPermitAdapter:
    """Safety owner adapter.

    Native interface differs from LeaseRegistryAdapter: a structured operation
    is verified against a policy revision and returns a tuple-like decision
    document rather than a lease record.
    """

    def __init__(self, policy_documents: Mapping[str, Mapping[str, Any]]):
        self._policies = deepcopy(dict(policy_documents))
        self.query_count = 0

    def verify(
        self,
        operation: Mapping[str, Any],
        policy_revision: str,
        *,
        at_epoch: int,
    ) -> dict[str, Any]:
        self.query_count += 1
        native = deepcopy(self._policies[policy_revision])
        allowed = (
            native["verdictCode"] == 204
            and operation["object_id"] in native["scope"]["exactTargets"]
            and operation["operation_id"] in native["scope"]["operations"]
            and at_epoch <= native["validThroughEpoch"]
        )
        observation = {
            "adapter_id": "safety-permit-v3",
            "owner_id": native["issuer"],
            "policy_revision": policy_revision,
            "allowed": allowed,
            "valid_through_epoch": native["validThroughEpoch"],
            "operation_hash": digest(operation),
            "native_hash": digest(native),
        }
        observation["evidence_hash"] = digest(observation)
        return observation


class CapsuleV1Exporter:
    """Source runtime interface: one nested envelope returned by ``export``."""

    schema = "ce001.g7.capsule.v1"

    def export(
        self,
        *,
        source_runtime_id: str,
        source_epoch: int,
        target_epoch: int,
        bindings: Mapping[str, Any],
        history: AppendOnlyHistory,
        pending_acceptance: bool,
        unresolved_effect_keys: list[str],
        obligations: list[Mapping[str, Any]],
        owner_evidence_hashes: list[str],
        dependency_graph_version: str,
    ) -> dict[str, Any]:
        payload = {
            "header": {
                "schema": self.schema,
                "source_runtime_id": source_runtime_id,
                "source_epoch": source_epoch,
                "target_epoch": target_epoch,
            },
            "bindings": deepcopy(dict(bindings)),
            "recovery": {
                "history_records": history.snapshot(),
                "history_root": history.root,
                "pending_acceptance": pending_acceptance,
                "unresolved_effect_keys": list(unresolved_effect_keys),
                "obligations": deepcopy(list(obligations)),
                "owner_evidence_hashes": list(owner_evidence_hashes),
                "dependency_graph_version": dependency_graph_version,
            },
        }
        return {"payload": payload, "capsule_hash": digest(payload)}


class CapsuleV2Importer:
    """Target runtime interface.

    Unlike the exporter, ``ingest`` receives detached metadata and content.
    It translates the v1 wire shape into a flat target-runtime context.
    """

    REQUIRED_PATHS = (
        "header.schema",
        "header.source_runtime_id",
        "header.source_epoch",
        "header.target_epoch",
        "bindings.episode_id",
        "bindings.q_version",
        "bindings.object_id",
        "bindings.operation_id",
        "bindings.semantic_effect_key",
        "recovery.history_records",
        "recovery.history_root",
        "recovery.pending_acceptance",
        "recovery.unresolved_effect_keys",
        "recovery.obligations",
        "recovery.owner_evidence_hashes",
        "recovery.dependency_graph_version",
    )

    @staticmethod
    def _path(payload: Mapping[str, Any], dotted: str) -> Any:
        value: Any = payload
        for component in dotted.split("."):
            if not isinstance(value, Mapping) or component not in value:
                raise KeyError(dotted)
            value = value[component]
        return value

    def ingest(
        self,
        metadata: Mapping[str, Any],
        content: Mapping[str, Any],
        *,
        target_runtime_id: str,
    ) -> dict[str, Any]:
        missing = []
        for path in self.REQUIRED_PATHS:
            try:
                self._path(content, path)
            except KeyError:
                missing.append(path)
        valid_hash = metadata.get("capsule_hash") == digest(content)
        semantic_errors = []
        if not missing:
            if self._path(content, "header.schema") != CapsuleV1Exporter.schema:
                semantic_errors.append("unsupported schema")
            if self._path(content, "header.target_epoch") <= self._path(
                content, "header.source_epoch"
            ):
                semantic_errors.append("target epoch must advance")
            if not self._path(content, "bindings.semantic_effect_key"):
                semantic_errors.append("semantic effect key is empty")
            if self._path(content, "recovery.pending_acceptance"):
                obligations = self._path(content, "recovery.obligations")
                if not obligations:
                    semantic_errors.append(
                        "pending Acceptance requires non-empty obligations"
                    )
                elif not any(
                    isinstance(item, Mapping)
                    and item.get("type") == "ACCEPTANCE_THEN_SETTLEMENT"
                    and set(item.get("owner_ids", ())) >= {"O_Q", "O_V", "O_P"}
                    for item in obligations
                ):
                    semantic_errors.append(
                        "Acceptance/Settlement obligation semantics missing"
                    )
                if not self._path(
                    content, "recovery.unresolved_effect_keys"
                ):
                    semantic_errors.append(
                        "pending Acceptance requires an Effect reconciliation key"
                    )
            if not self._path(content, "recovery.owner_evidence_hashes"):
                semantic_errors.append("owner evidence bindings are empty")
        imported = not missing and not semantic_errors and valid_hash
        result: dict[str, Any] = {
            "imported": imported,
            "valid_hash": valid_hash,
            "missing_fields": missing,
            "semantic_errors": semantic_errors,
            "target_runtime_id": target_runtime_id,
        }
        if imported:
            result["context"] = {
                "episode_id": self._path(content, "bindings.episode_id"),
                "q_version": self._path(content, "bindings.q_version"),
                "object_id": self._path(content, "bindings.object_id"),
                "operation_id": self._path(content, "bindings.operation_id"),
                "semantic_effect_key": self._path(
                    content, "bindings.semantic_effect_key"
                ),
                "source_runtime_id": self._path(
                    content, "header.source_runtime_id"
                ),
                "source_epoch": self._path(content, "header.source_epoch"),
                "target_epoch": self._path(content, "header.target_epoch"),
                "pending_acceptance": self._path(
                    content, "recovery.pending_acceptance"
                ),
                "unresolved_effect_keys": self._path(
                    content, "recovery.unresolved_effect_keys"
                ),
                "obligations": self._path(content, "recovery.obligations"),
                "owner_evidence_hashes": self._path(
                    content, "recovery.owner_evidence_hashes"
                ),
                "dependency_graph_version": self._path(
                    content, "recovery.dependency_graph_version"
                ),
                "history_records": self._path(
                    content, "recovery.history_records"
                ),
                "history_root": self._path(content, "recovery.history_root"),
            }
        return result


def drop_capsule_field(
    capsule: Mapping[str, Any], dotted_path: str, *, resign: bool
) -> dict[str, Any]:
    result = deepcopy(dict(capsule))
    payload = result["payload"]
    parts = dotted_path.split(".")
    parent: Any = payload
    for component in parts[:-1]:
        parent = parent[component]
    parent.pop(parts[-1], None)
    if resign:
        result["capsule_hash"] = digest(payload)
    return result
