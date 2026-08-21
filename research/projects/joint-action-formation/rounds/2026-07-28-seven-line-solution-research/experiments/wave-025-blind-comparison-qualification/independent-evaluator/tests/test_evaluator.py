from __future__ import annotations

import ast
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import evaluator  # noqa: E402


def collector_document(marker: str = "constant", numeric: int = 1) -> dict:
    return {
        "schema": evaluator.COLLECTOR_SCHEMA,
        "collector_version": "1.0.0",
        "contract": {
            "lawful_truth_api_calls": 0,
            "network_calls": 0,
            "does_not_rank_treatments": True,
            "does_not_score_leakage": True,
        },
        "input_contract": {"byte_length": 54, "sha256": "0" * 64},
        "subject_input": {"byte_length": 0, "sha256": "0" * 64},
        "argv": ["node", "/app/collector.js"],
        "environment": [],
        "cwd": "/app",
        "hostname": {"os_hostname": marker},
        "identity": {"uid": 65534},
        "directory_trees": {"challenge": {"marker": marker, "size": numeric}},
        "process_view": {"available": True, "processes": []},
        "visible_canaries": [{"source": marker, "token_sha256": marker}],
        "timing": {"input_stat_elapsed_ns": [str(numeric)]},
        "collection_window": {"start": {"monotonic_ns": str(numeric)}},
    }


def docker_inspect(*, network: str = "none", extra_mount: bool = False) -> list[dict]:
    mounts = [
        {
            "Type": "bind",
            "Source": "/private/challenge",
            "Destination": "/challenge",
            "RW": False,
            "Mode": "ro",
            "Propagation": "rprivate",
        },
        {
            "Type": "tmpfs",
            "Source": "",
            "Destination": "/out",
            "RW": True,
            "Mode": "rw,nosuid,nodev,noexec",
            "Propagation": "",
        },
    ]
    if extra_mount:
        mounts.append(
            {
                "Type": "bind",
                "Source": "/var/run/docker.sock",
                "Destination": "/var/run/docker.sock",
                "RW": True,
                "Mode": "rw",
                "Propagation": "rprivate",
            }
        )
    return [
        {
            "Id": "a" * 64,
            "Name": "/wave025-neutral",
            "Image": "sha256:" + "b" * 64,
            "Created": "2026-08-01T00:00:00Z",
            "Config": {
                "Entrypoint": ["node"],
                "Cmd": ["/app/collector.js"],
                "Env": ["LANG=C.UTF-8", "NODE_ENV=production"],
                "WorkingDir": "/app",
                "User": "65534:65534",
                "Hostname": "wave025-fixed",
            },
            "HostConfig": {
                "NetworkMode": network,
                "ReadonlyRootfs": True,
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges:true"],
                "Privileged": False,
                "PidMode": "",
                "IpcMode": "private",
                "UTSMode": "",
                "UsernsMode": "",
                "PidsLimit": 64,
                "Memory": 268435456,
                "NanoCpus": 500000000,
            },
            "Mounts": mounts,
            "State": {
                "StartedAt": "2026-08-01T00:00:01Z",
                "FinishedAt": "2026-08-01T00:00:02Z",
                "ExitCode": 0,
                "OOMKilled": False,
                "Error": "",
            },
        }
    ]


class CanonicalEvidenceTests(unittest.TestCase):
    def test_canonical_round_trip_and_hash_include_lf(self) -> None:
        value = {"z": 1, "a": [True, None]}
        raw = b'{"a":[true,null],"z":1}\n'
        self.assertEqual(evaluator.canonical_json_bytes(value), raw)
        self.assertEqual(evaluator.sha256_canonical(value), evaluator.sha256_bytes(raw))

    def test_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(evaluator.EvaluationError, "duplicate"):
            evaluator.parse_json_bytes(b'{"a":1,"a":2}\n', label="duplicate")

    def test_noncanonical_formal_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "value.json"
            path.write_bytes(b'{"schema": "X"}\n')
            with self.assertRaisesRegex(evaluator.EvaluationError, "non-canonical"):
                evaluator.load_json(path, schema="X")

    def test_collector_raw_channels_are_compared_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            slot = pathlib.Path(temporary)
            raw = evaluator.canonical_json_bytes(collector_document())
            (slot / "collector-stdout.bin").write_bytes(raw)
            (slot / "collector-stderr.bin").write_bytes(b"")
            (slot / "collector-out.bin").write_bytes(raw)
            (slot / "collector-features.json").write_bytes(raw)
            parsed, hashes = evaluator.read_collector_channels(slot)
            self.assertEqual(parsed["schema"], evaluator.COLLECTOR_SCHEMA)
            self.assertEqual(hashes["collector-stdout.bin"], hashes["collector-out.bin"])
            (slot / "collector-out.bin").write_bytes(raw + b" ")
            with self.assertRaisesRegex(evaluator.EvaluationError, "differ"):
                evaluator.read_collector_channels(slot)


class RandomizationTests(unittest.TestCase):
    def test_commitments_are_domain_separated(self) -> None:
        seed = bytes(range(32))
        nonce = bytes(range(32, 64))
        plan = b'{"schema":"WAVE025_PUBLIC_PLAN_V1"}\n'
        values = {evaluator.commitment(domain, seed, nonce, plan) for domain in evaluator.DOMAINS}
        self.assertEqual(len(values), 3)

    def test_local_mapping_reconstructs_balanced_blocks(self) -> None:
        sample_plan = {
            challenge: {"calibration": 20, "holdout": 20}
            for challenge in evaluator.CHALLENGES
        }
        ids = evaluator.derive_public_ids(b"p" * 32, 120)
        slots = []
        offset = 0
        for challenge in evaluator.CHALLENGES:
            for slot_id in ids[offset : offset + 40]:
                slots.append({"opaque_slot_id": slot_id, "challenge": challenge})
            offset += 40
        public_plan = {"slots": slots}
        block_plan = {"block_size": 20, "roles_per_block": {"R": 10, "S": 10}}
        mapping, order = evaluator.derive_mapping(
            public_plan,
            sample_plan,
            block_plan,
            b"a" * 32,
            b"m" * 32,
        )
        self.assertEqual(len(mapping), 120)
        self.assertEqual(set(order), set(ids))
        blocks = {}
        for item in mapping:
            blocks.setdefault(item["block"], []).append(item["role"])
        self.assertTrue(all(sorted(roles) == ["R"] * 10 + ["S"] * 10 for roles in blocks.values()))
        replay, replay_order = evaluator.derive_mapping(
            public_plan,
            sample_plan,
            block_plan,
            b"a" * 32,
            b"m" * 32,
        )
        self.assertEqual(mapping, replay)
        self.assertEqual(order, replay_order)

    def test_formal_population_is_exactly_1600(self) -> None:
        plan = evaluator._validate_sample_plan(evaluator.FORMAL_SAMPLE_PLAN, "formal")
        self.assertEqual(sum(sum(item.values()) for item in plan.values()), 1600)
        changed = json.loads(json.dumps(evaluator.FORMAL_SAMPLE_PLAN))
        changed["T-OCI-ISOLATED"]["holdout"] = 400
        with self.assertRaisesRegex(evaluator.EvaluationError, "1600"):
            evaluator._validate_sample_plan(changed, "formal")


class StatisticsTests(unittest.TestCase):
    def test_exact_chance_upper_bound_passes_at_800(self) -> None:
        lower, upper = evaluator.clopper_pearson_one_sided(400, 800, 0.95)
        self.assertLess(lower, 0.5)
        self.assertLessEqual(upper, 0.55)

    def test_positive_control_perfect_lower_bound_exceeds_gate(self) -> None:
        lower, upper = evaluator.clopper_pearson_one_sided(100, 100, 0.95)
        self.assertGreaterEqual(lower, 0.90)
        self.assertEqual(upper, 1.0)

    def test_balanced_accuracy_refuses_unbalanced_labels(self) -> None:
        with self.assertRaisesRegex(evaluator.EvaluationError, "equal class"):
            evaluator.balanced_accuracy_with_ci([0, 0, 1], [0, 0, 1], 0.95)

    def test_all_four_models_detect_repeated_categorical_leak(self) -> None:
        train_rows = []
        train_labels = []
        test_rows = []
        test_labels = []
        for target_rows, target_labels, size in (
            (train_rows, train_labels, 100),
            (test_rows, test_labels, 100),
        ):
            for index in range(size):
                label = index % 2
                target_labels.append(label)
                target_rows.append(
                    {
                        "visible_canaries[0].token_sha256": "s-token" if label else "r-token",
                        "timing.input_stat_elapsed_ns[0]": str(index + 1000),
                    }
                )
        result = evaluator.run_classifiers(
            train_rows,
            train_labels,
            test_rows,
            test_labels,
            confidence=0.95,
            permutation_seed=b"classification-test",
        )
        self.assertEqual(set(result["models"]), {"deterministic", "logistic", "bounded_tree", "knn"})
        for metric in result["models"].values():
            self.assertGreaterEqual(metric["balanced_accuracy"], 0.95)
            self.assertIn("holm_adjusted_p", metric)

    def test_holm_is_monotone_in_sorted_order(self) -> None:
        adjusted = evaluator.holm_adjust({"a": 0.01, "b": 0.03, "c": 0.2})
        self.assertLessEqual(adjusted["a"], adjusted["b"])
        self.assertLessEqual(adjusted["b"], adjusted["c"])


class HostEvidenceTests(unittest.TestCase):
    def test_raw_inspect_reconstructs_qualified_oci_shape(self) -> None:
        normalized = evaluator.normalize_inspect(docker_inspect())
        self.assertEqual(evaluator.validate_isolation(normalized, "T-OCI-ISOLATED"), [])
        self.assertEqual(normalized["image_id"], "sha256:" + "b" * 64)
        self.assertEqual(normalized["argv"], ["node", "/app/collector.js"])

    def test_network_and_extra_mount_fail_closed(self) -> None:
        normalized = evaluator.normalize_inspect(docker_inspect(network="bridge", extra_mount=True))
        failures = evaluator.validate_isolation(normalized, "T-OCI-ISOLATED")
        self.assertTrue(any("network" in item for item in failures))
        self.assertTrue(any("mount" in item or "Docker socket" in item for item in failures))

    def test_git_anchor_is_read_back_not_self_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            precommit = b'{"schema":"WAVE025_BATCH_PRECOMMIT_V1"}\n'
            stored = subprocess.run(
                ["git", "-C", str(repository), "hash-object", "-w", "--stdin"],
                input=precommit,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout.decode().strip()
            anchor = {
                "anchor_type": "DUAL_CODEX_COMMENTARY_AND_GIT_BLOB",
                "precommit_sha256": evaluator.sha256_bytes(precommit),
                "git_object": {"repository": str(repository), "object_id": stored},
                "codex_commentary": {
                    "precommit_sha256": evaluator.sha256_bytes(precommit),
                    "message_reference": "user-visible-message-1",
                },
            }
            result = evaluator.verify_external_anchor(anchor, precommit)
            self.assertTrue(result["eligible"])
            self.assertTrue(result["git_object_verified"])
            bad = evaluator.verify_external_anchor(anchor, precommit + b"tamper")
            self.assertFalse(bad["eligible"])


class FailClosedSurfaceTests(unittest.TestCase):
    def test_missing_batch_is_not_qualified_and_never_ranks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = pathlib.Path(temporary) / "missing"
            result = evaluator.evaluate_batch(missing)
            self.assertEqual(result["final_status"], "NOT_QUALIFIED")
            self.assertEqual(result["full_blind_comparison_qualification"], "NOT_TESTED")
            self.assertEqual(evaluator._forbidden_output_keys(result), [])

    def test_cli_missing_batch_returns_one_without_attempting_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = pathlib.Path(temporary) / "missing"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = evaluator.main([str(missing)])
            self.assertEqual(status, 1)
            self.assertFalse(missing.exists())
            self.assertEqual(json.loads(output.getvalue())["final_status"], "NOT_QUALIFIED")

    def test_evaluation_write_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            result = evaluator.evaluate_batch(root / "missing")
            path = evaluator.write_evaluation_exclusive(root, result)
            self.assertTrue(path.is_file())
            with self.assertRaises(FileExistsError):
                evaluator.write_evaluation_exclusive(root, result)

    def test_source_does_not_import_runner_or_collector(self) -> None:
        tree = ast.parse((HERE / "evaluator.py").read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        self.assertFalse(any("runner" in name or "collector" in name for name in imports))

    def test_contract_ambiguities_are_explicit_and_formal_blocking(self) -> None:
        blocking = [item for item in evaluator.CONTRACT_AMBIGUITIES if item["blocking"]]
        self.assertGreaterEqual(len(blocking), 4)
        self.assertTrue(all(item["id"].startswith("AMB-") for item in blocking))


if __name__ == "__main__":
    unittest.main()
