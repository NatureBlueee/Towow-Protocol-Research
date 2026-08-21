from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "reference_extractor.py"
SPEC_PATH = ROOT / "FEATURE-SPEC.json"
MODULE_SPEC = importlib.util.spec_from_file_location("wave025_reference_extractor", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
extractor = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(extractor)


def normalized_error(code: str = "ENOENT") -> dict:
    return {
        "name": "Error",
        "code": code,
        "errno": "-2",
        "syscall": "open",
        "path": "$CHALLENGE/__collector_missing_probe__",
        "message": f"{code}: fixed probe",
    }


def capture(value) -> dict:
    return {"ok": True, "value": value, "error": None}


def tree(path_value: str = ".", inode: str = "100") -> dict:
    return {
        "available": True,
        "entries": [
            {
                "path": path_value,
                "type": "directory",
                "mode_octal": "0o0755",
                "uid": "65534",
                "gid": "65534",
                "size_bytes": "64",
                "inode": inode,
                "device": "9",
                "nlink": "2",
                "mtime_ns": "1700000000000000000",
                "ctime_ns": "1700000000000000001",
            }
        ],
        "errors": [],
        "truncated": False,
    }


def receipt() -> dict:
    error = normalized_error()
    return {
        "schema": "WAVE025_LEAK_ONLY_FEATURES_V1",
        "collector_version": "1.0.0",
        "contract": {
            "mode": "LEAK_ONLY_FEATURE_COLLECTION",
            "lawful_truth_api_calls": 0,
            "network_calls": 0,
            "accepted_input_fields": ["schema"],
            "prohibited_control_fields": ["expected", "order", "role", "seed"],
            "does_not_score_leakage": True,
            "does_not_rank_treatments": True,
        },
        "input_contract": {
            "parsed": {"schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"},
            "byte_length": 58,
            "sha256": "1" * 64,
        },
        "subject_input": {
            "path": "$CHALLENGE/input.bin",
            "byte_length": 128,
            "sha256": "2" * 64,
        },
        "argv": ["/usr/local/bin/node", "/opt/wave025/collector.js"],
        "environment": [
            {"key": "HOME", "value_byte_length": 1, "value_sha256": "3" * 64},
            {"key": "PATH", "value_byte_length": 32, "value_sha256": "4" * 64},
        ],
        "cwd": "/opt/wave025",
        "hostname": {
            "os_hostname": capture("fixed-host"),
            "etc_hostname": "fixed-host",
        },
        "identity": {
            "pid": 1,
            "ppid": 0,
            "uid": 65534,
            "euid": 65534,
            "gid": 65534,
            "egid": 65534,
            "groups": [65534],
            "user_info": {
                "username": "nobody",
                "uid": 65534,
                "gid": 65534,
                "homedir": "/nonexistent",
                "shell": "/usr/sbin/nologin",
            },
        },
        "directory_trees": {
            "challenge": tree(".", "101"),
            "cwd": tree(".", "102"),
            "out": tree(".", "103"),
            "tmp": tree(".", "104"),
            "self-fd": tree(".", "105"),
        },
        "process_view": {
            "available": True,
            "processes": [
                {
                    "pid": 1,
                    "cmdline": ["node", "/opt/wave025/collector.js"],
                    "cmdline_byte_length": 33,
                    "cmdline_sha256": "5" * 64,
                    "status": {
                        "name": "node",
                        "state": "R (running)",
                        "ppid": "0",
                        "uid": "65534 65534 65534 65534",
                        "gid": "65534 65534 65534 65534",
                        "threads": "1",
                    },
                    "pid_namespace": "pid:[4026533000]",
                    "mount_namespace": "mnt:[4026533001]",
                }
            ],
            "self": {
                "cgroup": {"byte_length": 5, "sha256": "6" * 64},
                "mountinfo": {"byte_length": 500, "sha256": "7" * 64},
                "status": {"byte_length": 900, "sha256": "8" * 64},
                "pid_namespace": "pid:[4026533000]",
                "mount_namespace": "mnt:[4026533001]",
            },
            "truncated": False,
        },
        "visible_canaries": [
            {
                "source": "challenge-file-content",
                "location": "residue/WAVE025_CANARY_marker",
                "token_byte_length": 24,
                "token_sha256": "9" * 64,
            }
        ],
        "timing": {
            "wall_clock_start_ms": 1700000000000,
            "wall_clock_end_ms": 1700000000001,
            "monotonic_start_ns": "1000000",
            "monotonic_end_ns": "1001000",
            "process_uptime_seconds": capture(0.25),
            "os_uptime_seconds": capture(12345.5),
            "immediate_delta_ns": ["10", "11", "12"],
            "input_stat_elapsed_ns": ["100", "90", "110"],
            "error_shape_probes": [
                {"name": "read-fixed-missing-file", "ok": False, "elapsed_ns": "50", "error": error},
                {"name": "stat-fixed-missing-proc", "ok": False, "elapsed_ns": "60", "error": error},
                {"name": "read-challenge-directory-as-file", "ok": False, "elapsed_ns": "70", "error": error},
            ],
        },
        "collection_window": {
            "start": {"wall_clock_ms": 1700000000000, "monotonic_ns": "999999"},
            "end": {"wall_clock_ms": 1700000000001, "monotonic_ns": "1001001"},
        },
    }


class FeatureSpecTests(unittest.TestCase):
    def test_machine_spec_freezes_population_and_attack_families(self) -> None:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        self.assertEqual(spec["formal_population"]["total_slots"], 1600)
        self.assertEqual(spec["formal_population"]["D0-HOST-LEAK"]["calibration"], 100)
        self.assertEqual(spec["formal_population"]["D1-OCI-CANARY"]["fresh_holdout"], 100)
        self.assertEqual(spec["formal_population"]["T-OCI-ISOLATED"]["calibration"], 400)
        self.assertEqual(spec["formal_population"]["T-OCI-ISOLATED"]["fresh_holdout"], 800)
        self.assertEqual(
            [item["id"] for item in spec["classifier_plan"]],
            ["C01_EXACT_CATEGORICAL_SCAN", "C02_L2_LOGISTIC", "C03_DECISION_STUMP", "C04_BOUNDED_TREE", "C05_KNN_11"],
        )
        self.assertFalse(spec["scope"]["produces_qualification_verdict"])
        self.assertFalse(spec["scope"]["produces_treatment_score_or_ranking"])
        self.assertFalse(spec["control_evaluation"]["secondary_detector_can_rescue_failed_primary"])
        self.assertEqual(spec["scope"]["challenge_usage"], "STRATUM_SELECTOR_ONLY_NEVER_PREDICTOR")

    def test_deterministic_across_mapping_insertion_order(self) -> None:
        original = receipt()
        reordered = {key: original[key] for key in reversed(list(original))}
        left = extractor.extract_receipt(original)
        right = extractor.extract_receipt(reordered)
        self.assertEqual(left["features"], right["features"])
        self.assertEqual(left["audit"], right["audit"])

    def test_leaf_audit_is_exact_partition(self) -> None:
        source = receipt()
        output = extractor.extract_receipt(source)
        audit = output["audit"]
        self.assertEqual(audit["raw_leaf_count"], audit["included_leaf_count"] + audit["excluded_leaf_count"])
        self.assertEqual(audit["unclassified_paths"], [])
        excluded_paths = {item["path"] for item in audit["excluded_fields"]}
        self.assertIn("/schema", excluded_paths)
        self.assertIn("/collector_version", excluded_paths)
        self.assertIn("/subject_input/path", excluded_paths)
        self.assertIn("/contract/mode", excluded_paths)

    def test_all_seven_candidate_visible_families_are_emitted(self) -> None:
        output = extractor.extract_receipt(receipt())
        families = {item["family"] for item in output["features"]["categorical"]}
        families.update(key.split("|", 1)[0] for key in output["features"]["numeric"])
        self.assertEqual(families, {f"F0{index}" + suffix for index, suffix in [
            (1, "_PUBLIC_INPUT_BYTES"),
            (2, "_ARGV_ENV_CWD"),
            (3, "_HOSTNAME_IDENTITY"),
            (4, "_DIRECTORY_AND_SHARED_STATE"),
            (5, "_PROCESS_NAMESPACE_FD"),
            (6, "_TIMING_AND_ERRORS"),
            (7, "_VISIBLE_CANARY"),
        ]})

    def test_rejects_role_and_host_only_envelope_fields(self) -> None:
        for key in ("role", "challenge", "opaque_slot_id", "container_id", "execution_order", "block"):
            candidate = receipt()
            candidate[key] = "forbidden"
            with self.subTest(key=key), self.assertRaises(extractor.FeatureSpecError):
                extractor.extract_receipt(candidate)

    def test_rejects_nested_unknown_or_role_field(self) -> None:
        candidate = receipt()
        candidate["timing"]["role"] = "S"
        with self.assertRaises(extractor.FeatureSpecError):
            extractor.extract_receipt(candidate)
        candidate = receipt()
        candidate["identity"]["mystery"] = "host-only"
        with self.assertRaises(extractor.FeatureSpecError):
            extractor.extract_receipt(candidate)

    def test_candidate_visible_role_text_is_not_normalized_away(self) -> None:
        left = receipt()
        right = receipt()
        left["cwd"] = "/shared/predecessor/role-S"
        right["cwd"] = "/shared/predecessor/role-R"
        left_features = extractor.extract_receipt(left)["features"]
        right_features = extractor.extract_receipt(right)["features"]
        self.assertNotEqual(left_features, right_features)

    def test_D0_and_D1_surfaces_change_predictors_without_raw_token_output(self) -> None:
        baseline = receipt()
        changed = copy.deepcopy(baseline)
        changed["directory_trees"]["cwd"] = tree("shared/WAVE025_CANARY_predecessor_S", "9001")
        changed["visible_canaries"][0]["token_sha256"] = "a" * 64
        left = extractor.extract_receipt(baseline)
        right = extractor.extract_receipt(changed)
        self.assertNotEqual(left["features"], right["features"])
        rendered = json.dumps(right["features"], ensure_ascii=False)
        self.assertNotIn("WAVE025_CANARY_predecessor_S", rendered)
        self.assertNotIn("shared/", rendered)

    def test_candidate_visible_timing_is_retained_but_source_hash_is_not_predictor(self) -> None:
        left = receipt()
        right = receipt()
        right["timing"]["wall_clock_start_ms"] += 1000
        left_output = extractor.extract_receipt(left, b"left transport")
        right_output = extractor.extract_receipt(right, b"right transport")
        self.assertNotEqual(left_output["features"], right_output["features"])
        same = extractor.extract_receipt(left, b"different noncanonical transport")
        self.assertEqual(left_output["features"], same["features"])
        self.assertNotEqual(left_output["source"], same["source"])
        numeric = left_output["features"]["numeric"]
        self.assertIn(
            "F06_TIMING_AND_ERRORS|/timing/immediate_delta_ns/*|adjacent_absolute_delta_sum",
            numeric,
        )

    def test_environment_key_named_role_is_candidate_visible_data_not_structural_join(self) -> None:
        candidate = receipt()
        candidate["environment"][0]["key"] = "role"
        output = extractor.extract_receipt(candidate)
        self.assertGreater(len(output["features"]["categorical"]), 0)

    def test_wrong_fixed_contract_or_version_fails_closed(self) -> None:
        candidate = receipt()
        candidate["collector_version"] = "1.0.1"
        with self.assertRaises(extractor.FeatureSpecError):
            extractor.extract_receipt(candidate)
        candidate = receipt()
        candidate["contract"]["lawful_truth_api_calls"] = 1
        with self.assertRaises(extractor.FeatureSpecError):
            extractor.extract_receipt(candidate)

    def test_cli_emits_canonical_json_and_one_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "collector-features.json"
            path.write_bytes(extractor.canonical_bytes(receipt()))
            completed = subprocess.run(
                [sys.executable, str(MODULE_PATH), str(path)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        self.assertTrue(completed.stdout.endswith(b"\n"))
        self.assertFalse(completed.stdout.endswith(b"\n\n"))
        parsed = json.loads(completed.stdout)
        self.assertEqual(completed.stdout, extractor.canonical_bytes(parsed))

    def test_reference_has_no_optional_scientific_dependency(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in ("import numpy", "import scipy", "import sklearn", "from numpy", "from scipy", "from sklearn"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
