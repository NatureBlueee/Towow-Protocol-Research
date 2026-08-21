#!/usr/bin/env python3
"""Wave 007-A2 runner and repair-specific attacks."""

from __future__ import annotations

import copy
import json
import multiprocessing
import subprocess
import sys
from pathlib import Path
from typing import Any

from authorities import (
    AuthorityNetwork,
    WITNESS_ALLOWLIST,
    WITNESS_THRESHOLD,
    verify_witness_quorum,
)
from evaluator import evaluate
from protocol import EvidenceError, normalize_request


ROOT = Path(__file__).resolve().parent
ROUND = ROOT.parents[1]
V1_DIR = ROOT.parent / "wave-007-a-opaque-authority-harness"
PUBLIC_FIXTURE = V1_DIR / "fixtures" / "public-requests.json"
HIDDEN_FIXTURE = V1_DIR / "fixtures" / "hidden-worlds.json"
ROOT_ATTACK = ROUND / "audits" / "wave-007" / "root_attack_a.py"


class RemoteCandidateAPI:
    """Child-side facade. It protects parent memory, not readable files."""

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
    from strategy import bounded_reopen, bounded_reopen_relabelled

    strategies = {
        "bounded_reopen": bounded_reopen,
        "bounded_reopen_relabelled": bounded_reopen_relabelled,
    }
    try:
        value = strategies[strategy_name](RemoteCandidateAPI(connection))
        connection.send({"type": "RESULT", "value": value})
    except Exception as error:
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
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(
        target=_candidate_child,
        args=(child, strategy_name),
        name=f"wave007-a2-candidate-{strategy_name}",
    )
    process.start()
    child.close()
    result: dict[str, Any] | None = None
    try:
        while True:
            message = parent.recv()
            if message["type"] == "CALL":
                try:
                    parent.send(
                        {
                            "type": "VALUE",
                            "value": _dispatch(
                                network,
                                message["operation"],
                                tuple(message["args"]),
                            ),
                        }
                    )
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
        raise RuntimeError("candidate exited without result") from error
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


def _evaluate_network_run(
    network: AuthorityNetwork,
    public_request: dict[str, Any],
    world_truth: dict[str, Any],
    before: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
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
    return _evaluate_network_run(
        network, public_request, world_truth, before, candidate
    )


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


def _progress_baseline(
    network: AuthorityNetwork,
    request: dict[str, Any],
    stop_after: str,
) -> None:
    a1 = network.holder_authorize("LAB-SEEK", request)
    a2 = network.holder_authorize("LAB-OFFER", request)
    attempt = network.controller_attempt(request, [a1, a2])
    if stop_after == "L1_ATTEMPT":
        return
    delivery = network.controller_delivery(request, attempt)
    if stop_after == "L2_DELIVERY":
        return
    anchor = network.anchor_commit(request, delivery)
    ack = network.recipient_ack(request, delivery, anchor)
    postcondition = network.domain_postcondition(request, ack)
    if stop_after == "L3_POSTCONDITION":
        return
    network.beneficiary_decision(request, postcondition)


def run_partial_then_changed_matrix() -> dict[str, Any]:
    public, hidden = load_fixtures()
    baseline = normalize_request(public["requests"]["X7-C73"])
    changed = copy.deepcopy(baseline)
    changed["command"] = {"capacity_units": 9, "window": "E0-E8"}
    results: dict[str, Any] = {}
    for stop_after in (
        "L1_ATTEMPT",
        "L2_DELIVERY",
        "L3_POSTCONDITION",
        "L4_BENEFICIARY_REFUSE",
    ):
        world = copy.deepcopy(hidden["worlds"]["X7-C73"])
        if stop_after != "L4_BENEFICIARY_REFUSE":
            world["beneficiary"] = "ACCEPT"
        world["preload"] = "NONE"
        world["idempotency_conflict"] = True
        world["expected_terminal"] = "REFUSE"
        network = AuthorityNetwork(changed, world)
        _progress_baseline(network, baseline, stop_after)
        network.operation_log.clear()
        before = network.snapshot()
        candidate = execute_candidate(network)
        result = _evaluate_network_run(
            network, changed, world, before, candidate
        )
        operations = result["operation_log"]
        results[stop_after] = {
            "actual_terminal": result["evaluation"]["actual_terminal"],
            "terminal_match": result["evaluation"]["terminal_match"],
            "controller_refused_at_attempt": any(
                row["operation"] == "REQUEST_EFFECT_ATTEMPT"
                and row["outcome"] == "REFUSE"
                for row in operations
            ),
            "new_delivery_called": any(
                row["operation"] == "REQUEST_DELIVERY"
                for row in operations
            ),
            "new_domain_postcondition_called": any(
                row["operation"] == "REQUEST_DOMAIN_POSTCONDITION"
                for row in operations
            ),
            "attempt_binding_delta": result["evaluation"][
                "actual_attempt_binding_delta"
            ],
            "l3_delta": result["evaluation"][
                "actual_l3_domain_postcondition_delta"
            ],
            "l4_delta": result["evaluation"][
                "actual_l4_beneficiary_acceptance_delta"
            ],
            "all_level_deltas_match": result["evaluation"][
                "all_level_deltas_match"
            ],
            "operations": [
                row["operation"] for row in operations
            ],
        }
    return results


def run_quorum_attacks() -> dict[str, bool]:
    _, hidden = load_fixtures()
    request = baseline_request()
    network = AuthorityNetwork(
        request, copy.deepcopy(hidden["worlds"]["X7-A03"])
    )
    a1 = network.holder_authorize("LAB-SEEK", request)
    a2 = network.holder_authorize("LAB-OFFER", request)
    attempt = network.controller_attempt(request, [a1, a2])
    delivery = network.controller_delivery(request, attempt)
    anchor = network.anchor_commit(request, delivery)
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
    material = copy.deepcopy(request)
    material["idempotency_key"] = "a2-cross-checkpoint"
    material["command"] = {"capacity_units": 4, "window": "E3-E7"}
    m1 = network.holder_authorize("LAB-SEEK", material)
    m2 = network.holder_authorize("LAB-OFFER", material)
    material_attempt = network.controller_attempt(material, [m1, m2])
    material_delivery = network.controller_delivery(
        material, material_attempt
    )
    material_anchor = network.anchor_commit(
        material, material_delivery
    )
    cross_slot_attestation = network._witness_attestation(  # noqa: SLF001
        "WITNESS-2",
        body["checkpoint_sha256"],
        "W7-A2-OTHER-SLOT",
        body["branch_sha256"],
    )
    return {
        "valid_distinct": verify_witness_quorum(
            attestations, **common
        )["quorum"],
        "duplicate": verify_witness_quorum(
            [attestations[0], attestations[0]], **common
        )["quorum"],
        "replay": verify_witness_quorum(
            [attestations[0], copy.deepcopy(attestations[0])],
            **common,
        )["quorum"],
        "cross_checkpoint": verify_witness_quorum(
            [
                attestations[0],
                material_anchor["body"]["witness_attestations"][1],
            ],
            **common,
        )["quorum"],
        "cross_slot": verify_witness_quorum(
            [attestations[0], cross_slot_attestation],
            **common,
        )["quorum"],
    }


def filesystem_peer_observation() -> dict[str, Any]:
    code = (
        "from pathlib import Path; "
        f"p=Path({str(HIDDEN_FIXTURE)!r}); "
        "s=p.read_text(); "
        "print('1' if 'expected_terminal' in s else '0')"
    )
    output = subprocess.check_output(
        [sys.executable, "-c", code], text=True
    ).strip()
    return {
        "same_os_permission_peer_can_read_hidden_fixture": output == "1",
        "filesystem_truth_isolation_claim": "REFUTED_NOT_CLAIMED",
        "spawn_claim": (
            "PARENT_MEMORY_KEYS_AND_LOG_NOT_PASSED_TO_FIXED_CANDIDATE"
        ),
        "fixed_candidate_source_truth_read": "NOT_OBSERVED_BY_SOURCE_AUDIT",
    }


def build_report() -> dict[str, Any]:
    public, _ = load_fixtures()
    cases = [run_case(case_id) for case_id in public["requests"]]
    evaluations = [case["evaluation"] for case in cases]
    c73 = next(
        case["evaluation"]
        for case in cases
        if case["opaque_case_id"] == "X7-C73"
    )
    matrix = run_partial_then_changed_matrix()
    return {
        "schema": "towow.wave007-a2.results.v1",
        "scope": "A v1 repair; same-researcher self-test",
        "root_attack_sha256": (
            "1e99f17136f4868de724d13c52cb7018c48dc880b18c2cce35ce8ee5d8b9a72f"
        ),
        "cases": [
            {
                "opaque_case_id": case["opaque_case_id"],
                "evaluation": case["evaluation"],
            }
            for case in cases
        ],
        "aggregate": {
            "case_count": len(cases),
            "terminal_match_count": sum(
                item["terminal_match"] for item in evaluations
            ),
            "attempt_binding_delta_match_count": sum(
                item["attempt_binding_delta_match"]
                for item in evaluations
            ),
            "l3_delta_match_count": sum(
                item["l3_domain_postcondition_delta_match"]
                for item in evaluations
            ),
            "l4_delta_match_count": sum(
                item["l4_beneficiary_acceptance_delta_match"]
                for item in evaluations
            ),
            "false_positive_count": sum(
                item["false_positive"] for item in evaluations
            ),
            "false_negative_count": sum(
                item["false_negative"] for item in evaluations
            ),
        },
        "root_attack_reproduction_and_repair": matrix[
            "L4_BENEFICIARY_REFUSE"
        ],
        "partial_then_changed_matrix": matrix,
        "l3_l4_separation_beneficiary_refuse": {
            "actual_terminal": c73["actual_terminal"],
            "l3_domain_postcondition_delta": c73[
                "actual_l3_domain_postcondition_delta"
            ],
            "l4_beneficiary_acceptance_delta": c73[
                "actual_l4_beneficiary_acceptance_delta"
            ],
        },
        "quorum_verifier_conditions": run_quorum_attacks(),
        "truth_isolation_scope": filesystem_peer_observation(),
        "anchor_scope": {
            "equivocation_fixture": (
                "CENTRAL_HIDDEN_STATE_DETECTOR_FIXTURE_ONLY"
            ),
            "malicious_anchor_self_proof": "NOT_CLAIMED",
            "retained_claim": (
                "UNIQUE_ALLOWLISTED_ISSUERS_BOUND_TO_CHECKPOINT_SLOT_BRANCH"
            ),
        },
        "claim_status": {
            "a_v1": "INVALIDATED_BY_ROOT_ATTACK",
            "a2_repair": "SAME_RESEARCHER_SELF_TEST_ONLY",
            "independent_a2_audit": "NOT_YET_RUN_BY_ROOT",
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, indent=2))
