#!/usr/bin/env python3

import copy
import hashlib
import importlib.util
import math
import pathlib
import sys
import unittest


ENGINE_PATH = pathlib.Path(__file__).resolve().parents[1] / "engine.py"
SPEC = importlib.util.spec_from_file_location("wave025_full_evaluator_engine", ENGINE_PATH)
engine = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def error_shape(code="ENOENT"):
    return {"name": "Error", "code": code, "errno": "-2", "syscall": "open",
            "path": "$CHALLENGE/missing", "message": "missing"}


def tree(entries=None):
    return {"available": True, "entries": entries or [], "errors": [], "truncated": False}


def entry(path=".", **extra):
    value = {
        "path": path, "type": "file", "mode_octal": "0o0444", "uid": "65534",
        "gid": "65534", "size_bytes": "7", "inode": "101", "device": "2",
        "nlink": "1", "mtime_ns": "1000", "ctime_ns": "1001",
    }
    value.update(extra)
    return value


def make_receipt(directory_entries=None):
    return {
        "schema": "WAVE025_LEAK_ONLY_FEATURES_V1",
        "collector_version": "1.0.0",
        "contract": {
            "mode": "LEAK_ONLY_FEATURE_COLLECTION", "lawful_truth_api_calls": 0,
            "network_calls": 0, "accepted_input_fields": ["schema"],
            "prohibited_control_fields": ["expected", "order", "role", "seed"],
            "does_not_score_leakage": True, "does_not_rank_treatments": True,
        },
        "input_contract": {"parsed": {"schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"},
                           "byte_length": 54, "sha256": digest("collector-input")},
        "subject_input": {"path": "$CHALLENGE/input.bin", "byte_length": 9,
                          "sha256": digest("subject")},
        "argv": ["node", "/app/collector.js"],
        "environment": [{"key": "LANG", "value_byte_length": 7,
                         "value_sha256": digest("C.UTF-8")}],
        "cwd": "/app",
        "hostname": {"os_hostname": {"ok": True, "value": "isolated", "error": None},
                     "etc_hostname": "isolated"},
        "identity": {
            "pid": 1, "ppid": 0, "uid": 65534, "euid": 65534, "gid": 65534,
            "egid": 65534, "groups": [65534],
            "user_info": {"username": "nobody", "uid": 65534, "gid": 65534,
                          "homedir": "/nonexistent", "shell": "/usr/sbin/nologin"},
        },
        "directory_trees": {
            "challenge": tree(directory_entries or [entry("deep/a/b/c/value")]),
            "cwd": tree([entry(".")]), "out": tree([entry(".")]),
            "tmp": tree([entry(".")]), "self-fd": tree([entry("0", symlink_target="/dev/null")]),
        },
        "process_view": {
            "available": True,
            "processes": [{
                "pid": 1, "cmdline": ["node", "/app/collector.js"],
                "cmdline_byte_length": 23, "cmdline_sha256": digest("cmdline"),
                "status": {"name": "node", "state": "R", "ppid": "0", "uid": "65534",
                           "gid": "65534", "threads": "1"},
                "pid_namespace": "pid:[1]", "mount_namespace": "mnt:[2]",
            }],
            "self": {
                "cgroup": {"byte_length": 5, "sha256": digest("cg")},
                "mountinfo": {"byte_length": 6, "sha256": digest("mi")},
                "status": {"byte_length": 7, "sha256": digest("st")},
                "pid_namespace": "pid:[1]", "mount_namespace": "mnt:[2]",
            },
            "truncated": False,
        },
        "visible_canaries": [{"source": "environment-value", "location": "CANARY",
                              "token_byte_length": 22, "token_sha256": digest("canary")}],
        "timing": {
            "wall_clock_start_ms": 100, "wall_clock_end_ms": 101,
            "monotonic_start_ns": "1000", "monotonic_end_ns": "2000",
            "process_uptime_seconds": {"ok": True, "value": 1.5, "error": None},
            "os_uptime_seconds": {"ok": True, "value": 20.0, "error": None},
            "immediate_delta_ns": ["1", "2", "3"],
            "input_stat_elapsed_ns": ["4", "5", "6"],
            "error_shape_probes": [
                {"name": "read-fixed-missing-file", "ok": False, "elapsed_ns": "12",
                 "error": error_shape()},
            ],
        },
        "collection_window": {
            "start": {"wall_clock_ms": 100, "monotonic_ns": "1000"},
            "end": {"wall_clock_ms": 101, "monotonic_ns": "2000"},
        },
    }


def fv(categories=(), numeric=None):
    return engine.FeatureVector(
        numeric=numeric or {}, categorical={token: 1 for token in categories},
        audit={"unclassified_paths_empty": True},
    )


class FullLeafFixtureTests(unittest.TestCase):
    def test_deep_leaves_and_all_f01_f07_are_extracted_without_96_or_128_cap(self):
        entries = [entry(f"nested/a/b/c/leaf-{index}", inode=str(1000 + index)) for index in range(220)]
        receipt = make_receipt(entries)
        vector = engine.RawReceiptFeatureProvider().extract(receipt)
        self.assertEqual(set(vector.audit["families_present"]), set(engine.FAMILIES))
        self.assertGreater(vector.audit["included_leaf_count"], 128)
        self.assertTrue(vector.audit["unclassified_paths_empty"])
        before = vector.predictors_json()
        changed = copy.deepcopy(receipt)
        changed["process_view"]["processes"][0]["status"]["threads"] = "role-coded-deep-leaf"
        after = engine.RawReceiptFeatureProvider().extract(changed).predictors_json()
        self.assertNotEqual(before, after)

    def test_unknown_nested_leaf_fails_closed(self):
        receipt = make_receipt()
        receipt["process_view"]["processes"][0]["private_oracle"] = "forbidden"
        with self.assertRaises(engine.ReceiptSchemaError):
            engine.RawReceiptFeatureProvider().extract(receipt)

    def test_nonfinite_leaf_fails_closed(self):
        receipt = make_receipt()
        receipt["timing"]["wall_clock_start_ms"] = float("nan")
        with self.assertRaises(engine.NonFiniteFeature):
            engine.RawReceiptFeatureProvider().extract(receipt)


class ClassifierFixtureTests(unittest.TestCase):
    def test_c01_top256_two_token_conjunction_is_required_and_selected(self):
        left = "F02_ARGV_ENV_CWD|left|a"
        right = "F03_HOSTNAME_IDENTITY|right|b"
        vectors = [fv([left, right]) for _ in range(20)]
        labels = [1] * 20
        vectors += [fv([left]) for _ in range(10)] + [fv([right]) for _ in range(10)]
        labels += [0] * 20
        model = engine.fit_exact_rule(vectors, labels)
        self.assertEqual(model.rule["kind"], "conjunction")
        self.assertEqual(model.calibration_balanced_accuracy, 1.0)

    def test_depth_three_tree_recovers_three_way_interaction_stump_cannot(self):
        rows, labels = [], []
        for a in (0.0, 1.0):
            for b in (0.0, 1.0):
                for c in (0.0, 1.0):
                    for _ in range(10):
                        rows.append({"a": a, "b": b, "c": c})
                        labels.append(int(a == b == c == 1.0))
        stump = engine.fit_tree(rows, labels, maximum_depth=1, minimum_leaf=10)
        depth3 = engine.fit_tree(rows, labels, maximum_depth=3, minimum_leaf=10, minimum_gain=1e-12)
        self.assertLess(engine.balanced_accuracy(labels, stump.predict(rows)), 1.0)
        self.assertEqual(engine.balanced_accuracy(labels, depth3.predict(rows)), 1.0)

    def test_knn_uses_k11_and_includes_all_boundary_ties(self):
        training = [{0: value} for value in (0.01, 0.02, 0.03, 0.04, 0.05)]
        labels = [0] * 5
        training += [{0: value} for value in (0.06, 0.07, 0.08, 0.09, 0.10, 0.11)]
        labels += [1] * 6
        training += [{0: -0.11}, {0: 0.11}]
        labels += [0, 1]
        model = engine.KNNModel(training, labels, 11)
        self.assertEqual(model.predict_one({0: 0.0}), 1)
        distances = sorted(model.distance_squared({0: 0.0}, row) for row in training)
        boundary = distances[10]
        self.assertEqual(sum(distance <= boundary + 1e-15 for distance in distances), 13)

    def test_diffuse_logistic_signal_converges_without_feature_cap(self):
        # Each coordinate alone is exactly chance, while their common direction
        # carries a 0.95 role signal.  Symmetric orthogonal noise also makes the
        # frozen Armijo step land on the float64 optimum, so strict 1e-10
        # convergence is exercised rather than relaxed.
        dimension, q = 32, 0.95
        c = q - 0.5
        amplitude = math.sqrt(math.log((q - 0.01 * c) / (1.0 - (q - 0.01 * c))) / c)
        unit = 1.0 / math.sqrt(dimension)
        calibration, labels = [], []
        for direction in (-1, 1):
            for correct, pairs in ((True, 19), (False, 1)):
                label = int((direction == 1) == correct)
                for pattern_index in range(pairs):
                    pattern = [
                        1.0 if bin((pattern_index + 1) & feature).count("1") % 2 == 0 else -1.0
                        for feature in range(dimension)
                    ]
                    mean = sum(pattern) / dimension
                    pattern = [value - mean for value in pattern]
                    for flip in (1.0, -1.0):
                        calibration.append({
                            feature: direction * amplitude * unit + flip * pattern[feature]
                            for feature in range(dimension)
                        })
                        labels.append(label)
        best_single = max(
            engine.balanced_accuracy(labels, [1 if row[feature] > 0 else 0 for row in calibration])
            for feature in range(dimension)
        )
        model = engine.fit_logistic(calibration, labels, dimension)
        self.assertLess(best_single, 0.75)
        self.assertTrue(model.converged)
        self.assertGreater(engine.balanced_accuracy(labels, model.predict(calibration)), 0.90)

    def test_logistic_nonconvergence_and_nan_are_abnormal_not_chance(self):
        model = engine.fit_logistic([{0: -1.0}, {0: 1.0}], [0, 1], 1, maximum_iterations=0)
        self.assertFalse(model.converged)
        with self.assertRaises(engine.NonFiniteFeature):
            engine.fit_logistic([{0: float("nan")}, {0: 1.0}], [0, 1], 1)


class StatisticalAndReplayTests(unittest.TestCase):
    def test_classwise_clopper_pearson_and_balanced_interval(self):
        lower, upper = engine.clopper_pearson(50, 50)
        self.assertAlmostEqual(lower, 0.9288782635, places=9)
        self.assertEqual(upper, 1.0)
        interval = engine.classwise_balanced_interval([0] * 50 + [1] * 50, [0] * 50 + [1] * 50)
        self.assertAlmostEqual(interval["lower_balanced_accuracy"], lower, places=12)

    def test_9999_frozen_prediction_block_permutation_and_holm(self):
        labels = [0] * 10 + [1] * 10
        predictions = list(labels)
        metadata = [
            {"challenge": "T", "phase": "fresh_holdout", "block": "b0", "opaque_slot_id": f"s-{i:02d}"}
            for i in range(20)
        ]
        result = engine.frozen_prediction_permutation(labels, predictions, metadata, b"seed", 9999)
        self.assertEqual(result["replicates"], 9999)
        self.assertFalse(result["retrained_per_replicate"])
        self.assertLessEqual(result["p_value"], 0.001)
        holm = engine.holm_step_down({"z": 0.06, "a": 0.001, "b": 0.02})
        self.assertTrue(holm["rejected"]["a"])
        self.assertTrue(holm["rejected"]["b"])
        self.assertFalse(holm["rejected"]["z"])

    def test_host_only_statistic_uses_separate_holm_and_never_predictor_matrix(self):
        labels = [0] * 10 + [1] * 10
        metadata = [
            {"challenge": "T", "phase": "fresh_holdout", "block": "b0", "opaque_slot_id": f"h-{i:02d}"}
            for i in range(20)
        ]
        rows = [{"order": label} for label in labels]
        result = engine.evaluate_host_only(
            [{"test_id": "HOST_ORDER", "kind": "numeric", "field": "order"}],
            rows, labels, metadata, b"host-seed", 9999,
        )
        self.assertFalse(result["predictor_matrix_imported"])
        self.assertTrue(result["holm"]["rejected"]["HOST_ORDER"])
        engine.canonical_bytes(result)

    def test_host_only_population_excludes_d0_and_d1_values(self):
        records = [
            {"challenge": "D0-HOST-LEAK", "phase": "fresh_holdout", "host_only": {"order": 999}},
            {"challenge": "D1-OCI-CANARY", "phase": "fresh_holdout", "host_only": {"order": -999}},
            {"challenge": "T-OCI-ISOLATED", "phase": "calibration", "host_only": {"order": 777}},
        ]
        records += [
            {"challenge": "T-OCI-ISOLATED", "phase": "fresh_holdout", "host_only": {"order": index % 2}}
            for index in range(20)
        ]
        selected = engine.t_host_holdout_indices(records)
        before = [records[index]["host_only"] for index in selected]
        records[0]["host_only"]["order"] = 10 ** 9
        records[1]["host_only"]["order"] = -(10 ** 9)
        after = [records[index]["host_only"] for index in engine.t_host_holdout_indices(records)]
        self.assertEqual(before, after)
        self.assertEqual(len(after), 20)

    def test_permutation_seed_uses_explicit_ascii_hex_convention(self):
        precommit = "01" * 32
        feature_spec = "ab" * 32
        expected = hashlib.sha256(
            b"WAVE025_PERMUTATION_SEED_V1\x00" + precommit.encode("ascii")
            + b"\x00" + feature_spec.encode("ascii")
        ).digest()
        self.assertEqual(engine.permutation_seed(precommit, feature_spec), expected)
        raw_digest_convention = hashlib.sha256(
            b"WAVE025_PERMUTATION_SEED_V1\x00" + bytes.fromhex(precommit)
            + b"\x00" + bytes.fromhex(feature_spec)
        ).digest()
        self.assertNotEqual(expected, raw_digest_convention)

    def test_provider_and_replay_mismatch_fail_closed(self):
        instance = engine.FullEvaluatorEngine()
        receipt = engine.verify_execution_provider(instance.profile)
        self.assertEqual(receipt["numpy_version"], "2.0.2")
        wrong = copy.deepcopy(instance.profile)
        wrong["execution_provider"]["numpy"]["version"] = "0.0.0"
        with self.assertRaises(engine.ProviderMismatch):
            engine.verify_execution_provider(wrong)
        first = {"hash_manifest": {"A": "0"}, "payload": 1}
        second = {"hash_manifest": {"A": "1"}, "payload": 1}
        with self.assertRaises(engine.ReplayMismatch):
            engine.enforce_replay_identity(first, second, ["A"])

    def test_profile_keeps_model_selection_randomization_not_tested_and_has_no_caps(self):
        instance = engine.FullEvaluatorEngine()
        self.assertEqual(instance.profile["deferred_challenge"]["status"], "NOT_TESTED")
        self.assertEqual(instance.profile["inherited_attack_surface"]["candidate_visible_leaf_cap"], "NONE")
        self.assertEqual(instance.profile["inherited_attack_surface"]["numeric_path_cap"], "NONE")

    def test_full_engine_runs_twice_with_all_hash_classes_and_no_verdict(self):
        class EmptyDeterministicProvider:
            provider_id = "TEST_EMPTY_DETERMINISTIC_PROVIDER"

            def extract(self, _receipt):
                return engine.FeatureVector(
                    numeric={}, categorical={},
                    audit={"raw_leaf_count": 0, "included_leaf_count": 0,
                           "excluded_leaf_count": 0, "included_paths_sha256": engine.canonical_sha256([]),
                           "excluded_fields_with_path_and_reason": [],
                           "unclassified_paths_empty": True, "families_present": []},
                )

        records = []
        for phase, per_role in (("calibration", 11), ("fresh_holdout", 10)):
            for role in ("alpha", "beta"):
                for index in range(per_role):
                    records.append({
                        "receipt": {"opaque-test-byte": f"{phase}-{role}-{index}"},
                        "challenge": "T-OCI-ISOLATED", "phase": phase,
                        "block": "c0" if phase == "calibration" else "h0",
                        "opaque_slot_id": f"{phase}-{role}-{index:02d}", "role": role,
                    })
        result = engine.FullEvaluatorEngine(feature_provider=EmptyDeterministicProvider()).evaluate(
            records, "12" * 32,
        )
        self.assertEqual(result["deterministic_replay"]["status"], "REPLAY_IDENTICAL")
        self.assertEqual(set(result["hash_manifest"]), set(engine.FullEvaluatorEngine().profile["deterministic_replay"]["required_hash_classes"]))
        self.assertFalse(result["evaluation"]["qualification_verdict_produced"])
        self.assertFalse(result["evaluation"]["treatment_score_or_ranking_produced"])
        self.assertEqual(result["evaluation"]["MODEL-SELECTION-RANDOMIZATION"], "NOT_TESTED")


if __name__ == "__main__":
    unittest.main()
