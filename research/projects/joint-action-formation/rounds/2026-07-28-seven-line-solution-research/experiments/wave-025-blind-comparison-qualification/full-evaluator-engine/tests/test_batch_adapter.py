#!/usr/bin/env python3

import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock


ENGINE_DIR = pathlib.Path(__file__).resolve().parents[1]
WAVE_ROOT = ENGINE_DIR.parent
F_BATCH = WAVE_ROOT / "runs" / "smoke-v13-20260801-f"
ADAPTER_PATH = ENGINE_DIR / "batch_adapter.py"
SPEC = importlib.util.spec_from_file_location("wave025_batch_adapter", ADAPTER_PATH)
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def canonical_write(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False) + "\n").encode())


class BatchAdapterTests(unittest.TestCase):
    def copy_f(self):
        temp = tempfile.TemporaryDirectory(prefix="w025-adapter-")
        target = pathlib.Path(temp.name) / "f"
        shutil.copytree(F_BATCH, target)
        self.addCleanup(temp.cleanup)
        return target

    def test_exact_f_read_only_and_no_verdict(self):
        before_names = sorted(str(path.relative_to(F_BATCH)) for path in F_BATCH.rglob("*"))
        evaluation = F_BATCH / "evaluation.json"
        before_eval = (hashlib.sha256(evaluation.read_bytes()).hexdigest(), evaluation.stat().st_mtime_ns)
        original_read = adapter._read_bytes

        def guarded_read(path):
            if pathlib.Path(path).name == "evaluation.json":
                raise AssertionError("adapter attempted to read evaluator-owned output")
            return original_read(path)

        with mock.patch.object(adapter, "_read_bytes", side_effect=guarded_read):
            result = adapter.BatchAdapter().adapt(F_BATCH)

        self.assertEqual(len(result.records), 12)
        self.assertEqual(len(result.host_only_rows), 12)
        self.assertEqual({row["phase"] for row in result.records}, {"calibration", "fresh_holdout"})
        self.assertEqual({row["challenge"] for row in result.records},
                         {"D0-HOST-LEAK", "D1-OCI-CANARY", "T-OCI-ISOLATED"})
        self.assertEqual(result.evidence_receipt["batch_merkle_root"],
                         "e80f30077cf32af0ccb2ee09e7790e7789a0885bc7926ba579016426ea747f54")
        self.assertFalse(result.evidence_receipt["evaluation_json_read"])
        self.assertFalse(result.evidence_receipt["batch_writes_performed"])
        self.assertFalse(result.evidence_receipt["qualification_verdict_produced"])
        self.assertFalse(result.evidence_receipt["treatment_score_or_ranking_produced"])
        self.assertFalse(result.evidence_receipt["future_v1_4_self_contained_profile_bytes_supported"])
        self.assertFalse(any("verdict" in row for row in result.records))
        after_eval = (hashlib.sha256(evaluation.read_bytes()).hexdigest(), evaluation.stat().st_mtime_ns)
        after_names = sorted(str(path.relative_to(F_BATCH)) for path in F_BATCH.rglob("*"))
        self.assertEqual(before_eval, after_eval)
        self.assertEqual(before_names, after_names)

    def test_unknown_runner_owned_field_fails_schema(self):
        batch = self.copy_f()
        path = batch / "precommit.json"
        value = json.loads(path.read_text())
        value["unexpected_field"] = True
        canonical_write(path, value)
        with self.assertRaisesRegex(adapter.SchemaValidationError, "unexpected_field"):
            adapter.BatchAdapter(enforce_f_root_locks=False).adapt(batch)

    def test_raw_channel_tamper_fails_equality(self):
        batch = self.copy_f()
        reveal = json.loads((batch / "reveal.json").read_text())
        slot_id = reveal["mapping"][0]["opaque_slot_id"]
        path = batch / "slots" / slot_id / "collector-out.bin"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(adapter.EvidenceIntegrityError, "stdout/channel"):
            adapter.BatchAdapter(enforce_f_root_locks=False).adapt(batch)

    def test_extra_docker_event_fails_exact_projection(self):
        batch = self.copy_f()
        reveal = json.loads((batch / "reveal.json").read_text())
        slot_id = reveal["mapping"][0]["opaque_slot_id"]
        path = batch / "slots" / slot_id / "docker-events.jsonl"
        first = path.read_bytes().splitlines(keepends=True)[0]
        path.write_bytes(path.read_bytes() + first)
        with self.assertRaisesRegex(adapter.EvidenceIntegrityError, "exactly 19"):
            adapter.BatchAdapter(enforce_f_root_locks=False).adapt(batch)

    def test_wrong_reveal_mapping_fails_deterministic_reconstruction(self):
        batch = self.copy_f()
        path = batch / "reveal.json"
        value = json.loads(path.read_text())
        value["mapping"][0]["role"] = "S" if value["mapping"][0]["role"] == "R" else "R"
        canonical_write(path, value)
        with self.assertRaisesRegex(adapter.EvidenceIntegrityError, "reveal mapping"):
            adapter.BatchAdapter(enforce_f_root_locks=False).adapt(batch)

    def test_future_self_contained_profile_is_explicitly_unsupported(self):
        batch = self.copy_f()
        canonical_write(batch / "shared-evidence-profile.json", {"schema": "WAVE025_V1_4"})
        with self.assertRaisesRegex(adapter.UnsupportedBatchVersion, "V1.4 self-contained"):
            adapter.BatchAdapter(enforce_f_root_locks=False).adapt(batch)


if __name__ == "__main__":
    unittest.main()
