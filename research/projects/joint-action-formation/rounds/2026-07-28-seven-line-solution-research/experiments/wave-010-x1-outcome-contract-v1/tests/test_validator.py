from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("x1_v1_validator", ROOT / "validator.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def receipt(label: str, owner: str = "owner") -> dict[str, str]:
    return {
        "ref": f"receipt:{label}",
        "raw_bytes_sha256": digest(f"raw:{label}"),
        "owner_key_id": owner,
        "receipt_version": "1",
        "status": "FINAL",
    }


def base_body() -> dict:
    task_hash = digest("original-task")
    return {
        "C": "SAT",
        "N": "NONE",
        "E": "SAME",
        "T": "INVARIANT",
        "V": "VALID",
        "R": {
            "R_physical_exists": "TRUE",
            "R_measurable_exists": "TRUE",
            "R_actual": "TRUE",
            "R_effect_robust": "UNKNOWN",
            "R_safe_robust": "TRUE",
            "R_terminal_robust": "TRUE",
        },
        "inventory_completeness": {
            "action_inventory": "COMPLETE",
            "response_family": "COMPLETE",
            "observation_kernel": "COMPLETE",
            "transition_semantics": "COMPLETE",
            "search_bound_frozen": True,
            "horizon": 12,
            "unresolved_items": [],
            "evidence_sha256": digest("inventory"),
        },
        "counterfactual": {
            "status": "NOT_APPLICABLE",
            "operator_ids": [],
            "remove_result": "NOT_APPLICABLE",
            "reverse_result": "NOT_APPLICABLE",
            "block_result": "NOT_APPLICABLE",
            "evidence_sha256": digest("counterfactual"),
        },
        "task_diff": {
            "classification": "UNCHANGED",
            "original_task_sha256": task_hash,
            "result_task_sha256": task_hash,
            "material_fields": [],
            "changes": [],
            "owner_authorization_receipts": [],
            "controller_claim_refs": [],
        },
    }


def make_instance(
    contract: dict,
    category: str,
    reason: str,
    body: dict,
) -> dict:
    g3_ref = receipt("G3", "g3-truth-owner")
    line_refs = {key: receipt(key) for key in ["G1", "G2", "G5"]}
    line_refs["G3"] = g3_ref
    transition_refs = {
        key: receipt(key)
        for key in ["T_G1_TO_G2", "T_G2_TO_G3", "T_G3_TO_G5", "T_G5_TO_X2"]
    }
    return {
        "schema_version": "1",
        "schema_sha256": contract["hash_binding_rules"]["schema_sha256"][
            "current_preimage_sha256"
        ],
        "reason_registry_version": "x1-reason-registry-v2",
        "reason_registry_sha256": contract["hash_binding_rules"][
            "reason_registry_sha256"
        ]["current_preimage_sha256"],
        "x1_run_id": "synthetic-conformance-only",
        "x1_world_id": "synthetic-world",
        "x1_arm_id": "synthetic-arm",
        "raw_method_return_bytes_sha256": digest("method-return"),
        "category": category,
        "reason_code": reason,
        "line_receipt_refs": line_refs,
        "transition_receipt_refs": transition_refs,
        "g3_receipt": {
            "receipt_ref": copy.deepcopy(g3_ref),
            "body_sha256": validator.canonical_sha256(body),
            "body": body,
        },
    }


class OutcomeContractV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v0 = validator.load_json(validator.V0_PATH)
        cls.contract = validator.build_v1_contract(cls.v0)

    def assert_invalid(self, instance: dict) -> None:
        with self.assertRaises(validator.ValidationError):
            validator.validate_instance(self.contract, instance)

    def test_contract_is_candidate_and_v0_is_bound_but_not_overwritten(self) -> None:
        validator.validate_contract(self.contract)
        self.assertEqual(
            validator.load_json(validator.V1_PATH),
            self.contract,
            "on-disk v1 must equal the reproducible migration output",
        )
        self.assertEqual(self.contract["status"], "CANDIDATE_NOT_RUN")
        self.assertEqual(self.v0["contract_version"], "0")
        self.assertEqual(self.v0["status"], "CANDIDATE_NOT_RUN")
        self.assertEqual(
            self.contract["base_contract"]["raw_sha256"],
            validator.raw_sha256(validator.V0_PATH),
        )

    def test_measurable_path_actual_policy_miss_is_not_bounded_unreachable(self) -> None:
        body = base_body()
        body["R"]["R_actual"] = "FALSE"
        valid = make_instance(
            self.contract,
            "ACTUAL_POLICY_MISS",
            "G3_MEASURABLE_PATH_EXISTS_ACTUAL_POLICY_MISS",
            body,
        )
        validator.validate_instance(self.contract, valid)

        mislabeled = copy.deepcopy(valid)
        mislabeled["category"] = "BOUNDED_UNREACHABLE"
        mislabeled["reason_code"] = "G3_BOUNDED_UNREACHABLE"
        self.assert_invalid(mislabeled)

        retired = copy.deepcopy(valid)
        retired["category"] = "BOUNDED_UNREACHABLE"
        retired["reason_code"] = "G3_NO_ACTUAL_POLICY_PATH"
        self.assert_invalid(retired)

    def test_bounded_unreachable_requires_closed_complete_measurable_unsat(self) -> None:
        body = base_body()
        body["C"] = "UNSAT"
        body["V"] = "NO_QUALIFIED_EFFECT"
        body["R"]["R_physical_exists"] = "FALSE"
        body["R"]["R_measurable_exists"] = "FALSE"
        body["R"]["R_actual"] = "FALSE"
        valid = make_instance(
            self.contract,
            "BOUNDED_UNREACHABLE",
            "G3_BOUNDED_UNREACHABLE",
            body,
        )
        validator.validate_instance(self.contract, valid)

        incomplete = copy.deepcopy(valid)
        incomplete["g3_receipt"]["body"]["inventory_completeness"][
            "response_family"
        ] = "UNKNOWN"
        incomplete["g3_receipt"]["body_sha256"] = validator.canonical_sha256(
            incomplete["g3_receipt"]["body"]
        )
        self.assert_invalid(incomplete)

    def test_owner_authorized_new_episode_and_controller_substitution_are_distinct(self) -> None:
        owner_body = base_body()
        owner_body["T"] = "OWNER_AUTHORIZED_NEW_EPISODE"
        owner_body["task_diff"].update(
            {
                "classification": "OWNER_AUTHORIZED_NEW_EPISODE",
                "result_task_sha256": digest("owner-authorized-new-task"),
                "material_fields": ["V0.unacceptable_floor"],
                "changes": [
                    {
                        "path": "V0.unacceptable_floor",
                        "before_value": "no-third-party-disclosure",
                        "after_value": "purpose-bound-disclosure-allowed",
                    }
                ],
                "owner_authorization_receipts": [
                    receipt("owner-goal-change", "principal-owner")
                ],
            }
        )
        owner_case = make_instance(
            self.contract,
            "AUTHORIZED_NEW_EPISODE",
            "G3_OWNER_AUTHORIZED_MATERIAL_GOAL_CHANGE",
            owner_body,
        )
        validator.validate_instance(self.contract, owner_case)

        controller_body = base_body()
        controller_body["T"] = "CONTROLLER_SUBSTITUTION"
        controller_body["V"] = "INVALID"
        controller_body["task_diff"].update(
            {
                "classification": "CONTROLLER_SUBSTITUTION",
                "result_task_sha256": digest("controller-substituted-task"),
                "material_fields": ["Q_episode.target"],
                "changes": [
                    {
                        "path": "Q_episode.target",
                        "before_value": "submit-valid-joint-bid",
                        "after_value": "write-progress-report",
                    }
                ],
                "controller_claim_refs": [
                    receipt("controller-claim", "controller")
                ],
            }
        )
        controller_case = make_instance(
            self.contract,
            "INVALID_SUBSTITUTION",
            "G3_CONTROLLER_INVALID_SUBSTITUTION",
            controller_body,
        )
        validator.validate_instance(self.contract, controller_case)

        mixed = copy.deepcopy(controller_case)
        mixed["category"] = "AUTHORIZED_NEW_EPISODE"
        mixed["reason_code"] = "G3_OWNER_AUTHORIZED_MATERIAL_GOAL_CHANGE"
        self.assert_invalid(mixed)

    def test_g3_body_cannot_be_replaced_by_ref_hash_only_or_tampered(self) -> None:
        body = base_body()
        valid = make_instance(
            self.contract,
            "ACTUAL_POLICY_MISS",
            "G3_MEASURABLE_PATH_EXISTS_ACTUAL_POLICY_MISS",
            body,
        )
        valid["g3_receipt"]["body"]["R"]["R_actual"] = "FALSE"
        valid["g3_receipt"]["body_sha256"] = validator.canonical_sha256(
            valid["g3_receipt"]["body"]
        )
        validator.validate_instance(self.contract, valid)

        for missing in [
            "C",
            "N",
            "E",
            "T",
            "V",
            "R",
            "inventory_completeness",
            "counterfactual",
            "task_diff",
        ]:
            malformed = copy.deepcopy(valid)
            malformed["g3_receipt"]["body"].pop(missing)
            malformed["g3_receipt"]["body_sha256"] = validator.canonical_sha256(
                malformed["g3_receipt"]["body"]
            )
            self.assert_invalid(malformed)

        tampered = copy.deepcopy(valid)
        tampered["g3_receipt"]["body"]["E"] = "CHANGED"
        self.assert_invalid(tampered)

        ref_only = copy.deepcopy(valid)
        ref_only["g3_receipt"].pop("body")
        self.assert_invalid(ref_only)

    def test_embedded_g3_ref_must_equal_top_level_g3_ref(self) -> None:
        body = base_body()
        body["R"]["R_actual"] = "FALSE"
        instance = make_instance(
            self.contract,
            "ACTUAL_POLICY_MISS",
            "G3_MEASURABLE_PATH_EXISTS_ACTUAL_POLICY_MISS",
            body,
        )
        instance["g3_receipt"]["receipt_ref"] = receipt("other-G3")
        self.assert_invalid(instance)


if __name__ == "__main__":
    unittest.main()
