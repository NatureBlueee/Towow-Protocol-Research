from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT.parent
FIXTURE_PATH = ROOT / "fixtures" / "NORMATIVE-COMPLETENESS-MINIMAL-PAIRS.json"
SPEC_PATH = ROOT / "FEATURE-SPEC.json"
REFERENCE_PATH = ROOT / "reference_extractor.py"
REFERENCE_TESTS_PATH = ROOT / "tests" / "test_reference_extractor.py"
PROFILE_PATH = EXPERIMENT / "EXECUTABLE-ATTACK-PROFILE.json"
SLOTS_PATH = EXPERIMENT / "runs" / "smoke-v13-20260801-f" / "slots"

MODULE_SPEC = importlib.util.spec_from_file_location("wave025_reference_extractor_completeness", REFERENCE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
reference = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(reference)


def canonical_without_lf(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class NormativeCompletenessFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_bytes())
        cls.cases = {case["id"]: case for case in cls.fixture["cases"]}

    def test_source_bindings_and_profile_authority_boundary(self):
        bindings = self.fixture["source_bindings"]
        self.assertEqual(bindings["feature_spec_sha256"], sha256(SPEC_PATH.read_bytes()))
        self.assertEqual(bindings["reference_extractor_sha256"], sha256(REFERENCE_PATH.read_bytes()))
        self.assertEqual(bindings["reference_extractor_tests_sha256"], sha256(REFERENCE_TESTS_PATH.read_bytes()))
        self.assertEqual(bindings["selected_profile_sha256"], sha256(PROFILE_PATH.read_bytes()))
        profile = json.loads(PROFILE_PATH.read_bytes())
        self.assertEqual(profile["feature_spec_binding"]["semantic_authority"], "FEATURE_SPEC_BYTES_NOT_REFERENCE_EXTRACTOR_CODE")
        self.assertEqual(profile["feature_spec_binding"]["reference_extractor_role"], "NONAUTHORITATIVE_COMPARISON_IMPLEMENTATION_ONLY")

    def test_every_fixture_case_has_two_divergent_interpretations(self):
        self.assertEqual(len(self.cases), 11)
        for case in self.cases.values():
            self.assertEqual(len(case["input_pair"]), 2)
            self.assertIn("interpretation_a", case)
            self.assertIn("interpretation_b", case)
            self.assertTrue(case["outputs_differ"])

    def test_category_scalar_and_domain_hash_examples(self):
        prefix = b"WAVE025_CATEGORY_V1\0F02_ARGV_ENV_CWD\0/c\0"
        scalar = self.cases["NC02_CATEGORY_STRING_VS_CANONICAL_SCALAR_BYTES"]
        self.assertEqual(sha256(prefix + b"1"), scalar["interpretation_a"]["string_sha256"])
        self.assertEqual(sha256(prefix + canonical_without_lf("1")), scalar["interpretation_b"]["string_sha256"])
        self.assertEqual(sha256(prefix + canonical_without_lf(1)), scalar["interpretation_b"]["number_sha256"])
        self.assertTrue(scalar["interpretation_a"]["type_collision"])
        self.assertFalse(scalar["interpretation_b"]["type_collision"])

        framing = self.cases["NC03_CATEGORY_DOMAIN_AND_FRAMING"]
        self.assertEqual(sha256(prefix + canonical_without_lf("x")), framing["interpretation_a"]["first_sha256"])
        tuple_preimage = b"WAVE025_CATEGORY_V1\0" + canonical_without_lf(["F02_ARGV_ENV_CWD", "/c", "x"])
        self.assertEqual(sha256(tuple_preimage), framing["interpretation_b"]["first_sha256"])

    def test_record_bag_atomicity_hashes(self):
        case = self.cases["NC05_RECORD_BAG_ATOMICITY"]
        left_hashes = [sha256(canonical_without_lf(record)) for record in case["input_pair"][0]]
        right_hashes = [sha256(canonical_without_lf(record)) for record in case["input_pair"][1]]
        self.assertEqual(left_hashes, case["interpretation_a"]["left_record_sha256"])
        self.assertEqual(right_hashes, case["interpretation_a"]["right_record_sha256"])
        self.assertNotEqual(set(left_hashes), set(right_hashes))
        self.assertEqual(sorted(case["interpretation_b"]["left_k_bag"]), sorted(case["interpretation_b"]["right_k_bag"]))
        self.assertEqual(sorted(case["interpretation_b"]["left_v_bag"]), sorted(case["interpretation_b"]["right_v_bag"]))

    def test_ngram_preimage_and_bucket_examples(self):
        case = self.cases["NC08_NGRAM_PREIMAGE_AND_BUCKET"]
        domain = b"WAVE025_UTF8_NGRAM_V1"
        for index, gram_text in enumerate(case["input_pair"]):
            gram = gram_text.encode("utf-8")
            digest_a = hashlib.sha256(domain + b"\0" + bytes([2]) + gram).digest()
            digest_b = hashlib.sha256(domain + b"\0" + b"2\0" + gram).digest()
            side = "left" if index == 0 else "right"
            self.assertEqual(digest_a.hex(), case["interpretation_a"][f"{side}_digest"])
            self.assertEqual(int.from_bytes(digest_a[:4], "big") % 4096, case["interpretation_a"][f"{side}_bucket"])
            self.assertEqual(digest_b.hex(), case["interpretation_b"][f"{side}_digest"])
            self.assertEqual(int.from_bytes(digest_b, "big") % 4096, case["interpretation_b"][f"{side}_bucket"])

    def test_quantile_and_signed_hash_examples(self):
        quantile = self.cases["NC10_QUANTILE_AND_IQR_INTERPOLATION"]
        self.assertAlmostEqual(quantile["interpretation_a"]["left_scale_iqr_div_1_349"], 15 / 1.349)
        self.assertAlmostEqual(quantile["interpretation_b"]["left_scale_iqr_div_1_349"], 20 / 1.349)

        signed = self.cases["NC11_SIGNED_CATEGORICAL_HASHING"]
        value_sha = signed["input_pair"][0]["value_sha256"]
        domain = b"WAVE025_CATEGORICAL_MODEL_HASH_V1"
        digest_a = hashlib.sha256(domain + b"\0F\0C\0" + value_sha.encode("ascii")).digest()
        self.assertEqual(digest_a.hex(), signed["interpretation_a"]["digest_for_both_counts"])
        self.assertEqual(int.from_bytes(digest_a[:4], "big") % 16384, signed["interpretation_a"]["bucket_for_both_counts"])
        sign_a = -1 if digest_a[4] & 0x80 else 1
        self.assertEqual(sign_a, signed["interpretation_a"]["sign_for_both_counts"])
        for count in (1, 3):
            record = {"family": "F", "context": "C", "value_sha256": value_sha, "count": count}
            digest_b = hashlib.sha256(domain + b"\0" + canonical_without_lf(record)).digest()
            self.assertEqual(digest_b.hex(), signed["interpretation_b"][f"count_{count}_digest"])
            self.assertEqual(int.from_bytes(digest_b, "big") % 16384, signed["interpretation_b"][f"count_{count}_bucket"])
            sign_b = 1 if digest_b[-1] & 1 == 0 else -1
            self.assertEqual(sign_b, signed["interpretation_b"][f"count_{count}_sign"])

    def test_reference_choices_are_characterized_not_promoted_to_normative(self):
        self.assertEqual(reference._normalized_context("/argv/0"), "/argv/@0000")
        self.assertEqual(reference._normalized_context("/environment/0/key"), "/environment/*/key")

        category_builder = reference.FeatureBuilder()
        category_builder.add_category("F02_ARGV_ENV_CWD", "/c", "1")
        category = category_builder.finish_categories()[0]
        self.assertEqual(
            category["value_sha256"],
            self.cases["NC02_CATEGORY_STRING_VS_CANONICAL_SCALAR_BYTES"]["interpretation_b"]["string_sha256"],
        )

        unicode_builder = reference.FeatureBuilder()
        unicode_builder.add_string("F", "C", "é")
        unicode_numeric = unicode_builder.finish_numeric()
        self.assertEqual(unicode_numeric["F|C|shape.non_ascii|value"], 2)

        sha_builder = reference.FeatureBuilder()
        sha_builder.add_string("F", "C", "a" * 64, sha_leaf=True)
        sha_numeric = sha_builder.finish_numeric()
        self.assertIn("F|C|shape.byte_length|value", sha_numeric)
        self.assertIn("F|C|shape.codepoint_length|value", sha_numeric)
        self.assertFalse(any("lexical|" in key for key in sha_numeric))

    def test_f_receipts_activate_the_relevant_ambiguities(self):
        counts = {
            "receipt_count": 0,
            "string_scalar_count": 0,
            "float_scalar_count": 0,
            "array_count": 0,
            "multi_element_array_count": 0,
            "maximum_string_utf8_bytes": 0,
            "non_ascii_string_count": 0,
            "over_4096_byte_string_count": 0,
        }

        def walk(value):
            if isinstance(value, dict):
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                counts["array_count"] += 1
                counts["multi_element_array_count"] += int(len(value) > 1)
                for child in value:
                    walk(child)
            elif isinstance(value, str):
                counts["string_scalar_count"] += 1
                length = len(value.encode("utf-8"))
                counts["maximum_string_utf8_bytes"] = max(counts["maximum_string_utf8_bytes"], length)
                counts["non_ascii_string_count"] += int(any(ord(char) > 127 for char in value))
                counts["over_4096_byte_string_count"] += int(length > 4096)
            elif isinstance(value, float):
                counts["float_scalar_count"] += 1

        for path in sorted(SLOTS_PATH.glob("*/collector-features.json")):
            counts["receipt_count"] += 1
            walk(json.loads(path.read_bytes()))
        self.assertEqual(counts, self.fixture["f_receipt_activation"])


if __name__ == "__main__":
    unittest.main()
