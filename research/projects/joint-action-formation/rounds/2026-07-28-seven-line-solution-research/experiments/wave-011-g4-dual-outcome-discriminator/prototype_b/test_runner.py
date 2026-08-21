from __future__ import annotations

import unittest
from typing import Any

from fixtures import by_ref
from primitive_service import FORBIDDEN_RESPONSE_KEYS, PrimitiveService
from runner import run_world


def response_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(value)
        for nested in value.values():
            keys.update(response_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(response_keys(nested))
    return keys


def prediction_map(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["stage"]: item for item in result["predictions"]}


class PrimitiveServiceTest(unittest.TestCase):
    def test_raw_responses_have_no_pre_adjudicated_keys(self) -> None:
        result = run_world(by_ref("ACTIVE-RESERVATION-GRANTED"))
        keys = response_keys([entry["response"] for entry in result["broker_log"]])
        self.assertFalse(FORBIDDEN_RESPONSE_KEYS.intersection(keys))

    def test_active_pair_is_identical_until_reservation_response(self) -> None:
        left = run_world(by_ref("ACTIVE-RESERVATION-GRANTED"))
        right = run_world(by_ref("ACTIVE-RESERVATION-REFUSED"))
        left_log = left["broker_log"]
        right_log = right["broker_log"]
        self.assertEqual(
            [entry["response"] for entry in left_log[:3]],
            [entry["response"] for entry in right_log[:3]],
        )
        self.assertEqual(
            left_log[3]["response"]["outcome"],
            "GRANTED",
        )
        self.assertEqual(
            right_log[3]["response"]["outcome"],
            "REFUSED",
        )
        self.assertEqual(prediction_map(left)["P1"]["Y_success"], "RELY")
        self.assertEqual(prediction_map(right)["P1"]["Y_success"], "BLOCK")

    def test_passive_pair_keeps_same_predictions(self) -> None:
        left = run_world(by_ref("PASSIVE-LATENT-READY"))
        right = run_world(by_ref("PASSIVE-LATENT-BROKEN"))
        self.assertEqual(left["predictions"], right["predictions"])
        self.assertEqual(prediction_map(left)["P1"]["Y_success"], "ABSTAIN")
        self.assertEqual(
            prediction_map(left)["P1"]["Y_effect"], "NOT_PREDICTED_BY_G4"
        )

    def test_hard_pair_has_same_allowed_interaction_transcript(self) -> None:
        left = run_world(by_ref("HARD-LATENT-READY"))
        right = run_world(by_ref("HARD-LATENT-BROKEN"))
        self.assertEqual(left["predictions"], right["predictions"])
        self.assertEqual(left["broker_log"], right["broker_log"])
        self.assertEqual(prediction_map(left)["P1"]["Y_success"], "RELY")
        self.assertEqual(prediction_map(left)["P1"]["Y_resolution"], "ABSTAIN")

    def test_response_loss_runs_readback_and_reconciliation_once(self) -> None:
        result = run_world(by_ref("ACTIVE-RESERVATION-GRANTED"))
        self.assertEqual(
            [entry["primitive"] for entry in result["broker_log"]],
            [
                "read_revision",
                "read_policy",
                "request_authority",
                "request_reservation",
                "submit_operation",
                "read_operation_status",
                "reconcile_operation",
                "read_operation_status",
            ],
        )
        self.assertEqual(
            result["final"]["execution"], "RECONCILED_AFTER_RESPONSE_LOSS"
        )
        self.assertEqual(result["final"]["effect_count"], 1)
        self.assertEqual(
            result["final"]["resolution_disposition"],
            "CONFIRMED_APPLIED_NO_RETRY",
        )
        state = result["state_after"]
        self.assertEqual(
            state["operation_records"]["refund-op-001"]["effect_count"], 1
        )
        self.assertIn("refund-op-001", state["reconciliation_records"])

    def test_service_rejects_unavailable_primitive(self) -> None:
        service = PrimitiveService(by_ref("PASSIVE-LATENT-READY"))
        with self.assertRaises(ValueError):
            service.call("request_reservation", {})


if __name__ == "__main__":
    unittest.main()
