from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "nac_h1_eval",
    ROOT / "tools" / "nac_h1_eval.py",
)
assert SPEC and SPEC.loader
nac_h1_eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nac_h1_eval)


def canonical_write(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def artifact(path: Path, relative_to: Path) -> dict:
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class NACH1EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.manifest_path = self.directory / "manifest.json"
        self.manifest = self.make_manifest()
        canonical_write(self.manifest_path, self.manifest)

    def tearDown(self):
        self.temporary.cleanup()

    def write_json(self, name: str, value) -> Path:
        path = self.directory / name
        canonical_write(path, value)
        return path

    @staticmethod
    def budget_cost(corpus_items: int = 10) -> dict:
        return {
            "corpus_items": corpus_items,
            "encoder_calls": corpus_items * 2,
            "training_compute_seconds": 3.0,
            "training_seed_count": 3,
            "onboarding_compute_seconds": 2.0,
            "query_encoding_compute_seconds": 1.0,
            "candidate_encoding_compute_seconds": 4.0,
            "retrieval_compute_seconds": 1.0,
            "storage_bytes": 1000,
            "transfer_bytes": 500,
            "adapter_count": 1,
            "mapping_count": 1,
            "version_recompute_compute_seconds": 2.0,
            "dual_write_seconds": 1.0,
            "downtime_seconds": 0.0,
        }

    def vector_artifact(self, name: str, dimension: int, candidate: bool) -> dict:
        if candidate:
            vectors = []
            for index in range(101):
                values = [-1.0] + [0.01 * ((index % 7) + 1)] * (dimension - 1)
                if index == 0:
                    values = [1.0] + [0.0] * (dimension - 1)
                vectors.append({"id": f"c{index:03d}", "values": values})
        else:
            vectors = [{"id": "q1", "values": [1.0] + [0.0] * (dimension - 1)}]
        path = self.write_json(name, {"vectors": vectors})
        return artifact(path, self.directory)

    def make_manifest(self) -> dict:
        labels_path = self.write_json(
            "labels.json",
            {
                "candidate_ids": [f"c{index:03d}" for index in range(101)],
                "queries": [
                    {
                        "id": "q1",
                        "positive_candidate_ids": ["c000"],
                        "slices": ["cross_language", "long_tail"],
                    }
                ],
            },
        )
        split_path = self.write_json(
            "split.json",
            {
                "evaluation_query_ids": ["q1"],
                "anchor_selection_query_ids": ["q-anchor"],
                "alignment_training_query_ids": ["q-train"],
            },
        )
        query_by_dimension = {
            dimension: self.vector_artifact(
                f"query-{dimension}.json",
                dimension,
                candidate=False,
            )
            for dimension in (2, 3)
        }
        candidate_by_dimension = {
            dimension: self.vector_artifact(
                f"candidate-{dimension}.json",
                dimension,
                candidate=True,
            )
            for dimension in (2, 3)
        }

        models = []
        for index in range(5):
            dimension = 2 if index < 3 else 3
            model_id = f"model-{index}"
            provider = f"provider-{index % 3}"
            backbone = f"backbone-{index % 2}"
            language_profile = ["zh", "en"] if index % 2 == 0 else ["en"]
            receipt_path = self.write_json(
                f"receipt-{index}.json",
                {
                    "model_id": model_id,
                    "provider": provider,
                    "backbone": backbone,
                    "version": "v1",
                    "embedding_dimension": dimension,
                    "source": "test fixture",
                },
            )
            models.append(
                {
                    "id": model_id,
                    "provider": provider,
                    "backbone": backbone,
                    "version": "v1",
                    "embedding_dimension": dimension,
                    "language_profile": language_profile,
                    "receipt_status": "VERIFIED",
                    "receipt": artifact(receipt_path, self.directory),
                }
            )

        budget = self.budget_cost()
        same_model = []
        for model in models:
            dimension = model["embedding_dimension"]
            same_model.append(
                {
                    "model_id": model["id"],
                    "budget_ceiling_id": "BUDGET-EH1-TEST",
                    "inputs": {
                        "query_embeddings": query_by_dimension[dimension],
                        "candidate_embeddings": candidate_by_dimension[dimension],
                    },
                    "cost": copy.deepcopy(budget),
                }
            )

        arms = [
            "nac_relative",
            "vec2vec",
            "procrustes",
            "shared_reference",
            "stable_schema_sparse",
        ]
        conditions = {
            "nac_relative": {
                "condition_type": "public_anchor_texts",
                "anchor_text_count": 10,
                "paired_correspondence_count": 0,
                "unpaired_source_embedding_count": 0,
                "unpaired_target_embedding_count": 0,
                "shared_encoder_call_count": 0,
                "lexical_corpus_item_count": 0,
            },
            "vec2vec": {
                "condition_type": "unpaired_corpora",
                "anchor_text_count": 0,
                "paired_correspondence_count": 0,
                "unpaired_source_embedding_count": 100,
                "unpaired_target_embedding_count": 100,
                "shared_encoder_call_count": 0,
                "lexical_corpus_item_count": 0,
            },
            "procrustes": {
                "condition_type": "paired_correspondences",
                "anchor_text_count": 0,
                "paired_correspondence_count": 25,
                "unpaired_source_embedding_count": 0,
                "unpaired_target_embedding_count": 0,
                "shared_encoder_call_count": 0,
                "lexical_corpus_item_count": 0,
            },
            "shared_reference": {
                "condition_type": "shared_reference_encoder",
                "anchor_text_count": 0,
                "paired_correspondence_count": 0,
                "unpaired_source_embedding_count": 0,
                "unpaired_target_embedding_count": 0,
                "shared_encoder_call_count": 101,
                "lexical_corpus_item_count": 0,
            },
            "stable_schema_sparse": {
                "condition_type": "lexical_or_sparse_corpus",
                "anchor_text_count": 0,
                "paired_correspondence_count": 0,
                "unpaired_source_embedding_count": 0,
                "unpaired_target_embedding_count": 0,
                "shared_encoder_call_count": 0,
                "lexical_corpus_item_count": 101,
            },
        }
        condition_artifacts = {}
        for arm in arms:
            receipt_path = self.write_json(
                f"information-condition-{arm}.json",
                {"arm_id": arm, **conditions[arm]},
            )
            condition_artifacts[arm] = {
                **conditions[arm],
                "receipt": artifact(receipt_path, self.directory),
            }
        corpus_by_arm = {
            "nac_relative": 10,
            "vec2vec": 200,
            "procrustes": 25,
            "shared_reference": 101,
            "stable_schema_sparse": 101,
        }
        cross_model = []
        for arm in arms:
            for source in models:
                for target in models:
                    if source["id"] == target["id"]:
                        continue
                    cross_model.append(
                        {
                            "arm_id": arm,
                            "source_model_id": source["id"],
                            "target_model_id": target["id"],
                            "information_condition": copy.deepcopy(
                                condition_artifacts[arm]
                            ),
                            "budget_ceiling_id": "BUDGET-EH1-TEST",
                            "inputs": {
                                "query_embeddings": query_by_dimension[2],
                                "candidate_embeddings": candidate_by_dimension[2],
                            },
                            "cost": self.budget_cost(corpus_by_arm[arm]),
                        }
                    )

        return {
            "schema_version": "1.0",
            "kind": "NACH1EmbeddingManifest",
            "experiment_id": "E-H1-TEST",
            "input_evidence_class": "EVALUATIVE_EH1",
            "hypothesis_id": "E-H1-PRIME",
            "tested_claim_id": "MC-NAC-ANCHOR",
            "dataset": {
                "labels": artifact(labels_path, self.directory),
                "split_manifest": artifact(split_path, self.directory),
                "label_status": "GOLD",
                "ground_truth_independent_of_tested_models": True,
                "query_direction": "SEEK",
                "candidate_direction": "OFFER",
            },
            "models": models,
            "required_cross_model_arms": arms,
            "critical_slices": [
                {"id": "cross_language", "minimum_queries": 1},
                {"id": "long_tail", "minimum_queries": 1},
            ],
            "recall_policy": {
                "k": 100,
                "aggregation": "macro_query_recall",
                "threshold_fraction": 0.8,
                "source_denominator": "R_AB/R_AA",
                "target_denominator": "R_AB/R_BB",
                "symmetric_denominator": "R_AB/sqrt(R_AA*R_BB)",
                "gate_scope": "every_ordered_pair_and_critical_slice",
            },
            "fairness_policy": "NATIVE_INFORMATION_CONDITIONS_ACCOUNTED_NOT_EQUAL_K",
            "fair_budget": {
                "ceiling_id": "BUDGET-EH1-TEST",
                "max_corpus_items": 500,
                "max_encoder_calls": 1000,
                "max_training_compute_seconds": 10.0,
                "max_training_seed_count": 5,
                "max_onboarding_compute_seconds": 10.0,
                "max_query_encoding_compute_seconds": 10.0,
                "max_candidate_encoding_compute_seconds": 10.0,
                "max_retrieval_compute_seconds": 10.0,
                "max_storage_bytes": 10000,
                "max_transfer_bytes": 10000,
                "max_adapter_count": 10,
                "max_mapping_count": 10,
                "max_version_recompute_compute_seconds": 10.0,
                "max_dual_write_seconds": 10.0,
                "max_downtime_seconds": 1.0,
            },
            "same_model_baselines": same_model,
            "cross_model_evaluations": cross_model,
            "claim_boundary": "TOOL_VALIDATION_IS_NOT_MECHANISM_VALIDATION",
        }

    def rewrite_manifest(self) -> None:
        canonical_write(self.manifest_path, self.manifest)

    def test_valid_manifest_covers_five_models_all_arms_and_ordered_pairs(self):
        inputs = nac_h1_eval.load_and_validate_manifest(self.manifest_path)

        self.assertEqual(5, len(inputs.baseline_vectors))
        self.assertEqual(100, len(inputs.cross_vectors))
        report = nac_h1_eval.evaluate(inputs)
        self.assertTrue(report["ordered_pair_and_slice_metric_gate_passed"])
        self.assertEqual(
            "TOOL_VALIDATION_IS_NOT_MECHANISM_VALIDATION",
            report["claim_boundary"],
        )
        corpus_sizes = {
            evaluation["arm_id"]: evaluation["cost"]["corpus_items"]
            for evaluation in self.manifest["cross_model_evaluations"]
        }
        self.assertEqual(10, corpus_sizes["nac_relative"])
        self.assertEqual(200, corpus_sizes["vec2vec"])
        self.assertEqual(
            "NATIVE_INFORMATION_CONDITIONS_ACCOUNTED_NOT_EQUAL_K",
            report["fairness_policy"],
        )
        result_by_arm = {
            result["arm_id"]: result for result in report["cross_model_results"]
        }
        self.assertEqual(
            "unpaired_corpora",
            result_by_arm["vec2vec"]["information_condition"]["condition_type"],
        )
        self.assertEqual("REQUIRES_RESEARCH_REVIEW", report["interpretation_status"])
        first = report["cross_model_results"][0]["slices"]["cross_language"]
        self.assertEqual(1.0, first["recall_at_100"])
        self.assertEqual(1.0, first["ratio_R_AB_over_R_AA"])
        self.assertEqual(1.0, first["ratio_R_AB_over_R_BB"])

    def test_rejects_missing_ordered_pair_in_one_arm(self):
        self.manifest["cross_model_evaluations"].pop()
        self.rewrite_manifest()

        with self.assertRaisesRegex(
            nac_h1_eval.ManifestError,
            "must cover every ordered model pair",
        ):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

    def test_rejects_stale_input_hash(self):
        self.manifest["dataset"]["labels"]["sha256"] = "0" * 64
        self.rewrite_manifest()

        with self.assertRaisesRegex(nac_h1_eval.ManifestError, "SHA-256 mismatch"):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

    def test_rejects_fewer_than_five_models_at_schema_boundary(self):
        self.manifest["models"] = self.manifest["models"][:4]
        self.rewrite_manifest()

        with self.assertRaisesRegex(nac_h1_eval.ManifestError, "is too short"):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

    def test_structurally_complete_e0_packet_is_explicitly_non_evaluative(self):
        self.manifest["input_evidence_class"] = "E0_NON_EVALUATIVE"
        self.manifest["dataset"]["label_status"] = "NON_GOLD"
        labels_path = self.directory / self.manifest["dataset"]["labels"]["path"]
        canonical_write(
            labels_path,
            {
                "candidate_ids": [f"c{index:03d}" for index in range(100)],
                "queries": [
                    {
                        "id": "q1",
                        "positive_candidate_ids": ["c000"],
                        "slices": ["cross_language", "long_tail"],
                    }
                ],
            },
        )
        self.manifest["dataset"]["labels"] = artifact(labels_path, self.directory)
        for model in self.manifest["models"]:
            model.pop("receipt")
            model["receipt_status"] = "NON_EVALUATIVE"
        self.rewrite_manifest()

        with self.assertRaises(nac_h1_eval.ManifestError) as captured:
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

        message = str(captured.exception)
        self.assertIn("EH1_NOT_EVALUATIVE_CLASS", message)
        self.assertIn("EH1_CANDIDATE_POOL_TOO_SMALL", message)
        self.assertIn("EH1_GOLD_LABELS_REQUIRED", message)
        self.assertIn("EH1_FIVE_MODEL_RECEIPTS_REQUIRED", message)

    def test_rejects_unpopulated_critical_slice(self):
        self.manifest["critical_slices"].append(
            {"id": "complex_conjunction", "minimum_queries": 1}
        )
        self.rewrite_manifest()

        with self.assertRaisesRegex(nac_h1_eval.ManifestError, "has 0 queries"):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

    def test_rejects_evaluation_query_leakage(self):
        split_path = self.directory / self.manifest["dataset"]["split_manifest"]["path"]
        canonical_write(
            split_path,
            {
                "evaluation_query_ids": ["q1"],
                "anchor_selection_query_ids": ["q1"],
                "alignment_training_query_ids": ["q-train"],
            },
        )
        self.manifest["dataset"]["split_manifest"] = artifact(
            split_path,
            self.directory,
        )
        self.rewrite_manifest()

        with self.assertRaisesRegex(nac_h1_eval.ManifestError, "leak"):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

    def test_rejects_cost_over_frozen_budget(self):
        self.manifest["cross_model_evaluations"][0]["cost"]["storage_bytes"] = 10001
        self.rewrite_manifest()

        with self.assertRaisesRegex(
            nac_h1_eval.ManifestError,
            "exceeds max_storage_bytes",
        ):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)

    def test_rejects_same_k_assumption_disguised_as_vec2vec_condition(self):
        evaluation = next(
            item
            for item in self.manifest["cross_model_evaluations"]
            if item["arm_id"] == "vec2vec"
        )
        evaluation["information_condition"] = copy.deepcopy(
            next(
                item["information_condition"]
                for item in self.manifest["cross_model_evaluations"]
                if item["arm_id"] == "nac_relative"
            )
        )
        self.rewrite_manifest()

        with self.assertRaisesRegex(
            nac_h1_eval.ManifestError,
            "must declare its native information condition unpaired_corpora",
        ):
            nac_h1_eval.load_and_validate_manifest(self.manifest_path)


if __name__ == "__main__":
    unittest.main()
