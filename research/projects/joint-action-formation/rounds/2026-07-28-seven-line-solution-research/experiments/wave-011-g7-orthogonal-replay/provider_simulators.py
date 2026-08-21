"""Provider-native simulators for the G7 orthogonal replay.

This module deliberately does not import the private oracle.  It models the
state and failure domains a method may lawfully interact with:

* Authority owners answer in their native schemas and independently enforce
  commit-time fences.
* An effector owns intent dispatch, idempotency and target-domain readback.
* An Acceptance owner answers for an exact goal/effect/object binding.
* Source and target runtimes own separate ledgers and exchange a semantic
  recovery capsule.

The grader is expected to live in ``private_oracle.py`` and to inspect the
records produced here only after a method has completed.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _first(mapping: Mapping[str, Any] | None, names: Iterable[str], default: Any = None) -> Any:
    if not isinstance(mapping, Mapping):
        return default
    for name in names:
        if name in mapping:
            return mapping[name]
    return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


@dataclass
class AppendOnlyLedger:
    owner: str
    records: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        previous = self.records[-1]["record_hash"] if self.records else "GENESIS"
        record = {
            "index": len(self.records),
            "owner": self.owner,
            "event": event,
            "payload": deepcopy(dict(payload or {})),
            "previous_hash": previous,
        }
        record["record_hash"] = digest(record)
        self.records.append(record)
        return deepcopy(record)

    def snapshot(self) -> list[dict[str, Any]]:
        return deepcopy(self.records)

    def root(self) -> str:
        return self.records[-1]["record_hash"] if self.records else "GENESIS"


class NativeAuthorityProvider:
    """Independent Authority service with provider-native response shapes."""

    def __init__(self, config: Mapping[str, Any] | None):
        self.config = deepcopy(dict(config or {}))
        self.provider_id = str(
            _first(self.config, ("provider_id", "owner_id", "authority_id"), "authority-owner")
        )
        self.responses = deepcopy(
            _first(self.config, ("responses", "native_responses", "query_responses"), {})
        )
        self.default_response = deepcopy(
            _first(self.config, ("default_response", "native_response", "response"), {})
        )
        self.query_counts: dict[str, int] = {}
        self.commit_policy = deepcopy(
            _first(
                self.config,
                ("commit_policy", "commit_check", "commit_state", "commit_stance"),
                {},
            )
        )
        self.fence_supported = bool(
            _first(self.config, ("fence_supported", "supports_fence"), True)
        )
        self.current_epoch = int(
            _first(self.config, ("coordinator_epoch", "current_epoch", "epoch"), 1)
        )
        self.ledger = AppendOnlyLedger(self.provider_id)

    def query(self, request: Mapping[str, Any]) -> dict[str, Any]:
        endpoint = str(
            _first(request, ("endpoint", "provider_endpoint", "query_endpoint", "alias"), "default")
        )
        response_ref = str(_first(request, ("response_ref", "native_response_ref"), endpoint))
        index = self.query_counts.get(endpoint, 0)
        self.query_counts[endpoint] = index + 1

        configured = None
        if isinstance(self.responses, Mapping):
            configured = self.responses.get(
                response_ref, self.responses.get(endpoint, self.responses.get("default"))
            )
        elif self.responses:
            configured = self.responses
        sequence = _as_list(configured)
        if sequence:
            response = deepcopy(sequence[min(index, len(sequence) - 1)])
        else:
            response = deepcopy(self.default_response)

        if not isinstance(response, Mapping):
            response = {"body": response}
        response = dict(response)
        transport = str(
            _first(response, ("channel_outcome", "transport", "transport_status"), "RESPONSE")
        ).upper()
        native_body = deepcopy(
            _first(response, ("native_body", "body", "payload", "response"), response)
        )
        envelope = {
            "provider_id": self.provider_id,
            "endpoint": endpoint,
            "query_id": f"{self.provider_id}:{endpoint}:{index + 1}",
            "channel_outcome": transport,
            "native_body": native_body,
            "native_response_sha256": digest(native_body),
        }
        # These are transport facts, not normalized truth labels.
        for key in ("observed_at", "received_at", "status_code", "retry_after"):
            if key in response:
                envelope[key] = deepcopy(response[key])
        if "headers" in response:
            envelope["native_headers"] = deepcopy(response["headers"])
        if "elapsed_ms" in response:
            envelope["elapsed_ms"] = deepcopy(response["elapsed_ms"])
        self.ledger.append("QUERY", {"request": dict(request), "response": envelope})
        return envelope

    def advance_epoch(self, target_epoch: int) -> dict[str, Any]:
        previous = self.current_epoch
        if target_epoch > self.current_epoch:
            self.current_epoch = int(target_epoch)
        return self.ledger.append(
            "EPOCH_ADVANCED",
            {"previous_epoch": previous, "current_epoch": self.current_epoch},
        )

    def commit_check(
        self,
        operation: Mapping[str, Any],
        coordinator_epoch: int,
        fence_token: str | None,
    ) -> dict[str, Any]:
        policy = self.commit_policy if isinstance(self.commit_policy, Mapping) else {}
        policy_text = json.dumps(policy, ensure_ascii=False, sort_keys=True).lower()
        stance = str(_first(policy, ("normative_stance", "stance", "state"), "")).upper()
        if not stance:
            if any(word in policy_text for word in ('"decision": "permit"', '"decision":"permit"', '"active": true', '"active":true')):
                stance = "CURRENT"
            elif any(word in policy_text for word in ('"decision": "deny"', '"decision":"deny"', "unavailable", "conflict", "mismatch", "no_disclosure")):
                stance = "DENY"
            else:
                stance = "UNKNOWN"
        required_head = _first(policy, ("required_head", "head", "authority_head"))
        supplied_head = _first(operation, ("authority_head", "head"))
        epoch_ok = (not self.fence_supported) or coordinator_epoch >= self.current_epoch
        fence_required = bool(_first(policy, ("fence_required",), self.fence_supported))
        fence_ok = (not fence_required) or bool(fence_token)
        head_ok = required_head is None or supplied_head == required_head
        allowed = stance in {"CURRENT", "ACTIVE", "ALLOW", "ALLOWED", "PERMIT"} and epoch_ok and fence_ok and head_ok
        result = {
            "provider_id": self.provider_id,
            "allowed": allowed,
            "commit_stance": stance,
            "epoch_ok": epoch_ok,
            "fence_ok": fence_ok,
            "head_ok": head_ok,
            "required_epoch": self.current_epoch,
            "observed_epoch": coordinator_epoch,
            "fence_supported": self.fence_supported,
        }
        self.ledger.append("COMMIT_CHECK", result)
        return result


class EffectorProvider:
    """Target-domain effector; dispatch responses and readback can diverge."""

    def __init__(self, config: Mapping[str, Any] | None):
        self.config = deepcopy(dict(config or {}))
        self.provider_id = str(
            _first(self.config, ("provider_id", "owner_id", "effector_id"), "effector-owner")
        )
        self.dispatch_mode = str(
            _first(self.config, ("dispatch_outcome", "dispatch_mode", "commit_outcome"), "COMMIT")
        ).upper()
        self.response_outcome = str(
            _first(self.config, ("response_outcome", "channel_outcome"), "DELIVERED")
        ).upper()
        self.readback_override = deepcopy(
            _first(
                self.config,
                ("readback_response", "native_readback", "readback", "readback_state"),
                None,
            )
        )
        self.idempotency_horizon = int(
            _first(self.config, ("idempotency_horizon", "key_retention"), 100)
        )
        self.effects_by_key: dict[str, dict[str, Any]] = {}
        self.dispatch_count = 0
        self.ledger = AppendOnlyLedger(self.provider_id)

    def dispatch(
        self,
        *,
        operation: Mapping[str, Any],
        intent: Mapping[str, Any],
        coordinator_epoch: int,
        authority_check: Mapping[str, Any],
    ) -> dict[str, Any]:
        self.dispatch_count += 1
        effect_key = str(
            _first(
                operation,
                ("semantic_effect_key", "effect_key", "idempotency_key"),
                _first(intent, ("semantic_effect_key", "effect_key"), "missing-effect-key"),
            )
        )
        existing = self.effects_by_key.get(effect_key)
        if not authority_check.get("allowed", False):
            committed = False
            duplicate_suppressed = False
            effect_record = {}
            outcome = "FENCED_OR_DENIED"
        elif existing is not None:
            committed = True
            duplicate_suppressed = True
            effect_record = existing
            outcome = "DEDUPLICATED"
        elif self.dispatch_mode in {"REJECT", "FAIL_BEFORE_COMMIT", "NO_COMMIT", "BLOCK"}:
            committed = False
            duplicate_suppressed = False
            effect_record = {}
            outcome = "NOT_COMMITTED"
        else:
            committed = True
            duplicate_suppressed = False
            effect_record = {
                "effect_key": effect_key,
                "operation_id": _first(operation, ("id", "operation_id", "name")),
                "operation_version": _first(operation, ("version", "operation_version")),
                "object_id": _first(operation, ("object_id", "target_object", "subject_id")),
                "coordinator_epoch": coordinator_epoch,
                "intent_sha256": digest(intent),
                "effect_sequence": len(self.effects_by_key) + 1,
            }
            self.effects_by_key[effect_key] = effect_record
            outcome = "COMMITTED"

        receipt = {
            "provider_id": self.provider_id,
            "dispatch_id": f"{self.provider_id}:dispatch:{self.dispatch_count}",
            "effect_key": effect_key,
            "outcome": outcome,
            "committed": committed,
            "duplicate_suppressed": duplicate_suppressed,
            "response_outcome": self.response_outcome,
        }
        self.ledger.append(
            "DISPATCH",
            {"receipt": receipt, "effect_record": effect_record, "authority_check": authority_check},
        )
        if self.response_outcome in {"LOST", "TIMEOUT", "CONNECTION_LOST", "NO_RESPONSE"}:
            return {
                "provider_id": self.provider_id,
                "dispatch_id": receipt["dispatch_id"],
                "effect_key": effect_key,
                "channel_outcome": self.response_outcome,
                "commit_status": "UNKNOWN_TO_CALLER",
            }
        return {**receipt, "channel_outcome": "RESPONSE"}

    def readback(self, request: Mapping[str, Any]) -> dict[str, Any]:
        effect_key = str(
            _first(request, ("semantic_effect_key", "effect_key", "idempotency_key"), "")
        )
        if self.readback_override is not None:
            body = deepcopy(self.readback_override)
            if isinstance(body, Mapping) and effect_key in body:
                body = deepcopy(body[effect_key])
        else:
            record = self.effects_by_key.get(effect_key)
            body = {
                "status": "CONFIRMED" if record else "NOT_FOUND",
                "effect_key": effect_key,
                "effect": deepcopy(record),
            }
        envelope = {
            "provider_id": self.provider_id,
            "query_id": f"{self.provider_id}:readback:{len(self.ledger.records) + 1}",
            "channel_outcome": "RESPONSE",
            "native_body": body,
            "native_response_sha256": digest(body),
        }
        self.ledger.append("READBACK", {"request": dict(request), "response": envelope})
        return envelope


class AcceptanceProvider:
    """Independent Acceptance owner; it may return wrong/stale/refused objects."""

    def __init__(self, config: Mapping[str, Any] | None):
        self.config = deepcopy(dict(config or {}))
        self.provider_id = str(
            _first(
                self.config,
                ("provider_id", "owner_id", "acceptance_owner_id"),
                "acceptance-owner",
            )
        )
        self.native_response = deepcopy(
            _first(self.config, ("native_response", "response", "readback"), {})
        )
        self.ledger = AppendOnlyLedger(self.provider_id)

    def readback(self, request: Mapping[str, Any]) -> dict[str, Any]:
        response = deepcopy(self.native_response)
        if not isinstance(response, Mapping):
            response = {"body": response}
        response = dict(response)
        transport = str(
            _first(response, ("channel_outcome", "transport", "transport_status"), "RESPONSE")
        ).upper()
        body = deepcopy(_first(response, ("native_body", "body", "payload"), response))
        envelope = {
            "provider_id": self.provider_id,
            "query_id": f"{self.provider_id}:acceptance:{len(self.ledger.records) + 1}",
            "channel_outcome": transport,
            "native_body": body,
            "native_response_sha256": digest(body),
        }
        self.ledger.append("ACCEPTANCE_READBACK", {"request": dict(request), "response": envelope})
        return envelope


@dataclass
class SemanticRuntime:
    runtime_id: str
    epoch: int
    public_packet: dict[str, Any]
    node_states: dict[str, str] = field(default_factory=dict)
    active_intents: dict[str, dict[str, Any]] = field(default_factory=dict)
    uncertain_effects: dict[str, dict[str, Any]] = field(default_factory=dict)
    effect_witnesses: dict[str, dict[str, Any]] = field(default_factory=dict)
    acceptance_records: list[dict[str, Any]] = field(default_factory=list)
    authority_observations: list[dict[str, Any]] = field(default_factory=list)
    obligations: list[dict[str, Any]] = field(default_factory=list)
    timers: list[dict[str, Any]] = field(default_factory=list)
    human_holds: list[dict[str, Any]] = field(default_factory=list)
    fenced: bool = False
    ledger: AppendOnlyLedger = field(init=False)

    def __post_init__(self) -> None:
        self.ledger = AppendOnlyLedger(self.runtime_id)
        graph = _first(self.public_packet, ("public_graph", "dependency_graph", "graph"), {})
        nodes = _first(graph, ("nodes",), []) if isinstance(graph, Mapping) else []
        for node in nodes:
            node_id = node if isinstance(node, str) else _first(node, ("id", "node_id", "name"))
            if node_id is not None:
                self.node_states[str(node_id)] = "PRESERVED"
        self.ledger.append(
            "RUNTIME_STARTED", {"runtime_id": self.runtime_id, "epoch": self.epoch}
        )

    def persist_intent(self, operation: Mapping[str, Any]) -> dict[str, Any]:
        effect_key = str(
            _first(operation, ("semantic_effect_key", "effect_key", "idempotency_key"), "")
        )
        intent = {
            "intent_id": f"{self.runtime_id}:intent:{len(self.active_intents) + 1}",
            "runtime_id": self.runtime_id,
            "coordinator_epoch": self.epoch,
            "operation": deepcopy(dict(operation)),
            "semantic_effect_key": effect_key,
            "status": "INTENT_PERSISTED",
        }
        self.active_intents[effect_key] = intent
        self.ledger.append("INTENT_PERSISTED", intent)
        return deepcopy(intent)

    def record_authority_observation(self, response: Mapping[str, Any]) -> None:
        self.authority_observations.append(deepcopy(dict(response)))
        self.ledger.append("AUTHORITY_OBSERVATION", dict(response))

    def record_dispatch(self, effect_key: str, response: Mapping[str, Any]) -> None:
        if effect_key in self.active_intents:
            self.active_intents[effect_key]["status"] = "DISPATCHED"
        if str(response.get("commit_status", "")).upper() == "UNKNOWN_TO_CALLER":
            self.uncertain_effects[effect_key] = {
                "effect_key": effect_key,
                "dispatch_response": deepcopy(dict(response)),
            }
        self.ledger.append("DISPATCH_OBSERVED", dict(response))

    def record_readback(self, effect_key: str, response: Mapping[str, Any]) -> None:
        body = response.get("native_body", {})
        status = str(_first(body, ("status", "state", "result"), "")).upper()
        encoded = json.dumps(body, ensure_ascii=False, sort_keys=True).lower()
        if not status:
            if any(
                marker in encoded
                for marker in (
                    '"phase": "completed"',
                    '"phase":"completed"',
                    '"status": "confirmed"',
                    '"status":"confirmed"',
                )
            ):
                status = "CONFIRMED"
            elif any(
                marker in encoded
                for marker in (
                    "object_not_found",
                    "effect_not_found",
                    '"status_code": 404',
                    '"status_code":404',
                )
            ):
                status = "NOT_FOUND"
        if status in {"CONFIRMED", "COMMITTED", "SUCCEEDED", "EFFECT_TRUE", "TRUE"}:
            self.effect_witnesses[effect_key] = deepcopy(dict(response))
            self.uncertain_effects.pop(effect_key, None)
            if effect_key in self.active_intents:
                self.active_intents[effect_key]["status"] = "CONFIRMED"
        elif status in {"NOT_FOUND", "NOT_COMMITTED", "ABSENT", "FALSE"}:
            self.uncertain_effects.pop(effect_key, None)
            if effect_key in self.active_intents:
                self.active_intents[effect_key]["status"] = "NOT_COMMITTED"
        self.ledger.append("EFFECT_READBACK", dict(response))

    def record_acceptance(self, response: Mapping[str, Any]) -> None:
        self.acceptance_records.append(deepcopy(dict(response)))
        self.ledger.append("ACCEPTANCE_READBACK", dict(response))

    def apply_reopen(self, action: str, closure: Iterable[str], reason: str) -> None:
        normalized = sorted({str(node) for node in closure})
        for node in normalized:
            self.node_states[node] = "REOPENED"
        self.ledger.append(
            "REOPEN_APPLIED",
            {"action": action, "closure": normalized, "reason": reason},
        )

    def fence(self, new_epoch: int) -> None:
        self.fenced = True
        self.ledger.append(
            "RUNTIME_FENCED", {"old_epoch": self.epoch, "new_epoch": new_epoch}
        )

    def export_capsule(self) -> dict[str, Any]:
        operation = _first(self.public_packet, ("operation", "exact_operation"), {})
        active_nodes = sorted(
            node for node, state in self.node_states.items() if state != "REOPENED"
        )
        effect_keys = sorted(
            {
                str(key)
                for key in (
                    list(self.active_intents)
                    + list(self.uncertain_effects)
                    + list(self.effect_witnesses)
                )
                if key
            }
        )
        capsule = {
            "schema_version": "g7-recovery-capsule-v1",
            "case_id": _first(self.public_packet, ("case_id", "episode_id", "relation_id")),
            "goal_version": _first(self.public_packet, ("goal_version", "goal")),
            "relation_version": _first(
                self.public_packet, ("relation_version", "relation_version_id")
            ),
            "active_nodes": active_nodes,
            "authority_observations": deepcopy(self.authority_observations),
            "effect_intents": deepcopy(self.active_intents),
            "semantic_effect_keys": effect_keys,
            "operation": deepcopy(operation),
            "node_states": deepcopy(self.node_states),
            "active_intents": deepcopy(self.active_intents),
            "uncertain_effects": deepcopy(self.uncertain_effects),
            "effect_witnesses": deepcopy(self.effect_witnesses),
            "acceptance_records": deepcopy(self.acceptance_records),
            "compensation_obligations": deepcopy(self.obligations),
            "timers": deepcopy(self.timers),
            "human_holds": deepcopy(self.human_holds),
            "policy_versions": deepcopy(
                _first(self.public_packet, ("policy_versions",), [])
            ),
            "connector_versions": deepcopy(
                _first(self.public_packet, ("connector_versions",), [])
            ),
            "coordinator_epoch": self.epoch,
            "fences": {"runtime_fenced": self.fenced, "epoch": self.epoch},
            "unresolved_items": {
                "uncertain_effects": sorted(self.uncertain_effects),
                "human_holds": deepcopy(self.human_holds),
            },
            "history_refs": {"source_ledger_root": self.ledger.root()},
            "source_runtime_id": self.runtime_id,
            "source_epoch": self.epoch,
            "source_ledger_root": self.ledger.root(),
            "exported_history": self.ledger.snapshot(),
        }
        capsule["capsule_sha256"] = digest(capsule)
        self.ledger.append(
            "CAPSULE_EXPORTED",
            {"capsule_sha256": capsule["capsule_sha256"], "effect_key": _first(operation, ("semantic_effect_key", "effect_key"))},
        )
        return capsule

    def import_capsule(self, capsule: Mapping[str, Any]) -> dict[str, Any]:
        supplied = deepcopy(dict(capsule))
        claimed = supplied.pop("capsule_sha256", None)
        computed = digest(supplied)
        required = {
            "schema_version",
            "case_id",
            "goal_version",
            "relation_version",
            "operation",
            "active_nodes",
            "authority_observations",
            "effect_intents",
            "semantic_effect_keys",
            "node_states",
            "active_intents",
            "uncertain_effects",
            "effect_witnesses",
            "acceptance_records",
            "compensation_obligations",
            "timers",
            "human_holds",
            "policy_versions",
            "connector_versions",
            "coordinator_epoch",
            "fences",
            "unresolved_items",
            "history_refs",
            "source_runtime_id",
            "source_epoch",
            "source_ledger_root",
        }
        missing = sorted(required - set(supplied))
        valid_hash = claimed == computed
        imported = not missing and valid_hash
        if imported:
            self.node_states = deepcopy(supplied["node_states"])
            self.active_intents = deepcopy(supplied["active_intents"])
            self.uncertain_effects = deepcopy(supplied["uncertain_effects"])
            self.effect_witnesses = deepcopy(supplied["effect_witnesses"])
            self.acceptance_records = deepcopy(supplied["acceptance_records"])
            self.obligations = deepcopy(supplied["compensation_obligations"])
            self.timers = deepcopy(supplied["timers"])
            self.human_holds = deepcopy(supplied.get("human_holds", []))
        result = {
            "imported": imported,
            "valid_hash": valid_hash,
            "missing_fields": missing,
            "claimed_capsule_sha256": claimed,
            "computed_capsule_sha256": computed,
        }
        self.ledger.append("CAPSULE_IMPORT", result)
        return result


def mutate_capsule(
    capsule: Mapping[str, Any],
    *,
    drop_fields: Iterable[str] = (),
    rename_fields: Mapping[str, str] | None = None,
    duplicate_fields: Mapping[str, str] | None = None,
    resign: bool = False,
) -> dict[str, Any]:
    """Apply connector/runtime migration faults without consulting an oracle."""

    result = deepcopy(dict(capsule))
    for field_name in drop_fields:
        result.pop(str(field_name), None)
    for old, new in dict(rename_fields or {}).items():
        if old in result:
            result[str(new)] = result.pop(old)
    for source, destination in dict(duplicate_fields or {}).items():
        if source in result:
            result[str(destination)] = deepcopy(result[source])
    if resign:
        unsigned = deepcopy(result)
        unsigned.pop("capsule_sha256", None)
        result["capsule_sha256"] = digest(unsigned)
    return result


def build_runtime_pair(
    public_packet: Mapping[str, Any],
    runtime_scenario: Mapping[str, Any] | None,
) -> tuple[SemanticRuntime, SemanticRuntime]:
    scenario = dict(runtime_scenario or {})
    source_epoch = int(_first(scenario, ("source_epoch", "old_epoch"), 1))
    target_epoch = int(_first(scenario, ("target_epoch", "new_epoch"), source_epoch + 1))
    source = SemanticRuntime(
        str(_first(scenario, ("source_runtime_id",), "source-runtime")),
        source_epoch,
        deepcopy(dict(public_packet)),
    )
    target = SemanticRuntime(
        str(_first(scenario, ("target_runtime_id",), "target-runtime")),
        target_epoch,
        deepcopy(dict(public_packet)),
    )
    initial = _first(scenario, ("initial_state", "source_state"), {})
    if isinstance(initial, Mapping):
        source.active_intents.update(deepcopy(initial.get("active_intents", {})))
        source.uncertain_effects.update(deepcopy(initial.get("uncertain_effects", {})))
        source.effect_witnesses.update(deepcopy(initial.get("effect_witnesses", {})))
        source.acceptance_records.extend(deepcopy(initial.get("acceptance_records", [])))
        source.obligations.extend(deepcopy(initial.get("obligations", [])))
        source.timers.extend(deepcopy(initial.get("timers", [])))
    return source, target
