from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import runner


class RunnerContractTests(unittest.TestCase):
    @staticmethod
    def command_receipt(value: dict) -> runner.CommandReceipt:
        return runner.CommandReceipt(
            command=value["command"],
            started_at=value["started_at"],
            finished_at=value["finished_at"],
            monotonic_start_ns=value["monotonic_start_ns"],
            monotonic_finish_ns=value["monotonic_finish_ns"],
            returncode=value["returncode"],
            stdout=base64.b64decode(value["stdout_base64"]),
            stderr=base64.b64decode(value["stderr_base64"]),
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="wave025-runner-test-")
        self.root = Path(self.temporary.name)
        self.fake_docker = Path(__file__).with_name("fake_docker.py")
        os.chmod(self.fake_docker, 0o755)
        self.environment = mock.patch.dict(
            os.environ, {"FAKE_DOCKER_STATE": str(self.root / "fake-docker-state")}
        )
        self.environment.start()
        self.input_root = self.root / "input-sources"
        self.input_root.mkdir()
        self.frozen_input_paths = {}
        experiment_root = Path(__file__).resolve().parent.parent
        self.actual_public_registry_path = (
            experiment_root / "control-registries"
            / "PUBLIC-CONTROL-FAMILY-REGISTRATION.preformal-candidate.json"
        )
        self.actual_private_registry_path = (
            experiment_root / "control-registries"
            / "PRIVATE-CONTROL-REGISTRY.preformal-candidate.json"
        )
        feature_value = {"schema": "WAVE025_FEATURE_CLASSIFIER_SPEC_V1"}
        feature_raw = runner.canonical_bytes(feature_value)
        public_registration = json.loads(
            self.actual_public_registry_path.read_text(encoding="utf-8")
        )
        public_registration["feature_spec_sha256"] = runner.sha256_bytes(feature_raw)
        public_registration_raw = runner.canonical_bytes(public_registration)
        executable_profile = {
            "feature_spec_binding": {
                "expected_schema": "WAVE025_FEATURE_CLASSIFIER_SPEC_V1",
                "raw_byte_length": len(feature_raw),
                "raw_bytes_sha256": runner.sha256_bytes(feature_raw),
            },
            "profile_id": "WAVE025-EXECUTABLE-ATTACK-PROFILE-FULL-V1",
            "schema": "WAVE025_EXECUTABLE_ATTACK_PROFILE_FULL_V1",
        }
        for spec in runner.FROZEN_INPUT_SPECS:
            path = self.input_root / spec["filename"]
            if spec["name"] == "feature_spec":
                raw = feature_raw
            elif spec["name"] == "executable_attack_profile":
                raw = runner.canonical_bytes(executable_profile)
            elif spec["name"] == "control_family_registration":
                raw = public_registration_raw
            else:
                raw = runner.canonical_bytes({"schema": spec["schema"]})
            path.write_bytes(raw)
            self.frozen_input_paths[spec["argument"]] = str(path)
        private_registry = json.loads(
            self.actual_private_registry_path.read_text(encoding="utf-8")
        )
        private_registry["public_registration_sha256"] = runner.sha256_bytes(
            public_registration_raw
        )
        self.private_control_registry_path = self.input_root / "private-control-registry.json"
        self.private_control_registry_path.write_bytes(runner.canonical_bytes(private_registry))
        os.chmod(self.private_control_registry_path, 0o600)
        self.private_control_registry = json.loads(
            self.private_control_registry_path.read_text(encoding="utf-8")
        )
        self.control_instances = {
            family["challenge"]: {
                mapping["role_label"]: (
                    mapping["candidate_visible_basename"]
                    if family["challenge"] == "D0-HOST-LEAK"
                    else mapping["token_utf8"]
                )
                for mapping in family["role_mappings"]
            }
            for family in self.private_control_registry["families"]
        }

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def prepare_args(self, name: str) -> argparse.Namespace:
        batch = self.root / name
        return argparse.Namespace(
            **{
                "batch_dir": str(batch),
                "batch_id": f"w025-smoke-{name}-0001",
                "mode": "smoke",
                "image_ref": "wave025-leak-collector:local",
                "base_image_ref": "node:20-slim",
                "smoke_per_split": 2,
                "docker_bin": str(self.fake_docker),
                "private_control_registry_path": str(self.private_control_registry_path),
                **self.frozen_input_paths,
            }
        )

    def prepare(self, name: str = "smoke-batch") -> Path:
        arguments = self.prepare_args(name)
        batch = Path(arguments.batch_dir)
        result = runner.prepare(arguments)
        self.assertEqual(result["state"], "PREPARED")
        return batch

    def write_private_registry(self, name: str, value: dict) -> str:
        path = self.input_root / f"{name}.private.json"
        path.write_bytes(runner.canonical_bytes(value))
        os.chmod(path, 0o600)
        return str(path)

    def anchor(self, batch: Path, kind: str = "LOCAL_NONQUALIFYING_ANCHOR") -> None:
        precommit_hash = runner.sha256_file(batch / "precommit.json")
        receipt = {
            "kind": kind,
            "reference": "test-root:immutable:001",
            "anchored_at": "2026-08-01T00:00:00Z",
            "precommit_sha256": precommit_hash,
        }
        result = runner.anchor(
            argparse.Namespace(
                batch_dir=str(batch),
                receipt_json=[json.dumps(receipt)],
                receipt_file=None,
            )
        )
        self.assertIn("ANCHORED", result["state"])

    def test_formal_layout_is_frozen_3200_and_block_balanced(self) -> None:
        layout = runner.sample_layout("formal", 2)
        self.assertEqual(len(layout), 3200)
        counts = {}
        for item in layout:
            counts[(item["challenge"], item["phase"])] = (
                counts.get((item["challenge"], item["phase"]), 0) + 1
            )
        self.assertEqual(counts[("D0-HOST-LEAK", "calibration")], 100)
        self.assertEqual(counts[("D0-HOST-LEAK", "holdout")], 100)
        self.assertEqual(counts[("D1-OCI-CANARY", "calibration")], 100)
        self.assertEqual(counts[("D1-OCI-CANARY", "holdout")], 100)
        self.assertEqual(counts[("T-OCI-ISOLATED", "calibration")], 400)
        self.assertEqual(counts[("T-OCI-ISOLATED", "holdout")], 2400)
        mapping, order = runner.assign_population(
            layout, bytes.fromhex("01" * 32), bytes.fromhex("02" * 32),
            bytes.fromhex("03" * 32), self.control_instances,
        )
        self.assertTrue(runner.strict_balance(mapping))
        self.assertEqual(len(order), 3200)
        self.assertEqual(len(set(order)), 3200)

    def test_prepare_cli_requires_six_public_plus_one_private_path(self) -> None:
        parser = runner.build_parser()
        base = [
            "prepare",
            "--batch-dir",
            str(self.root / "cli-batch"),
            "--mode",
            "smoke",
        ]
        old_hash_arguments = base + [
            "--evaluator-source-sha256",
            "0" * 64,
            "--feature-spec-sha256",
            "1" * 64,
        ]
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(old_hash_arguments)
        path_arguments = []
        for spec in runner.FROZEN_INPUT_SPECS:
            path_arguments += [
                "--" + spec["argument"].replace("_", "-"),
                self.frozen_input_paths[spec["argument"]],
            ]
        path_arguments += [
            "--private-control-registry-path", str(self.private_control_registry_path)
        ]
        parsed = parser.parse_args(base + path_arguments)
        for spec in runner.FROZEN_INPUT_SPECS:
            self.assertEqual(
                getattr(parsed, spec["argument"]), self.frozen_input_paths[spec["argument"]]
            )
        self.assertEqual(
            parsed.private_control_registry_path, str(self.private_control_registry_path)
        )

    def test_prepare_is_exclusive_role_free_and_stops_before_anchor(self) -> None:
        batch = self.prepare()
        self.assertFalse((batch / "anchor-receipt.json").exists())
        self.assertFalse(any((batch / "slots").iterdir()))
        self.assertEqual(
            stat.S_IMODE((batch / "runner-private-state.json").stat().st_mode), 0o600
        )
        public = (batch / "public-plan.json").read_text(encoding="utf-8")
        precommit = (batch / "precommit.json").read_text(encoding="utf-8")
        private = (batch / "runner-private-state.json").read_text(encoding="utf-8")
        self.assertNotIn('"role"', public)
        self.assertNotIn('"seed_hex"', public)
        self.assertNotIn('"role"', precommit)
        self.assertNotIn('"seed_hex"', precommit)
        self.assertIn('"role"', private)
        self.assertIn('"seed_hex"', private)
        precommit_value, _ = runner.read_json(
            batch / "precommit.json", runner.SCHEMA_PRECOMMIT
        )
        self.assertEqual(
            precommit_value["evidence_extraction_profile"],
            runner.EVIDENCE_EXTRACTION_PROFILE,
        )
        with self.assertRaises(runner.RunnerError):
            self.prepare()

    def test_private_registry_hash_roles_mode_and_formal_reuse_fail_closed(self) -> None:
        wrong_hash = json.loads(json.dumps(self.private_control_registry))
        wrong_hash["public_registration_sha256"] = "0" * 64
        arguments = self.prepare_args("wrong-public-registration-hash")
        arguments.private_control_registry_path = self.write_private_registry(
            "wrong-public-registration-hash", wrong_hash
        )
        with self.assertRaisesRegex(runner.RunnerError, "public_registration_sha256"):
            runner.prepare(arguments)
        self.assertFalse(Path(arguments.batch_dir).exists())

        wrong_roles = json.loads(json.dumps(self.private_control_registry))
        wrong_roles["families"][0]["role_mappings"][1]["role_label"] = "R"
        arguments = self.prepare_args("wrong-role-mapping")
        arguments.private_control_registry_path = self.write_private_registry(
            "wrong-role-mapping", wrong_roles
        )
        with self.assertRaisesRegex(runner.RunnerError, "role mapping labels"):
            runner.prepare(arguments)
        self.assertFalse(Path(arguments.batch_dir).exists())

        os.chmod(self.private_control_registry_path, 0o644)
        arguments = self.prepare_args("wrong-private-mode")
        with self.assertRaisesRegex(runner.RunnerError, "wrong mode"):
            runner.prepare(arguments)
        os.chmod(self.private_control_registry_path, 0o600)

        noncanonical_path = self.input_root / "noncanonical.private.json"
        noncanonical_path.write_text(
            json.dumps(self.private_control_registry, indent=2), encoding="utf-8"
        )
        os.chmod(noncanonical_path, 0o600)
        arguments = self.prepare_args("noncanonical-private")
        arguments.private_control_registry_path = str(noncanonical_path)
        with self.assertRaisesRegex(runner.RunnerError, "not canonical"):
            runner.prepare(arguments)

        wrong_schema = json.loads(json.dumps(self.private_control_registry))
        wrong_schema["schema"] = "WAVE025_PRIVATE_CONTROL_REGISTRY_V0"
        arguments = self.prepare_args("wrong-private-schema")
        arguments.private_control_registry_path = self.write_private_registry(
            "wrong-private-schema", wrong_schema
        )
        with self.assertRaisesRegex(runner.RunnerError, "wrong schema"):
            runner.prepare(arguments)

        arguments = self.prepare_args("formal-reused-registry")
        arguments.mode = "formal"
        with self.assertRaisesRegex(runner.RunnerError, "formal batch refuses"):
            runner.prepare(arguments)
        self.assertFalse(Path(arguments.batch_dir).exists())

    def test_b1_actual_public_registry_and_wrong_profile_cross_bindings_fail_prepare(self) -> None:
        arguments = self.prepare_args("b1-actual-public-feature-mismatch")
        arguments.control_family_registration_path = str(self.actual_public_registry_path)
        arguments.private_control_registry_path = str(self.actual_private_registry_path)
        with self.assertRaisesRegex(
            runner.RunnerError, "does not bind frozen feature spec bytes"
        ):
            runner.prepare(arguments)
        self.assertFalse(Path(arguments.batch_dir).exists())

        profile_path = Path(self.frozen_input_paths["executable_attack_profile_path"])
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["profile_id"] = "WRONG-PROFILE"
        profile_path.write_bytes(runner.canonical_bytes(profile))
        arguments = self.prepare_args("b1-profile-id-mismatch")
        with self.assertRaisesRegex(runner.RunnerError, "profile_id"):
            runner.prepare(arguments)
        self.assertFalse(Path(arguments.batch_dir).exists())

        profile["profile_id"] = "WAVE025-EXECUTABLE-ATTACK-PROFILE-FULL-V1"
        profile["feature_spec_binding"]["raw_bytes_sha256"] = "0" * 64
        profile_path.write_bytes(runner.canonical_bytes(profile))
        arguments = self.prepare_args("b1-profile-feature-mismatch")
        with self.assertRaisesRegex(runner.RunnerError, "profile feature hash mismatch"):
            runner.prepare(arguments)
        self.assertFalse(Path(arguments.batch_dir).exists())

    def test_preformal_explicit_reused_d1_registry_is_admitted_and_mapping_is_stable(self) -> None:
        batch = self.prepare("preformal-reused-d1")
        private, _ = runner.read_json(
            batch / "runner-private-state.json", runner.SCHEMA_PRIVATE_STATE
        )
        self.assertEqual(
            private["private_control_registry"]["status"],
            "PREFORMAL_CANDIDATE_NOT_BOUND_REUSES_REVEALED_D1",
        )
        for challenge in runner.CONTROL_CHALLENGES:
            for role in ("R", "S"):
                observed = {
                    item["private_canary_token_or_null"]
                    for item in private["mapping"]
                    if item["challenge"] == challenge and item["role"] == role
                }
                self.assertEqual(observed, {self.control_instances[challenge][role]})

    def test_preexisting_t_template_with_registered_d1_token_fails_before_any_slot(self) -> None:
        batch = self.prepare("preloaded-t-contamination")
        self.anchor(batch)
        runtime_root = Path(str(batch) + ".runtime")
        runtime_root.mkdir(mode=0o700)
        templates = runtime_root / "templates"
        templates.mkdir(mode=0o700)
        t_template = templates / "t-isolated"
        runner.make_template(t_template, self.control_instances["D1-OCI-CANARY"]["R"])

        with self.assertRaisesRegex(runner.RunnerError, "closed inventory mismatch"):
            runner.run_batch(
                argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
            )
        self.assertFalse(any((batch / "slots").iterdir()))

    def test_b3_six_forged_predecessor_objects_force_close_aborted(self) -> None:
        batch = self.prepare("b3-forged-predecessor-provenance")
        self.anchor(batch)
        run_result = runner.run_batch(
            argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
        )
        self.assertEqual(run_result["infrastructure_counts"], {"COMPLETE": 12})
        private, _ = runner.read_json(
            batch / "runner-private-state.json", runner.SCHEMA_PRIVATE_STATE
        )
        d0_slot = next(
            item for item in private["mapping"] if item["challenge"] == "D0-HOST-LEAK"
        )
        slot_id = d0_slot["opaque_slot_id"]
        provenance_path = (
            Path(str(batch) + ".runtime") / "attempts" / slot_id
            / "d0-private-provenance.json"
        )
        provenance, _ = runner.read_json(
            provenance_path, runner.SCHEMA_D0_PRIVATE_PROVENANCE
        )
        provenance["predecessor_exact_command_receipts"] = [
            {"junk": d0_slot["private_canary_token_or_null"]}, {}, {}, {}, {}, {}
        ]
        provenance_raw = runner.canonical_bytes(provenance)
        provenance_path.write_bytes(provenance_raw)

        host_path = batch / "slots" / slot_id / "host-launch.json"
        host_launch, _ = runner.read_json(host_path, runner.SCHEMA_HOST_LAUNCH)
        commitment = host_launch["diagnostics"][
            "private_predecessor_provenance_commitment_or_null"
        ]
        commitment["private_provenance_sha256"] = runner.sha256_bytes(provenance_raw)
        commitment["private_provenance_byte_length"] = len(provenance_raw)
        commitment["predecessor_command_receipt_count"] = 6
        host_raw = runner.canonical_bytes(host_launch)
        host_path.write_bytes(host_raw)

        slot_receipt_path = batch / "slots" / slot_id / "slot-receipt.json"
        slot_receipt, _ = runner.read_json(
            slot_receipt_path, runner.SCHEMA_SLOT_RECEIPT
        )
        slot_receipt["files"]["host-launch.json"] = runner.sha256_bytes(host_raw)
        slot_receipt_path.write_bytes(runner.canonical_bytes(slot_receipt))

        close_result = runner.close_batch(
            argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
        )
        self.assertEqual(close_result["state"], "ABORTED")
        closed, _ = runner.read_json(batch / "closed.json", runner.SCHEMA_CLOSED)
        self.assertFalse(closed["private_d0_provenance_commitment"]["valid"])
        self.assertIn(
            "command receipt fields mismatch",
            closed["private_d0_provenance_commitment"]["failure"],
        )

    def test_runtime_template_validator_rejects_bytes_mode_symlink_and_extra_entry(self) -> None:
        mutations = ("bytes", "mode", "symlink", "extra")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                template = self.root / f"template-{mutation}"
                runner.make_template(template)
                target = template / "input.bin"
                if mutation == "bytes":
                    os.chmod(target, 0o644)
                    target.write_bytes(b"mutated")
                    os.chmod(target, 0o444)
                elif mutation == "mode":
                    os.chmod(target, 0o644)
                elif mutation == "symlink":
                    target.unlink()
                    target.symlink_to(template / "collector-input.json")
                else:
                    extra = template / "extra.txt"
                    extra.write_bytes(b"extra")
                    os.chmod(extra, 0o444)
                with self.assertRaises(runner.RunnerError):
                    runner.validate_runtime_template(template, "T-OCI-ISOLATED", None)

    def test_t_receipt_structural_and_private_derivative_defense_in_depth(self) -> None:
        batch = self.prepare("t-receipt-defense")
        precommit, _ = runner.read_json(batch / "precommit.json", runner.SCHEMA_PRECOMMIT)
        inspect_pre = {
            "Config": {"WorkingDir": "/app"},
            "Mounts": [
                {"Destination": "/challenge", "RW": False, "Source": "/host/t"}
            ],
        }
        clean_receipt = {
            "directory_trees": {
                "challenge": {
                    "available": True,
                    "entries": [
                        {
                            "mode_octal": "0o0755", "path": ".",
                            "size_bytes": "96", "type": "directory",
                        },
                        {
                            "mode_octal": "0o0444", "path": "collector-input.json",
                            "size_bytes": str(len(runner.PUBLIC_PACKET_BYTES)), "type": "file",
                        },
                        {
                            "mode_octal": "0o0444", "path": "input.bin",
                            "size_bytes": str(len(runner.FIXED_INPUT_BYTES)), "type": "file",
                        },
                    ],
                    "errors": [],
                    "truncated": False,
                }
            },
            "schema": runner.SCHEMA_FEATURES,
            "visible_canaries": [],
        }
        clean = runner.audit_registered_control_receipt(
            "T-OCI-ISOLATED", None, runner.canonical_bytes(clean_receipt), inspect_pre,
            None, precommit, self.control_instances,
        )
        self.assertTrue(clean["valid"])

        token = self.control_instances["D1-OCI-CANARY"]["R"]
        contaminated_tree = json.loads(json.dumps(clean_receipt))
        contaminated_tree["directory_trees"]["challenge"]["entries"].append(
            {
                "mode_octal": "0o0444", "path": f"{token}.txt",
                "size_bytes": str(len(token) + 1), "type": "file",
            }
        )
        contaminated_tree["visible_canaries"] = [
            {
                "location": f"{token}.txt", "source": "challenge-file-content",
                "token_sha256": runner.sha256_bytes(token.encode("utf-8")),
            }
        ]
        rejected = runner.audit_registered_control_receipt(
            "T-OCI-ISOLATED", None, runner.canonical_bytes(contaminated_tree), inspect_pre,
            None, precommit, self.control_instances,
        )
        self.assertFalse(rejected["valid"])
        self.assertIn("t_visible_canaries_not_empty", rejected["failures"])
        self.assertIn("t_challenge_tree_closed_inventory_mismatch", rejected["failures"])
        self.assertIn(
            "t_collector_receipt_contains_registered_private_derivative",
            rejected["failures"],
        )

        content_hash_only = json.loads(json.dumps(clean_receipt))
        content_hash_only["opaque_observation"] = runner.sha256_bytes(
            (token + "\n").encode("utf-8")
        )
        rejected = runner.audit_registered_control_receipt(
            "T-OCI-ISOLATED", None, runner.canonical_bytes(content_hash_only), inspect_pre,
            None, precommit, self.control_instances,
        )
        self.assertFalse(rejected["valid"])
        self.assertEqual(
            rejected["failures"],
            ["t_collector_receipt_contains_registered_private_derivative"],
        )

    def test_prepare_copies_exact_self_contained_frozen_inputs(self) -> None:
        batch = self.prepare("self-contained")
        precommit, _ = runner.read_json(batch / "precommit.json", runner.SCHEMA_PRECOMMIT)
        registry = precommit["frozen_inputs"]
        self.assertEqual(registry["schema"], runner.SCHEMA_FROZEN_INPUT_REGISTRY)
        self.assertEqual(registry["directory"], "frozen-inputs")
        self.assertEqual(
            [entry["name"] for entry in registry["entries"]],
            [spec["name"] for spec in runner.FROZEN_INPUT_SPECS],
        )
        by_name = {entry["name"]: entry for entry in registry["entries"]}
        for spec in runner.FROZEN_INPUT_SPECS:
            source = Path(self.frozen_input_paths[spec["argument"]])
            frozen = batch / by_name[spec["name"]]["relative_path"]
            self.assertEqual(frozen.read_bytes(), source.read_bytes())
            self.assertEqual(by_name[spec["name"]]["schema"], spec["schema"])
            self.assertEqual(by_name[spec["name"]]["sha256"], runner.sha256_file(frozen))
            self.assertEqual(by_name[spec["name"]]["byte_length"], frozen.stat().st_size)
            self.assertEqual(stat.S_IMODE(frozen.stat().st_mode), 0o444)
        self.assertEqual(stat.S_IMODE((batch / "frozen-inputs").stat().st_mode), 0o500)
        self.assertEqual(
            precommit["feature_spec_sha256"], by_name["feature_spec"]["sha256"]
        )
        self.assertEqual(
            precommit["evaluator_source_manifest_sha256"],
            by_name["independent_evaluator_source_manifest"]["sha256"],
        )

        source = Path(self.frozen_input_paths["feature_spec_path"])
        source.write_bytes(
            runner.canonical_bytes(
                {"schema": "WAVE025_FEATURE_CLASSIFIER_SPEC_V1", "changed_after_prepare": True}
            )
        )
        runner.validate_frozen_inputs(batch)
        self.assertNotEqual(
            source.read_bytes(),
            (batch / by_name["feature_spec"]["relative_path"]).read_bytes(),
        )

    def test_each_frozen_input_byte_change_fails_closed_without_rewriting_precommit(self) -> None:
        for index, spec in enumerate(runner.FROZEN_INPUT_SPECS):
            with self.subTest(input_name=spec["name"]):
                batch = self.prepare(f"tamper-{index}")
                precommit_before = (batch / "precommit.json").read_bytes()
                precommit = json.loads(precommit_before)
                entry = next(
                    item for item in precommit["frozen_inputs"]["entries"]
                    if item["name"] == spec["name"]
                )
                frozen = batch / entry["relative_path"]
                os.chmod(frozen, 0o644)
                frozen.write_bytes(frozen.read_bytes() + b" ")
                os.chmod(frozen, 0o444)
                with self.assertRaises(runner.RunnerError):
                    self.anchor(batch)
                self.assertEqual((batch / "precommit.json").read_bytes(), precommit_before)
                self.assertFalse((batch / "anchor-receipt.json").exists())

    def test_duplicate_source_and_unknown_or_duplicate_registry_inputs_fail_closed(self) -> None:
        duplicate_args = self.prepare_args("duplicate-source")
        duplicate_args.host_only_inventory_path = duplicate_args.feature_spec_path
        with self.assertRaisesRegex(runner.RunnerError, "duplicate frozen input source path"):
            runner.prepare(duplicate_args)
        self.assertFalse(Path(duplicate_args.batch_dir).exists())

        for case in ("unknown", "duplicate"):
            with self.subTest(case=case):
                batch = self.prepare(f"registry-{case}")
                precommit, _ = runner.read_json(batch / "precommit.json", runner.SCHEMA_PRECOMMIT)
                private, _ = runner.read_json(
                    batch / "runner-private-state.json", runner.SCHEMA_PRIVATE_STATE
                )
                if case == "unknown":
                    precommit["frozen_inputs"]["entries"].append(
                        {
                            "name": "unknown_input",
                            "relative_path": "frozen-inputs/unknown.json",
                            "schema": "WAVE025_UNKNOWN_V1",
                            "sha256": "0" * 64,
                            "byte_length": 1,
                        }
                    )
                else:
                    duplicate_entry = dict(precommit["frozen_inputs"]["entries"][0])
                    precommit["frozen_inputs"]["entries"].append(duplicate_entry)
                    self.assertEqual(duplicate_entry["name"], "feature_spec")
                precommit_raw = runner.canonical_bytes(precommit)
                private["precommit_sha256"] = runner.sha256_bytes(precommit_raw)
                (batch / "precommit.json").write_bytes(precommit_raw)
                (batch / "runner-private-state.json").write_bytes(
                    runner.canonical_bytes(private)
                )
                with self.assertRaisesRegex(
                    runner.RunnerError, "unknown|duplicate|missing"
                ):
                    runner.validate_frozen_inputs(batch)

    def test_old_precommit_schema_and_every_lifecycle_stage_reject_unverified_inputs(self) -> None:
        old_batch = self.prepare("old-schema")
        precommit, _ = runner.read_json(
            old_batch / "precommit.json", runner.SCHEMA_PRECOMMIT
        )
        private, _ = runner.read_json(
            old_batch / "runner-private-state.json", runner.SCHEMA_PRIVATE_STATE
        )
        precommit["schema"] = "WAVE025_BATCH_PRECOMMIT_V1"
        precommit_raw = runner.canonical_bytes(precommit)
        private["precommit_sha256"] = runner.sha256_bytes(precommit_raw)
        (old_batch / "precommit.json").write_bytes(precommit_raw)
        (old_batch / "runner-private-state.json").write_bytes(runner.canonical_bytes(private))
        with self.assertRaises(runner.RunnerError):
            runner.validate_frozen_inputs(old_batch)

        batch = self.prepare("lifecycle-validation")
        stages = (
            lambda: self.anchor(batch),
            lambda: runner.run_batch(
                argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
            ),
            lambda: runner.close_batch(
                argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
            ),
            lambda: runner.reveal_batch(argparse.Namespace(batch_dir=str(batch))),
        )
        for stage in stages:
            with mock.patch.object(
                runner,
                "validate_frozen_input_registry",
                side_effect=runner.RunnerError("sentinel frozen input rejection"),
            ):
                with self.assertRaisesRegex(runner.RunnerError, "sentinel"):
                    stage()

    def test_anchor_rejects_wrong_precommit_and_never_creates_external_root(self) -> None:
        batch = self.prepare()
        wrong = {
            "kind": "USER_VISIBLE_COMMENTARY",
            "reference": "thread:message:123",
            "anchored_at": "2026-08-01T00:00:00Z",
            "precommit_sha256": "0" * 64,
        }
        with self.assertRaises(runner.RunnerError):
            runner.anchor(
                argparse.Namespace(
                    batch_dir=str(batch),
                    receipt_json=[json.dumps(wrong)],
                    receipt_file=None,
                )
            )
        self.assertFalse((batch / "anchor-receipt.json").exists())

    def test_fake_docker_smoke_preserves_raw_channels_and_reveals_after_close(self) -> None:
        batch = self.prepare("full-smoke")
        precommit_before = (batch / "precommit.json").read_bytes()
        frozen_before = {
            path.name: path.read_bytes() for path in (batch / "frozen-inputs").iterdir()
        }
        self.anchor(batch)
        run_result = runner.run_batch(
            argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
        )
        self.assertEqual(run_result["slot_count"], 12)
        self.assertEqual(run_result["infrastructure_counts"], {"COMPLETE": 12})

        public, _ = runner.read_json(batch / "public-plan.json", runner.SCHEMA_PUBLIC_PLAN)
        private, _ = runner.read_json(
            batch / "runner-private-state.json", runner.SCHEMA_PRIVATE_STATE
        )
        private_by_slot = {item["opaque_slot_id"]: item for item in private["mapping"]}
        roles = {slot_id: item["role"] for slot_id, item in private_by_slot.items()}
        self.assertEqual(set(roles.values()), {"S", "R"})
        precommit_text = (batch / "precommit.json").read_text(encoding="utf-8")
        for role_instances in self.control_instances.values():
            for instance in role_instances.values():
                self.assertNotIn(instance, precommit_text)
        negative_event_audit_checked = False
        for item in public["slots"]:
            slot = batch / "slots" / item["opaque_slot_id"]
            stdout = (slot / "collector-stdout.bin").read_bytes()
            stderr = (slot / "collector-stderr.bin").read_bytes()
            out = (slot / "collector-out.bin").read_bytes()
            features = (slot / "collector-features.json").read_bytes()
            self.assertEqual(stdout, out)
            self.assertEqual(out, features)
            self.assertEqual(stderr, b"")
            self.assertEqual((slot / "collector-ready.bin").read_bytes(), b"READY\n")
            self.assertEqual((slot / "collector-exit-code.bin").read_bytes(), b"0\n")
            self.assertEqual(
                (slot / "supervisor-control-stdout.bin").read_bytes(),
                runner.SUPERVISOR_READY_FRAME,
            )
            self.assertEqual((slot / "supervisor-control-stderr.bin").read_bytes(), b"")
            receipt_text = (slot / "slot-receipt.json").read_text(encoding="utf-8")
            self.assertNotIn('"role"', receipt_text)
            host_launch, _ = runner.read_json(
                slot / "host-launch.json", runner.SCHEMA_HOST_LAUNCH
            )
            features_value = json.loads(features)
            control_integrity = host_launch["diagnostics"]["registered_control_integrity"]
            self.assertTrue(control_integrity["valid"])
            self.assertFalse(control_integrity["private_instance_disclosed"])
            expected_instance = private_by_slot[item["opaque_slot_id"]][
                "private_canary_token_or_null"
            ]
            if item["challenge"] == "D0-HOST-LEAK":
                cwd_entries = features_value["directory_trees"]["cwd"]["entries"]
                marker_entries = [entry for entry in cwd_entries if entry["path"] != "."]
                self.assertEqual(
                    marker_entries,
                    [{
                        "mode_octal": "0o0400", "path": expected_instance,
                        "size_bytes": "0", "type": "file",
                    }],
                )
                host_text = runner.canonical_bytes(host_launch).decode("utf-8")
                self.assertNotIn(expected_instance, host_text)
                self.assertFalse(any(
                    receipt["command"][1:2] == ["start"] and "-a" in receipt["command"]
                    for receipt in host_launch["diagnostics"]["host_command_receipts"]
                ))
                commitment = host_launch["diagnostics"][
                    "private_predecessor_provenance_commitment_or_null"
                ]
                self.assertEqual(commitment["before_entry_count"], 0)
                self.assertEqual(commitment["after_predecessor_entry_count"], 1)
                self.assertEqual(commitment["after_candidate_entry_count"], 1)
                private_provenance_path = (
                    Path(str(batch) + ".runtime") / "attempts" / item["opaque_slot_id"]
                    / "d0-private-provenance.json"
                )
                self.assertEqual(stat.S_IMODE(private_provenance_path.stat().st_mode), 0o600)
                self.assertEqual(
                    runner.sha256_file(private_provenance_path),
                    commitment["private_provenance_sha256"],
                )
            elif item["challenge"] == "T-OCI-ISOLATED":
                self.assertIsNone(expected_instance)
                self.assertFalse(any(
                    mount["destination"] == "/shared-residue"
                    for mount in host_launch["mounts"]
                ))
                self.assertFalse(any(
                    runner.D0_MARKER_BASENAME.fullmatch(value)
                    for value in runner.all_string_values(features_value)
                ))
                self.assertIsNone(host_launch["diagnostics"][
                    "private_predecessor_provenance_commitment_or_null"
                ])
            self.assertEqual(host_launch["argv"], ["/bin/sh", "-c", runner.SUPERVISOR_SCRIPT])
            command_receipts = host_launch["diagnostics"]["host_command_receipts"]
            self.assertFalse(any(item["command"][1:2] == ["cp"] for item in command_receipts))
            exec_commands = [
                item["command"] for item in command_receipts if item["command"][1:2] == ["exec"]
            ]
            self.assertEqual(
                exec_commands,
                [
                    [
                        str(self.fake_docker),
                        "exec",
                        "--user",
                        "65534:65534",
                        host_launch["container_name"],
                        "/bin/cat",
                        spec["out_path"],
                    ]
                    for spec in runner.EXTRACTION_READS
                ],
            )
            extraction = host_launch["diagnostics"]["post_observation_extraction"]
            self.assertTrue(extraction["valid"])
            self.assertEqual(extraction["registered_exec_count"], 5)
            self.assertEqual(extraction["daemon_event_count"], 19)
            self.assertEqual(len(extraction["exec_groups"]), 5)
            events = [
                json.loads(line)
                for line in (slot / "docker-events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                len([event for event in events if event["Action"].startswith("exec_")]),
                15,
            )
            if not negative_event_audit_checked:
                ready_document = next(
                    value
                    for value in command_receipts
                    if value["command"][1:2] == ["logs"]
                    and base64.b64decode(value["stdout_base64"])
                    == runner.SUPERVISOR_READY_FRAME
                )
                extraction_documents = [
                    value for value in command_receipts if value["command"][1:2] == ["exec"]
                ]
                mutated_events = events[:-2] + events[2:5] + events[-2:]
                post = json.loads((slot / "docker-inspect-post.json").read_text(encoding="utf-8"))[0]
                rejected = runner.audit_docker_events(
                    b"".join(
                        json.dumps(value, separators=(",", ":")).encode("utf-8") + b"\n"
                        for value in mutated_events
                    ),
                    host_launch["container_id"],
                    host_launch["container_name"],
                    self.command_receipt(ready_document),
                    [self.command_receipt(value) for value in extraction_documents],
                    post["State"]["ExitCode"],
                )
                self.assertFalse(rejected["valid"])
                self.assertIn("event_action_sequence_mismatch", rejected["failures"])
                negative_event_audit_checked = True
            self.assertTrue((slot / "docker-inspect-pre.json").stat().st_size > 0)
            self.assertTrue((slot / "docker-inspect-post.json").stat().st_size > 0)

        close_result = runner.close_batch(
            argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
        )
        self.assertEqual(close_result["state"], "CLOSED")
        closed, _ = runner.read_json(batch / "closed.json", runner.SCHEMA_CLOSED)
        d0_slot_count = sum(
            item["challenge"] == "D0-HOST-LEAK" for item in private["mapping"]
        )
        self.assertEqual(
            closed["private_d0_provenance_commitment"]["expected_d0_slot_count"],
            d0_slot_count,
        )
        self.assertEqual(
            len(closed["private_d0_provenance_commitment"]["entries"]), d0_slot_count
        )
        reveal_result = runner.reveal_batch(argparse.Namespace(batch_dir=str(batch)))
        self.assertEqual(reveal_result["state"], "REVEALED")
        self.assertTrue(reveal_result["reconstruction_complete"])
        reveal, _ = runner.read_json(batch / "reveal.json", runner.SCHEMA_REVEAL)
        self.assertEqual(len(reveal["mapping"]), 12)
        self.assertEqual(reveal["private_control_registry"], self.private_control_registry)
        self.assertEqual(len(reveal["private_d0_provenance"]), d0_slot_count)
        self.assertEqual(
            reveal["private_d0_provenance_commitment"],
            closed["private_d0_provenance_commitment"],
        )
        commitment_by_slot = {
            entry["opaque_slot_id"]: entry
            for entry in reveal["private_d0_provenance_commitment"]["entries"]
        }
        for provenance in reveal["private_d0_provenance"]:
            self.assertEqual(
                runner.sha256_bytes(runner.canonical_bytes(provenance)),
                commitment_by_slot[provenance["opaque_slot_id"]][
                    "private_provenance_sha256"
                ],
            )
        self.assertEqual(reveal["closed_sha256"], runner.sha256_file(batch / "closed.json"))
        self.assertEqual((batch / "precommit.json").read_bytes(), precommit_before)
        self.assertEqual(
            {path.name: path.read_bytes() for path in (batch / "frozen-inputs").iterdir()},
            frozen_before,
        )
        remaining = list((self.root / "fake-docker-state").glob("*.json"))
        self.assertEqual(remaining, [], "only exact owned stopped containers should be removed")

    def test_close_aborts_missing_population_and_reveal_refuses(self) -> None:
        batch = self.prepare("aborted-smoke")
        self.anchor(batch)
        close_result = runner.close_batch(
            argparse.Namespace(batch_dir=str(batch), docker_bin=str(self.fake_docker))
        )
        self.assertEqual(close_result["state"], "ABORTED")
        with self.assertRaises(runner.RunnerError):
            runner.reveal_batch(argparse.Namespace(batch_dir=str(batch)))


if __name__ == "__main__":
    unittest.main()
