from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

from integration_export import export_fragment


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_ROOT = ROOT.parent / "integration-preflight"
SPEC = importlib.util.spec_from_file_location(
    "ce001_preflight", PREFLIGHT_ROOT / "preflight.py"
)
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class IntegrationExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(
            (ROOT / "artifacts" / "e2e-results.json").read_text(encoding="utf-8")
        )

    def test_export_is_deterministic_and_namespaced(self) -> None:
        first = export_fragment(self.report)
        second = export_fragment(copy.deepcopy(self.report))
        self.assertEqual(first, second)
        self.assertEqual(first["namespace"], "G6")
        self.assertEqual(first["qualification"], "QUALIFIED_COMPONENT_OUTPUT")
        self.assertEqual(first["evidence"]["record_count"], 8)
        self.assertEqual(first["evidence"]["line_local_closed_count"], 6)

    def test_export_contains_no_contract_level_passthrough(self) -> None:
        fragment = export_fragment(self.report)
        forbidden = {
            item.replace("_", "")
            for item in PREFLIGHT.CONTRACT_LEVEL_FIELDS
        }
        hits: list[str] = []

        def walk(value, path="$"):
            if isinstance(value, dict):
                for key, child in value.items():
                    normalized = key.replace("_", "").lower()
                    if normalized in forbidden or normalized.startswith("contract"):
                        hits.append(f"{path}.{key}")
                    walk(child, f"{path}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}[{index}]")

        walk(fragment)
        self.assertEqual(hits, [])

    def test_actual_fragment_is_scope_safe_but_not_integration_complete(self) -> None:
        envelope = PREFLIGHT.load_envelope(
            PREFLIGHT_ROOT / "fixtures" / "qualified-e6.json"
        )
        envelope["components"]["G6"] = export_fragment(self.report)
        result = PREFLIGHT.validate_envelope(envelope)
        self.assertEqual(result["preflight_status"], "REJECTED")
        codes = {item["code"] for item in result["rejections"]}
        self.assertTrue(
            {
                "TARGET_CONSUMED_AUTHORITY_MISSING",
                "EXACT_EFFECT_BINDING_MISSING",
                "ACCEPTANCE_CLOSURE_MISSING",
                "OP_FINALITY_MISSING",
            }.issubset(codes)
        )
        self.assertNotIn("CONTRACT_FIELD_PASSTHROUGH", codes)
        self.assertEqual(
            result["contract_score_status"], "CONTRACT_SCORE_NOT_COMPUTED"
        )

    def test_actual_fragment_can_accompany_a_complete_integration_envelope(self) -> None:
        envelope = PREFLIGHT.load_envelope(
            PREFLIGHT_ROOT / "fixtures" / "qualified-e6.json"
        )
        envelope["components"]["G6"]["local_adapter_export"] = export_fragment(
            self.report
        )
        result = PREFLIGHT.validate_envelope(envelope)
        self.assertEqual(result["preflight_status"], "QUALIFIED_COMPONENT_OUTPUTS")
        self.assertEqual(result["rejections"], [])
        self.assertEqual(
            result["contract_score_status"], "CONTRACT_SCORE_NOT_COMPUTED"
        )

    def test_invalid_or_detached_closure_is_not_exported(self) -> None:
        invalid = copy.deepcopy(self.report)
        invalid["records"][0]["evaluation"]["evidence_closure_valid"] = False
        with self.assertRaisesRegex(ValueError, "no valid evidence closure"):
            export_fragment(invalid)

        detached = copy.deepcopy(self.report)
        detached["records"][0]["method_result"]["evidence_closure"][
            "trace_head"
        ] = "detached"
        with self.assertRaisesRegex(ValueError, "closure binding mismatch"):
            export_fragment(detached)


if __name__ == "__main__":
    unittest.main()
