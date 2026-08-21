from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from visibility import (  # noqa: E402
    ARM_VIEW_FIELDS,
    ARM_VIEW_SCHEMA,
    PUBLIC_INPUT_SCHEMA,
    ArmViewFactory,
    BlindProcessLauncher,
    VisibilityViolation,
    canonical_bytes,
    validate_arm_view,
)


ARM_ID = "A4-DETERMINISTIC-MATURE-COMPOSITION"
E3A = "E3A-ACK-LOST-EFFECT"
E3B = "E3B-ACK-LOST-NO-EFFECT"


def public_input(**task_patch):
    task = {
        "q_version": "Q@v1",
        "object_id": "VenueV:CircuitC7",
        "target_id": "VenueV:CircuitC7",
        "deadline_minute": 90,
        "required_duration_minutes": 45,
        "required_power_kw": 3.0,
        "power_tolerance_percent": 5,
    }
    task.update(task_patch)
    return {"schema": PUBLIC_INPUT_SCHEMA, "task": task}


class ArmViewFactoryTests(unittest.TestCase):
    def setUp(self):
        self.factory = ArmViewFactory(arm_id=ARM_ID)

    def test_builds_only_exact_allowlist(self):
        view = self.factory.build(
            public_input(),
            private_materials=(
                {"case_id": E3A, "world_root": "private-world"},
                E3B,
            ),
        )
        self.assertEqual(set(view), set(ARM_VIEW_FIELDS))
        self.assertEqual(view["schema"], ARM_VIEW_SCHEMA)
        self.assertNotIn("case_id", canonical_bytes(view).decode())
        self.assertNotIn("world_root", canonical_bytes(view).decode())
        validate_arm_view(view)

    def test_unknown_top_level_fields_fail_closed(self):
        for key, value in (
            ("case_id", E3A),
            ("world_root", "secret-root"),
            ("owner_topology", {"count": 7}),
            ("crash_schedule", {"minute": 46}),
            ("private_truth_sha256", "0" * 64),
        ):
            candidate = public_input()
            candidate[key] = value
            with self.subTest(key=key), self.assertRaises(VisibilityViolation):
                self.factory.build(candidate)

    def test_nested_unknown_and_private_fields_fail_closed(self):
        for key, value in (
            ("case_id", E3A),
            ("metadata", {"world_root": "private"}),
            ("fault_schedule", {"drop_ack": True}),
            ("owner_registry_sha256", "1" * 64),
        ):
            candidate = public_input()
            candidate["task"][key] = value
            with self.subTest(key=key), self.assertRaises(VisibilityViolation):
                self.factory.build(candidate)

    def test_semantic_case_value_attack_fails_closed(self):
        for field in ("q_version", "object_id", "target_id"):
            with self.subTest(field=field), self.assertRaises(VisibilityViolation):
                self.factory.build(public_input(**{field: E3A}))

    def test_candidate_hash_dictionary_attack_fails_closed(self):
        private_manifest = {
            "case_id": E3A,
            "world_root": "private-world-root",
            "crash_schedule": None,
        }
        candidate_hash = hashlib.sha256(canonical_bytes(private_manifest)).hexdigest()
        with self.assertRaises(VisibilityViolation):
            self.factory.build(
                public_input(q_version=candidate_hash),
                private_materials=(private_manifest,),
            )

    def test_private_label_and_candidate_hash_absent(self):
        private_materials = (
            E3A,
            E3B,
            {"case_id": E3A, "effect_occurred": True},
            {"case_id": E3B, "effect_occurred": False},
        )
        view = self.factory.build(public_input(), private_materials=private_materials)
        raw = canonical_bytes(view)
        for material in private_materials:
            material_bytes = (
                material.encode()
                if isinstance(material, str)
                else canonical_bytes(material)
            )
            self.assertNotIn(material_bytes, raw)
            self.assertNotIn(hashlib.sha256(material_bytes).hexdigest().encode(), raw)

    def test_nested_private_scalar_and_its_hash_cannot_be_smuggled(self):
        private_manifest = {
            "owner_topology": {
                "principal_id": "principal-alternative",
                "resource_id": "generator-hidden-002",
            }
        }
        for leaked in ("principal-alternative", "generator-hidden-002"):
            with self.subTest(leaked=leaked), self.assertRaises(VisibilityViolation):
                self.factory.build(
                    public_input(q_version=leaked),
                    private_materials=(private_manifest,),
                )
            leaked_hash = hashlib.sha256(leaked.encode()).hexdigest()
            with self.subTest(leaked_hash=leaked_hash), self.assertRaises(
                VisibilityViolation
            ):
                self.factory.build(
                    public_input(q_version=leaked_hash),
                    private_materials=(private_manifest,),
                )

    def test_pair_length_and_alpha_projection_resist_label_dictionary(self):
        left = self.factory.build(public_input(), private_materials=(E3A,))
        right = self.factory.build(public_input(), private_materials=(E3B,))
        receipt = self.factory.assert_pair_compatible(left, right)
        self.assertEqual(receipt["status"], "PAIR_COMPATIBLE")
        self.assertEqual(len(canonical_bytes(left)), len(canonical_bytes(right)))
        self.assertEqual(
            self.factory.pair_projection(left),
            self.factory.pair_projection(right),
        )

    def test_length_attack_by_optional_padding_is_rejected(self):
        candidate = public_input()
        candidate["task"]["padding"] = E3A * 3
        with self.assertRaises(VisibilityViolation):
            self.factory.build(candidate)

    def test_mutated_arm_view_is_rejected_by_second_gate(self):
        view = self.factory.build(public_input())
        view["case_id"] = E3A
        with self.assertRaises(VisibilityViolation):
            validate_arm_view(view)


class BlindProcessLauncherTests(unittest.TestCase):
    def setUp(self):
        self.factory = ArmViewFactory(arm_id=ARM_ID)
        self.launcher = BlindProcessLauncher()

    def test_real_spawn_records_sanitized_child_surface(self):
        private_manifest = {
            "case_id": E3A,
            "world_root": "private-world-root",
            "owner_topology": ["O_R:primary", "O_R:alternative"],
            "crash_schedule": {"minute": 46},
        }
        view = self.factory.build(
            public_input(),
            private_materials=(private_manifest, E3A, E3B),
        )

        parent_argv = list(sys.argv)
        parent_cwd = os.getcwd()
        parent_name = multiprocessing.current_process().name
        parent_environment = dict(os.environ)
        with tempfile.TemporaryDirectory(prefix=f"{E3A}-parent-") as hostile_cwd:
            sys.argv[:] = ["runner.py", "--case", E3A]
            os.chdir(hostile_cwd)
            multiprocessing.current_process().name = E3A
            os.environ["CE001_CASE"] = E3A
            try:
                receipt = self.launcher.launch(
                    view,
                    private_materials=(private_manifest, E3A, E3B),
                )
            finally:
                sys.argv[:] = parent_argv
                os.chdir(parent_cwd)
                multiprocessing.current_process().name = parent_name
                os.environ.clear()
                os.environ.update(parent_environment)

        surface = receipt.visible_surface
        self.assertEqual(receipt.process_start_method, "spawn")
        self.assertEqual(receipt.worker_result["status"], "SURFACE_RECORDED")
        self.assertEqual(
            receipt.worker_result["view_sha256"],
            hashlib.sha256(canonical_bytes(view)).hexdigest(),
        )
        self.assertEqual(surface["argv"], ["wave015-blind-child", "--opaque"])
        self.assertTrue(surface["process_name"].startswith("arm-worker-"))
        self.assertNotIn(E3A, surface["process_name"])
        self.assertNotIn(E3A, surface["cwd"])
        self.assertEqual(surface["cwd_entries"], [])
        self.assertEqual(
            set(surface["environment"]),
            {"LANG", "PATH", "PYTHONHASHSEED"},
        )
        visible = canonical_bytes(surface)
        self.assertNotIn(E3A.encode(), visible)
        self.assertNotIn(E3B.encode(), visible)
        self.assertNotIn(
            hashlib.sha256(canonical_bytes(private_manifest)).hexdigest().encode(),
            visible,
        )
        self.assertTrue(receipt.private_material_absent)

    def test_launcher_rejects_unknown_field_even_after_factory(self):
        view = self.factory.build(public_input())
        view["nested_private"] = {"case_id": E3A}
        with self.assertRaises(VisibilityViolation):
            self.launcher.launch(view)

    def test_launcher_rejects_candidate_hash_in_mutated_public_value(self):
        private_manifest = {"case_id": E3A, "effect_occurred": True}
        view = self.factory.build(public_input())
        view["q_version"] = hashlib.sha256(
            canonical_bytes(private_manifest)
        ).hexdigest()
        with self.assertRaises(VisibilityViolation):
            self.launcher.launch(view, private_materials=(private_manifest,))


if __name__ == "__main__":
    unittest.main()
