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

    def test_json_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"id": "one", "id": "two"}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                researchctl.ResearchError,
                "duplicate JSON key: id",
            ):
                researchctl.load_json(path)

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

        original_load_json = researchctl.load_json

        def load_nonready_audit(candidate_path):
            document = original_load_json(candidate_path)
            if document.get("kind") == "HistoricalInheritanceAudit":
                document["activation_recommendation"] = "REWRITE_BEFORE_ACTIVATION"
            return document

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_nonready_audit,
        ):
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
        self.assertIn(
            "exact source/target-hash user promotion receipt",
            "\n".join(
                researchctl.check_exact_promotion_receipt(
                    path,
                    scenario,
                    "scenario",
                )
            ),
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

    def test_v2_is_additive_snapshot_and_v1_hashes_are_unchanged(self):
        problem_dir = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
        )
        v2 = researchctl.load_json(problem_dir / "v2-candidate.json")
        lineage = v2["lineage"]

        self.assertEqual("ADDITIVE_SNAPSHOT", lineage["relationship"])
        self.assertEqual(
            "9a59de81ac7c5ca0a42ff012bbade98b4be60978742b3c81d26f9024a3e9b408",
            researchctl.sha256_file(problem_dir / "v1-candidate.json"),
        )
        self.assertEqual(
            "7982aa908ce4e457e655fbe553db228f2ab9a09fdaa1202309df261d1bdc4a56",
            researchctl.sha256_file(problem_dir / "v1-candidate.md"),
        )
        self.assertEqual(
            "ed98af1e8ce8d6fd1494e6881ab47bb7c63eea2b1d1cf003f343f869eac39381",
            researchctl.sha256_file(
                problem_dir / "v1-history-alignment.json"
            ),
        )
        self.assertEqual(
            "11a25e60edbfad0ec53f92c038356150ee3685dff349b1869148abf54acc1784",
            researchctl.sha256_file(
                problem_dir / "v1-history-alignment.md"
            ),
        )
        self.assertEqual(
            lineage["predecessor_sha256"],
            researchctl.sha256_file(
                researchctl.resolve_root_path(lineage["predecessor_ref"])
            ),
        )
        self.assertEqual(
            lineage["predecessor_companion_sha256"],
            researchctl.sha256_file(
                researchctl.resolve_root_path(
                    lineage["predecessor_companion_ref"]
                )
            ),
        )
        self.assertEqual(
            lineage["predecessor_audit_sha256"],
            researchctl.sha256_file(
                researchctl.resolve_root_path(
                    lineage["predecessor_audit_ref"]
                )
            ),
        )
        self.assertEqual(
            lineage["predecessor_audit_companion_sha256"],
            researchctl.sha256_file(
                researchctl.resolve_root_path(
                    lineage["predecessor_audit_companion_ref"]
                )
            ),
        )

    def test_problem_contract_v2_requires_lineage_and_shared_basis(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v2-candidate.json"
        )
        problem = researchctl.load_json(path)
        self.assertEqual([], researchctl.validate_schema(problem, path))

        without_lineage = copy.deepcopy(problem)
        without_lineage.pop("lineage")
        self.assertIn(
            "'lineage' is a required property",
            "\n".join(researchctl.validate_schema(without_lineage, path)),
        )

        without_basis = copy.deepcopy(problem)
        without_basis.pop("shared_basis")
        self.assertIn(
            "'shared_basis' is a required property",
            "\n".join(researchctl.validate_schema(without_basis, path)),
        )

        without_bundle = copy.deepcopy(problem)
        without_bundle.pop("activation_bundle_ref")
        self.assertIn(
            "'activation_bundle_ref' is a required property",
            "\n".join(researchctl.validate_schema(without_bundle, path)),
        )

    def test_active_v2_requires_its_own_reviewed_inheritance_audit(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v2-candidate.json"
        )
        problem = researchctl.load_json(path)
        problem["status"] = "ACTIVE"
        problem["historical_inheritance_ref"] = problem["lineage"][
            "predecessor_audit_ref"
        ]
        errors = researchctl.check_problem_historical_inheritance(
            researchctl.DEFAULT_PROJECT,
            path,
            problem,
        )
        self.assertIn(
            "requires a current-version historical inheritance audit",
            "\n".join(errors),
        )
        self.assertIn(
            "current-version audit must have a distinct path",
            "\n".join(errors),
        )

    def test_v2_inheritance_audit_is_current_reviewed_and_complete(self):
        problem_dir = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
        )
        path = problem_dir / "v2-history-alignment.json"
        audit = researchctl.load_json(path)

        self.assertEqual("REVIEWED", audit["status"])
        self.assertEqual("READY", audit["activation_recommendation"])
        self.assertEqual(
            {
                "id": "PRB-JOINT-ACTION-FORMATION",
                "version": "v2",
            },
            audit["problem_ref"],
        )
        self.assertEqual(39, len(audit["capabilities"]))
        self.assertEqual(
            {"explicit": 22, "partial": 10, "absent": 7},
            audit["coverage_summary"],
        )
        self.assertTrue(
            all(
                "problem_coverage" in capability
                and "v1_coverage" not in capability
                for capability in audit["capabilities"]
            )
        )
        self.assertEqual(
            [],
            researchctl.validate_historical_inheritance(audit, path),
        )

    def test_relabelled_v1_audit_cannot_satisfy_v2(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v2-candidate.json"
        )
        problem = researchctl.load_json(path)
        predecessor_locator = problem["lineage"]["predecessor_audit_ref"]
        problem["historical_inheritance_ref"] = predecessor_locator
        predecessor_path = researchctl.resolve_root_path(predecessor_locator)
        original_load_json = researchctl.load_json

        def load_relabelled_audit(candidate_path):
            document = original_load_json(candidate_path)
            if candidate_path.resolve() == predecessor_path.resolve():
                document["problem_ref"] = {
                    "id": problem["id"],
                    "version": problem["version"],
                }
                document["status"] = "REVIEWED"
                document["activation_recommendation"] = "READY"
            return document

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_relabelled_audit,
        ):
            errors = researchctl.check_problem_historical_inheritance(
                researchctl.DEFAULT_PROJECT,
                path,
                problem,
            )

        joined = "\n".join(errors)
        self.assertIn("distinct path from predecessor audit", joined)
        self.assertIn("distinct id from predecessor audit", joined)
        self.assertIn("problem_coverage for every capability", joined)

    def test_v2_activation_bundle_freezes_exact_five_artifacts(self):
        problem_dir = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
        )
        path = problem_dir / "v2-candidate.json"
        problem = researchctl.load_json(path)
        bundle_path = researchctl.resolve_root_path(
            problem["activation_bundle_ref"]
        )
        bundle = researchctl.load_json(bundle_path)

        self.assertEqual([], researchctl.validate_schema(bundle, bundle_path))
        self.assertEqual(
            researchctl.PROBLEM_ACTIVATION_ARTIFACT_ROLES,
            {artifact["role"] for artifact in bundle["artifacts"]},
        )
        self.assertEqual(
            [],
            researchctl.verify_problem_activation_bundle(problem, path),
        )
        for artifact in bundle["artifacts"]:
            artifact_path = researchctl.resolve_root_path(artifact["path"])
            self.assertEqual(
                artifact["sha256"],
                researchctl.sha256_file(artifact_path),
            )

    def test_v2_activation_bundle_detects_any_artifact_drift(self):
        problem_dir = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
        )
        path = problem_dir / "v2-candidate.json"
        problem = researchctl.load_json(path)
        bundle = researchctl.load_json(
            researchctl.resolve_root_path(problem["activation_bundle_ref"])
        )
        original_sha256_file = researchctl.sha256_file

        for artifact in bundle["artifacts"]:
            tampered_path = researchctl.resolve_root_path(artifact["path"])

            def drifted_hash(candidate_path, target=tampered_path):
                if candidate_path.resolve() == target.resolve():
                    return "0" * 64
                return original_sha256_file(candidate_path)

            with self.subTest(role=artifact["role"]), mock.patch.object(
                researchctl,
                "sha256_file",
                side_effect=drifted_hash,
            ):
                self.assertIn(
                    "activation artifact SHA-256 differs",
                    "\n".join(
                        researchctl.verify_problem_activation_bundle(
                            problem,
                            path,
                        )
                    ),
                )

    def test_v2_activation_bundle_roles_require_distinct_files(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v2-candidate.json"
        )
        problem = researchctl.load_json(path)
        bundle_path = researchctl.resolve_root_path(
            problem["activation_bundle_ref"]
        )
        bundle = researchctl.load_json(bundle_path)
        duplicate = copy.deepcopy(bundle)
        duplicate["artifacts"][1]["path"] = duplicate["artifacts"][0][
            "path"
        ]
        duplicate["artifacts"][1]["sha256"] = duplicate["artifacts"][0][
            "sha256"
        ]
        original_load_json = researchctl.load_json

        def load_duplicate_bundle(candidate_path):
            if candidate_path.resolve() == bundle_path.resolve():
                return copy.deepcopy(duplicate)
            return original_load_json(candidate_path)

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_duplicate_bundle,
        ):
            self.assertIn(
                "must resolve to five distinct files",
                "\n".join(
                    researchctl.verify_problem_activation_bundle(
                        problem,
                        path,
                    )
                ),
            )

    def test_v2_activation_decision_must_bind_bundle_hash(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "problem"
            / "v2-candidate.json"
        )
        problem = researchctl.load_json(path)
        bundle_path = researchctl.resolve_root_path(
            problem["activation_bundle_ref"]
        )
        decision_id = "DEC-TEST-V2-ACTIVATION"
        target = {
            "id": problem["id"],
            "version": problem["version"],
            "source_path": researchctl.relative(path),
            "source_sha256": researchctl.sha256_file(path),
        }

        def allowed(candidate_target):
            decision = {
                "decision_id": decision_id,
                "status": "APPROVED",
                "decided_by": "USER",
                "actions": ["ACTIVATE_PROBLEM"],
                "target": candidate_target,
            }
            with mock.patch.object(
                researchctl,
                "read_decisions",
                return_value={decision_id: decision},
            ):
                return researchctl.decision_allows_promotion(
                    decision_id,
                    "ACTIVATE_PROBLEM",
                    problem,
                    path,
                )

        self.assertFalse(allowed(target))
        exact = {
            **target,
            "activation_bundle_path": researchctl.relative(bundle_path),
            "activation_bundle_sha256": researchctl.sha256_file(bundle_path),
        }
        self.assertTrue(allowed(exact))
        stale = {**exact, "activation_bundle_sha256": "0" * 64}
        self.assertFalse(allowed(stale))

    def test_v2_problem_receipt_must_preserve_bundle_binding(self):
        researchctl.RUNTIME.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=researchctl.RUNTIME
        ) as temporary:
            project = Path(temporary) / "receipt-project"
            for name in ("problem", "lines", "promotions"):
                (project / name).mkdir(parents=True, exist_ok=True)
            source_path = (
                ROOT
                / "research"
                / "projects"
                / "joint-action-formation"
                / "problem"
                / "v2-candidate.json"
            )
            candidate = researchctl.load_json(source_path)
            candidate_path = project / "problem" / "v2-candidate.json"
            researchctl.write_json(candidate_path, candidate)
            target_path = project / "problem" / "v2.json"
            decision_id = "DEC-TEST-V2-RECEIPT"
            active = researchctl.expected_promoted_document(
                candidate,
                "problem",
                decision_id,
                target_path,
            )
            researchctl.write_json(target_path, active)
            active_companion = researchctl.resolve_root_path(
                active["companion_markdown"]
            )
            researchctl.atomic_write_text(
                active_companion,
                researchctl.render_problem_active_companion(
                    candidate,
                    candidate_path,
                    decision_id,
                ),
            )
            receipt_path = project / "promotions" / "v2.json"
            receipt = {
                "promotion_id": "PROM-TEST-V2",
                "target_kind": "problem",
                "target_id": candidate["id"],
                "target_version": candidate["version"],
                "decision_id": decision_id,
                "promoted_at": researchctl.utc_now(),
                "source_candidate": researchctl.relative(candidate_path),
                "source_sha256": researchctl.sha256_file(candidate_path),
                "target": researchctl.relative(target_path),
                "target_sha256": researchctl.sha256_file(target_path),
                "target_companion": researchctl.relative(
                    active_companion
                ),
                "target_companion_sha256": researchctl.sha256_file(
                    active_companion
                ),
            }
            researchctl.write_json(receipt_path, receipt)

            with mock.patch.object(
                researchctl,
                "decision_allows_promotion",
                return_value=True,
            ):
                self.assertIn(
                    "does not bind the current activation bundle",
                    "\n".join(
                        researchctl.check_exact_promotion_receipt(
                            target_path,
                            active,
                            "problem",
                        )
                    ),
                )
                bundle_path = researchctl.resolve_root_path(
                    candidate["activation_bundle_ref"]
                )
                receipt.update(
                    {
                        "activation_bundle_path": researchctl.relative(
                            bundle_path
                        ),
                        "activation_bundle_sha256": researchctl.sha256_file(
                            bundle_path
                        ),
                    }
                )
                researchctl.write_json(receipt_path, receipt)
                self.assertEqual(
                    [],
                    researchctl.check_exact_promotion_receipt(
                        target_path,
                        active,
                        "problem",
                    ),
                )
                original_companion = active_companion.read_text(
                    encoding="utf-8"
                )
                researchctl.atomic_write_text(
                    active_companion,
                    original_companion
                    + "\n静默改写，但保留 ID、version 与 ACTIVE 标记。\n",
                )
                receipt["target_companion_sha256"] = (
                    researchctl.sha256_file(active_companion)
                )
                researchctl.write_json(receipt_path, receipt)
                self.assertIn(
                    "ACTIVE companion is not the deterministic projection",
                    "\n".join(
                        researchctl.check_exact_promotion_receipt(
                            target_path,
                            active,
                            "problem",
                        )
                    ),
                )

    def test_v2_problem_promotion_resumes_before_now_update(self):
        researchctl.RUNTIME.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=researchctl.RUNTIME
        ) as temporary:
            project = Path(temporary) / "problem-promotion-project"
            for name in ("problem", "lines"):
                (project / name).mkdir(parents=True, exist_ok=True)
            source_path = (
                ROOT
                / "research"
                / "projects"
                / "joint-action-formation"
                / "problem"
                / "v2-candidate.json"
            )
            candidate = researchctl.load_json(source_path)
            candidate_path = project / "problem" / "v2-candidate.json"
            researchctl.write_json(candidate_path, candidate)
            decision_id = "DEC-TEST-V2-RESUME"
            args = argparse.Namespace(
                project=researchctl.relative(project),
                candidate=researchctl.relative(candidate_path),
                target="problem",
                decision_id=decision_id,
            )
            initial_state = {
                "candidate_problem": researchctl.relative(candidate_path),
                "active_problem": None,
                "lines_by_problem": {},
                "active_lines": [],
                "pending_user_decisions": [
                    f"审阅、重写或激活 {researchctl.relative(candidate_path)}"
                ],
            }
            write_state = mock.Mock(
                side_effect=[
                    researchctl.ResearchError(
                        "simulated interruption before NOW commit"
                    ),
                    None,
                ]
            )
            with (
                mock.patch.object(
                    researchctl,
                    "verify_problem_activation_bundle",
                    return_value=[],
                ),
                mock.patch.object(
                    researchctl,
                    "decision_allows_promotion",
                    return_value=True,
                ),
                mock.patch.object(
                    researchctl,
                    "check_problem_lineage",
                    return_value=[],
                ),
                mock.patch.object(
                    researchctl,
                    "check_problem_historical_inheritance",
                    return_value=[],
                ),
                mock.patch.object(
                    researchctl,
                    "read_state",
                    side_effect=lambda: copy.deepcopy(initial_state),
                ),
                mock.patch.object(
                    researchctl,
                    "write_state",
                    write_state,
                ),
            ):
                with self.assertRaisesRegex(
                    researchctl.ResearchError,
                    "simulated interruption",
                ):
                    researchctl.promote(args)
                active_path = project / "problem" / "v2.json"
                active_companion = project / "problem" / "v2.md"
                receipt_path = (
                    project
                    / "promotions"
                    / f"{candidate['id']}-{decision_id}.json"
                )
                self.assertTrue(active_path.is_file())
                self.assertTrue(active_companion.is_file())
                self.assertTrue(receipt_path.is_file())

                self.assertEqual(0, researchctl.promote(args))
                self.assertEqual(2, write_state.call_count)
                self.assertEqual(
                    [],
                    researchctl.check_exact_promotion_receipt(
                        active_path,
                        researchctl.load_json(active_path),
                        "problem",
                    ),
                )

    def test_now_history_alignment_tracks_current_problem(self):
        state = researchctl.read_state()
        problem_path = researchctl.resolve_root_path(
            state["candidate_problem"]
        )
        problem = researchctl.load_json(problem_path)
        self.assertEqual(
            problem["historical_inheritance_ref"],
            state["history_alignment"],
        )


    def test_problem_version_exactly_filters_active_lines(self):
        project = researchctl.DEFAULT_PROJECT
        v0 = researchctl.load_json(project / "problem" / "v0.json")
        v2 = researchctl.load_json(project / "problem" / "v2-candidate.json")

        v0_lines = researchctl.select_active_lines(project, v0)
        self.assertEqual(7, len(v0_lines))
        self.assertEqual(
            ["LINE-01-DISCOVERY-BOUNDARY"],
            [
                line["id"]
                for _, line in researchctl.select_active_lines(
                    project,
                    v0,
                    ["LINE-01-DISCOVERY-BOUNDARY"],
                )
            ],
        )
        self.assertEqual([], researchctl.select_active_lines(project, v2))
        with self.assertRaises(researchctl.ResearchError):
            researchctl.select_active_lines(
                project,
                v2,
                ["LINE-01-DISCOVERY-BOUNDARY"],
            )

    def test_v2_line_requires_bounded_target_review_and_outcome_policy(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "lines"
            / "01-nac.json"
        )
        line = researchctl.load_json(path)
        self.assertEqual([], researchctl.validate_schema(line, path))
        for field in ("research_target", "prior_solution_review", "outcome_policy"):
            with self.subTest(field=field):
                invalid = copy.deepcopy(line)
                invalid.pop(field)
                self.assertIn(
                    f"'{field}' is a required property",
                    "\n".join(researchctl.validate_schema(invalid, path)),
                )
        self.assertEqual(
            {
                "MC-NAC-PREFIX",
                "MC-NAC-DIRECTION",
                "MC-NAC-SELF-DESCRIPTION",
                "MC-NAC-MIGRATION",
            },
            set(line["outcome_policy"]["unaffected_claim_ids"]),
        )

    def test_nac_profile_is_active_research_but_not_validated(self):
        path = (
            ROOT
            / "research"
            / "projects"
            / "joint-action-formation"
            / "mechanisms"
            / "nac.json"
        )
        profile = researchctl.load_json(path)
        self.assertEqual([], researchctl.validate_schema(profile, path))
        self.assertEqual("ACTIVE_RESEARCH", profile["research_status"])
        self.assertNotEqual("VALIDATED_SCOPED", profile["research_status"])
        self.assertTrue(
            researchctl.decision_allows(
                profile["decision_ref"],
                "CONTINUE_SCOPED_MECHANISM_RESEARCH",
            )
        )
        self.assertFalse(
            researchctl.decision_allows(
                profile["decision_ref"],
                "VALIDATE_SCOPED_MECHANISM",
            )
        )
        self.assertFalse(
            researchctl.decision_allows(
                profile["decision_ref"],
                "SUPERSEDE_SCOPED_MECHANISM",
            )
        )
        self.assertFalse(
            researchctl.decision_allows_mechanism_transition(
                profile["decision_ref"],
                "VALIDATE_SCOPED_MECHANISM",
                profile,
                path,
            )
        )
        self.assertTrue(
            researchctl.decision_allows_mechanism_registration(
                profile["decision_ref"],
                profile,
                path,
            )
        )
        rewritten = copy.deepcopy(profile)
        rewritten["origin_problem"] += " Silent semantic rewrite."
        self.assertFalse(
            researchctl.decision_allows_mechanism_registration(
                rewritten["decision_ref"],
                rewritten,
                path,
            )
        )
        non_responsibilities = "\n".join(profile["non_responsibilities"])
        self.assertIn("授权", non_responsibilities)
        self.assertIn("Effect", non_responsibilities)
        self.assertGreaterEqual(len(profile["scoped_claims"]), 5)
        self.assertEqual([], researchctl.check_companion(profile, path))
        wrong_companion_hash = copy.deepcopy(profile)
        wrong_companion_hash["companion_sha256"] = "0" * 64
        self.assertIn(
            "companion SHA-256 differs",
            "\n".join(
                researchctl.check_companion(
                    wrong_companion_hash,
                    path,
                )
            ),
        )

    def test_v2_result_cannot_update_claim_outside_line_scope(self):
        project = researchctl.DEFAULT_PROJECT
        line = researchctl.load_json(project / "lines" / "01-nac.json")
        problem = researchctl.load_json(project / "problem" / "v2-candidate.json")
        scenario = researchctl.load_json(
            project / "scenarios" / "problem-definition-archive-v0.json"
        )
        bundle = {
            "run_id": "BATCH-TEST-SCOPE-LINE-01-NAC",
            "batch_id": "BATCH-TEST-SCOPE",
            "problem": problem,
            "scenario": scenario,
            "line": line,
            "input_hash": "f" * 64,
            "sources": [
                {
                    "locator": (
                        "research/projects/a2a-reconstruction/04_audit/"
                        "native_lines/01_discovery_and_boundary.md"
                    )
                }
            ],
        }
        result = researchctl.mock_result(bundle)
        self.assertEqual("2.0", result["schema_version"])
        self.assertEqual(["E-H1-PRIME"], result["hypothesis_ids"])
        self.assertEqual(["MC-NAC-ANCHOR"], result["tested_claim_ids"])
        self.assertEqual([], result["scoped_claim_updates"])
        self.assertEqual([], researchctl.validate_result_semantics(result, bundle))

        escaped = copy.deepcopy(result)
        escaped["scoped_claim_updates"] = [
            {
                "claim_id": "MC-OTHER-LINE",
                "proposed_status": "NARROWED",
                "rationale": "This deliberately escapes the declared mechanism scope.",
                "evidence_refs": [],
            }
        ]
        self.assertIn(
            "result updates claims outside line scope",
            "\n".join(researchctl.validate_result_semantics(escaped, bundle)),
        )

        incomplete = copy.deepcopy(result)
        incomplete["unaffected_claim_ids"].pop()
        self.assertIn(
            "result does not classify every scoped claim",
            "\n".join(researchctl.validate_result_semantics(incomplete, bundle)),
        )

        wrong_focus = copy.deepcopy(result)
        wrong_focus["hypothesis_ids"] = ["H2"]
        self.assertIn(
            "result hypothesis_ids differ from frozen run focus",
            "\n".join(researchctl.validate_result_semantics(wrong_focus, bundle)),
        )

        failed_but_completed = copy.deepcopy(result)
        failed_but_completed["status"] = "FAILED"
        failed_but_completed["hypothesis_outcomes"][0] = {
            "hypothesis_id": "E-H1-PRIME",
            "outcome": "COMPLETED",
            "rationale": (
                "This result falsely marks a failed run as completed evidence."
            ),
            "evidence_refs": [line["source_allowlist"][0]],
        }
        self.assertIn(
            "FAILED or REFUSED result cannot complete",
            "\n".join(
                researchctl.validate_result_semantics(
                    failed_but_completed,
                    bundle,
                )
            ),
        )
        failed_not_run = copy.deepcopy(result)
        failed_not_run["status"] = "FAILED"
        failed_not_run["hypothesis_outcomes"][0]["outcome"] = "NOT_RUN"
        self.assertEqual(
            [],
            researchctl.validate_result_semantics(failed_not_run, bundle),
        )

    def test_candidate_problem_blocks_implicit_fallback_to_seed(self):
        state = researchctl.read_state()
        self.assertIsNone(state["active_problem"])
        self.assertTrue(state["candidate_problem"])
        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "pass --problem explicitly",
        ):
            researchctl.select_problem(researchctl.DEFAULT_PROJECT, state)

    def test_nac_hypotheses_separate_core_from_companion_mechanisms(self):
        profile = researchctl.load_json(
            researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
        )
        claims = {
            claim["id"]: (
                claim["identity_criticality"],
                claim["portability"],
            )
            for claim in profile["scoped_claims"]
        }
        self.assertEqual(
            ("IDENTITY_CORE", "SUBSTRATE_BOUND"),
            claims["MC-NAC-ANCHOR"],
        )
        self.assertEqual(
            ("IDENTITY_CORE", "PORTABLE"),
            claims["MC-NAC-PREFIX"],
        )
        hypotheses = {item["id"]: item for item in profile["hypothesis_map"]}
        self.assertEqual("PRE_REGISTERED", hypotheses["E-H1-PRIME"]["provenance_status"])
        self.assertIn("H1", hypotheses["E-H1-PRIME"]["aliases"])
        self.assertNotIn("H1", hypotheses)
        self.assertEqual("M3_ENVELOPE_ROUTING", hypotheses["H3"]["primary_owner"])
        self.assertEqual([], hypotheses["H3"]["scoped_claim_ids"])
        claim_capabilities = {
            item["id"]: item["capability_ids"]
            for item in profile["scoped_claims"]
        }
        self.assertEqual(
            ["CAP-DISC-005"],
            claim_capabilities["MC-NAC-DIRECTION"],
        )
        self.assertEqual(
            [],
            claim_capabilities["MC-NAC-SELF-DESCRIPTION"],
        )
        self.assertEqual([], claim_capabilities["MC-NAC-MIGRATION"])

    def test_mechanism_profile_schema_is_not_nac_shaped(self):
        profile = copy.deepcopy(
            researchctl.load_json(
                researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
            )
        )
        profile["id"] = "MEC-GENERIC-EXAMPLE"
        profile["research_status"] = "DRAFT"
        profile.pop("decision_ref", None)
        profile["scoped_claims"] = [
            {
                "id": "MC-GENERIC-RESULT",
                "statement": "A generic completed mechanism claim remains representable.",
                "identity_criticality": "NOT_IDENTITY",
                "portability": "PORTABLE",
                "capability_ids": ["CAP-DISC-003"],
                "evidence_status": "HISTORICAL_DESIGN",
                "status_evidence": [],
                "falsifier": "A bounded replay fails under the declared assumptions.",
            }
        ]
        profile["hypothesis_map"] = [
            {
                "id": "EXP-COMPLETED-ALPHA",
                "aliases": ["alpha"],
                "provenance_status": "PROPOSED",
                "execution_status": "UNRUN",
                "execution_evidence": [],
                "primary_owner": "GENERIC_MECHANISM",
                "companion_owners": [],
                "scoped_claim_ids": ["MC-GENERIC-RESULT"],
                "result_scope": "Future mechanisms are not forced into NAC H-number conventions.",
            }
        ]
        path = researchctl.DEFAULT_PROJECT / "mechanisms" / "generic-test.json"
        self.assertEqual([], researchctl.validate_schema(profile, path))

    def test_mechanism_evidence_status_requires_finalized_bindings(self):
        path = researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
        profile = researchctl.load_json(path)

        unsupported_claim = copy.deepcopy(profile)
        unsupported_claim["scoped_claims"][0]["evidence_status"] = (
            "SUPPORTED_LOCAL"
        )
        self.assertIn(
            "should be non-empty",
            "\n".join(researchctl.validate_schema(unsupported_claim, path)),
        )

        unbound_execution = copy.deepcopy(profile)
        unbound_execution["hypothesis_map"][0]["execution_status"] = (
            "COMPLETED"
        )
        self.assertIn(
            "should be non-empty",
            "\n".join(researchctl.validate_schema(unbound_execution, path)),
        )

        runtime_parent = ROOT / ".research-runtime"
        runtime_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime_parent) as temporary:
            project = Path(temporary)
            (project / "candidates" / "BATCH-FAKE").mkdir(parents=True)
            mutated = copy.deepcopy(profile)
            claim = mutated["scoped_claims"][0]
            hypothesis = mutated["hypothesis_map"][0]
            fake_binding = {
                "result_path": researchctl.relative(
                    project / "candidates" / "BATCH-FAKE" / "LINE-FAKE.json"
                ),
                "result_sha256": "a" * 64,
                "evidence_receipt_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "evidence-LINE-FAKE.json"
                ),
                "evidence_receipt_sha256": "c" * 64,
                "finalization_manifest_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "finalization-manifest.json"
                ),
                "finalization_manifest_sha256": "d" * 64,
                "plan_snapshot_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "plan-snapshot.json"
                ),
                "plan_snapshot_sha256": "e" * 64,
                "plan_seal_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "plan-seal.json"
                ),
                "plan_seal_sha256": "1" * 64,
                "run_manifest_snapshot_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "run-manifest-LINE-FAKE.json"
                ),
                "run_manifest_snapshot_sha256": "f" * 64,
                "input_snapshot_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "input-LINE-FAKE.json"
                ),
                "input_snapshot_sha256": "2" * 64,
                "raw_result_snapshot_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "raw-result-LINE-FAKE.json"
                ),
                "raw_result_snapshot_sha256": "3" * 64,
                "events_snapshot_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "events-LINE-FAKE.jsonl"
                ),
                "events_snapshot_sha256": "4" * 64,
                "completion_seal_snapshot_path": researchctl.relative(
                    project
                    / "candidates"
                    / "BATCH-FAKE"
                    / "completion-seal-LINE-FAKE.json"
                ),
                "completion_seal_snapshot_sha256": "5" * 64,
                "run_id": "RUN-FAKE",
                "input_hash": "b" * 64,
                "definition_sha256": researchctl.claim_definition_hash(claim),
            }
            claim["evidence_status"] = "SUPPORTED_LOCAL"
            claim["status_evidence"] = [fake_binding]
            hypothesis["provenance_status"] = "EMPIRICAL"
            hypothesis["execution_status"] = "COMPLETED"
            hypothesis_binding = copy.deepcopy(fake_binding)
            hypothesis_binding["definition_sha256"] = (
                researchctl.hypothesis_definition_hash(hypothesis)
            )
            hypothesis["execution_evidence"] = [hypothesis_binding]
            profile_path = project / "nac-mutated.json"
            researchctl.write_json(profile_path, mutated)
            errors = researchctl.check_mechanism_semantics(
                project,
                [
                    researchctl.DEFAULT_PROJECT
                    / "problem"
                    / "v2-candidate.json"
                ],
                [researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"],
                [profile_path],
            )
        joined = "\n".join(errors)
        self.assertIn("missing finalized artifacts", joined)
        self.assertIn("UPDATE_SCOPED_MECHANISM_EVIDENCE", joined)

    def test_validated_scope_cannot_expand_one_claim_to_all_capabilities(self):
        path = researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
        profile = researchctl.load_json(path)
        promoted = copy.deepcopy(profile)
        promoted["research_status"] = "VALIDATED_SCOPED"
        promoted["validated_scope"] = {
            "claim_ids": ["MC-NAC-ANCHOR"],
            "hypothesis_ids": ["E-H1-PRIME"],
            "capability_ids": list(promoted["capability_ids"]),
        }
        # The canonical file remains ACTIVE_RESEARCH; apply the mutation only
        # through the semantic loader so the test attacks promotion semantics.
        original_load_json = researchctl.load_json

        def load_promoted(candidate_path):
            if candidate_path == path:
                return copy.deepcopy(promoted)
            return original_load_json(candidate_path)

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_promoted,
        ):
            errors = researchctl.check_mechanism_semantics(
                researchctl.DEFAULT_PROJECT,
                [
                    researchctl.DEFAULT_PROJECT
                    / "problem"
                    / "v2-candidate.json"
                ],
                [researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"],
                [path],
            )
        joined = "\n".join(errors)
        self.assertIn(
            "validated_scope capability_ids must exactly equal",
            joined,
        )
        self.assertIn("validated hypothesis is not COMPLETED", joined)
        self.assertIn("VALIDATE_SCOPED_MECHANISM", joined)

    def test_validated_scope_cannot_include_companion_only_hypothesis(self):
        path = researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
        promoted = copy.deepcopy(researchctl.load_json(path))
        promoted["research_status"] = "VALIDATED_SCOPED"
        promoted["validated_scope"] = {
            "claim_ids": ["MC-NAC-ANCHOR"],
            "hypothesis_ids": ["E-H1-PRIME", "H3"],
            "capability_ids": ["CAP-DISC-003"],
        }
        original_load_json = researchctl.load_json

        def load_promoted(candidate_path):
            if candidate_path == path:
                return copy.deepcopy(promoted)
            return original_load_json(candidate_path)

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_promoted,
        ):
            errors = researchctl.check_mechanism_semantics(
                researchctl.DEFAULT_PROJECT,
                [
                    researchctl.DEFAULT_PROJECT
                    / "problem"
                    / "v2-candidate.json"
                ],
                [researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"],
                [path],
            )
        self.assertIn(
            "validated hypothesis H3 does not exclusively cover",
            "\n".join(errors),
        )

    def test_adverse_scope_must_preserve_every_unaffected_claim(self):
        path = researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
        rebased = copy.deepcopy(researchctl.load_json(path))
        rebased["research_status"] = "REBASE_REQUIRED"
        rebased["validated_scope"] = None
        rebased["adverse_scope"] = {
            "claim_ids": ["MC-NAC-ANCHOR"],
            "hypothesis_ids": ["E-H1-PRIME"],
            "capability_ids": ["CAP-DISC-003"],
            "unaffected_claim_ids": ["MC-NAC-PREFIX"],
        }
        original_load_json = researchctl.load_json

        def load_rebased(candidate_path):
            if candidate_path == path:
                return copy.deepcopy(rebased)
            return original_load_json(candidate_path)

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_rebased,
        ):
            errors = researchctl.check_mechanism_semantics(
                researchctl.DEFAULT_PROJECT,
                [
                    researchctl.DEFAULT_PROJECT
                    / "problem"
                    / "v2-candidate.json"
                ],
                [researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"],
                [path],
            )
        self.assertIn(
            "adverse_scope must enumerate every unaffected mechanism claim",
            "\n".join(errors),
        )
        self.assertIn(
            "adverse claim lacks REFUTED evidence state",
            "\n".join(errors),
        )
        self.assertIn(
            "adverse hypothesis lacks an EMPIRICAL INVALIDATED",
            "\n".join(errors),
        )

    def test_scoped_blind_review_preserves_conflicting_units(self):
        bundle = {
            "review_scope": "SCOPED_MECHANISM",
            "anonymous_returns": [
                {
                    "anonymous_return_id": "R01",
                    "bounded_target": {
                        "tested_claim_ids": ["MC-SHARED"],
                        "hypothesis_ids": ["H-ONE"],
                        "mechanism": {
                            "selected_claims": [{"id": "MC-SHARED"}],
                            "selected_hypotheses": [
                                {
                                    "id": "H-ONE",
                                    "scoped_claim_ids": ["MC-SHARED"],
                                }
                            ]
                        },
                    },
                },
                {
                    "anonymous_return_id": "R02",
                    "bounded_target": {
                        "tested_claim_ids": ["MC-SHARED"],
                        "hypothesis_ids": ["H-TWO", "H-ZERO"],
                        "mechanism": {
                            "selected_claims": [{"id": "MC-SHARED"}],
                            "selected_hypotheses": [
                                {
                                    "id": "H-TWO",
                                    "scoped_claim_ids": ["MC-SHARED"],
                                },
                                {
                                    "id": "H-ZERO",
                                    "scoped_claim_ids": [],
                                },
                            ]
                        },
                    },
                },
            ],
        }
        review = {
            "schema_version": "2.0",
            "kind": "BlindReview",
            "review_scope": "SCOPED_MECHANISM",
            "status": "COMPLETED",
            "strongest_counterarguments": [
                "The strongest alternative can explain one bounded return."
            ],
            "unsupported_inferences": [],
            "erased_distinctions": [],
            "missing_evidence": [],
            "baseline_challenges": [],
            "recommendation": "KEEP_COMPETING_RESULTS",
            "scoped_assessments": [
                {
                    "anonymous_return_id": "R01",
                    "hypothesis_id": "H-ONE",
                    "claim_id": "MC-SHARED",
                    "assessment": "SUPPORTED_WITHIN_SCOPE",
                    "rationale": "This return supports only its own frozen unit.",
                },
                {
                    "anonymous_return_id": "R02",
                    "hypothesis_id": "H-TWO",
                    "claim_id": "MC-SHARED",
                    "assessment": "REFUTE_CANDIDATE",
                    "rationale": "This separate hypothesis produces the opposite result.",
                },
                {
                    "anonymous_return_id": "R02",
                    "hypothesis_id": "H-ZERO",
                    "claim_id": None,
                    "assessment": "UNAFFECTED",
                    "rationale": "The hypothesis has no scoped mechanism claim to update.",
                },
            ],
            "cannot_conclude": [
                "The review cannot generalize beyond the frozen units."
            ],
        }
        review_path = researchctl.RUNTIME / "blind-review.json"
        self.assertEqual(
            [],
            researchctl.validate_blind_review_semantics(
                review,
                bundle,
                review_path,
            ),
        )

        missing = copy.deepcopy(review)
        missing["scoped_assessments"].pop()
        self.assertIn(
            "omits frozen scoped units",
            "\n".join(
                researchctl.validate_blind_review_semantics(
                    missing,
                    bundle,
                    review_path,
                )
            ),
        )
        duplicate = copy.deepcopy(review)
        duplicate["scoped_assessments"].append(
            copy.deepcopy(duplicate["scoped_assessments"][0])
        )
        self.assertIn(
            "repeats an exact",
            "\n".join(
                researchctl.validate_blind_review_semantics(
                    duplicate,
                    bundle,
                    review_path,
                )
            ),
        )

    def test_problem_frame_review_does_not_require_mechanism_units(self):
        review = {
            "schema_version": "2.0",
            "kind": "BlindReview",
            "review_scope": "PROBLEM_FRAME",
            "status": "INCONCLUSIVE",
            "strongest_counterarguments": [
                "The frame may still omit one important historical distinction."
            ],
            "unsupported_inferences": [],
            "erased_distinctions": [],
            "missing_evidence": [],
            "baseline_challenges": [],
            "recommendation": "INSUFFICIENT_EVIDENCE",
            "cannot_conclude": [
                "The problem cannot yet be activated from this review."
            ],
        }
        self.assertEqual(
            [],
            researchctl.validate_blind_review_semantics(
                review,
                {"review_scope": "PROBLEM_FRAME"},
                researchctl.RUNTIME / "problem-review.json",
            ),
        )

    def test_zero_claim_hypothesis_keeps_a_blind_review_unit(self):
        profile_path = (
            researchctl.DEFAULT_PROJECT / "mechanisms" / "nac.json"
        )
        profile = researchctl.load_json(profile_path)
        line = copy.deepcopy(
            researchctl.load_json(
                researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"
            )
        )
        line["research_target"]["hypothesis_ids"] = ["H3"]
        line["research_target"]["scoped_claim_ids"] = []
        self.assertEqual(
            [],
            researchctl.validate_schema(
                line,
                researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json",
            ),
        )
        bundle = {
            "research_focus": {
                "mechanism_ref": researchctl.relative(profile_path),
                "hypothesis_ids": ["H3"],
                "tested_claim_ids": [],
            },
            "mechanism_profiles": [
                {
                    "locator": researchctl.relative(profile_path),
                    "profile": profile,
                }
            ],
            "line": line,
        }
        target = researchctl.build_bounded_review_target(bundle)
        self.assertIsNotNone(target)
        review_bundle = {
            "review_scope": "SCOPED_MECHANISM",
            "anonymous_returns": [
                {
                    "anonymous_return_id": "R01",
                    "bounded_target": target,
                }
            ],
        }
        self.assertEqual(
            {("R01", "H3", None)},
            researchctl.expected_scoped_review_units(review_bundle),
        )

    def test_v2_active_problem_cannot_reuse_candidate_companion(self):
        path = researchctl.DEFAULT_PROJECT / "problem" / "v2-candidate.json"
        active = copy.deepcopy(researchctl.load_json(path))
        active["status"] = "ACTIVE"
        self.assertIn(
            "companion does not declare 状态：`ACTIVE`",
            "\n".join(researchctl.check_companion(active, path)),
        )

    def test_gap_confirmed_requires_real_allowlisted_solution_review(self):
        runtime_parent = ROOT / ".research-runtime"
        runtime_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime_parent) as temporary:
            line = copy.deepcopy(
                researchctl.load_json(
                    researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"
                )
            )
            line["id"] = "LINE-99-NEW-GAP"
            line["research_target"] = {
                "kind": "NEW_GAP",
                "mechanism_ref": None,
                "scoped_claim_ids": ["MC-NEW-GAP"],
                "applicable_assumptions": ["WORLD-OPEN-ACTION-SPACE"],
                "non_claims": ["Does not claim a complete relation lifecycle."],
            }
            line["prior_solution_review"] = {
                "checked_historical_refs": [],
                "checked_existing_solution_refs": [],
                "disposition": "GAP_CONFIRMED",
                "uncovered_requirement": "No existing solution covers the claimed gap.",
                "coverage_findings": [],
            }
            line_path = Path(temporary) / "new-gap.json"
            researchctl.write_json(line_path, line)
            problems = sorted(
                (researchctl.DEFAULT_PROJECT / "problem").glob("*.json")
            )
            errors = researchctl.check_problem_scenario_line_semantics(
                Path(temporary),
                problems,
                [],
                [line_path],
            )
        self.assertIn(
            "GAP_CONFIRMED requires non-empty historical and existing-solution",
            "\n".join(errors),
        )

    def test_active_v2_line_cannot_keep_solution_review_unresolved(self):
        path = researchctl.DEFAULT_PROJECT / "lines" / "01-nac.json"
        active = copy.deepcopy(researchctl.load_json(path))
        active["status"] = "ACTIVE"
        original_load_json = researchctl.load_json

        def load_active(candidate_path):
            if candidate_path == path:
                return copy.deepcopy(active)
            return original_load_json(candidate_path)

        with mock.patch.object(
            researchctl,
            "load_json",
            side_effect=load_active,
        ):
            errors = researchctl.check_problem_scenario_line_semantics(
                researchctl.DEFAULT_PROJECT,
                sorted(
                    (
                        researchctl.DEFAULT_PROJECT / "problem"
                    ).glob("*.json")
                ),
                sorted(
                    (
                        researchctl.DEFAULT_PROJECT / "scenarios"
                    ).glob("*.json")
                ),
                [path],
            )
        self.assertIn(
            "ACTIVE LineContract 2.0 requires a resolved "
            "prior_solution_review disposition",
            "\n".join(errors),
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
            problem="v0",
            scenario=None,
            mode="mock",
            batch_id=batch_id,
            max_parallel=3,
        )
        self.assertEqual(0, researchctl.plan_batch(args))
        return researchctl.RUNTIME / batch_id / "plan.json"

    def reseal_plan(self, plan_path, plan):
        """Test helper for deliberate pre-run plan construction."""
        plan["plan_fingerprint"] = researchctl.compute_plan_fingerprint(plan)
        for run in plan["runs"]:
            manifest_path = (
                researchctl.resolve_root_path(run["run_dir"])
                / "manifest.json"
            )
            manifest = researchctl.load_json(manifest_path)
            manifest["plan_fingerprint"] = plan["plan_fingerprint"]
            researchctl.write_json(manifest_path, manifest)
        researchctl.write_json(plan_path, plan)
        seal_path = plan_path.parent / "plan-seal.json"
        if seal_path.exists():
            seal_path.unlink()
        researchctl.write_controller_seal(
            seal_path,
            researchctl.plan_seal_document(plan),
        )
        return plan

    def finalize_mock_candidate(self, batch_id, project_name):
        """Create one isolated, sealed candidate packet for tamper tests."""
        plan_path = self.plan(batch_id)
        plan = researchctl.load_plan(plan_path)
        project = researchctl.RUNTIME / project_name
        project.mkdir(parents=True)
        plan["project"] = researchctl.relative(project)
        plan["protected_hashes"] = researchctl.hash_paths(
            researchctl.protected_paths(project)
        )
        self.reseal_plan(plan_path, plan)
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)
        self.assertEqual(
            0,
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            ),
        )
        return (
            plan,
            project,
            project / "candidates" / plan["batch_id"],
        )

    def test_atomic_json_publish_failure_preserves_existing_bytes_and_retries(
        self,
    ):
        plan_path = self.plan("BATCH-TEST-ATOMIC-PUBLISH")
        plan = researchctl.load_json(plan_path)
        manifest_path = (
            researchctl.resolve_root_path(plan["runs"][0]["run_dir"])
            / "manifest.json"
        )

        for target in (plan_path, manifest_path):
            with self.subTest(target=target.name):
                original_bytes = target.read_bytes()
                replacement = researchctl.load_json(target)
                replacement["atomic_publish_test_marker"] = target.name

                with mock.patch.object(
                    researchctl.os,
                    "replace",
                    side_effect=OSError(
                        "simulated atomic publish interruption"
                    ),
                ):
                    with self.assertRaisesRegex(
                        OSError,
                        "simulated atomic publish interruption",
                    ):
                        researchctl.write_json(target, replacement)

                self.assertEqual(original_bytes, target.read_bytes())
                self.assertEqual(
                    [],
                    list(
                        target.parent.glob(
                            f".{target.name}.*.tmp"
                        )
                    ),
                )
                self.assertNotIn(
                    "atomic_publish_test_marker",
                    researchctl.load_json(target),
                )

                researchctl.write_json(target, replacement)
                self.assertEqual(
                    replacement,
                    researchctl.load_json(target),
                )

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

    def test_resume_recovers_last_attempt_running_residue(self):
        plan_path = self.plan("BATCH-TEST-INTERRUPTED-LAST-ATTEMPT")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        manifest_path = run_dir / "manifest.json"
        manifest = researchctl.load_json(manifest_path)
        max_attempts = researchctl.load_json(
            run_dir / "input.json"
        )["line"]["budget"]["max_attempts"]
        manifest["status"] = "RUNNING"
        manifest["attempt"] = max_attempts
        manifest["started_at"] = researchctl.utc_now()
        researchctl.write_json(manifest_path, manifest)
        (run_dir / "result.raw.json").write_text(
            '{"partial":"crash residue"}\n',
            encoding="utf-8",
        )
        (run_dir / "events.jsonl").write_text(
            "controller interrupted\n",
            encoding="utf-8",
        )

        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        recovered = researchctl.load_json(manifest_path)
        self.assertEqual("COMPLETED", recovered["status"])
        self.assertEqual(max_attempts, recovered["attempt"])
        interruption_receipts = list(
            run_dir.glob(
                "interruption-history/*/interruption.json"
            )
        )
        self.assertEqual(1, len(interruption_receipts))
        self.assertFalse(
            researchctl.load_json(
                interruption_receipts[0]
            )["retry_consumed"]
        )

    def test_plan_input_fingerprint_tampering_is_policy_violation(self):
        plan_path = self.plan("BATCH-TEST-STALE")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        locator = next(iter(first["input_components"]))
        first["input_components"][locator] = "0" * 64
        researchctl.write_json(plan_path, plan)
        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "plan immutable fields changed",
        ):
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            )

    def test_coordinated_plan_input_manifest_rewrite_cannot_replace_problem(self):
        plan_path = self.plan("BATCH-TEST-COORDINATED-REWRITE")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        bundle = researchctl.load_json(run_dir / "input.json")
        bundle["problem"]["title"] = "Rewritten runtime-only problem"
        bundle["input_hash"] = researchctl.run_input_hash(bundle)
        researchctl.write_json(run_dir / "input.json", bundle)
        first["input_hash"] = bundle["input_hash"]
        first["input_payload_sha256"] = researchctl.sha256_file(
            run_dir / "input.json"
        )
        manifest_path = run_dir / "manifest.json"
        manifest = researchctl.load_json(manifest_path)
        manifest["input_hash"] = first["input_hash"]
        manifest["input_payload_sha256"] = first[
            "input_payload_sha256"
        ]
        researchctl.write_json(manifest_path, manifest)
        self.reseal_plan(plan_path, plan)

        _, status = researchctl.run_one(plan, first)

        self.assertEqual("POLICY_VIOLATION", status)
        self.assertFalse((run_dir / "result.json").exists())

    def test_research_focus_tampering_is_policy_violation(self):
        plan_path = self.plan("BATCH-TEST-FOCUS-TAMPER")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        bundle = researchctl.load_json(run_dir / "input.json")
        bundle["research_focus"]["hypothesis_ids"] = ["INJECTED-HYPOTHESIS"]
        bundle["input_hash"] = researchctl.run_input_hash(bundle)
        researchctl.write_json(run_dir / "input.json", bundle)

        _, status = researchctl.run_one(plan, first)

        self.assertEqual("POLICY_VIOLATION", status)
        manifest = researchctl.load_json(run_dir / "manifest.json")
        self.assertEqual(0, manifest["attempt"])
        self.assertFalse((run_dir / "result.json").exists())

    def test_completed_input_tampering_blocks_review_and_finalize(self):
        plan_path = self.plan("BATCH-TEST-POSTRUN-INPUT-TAMPER")
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        input_path = (
            researchctl.resolve_root_path(first["run_dir"]) / "input.json"
        )
        bundle = researchctl.load_json(input_path)
        bundle["research_focus"]["tested_claim_ids"] = ["MC-INJECTED"]
        researchctl.write_json(input_path, bundle)

        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "frozen input.json bytes changed",
        ):
            researchctl.prepare_review(
                argparse.Namespace(batch=plan["batch_id"])
            )
        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "frozen input.json bytes changed",
        ):
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            )

    def test_completed_result_and_manifest_rewrite_cannot_replace_raw_output(self):
        plan_path = self.plan("BATCH-TEST-POSTRUN-RESULT-TAMPER")
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        result_path = run_dir / "result.json"
        result = researchctl.load_json(result_path)
        result["candidate_claims"].append(
            "A post-run replacement must not become evidence."
        )
        researchctl.write_json(result_path, result)
        manifest_path = run_dir / "manifest.json"
        manifest = researchctl.load_json(manifest_path)
        manifest["result_sha256"] = researchctl.sha256_file(result_path)
        researchctl.write_json(manifest_path, manifest)

        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "read-only controller seal",
        ):
            researchctl.completed_results(plan)

    def test_finalize_emits_hash_bound_run_evidence_receipts(self):
        plan_path = self.plan("BATCH-TEST-EVIDENCE-RECEIPTS")
        plan = researchctl.load_plan(plan_path)
        project = researchctl.RUNTIME / "finalize-project"
        project.mkdir(parents=True)
        plan["project"] = researchctl.relative(project)
        plan["protected_hashes"] = researchctl.hash_paths(
            researchctl.protected_paths(project)
        )
        self.reseal_plan(plan_path, plan)
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)

        self.assertEqual(
            0,
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            ),
        )
        packet = project / "candidates" / plan["batch_id"]
        manifest = researchctl.load_json(
            packet / "finalization-manifest.json"
        )
        plan_snapshot = packet / "plan-snapshot.json"
        self.assertEqual(
            researchctl.sha256_file(plan_snapshot),
            manifest["result_hashes"][plan_snapshot.name],
        )
        self.assertEqual(
            researchctl.load_json(plan_snapshot)["plan_fingerprint"],
            plan["plan_fingerprint"],
        )
        for run in plan["runs"]:
            evidence_path = packet / f"evidence-{run['line_id']}.json"
            result_path = packet / f"{run['line_id']}.json"
            run_snapshot = (
                packet / f"run-manifest-{run['line_id']}.json"
            )
            evidence = researchctl.load_json(evidence_path)
            self.assertEqual(
                researchctl.sha256_file(evidence_path),
                manifest["result_hashes"][evidence_path.name],
            )
            self.assertEqual(
                researchctl.sha256_file(result_path),
                evidence["result_sha256"],
            )
            self.assertEqual(run["input_hash"], evidence["input_hash"])
            self.assertEqual(
                run["input_payload_sha256"],
                evidence["input_payload_sha256"],
            )
            self.assertEqual(
                researchctl.sha256_file(plan_snapshot),
                evidence["plan_snapshot_sha256"],
            )
            self.assertEqual(
                researchctl.sha256_file(run_snapshot),
                evidence["run_manifest_snapshot_sha256"],
            )
            self.assertEqual(
                "COMPLETED",
                researchctl.load_json(run_snapshot)["status"],
            )
            for artifact_name, receipt_field in (
                (f"input-{run['line_id']}.json", "input_snapshot_sha256"),
                (
                    f"raw-result-{run['line_id']}.json",
                    "raw_result_snapshot_sha256",
                ),
                (
                    f"events-{run['line_id']}.jsonl",
                    "events_snapshot_sha256",
                ),
                (
                    f"completion-seal-{run['line_id']}.json",
                    "completion_seal_snapshot_sha256",
                ),
            ):
                artifact_path = packet / artifact_name
                self.assertEqual(
                    researchctl.sha256_file(artifact_path),
                    evidence[receipt_field],
                )
                self.assertEqual(
                    researchctl.sha256_file(artifact_path),
                    manifest["result_hashes"][artifact_name],
                )

    def test_finalized_candidate_rejects_late_blind_review_attachment(self):
        plan, _, packet = self.finalize_mock_candidate(
            "BATCH-TEST-LATE-BLIND-REVIEW",
            "late-blind-review-project",
        )
        manifest_path = packet / "finalization-manifest.json"
        original_manifest_sha = researchctl.sha256_file(manifest_path)
        original_artifacts = sorted(path.name for path in packet.iterdir())
        review_path = (
            researchctl.RUNTIME
            / plan["batch_id"]
            / "review"
            / "blind-review.json"
        )
        researchctl.write_json(
            review_path,
            {
                "kind": "BlindReview",
                "status": "COMPLETED",
            },
        )

        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "candidate packets are immutable.*after finalization",
        ):
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            )

        self.assertEqual(
            original_manifest_sha,
            researchctl.sha256_file(manifest_path),
        )
        self.assertEqual(
            original_artifacts,
            sorted(path.name for path in packet.iterdir()),
        )

    def test_finalize_deep_verifies_staging_before_atomic_publish(self):
        plan_path = self.plan("BATCH-TEST-STAGING-VERIFY-BEFORE-PUBLISH")
        plan = researchctl.load_plan(plan_path)
        project = researchctl.RUNTIME / "staging-verify-project"
        project.mkdir(parents=True)
        plan["project"] = researchctl.relative(project)
        plan["protected_hashes"] = researchctl.hash_paths(
            researchctl.protected_paths(project)
        )
        self.reseal_plan(plan_path, plan)
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)
        candidates = project / "candidates"
        staging = candidates / f".{plan['batch_id']}.staging"
        published = candidates / plan["batch_id"]
        observed = []

        def reject_candidate(packet, *, published_target=None):
            observed.append(
                {
                    "packet": packet,
                    "published_target": published_target,
                    "published_exists": published.exists(),
                }
            )
            raise researchctl.ResearchError(
                "synthetic staging verification failure"
            )

        with mock.patch.object(
            researchctl,
            "verify_candidate_packet",
            side_effect=reject_candidate,
        ):
            with self.assertRaisesRegex(
                researchctl.ResearchError,
                "synthetic staging verification failure",
            ):
                researchctl.finalize_batch(
                    argparse.Namespace(batch=plan["batch_id"])
                )

        self.assertEqual(
            [
                {
                    "packet": staging,
                    "published_target": published,
                    "published_exists": False,
                }
            ],
            observed,
        )
        self.assertFalse(published.exists())
        self.assertFalse(staging.exists())
        interrupted = candidates / "interrupted-finalizations"
        preserved = [
            path
            for path in interrupted.iterdir()
            if path.is_dir() and path.name.startswith(plan["batch_id"])
        ]
        self.assertEqual(1, len(preserved))
        self.assertTrue(
            (preserved[0] / "finalization-manifest.json").is_file()
        )

    def test_check_candidate_packets_deeply_rejects_rehashed_result_tamper(
        self,
    ):
        plan, project, packet = self.finalize_mock_candidate(
            "BATCH-TEST-DEEP-CANDIDATE-CHECK",
            "deep-candidate-check-project",
        )
        result_path = packet / f"{plan['runs'][0]['line_id']}.json"
        result = researchctl.load_json(result_path)
        result["candidate_claims"].append(
            "A synchronized result and manifest rewrite is still tampering."
        )
        researchctl.write_json(result_path, result)
        manifest_path = packet / "finalization-manifest.json"
        manifest = researchctl.load_json(manifest_path)
        manifest["result_hashes"][result_path.name] = (
            researchctl.sha256_file(result_path)
        )
        researchctl.write_json(manifest_path, manifest)

        errors = researchctl.check_candidate_packets(project)

        self.assertIn(
            "deep candidate verification failed",
            "\n".join(errors),
        )

    def test_candidate_verifier_rejects_finalization_manifest_relabel(self):
        _, _, packet = self.finalize_mock_candidate(
            "BATCH-TEST-MANIFEST-RELABEL",
            "manifest-relabel-project",
        )
        manifest_path = packet / "finalization-manifest.json"
        manifest = researchctl.load_json(manifest_path)
        manifest["kind"] = "ForgedPacketKind"
        manifest["problem_ref"] = "PRB-FORGED@v999"
        manifest["scenario_ref"] = "SCN-FORGED@v999"
        researchctl.write_json(manifest_path, manifest)

        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "finalization manifest has invalid packet semantics",
        ):
            researchctl.verify_candidate_packet(packet)

    def test_candidate_verifier_rejects_plan_status_and_external_relabel(
        self,
    ):
        _, _, packet = self.finalize_mock_candidate(
            "BATCH-TEST-PLAN-RELABEL",
            "plan-relabel-project",
        )
        plan_path = packet / "plan-snapshot.json"
        plan = researchctl.load_json(plan_path)
        plan["status"] = "PLANNED"
        plan["external_disclosure"] = {
            "manifest": ".research-runtime/FORGED-DISCLOSURE.json",
            "disclosure_sha256": "f" * 64,
            "approval_decision_id": "DEC-FORGED",
        }
        researchctl.write_json(plan_path, plan)
        manifest_path = packet / "finalization-manifest.json"
        manifest = researchctl.load_json(manifest_path)
        manifest["result_hashes"][plan_path.name] = (
            researchctl.sha256_file(plan_path)
        )
        researchctl.write_json(manifest_path, manifest)

        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "candidate packet has an invalid frozen plan seal",
        ):
            researchctl.verify_candidate_packet(packet)

    def test_existing_candidate_is_reverified_before_finalize_noop(self):
        plan_path = self.plan("BATCH-TEST-CANDIDATE-REVERIFY")
        plan = researchctl.load_plan(plan_path)
        project = researchctl.RUNTIME / "candidate-reverify-project"
        project.mkdir(parents=True)
        plan["project"] = researchctl.relative(project)
        plan["protected_hashes"] = researchctl.hash_paths(
            researchctl.protected_paths(project)
        )
        self.reseal_plan(plan_path, plan)
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)
        self.assertEqual(
            0,
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            ),
        )
        packet = project / "candidates" / plan["batch_id"]
        result_path = (
            packet / f"{plan['runs'][0]['line_id']}.json"
        )
        result = researchctl.load_json(result_path)
        result["candidate_claims"].append("Mutated after finalization.")
        researchctl.write_json(result_path, result)
        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "candidate artifact hash mismatch",
        ):
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            )

    def test_finalize_rejects_schema_only_blind_review_without_provenance(self):
        plan_path = self.plan("BATCH-TEST-REVIEW-PROVENANCE")
        plan = researchctl.load_plan(plan_path)
        project = researchctl.RUNTIME / "review-finalize-project"
        project.mkdir(parents=True)
        plan["project"] = researchctl.relative(project)
        plan["protected_hashes"] = researchctl.hash_paths(
            researchctl.protected_paths(project)
        )
        self.reseal_plan(plan_path, plan)
        self.assertEqual(
            0,
            researchctl.run_batch(
                argparse.Namespace(plan=researchctl.relative(plan_path))
            ),
        )
        plan = researchctl.load_plan(plan_path)
        self.assertEqual(
            0,
            researchctl.prepare_review(
                argparse.Namespace(batch=plan["batch_id"])
            ),
        )
        review_path = (
            researchctl.RUNTIME
            / plan["batch_id"]
            / "review"
            / "blind-review.json"
        )
        researchctl.write_json(
            review_path,
            {
                "schema_version": "2.0",
                "kind": "BlindReview",
                "review_scope": "PROBLEM_FRAME",
                "status": "COMPLETED",
                "strongest_counterarguments": [
                    "A schema-valid review alone does not prove external execution."
                ],
                "unsupported_inferences": [],
                "erased_distinctions": [],
                "missing_evidence": [],
                "baseline_challenges": [],
                "recommendation": "KEEP_COMPETING_RESULTS",
                "cannot_conclude": [
                    "The review cannot activate or replace a problem."
                ],
            },
        )
        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "provenance artifacts are missing",
        ):
            researchctl.finalize_batch(
                argparse.Namespace(batch=plan["batch_id"])
            )
        review_dir = review_path.parent
        bundle_path = review_dir / "review-bundle.json"
        disclosure_path = review_dir / "review-disclosure.json"
        raw_path = review_dir / "claude-raw.json"
        review = researchctl.load_json(review_path)
        raw_path.write_text(
            json.dumps(
                {"structured_output": review},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        stderr_path = review_dir / "claude-stderr.txt"
        stderr_path.write_text("", encoding="utf-8")
        disclosure = researchctl.load_json(disclosure_path)
        disclosure["approval_decision_id"] = "DEC-TEST-CLAUDE-REVIEW"
        researchctl.write_json(disclosure_path, disclosure)
        execution_path = review_dir / "blind-review-execution.json"
        researchctl.write_json(
            execution_path,
            {
                "schema_version": "1.0",
                "kind": "BlindReviewExecutionReceipt",
                "batch_id": plan["batch_id"],
                "reviewer": "Anthropic Claude",
                "model": "test-claude",
                "review_scope": "PROBLEM_FRAME",
                "payload_path": researchctl.relative(bundle_path),
                "payload_sha256": researchctl.sha256_file(bundle_path),
                "disclosure_path": researchctl.relative(disclosure_path),
                "disclosure_sha256": researchctl.sha256_file(
                    disclosure_path
                ),
                "review_path": researchctl.relative(review_path),
                "review_sha256": researchctl.sha256_file(review_path),
                "raw_path": researchctl.relative(raw_path),
                "raw_sha256": researchctl.sha256_file(raw_path),
                "stderr_path": researchctl.relative(stderr_path),
                "stderr_sha256": researchctl.sha256_file(stderr_path),
                "process_exit_code": 0,
                "approval_decision_id": "DEC-TEST-CLAUDE-REVIEW",
                "completed_at": researchctl.utc_now(),
            },
        )
        researchctl.write_controller_seal(
            review_dir / "blind-review-seal.json",
            {
                "schema_version": "1.0",
                "kind": "BlindReviewControllerSeal",
                "batch_id": plan["batch_id"],
                "execution_receipt_sha256": researchctl.sha256_file(
                    execution_path
                ),
                "payload_sha256": researchctl.sha256_file(bundle_path),
                "review_sha256": researchctl.sha256_file(review_path),
                "raw_sha256": researchctl.sha256_file(raw_path),
                "stderr_sha256": researchctl.sha256_file(stderr_path),
                "sealed_at": researchctl.utc_now(),
            },
        )
        with mock.patch.object(
            researchctl,
            "decision_allows_transfer",
            return_value=True,
        ):
            self.assertEqual(
                0,
                researchctl.finalize_batch(
                    argparse.Namespace(batch=plan["batch_id"])
                ),
            )
        packet = project / "candidates" / plan["batch_id"]
        packet_manifest = researchctl.load_json(
            packet / "finalization-manifest.json"
        )
        for name in (
            "review-bundle.json",
            "review-disclosure.json",
            "blind-review.json",
            "blind-review-execution.json",
            "claude-raw.json",
            "claude-stderr.txt",
            "blind-review-seal.json",
        ):
            self.assertEqual(
                researchctl.sha256_file(packet / name),
                packet_manifest["result_hashes"][name],
            )
        tampered_review_path = packet / "blind-review.json"
        tampered_review = researchctl.load_json(tampered_review_path)
        tampered_review["missing_evidence"].append(
            "A coordinated manifest rehash must not replace Claude evidence."
        )
        researchctl.write_json(tampered_review_path, tampered_review)
        packet_manifest["result_hashes"][
            tampered_review_path.name
        ] = researchctl.sha256_file(tampered_review_path)
        packet_manifest["blind_review"][
            "result_sha256"
        ] = researchctl.sha256_file(tampered_review_path)
        researchctl.write_json(
            packet / "finalization-manifest.json",
            packet_manifest,
        )
        with self.assertRaisesRegex(
            researchctl.ResearchError,
            "differs from Claude raw output",
        ):
            researchctl.verify_candidate_packet(packet)

    def test_source_change_is_marked_stale_without_overwrite(self):
        plan_path = self.plan("BATCH-TEST-SOURCE-STALE")
        plan = researchctl.load_plan(plan_path)
        first = plan["runs"][0]
        run_dir = researchctl.resolve_root_path(first["run_dir"])
        source = researchctl.RUNTIME / "mutable-source.txt"
        source.write_text("version one\n", encoding="utf-8")
        locator = researchctl.relative(source)
        first["input_components"][locator] = researchctl.sha256_file(source)
        bundle = researchctl.load_json(run_dir / "input.json")
        bundle["input_components"] = copy.deepcopy(first["input_components"])
        bundle["input_hash"] = researchctl.run_input_hash(bundle)
        first["input_hash"] = bundle["input_hash"]
        researchctl.write_json(run_dir / "input.json", bundle)
        first["input_payload_sha256"] = researchctl.sha256_file(
            run_dir / "input.json"
        )
        manifest = researchctl.load_json(run_dir / "manifest.json")
        manifest["input_hash"] = first["input_hash"]
        manifest["input_payload_sha256"] = first["input_payload_sha256"]
        researchctl.write_json(run_dir / "manifest.json", manifest)
        self.reseal_plan(plan_path, plan)
        source.write_text("version two\n", encoding="utf-8")
        line_id, status = researchctl.run_one(plan, first)
        self.assertEqual(first["line_id"], line_id)
        self.assertEqual("STALE_FOR_CURRENT", status)
        manifest = researchctl.load_json(run_dir / "manifest.json")
        self.assertEqual("STALE_FOR_CURRENT", manifest["status"])
        self.assertFalse((run_dir / "result.json").exists())

    def test_scenario_promotion_preserves_candidate_and_exact_receipt(self):
        project = researchctl.RUNTIME / "scenario-project"
        for name in ("problem", "lines", "scenarios"):
            (project / name).mkdir(parents=True, exist_ok=True)
        source_path = (
            researchctl.DEFAULT_PROJECT
            / "scenarios"
            / "problem-definition-archive-v0.json"
        )
        candidate = researchctl.load_json(source_path)
        candidate["status"] = "VALIDATED"
        candidate_path = project / "scenarios" / "candidate.json"
        researchctl.write_json(candidate_path, candidate)
        source_sha = researchctl.sha256_file(candidate_path)
        decision_id = "DEC-TEST-SCENARIO-ACTIVATION"
        decision = {
            "decision_id": decision_id,
            "status": "APPROVED",
            "decided_by": "USER",
            "actions": ["ACTIVATE_SCENARIO"],
            "target": {
                "id": candidate["id"],
                "version": candidate["version"],
                "source_path": researchctl.relative(candidate_path),
                "source_sha256": source_sha,
            },
        }
        args = argparse.Namespace(
            project=researchctl.relative(project),
            candidate=researchctl.relative(candidate_path),
            target="scenario",
            decision_id=decision_id,
        )
        with (
            mock.patch.object(
                researchctl,
                "read_decisions",
                return_value={decision_id: decision},
            ),
            mock.patch.object(researchctl, "read_state", return_value={}),
            mock.patch.object(researchctl, "write_state"),
        ):
            self.assertEqual(0, researchctl.promote(args))
            active_path = (
                project / "scenarios" / "candidate-active.json"
            )
            self.assertTrue(active_path.is_file())
            self.assertEqual(source_sha, researchctl.sha256_file(candidate_path))
            self.assertNotEqual(candidate_path, active_path)
            active = researchctl.load_json(active_path)
            self.assertEqual(
                [],
                researchctl.check_exact_promotion_receipt(
                    active_path,
                    active,
                    "scenario",
                ),
            )
            original_active = copy.deepcopy(active)
            active["initial_state"] += " Material mutation after approval."
            researchctl.write_json(active_path, active)
            receipt_path = next((project / "promotions").glob("*.json"))
            receipt = researchctl.load_json(receipt_path)
            receipt["target_sha256"] = researchctl.sha256_file(active_path)
            researchctl.write_json(receipt_path, receipt)
            self.assertIn(
                "exact source/target-hash user promotion receipt",
                "\n".join(
                    researchctl.check_exact_promotion_receipt(
                        active_path,
                        active,
                        "scenario",
                    )
                ),
            )
            researchctl.write_json(active_path, original_active)
            receipt["target_sha256"] = researchctl.sha256_file(active_path)
            changed_source = researchctl.load_json(candidate_path)
            changed_source["initial_state"] += " Mutated source preimage."
            researchctl.write_json(candidate_path, changed_source)
            receipt["source_sha256"] = researchctl.sha256_file(candidate_path)
            researchctl.write_json(receipt_path, receipt)
            self.assertIn(
                "exact source/target-hash user promotion receipt",
                "\n".join(
                    researchctl.check_exact_promotion_receipt(
                        active_path,
                        original_active,
                        "scenario",
                    )
                ),
            )

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
        self.assertEqual("2.0", bundle["schema_version"])
        self.assertEqual("PROBLEM_FRAME", bundle["review_scope"])
        self.assertTrue(
            all(
                item["bounded_target"] is None
                for item in bundle["anonymous_returns"]
            )
        )
        self.assertEqual(7, len(bundle["anonymous_returns"]))
        self.assertIn("expected answer", bundle["excluded"])

    def test_scoped_mechanism_review_preserves_exact_hypothesis_and_claim(self):
        project = researchctl.DEFAULT_PROJECT
        line_path = project / "lines" / "01-nac.json"
        line = researchctl.load_json(line_path)
        profile_path = project / "mechanisms" / "nac.json"
        profile = researchctl.load_json(profile_path)
        focus = {
            "mechanism_ref": researchctl.relative(profile_path),
            "hypothesis_ids": ["E-H1-PRIME"],
            "tested_claim_ids": ["MC-NAC-ANCHOR"],
        }
        bundle = {
            "line": line,
            "research_focus": focus,
            "mechanism_profiles": [
                {
                    "locator": researchctl.relative(profile_path),
                    "sha256": researchctl.sha256_file(profile_path),
                    "profile": profile,
                }
            ],
        }
        target = researchctl.build_bounded_review_target(bundle)
        self.assertIsNotNone(target)
        self.assertEqual(["E-H1-PRIME"], target["hypothesis_ids"])
        self.assertEqual(["MC-NAC-ANCHOR"], target["tested_claim_ids"])
        self.assertEqual(
            "MC-NAC-ANCHOR",
            target["mechanism"]["selected_claims"][0]["id"],
        )

    def test_mixed_problem_scenario_bundle_is_rejected(self):
        project = researchctl.DEFAULT_PROJECT
        problem = researchctl.load_json(
            project / "problem" / "v2-candidate.json"
        )
        scenario = researchctl.load_json(
            project / "scenarios" / "problem-definition-archive-v0.json"
        )
        line = researchctl.load_json(project / "lines" / "01-nac.json")
        batch_id = "BATCH-TEST-MIXED-VERSIONS"
        run_id = f"{batch_id}-{line['id']}"
        plan = {
            "schema_version": "2.0",
            "batch_id": batch_id,
            "mode": "mock",
        }
        run = {"run_id": run_id, "line_id": line["id"]}
        manifest = {
            "run_id": run_id,
            "batch_id": batch_id,
            "line_id": line["id"],
            "mode": "mock",
            "problem_ref": f"{problem['id']}@{problem['version']}",
            "scenario_ref": f"{scenario['id']}@{scenario['version']}",
        }
        errors = researchctl.frozen_bundle_binding_errors(
            plan,
            run,
            manifest,
            {
                "batch_id": batch_id,
                "run_id": run_id,
                "problem": problem,
                "scenario": scenario,
                "line": line,
            },
        )
        self.assertIn(
            "scenario.problem_ref differs from the frozen problem",
            errors,
        )
        self.assertIn("frozen research line is not ACTIVE", errors)

    def test_codex_batch_requires_exact_disclosure_decision(self):
        args = argparse.Namespace(
            project=None,
            problem="v0",
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
            problem="v0",
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

    def test_authorization_reentry_recovers_after_seal_is_written(self):
        batch_id = "BATCH-TEST-AUTHORIZATION-REENTRY"
        self.assertEqual(
            0,
            researchctl.plan_batch(
                argparse.Namespace(
                    project=None,
                    problem="v0",
                    scenario=None,
                    mode="codex",
                    batch_id=batch_id,
                    max_parallel=3,
                )
            ),
        )
        plan_path = researchctl.RUNTIME / batch_id / "plan.json"
        plan = researchctl.load_plan(plan_path)
        disclosure_path = researchctl.resolve_root_path(
            plan["external_disclosure"]["manifest"]
        )
        authorization_path = (
            researchctl.RUNTIME / batch_id / "authorization-seal.json"
        )
        original_write_json = researchctl.write_json
        interrupted = False

        def interrupt_after_seal(path, value):
            nonlocal interrupted
            if Path(path) == disclosure_path and not interrupted:
                interrupted = True
                raise OSError("simulated authorization interruption")
            return original_write_json(path, value)

        with (
            mock.patch.object(
                researchctl,
                "decision_allows_transfer",
                return_value=True,
            ),
            mock.patch.object(
                researchctl,
                "write_json",
                side_effect=interrupt_after_seal,
            ),
        ):
            with self.assertRaisesRegex(
                OSError,
                "simulated authorization interruption",
            ):
                researchctl.authorize_batch(
                    argparse.Namespace(
                        batch=batch_id,
                        decision_id="DEC-TEST-AUTHORIZATION-REENTRY",
                    )
                )

        self.assertTrue(authorization_path.is_file())
        sealed_sha = researchctl.sha256_file(authorization_path)
        self.assertIsNone(
            researchctl.load_json(plan_path)["external_disclosure"][
                "approval_decision_id"
            ]
        )

        with mock.patch.object(
            researchctl,
            "decision_allows_transfer",
            return_value=True,
        ):
            self.assertEqual(
                0,
                researchctl.authorize_batch(
                    argparse.Namespace(
                        batch=batch_id,
                        decision_id="DEC-TEST-AUTHORIZATION-REENTRY",
                    )
                ),
            )

        authorized = researchctl.load_plan(plan_path)
        self.assertEqual(
            "DEC-TEST-AUTHORIZATION-REENTRY",
            authorized["external_disclosure"]["approval_decision_id"],
        )
        self.assertEqual(
            "DEC-TEST-AUTHORIZATION-REENTRY",
            researchctl.load_json(disclosure_path)[
                "approval_decision_id"
            ],
        )
        self.assertEqual(
            sealed_sha,
            researchctl.sha256_file(authorization_path),
        )

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
        self.reseal_plan(plan_path, plan)

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
        self.reseal_plan(plan_path, plan)

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
