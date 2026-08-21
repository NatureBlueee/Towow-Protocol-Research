#!/usr/bin/env python3
"""Spawn-isolated candidate runner, paired worlds and adversarial mutations."""

from __future__ import annotations

import copy
import json
import multiprocessing
from pathlib import Path
from typing import Any

from authorities import (
    AuthorityNetwork,
    WITNESS_ALLOWLIST,
    WITNESS_THRESHOLD,
    verify_witness_quorum,
)
from evaluator import evaluate
from protocol import (
    EvidenceError,
    envelope_sha256,
    normalize_request,
    sha256_value,
)


ROOT = Path(__file__).resolve().parent
PUBLIC_FIXTURE = ROOT / "fixtures" / "public-requests.json"
HIDDEN_FIXTURE = ROOT / "fixtures" / "hidden-worlds.json"


class RemoteCandidateAPI:
    """Child-side RPC client. It contains a pipe, not an authority object."""

    __slots__ = ("__connection",)

    def __init__(self, connection: Any):
        self.__connection = connection

    def _call(self, operation: str, *args: Any) -> Any:
        self.__connection.send(
            {"type": "CALL", "operation": operation, "args": args}
        )
        response = self.__connection.recv()
        if response["type"] == "ERROR":
            raise RuntimeError(response["error"])
        return response["value"]

    def read_request(self) -> dict[str, Any]:
        return self._call("read_request")

    def request_holder_authorization(
        self, holder_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call("holder", holder_id, request)

    def request_attempt(
        self, request: dict[str, Any], authorizations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._call("attempt", request, authorizations)

    def request_delivery(
        self, request: dict[str, Any], attempt: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call("delivery", request, attempt)

    def request_anchor(
        self, request: dict[str, Any], delivery: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call("anchor", request, delivery)

    def request_recipient_ack(
        self,
        request: dict[str, Any],
        delivery: dict[str, Any],
        anchor: dict[str, Any],
    ) -> dict[str, Any]:
        return self._call("recipient", request, delivery, anchor)

    def request_domain_postcondition(
        self, request: dict[str, Any], ack: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call("postcondition", request, ack)

    def request_beneficiary_decision(
        self, request: dict[str, Any], postcondition: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call("beneficiary", request, postcondition)

    def verify(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._call("verify", envelope)


def _candidate_child(connection: Any, strategy_name: str) -> None:
    # Imported only inside the spawned process.  The child is never passed an
    # AuthorityNetwork, world fixture, evaluator, registry, key, or case ID.
    from strategy import bounded_reopen, bounded_reopen_relabelled

    strategies = {
        "bounded_reopen": bounded_reopen,
        "bounded_reopen_relabelled": bounded_reopen_relabelled,
    }
    try:
        output = strategies[strategy_name](RemoteCandidateAPI(connection))
        connection.send({"type": "RESULT", "value": output})
    except Exception as error:  # surfaced as harness evidence, not swallowed
        connection.send(
            {
                "type": "CANDIDATE_ERROR",
                "error": f"{type(error).__name__}:{error}",
            }
        )
    finally:
        connection.close()


def _dispatch(
    network: AuthorityNetwork, operation: str, args: tuple[Any, ...]
) -> Any:
    operations = {
        "read_request": network.read_request,
        "holder": network.holder_authorize,
        "attempt": network.controller_attempt,
        "delivery": network.controller_delivery,
        "anchor": network.anchor_commit,
        "recipient": network.recipient_ack,
        "postcondition": network.domain_postcondition,
        "beneficiary": network.beneficiary_decision,
        "verify": network.verify_for_candidate,
    }
    if operation not in operations:
        raise EvidenceError("RPC_OPERATION_NOT_ALLOWED")
    return operations[operation](*args)


def execute_candidate(
    network: AuthorityNetwork, strategy_name: str = "bounded_reopen"
) -> dict[str, Any]:
    """Run a candidate in a clean spawned process and service narrow RPCs."""

    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(
        target=_candidate_child,
        args=(child, strategy_name),
        name=f"wave007-candidate-{strategy_name}",
    )
    process.start()
    child.close()
    result: dict[str, Any] | None = None
    try:
        while True:
            message = parent.recv()
            if message["type"] == "CALL":
                try:
                    value = _dispatch(
                        network,
                        message["operation"],
                        tuple(message["args"]),
                    )
                    parent.send({"type": "VALUE", "value": value})
                except Exception as error:
                    parent.send(
                        {
                            "type": "ERROR",
                            "error": f"{type(error).__name__}:{error}",
                        }
                    )
            elif message["type"] == "RESULT":
                result = message["value"]
                break
            elif message["type"] == "CANDIDATE_ERROR":
                raise RuntimeError(message["error"])
            else:
                raise RuntimeError("candidate protocol violation")
    except EOFError as error:
        raise RuntimeError("candidate process exited without result") from error
    finally:
        parent.close()
        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    if process.exitcode != 0 or result is None:
        raise RuntimeError(f"candidate exit code {process.exitcode}")
    return result


def load_fixtures() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(PUBLIC_FIXTURE.read_text(encoding="utf-8")),
        json.loads(HIDDEN_FIXTURE.read_text(encoding="utf-8")),
    )


def baseline_request() -> dict[str, Any]:
    public, _ = load_fixtures()
    return normalize_request(public["requests"]["X7-A03"])


def run_inputs(
    public_request: dict[str, Any],
    world_truth: dict[str, Any],
    *,
    strategy_name: str = "bounded_reopen",
) -> dict[str, Any]:
    network = AuthorityNetwork(public_request, world_truth)
    if world_truth.get("preload") == "BASELINE":
        network.preload(baseline_request())
    before = network.snapshot()
    candidate = execute_candidate(network, strategy_name)
    after = network.snapshot()
    operation_log = copy.deepcopy(network.operation_log)
    registry = network.public_registry()
    evaluation = evaluate(
        public_request=public_request,
        world_truth=world_truth,
        public_registry=registry,
        candidate_output=candidate,
        operation_log=operation_log,
        before_snapshot=before,
        after_snapshot=after,
    )
    return {
        "candidate_output": candidate,
        "evaluation": evaluation,
        "operation_log": operation_log,
        "before_snapshot": before,
        "after_snapshot": after,
        "public_registry": registry,
    }


def run_case(
    opaque_case_id: str, *, strategy_name: str = "bounded_reopen"
) -> dict[str, Any]:
    public, hidden = load_fixtures()
    result = run_inputs(
        public["requests"][opaque_case_id],
        hidden["worlds"][opaque_case_id],
        strategy_name=strategy_name,
    )
    return {"opaque_case_id": opaque_case_id, **result}


def _evaluate_mutated(
    base: dict[str, Any],
    public_request: dict[str, Any],
    world_truth: dict[str, Any],
    *,
    candidate_output: dict[str, Any] | None = None,
    operation_log: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return evaluate(
        public_request=public_request,
        world_truth=world_truth,
        public_registry=base["public_registry"],
        candidate_output=(
            candidate_output
            if candidate_output is not None
            else base["candidate_output"]
        ),
        operation_log=(
            operation_log
            if operation_log is not None
            else base["operation_log"]
        ),
        before_snapshot=base["before_snapshot"],
        after_snapshot=base["after_snapshot"],
    )


def _to_anchor(
    network: AuthorityNetwork, request: dict[str, Any]
) -> dict[str, Any]:
    request = normalize_request(request)
    a1 = network.holder_authorize("LAB-SEEK", request)
    a2 = network.holder_authorize("LAB-OFFER", request)
    attempt = network.controller_attempt(request, [a1, a2])
    delivery = network.controller_delivery(request, attempt)
    return network.anchor_commit(request, delivery)


def run_attestation_attacks() -> dict[str, Any]:
    _, hidden = load_fixtures()
    world = copy.deepcopy(hidden["worlds"]["X7-A03"])
    request = baseline_request()
    network = AuthorityNetwork(request, world)
    anchor = _to_anchor(network, request)
    body = anchor["body"]
    attestations = body["witness_attestations"]
    common = {
        "public_registry": network.public_registry(),
        "allowlist": WITNESS_ALLOWLIST,
        "threshold": WITNESS_THRESHOLD,
        "checkpoint_sha256": body["checkpoint_sha256"],
        "slot": body["slot"],
        "branch_sha256": body["branch_sha256"],
    }
    valid = verify_witness_quorum(attestations, **common)
    duplicate = verify_witness_quorum(
        [attestations[0], attestations[0]], **common
    )
    replayed = verify_witness_quorum(
        [attestations[0], copy.deepcopy(attestations[0])], **common
    )

    material = copy.deepcopy(request)
    material["idempotency_key"] = "cross-checkpoint-attack"
    material["command"] = {"capacity_units": 4, "window": "E3-E7"}
    other_anchor = _to_anchor(network, material)
    cross_checkpoint = verify_witness_quorum(
        [attestations[0], other_anchor["body"]["witness_attestations"][1]],
        **common,
    )
    cross_slot_attestation = network._witness_attestation(  # noqa: SLF001
        "WITNESS-2",
        body["checkpoint_sha256"],
        "W7-DELIVERY-COMMIT-SLOT-OTHER",
        body["branch_sha256"],
    )
    cross_slot = verify_witness_quorum(
        [attestations[0], cross_slot_attestation], **common
    )
    return {
        "valid_distinct_issuers": valid,
        "duplicate_same_object": duplicate,
        "replayed_copy": replayed,
        "cross_checkpoint": cross_checkpoint,
        "cross_slot": cross_slot,
    }


def run_mutation_attacks() -> dict[str, Any]:
    public, hidden = load_fixtures()
    request = public["requests"]["X7-A03"]
    world = hidden["worlds"]["X7-A03"]
    base = run_inputs(request, world)

    deleted = copy.deepcopy(base["candidate_output"])
    del deleted["evidence"]["recipient_ack"]
    deletion_eval = _evaluate_mutated(
        base, request, world, candidate_output=deleted
    )

    duplicated_holder = copy.deepcopy(base["candidate_output"])
    duplicated_holder["evidence"]["holder_authorization_2"] = copy.deepcopy(
        duplicated_holder["evidence"]["holder_authorization_1"]
    )
    duplicated_holder_eval = _evaluate_mutated(
        base, request, world, candidate_output=duplicated_holder
    )

    replayed_ack_only = copy.deepcopy(base["candidate_output"])
    original_ack = replayed_ack_only["evidence"].pop("recipient_ack")
    replayed_ack_only["evidence"]["recipient_ack_replays"] = [
        original_ack,
        copy.deepcopy(original_ack),
    ]
    replayed_ack_eval = _evaluate_mutated(
        base, request, world, candidate_output=replayed_ack_only
    )

    unauthorized = copy.deepcopy(base["candidate_output"])
    unauthorized["evidence"]["beneficiary_acceptance"] = unauthorized[
        "evidence"
    ]["attempt"]
    unauthorized_eval = _evaluate_mutated(
        base, request, world, candidate_output=unauthorized
    )

    self_report = copy.deepcopy(base["candidate_output"])
    self_report.update(
        {
            "accepted": False,
            "false_positive": 0,
            "net_value": 9999,
            "cost": 0,
        }
    )
    self_report_eval = _evaluate_mutated(
        base, request, world, candidate_output=self_report
    )

    flipped_truth = copy.deepcopy(world)
    flipped_truth["expected_terminal"] = "REFUSE"
    truth_flip_eval = _evaluate_mutated(
        base, request, flipped_truth
    )

    renamed_case_run = run_inputs(request, world)
    relabelled_run = run_inputs(
        request, world, strategy_name="bounded_reopen_relabelled"
    )

    byte_mutations: dict[str, dict[str, Any]] = {}
    for field, value in (
        ("command", {"capacity_units": 99, "window": "E0-E8"}),
        ("purpose", "different-purpose"),
        ("idempotency_key", "different-idempotency-key"),
        ("environment_version", "sterile-sim-env-other"),
    ):
        changed = copy.deepcopy(request)
        changed[field] = value
        try:
            mutation_eval = _evaluate_mutated(
                base, changed, world
            )
            byte_mutations[field] = {
                "accepted": mutation_eval["accepted"],
                "errors": mutation_eval["errors"],
            }
        except EvidenceError as error:
            byte_mutations[field] = {
                "accepted": False,
                "errors": [error.code],
            }

    conflict_world = copy.deepcopy(world)
    conflict_world["preload"] = "BASELINE"
    conflict_world["expected_terminal"] = "REFUSE"
    conflict_world["idempotency_conflict"] = True
    same_key_changed_command = copy.deepcopy(request)
    same_key_changed_command["command"] = {
        "capacity_units": 3,
        "window": "E2-E6",
    }
    conflict_run = run_inputs(same_key_changed_command, conflict_world)

    shortened_log = copy.deepcopy(base["operation_log"][:-1])
    added_log = copy.deepcopy(base["operation_log"])
    added_log.append(
        {
            "sequence": len(added_log) + 1,
            "operation": "VERIFY_EVIDENCE",
            "authority": "MUTATION",
            "outcome": "MUTATION",
            "cache_hit": False,
            "response_bytes": 17,
            "response_sha256": None,
        }
    )
    reversed_log = list(reversed(copy.deepcopy(base["operation_log"])))
    log_costs = {
        "original": base["evaluation"]["cost"],
        "deleted_call": _evaluate_mutated(
            base, request, world, operation_log=shortened_log
        )["cost"],
        "added_call": _evaluate_mutated(
            base, request, world, operation_log=added_log
        )["cost"],
        "reordered_same_multiset": _evaluate_mutated(
            base, request, world, operation_log=reversed_log
        )["cost"],
    }

    return {
        "opaque_rename": {
            "candidate_received_no_case_id": True,
            "same_result": (
                base["evaluation"]["actual_terminal"]
                == renamed_case_run["evaluation"]["actual_terminal"]
            ),
            "same_cost": (
                base["evaluation"]["cost"]
                == renamed_case_run["evaluation"]["cost"]
            ),
        },
        "evidence_deletion": {
            "accepted_after_deletion": deletion_eval["accepted"],
            "errors": deletion_eval["errors"],
        },
        "duplicate_non_quorum_evidence": {
            "duplicate_holder_counts_as_two": duplicated_holder_eval[
                "accepted"
            ],
            "replayed_ack_substitutes_for_required_ack": replayed_ack_eval[
                "accepted"
            ],
            "duplicate_holder_errors": duplicated_holder_eval["errors"],
            "replayed_ack_errors": replayed_ack_eval["errors"],
        },
        "unauthorized_signature": {
            "accepted_after_substitution": unauthorized_eval["accepted"],
            "errors": unauthorized_eval["errors"],
        },
        "self_report_injection": {
            "accepted_recomputed": self_report_eval["accepted"],
            "net_value_recomputed": self_report_eval["net_task_value"],
            "ignored_fields": self_report_eval[
                "ignored_self_report_fields"
            ],
        },
        "truth_label_flip": {
            "candidate_output_reused_without_rerun": True,
            "base_false_positive": base["evaluation"]["false_positive"],
            "flipped_false_positive": truth_flip_eval["false_positive"],
            "base_expected": base["evaluation"]["expected_terminal"],
            "flipped_expected": truth_flip_eval["expected_terminal"],
        },
        "label_function_swap": {
            "same_terminal": (
                base["evaluation"]["actual_terminal"]
                == relabelled_run["evaluation"]["actual_terminal"]
            ),
            "same_cost": (
                base["evaluation"]["cost"]
                == relabelled_run["evaluation"]["cost"]
            ),
        },
        "bytes_binding_mutations": byte_mutations,
        "same_idempotency_changed_command": {
            "actual_terminal": conflict_run["evaluation"][
                "actual_terminal"
            ],
            "accepted": conflict_run["evaluation"]["accepted"],
            "effect_delta": conflict_run["evaluation"][
                "actual_effect_delta"
            ],
        },
        "operation_log_recompute": log_costs,
        "attestation_quorum": run_attestation_attacks(),
    }


def build_report() -> dict[str, Any]:
    public, _ = load_fixtures()
    cases = [run_case(case_id) for case_id in public["requests"]]
    evaluations = [item["evaluation"] for item in cases]
    return {
        "schema": "towow.wave007-a.results.v1",
        "shared_task_id": public["shared_task_id"],
        "shared_task_sha256": public["shared_task_sha256"],
        "scope": "G6/G7 minimum closure; no winner claim",
        "cases": [
            {
                "opaque_case_id": item["opaque_case_id"],
                "evaluation": item["evaluation"],
            }
            for item in cases
        ],
        "aggregate": {
            "case_count": len(cases),
            "accepted_count": sum(item["accepted"] for item in evaluations),
            "false_positive_count": sum(
                item["false_positive"] for item in evaluations
            ),
            "false_negative_count": sum(
                item["false_negative"] for item in evaluations
            ),
            "terminal_match_count": sum(
                item["terminal_match"] for item in evaluations
            ),
            "effect_delta_match_count": sum(
                item["effect_delta_match"] for item in evaluations
            ),
            "terminal_counts": {
                terminal: sum(
                    item["actual_terminal"] == terminal
                    for item in evaluations
                )
                for terminal in [
                    "ACCEPTED",
                    "UNKNOWN",
                    "REFUSE",
                    "ABSENT",
                ]
            },
        },
        "mutations": run_mutation_attacks(),
        "claim_status": {
            "candidate_truth_isolation": "SELF_TEST_ONLY",
            "authority_signature_chain": "SELF_TEST_ONLY",
            "idempotent_exact_replay": "SELF_TEST_ONLY",
            "material_drift_reauthorization": "SELF_TEST_ONLY",
            "unique_issuer_anchor_quorum": "SELF_TEST_ONLY",
            "independent_audit": "NOT_YET_RUN_BY_ROOT",
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
