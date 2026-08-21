from __future__ import annotations

from copy import deepcopy
import base64
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g2_relation import (  # noqa: E402
    AXES,
    ReceiptVerificationError,
    run_scenario,
    schema_delta,
    semantic_projection,
    verify_receipt,
)


SCENARIOS = {
    item["episode_id"]: item
    for fixture in ("e2.json", "e0.json")
    for item in json.loads((ROOT / "fixtures" / fixture).read_text(encoding="utf-8"))
}


def scenario(episode_id: str, **overrides):
    value = deepcopy(SCENARIOS[episode_id])
    value.update(overrides)
    return value


class RelationProcessBoundaryTests(unittest.TestCase):
    def test_five_owners_are_distinct_processes_keys_instances_and_profiles(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        manifests = output["process_manifests"]
        self.assertEqual(len(manifests), 5)
        self.assertEqual(len({item["pid"] for item in manifests}), 5)
        self.assertEqual(len({item["key_id"] for item in manifests}), 5)
        self.assertEqual(len({item["process_instance_id"] for item in manifests}), 5)
        self.assertEqual(len({item["profile_source"]["id"] for item in manifests}), 5)
        self.assertTrue(all(item["returncode"] == 0 for item in output["process_exits"]))
        signer_by_owner = {
            act["preimage"]["owner_id"]: act["key_id"] for act in output["owner_acts"]
        }
        self.assertEqual(set(signer_by_owner), {"O_Q", "O_V", "O_R", "O_S", "O_P"})
        self.assertEqual(len(set(signer_by_owner.values())), 5)

    def test_every_receipt_preserves_raw_bytes_signature_key_pid_and_source(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        manifests = {item["owner_id"]: item for item in output["process_manifests"]}
        for act in output["owner_acts"]:
            pre = act["preimage"]
            raw = base64.b64decode(act["raw_bytes_b64"])
            self.assertEqual(json.loads(raw), pre)
            self.assertEqual(pre["process"]["pid"], manifests[pre["owner_id"]]["pid"])
            self.assertEqual(pre["source"], manifests[pre["owner_id"]]["source"])
            verify_receipt(
                act,
                manifests[pre["owner_id"]],
                {
                    "owner_id": pre["owner_id"],
                    "episode_id": pre["episode_id"],
                    "q": pre["q"],
                    "object_id": pre["object_id"],
                    "purpose": pre["purpose"],
                    "relation_revision": pre["relation_revision"],
                    "relation_revision_hash": pre["relation_revision_hash"],
                    "relation_version_hash": pre["relation_version_hash"],
                },
            )

    def test_relation_version_is_derived_snapshot_not_owner_or_downstream_truth(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        version = output["relation_version"]
        self.assertEqual(
            version["evidence_status"],
            "DERIVED_SNAPSHOT_OF_VERIFIED_EXACT_BOUND_OWNER_EVIDENCE",
        )
        self.assertEqual(len(version["verified_source_act_hashes"]), 6)
        self.assertTrue(
            {"NOT_AN_OWNER_ACT", "NOT_AUTHORITY", "NOT_EFFECT", "NOT_ACCEPTANCE"}
            <= set(version["non_entailments"])
        )
        self.assertEqual(output["evidence_boundaries"]["effect"], "NOT_RUN")
        self.assertEqual(output["evidence_boundaries"]["acceptance"], "NOT_RUN")

    def test_authorized_and_activated_are_only_g5_g6_unverified(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        authorized = output["axis_evidence"]["authorized"]
        activated = output["axis_evidence"]["activated"]
        self.assertEqual(authorized["truth_owner_boundary"], "G5_UNVERIFIED")
        self.assertEqual(activated["truth_owner_boundary"], "G6_UNVERIFIED")
        self.assertTrue(
            all(state == "G5_UNVERIFIED_OWNER_INTENT_ONLY" for state in authorized["owner_states"].values())
        )
        self.assertTrue(
            all(state == "G6_UNVERIFIED_NO_EFFECT" for state in activated["owner_states"].values())
        )
        self.assertTrue(
            all(
                act["preimage"]["payload"].get("effect_asserted") is False
                for act in output["owner_acts"]
                if act["preimage"]["kind"] == "ACTIVATE"
            )
        )

    def test_query_and_receipt_raw_bytes_are_saved_in_order(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        records = output["trace"]
        for index, record in enumerate(records):
            if record["event"] != "owner_receipt_received":
                continue
            self.assertGreater(index, 0)
            prior = records[index - 1]
            self.assertEqual(prior["event"], "owner_query")
            self.assertEqual(prior["query_id"], record["query_id"])
            self.assertIn("request_raw_bytes_b64", prior)
            self.assertIn("raw_bytes_b64", record["receipt"])

    def test_absent_withheld_and_disclosed_are_distinct_signed_derivations(self):
        absent = run_scenario(scenario("CE001-E2-COLUMN-ABSENT"))
        withheld = run_scenario(scenario("CE001-E2-COLUMN-WITHHELD"))
        disclosed = run_scenario(scenario("CE001-E2-EXACT-V1"))
        self.assertEqual(absent["private_column_evidence"]["state"], "ABSENT")
        self.assertEqual(withheld["private_column_evidence"]["state"], "WITHHELD")
        self.assertEqual(disclosed["private_column_evidence"]["state"], "DISCLOSED")
        hashes = {
            absent["relation_version"]["version_hash"],
            withheld["relation_version"]["version_hash"],
            disclosed["relation_version"]["version_hash"],
        }
        self.assertEqual(len(hashes), 3)

    def test_refusal_keeps_raw_act_and_closes_global_downstream_gate(self):
        output = run_scenario(scenario("CE001-E2-SAFETY-REFUSAL"))
        acts = output["owner_acts"]
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_S"
                and act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in acts
            )
        )
        self.assertFalse(
            any(act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"} for act in acts)
        )
        self.assertEqual(
            output["axis_evidence"]["claimed"]["owner_states"]["O_S"],
            "REFUSED_BLOCKING",
        )
        self.assertEqual(
            output["relation_version"]["evidence_status"],
            "DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION",
        )
        self.assertFalse(output["relation_version"]["downstream_relation_gate_open"])

    def test_schema_delta_keeps_structural_materiality(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        self.assertTrue(output["relation_version"]["delta"]["material"])
        parameter = schema_delta({"parameters": ["T0"]}, {"parameters": ["T0+5m"]})
        presentation = schema_delta({"presentation": ["a"]}, {"presentation": ["b"]})
        self.assertFalse(parameter["material"])
        self.assertFalse(presentation["material"])

    def test_no_green_or_success_total_is_emitted(self):
        output = run_scenario(scenario("CE001-E2-EXACT-V1"))
        self.assertTrue({"green", "success", "relation_valid", "overall_status"}.isdisjoint(output))
        self.assertEqual(set(output["axis_evidence"]), set(AXES))
        self.assertTrue(
            all(output["axis_evidence"][axis]["global_status"] == "NOT_COMPUTED" for axis in AXES)
        )

    def test_semantic_rerun_matches_while_process_identity_changes(self):
        first = run_scenario(scenario("CE001-E2-EXACT-V1"), run_id="r1")
        second = run_scenario(scenario("CE001-E2-EXACT-V1"), run_id="r2")
        self.assertEqual(semantic_projection(first), semantic_projection(second))
        self.assertNotEqual(
            {item["pid"] for item in first["process_manifests"]},
            {item["pid"] for item in second["process_manifests"]},
        )
        self.assertNotEqual(
            {item["key_id"] for item in first["process_manifests"]},
            {item["key_id"] for item in second["process_manifests"]},
        )


if __name__ == "__main__":
    unittest.main()
