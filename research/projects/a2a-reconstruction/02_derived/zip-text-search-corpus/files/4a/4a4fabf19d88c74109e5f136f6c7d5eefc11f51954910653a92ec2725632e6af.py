from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from towow_fieldkit.schema_change import classify_change, compile_readiness
from towow_fieldkit.store import CaseStore


BASE_SCHEMA = {
    "schema_id": "pilot",
    "version": "1",
    "roles": {"buyer": {}, "provider": {}},
    "object_types": {"dataset": {}},
    "actions": {
        "propose": {"actor_roles": ["provider"], "material": True},
        "commit": {"actor_roles": ["buyer"], "material": True},
        "run_probe": {"actor_roles": ["provider"], "material": True, "produces_effect": True},
    },
    "transitions": [
        {"from": "FORMING", "action": "propose", "to": "PROPOSED"},
        {"from": "PROPOSED", "action": "commit", "to": "COMMITTED"},
        {"from": "COMMITTED", "action": "run_probe", "to": "EFFECT_PENDING"},
    ],
    "authority_rules": {"propose": ["provider"], "commit": ["buyer"], "run_probe": ["provider"]},
    "witness_rules": {"run_probe": {"source": "buyer"}},
    "acceptance_rules": {"probe": {"required_roles": ["buyer"]}},
    "data_rules": {"dataset": {"purposes": ["pilot"], "training": False}},
    "metadata": {"label": "base"},
}


class FieldkitTests(unittest.TestCase):
    def test_event_hash_chain_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = CaseStore.create(Path(temp) / "case", "Demo", "case-demo")
            store.add_party("buyer", "Buyer", "root:buyer")
            store.set_private_intake("buyer", {"hard_constraints": ["no training"]})
            store.add_relation_version({"schema": BASE_SCHEMA, "instance": {"state": "FORMING"}})
            store.append_event(event_type="REFUSAL", actor="buyer", payload={"reason": "raw data"}, relation_version=1)
            check = store.validate()
            self.assertTrue(check["valid"], check)
            self.assertEqual(check["party_count"], 1)
            metrics = store.metrics()
            self.assertEqual(metrics["event_types"]["REFUSAL"], 1)

    def test_adjudication_and_redacted_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "case"
            store = CaseStore.create(root, "Demo", "case-demo")
            store.add_party("buyer", "Buyer", "root:buyer")
            store.set_private_intake("buyer", {"secret": "not-exported"})
            store.add_relation_version({"schema": BASE_SCHEMA, "instance": {"state": "FORMING"}})
            store.record_adjudication({"adjudicator_id": "adj-1", "stable_disposition": "CONDITIONAL", "confidence": 0.8})
            target = Path(temp) / "export"
            store.export_redacted(target)
            self.assertTrue((target / "shared" / "events.jsonl").exists())
            self.assertFalse((target / "private").exists())
            self.assertTrue((target / "REDACTION_NOTICE.json").exists())

    def test_explicit_metrics_are_summed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = CaseStore.create(Path(temp) / "case", "Demo", "case-demo")
            store.append_event(event_type="PROBE_RESULT", actor="provider", payload={"human_minutes": 12.5, "sensitive_disclosure_units": 3, "elapsed_seconds": 120})
            report = store.metrics()
            self.assertEqual(report["explicit_human_minutes"], 12.5)
            self.assertEqual(report["explicit_sensitive_disclosure_units"], 3.0)
            self.assertEqual(report["explicit_elapsed_seconds"], 120.0)

    def test_material_authority_change(self) -> None:
        changed = json.loads(json.dumps(BASE_SCHEMA))
        changed["authority_rules"]["commit"] = ["buyer", "legal"]
        report = classify_change(BASE_SCHEMA, changed, current_state="FORMING", active_resources=["dataset"], active_roles=["buyer", "provider"])
        self.assertEqual(report.classification, "MATERIAL_SCHEMA_CHANGE")

    def test_metadata_change_is_nonmaterial(self) -> None:
        changed = json.loads(json.dumps(BASE_SCHEMA))
        changed["metadata"]["label"] = "renamed"
        report = classify_change(BASE_SCHEMA, changed, current_state="FORMING")
        self.assertEqual(report.classification, "NON_MATERIAL_SCHEMA_CHANGE")


    def test_order_only_rule_change_is_ignored(self) -> None:
        changed = json.loads(json.dumps(BASE_SCHEMA))
        changed["authority_rules"]["run_probe"] = ["auditor", "provider"]
        base = json.loads(json.dumps(BASE_SCHEMA))
        base["authority_rules"]["run_probe"] = ["provider", "auditor"]
        report = classify_change(base, changed, current_state="FORMING")
        self.assertEqual(report.classification, "PARAMETER_OR_NO_SCHEMA_CHANGE")

    def test_parameter_only_has_no_schema_change(self) -> None:
        report = classify_change(BASE_SCHEMA, json.loads(json.dumps(BASE_SCHEMA)), current_state="FORMING")
        self.assertEqual(report.classification, "PARAMETER_OR_NO_SCHEMA_CHANGE")

    def test_active_data_right_change_is_material(self) -> None:
        changed = json.loads(json.dumps(BASE_SCHEMA))
        changed["data_rules"]["dataset"]["training"] = True
        report = classify_change(BASE_SCHEMA, changed, current_state="FORMING", active_resources=["dataset"])
        self.assertTrue(report.material)

    def test_jurisdiction_rule_change_is_material(self) -> None:
        base = json.loads(json.dumps(BASE_SCHEMA))
        base["jurisdiction_rules"] = {"required": ["corporate"]}
        changed = json.loads(json.dumps(base))
        changed["jurisdiction_rules"]["required"].append("competition")
        report = classify_change(base, changed, current_state="FORMING")
        self.assertEqual(report.classification, "MATERIAL_SCHEMA_CHANGE")
        self.assertTrue(any(f.component == "jurisdiction_rules" for f in report.findings))

    def test_compile_readiness_rejects_missing_stance(self) -> None:
        state = {
            "state": "FORMING",
            "required_stances": ["buyer:commit"],
            "obtained_stances": [],
            "required_mandates": [],
            "valid_mandates": [],
            "unresolved_material_counterexamples": [],
            "reopen_rules_defined": True,
            "rollback_or_compensation_defined": True,
        }
        report = compile_readiness(BASE_SCHEMA, state)
        self.assertFalse(report["ready"])
        self.assertIn("MISSING_REQUIRED_STANCE", {x["code"] for x in report["failures"]})

    def test_validation_detects_event_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "case"
            store = CaseStore.create(root, "Demo", "case-demo")
            store.append_event(event_type="ASSERTION_MADE", actor="agent", payload={"claim": "x"})
            events = root / "shared" / "events.jsonl"
            value = json.loads(events.read_text(encoding="utf-8"))
            value["payload"]["claim"] = "tampered"
            events.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
            report = store.validate()
            self.assertFalse(report["valid"])
            self.assertTrue(any("hash mismatch" in e for e in report["errors"]))

    def test_compile_readiness(self) -> None:
        state = {
            "state": "FORMING",
            "required_stances": ["buyer:commit"],
            "obtained_stances": ["buyer:commit"],
            "required_mandates": ["buyer:budget"],
            "valid_mandates": ["buyer:budget"],
            "unresolved_material_counterexamples": [],
            "reopen_rules_defined": True,
            "rollback_or_compensation_defined": True,
        }
        report = compile_readiness(BASE_SCHEMA, state)
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["readiness"], "READY")

    def test_compile_readiness_rejects_missing_jurisdiction_review(self) -> None:
        state = {
            "state": "FORMING",
            "required_stances": [],
            "obtained_stances": [],
            "required_mandates": [],
            "valid_mandates": [],
            "unresolved_material_counterexamples": [],
            "reopen_rules_defined": True,
            "rollback_or_compensation_defined": True,
            "required_jurisdictions": ["competition", "privacy"],
            "covered_jurisdictions": ["privacy"],
        }
        report = compile_readiness(BASE_SCHEMA, state)
        self.assertFalse(report["ready"])
        self.assertEqual(report["readiness"], "NOT_READY")
        self.assertIn("MISSING_REQUIRED_JURISDICTION_REVIEW", {x["code"] for x in report["failures"]})

    def test_open_challenge_with_contingency_is_ready_with_contingency(self) -> None:
        state = {
            "state": "FORMING",
            "required_stances": [],
            "obtained_stances": [],
            "required_mandates": [],
            "valid_mandates": [],
            "unresolved_material_counterexamples": [],
            "reopen_rules_defined": True,
            "rollback_or_compensation_defined": True,
            "open_material_challenges": ["regulatory-review"],
            "challenge_contingency_defined": True,
            "challenge_horizon": "until-final-order",
        }
        report = compile_readiness(BASE_SCHEMA, state)
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["readiness"], "READY_WITH_CONTINGENCY")
        self.assertIn("OPEN_MATERIAL_CHALLENGE_COMPILED_WITH_CONTINGENCY", {x["code"] for x in report["warnings"]})

    def test_open_challenge_without_contingency_blocks_compile(self) -> None:
        state = {
            "state": "FORMING",
            "required_stances": [],
            "obtained_stances": [],
            "required_mandates": [],
            "valid_mandates": [],
            "unresolved_material_counterexamples": [],
            "reopen_rules_defined": True,
            "rollback_or_compensation_defined": True,
            "open_material_challenges": ["regulatory-review"],
            "challenge_contingency_defined": False,
        }
        report = compile_readiness(BASE_SCHEMA, state)
        self.assertFalse(report["ready"])
        self.assertIn("OPEN_MATERIAL_CHALLENGE_WITHOUT_CONTINGENCY", {x["code"] for x in report["failures"]})


if __name__ == "__main__":
    unittest.main()
