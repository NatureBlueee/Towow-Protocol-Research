from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("researchctl", ROOT / "tools" / "researchctl.py")
assert SPEC and SPEC.loader
researchctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(researchctl)


def remove_path(value, parts):
    target = value
    for part in parts[:-1]:
        target = target[part]
    del target[parts[-1]]


class ContractTests(unittest.TestCase):
    def test_current_project_validates(self):
        self.assertEqual([], researchctl.validate_project(researchctl.DEFAULT_PROJECT, strict=True))

    def test_negative_contract_fixtures(self):
        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "invalid-contract-mutations.json").read_text(
                encoding="utf-8"
            )
        )
        for case in fixture["cases"]:
            with self.subTest(case=case["name"]):
                base = researchctl.load_json(ROOT / case["base"])
                mutated = copy.deepcopy(base)
                remove_path(mutated, case["remove"])
                errors = researchctl.validate_schema(mutated, ROOT / case["base"])
                self.assertTrue(errors)
                self.assertIn(case["expected_error_fragment"], "\n".join(errors))

    def test_environment_decision_cannot_activate_problem_or_stable_claim(self):
        decision_id = "DEC-2026-07-28-ENVIRONMENT-V1"
        self.assertFalse(researchctl.decision_allows(decision_id, "ACTIVATE_PROBLEM"))
        self.assertFalse(researchctl.decision_allows(decision_id, "PROMOTE_STABLE_CLAIM"))
        self.assertFalse(researchctl.decision_allows(decision_id, "ACTIVATE_REAL_SCENARIO"))

    def test_real_scenario_cannot_auto_activate(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "scenarios"
            / "problem-definition-archive-v0.json"
        )
        scenario = researchctl.load_json(path)
        scenario["scenario_class"] = "REAL"
        scenario["status"] = "ACTIVE"
        scenario["activation"] = {
            "requires_user_approval": False,
            "approval_decision_id": "DEC-2026-07-28-ENVIRONMENT-V1",
        }
        self.assertFalse(
            researchctl.decision_allows(
                scenario["activation"]["approval_decision_id"],
                "ACTIVATE_REAL_SCENARIO",
                scenario,
            )
        )


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        runtime_parent = ROOT / ".research-runtime"
        runtime_parent.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=runtime_parent)
        self.original_runtime = researchctl.RUNTIME
        researchctl.RUNTIME = Path(self.temporary.name) / "runtime"

    def tearDown(self):
        researchctl.RUNTIME = self.original_runtime
        self.temporary.cleanup()

    def plan(self, batch_id):
        args = argparse.Namespace(
            project=None,
            scenario=None,
            mode="mock",
            batch_id=batch_id,
            max_parallel=3,
        )
        self.assertEqual(0, researchctl.plan_batch(args))
        return researchctl.RUNTIME / batch_id / "plan.json"

    def test_mock_seven_line_batch_is_isolated_and_idempotent(self):
        plan_path = self.plan("BATCH-TEST-SEVEN-LINES")
        args = argparse.Namespace(plan=researchctl.relative(plan_path))
        self.assertEqual(0, researchctl.run_batch(args))
        plan = researchctl.load_plan(plan_path)
        self.assertEqual(7, len(plan["runs"]))
        attempts = {}
        for run in plan["runs"]:
            run_dir = researchctl.resolve_root_path(run["run_dir"])
            manifest = researchctl.load_json(run_dir / "manifest.json")
            result = researchctl.load_json(run_dir / "result.json")
            attempts[run["line_id"]] = manifest["attempt"]
            self.assertEqual("COMPLETED", manifest["status"])
            self.assertEqual(run["line_id"], result["line_id"])
            self.assertEqual(
                [],
                researchctl.validate_result_semantics(
                    result, researchctl.load_json(run_dir / "input.json")
                ),
            )
        self.assertEqual(0, researchctl.run_batch(args))
        for run in plan["runs"]:
            manifest = researchctl.load_json(
                researchctl.resolve_root_path(run["run_dir"]) / "manifest.json"
            )
            self.assertEqual(attempts[run["line_id"]], manifest["attempt"])

    def test_plan_input_fingerprint_tampering_is_policy_violation(self):
        plan_path = self.plan("BATCH-TEST-STALE")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        locator = next(iter(first["input_components"]))
        first["input_components"][locator] = "0" * 64
        researchctl.write_json(plan_path, plan)
        result = researchctl.run_batch(argparse.Namespace(plan=researchctl.relative(plan_path)))
        self.assertEqual(1, result)
        manifest = researchctl.load_json(
            researchctl.resolve_root_path(first["run_dir"]) / "manifest.json"
        )
        self.assertEqual("POLICY_VIOLATION", manifest["status"])

    def test_source_change_is_marked_stale_without_overwrite(self):
        plan_path = self.plan("BATCH-TEST-SOURCE-STALE")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        source = researchctl.RUNTIME / "mutable-source.txt"
        source.write_text("version one\n", encoding="utf-8")
        locator = researchctl.relative(source)
        first["input_components"][locator] = researchctl.sha256_file(source)
        first["input_hash"] = researchctl.json_hash(first["input_components"])
        bundle = researchctl.load_json(run_dir / "input.json")
        bundle["input_components"] = copy.deepcopy(first["input_components"])
        bundle["input_hash"] = first["input_hash"]
        researchctl.write_json(run_dir / "input.json", bundle)
        manifest = researchctl.load_json(run_dir / "manifest.json")
        manifest["input_hash"] = first["input_hash"]
        researchctl.write_json(run_dir / "manifest.json", manifest)
        source.write_text("version two\n", encoding="utf-8")
        line_id, status = researchctl.run_one(plan, first)
        self.assertEqual(first["line_id"], line_id)
        self.assertEqual("STALE_FOR_CURRENT", status)
        manifest = researchctl.load_json(run_dir / "manifest.json")
        self.assertEqual("STALE_FOR_CURRENT", manifest["status"])
        self.assertFalse((run_dir / "result.json").exists())

    def test_blind_review_bundle_hides_formal_line_identity(self):
        plan_path = self.plan("BATCH-TEST-BLIND")
        self.assertEqual(
            0,
            researchctl.run_batch(argparse.Namespace(plan=researchctl.relative(plan_path))),
        )
        self.assertEqual(
            0,
            researchctl.prepare_review(argparse.Namespace(batch="BATCH-TEST-BLIND")),
        )
        bundle_path = researchctl.RUNTIME / "BATCH-TEST-BLIND" / "review" / "review-bundle.json"
        text = bundle_path.read_text(encoding="utf-8")
        self.assertNotIn('"line_id"', text)
        self.assertNotIn("/native_lines/", text)
        bundle = researchctl.load_json(bundle_path)
        self.assertEqual(7, len(bundle["anonymous_returns"]))
        self.assertIn("expected answer", bundle["excluded"])

    def test_codex_batch_requires_exact_disclosure_decision(self):
        args = argparse.Namespace(
            project=None,
            scenario=None,
            mode="codex",
            batch_id="BATCH-TEST-CODEX-CONSENT",
            max_parallel=3,
        )
        self.assertEqual(0, researchctl.plan_batch(args))
        plan_path = researchctl.RUNTIME / args.batch_id / "plan.json"
        plan = researchctl.load_plan(plan_path)
        disclosure = researchctl.load_json(
            researchctl.resolve_root_path(plan["external_disclosure"]["manifest"])
        )
        self.assertEqual("OpenAI Codex", disclosure["destination"])
        self.assertNotIn("source_registry.csv", disclosure["unique_source_locators"])
        self.assertNotIn(
            "capability_preservation_matrix.csv",
            disclosure["unique_source_locators"],
        )
        with self.assertRaises(researchctl.ResearchError):
            researchctl.run_batch(argparse.Namespace(plan=researchctl.relative(plan_path)))

    def test_disclosed_payload_change_is_rejected(self):
        args = argparse.Namespace(
            project=None,
            scenario=None,
            mode="codex",
            batch_id="BATCH-TEST-DISCLOSURE-MUTATION",
            max_parallel=3,
        )
        self.assertEqual(0, researchctl.plan_batch(args))
        plan_path = researchctl.RUNTIME / args.batch_id / "plan.json"
        plan = researchctl.load_plan(plan_path)
        first_payload = researchctl.resolve_root_path(
            researchctl.load_json(
                researchctl.resolve_root_path(plan["external_disclosure"]["manifest"])
            )["payloads"][0]["payload"]
        )
        first_payload.write_text(first_payload.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(researchctl.ResearchError):
            researchctl.verify_external_disclosure(plan)


if __name__ == "__main__":
    unittest.main()
