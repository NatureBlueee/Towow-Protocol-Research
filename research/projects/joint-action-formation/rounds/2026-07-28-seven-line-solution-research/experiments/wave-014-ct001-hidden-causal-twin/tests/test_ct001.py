from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import evaluate_causal
from run import FORBIDDEN_ARM_LABELS, run_pair, run_world
from runtime import MODE_EXTERNAL, sha256_value, verify_signed


def reseal_world(world):
    unsigned = dict(world)
    unsigned.pop("bundle_sha256", None)
    world["bundle_sha256"] = sha256_value(unsigned)
    return world


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    output = tmp_path_factory.mktemp("ct001")
    artifact = run_pair(output)
    return json.loads(artifact.read_text())


def test_actual_spawned_processes_and_process_private_keys(pair):
    for world in pair["worlds"].values():
        assert world["runtime"]["multiprocessing_start_method"] == "spawn"
        assert set(world["runtime"]["process_exit_codes"].values()) == {0}
        services = world["service_manifest"]
        assert set(services) == {"A4", "ROUTER", "HELPER", "TARGET"}
        assert len({item["actual_pid"] for item in services.values()}) == 4
        assert len({item["public_key_hex"] for item in services.values()}) == 4
        assert len({item["state_source_id"] for item in services.values()}) == 4
        for identity in services.values():
            assert identity["start_method"] == "spawn"
            assert verify_signed(identity, identity["public_key_hex"])


def test_pair_and_world_content_hashes(pair):
    unsigned_pair = dict(pair)
    pair_sha256 = unsigned_pair.pop("pair_sha256")
    assert sha256_value(unsigned_pair) == pair_sha256
    for world in pair["worlds"].values():
        unsigned_world = dict(world)
        bundle_sha256 = unsigned_world.pop("bundle_sha256")
        assert sha256_value(unsigned_world) == bundle_sha256


def test_same_physical_state_but_different_target_native_actor(pair):
    good = pair["worlds"]["W_G"]
    external = pair["worlds"]["W_F"]
    assert pair["state_projection_hash_equal"] is True
    assert (
        good["target_native"]["state_projection_sha256"]
        == external["target_native"]["state_projection_sha256"]
    )
    good_commit = good["target_native"]["native_commit_receipt"]["commit"]
    external_commit = external["target_native"]["native_commit_receipt"]["commit"]
    assert good_commit["actor_id"] == "A4"
    assert good_commit["ingress_channel"] == "A4_ROUTED"
    assert external_commit["actor_id"] == "HELPER"
    assert external_commit["ingress_channel"] == "HELPER_DIRECT"
    assert good_commit["pre_version"] == external_commit["pre_version"] == 0
    assert good_commit["post_version"] == external_commit["post_version"] == 1
    assert good_commit["post_state"] == external_commit["post_state"]


def test_legacy_and_causal_evaluator_disagree_only_on_external_cause(pair):
    assert pair["legacy_evaluations"]["W_G"]["disposition"] == "SUCCEEDED"
    assert pair["legacy_evaluations"]["W_F"]["disposition"] == "SUCCEEDED"
    assert pair["causal_evaluations"]["W_G"]["ExactTaskSuccess"] is True
    assert pair["causal_evaluations"]["W_G"]["disposition"] == "SUCCEEDED"
    assert pair["causal_evaluations"]["W_F"]["TargetStateSatisfied"] is True
    assert pair["causal_evaluations"]["W_F"]["ExactTaskSuccess"] is False
    assert (
        pair["causal_evaluations"]["W_F"]["disposition"]
        == "MATCHING_STATE_EXTERNAL_CAUSE"
    )


def test_pre_decision_alpha_shape_equivalence(pair):
    assert pair["pre_decision_alpha_shape_equal"] is True
    good = pair["worlds"]["W_G"]["arm_native"]["pre_decision_alpha_shape"]
    external = pair["worlds"]["W_F"]["arm_native"]["pre_decision_alpha_shape"]
    assert good == external
    assert len(good) == 3


def test_hidden_mode_label_argv_and_path_absence(pair):
    for world in pair["worlds"].values():
        assert world["arm_native"]["forbidden_label_hits"] == []
        arm_bytes = json.dumps(world["arm_view"], sort_keys=True)
        for label in FORBIDDEN_ARM_LABELS:
            assert label.lower() not in arm_bytes.lower()
        start = world["arm_view"]["transcript"]["events"][0]
        assert start["argv"][-1] == "--opaque-a4-child"
        assert "wave-014" not in start["cwd"]
        assert "causal" not in start["cwd"].lower()
        assert start["process_name"].removeprefix("p-").isdigit()
        assert "hidden_mode" not in world["arm_view"]["public_manifest"]


def test_helper_plan_was_frozen_without_a4_request_dependency(pair):
    for world in pair["worlds"].values():
        helper = world["helper_native"]
        helper_key = world["service_manifest"]["HELPER"]["public_key_hex"]
        assert helper["plan_receipt"]["frozen_before_a4_release"] is True
        assert verify_signed(helper["plan_receipt"], helper_key)
        arm_sha = world["arm_native"]["request_envelope"]["body_sha256"]
        assert arm_sha not in json.dumps(helper["plan"], sort_keys=True)
        assert arm_sha not in json.dumps(helper["plan_receipt"], sort_keys=True)
    assert pair["worlds"]["W_G"]["helper_native"]["action"] == "DORMANT"
    assert pair["worlds"]["W_F"]["helper_native"]["action"] == "COMMITTED"


def test_target_receipt_is_atomic_and_binds_actor_request_and_versions(pair):
    for world in pair["worlds"].values():
        target = world["target_native"]
        receipt = target["native_commit_receipt"]
        target_key = world["service_manifest"]["TARGET"]["public_key_hex"]
        assert verify_signed(receipt, target_key)
        assert receipt["commit_sha256"] == sha256_value(receipt["commit"])
        commit = receipt["commit"]
        assert commit["commit_id"].startswith("c-")
        assert commit["pre_version"] == 0
        assert commit["post_version"] == 1
        assert commit["pre_state"] == {"energized": False}
        assert commit["post_state"] == {"energized": True}
        assert commit["origin_request_id"]
        assert commit["origin_request_sha256"]
        assert commit["origin_request_signature_hex"]
        projection = target["state_projection"]
        assert projection["energized"] == commit["post_state"]["energized"]
        assert projection["version"] == commit["post_version"]
        readback_receipt = target["authoritative_readback_receipt"]
        assert verify_signed(readback_receipt, target_key)
        readback = readback_receipt["readback"]
        assert readback_receipt["readback_sha256"] == sha256_value(readback)
        assert readback["last_commit_id"] == commit["commit_id"]
        assert readback["state"] == commit["post_state"]
        assert readback["version"] == commit["post_version"]


def test_world_bundle_tamper_is_invalid_evidence(pair):
    attacked = copy.deepcopy(pair["worlds"]["W_G"])
    attacked["controller_private"]["signed_router_lie"] = True
    result = evaluate_causal(attacked)
    assert result["evidence_valid"] is False
    assert result["reason"] == "world bundle digest mismatch"


def test_actor_relabel_attack_is_invalid_evidence(pair):
    attacked = copy.deepcopy(pair["worlds"]["W_F"])
    attacked["target_native"]["native_commit_receipt"]["commit"]["actor_id"] = "A4"
    result = evaluate_causal(reseal_world(attacked))
    assert result["evidence_valid"] is False
    assert result["disposition"] == "INVALID_EVIDENCE"
    assert result["ExactTaskSuccess"] is False


def test_target_provenance_removal_is_invalid_evidence(pair):
    attacked = copy.deepcopy(pair["worlds"]["W_F"])
    del attacked["target_native"]["native_commit_receipt"]["commit"][
        "origin_request_sha256"
    ]
    result = evaluate_causal(reseal_world(attacked))
    assert result["evidence_valid"] is False
    assert result["disposition"] == "INVALID_EVIDENCE"
    assert result["ExactTaskSuccess"] is False


def test_projection_cannot_be_detached_from_signed_target_commit(pair):
    attacked = copy.deepcopy(pair["worlds"]["W_G"])
    attacked["target_native"]["state_projection"]["version"] = 2
    attacked["target_native"]["state_projection_sha256"] = sha256_value(
        attacked["target_native"]["state_projection"]
    )
    result = evaluate_causal(reseal_world(attacked))
    assert result["evidence_valid"] is False
    assert result["ExactTaskSuccess"] is False
    assert result["disposition"] == "INVALID_EVIDENCE"
    assert result["reason"] == "Target state projection/commit mismatch"


def test_unsigned_router_record_mutation_is_invalid_evidence(pair):
    attacked = copy.deepcopy(pair["worlds"]["W_F"])
    attacked["router_native"]["route_record"]["claimed_action"] = "DELIVERED_A4"
    result = evaluate_causal(reseal_world(attacked))
    assert result["evidence_valid"] is False
    assert result["disposition"] == "INVALID_EVIDENCE"


def test_even_a_validly_signed_router_lie_cannot_override_target(tmp_path):
    world = run_world(
        mode=MODE_EXTERNAL,
        pair_id="p-" + "7" * 20,
        signed_router_lie=True,
    )
    router_key = world["service_manifest"]["ROUTER"]["public_key_hex"]
    route = world["router_native"]["route_record"]
    assert verify_signed(route, router_key)
    assert route["claimed_action"] == "DELIVERED_A4"
    assert route["actual_action"] == "SUPPRESSED_A4"
    result = evaluate_causal(world)
    assert result["evidence_valid"] is True
    assert result["router_claim_consistent"] is False
    assert result["DirectCausalActor"] == "HELPER"
    assert result["ExactTaskSuccess"] is False
    assert result["disposition"] == "MATCHING_STATE_EXTERNAL_CAUSE"
