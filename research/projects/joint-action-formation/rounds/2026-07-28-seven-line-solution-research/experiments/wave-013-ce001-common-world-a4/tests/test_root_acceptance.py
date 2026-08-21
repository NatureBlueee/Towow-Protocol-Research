from __future__ import annotations

import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import evaluate_path
from run import run_case


E1 = "E1-EXTANT-MULTI-OWNER"
E5 = "E5-IMPOSSIBLE-REFUSAL"


@pytest.fixture(scope="module")
def actual_runs(tmp_path_factory):
    artifacts = tmp_path_factory.mktemp("ce001-root-acceptance")
    result = {}
    for case_id in (E1, E5):
        bundle_path, seal_path = run_case(case_id, artifacts)
        result[case_id] = {
            "bundle_path": bundle_path,
            "seal_path": seal_path,
            "bundle": json.loads(bundle_path.read_text()),
            "seal": json.loads(seal_path.read_text()),
            "evaluation": evaluate_path(bundle_path, seal_path),
        }
    result["artifacts"] = artifacts
    return result


def test_actual_e1_and_e5_cross_independent_evaluator(actual_runs):
    e1 = actual_runs[E1]
    e5 = actual_runs[E5]
    assert e1["evaluation"]["terminal_disposition"] == "SUCCEEDED"
    assert e1["evaluation"]["ExactTaskSuccess"] is True
    assert e1["evaluation"]["CorrectResolution"] is True
    assert e1["evaluation"]["evidence_boundary"]["errors"] == []
    assert e5["evaluation"]["terminal_disposition"] == "BOUNDED_REFUSAL"
    assert e5["evaluation"]["ExactTaskSuccess"] is False
    assert e5["evaluation"]["CorrectResolution"] is True
    assert e5["evaluation"]["evidence_boundary"]["errors"] == []
    for run in (e1, e5):
        binding = run["evaluation"]["evidence_binding"]
        assert binding["run_id"] == run["bundle"]["episode_manifest"]["run_id"]
        assert binding["bundle_sha256"] == run["bundle"]["bundle_sha256"]
        assert binding["seal_sha256"] == run["seal"]["seal_sha256"]


def test_actual_e1_has_content_addressed_causal_chain(actual_runs):
    bundle = actual_runs[E1]["bundle"]
    target_requests = bundle["arm_transcript"]["target_requests"]
    execute = next(
        request for request in target_requests if request["payload"]["action"] == "EXECUTE"
    )
    readback_request = next(
        request for request in target_requests if request["payload"]["action"] == "READBACK"
    )
    target = bundle["target_native_log"]
    occurrence = target["occurrences"][0]
    readback = next(entry for entry in target["entries"] if entry["kind"] == "READBACK")
    assert occurrence["source_execute_request_id"] == execute["request_id"]
    assert occurrence["source_execute_request_nonce"] == execute["request_nonce"]
    assert occurrence["source_execute_request_sha256"] == execute["request_sha256"]
    assert all(
        sample["source_occurrence_event_sha256"] == occurrence["event_sha256"]
        and sample["source_execute_request_sha256"] == execute["request_sha256"]
        for sample in target["sensor_samples"]
    )
    assert readback["source_readback_request_id"] == readback_request["request_id"]
    assert readback["source_readback_request_nonce"] == readback_request["request_nonce"]
    assert readback["source_readback_request_sha256"] == readback_request["request_sha256"]
    for owner_id in ("O_E", "O_Q", "O_V"):
        matching = [
            entry
            for entry in bundle["owner_native_logs"][owner_id]["entries"]
            if entry["payload"]["kind"] in {"EFFECT_OBSERVATION", "ACCEPTANCE"}
        ]
        assert len(matching) == 1
        assert (
            matching[0]["payload"]["readback_event_sha256"]
            == readback["event_sha256"]
        )


def test_actual_duplicate_execute_is_idempotent_and_still_valid(tmp_path):
    bundle_path, seal_path = run_case(
        E1,
        tmp_path,
        duplicate_execute_probe=True,
    )
    bundle = json.loads(bundle_path.read_text())
    evaluation = evaluate_path(bundle_path, seal_path)
    assert len(bundle["target_native_log"]["occurrences"]) == 1
    assert len(bundle["target_native_log"]["sensor_samples"]) == 46
    probe = [
        event
        for event in bundle["arm_transcript"]["events"]
        if event["kind"] == "IDEMPOTENCY_PROBE"
    ]
    assert len(probe) == 1
    assert probe[0]["replay_decision"] == "IDEMPOTENT_REPLAY"
    assert evaluation["terminal_disposition"] == "SUCCEEDED"
    assert evaluation["ExactTaskSuccess"] is True


def test_actual_e5_private_alternative_contradiction_is_rejected(tmp_path):
    bundle_path, seal_path = run_case(
        E5,
        tmp_path,
        feasible_alternatives_override=["BatteryB"],
    )
    bundle = json.loads(bundle_path.read_text())
    evaluation = evaluate_path(bundle_path, seal_path)
    assert (
        bundle["private_case_reveal"]["alternative_oracle"][
            "feasible_alternatives"
        ]
        == ["BatteryB"]
    )
    assert evaluation["evidence_boundary"]["bundle_valid"] is True
    assert evaluation["terminal_disposition"] == "INVALID_REFUSAL"
    assert evaluation["CorrectResolution"] is False


def test_artifacts_are_run_scoped_and_latest_pointer_is_bound(actual_runs):
    artifacts = actual_runs["artifacts"]
    first = actual_runs[E1]
    first_bundle_bytes = first["bundle_path"].read_bytes()
    second_bundle_path, second_seal_path = run_case(E1, artifacts)
    second = json.loads(second_bundle_path.read_text())
    latest_path = artifacts / "latest-e1-extant-multi-owner.json"
    latest = json.loads(latest_path.read_text())
    assert first["bundle_path"].exists()
    assert first["bundle_path"].read_bytes() == first_bundle_bytes
    assert first["bundle_path"].parent != second_bundle_path.parent
    assert second_bundle_path.name == "bundle.json"
    assert second_seal_path.name == "run-seal.json"
    assert latest["run_id"] == second["episode_manifest"]["run_id"]
    assert latest["bundle_sha256"] == second["bundle_sha256"]
    assert artifacts / latest["bundle_file"] == second_bundle_path
    assert artifacts / latest["seal_file"] == second_seal_path
