from __future__ import annotations

import copy
import re
from typing import Any

from .canonical import sha256
from .models import RunRecord


class FormationScorer:
    """Scorer-only verification of closure, receipts and complete task value."""

    def __init__(
        self, case_truth: dict[str, Any], semantic_case_id: str
    ) -> None:
        self.__truth = copy.deepcopy(case_truth)
        self.semantic_case_id = semantic_case_id
        self.__current_anchors = self._truth_anchors()

    def score(
        self,
        public_case: dict[str, Any],
        run: RunRecord,
        counterfactuals: list[RunRecord] | None = None,
    ) -> dict[str, Any]:
        counterfactuals = counterfactuals or []
        c_value = self._old_full_policy_closure(public_case)
        task_same = sha256(run.frozen_s0["task"]) == sha256(run.result_task)
        credential_valid = self._s0_credential_valid(public_case, run)
        trace_valid = self._trace_valid(run, task_same, credential_valid)
        value_valid = self._full_value(run)
        if run.final_state.get("effect") is not None and not value_valid:
            trace_valid = False
        full_value = value_valid and trace_valid
        token_formed = any(
            item["type"] == "PURPOSE_TOKEN_DELEGATION_FORMED"
            for item in run.trace
        )
        extant_token_used = any(
            item["type"] == "EXTANT_PURPOSE_TOKEN_DELEGATION_USED"
            for item in run.trace
        )
        kernel_changed = any(
            item["type"] == "KERNEL_EXTENSION_INSTALLED" for item in run.trace
        )
        direct = self._direct_path_exists()
        physical = self._physical_reachability(public_case)
        measurable = self._measurable_reachability(public_case, c_value)

        if not task_same:
            n_value = "UNKNOWN"
        elif token_formed:
            n_value = "NEW_TOKEN"
        elif direct:
            n_value = "NONE"
        elif extant_token_used:
            n_value = "EXTANT_ACTIVATED"
        elif full_value:
            n_value = "NONE"
        elif public_case["inventory"]["status"] != "COMPLETE":
            n_value = "UNKNOWN"
        else:
            n_value = "NONE"

        counterfactual_receipts = []
        for item in counterfactuals:
            exact_s0 = (
                item.frozen_s0_sha256 == run.frozen_s0_sha256
                and item.frozen_s0 == run.frozen_s0
                and self._s0_credential_valid(public_case, item)
            )
            removed = item.intervention_delta.get("removed_actions", [])
            final_registry = item.final_state.get(
                "executable_operator_registry", []
            )
            matching_operator_ids = [
                operator.get("operator_id")
                for operator in final_registry
                if operator.get("executable")
                and operator.get("action_kind")
                == "FORM_PURPOSE_TOKEN_AND_DELEGATION"
            ]
            counterfactual_receipts.append(
                {
                    "intervention": item.intervention,
                    "intervention_delta": copy.deepcopy(
                        item.intervention_delta
                    ),
                    "s0_sha256": item.frozen_s0_sha256,
                    "exact_s0_replay": exact_s0,
                    "frozen_coordinate_observed": self._full_value(item),
                    "formation_action_actually_removed": (
                        item.intervention
                        == "REMOVE_FORMATION_OPERATOR"
                        and "REQUEST_PURPOSE_DELEGATION" in removed
                        and "REQUEST_PURPOSE_DELEGATION"
                        not in item.final_state.get("executable_kernel", [])
                    ),
                    "closed_registry_observation": {
                        "frozen_registry_sha256": sha256(
                            item.frozen_s0["operator_registry"]
                        ),
                        "executable_registry_sha256": sha256(
                            final_registry
                        ),
                        "matching_action_operator_ids": (
                            matching_operator_ids
                        ),
                        "proposal_count": sum(
                            event["type"]
                            == "FORMATION_PROPOSAL_CREATED"
                            for event in item.trace
                        ),
                        "sign_request_count": sum(
                            event["type"] == "OWNER_INTERACTION"
                            and event["event"].get("phase") == "sign"
                            for event in item.trace
                        ),
                        "token_formed_count": sum(
                            event["type"]
                            == "PURPOSE_TOKEN_DELEGATION_FORMED"
                            for event in item.trace
                        ),
                        "target_submit_count": sum(
                            event["type"] == "TARGET_SUBMIT"
                            for event in item.trace
                        ),
                        "intervention_delta_sha256": sha256(
                            item.intervention_delta
                        ),
                    },
                    "trace_sha256": sha256(item.trace),
                }
            )
        removal = next(
            (
                item
                for item in counterfactual_receipts
                if item["intervention"] == "REMOVE_FORMATION_OPERATOR"
            ),
            None,
        )

        post_revoke_trace = (
            full_value
            and any(
                event["type"] == "RESERVATION_REVOKED"
                for event in run.trace
            )
            and any(
                event["type"] == "RECOVERY_REDISCOVERY_QUERY"
                for event in run.trace
            )
            and any(
                event["type"] == "OWNER_INTERACTION"
                and event["event"].get("phase") == "rediscover"
                for event in run.trace
            )
        )
        robust_denominator = {
            "status": "UNKNOWN_UNFROZEN_COMPLETE_RESPONSE_TREE",
            "scripted_response_family_sha256": run.frozen_s0[
                "response_family_sha256"
            ],
            "scripted_response_family_status": run.frozen_s0[
                "response_family_status"
            ],
            "allowed_branch_population": None,
            "allowed_branch_population_sha256": None,
            "coverage_proof": None,
            "counterfactuals_are_not_robust_denominator": True,
        }
        body = {
            "case_handle": public_case["case_handle"],
            "episode_handle": public_case["episode_handle"],
            "C": c_value,
            "N": n_value,
            "E": "CHANGED" if kernel_changed else "SAME",
            "T": "INVARIANT" if task_same else "CONTROLLER_SUBSTITUTION",
            "V": "VALID" if trace_valid else "INVALID",
            "path_class": self._path_class(
                direct, c_value, token_formed, kernel_changed, task_same
            ),
            "reachability": {
                "physical": physical,
                "measurable": measurable,
                "actual": "TRUE" if full_value else "FALSE",
                "robust": "UNKNOWN",
                "robust_summary_semantics": (
                    "ALIAS_OF_R_BRANCH_ROBUST_NOT_A_REPLACEMENT_FOR_R_VECTOR"
                ),
            },
            "R": {
                "R_physical_exists": physical,
                "R_measurable_exists": measurable,
                "R_actual": "TRUE" if full_value else "FALSE",
                "R_branch_robust": "UNKNOWN",
                "R_safety_robust": "UNKNOWN",
                "R_terminal_robust": "UNKNOWN",
            },
            "robust_denominator": robust_denominator,
            "bounded_reachability_witness": {
                "frozen_coordinate_observed": full_value,
                "trace_binding_valid": trace_valid,
                "target_readback_observed": (
                    run.final_state.get("effect") is not None
                ),
                "terminal_observation": next(
                    (
                        item.get(
                            "reason",
                            "TARGET_READBACK_OBSERVED"
                            if item["type"] == "EFFECT_READBACK_OBSERVED"
                            else item["type"],
                        )
                        for item in reversed(run.trace)
                        if item["type"]
                        in {"BOUNDED_STOP", "EFFECT_READBACK_OBSERVED"}
                    ),
                    "NO_TERMINAL_OBSERVATION",
                ),
            },
            "post_revoke_observation": self._post_revoke_observation(
                run, post_revoke_trace
            ),
            "intervention_trace": {
                "runs": counterfactual_receipts,
                "removal_blocks_bounded_witness": (
                    removal is not None
                    and removal["exact_s0_replay"]
                    and removal["formation_action_actually_removed"]
                    and not removal["frozen_coordinate_observed"]
                ),
            },
            "bindings": {
                "frozen_s0_sha256": run.frozen_s0_sha256,
                "frozen_task_sha256": sha256(run.frozen_s0["task"]),
                "result_task_sha256": sha256(run.result_task),
                "response_family_sha256": run.frozen_s0[
                    "response_family_sha256"
                ],
                "trace_sha256": sha256(run.trace),
            },
        }
        return {"body": body, "body_sha256": sha256(body)}

    def _truth_anchors(self) -> dict[str, Any]:
        owner_ids = {"O_Q", "O_V", "O_R", "O_S", "O_E"}
        for phase in self.__truth["owner_events"].values():
            values = phase.values() if isinstance(phase, dict) else []
            for value in values:
                if isinstance(value, dict) and value.get("owner_id"):
                    owner_ids.add(value["owner_id"])
        default_head = f'HEAD-{sha256(self.__truth["owner_events"])[:16]}'
        heads = {
            owner_id: self.__truth.get("owner_policy_heads", {}).get(
                owner_id, default_head
            )
            for owner_id in sorted(owner_ids)
        }
        routing: dict[str, str] = {}
        for phase, phase_truth in self.__truth["owner_events"].items():
            if isinstance(phase_truth, dict) and phase_truth.get("owner_id"):
                routing[phase] = phase_truth["owner_id"]
            elif isinstance(phase_truth, dict):
                for resource_id, value in phase_truth.items():
                    if isinstance(value, dict) and value.get("owner_id"):
                        routing[f"{phase}:{resource_id}"] = value["owner_id"]
        return {
            "owner_routing": routing,
            "owner_state_versions": {
                owner_id: self.__truth.get("owner_state_versions", {}).get(
                    owner_id, f"STATE-{owner_id}-v1"
                )
                for owner_id in sorted(owner_ids)
            },
            "owner_policy_versions": {
                owner_id: self.__truth.get("owner_policy_versions", {}).get(
                    owner_id, f"POLICY-{owner_id}-v1"
                )
                for owner_id in sorted(owner_ids)
            },
            "owner_policy_heads": heads,
            "response_family_sha256": sha256(
                {
                    "owner_events": self.__truth["owner_events"],
                    "target_readback": self.__truth["target_readback"],
                    "acceptance": self.__truth.get("acceptance", {}),
                }
            ),
            "response_family_status": "SCRIPTED_OBSERVED_FAMILY_NOT_COMPLETE",
            "budget": copy.deepcopy(
                self.__truth.get(
                    "budget",
                    {"max_cost_units": 20, "max_owner_queries": 12},
                )
            ),
            "horizon": copy.deepcopy(
                self.__truth.get(
                    "horizon",
                    {"deadline_min": 90, "max_steps": 40},
                )
            ),
            "clock_seed": self.__truth.get("clock_seed", "CE001-CLOCK-SEED-1"),
        }

    def _s0_credential_valid(
        self, public_case: dict[str, Any], run: RunRecord
    ) -> bool:
        frozen = run.frozen_s0
        return (
            sha256(frozen) == run.frozen_s0_sha256
            and frozen["owner_routing"]
            == self.__current_anchors["owner_routing"]
            and frozen["owner_policy_heads"]
            == self.__current_anchors["owner_policy_heads"]
            and frozen["owner_state_versions"]
            == self.__current_anchors["owner_state_versions"]
            and frozen["owner_policy_versions"]
            == self.__current_anchors["owner_policy_versions"]
            and frozen["response_family_sha256"]
            == self.__current_anchors["response_family_sha256"]
            and frozen["response_family_status"]
            == self.__current_anchors["response_family_status"]
            and frozen["budget"] == self.__current_anchors["budget"]
            and frozen["horizon"] == self.__current_anchors["horizon"]
            and frozen["clock_seed"] == self.__current_anchors["clock_seed"]
            and frozen["public_packet_sha256"] == sha256(public_case)
        )

    def _trace_valid(
        self, run: RunRecord, task_same: bool, credential_valid: bool
    ) -> bool:
        if not task_same or not credential_valid:
            return False
        proposal_events = {
            item["proposal_sha256"]: item["proposal"]
            for item in run.trace
            if item["type"] == "FORMATION_PROPOSAL_CREATED"
        }
        for item in run.trace:
            if item["type"] != "PURPOSE_TOKEN_DELEGATION_FORMED":
                continue
            proposal_hash = item["purpose_token"].get("proposal_sha256")
            proposal = proposal_events.get(proposal_hash)
            if proposal is None or sha256(proposal) != proposal_hash:
                return False
            sign_events = [
                event["event"]
                for event in run.trace
                if event["type"] == "OWNER_INTERACTION"
                and event["event"].get("phase") == "sign"
                and event["event"].get("proposal_sha256") == proposal_hash
            ]
            if len(sign_events) != 1:
                return False
            if not self._formation_receipt_valid(
                run, proposal, sign_events[0], item
            ):
                return False
        return True

    def _formation_receipt_valid(
        self,
        run: RunRecord,
        proposal: dict[str, Any],
        sign_event: dict[str, Any],
        formed_event: dict[str, Any],
    ) -> bool:
        task = run.frozen_s0["task"]
        target = task["target"]
        exact_scope = {
            "venue_id": target["venue_id"],
            "circuit_id": target["circuit_id"],
            "power_kw": task["power_kw"],
            "power_tolerance_percent": task["power_tolerance_percent"],
            "minimum_duration_min": task["minimum_duration_min"],
            "constraints": task["constraints"],
        }
        receipt = sign_event.get("owner_receipt", {})
        receipt_copy = copy.deepcopy(receipt)
        claimed_receipt_hash = receipt_copy.pop("receipt_sha256", None)
        token = formed_event["purpose_token"]
        delegation = formed_event["delegation"]
        current_head = self.__current_anchors["owner_policy_heads"]["O_V"]
        return all(
            [
                proposal.get("task_sha256") == sha256(task),
                proposal.get("q_version") == task["q_version"],
                proposal.get("resource_id") == formed_event["resource_id"],
                proposal.get("purpose")
                == f'temporary-power-{target["circuit_id"]}',
                proposal.get("scope") == exact_scope,
                proposal.get("expiry") == task["deadline"],
                proposal.get("recipient_owner_id") == "O_V",
                sign_event.get("proposal") == proposal,
                sign_event.get("proposal_sha256") == sha256(proposal),
                proposal.get("cost", {}).get("units", 10**9)
                <= run.frozen_s0["budget"]["max_cost_units"],
                bool(proposal.get("nonce")),
                sign_event.get("owner_id") == "O_V",
                receipt.get("signer_owner_id") == "O_V",
                receipt.get("decision") in {"SIGNED", "APPROVED"},
                receipt.get("proposal_sha256") == sha256(proposal),
                receipt.get("owner_policy_head") == current_head,
                receipt.get("owner_policy_head")
                == run.frozen_s0["owner_policy_heads"]["O_V"],
                claimed_receipt_hash == sha256(receipt_copy),
                token.get("proposal_sha256") == sha256(proposal),
                token.get("resource_id") == proposal["resource_id"],
                token.get("q_version") == task["q_version"],
                token.get("purpose") == proposal["purpose"],
                delegation.get("proposal_sha256") == sha256(proposal),
                delegation.get("resource_id") == proposal["resource_id"],
                delegation.get("q_version") == task["q_version"],
                delegation.get("scope") == exact_scope,
                delegation.get("expiry") == task["deadline"],
            ]
        )

    def _full_value(self, run: RunRecord) -> bool:
        task = run.frozen_s0["task"]
        effect = run.final_state.get("effect")
        if not self._effect_matches_task(effect, task):
            return False
        readback_copy = copy.deepcopy(effect)
        claimed_readback_hash = readback_copy.pop("readback_sha256", None)
        if claimed_readback_hash != sha256(readback_copy):
            return False
        submits = [
            item
            for item in run.trace
            if item["type"] == "TARGET_SUBMIT"
            and item["resource_id"] == effect["resource_id"]
            and item["operation_id"] == effect.get("operation_id")
            and item["submitted_at_min"] <= effect["timestamp_min"]
        ]
        if not submits:
            return False
        operation_id = effect["operation_id"]
        required_owners = {"O_Q", "O_V"}
        acceptances = run.final_state.get("acceptances", [])
        if {item.get("owner_id") for item in acceptances} != required_owners:
            return False
        for acceptance in acceptances:
            body = copy.deepcopy(acceptance)
            claimed = body.pop("acceptance_sha256", None)
            owner_id = acceptance["owner_id"]
            if not all(
                [
                    claimed == sha256(body),
                    acceptance.get("decision") == "ACCEPT",
                    acceptance.get("q_version") == task["q_version"],
                    acceptance.get("task_sha256") == sha256(task),
                    acceptance.get("effect_readback_sha256")
                    == effect["readback_sha256"],
                    acceptance.get("operation_id") == operation_id,
                    acceptance.get("owner_policy_head")
                    == run.frozen_s0["owner_policy_heads"][owner_id],
                    acceptance.get("owner_policy_head")
                    == self.__current_anchors["owner_policy_heads"][owner_id],
                ]
            ):
                return False
        return True

    @staticmethod
    def _effect_matches_task(
        effect: dict[str, Any] | None, task: dict[str, Any]
    ) -> bool:
        if not effect or not effect.get("effect_occurred"):
            return False
        target = task["target"]
        tolerance = task["power_kw"] * task["power_tolerance_percent"] / 100
        constraints = effect.get("constraints", {})
        deadline_match = re.fullmatch(r"T0\+(\d+)min", task["deadline"])
        if deadline_match is None:
            return False
        deadline_min = int(deadline_match.group(1))
        return all(
            [
                effect.get("venue_id") == target["venue_id"],
                effect.get("circuit_id") == target["circuit_id"],
                effect.get("q_version") == task["q_version"],
                abs(effect.get("power_kw", -10**9) - task["power_kw"])
                <= tolerance,
                effect.get("duration_min", 0) >= task["minimum_duration_min"],
                effect.get("timestamp_min", 10**9) <= deadline_min,
                constraints.get("noise_compliant") is True,
                constraints.get("safety_compliant") is True,
                constraints.get("exact_target") is True,
                constraints.get("other_circuits_energized") == [],
                bool(effect.get("operation_id")),
                bool(effect.get("resource_id")),
            ]
        )

    def _old_full_policy_closure(self, public_case: dict[str, Any]) -> str:
        if public_case["inventory"]["status"] != "COMPLETE":
            return "UNKNOWN"
        read = self.__truth["owner_events"]["read"]
        if read.get("decision") != "DISCLOSED":
            return "UNSAT"
        resources = list(read.get("resources", []))
        rediscover = self.__truth["owner_events"].get("rediscover", {})
        if rediscover.get("decision") == "DISCLOSED":
            resources.extend(rediscover.get("resources", []))
        initial = self.__truth["initial_state"]
        initial_ops = set(initial.get("installed_operators", []))
        for resource in resources:
            resource_id = resource["resource_id"]
            if resource.get("requires_adapter") not in {None, *initial_ops}:
                continue
            if resource.get("requires_token"):
                extant_token = any(
                    item.get("resource_id") == resource_id
                    for item in initial.get("purpose_tokens", [])
                )
                extant_delegation = any(
                    item.get("resource_id") == resource_id
                    for item in initial.get("delegations", [])
                )
                sign = self.__truth["owner_events"]["sign"].get(resource_id, {})
                if not (
                    (extant_token and extant_delegation)
                    or (sign.get("purpose_token") and sign.get("delegation"))
                ):
                    continue
            reserve = self.__truth["owner_events"]["reserve"].get(resource_id, {})
            if reserve.get("decision") != "RESERVED":
                continue
            execute = self.__truth["owner_events"]["execute"].get(resource_id, {})
            if execute.get("decision") == "EXECUTE":
                return "SAT"
        return "UNSAT"

    def _direct_path_exists(self) -> bool:
        read = self.__truth["owner_events"]["read"]
        return any(
            resource.get("direct_qualified") is True
            for resource in read.get("resources", [])
        )

    def _physical_reachability(self, public_case: dict[str, Any]) -> str:
        if public_case["inventory"]["status"] != "COMPLETE":
            return "UNKNOWN"
        return "TRUE" if self.__truth.get("physical_solution_exists") else "FALSE"

    def _measurable_reachability(
        self, public_case: dict[str, Any], old_closure: str
    ) -> str:
        if public_case["inventory"]["status"] != "COMPLETE":
            return "UNKNOWN"
        if old_closure == "SAT" or self._extension_policy_exists():
            return "TRUE"
        return "FALSE"

    def _extension_policy_exists(self) -> bool:
        resources = list(
            self.__truth["owner_events"]["read"].get("resources", [])
        )
        rediscover = self.__truth["owner_events"].get("rediscover", {})
        resources.extend(rediscover.get("resources", []))
        for resource in resources:
            resource_id = resource["resource_id"]
            sign = self.__truth["owner_events"]["sign"].get(resource_id, {})
            if resource.get("requires_adapter") and not sign.get("kernel_extension"):
                continue
            if resource.get("requires_token") and not (
                sign.get("purpose_token") and sign.get("delegation")
            ):
                continue
            reserve = self.__truth["owner_events"]["reserve"].get(resource_id, {})
            execute = self.__truth["owner_events"]["execute"].get(resource_id, {})
            if (
                reserve.get("decision") == "RESERVED"
                and execute.get("decision") == "EXECUTE"
            ):
                return True
        return False

    @staticmethod
    def _post_revoke_observation(
        run: RunRecord, trace_complete: bool
    ) -> dict[str, Any]:
        readback = run.final_state.get("effect") or {}
        constraints = readback.get("constraints", {})
        owner_observations = run.final_state.get("acceptances", [])
        operation_ids = [
            item.get("operation_id")
            for item in run.trace
            if item["type"] == "TARGET_SUBMIT"
        ]
        return {
            "revocation_observed": any(
                item["type"] == "RESERVATION_REVOKED"
                for item in run.trace
            ),
            "post_revoke_rediscovery_observed": any(
                item["type"] == "RECOVERY_REDISCOVERY_QUERY"
                for item in run.trace
            ),
            "alternative_resource_id": run.final_state.get(
                "selected_resource"
            ),
            "operation_ids_observed": operation_ids,
            "readback_operation_id": readback.get("operation_id"),
            "readback_timestamp_min": readback.get("timestamp_min"),
            "deadline": run.frozen_s0["task"].get("deadline"),
            "safety_observation": {
                "noise_compliant": constraints.get("noise_compliant"),
                "safety_compliant": constraints.get("safety_compliant"),
                "other_circuits_energized": constraints.get(
                    "other_circuits_energized"
                ),
            },
            "owner_outcome_response_owners": sorted(
                item.get("owner_id") for item in owner_observations
            ),
            "trace_complete_for_frozen_coordinates": trace_complete,
            "future_contract_evaluator_required": True,
        }

    @staticmethod
    def _path_class(
        direct: bool,
        c_value: str,
        token_formed: bool,
        kernel_changed: bool,
        task_same: bool,
    ) -> str:
        if not task_same:
            return "TASK_CHANGE"
        if direct:
            return "DIRECT_PATH"
        if kernel_changed:
            return "MODEL_KERNEL_CHANGE"
        if token_formed:
            return "OLD_FULL_POLICY_NEW_TOKEN"
        if c_value == "SAT":
            return "OLD_FULL_POLICY_CLOSURE"
        if c_value == "UNKNOWN":
            return "OPEN_INVENTORY_UNKNOWN"
        return "BOUNDED_UNREACHABLE"
