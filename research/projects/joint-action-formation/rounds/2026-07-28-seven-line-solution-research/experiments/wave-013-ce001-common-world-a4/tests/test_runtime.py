from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run import run_case
from services import OWNER_IDS, sha256_value, verify_signed


@pytest.fixture(scope="module")
def bundles(tmp_path_factory):
    output = tmp_path_factory.mktemp("ce001-runtime")
    result = {}
    for case_id in ("E1-EXTANT-MULTI-OWNER", "E5-IMPOSSIBLE-REFUSAL"):
        bundle_path, seal_path = run_case(case_id, output)
        result[case_id] = (
            json.loads(bundle_path.read_text()),
            json.loads(seal_path.read_text()),
        )
    return result


def test_bundle_and_manifest_hashes(bundles):
    for bundle, seal in bundles.values():
        unsigned_bundle = dict(bundle)
        bundle_sha = unsigned_bundle.pop("bundle_sha256")
        assert sha256_value(unsigned_bundle) == bundle_sha
        manifest = dict(bundle["episode_manifest"])
        manifest_sha = manifest.pop("manifest_sha256")
        assert sha256_value(manifest) == manifest_sha
        unsigned_seal = dict(seal)
        seal_sha = unsigned_seal.pop("seal_sha256")
        assert sha256_value(unsigned_seal) == seal_sha
        assert seal["bundle_sha256"] == bundle["bundle_sha256"]


def test_real_process_and_identity_separation(bundles):
    for bundle, _ in bundles.values():
        owners = bundle["service_manifest"]["owners"]
        for field in (
            "actual_pid",
            "public_key_hex",
            "state_source_id",
            "state_head_at_start",
            "backend_identity_sha256",
        ):
            assert len({owners[owner][field] for owner in OWNER_IDS}) == 6
        pids = {owners[owner]["actual_pid"] for owner in OWNER_IDS}
        pids.add(bundle["service_manifest"]["target"]["actual_pid"])
        pids.add(bundle["arm_transcript"]["process_id"])
        assert len(pids) == 8
        assert set(bundle["runtime_log"]["process_exit_codes"].values()) == {0}


def test_native_signatures_and_freeze_receipts(bundles):
    for bundle, _ in bundles.values():
        service = bundle["service_manifest"]
        for owner in OWNER_IDS:
            public_key = service["owners"][owner]["public_key_hex"]
            log = bundle["owner_native_logs"][owner]
            assert verify_signed(log["freeze_receipt"], public_key)
            assert log["freeze_receipt"]["terminal_head"] == log["state_head"]
            for record in log["entries"]:
                assert verify_signed(record, public_key)
        target_key = service["target"]["public_key_hex"]
        target = bundle["target_native_log"]
        assert verify_signed(target["freeze_receipt"], target_key)
        assert all(verify_signed(record, target_key) for record in target["entries"])


def test_e1_exact_native_shape(bundles):
    bundle, _ = bundles["E1-EXTANT-MULTI-OWNER"]
    target = bundle["target_native_log"]
    assert len(target["occurrences"]) == 1
    assert [sample["minute"] for sample in target["sensor_samples"]] == list(range(46))
    assert all(2.85 <= sample["power_kw"] <= 3.15 for sample in target["sensor_samples"])
    assert all(sample["safety_ok"] and sample["noise_ok"] for sample in target["sensor_samples"])
    assert all(sample["other_circuits_energized"] == [] for sample in target["sensor_samples"])
    acceptances = [
        record
        for owner in ("O_Q", "O_V")
        for record in bundle["owner_native_logs"][owner]["entries"]
        if record["payload"]["kind"] == "ACCEPTANCE"
    ]
    assert len(acceptances) == 2
    finality = [
        record
        for record in bundle["owner_native_logs"]["O_P"]["entries"]
        if record["payload"]["kind"] == "FINALITY"
    ]
    assert len(finality) == 1
    assert set(finality[0]["payload"]["acceptance_hashes"]) == {
        record["response_sha256"] for record in acceptances
    }


def test_e5_refusal_has_zero_effect_acceptance_and_finality(bundles):
    bundle, _ = bundles["E5-IMPOSSIBLE-REFUSAL"]
    refusal = bundle["owner_native_logs"]["O_V"]["entries"]
    assert len(refusal) == 1
    assert refusal[0]["payload"]["decision"] == "REFUSED"
    assert refusal[0]["payload"]["delegable"] is False
    assert bundle["target_native_log"]["entries"] == []
    assert not any(
        record["payload"]["kind"] in {"ACCEPTANCE", "FINALITY"}
        for log in bundle["owner_native_logs"].values()
        for record in log["entries"]
    )
    reveal = bundle["private_case_reveal"]
    assert reveal["alternative_oracle"]["feasible_alternatives"] == []
    assert all(
        shard["known_feasible_alternatives"] == []
        for shard in reveal["owner_initial_shards"].values()
    )
    assert sha256_value(reveal) == bundle["private_case_receipt"]["private_truth_sha256"]


def test_arm_visibility_and_fragment_binding(bundles):
    forbidden = {
        "ExactTaskSuccess",
        "CorrectResolution",
        "contract_score",
        "success",
        "correct",
    }
    for bundle, _ in bundles.values():
        receipt = bundle["runtime_log"]["arm_visibility_receipt"]
        assert receipt["process_start_method"] == "spawn"
        assert receipt["private_canary_absent"] is True
        payload_bytes = receipt["start_payload_bytes"]
        transcript_bytes = json.dumps(
            bundle["arm_transcript"],
            sort_keys=True,
            separators=(",", ":"),
        )
        assert "case_id" not in payload_bytes
        assert "manifest_sha256" not in payload_bytes
        assert bundle["episode_manifest"]["manifest_sha256"] not in transcript_bytes
        assert (
            receipt["start_payload"]["episode_manifest"]["arm_binding_token"]
            == bundle["episode_manifest"]["arm_binding_token"]
        )
        for semantic_label in (
            "E1-EXTANT-MULTI-OWNER",
            "E5-IMPOSSIBLE-REFUSAL",
            "e1-extant-multi-owner",
            "e5-impossible-refusal",
        ):
            assert semantic_label not in payload_bytes
            assert semantic_label not in transcript_bytes
        assert set(receipt["start_payload"]).isdisjoint(
            {
                "case_id",
                "private_case_receipt",
                "private_case_reveal",
                "private_canary",
                "expected",
            }
        )
        assert "case_id" not in receipt["start_payload"]["episode_manifest"]
        assert "manifest_sha256" not in receipt["start_payload"]["episode_manifest"]
        manifest = bundle["episode_manifest"]
        for namespace, fragment in bundle["component_fragments"].items():
            assert namespace == fragment["namespace"]
            for key in (
                "run_id",
                "world_root",
                "case_id",
                "manifest_sha256",
                "q_version",
                "object_id",
                "operation_id",
            ):
                assert fragment[key] == manifest[key]
            assert forbidden.isdisjoint(fragment)


def test_cli_case_argument_is_not_in_child_visibility(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "run.py"),
            "--case",
            "E1-EXTANT-MULTI-OWNER",
            "--artifacts-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    emitted = json.loads(completed.stdout.strip())
    bundle = json.loads(pathlib.Path(emitted["bundle"]).read_text())
    observation = bundle["arm_transcript"]["events"][0]
    visible = json.dumps(observation, sort_keys=True)
    assert "E1-EXTANT-MULTI-OWNER" not in visible
    assert "E5-IMPOSSIBLE-REFUSAL" not in visible
    assert observation["argv"][-1] == "--opaque-arm-child"
    assert observation["process_name"].removeprefix("ce001-A4-").isdigit()


def test_duplicate_execute_is_idempotent(tmp_path):
    bundle_path, _ = run_case(
        "E1-EXTANT-MULTI-OWNER",
        tmp_path,
        duplicate_execute_probe=True,
    )
    bundle = json.loads(bundle_path.read_text())
    target = bundle["target_native_log"]
    execute_requests = [
        request
        for request in bundle["arm_transcript"]["target_requests"]
        if request["payload"]["action"] == "EXECUTE"
    ]
    probe = [
        event
        for event in bundle["arm_transcript"]["events"]
        if event["kind"] == "IDEMPOTENCY_PROBE"
    ]
    assert len(execute_requests) == 2
    assert len(target["occurrences"]) == 1
    assert len(target["sensor_samples"]) == 46
    assert len(probe) == 1
    assert probe[0]["replay_decision"] == "IDEMPOTENT_REPLAY"
    assert (
        probe[0]["replay_occurrence_event_sha256"]
        == probe[0]["first_occurrence_event_sha256"]
    )
