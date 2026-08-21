"""Parent-owned experiment runner for the crossed-square evaluation."""

from __future__ import annotations

import copy
import inspect
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from baselines import (
    center_authority_path,
    center_relation_path,
    composition_authority_path,
    composition_relation_path,
    workflow_authority_path,
    workflow_relation_path,
)
from authority_evaluator import evaluate_authority
from authority_truth_broker import AuthorityTruthBroker
from common import canonical_bytes, public_key_hex, sha256_hex
from integration_evaluator import integrate
from relation_evaluator import evaluate_relation
from relation_truth_broker import RelationTruthBroker
from world_factory import (
    AuthorityPrivateWorld,
    RelationPrivateWorld,
    WorldBundle,
    build_core_worlds,
    build_presentation_controls,
    build_mutation_pairs,
    build_t5_case,
)


ROOT = Path(__file__).resolve().parent
BASELINE_IDS = ("B0", "B1", "B2", "B3A", "B3B", "B4", "B5")
RUN_SEAL_KEY = Ed25519PrivateKey.generate()


def _evidence_material(parent_record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in parent_record.items()
        if key != "evidence_anchor_sha256"
    }


def _completion_material(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if key != "completion_seal"
    }


def _seal_completed_run(row: dict[str, Any]) -> dict[str, Any]:
    digest = sha256_hex(canonical_bytes(_completion_material(row)))
    signed = canonical_bytes(
        {
            "domain": "TOWOW-WAVE009-COMPLETED-RUN",
            "completed_material_sha256": digest,
        }
    )
    row["completion_seal"] = {
        "domain": "TOWOW-WAVE009-COMPLETED-RUN",
        "completed_material_sha256": digest,
        "signature_hex": RUN_SEAL_KEY.sign(signed).hex(),
    }
    return row


def verify_completed_run_record(
    row: dict[str, Any],
    *,
    trusted_public_key_hex: str | None = None,
) -> bool:
    try:
        record = row["parent_record"]
        evidence_digest = sha256_hex(
            canonical_bytes(_evidence_material(record))
        )
        if evidence_digest != record["evidence_anchor_sha256"]:
            return False
        for name in (
            "relation_public",
            "authority_public",
            "integration_public",
        ):
            if (
                row[name].get("evidence_anchor_sha256")
                != evidence_digest
            ):
                return False
        seal = row["completion_seal"]
        completion_digest = sha256_hex(
            canonical_bytes(_completion_material(row))
        )
        if completion_digest != seal["completed_material_sha256"]:
            return False
        signed = canonical_bytes(
            {
                "domain": seal["domain"],
                "completed_material_sha256": completion_digest,
            }
        )
        trusted_key = (
            trusted_public_key_hex or public_key_hex(RUN_SEAL_KEY)
        )
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(trusted_key)
        ).verify(bytes.fromhex(seal["signature_hex"]), signed)
        return seal["domain"] == "TOWOW-WAVE009-COMPLETED-RUN"
    except (InvalidSignature, KeyError, TypeError, ValueError):
        return False


def _invoke_worker(
    baseline_id: str,
    packet: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    stdin_bytes = canonical_bytes(packet)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [sys.executable, str(ROOT / "baseline_worker.py"), baseline_id],
        cwd=ROOT,
        input=stdin_bytes,
        capture_output=True,
        env=environment,
        timeout=20,
    )
    exit_record = {
        "returncode": process.returncode,
        "stderr_hex": process.stderr.hex(),
        "stderr_byte_count": len(process.stderr),
    }
    if process.returncode != 0:
        raise RuntimeError(
            f"BASELINE_WORKER_FAILED:{baseline_id}:"
            f"{process.stderr.decode('utf-8', errors='replace')}"
        )
    candidate = json.loads(process.stdout.decode("utf-8"))
    return candidate, {
        "stdin_bytes": stdin_bytes,
        "stdout_bytes": process.stdout,
        "exit": exit_record,
    }


def _prepare(
    bundle: WorldBundle,
) -> tuple[
    RelationTruthBroker,
    AuthorityTruthBroker,
    dict[str, Any],
]:
    relation_broker = RelationTruthBroker(bundle.relation_private)
    authority_broker = AuthorityTruthBroker(bundle.authority_private)
    task = copy.deepcopy(bundle.public_packet["task"])
    packet = copy.deepcopy(bundle.public_packet)
    semantic_input = {
        "world_id": packet["world_id"],
        "task": task,
        "presentation": packet["presentation"],
    }
    packet["semantic_input_sha256"] = sha256_hex(
        canonical_bytes(semantic_input)
    )
    current_head = (
        5
        if bundle.authority_private.authority_mode == "REVOKED"
        else bundle.authority_private.current_revoke_head
    )
    packet["issuance_context"] = {
        "world_id": packet["world_id"],
        "semantic_input_sha256": packet["semantic_input_sha256"],
        "current_relation_version": (
            bundle.relation_private.current_version
        ),
        "current_authority_head": current_head,
        "issuance_id": f"i-{secrets.token_hex(12)}",
        "task_fingerprint": task["task_fingerprint"],
    }
    packet["relation"] = relation_broker.issue_public_evidence(
        task, packet["issuance_context"]
    )
    packet["authority"] = authority_broker.issue_public_evidence(
        task, packet["issuance_context"]
    )
    packet["candidate_claimed_identity"] = "IGNORED-CANDIDATE-LABEL"
    return relation_broker, authority_broker, packet


def run_single(
    bundle: WorldBundle,
    baseline_id: str,
) -> dict[str, Any]:
    if baseline_id not in BASELINE_IDS:
        raise ValueError(f"BASELINE_NOT_REGISTERED:{baseline_id}")
    run_id = f"r-{secrets.token_hex(12)}"
    relation_broker, authority_broker, packet = _prepare(bundle)
    candidate, transport = _invoke_worker(baseline_id, packet)
    relation_cost = len(packet["relation"]["events"])
    authority_cost = len(packet["authority"]["events"])
    operations = [
        {
            "operation": "SPAWN_BASELINE_WORKER",
            "implementation_id": baseline_id,
        },
        {
            "operation": "WRITE_EXACT_STDIN",
            "byte_count": len(transport["stdin_bytes"]),
            "sha256": sha256_hex(transport["stdin_bytes"]),
        },
        {
            "operation": "READ_EXACT_STDOUT",
            "byte_count": len(transport["stdout_bytes"]),
            "sha256": sha256_hex(transport["stdout_bytes"]),
        },
        {
            "operation": "CAPTURE_PROCESS_EXIT",
            "returncode": transport["exit"]["returncode"],
        },
        {
            "operation": "EVALUATE_RELATION_PUBLIC_OUTPUT",
            "evidence_operations": relation_cost,
        },
        {
            "operation": "EVALUATE_AUTHORITY_PUBLIC_OUTPUT",
            "evidence_operations": authority_cost,
        },
        {"operation": "INTEGRATE_PUBLIC_OUTPUTS_ONLY"},
    ]
    parent_record = {
        "schema": "towow.wave009-parent-run-record.v1",
        "run_id": run_id,
        "world_id": packet["world_id"],
        "implementation_id": baseline_id,
        "candidate_claimed_identity_ignored": candidate.get(
            "candidate_claimed_identity"
        ),
        "identity_source": "PARENT_BASELINE_REGISTRY",
        "byte_provenance": "PARENT_PIPE_CAPTURE",
        "stdin_hex": transport["stdin_bytes"].hex(),
        "stdin_byte_count": len(transport["stdin_bytes"]),
        "stdin_sha256": sha256_hex(transport["stdin_bytes"]),
        "stdout_hex": transport["stdout_bytes"].hex(),
        "stdout_byte_count": len(transport["stdout_bytes"]),
        "stdout_sha256": sha256_hex(transport["stdout_bytes"]),
        "exit": transport["exit"],
        "operations": copy.deepcopy(operations),
        "relation_broker_ledger": relation_broker.ledger_snapshot(),
        "authority_broker_ledger": authority_broker.ledger_snapshot(),
        "successful_reservations": (
            authority_broker.successful_reservation_count()
        ),
        "worker_received_broker_object": False,
        "worker_received_private_truth": False,
        "filesystem_sandbox": False,
    }
    parent_record["evidence_anchor_sha256"] = sha256_hex(
        canonical_bytes(_evidence_material(parent_record))
    )
    evidence_anchor_sha256 = parent_record["evidence_anchor_sha256"]
    relation_public = evaluate_relation(
        relation_broker,
        candidate["relation"],
        run_id=run_id,
        world_id=packet["world_id"],
        operation_cost=relation_cost,
        evidence_anchor_sha256=evidence_anchor_sha256,
    )
    authority_public = evaluate_authority(
        authority_broker,
        candidate["authority"],
        run_id=run_id,
        world_id=packet["world_id"],
        operation_cost=authority_cost,
        evidence_anchor_sha256=evidence_anchor_sha256,
    )
    integration_public = integrate(relation_public, authority_public)
    truth_summary = {
        "relation_valid": bundle.relation_private.relation_valid,
        "authority_valid": bundle.authority_private.authority_valid,
        "task_kind": bundle.relation_private.task_kind,
        "horizon": bundle.relation_private.horizon,
        "relation_mode": bundle.relation_private.invalid_mode,
        "authority_mode": bundle.authority_private.authority_mode,
    }
    expected_ready = (
        truth_summary["relation_valid"]
        and truth_summary["authority_valid"]
    )
    row = {
        "schema": "towow.wave009-evaluated-run.v1",
        "baseline_id": baseline_id,
        "truth_summary": truth_summary,
        "relation_public": relation_public,
        "authority_public": authority_public,
        "integration_public": integration_public,
        "integration_exact": (
            integration_public["execution_ready"] == expected_ready
        ),
        "mechanism_trace": candidate["mechanism_trace"],
        "parent_record": parent_record,
    }
    return _seal_completed_run(row)


def _pair_results(
    pairs: dict[str, tuple[WorldBundle, WorldBundle]],
) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    results: dict[str, list[dict[str, Any]]] = {}
    all_distinguished = True
    for name, pair in pairs.items():
        rows = [run_single(bundle, "B5") for bundle in pair]
        results[name] = rows
        left_signature = (
            rows[0]["relation_public"]["formed"],
            rows[0]["relation_public"]["material_change"],
            rows[0]["relation_public"]["semantic_loss"],
            rows[0]["authority_public"]["authority_chain_valid"],
            rows[0]["authority_public"]["error"],
        )
        right_signature = (
            rows[1]["relation_public"]["formed"],
            rows[1]["relation_public"]["material_change"],
            rows[1]["relation_public"]["semantic_loss"],
            rows[1]["authority_public"]["authority_chain_valid"],
            rows[1]["authority_public"]["error"],
        )
        all_distinguished = all_distinguished and left_signature != right_signature
    return results, all_distinguished


def _public_probe(
    packet: dict[str, Any],
) -> dict[str, Any]:
    candidate, _ = _invoke_worker("B5", packet)
    return candidate


def _binding_attacks() -> dict[str, dict[str, Any]]:
    target = build_core_worlds()[1]
    donor = build_core_worlds()[5]
    _, _, target_packet = _prepare(target)
    _, _, donor_packet = _prepare(donor)

    attacks: dict[str, dict[str, Any]] = {}

    def record(name: str, packet: dict[str, Any]) -> None:
        decision = _public_probe(packet)["authority"]
        attacks[name] = {
            "rejected": decision["authority_chain_valid"] is False,
            "error": decision["error"],
        }

    cross_world = copy.deepcopy(target_packet)
    cross_world["authority"] = copy.deepcopy(donor_packet["authority"])
    record("cross_world_section_transplant", cross_world)

    top_world = copy.deepcopy(target_packet)
    top_world["world_id"] = f"w-{secrets.token_hex(10)}"
    record("top_level_world_id_tamper", top_world)

    text_tamper = copy.deepcopy(target_packet)
    text_tamper["presentation"]["source_text"] += " TAMPERED"
    record("top_level_text_tamper", text_tamper)

    old_section = copy.deepcopy(target_packet["authority"])
    fresh_head_bundle = WorldBundle(
        public_packet=copy.deepcopy(target.public_packet),
        relation_private=target.relation_private,
        authority_private=AuthorityPrivateWorld(
            truth_id=target.authority_private.truth_id,
            world_id=target.authority_private.world_id,
            task_kind=target.authority_private.task_kind,
            authority_mode="NONE",
            current_relation_version=(
                target.authority_private.current_relation_version
            ),
            current_revoke_head=(
                target.authority_private.current_revoke_head + 1
            ),
        ),
    )
    _, _, fresh_head_packet = _prepare(fresh_head_bundle)
    fresh_head_packet["authority"] = old_section
    record(
        "old_complete_section_replay_after_head_change",
        fresh_head_packet,
    )

    new_version = "REL-V3"
    fresh_version_bundle = WorldBundle(
        public_packet=copy.deepcopy(target.public_packet),
        relation_private=RelationPrivateWorld(
            truth_id=target.relation_private.truth_id,
            world_id=target.relation_private.world_id,
            task_kind=target.relation_private.task_kind,
            horizon=target.relation_private.horizon,
            relation_valid=target.relation_private.relation_valid,
            invalid_mode=target.relation_private.invalid_mode,
            current_version=new_version,
            material_change=target.relation_private.material_change,
            semantic_retained=target.relation_private.semantic_retained,
            source_text=target.relation_private.source_text,
            semantic_payload=target.relation_private.semantic_payload,
        ),
        authority_private=AuthorityPrivateWorld(
            truth_id=target.authority_private.truth_id,
            world_id=target.authority_private.world_id,
            task_kind=target.authority_private.task_kind,
            authority_mode="NONE",
            current_relation_version=new_version,
            current_revoke_head=(
                target.authority_private.current_revoke_head
            ),
        ),
    )
    _, _, fresh_version_packet = _prepare(fresh_version_bundle)
    fresh_version_packet["authority"] = copy.deepcopy(old_section)
    record(
        "old_complete_section_replay_after_version_change",
        fresh_version_packet,
    )

    event_transplant = copy.deepcopy(target_packet)
    donor_mandate = next(
        event
        for event in donor_packet["authority"]["events"]
        if event["kind"] == "MANDATE"
    )
    for index, event in enumerate(event_transplant["authority"]["events"]):
        if event["kind"] == "MANDATE":
            event_transplant["authority"]["events"][index] = copy.deepcopy(
                donor_mandate
            )
            break
    record("cross_world_event_transplant", event_transplant)
    return attacks


def _sequence_cardinality_attacks() -> dict[
    str, dict[str, dict[str, Any]]
]:
    bundle = next(
        item
        for item in build_core_worlds()
        if item.relation_private.relation_valid
        and item.authority_private.authority_valid
        and item.relation_private.horizon == "BOUNDED"
    )
    _, _, base_packet = _prepare(bundle)
    packets: dict[str, dict[str, Any]] = {}

    relation_reversed = copy.deepcopy(base_packet)
    relation_reversed["relation"]["events"].reverse()
    packets["relation_events_reversed"] = relation_reversed

    authority_reversed = copy.deepcopy(base_packet)
    authority_reversed["authority"]["events"].reverse()
    packets["authority_events_reversed"] = authority_reversed

    proposal_deleted = copy.deepcopy(base_packet)
    proposal_deleted["relation"]["events"] = [
        event
        for event in proposal_deleted["relation"]["events"]
        if event["kind"] != "PROPOSAL"
    ]
    packets["unique_proposal_deleted"] = proposal_deleted

    proposal_duplicated = copy.deepcopy(base_packet)
    proposal = next(
        event
        for event in proposal_duplicated["relation"]["events"]
        if event["kind"] == "PROPOSAL"
    )
    proposal_duplicated["relation"]["events"].insert(
        0, copy.deepcopy(proposal)
    )
    packets["proposal_duplicated"] = proposal_duplicated

    results: dict[str, dict[str, dict[str, Any]]] = {}
    for baseline in ("B0", "B1", "B5"):
        results[baseline] = {}
        for name, packet in packets.items():
            candidate, _ = _invoke_worker(baseline, packet)
            if name == "authority_events_reversed":
                decision = candidate["authority"]
                error = decision["error"]
                rejected = decision["authority_chain_valid"] is False
            else:
                decision = candidate["relation"]
                error = decision.get("context_error")
                rejected = decision["formed"] is False
            results[baseline][name] = {
                "rejected": rejected,
                "error": error,
            }
    return results


def _non_implication_gates(
    core_runs: list[dict[str, Any]],
    pair_runs: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, bool], dict[str, Any]]:
    sample = next(
        item
        for item in build_core_worlds()
        if item.relation_private.relation_valid
        and item.authority_private.authority_valid
        and item.relation_private.horizon == "BOUNDED"
    )
    _, _, packet = _prepare(sample)
    base_probe = _public_probe(packet)

    no_explain = copy.deepcopy(packet)
    no_explain["relation"]["events"] = [
        item
        for item in no_explain["relation"]["events"]
        if item["kind"] != "EXPLAIN_BACK"
    ]
    explain_probe = _public_probe(no_explain)

    no_stance = copy.deepcopy(packet)
    no_stance["relation"]["events"] = [
        item
        for item in no_stance["relation"]["events"]
        if item["kind"] != "STANCE"
    ]
    stance_probe = _public_probe(no_stance)

    no_commitment = copy.deepcopy(packet)
    no_commitment["authority"]["events"] = [
        item
        for item in no_commitment["authority"]["events"]
        if item["kind"] != "COMMITMENT"
    ]
    commitment_probe = _public_probe(no_commitment)

    duplicate = pair_runs["UNIQUE_VS_DUPLICATE"][1]
    controller = pair_runs["PRINCIPAL_VS_CONTROLLER"][1]
    revoked = pair_runs["ACTIVE_VS_REVOKED"][1]
    durable_invalid_auth = any(
        row["truth_summary"]["horizon"] == "DURABLE"
        and row["truth_summary"]["relation_valid"]
        and not row["truth_summary"]["authority_valid"]
        and row["relation_public"]["formed"]
        and not row["integration_public"]["execution_ready"]
        for row in core_runs
        if row["baseline_id"] == "B5"
    )
    material = pair_runs["PARAMETER_VS_MATERIAL"][1]
    gates = {
        "ACK_NOT_EXPLAIN_BACK": all(
            [
                base_probe["relation"]["formed"],
                not explain_probe["relation"]["formed"],
                any(
                    event["kind"] == "ACK"
                    for event in no_explain["relation"]["events"]
                ),
            ]
        ),
        "EXPLAIN_BACK_NOT_STANCE": not stance_probe["relation"]["formed"],
        "COUNTER_NOT_COMMITMENT": (
            commitment_probe["authority"]["commitment_valid"] is False
        ),
        "COMMITMENT_NOT_RESERVATION": all(
            [
                duplicate["authority_public"]["commitment_valid"],
                not duplicate["authority_public"]["reservation_valid"],
            ]
        ),
        "RESERVATION_NOT_MANDATE": all(
            [
                controller["authority_public"]["reservation_valid"],
                not controller["authority_public"]["mandate_valid"],
            ]
        ),
        "DURABLE_RELATION_NOT_BLANKET_AUTHORITY": durable_invalid_auth,
        "REVOCATION_DOES_NOT_DELETE_RELATION_HISTORY": all(
            [
                revoked["relation_public"]["formed"],
                not revoked["authority_public"]["mandate_valid"],
            ]
        ),
        "MATERIALITY_DOES_NOT_GRANT_ACCEPTANCE_AUTHORITY": all(
            [
                material["relation_public"]["material_change"],
                material["authority_public"]["standing_valid"],
                not material["integration_public"]["execution_ready"],
            ]
        ),
    }
    details = {
        "remove_explain_back_only": {
            "base_relation_formed": base_probe["relation"]["formed"],
            "remaining_explain_back": sum(
                event["kind"] == "EXPLAIN_BACK"
                for event in no_explain["relation"]["events"]
            ),
            "remaining_stance": sum(
                event["kind"] == "STANCE"
                for event in no_explain["relation"]["events"]
            ),
            "mutated_relation_formed": explain_probe["relation"][
                "formed"
            ],
        },
        "remove_stance_only": {
            "base_relation_formed": base_probe["relation"]["formed"],
            "remaining_explain_back": sum(
                event["kind"] == "EXPLAIN_BACK"
                for event in no_stance["relation"]["events"]
            ),
            "remaining_stance": sum(
                event["kind"] == "STANCE"
                for event in no_stance["relation"]["events"]
            ),
            "mutated_relation_formed": stance_probe["relation"]["formed"],
        },
    }
    return gates, details


class T5AuthoritativePlatform:
    """Parent-owned fixed-platform state machine with an idempotency ledger."""

    def __init__(self, contract: dict[str, Any]) -> None:
        self.__contract = copy.deepcopy(contract)
        self.__idempotency: dict[str, dict[str, Any]] = {}
        self.__accounts: dict[str, dict[str, Any]] = {}
        self.__ledger: list[dict[str, Any]] = []

    def authoritative_readback(self, buyer: str) -> dict[str, Any]:
        account = self.__accounts.get(buyer)
        if account is None:
            return {
                "buyer": buyer,
                "authoritative_state": "ABSENT",
                "active_seats": 0,
            }
        return copy.deepcopy(account)

    def ledger_snapshot(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.__ledger)

    def execute(
        self,
        request: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        request_bytes = canonical_bytes(request)
        request_sha256 = sha256_hex(request_bytes)
        previous = self.__idempotency.get(idempotency_key)
        if previous is not None:
            if previous["request_sha256"] != request_sha256:
                self.__ledger.append(
                    {
                        "operation": "IDEMPOTENCY_CONFLICT",
                        "idempotency_key": idempotency_key,
                        "request_sha256": request_sha256,
                    }
                )
                return {
                    "status": "IDEMPOTENCY_CONFLICT",
                    "reason": "SAME_KEY_DIFFERENT_EXACT_REQUEST_BYTES",
                }
            replay = copy.deepcopy(previous["result"])
            replay["status"] = "IDEMPOTENT_REPLAY"
            replay["operations"] = [
                {
                    "operation": "IDEMPOTENT_READBACK",
                    "request_sha256": request_sha256,
                }
            ]
            self.__ledger.append(
                {
                    "operation": "IDEMPOTENT_REPLAY",
                    "idempotency_key": idempotency_key,
                    "request_sha256": request_sha256,
                }
            )
            return replay

        buyer = request.get("buyer")
        catalog_item = self.__contract.get("catalog", {}).get(
            request.get("sku")
        )
        required_machine = [
            "REQUEST_VALIDATED",
            "REQUEST_CREATED",
            "BUYER_APPROVED",
            "SEATS_PROVISIONED",
            "TARGET_READBACK",
            "CLOSED",
        ]
        valid_contract = (
            self.__contract.get("authoritative_state_machine")
            == required_machine
            and isinstance(buyer, str)
            and bool(buyer.strip())
            and isinstance(catalog_item, dict)
            and catalog_item.get("monthly_price_cny")
            == request.get("total_price_cny")
            and catalog_item.get("seat_count")
            == request.get("seat_count")
            and request.get("buyer_approval") == "APPROVED"
        )
        if not valid_contract:
            self.__ledger.append(
                {
                    "operation": "REQUEST_REJECTED",
                    "idempotency_key": idempotency_key,
                    "request_sha256": request_sha256,
                }
            )
            return {
                "status": "BYPASS_UNAVAILABLE",
                "reason": "NO_EXECUTABLE_AUTHORITATIVE_PLATFORM_CONTRACT",
            }

        operations = []
        for operation, state in [
            ("VALIDATE_EXACT_REQUEST", "REQUEST_VALIDATED"),
            ("CREATE_REQUEST", "REQUEST_CREATED"),
            ("BUYER_APPROVE", "BUYER_APPROVED"),
            ("PROVISION_SEATS", "SEATS_PROVISIONED"),
            ("TARGET_READBACK", "TARGET_READBACK"),
            ("CLOSE_REQUEST", "CLOSED"),
        ]:
            entry = {
                "operation": operation,
                "authoritative_state": state,
                "request_sha256": request_sha256,
                "idempotency_key": idempotency_key,
            }
            operations.append(entry)
            self.__ledger.append(copy.deepcopy(entry))
            if operation == "PROVISION_SEATS":
                self.__accounts[buyer] = {
                    "buyer": buyer,
                    "sku": request["sku"],
                    "active_seats": request["seat_count"],
                    "billing_cadence": request["billing_cadence"],
                    "authoritative_state": "SEATS_PROVISIONED",
                }
            elif operation == "CLOSE_REQUEST":
                self.__accounts[buyer]["authoritative_state"] = "CLOSED"
        readback = self.authoritative_readback(buyer)
        result = {
            "status": "BYPASS_COMPLETE",
            "operations": operations,
            "target_readback": readback,
            "relation_objects_created": 0,
            "extra_authority_objects_created": 0,
            "evidence_boundary": (
                "PARENT_OWNED_AUTHORITATIVE_STATE_AND_READBACK"
            ),
        }
        self.__idempotency[idempotency_key] = {
            "request_sha256": request_sha256,
            "result": copy.deepcopy(result),
        }
        return result


def execute_t5_platform(
    case: dict[str, Any],
    *,
    platform: T5AuthoritativePlatform | None = None,
    idempotency_key: str = "T5-DEFAULT-REQUEST",
) -> dict[str, Any]:
    request = case.get("request", {})
    contract = case.get("platform_contract", {})
    required_machine = [
        "REQUEST_VALIDATED",
        "REQUEST_CREATED",
        "BUYER_APPROVED",
        "SEATS_PROVISIONED",
        "TARGET_READBACK",
        "CLOSED",
    ]
    if contract.get("authoritative_state_machine") != required_machine:
        return {
            "status": "BYPASS_UNAVAILABLE",
            "reason": "NO_EXECUTABLE_AUTHORITATIVE_PLATFORM_CONTRACT",
        }
    owner = platform or T5AuthoritativePlatform(contract)
    return owner.execute(request, idempotency_key=idempotency_key)


def _summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for baseline in BASELINE_IDS:
        rows = [row for row in runs if row["baseline_id"] == baseline]
        summary[baseline] = {
            "worlds": len(rows),
            "relation_exact": sum(
                row["relation_public"]["assertion_valid"] for row in rows
            ),
            "authority_exact": sum(
                row["authority_public"]["assertion_valid"] for row in rows
            ),
            "integration_exact": sum(
                row["integration_exact"] for row in rows
            ),
            "execution_ready": sum(
                row["integration_public"]["execution_ready"] for row in rows
            ),
            "stdin_bytes": sum(
                row["parent_record"]["stdin_byte_count"] for row in rows
            ),
            "stdout_bytes": sum(
                row["parent_record"]["stdout_byte_count"] for row in rows
            ),
        }
    return summary


def _concurrency_probe() -> dict[str, Any]:
    bundle = build_core_worlds()[0]
    task = bundle.public_packet["task"]
    observations = []
    for _ in range(20):
        broker = AuthorityTruthBroker(bundle.authority_private)
        result = broker.concurrent_reservation_probe(task)
        observations.append(
            {
                "successful": result["successful"],
                "conflicts": result["conflicts"],
            }
        )
    return {
        "runs": observations,
        "all_atomic": all(
            row == {"successful": 1, "conflicts": 1}
            for row in observations
        ),
    }


def decide_residual(matrix: dict[str, bool]) -> dict[str, Any]:
    all_pass = bool(matrix) and all(matrix.values())
    return {
        "residual_matrix_all_pass": all_pass,
        "existing_solution_result": (
            "POSITIVE_LOCAL_SYNTHETIC_EXISTING_COMPOSITION_SCOPED"
            if all_pass
            else "RESIDUAL_PRESENT_OR_HARNESS_INVALID"
        ),
        "b6_status": (
            "NOT_IMPLEMENTED_NO_OBSERVED_RESIDUAL"
            if all_pass
            else "NOT_IMPLEMENTED_PENDING_RESIDUAL_DIAGNOSIS"
        ),
    }


def run_experiment(*, write_outputs: bool = True) -> dict[str, Any]:
    core = build_core_worlds()
    runs = [
        run_single(bundle, baseline)
        for bundle in core
        for baseline in BASELINE_IDS
    ]
    pair_runs, all_distinguished = _pair_results(build_mutation_pairs())
    presentation_runs, _ = _pair_results(build_presentation_controls())
    similar = presentation_runs[
        "SAME_PRESENTATION_DIFFERENT_STRUCTURED_SEMANTICS"
    ]
    different = presentation_runs[
        "DIFFERENT_PRESENTATION_SAME_STRUCTURED_SEMANTICS"
    ]
    path_functions = {
        "B0_RELATION_CENTER": center_relation_path,
        "B1_RELATION_WORKFLOW": workflow_relation_path,
        "B5_RELATION_COMPOSITION": composition_relation_path,
        "B0_AUTHORITY_CENTER": center_authority_path,
        "B1_AUTHORITY_WORKFLOW": workflow_authority_path,
        "B5_AUTHORITY_COMPOSITION": composition_authority_path,
    }
    path_fingerprints = {
        name: sha256_hex(inspect.getsource(function).encode("utf-8"))
        for name, function in path_functions.items()
    }
    attacks = {
        "stale": pair_runs["CURRENT_VS_STALE"][1][
            "authority_public"
        ]["error"],
        "controller": pair_runs["PRINCIPAL_VS_CONTROLLER"][1][
            "authority_public"
        ]["error"],
        "revoked": pair_runs["ACTIVE_VS_REVOKED"][1][
            "authority_public"
        ]["error"],
        "duplicate": pair_runs["UNIQUE_VS_DUPLICATE"][1][
            "authority_public"
        ]["error"],
    }
    duplicate_bad = pair_runs["UNIQUE_VS_DUPLICATE"][1]
    t5_case = build_t5_case()
    t5_platform = T5AuthoritativePlatform(
        t5_case["platform_contract"]
    )
    t5_first = execute_t5_platform(
        t5_case,
        platform=t5_platform,
        idempotency_key="T5-FROZEN-REQUEST",
    )
    t5_replay = execute_t5_platform(
        t5_case,
        platform=t5_platform,
        idempotency_key="T5-FROZEN-REQUEST",
    )
    t5_conflict_case = copy.deepcopy(t5_case)
    t5_conflict_case["request"]["seat_count"] = 4
    t5_conflict = execute_t5_platform(
        t5_conflict_case,
        platform=t5_platform,
        idempotency_key="T5-FROZEN-REQUEST",
    )
    t5_missing_buyer_case = copy.deepcopy(t5_case)
    del t5_missing_buyer_case["request"]["buyer"]
    t5_missing_buyer = execute_t5_platform(
        t5_missing_buyer_case,
        platform=t5_platform,
        idempotency_key="T5-MISSING-BUYER",
    )
    summary = _summarize(runs)
    core_b0_b5_exact = all(
        summary[baseline][field] == 24
        for baseline in ("B0", "B5")
        for field in (
            "relation_exact",
            "authority_exact",
            "integration_exact",
        )
    )
    binding_results = _binding_attacks()
    sequence_results = _sequence_cardinality_attacks()
    non_implication_gates, non_implication_details = (
        _non_implication_gates(runs, pair_runs)
    )
    concurrency_result = _concurrency_probe()
    same_presentation_different_semantics = all(
        [
            similar[0]["relation_public"]["formed"],
            not similar[1]["relation_public"]["formed"],
            similar[0]["parent_record"]["stdin_sha256"]
            != similar[1]["parent_record"]["stdin_sha256"],
        ]
    )
    different_presentation_same_semantics = all(
        [
            different[0]["relation_public"]["formed"],
            different[1]["relation_public"]["formed"],
            different[0]["relation_public"]["stage"]
            == different[1]["relation_public"]["stage"],
            different[0]["parent_record"]["stdin_sha256"]
            != different[1]["parent_record"]["stdin_sha256"],
        ]
    )
    presentation_claim = (
        "PRESENTATION_NOOP_CONTROL_NOT_LANGUAGE_UNDERSTANDING_EVIDENCE"
    )
    all_completed_rows = (
        runs
        + [
            row
            for pair in pair_runs.values()
            for row in pair
        ]
        + [
            row
            for pair in presentation_runs.values()
            for row in pair
        ]
    )
    residual_matrix = {
        "core_b0_b5_exact": core_b0_b5_exact,
        "paired_mutations": all_distinguished,
        "binding_attacks": all(
            row["rejected"] for row in binding_results.values()
        ),
        "non_implication_gates": all(
            non_implication_gates.values()
        ),
        "sequence_and_cardinality": all(
            row["rejected"]
            for baseline in sequence_results.values()
            for row in baseline.values()
        ),
        "atomic_concurrency": concurrency_result["all_atomic"],
        "t5_state_and_idempotency": all(
            [
                t5_first["status"] == "BYPASS_COMPLETE",
                t5_replay["status"] == "IDEMPOTENT_REPLAY",
                t5_conflict["status"] == "IDEMPOTENCY_CONFLICT",
                t5_missing_buyer["status"] == "BYPASS_UNAVAILABLE",
                sum(
                    row["operation"] == "PROVISION_SEATS"
                    for row in t5_platform.ledger_snapshot()
                )
                == 1,
            ]
        ),
        "presentation_scope_honest": all(
            [
                same_presentation_different_semantics,
                different_presentation_same_semantics,
                presentation_claim
                == (
                    "PRESENTATION_NOOP_CONTROL_NOT_"
                    "LANGUAGE_UNDERSTANDING_EVIDENCE"
                ),
            ]
        ),
        "completed_run_record_seals": all(
            verify_completed_run_record(row)
            for row in all_completed_rows
        ),
        "single_authority_truth_representation": (
            "authority_valid"
            not in AuthorityPrivateWorld.__dataclass_fields__
        ),
        "distinct_paths_scoped_not_independent": (
            len(set(path_fingerprints.values()))
            == len(path_fingerprints)
        ),
    }
    residual_decision = decide_residual(residual_matrix)
    report = {
        "schema": "towow.wave009-g2-g5-crossed-square-report.v1",
        "status": "COMPLETE_LOCAL_SYNTHETIC",
        "trusted_run_seal_public_key_hex": public_key_hex(RUN_SEAL_KEY),
        "frozen_denominator": {
            "core_worlds": 24,
            "tasks": ["T3_SYNTHETIC_TASK_SPEC", "T4_SYNTHETIC_TASK_SPEC"],
            "horizons": ["ONE_SHOT", "BOUNDED", "DURABLE"],
            "relation_truth_values": [False, True],
            "authority_truth_values": [False, True],
            "baselines": list(BASELINE_IDS),
            "paired_mutations": 6,
            "presentation_noop_control_pairs": 2,
            "negative_control": "T5_NEGATIVE_CONTROL_SPEC",
        },
        "runs": runs,
        "mutation_pair_runs": pair_runs,
        "presentation_control_runs": presentation_runs,
        "implementation_independence": (
            "DISTINCT_PATHS_SAME_AUTHORING_STREAM"
        ),
        "implementation_path_fingerprints": path_fingerprints,
        "binding_attack_results": binding_results,
        "sequence_cardinality_attack_results": sequence_results,
        "mutation_results": {
            "all_six_pairs_distinguished": all_distinguished,
            "same_presentation_different_structured_semantics": (
                same_presentation_different_semantics
            ),
            "different_presentation_same_structured_semantics": (
                different_presentation_same_semantics
            ),
            "language_claim": presentation_claim,
            "attacks": attacks,
            "duplicate_pair": {
                "successful_reservations": duplicate_bad[
                    "parent_record"
                ]["successful_reservations"],
                "conflict_observed": (
                    duplicate_bad["authority_public"]["error"]
                    == "DUPLICATE_RESERVATION_CONFLICT"
                ),
            },
        },
        "non_implication_gate_results": non_implication_gates,
        "non_implication_probe_details": non_implication_details,
        "concurrency_probe": concurrency_result,
        "t5_bypass": t5_first,
        "t5_state_machine_attacks": {
            "idempotent_replay": t5_replay["status"],
            "same_key_changed_bytes": t5_conflict["status"],
            "missing_buyer": t5_missing_buyer["status"],
            "authoritative_readback": (
                t5_platform.authoritative_readback("BUYER-01")
            ),
            "parent_ledger": t5_platform.ledger_snapshot(),
        },
        "summary": {"core_by_baseline": summary},
        "residual_matrix": residual_matrix,
        **residual_decision,
        "limitations": [
            "LOCAL_SYNTHETIC",
            "NO_FILESYSTEM_SANDBOX",
            "SAME_AUTHORING_STREAM",
            "T3_NOT_REAL_TASK",
            "T4_SYNTHETIC_TASK",
            "NO_REAL_PRINCIPAL_AUTHORIZATION",
            "NO_PRODUCTION_OR_LONGITUDINAL_EVIDENCE",
            "STRUCTURED_SEMANTIC_PAYLOAD_ALREADY_EXPLICIT",
            "RUNTIME_PROCESS_ISOLATION_NOT_SAME_UID_FILE_ISOLATION",
            "V1_MULTI_LABEL_FULL_SOLVE_CLAIM_INVALIDATED",
            "PRESENTATION_TEXT_IS_BOUND_BUT_NOT_SEMANTICALLY_INTERPRETED",
        ],
    }
    if write_outputs:
        output_dir = ROOT / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "results.json").write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return report


def main() -> int:
    report = run_experiment(write_outputs=True)
    compact = {
        "status": report["status"],
        "core": report["summary"]["core_by_baseline"],
        "existing_solution_result": report["existing_solution_result"],
        "b6_status": report["b6_status"],
        "mutations": report["mutation_results"],
        "non_implication_gates": report["non_implication_gate_results"],
        "t5": report["t5_bypass"]["status"],
        "limitations": report["limitations"],
    }
    print(json.dumps(compact, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
