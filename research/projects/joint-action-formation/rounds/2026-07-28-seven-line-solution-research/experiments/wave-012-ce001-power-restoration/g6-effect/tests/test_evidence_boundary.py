import unittest

from run import end_to_end, failure_injections, semantic_conformance


class EvidenceBoundaryTests(unittest.TestCase):
    def test_semantic_and_e2e_denominators_are_explicitly_separate(self):
        semantic = semantic_conformance()
        e2e, _trace = end_to_end()
        self.assertEqual(
            semantic["end_to_end_execution"], "NOT_PART_OF_THIS_DENOMINATOR"
        )
        self.assertEqual(e2e["semantic_conformance"], "SEPARATE_RUN")
        self.assertEqual(semantic["evidence_class"], "LOCAL_SYNTHETIC_COMPONENT")
        self.assertEqual(e2e["evidence_class"], "LOCAL_SYNTHETIC_E2E")

    def test_product_and_production_claims_are_not_run(self):
        semantic = semantic_conformance()
        e2e, _trace = end_to_end()
        self.assertEqual(semantic["real_product_execution"], "NOT_RUN")
        self.assertEqual(e2e["real_product_execution"], "NOT_RUN")
        self.assertEqual(e2e["production_effect"], "NOT_RUN")
        self.assertEqual(e2e["human_acceptance"], "NOT_RUN")
        self.assertEqual(e2e["payment_finality"], "NOT_RUN")

    def test_failure_injection_is_its_own_denominator(self):
        failures, _trace = failure_injections()
        self.assertEqual(
            failures["evidence_class"], "LOCAL_SYNTHETIC_FAILURE_INJECTION"
        )
        self.assertEqual(failures["passed"], 4)
        self.assertEqual(failures["total"], 4)


if __name__ == "__main__":
    unittest.main()
