from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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

    def test_candidate_problem_requires_historical_inheritance_ref(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v1-candidate.json"
        )
        problem = researchctl.load_json(path)
        problem.pop("historical_inheritance_ref")

        errors = researchctl.check_problem_historical_inheritance(
            researchctl.DEFAULT_PROJECT,
            path,
            problem,
        )

        self.assertIn(
            "CANDIDATE/ACTIVE problem requires historical_inheritance_ref",
            "\n".join(errors),
        )

    def test_historical_inheritance_must_cover_canonical_capabilities(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v1-history-alignment.json"
        )
        audit = researchctl.load_json(path)
        self.assertEqual([], researchctl.validate_historical_inheritance(audit, path))

        incomplete = copy.deepcopy(audit)
        removed = incomplete["capabilities"].pop()
        coverage_key = removed["v1_coverage"].lower()
        incomplete["coverage_summary"][coverage_key] -= 1

        errors = researchctl.validate_historical_inheritance(incomplete, path)

        self.assertIn(
            "inheritance audit omits canonical capabilities",
            "\n".join(errors),
        )

    def test_active_problem_requires_reviewed_ready_inheritance(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v1-candidate.json"
        )
        problem = researchctl.load_json(path)
        problem["status"] = "ACTIVE"

        errors = researchctl.check_problem_historical_inheritance(
            researchctl.DEFAULT_PROJECT,
            path,
            problem,
        )

        joined = "\n".join(errors)
        self.assertIn("ACTIVE problem requires a REVIEWED", joined)
        self.assertIn("activation_recommendation READY", joined)

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

    def test_standing_transfer_authority_is_bounded_by_manifest(self):
        decision_id = "DEC-2026-07-28-STANDING-RESEARCH-TRANSFER"
        target = {"id": "BATCH-FUTURE", "version": "f" * 64}
        disclosure = {
            "destination": "Anthropic Claude",
            "classification": "NON_PUBLIC_DERIVED_RESEARCH",
            "payload_size_bytes": 1000,
            "does_not_include": ["private participant data"],
        }
        self.assertTrue(
            researchctl.decision_allows_transfer(
                decision_id,
                "SEND_BLIND_REVIEW_TO_CLAUDE",
                target,
                disclosure,
                "research/projects/joint-action-formation",
            )
        )
        missing_privacy_exclusion = copy.deepcopy(disclosure)
        missing_privacy_exclusion["does_not_include"] = []
        self.assertFalse(
            researchctl.decision_allows_transfer(
                decision_id,
                "SEND_BLIND_REVIEW_TO_CLAUDE",
                target,
                missing_privacy_exclusion,
                "research/projects/joint-action-formation",
            )
        )
        wrong_destination = copy.deepcopy(disclosure)
        wrong_destination["destination"] = "Unknown External Model"
        self.assertFalse(
            researchctl.decision_allows_transfer(
                decision_id,
                "SEND_BLIND_REVIEW_TO_CLAUDE",
                target,
                wrong_destination,
                "research/projects/joint-action-formation",
            )
        )
        self.assertFalse(
            researchctl.decision_allows(
                decision_id,
                "ACTIVATE_PROBLEM",
                target,
            )
        )

    def test_claude_output_schema_can_drop_external_draft_metadata(self):
        schema = {
            key: value
            for key, value in researchctl.schema_for("BlindReview").items()
            if key not in {"$schema", "$id"}
        }
        self.assertNotIn("$schema", schema)
        self.assertNotIn("$id", schema)
        self.assertEqual("object", schema["type"])
        self.assertIn("strongest_counterarguments", schema["required"])


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

    def test_infrastructure_retry_preserves_evidence_and_resets_same_batch(self):
        plan_path = self.plan("BATCH-TEST-INFRA-RETRY")
        plan = researchctl.load_plan(plan_path)
        plan["mode"] = "codex"
        plan["status"] = "FAILED"
        plan["external_disclosure"] = {
            "manifest": ".research-runtime/test-disclosure.json",
            "approval_decision_id": "DEC-TEST-INFRA-RETRY",
        }
        for run in plan["runs"]:
            run_dir = researchctl.resolve_root_path(run["run_dir"])
            manifest_path = run_dir / "manifest.json"
            manifest = researchctl.load_json(manifest_path)
            manifest["mode"] = "codex"
            manifest["status"] = "INFRA_FAILED"
            manifest["attempt"] = 1
            researchctl.write_json(manifest_path, manifest)
            (run_dir / "attempt-1-error.txt").write_text(
                "invalid_json_schema\n",
                encoding="utf-8",
            )
            (run_dir / "result.raw.json").write_text(
                '{"candidate_claims":[]}\n',
                encoding="utf-8",
            )
        researchctl.write_json(plan_path, plan)

        disclosure = {"disclosure_sha256": "a" * 64}
        with (
            mock.patch.object(
                researchctl,
                "verify_external_disclosure",
                return_value=disclosure,
            ),
            mock.patch.object(researchctl, "decision_allows_transfer", return_value=True),
        ):
            self.assertEqual(
                0,
                researchctl.retry_infra_batch(
                    argparse.Namespace(batch="BATCH-TEST-INFRA-RETRY")
                ),
            )

        reset_plan = researchctl.load_plan(plan_path)
        self.assertEqual("PLANNED", reset_plan["status"])
        for run in reset_plan["runs"]:
            run_dir = researchctl.resolve_root_path(run["run_dir"])
            manifest = researchctl.load_json(run_dir / "manifest.json")
            self.assertEqual("PLANNED", manifest["status"])
            self.assertEqual(0, manifest["attempt"])
            self.assertEqual(
                ["invalid_json_schema\n"],
                [
                    path.read_text(encoding="utf-8")
                    for path in sorted(run_dir.glob("infra-history/*/attempt-1-error.txt"))
                ],
            )
            self.assertEqual(
                ['{"candidate_claims":[]}\n'],
                [
                    path.read_text(encoding="utf-8")
                    for path in sorted(run_dir.glob("infra-history/*/result.raw.json"))
                ],
            )

    def test_runner_binds_authoritative_result_envelope(self):
        plan_path = self.plan("BATCH-TEST-RESULT-ENVELOPE")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        bundle = researchctl.load_json(run_dir / "input.json")
        model_result = {
            "run_id": "model-guessed-run",
            "batch_id": "model-guessed-batch",
            "line_id": "model-guessed-line",
            "question_version": "unknown",
            "scenario_version": "unknown",
            "input_hash": "0" * 64,
            "candidate_claims": [{"claim": "content remains unchanged"}],
        }
        bound = researchctl.bind_result_envelope(model_result, bundle)
        self.assertEqual(bundle["run_id"], bound["run_id"])
        self.assertEqual(bundle["batch_id"], bound["batch_id"])
        self.assertEqual(bundle["line"]["id"], bound["line_id"])
        self.assertEqual(bundle["problem"]["version"], bound["question_version"])
        self.assertEqual(bundle["scenario"]["version"], bound["scenario_version"])
        self.assertEqual(bundle["input_hash"], bound["input_hash"])
        self.assertEqual(model_result["candidate_claims"], bound["candidate_claims"])

    def test_codex_prompt_embeds_exact_authorized_input_without_file_access(self):
        plan_path = self.plan("BATCH-TEST-INBAND-INPUT")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        bundle = researchctl.load_json(run_dir / "input.json")
        input_text = (run_dir / "input.json").read_text(encoding="utf-8")
        prompt = researchctl.build_codex_prompt(bundle, input_text)
        self.assertIn(input_text, prompt)
        self.assertIn("<AUTHORIZED_INPUT_JSON>", prompt)
        self.assertIn("do not inspect the filesystem", prompt)
        self.assertNotIn("Read WORKER_POLICY.md", prompt)

    def test_access_blocked_result_is_retryable_but_substantive_result_is_not(self):
        blocked = {
            "source_statements": [],
            "candidate_claims": [],
            "negative_results": [
                {"finding": "The permitted evidence source was unavailable."}
            ],
        }
        substantive = {
            "source_statements": [
                {"source_locator": "allowed.md", "statement": "Observed content."}
            ],
            "candidate_claims": [],
            "negative_results": [],
        }
        self.assertTrue(researchctl.result_is_access_blocked(blocked))
        self.assertFalse(researchctl.result_is_access_blocked(substantive))

    def test_completed_access_block_is_archived_before_retry(self):
        plan_path = self.plan("BATCH-TEST-ACCESS-BLOCK-RETRY")
        plan = researchctl.load_plan(plan_path)
        plan["mode"] = "codex"
        plan["status"] = "COMPLETED"
        plan["external_disclosure"] = {
            "manifest": ".research-runtime/test-access-disclosure.json",
            "approval_decision_id": "DEC-TEST-ACCESS-RETRY",
        }
        for run in plan["runs"]:
            run_dir = researchctl.resolve_root_path(run["run_dir"])
            manifest_path = run_dir / "manifest.json"
            manifest = researchctl.load_json(manifest_path)
            manifest["mode"] = "codex"
            manifest["status"] = "COMPLETED"
            manifest["attempt"] = 1
            researchctl.write_json(manifest_path, manifest)
            researchctl.write_json(
                run_dir / "result.json",
                {
                    "source_statements": [],
                    "candidate_claims": [],
                    "negative_results": [
                        {"finding": "The permitted evidence source was unavailable."}
                    ],
                },
            )
        researchctl.write_json(plan_path, plan)

        with (
            mock.patch.object(
                researchctl,
                "verify_external_disclosure",
                return_value={"disclosure_sha256": "b" * 64},
            ),
            mock.patch.object(researchctl, "decision_allows_transfer", return_value=True),
        ):
            self.assertEqual(
                0,
                researchctl.retry_infra_batch(
                    argparse.Namespace(batch="BATCH-TEST-ACCESS-BLOCK-RETRY")
                ),
            )

        for run in researchctl.load_plan(plan_path)["runs"]:
            run_dir = researchctl.resolve_root_path(run["run_dir"])
            manifest = researchctl.load_json(run_dir / "manifest.json")
            self.assertEqual("PLANNED", manifest["status"])
            self.assertFalse((run_dir / "result.json").exists())
            self.assertEqual(
                1,
                len(list(run_dir.glob("infra-history/*/result.json"))),
            )


if __name__ == "__main__":
    unittest.main()
