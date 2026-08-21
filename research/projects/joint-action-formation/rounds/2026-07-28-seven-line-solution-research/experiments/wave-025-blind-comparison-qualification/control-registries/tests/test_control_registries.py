from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT.parent
PUBLIC_SCHEMA_PATH = ROOT / "PUBLIC-CONTROL-FAMILY-REGISTRATION.schema.json"
PUBLIC_PATH = ROOT / "PUBLIC-CONTROL-FAMILY-REGISTRATION.preformal-candidate.json"
PRIVATE_SCHEMA_PATH = ROOT / "PRIVATE-CONTROL-REGISTRY.schema.json"
PRIVATE_PATH = ROOT / "PRIVATE-CONTROL-REGISTRY.preformal-candidate.json"
PROFILE_PATH = EXPERIMENT / "EXECUTABLE-ATTACK-PROFILE.json"
FEATURE_SPEC_PATH = EXPERIMENT / "feature-spec" / "FEATURE-SPEC.json"
REVEAL_PATH = EXPERIMENT / "runs" / "smoke-v13-20260801-f" / "reveal.json"
D0_DESIGN_JSON_PATH = ROOT / "D0-CONTROL-DESIGN.candidate.json"
D0_DESIGN_MD_PATH = ROOT / "D0-CONTROL-DESIGN.candidate.md"

sys.path.insert(0, str(ROOT))
import generate_private_registry as generator  # noqa: E402


def load(path: Path):
    return json.loads(path.read_bytes())


def canonical_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class ControlRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.public_schema = load(PUBLIC_SCHEMA_PATH)
        cls.private_schema = load(PRIVATE_SCHEMA_PATH)
        cls.public = load(PUBLIC_PATH)
        cls.private = load(PRIVATE_PATH)
        cls.format_checker = jsonschema.FormatChecker()

    def validate(self, instance, schema):
        jsonschema.Draft202012Validator(schema, format_checker=self.format_checker).validate(instance)

    def test_public_registration_is_strict_and_complete(self):
        self.validate(self.public, self.public_schema)
        self.assertEqual(PUBLIC_PATH.read_bytes(), canonical_bytes(self.public))
        self.assertEqual(
            [family["challenge"] for family in self.public["families"]],
            ["D0-HOST-LEAK", "D1-OCI-CANARY"],
        )
        expected_keys = {
            "family_id",
            "challenge",
            "injection_surface",
            "expected_collector_feature_family",
            "primary_detector_id_from_C01_TO_C05",
            "calibration_population_by_role",
            "holdout_population_by_role",
        }
        for family in self.public["families"]:
            self.assertEqual(set(family), expected_keys)
            self.assertEqual(family["calibration_population_by_role"], 50)
            self.assertEqual(family["holdout_population_by_role"], 50)

        extra_top = copy.deepcopy(self.public)
        extra_top["unexpected"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(extra_top, self.public_schema)
        extra_family = copy.deepcopy(self.public)
        extra_family["families"][0]["private_token"] = "forbidden"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(extra_family, self.public_schema)

    def test_private_registry_is_strict_and_bound_to_public_bytes(self):
        self.validate(self.private, self.private_schema)
        self.assertEqual(PRIVATE_PATH.read_bytes(), canonical_bytes(self.private))
        public_raw = PUBLIC_PATH.read_bytes()
        self.assertEqual(self.private["public_registration_sha256"], hashlib.sha256(public_raw).hexdigest())
        self.assertEqual(self.private["role_labels"], ["R", "S"])
        self.assertEqual(self.private["binding_state"], "NOT_BOUND_TO_PROFILE_OR_PRECOMMIT")

        for family in self.private["families"]:
            expected_hash = hashlib.sha256(canonical_bytes(family)).hexdigest()
            self.assertEqual(self.private["per_family_canonical_sha256"][family["family_id"]], expected_hash)

        extra_mapping = copy.deepcopy(self.private)
        extra_mapping["families"][0]["role_mappings"][0]["unexpected"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(extra_mapping, self.private_schema)

    def test_d0_has_two_distinct_16_byte_tags_and_derived_basenames(self):
        d0 = self.private["families"][0]
        self.assertEqual(d0["family_id"], "D0_RESIDUE_OPAQUE_BASENAME_V1")
        mappings = d0["role_mappings"]
        self.assertEqual([row["role_label"] for row in mappings], ["R", "S"])
        tags = [row["tag_hex"] for row in mappings]
        self.assertEqual(len(set(tags)), 2)
        for row in mappings:
            self.assertEqual(len(bytes.fromhex(row["tag_hex"])), 16)
            self.assertEqual(row["candidate_visible_basename"], f"d0-residue-v1-{row['tag_hex']}")

    def test_d1_uses_current_revealed_smoke_tokens_with_one_mapping_per_role(self):
        d1 = self.private["families"][1]
        actual = {row["role_label"]: row["token_utf8"] for row in d1["role_mappings"]}
        reveal = load(REVEAL_PATH)
        observed = {"R": set(), "S": set()}
        for row in reveal["mapping"]:
            if row["challenge"] == "D1-OCI-CANARY":
                observed[row["role"]].add(row["canary_token_or_null"])
        self.assertEqual(actual, {role: next(iter(tokens)) for role, tokens in observed.items() if len(tokens) == 1})
        self.assertEqual(
            self.private["material_provenance"]["D1-OCI-CANARY"]["source_reveal_sha256"],
            hashlib.sha256(REVEAL_PATH.read_bytes()).hexdigest(),
        )
        self.assertFalse(self.private["material_provenance"]["D1-OCI-CANARY"]["fresh_for_formal"])

    def test_no_actual_private_material_is_present_in_public_registration(self):
        public_raw = PUBLIC_PATH.read_bytes()
        public_schema_raw = PUBLIC_SCHEMA_PATH.read_bytes()
        private_values = []
        for row in self.private["families"][0]["role_mappings"]:
            private_values.extend([row["tag_hex"], row["candidate_visible_basename"]])
        for row in self.private["families"][1]["role_mappings"]:
            private_values.append(row["token_utf8"])
        for value in private_values:
            self.assertNotIn(value.encode("utf-8"), public_raw)
            self.assertNotIn(value.encode("utf-8"), public_schema_raw)
        for forbidden_key in [b'"role_labels"', b'"role_mappings"', b'"tag_hex"', b'"token_utf8"']:
            self.assertNotIn(forbidden_key, public_raw)

    def test_generator_uses_csprng_path_writes_canonical_0600_and_rejects_overwrite(self):
        public_raw = PUBLIC_PATH.read_bytes()
        reveal_raw = REVEAL_PATH.read_bytes()
        tags = ["0" * 32, "1" * 32]
        with mock.patch.object(generator.secrets, "token_hex", side_effect=tags) as token_hex:
            built = generator.build_registry(public_raw, reveal_raw, "2026-08-01T00:00:00Z")
        self.assertEqual(token_hex.call_count, 2)
        self.assertEqual([row["tag_hex"] for row in built["families"][0]["role_mappings"]], tags)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "private.json"
            generator.write_exclusive_0600(output, generator.canonical_bytes(built))
            self.assertEqual(output.read_bytes(), canonical_bytes(built))
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                generator.write_exclusive_0600(output, b"overwrite")

    def test_profile_remains_unbound_and_correct_class_tail_is_used(self):
        profile = load(PROFILE_PATH)
        for key in ["D0_private_family_registry_sha256", "D1_private_family_registry_sha256"]:
            self.assertEqual(profile["external_bindings"][key], {"state": "BLOCKING_UNBOUND", "sha256": None})
        confidence = load(FEATURE_SPEC_PATH)["confidence_intervals"]
        self.assertEqual(confidence["class_tail_alpha"], 0.025)
        d0_design = load(D0_DESIGN_JSON_PATH)["c01_detectability_prediction"]
        self.assertEqual(d0_design["class_tail_alpha"], 0.025)
        self.assertAlmostEqual(d0_design["conditional_bonferroni_classwise_cp_lower_if_50_of_50"], 0.9288782635)
        self.assertNotIn("0.9418", D0_DESIGN_MD_PATH.read_text(encoding="utf-8"))
        self.assertIn("0.9288782635", D0_DESIGN_MD_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
