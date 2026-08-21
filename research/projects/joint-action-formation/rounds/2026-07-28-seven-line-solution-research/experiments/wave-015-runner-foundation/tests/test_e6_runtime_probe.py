from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from e6_runtime_probe import (
    RUNTIME_IDS,
    RUNTIME_VIEW_SCHEMA,
    evaluate_action_result,
    run_e6_runtime_probe,
    verify_capsule,
    verify_signed,
)
from hidden_world import verify_private_packet


@pytest.fixture(scope="module")
def probe():
    return run_e6_runtime_probe()


def test_three_actual_spawn_processes_share_one_view_schema(probe):
    json.dumps(probe, sort_keys=True)
    launches = probe["launch_receipts"]
    assert set(launches) == set(RUNTIME_IDS)
    assert probe["same_arm_view_schema"] is True
    assert probe["same_arm_view_hash"] is True
    assert probe["arm_view_schema"] == RUNTIME_VIEW_SCHEMA
    assert {
        receipt["process_start_method"] for receipt in launches.values()
    } == {"spawn"}
    assert len(
        {receipt["launcher_instance_id"] for receipt in launches.values()}
    ) == 1
    assert len(
        {receipt["worker_code_sha256"] for receipt in launches.values()}
    ) == 1
    assert len(
        {
            receipt["runtime_identity"]["process_id"]
            for receipt in launches.values()
        }
    ) == 3
    assert len(
        {
            receipt["runtime_identity"]["public_key_hex"]
            for receipt in launches.values()
        }
    ) == 3
    assert all(
        verify_signed(
            receipt["runtime_identity"],
            receipt["runtime_identity"]["public_key_hex"],
        )
        for receipt in launches.values()
    )


def test_all_three_used_same_blind_visibility_surface_shape(probe):
    surfaces = [
        receipt["visible_surface"]
        for receipt in probe["launch_receipts"].values()
    ]
    assert all(surface["argv"] == ["wave015-blind-child", "--opaque"] for surface in surfaces)
    assert all(surface["cwd_entries"] == [] for surface in surfaces)
    assert all(surface["process_name"].startswith("arm-worker-") for surface in surfaces)
    assert all(
        set(surface["environment"]) == {"LANG", "PATH", "PYTHONHASHSEED"}
        for surface in surfaces
    )
    assert len({tuple(sorted(surface)) for surface in surfaces}) == 1
    assert len({surface["view_bytes"] for surface in surfaces}) == 1


def test_crash_schedule_exists_only_in_controller_private_packet(probe):
    schedule = probe["private_schedule_packet"]["private_payload"]["schedule"]
    arm_bytes = json.dumps(probe["arm_view"], sort_keys=True)
    surfaces_bytes = json.dumps(
        {
            key: value["visible_surface"]
            for key, value in probe["launch_receipts"].items()
        },
        sort_keys=True,
    )
    for secret in (
        "E6-MIGRATION-REPLAY",
        schedule["crash_cut"],
        schedule["trigger_event_sha256"],
        "old_runtime_restart_minute",
    ):
        assert secret not in arm_bytes
        assert secret not in surfaces_bytes
    assert all(
        receipt["private_material_absent"] is True
        for receipt in probe["launch_receipts"].values()
    )


def test_exact_native_event_triggered_capsule_then_external_termination(probe):
    source_event = probe["source_native_event"]
    schedule = probe["private_schedule_packet"]["private_payload"]["schedule"]
    assert source_event["body_sha256"] == schedule["trigger_event_sha256"]
    assert source_event["body"]["logical_minute"] == schedule[
        "trigger_logical_minute"
    ]
    assert verify_private_packet(
        probe["trigger_packet"],
        expected_controller_instance_id=probe["controller_identity"][
            "controller_instance_id"
        ],
        expected_controller_public_key_hex=probe["controller_identity"][
            "controller_public_key_hex"
        ],
        expected_kind="E6_TRIGGER_FIRED",
        expected_episode_binding=probe["arm_view"]["episode_instance_id"],
        expected_public_view=probe["arm_view"],
    )
    assert probe["exit_codes"]["source"] is not None
    assert probe["exit_codes"]["source"] != 0
    assert verify_capsule(
        probe["capsule"],
        expected_source_public_key_hex=probe["launch_receipts"]["source"][
            "runtime_identity"
        ]["public_key_hex"],
        expected_episode_instance_id=probe["arm_view"]["episode_instance_id"],
        expected_operation_id=probe["arm_view"]["operation_id"],
        expected_public_view_sha256=probe["launch_receipts"]["source"][
            "runtime_identity"
        ]["public_view_sha256"],
    )
    assert [
        event["event"] for event in probe["lifecycle_trace"][:4]
    ] == [
        "SOURCE_NATIVE_EVENT",
        "EXACT_SCHEDULE_TRIGGERED",
        "SOURCE_CAPSULE_EXPORTED",
        "SOURCE_EXTERNALLY_TERMINATED",
    ]


def test_migrated_epoch_is_accepted_and_old_epoch_is_rejected(probe):
    migrated = probe["migrated_action_evaluation"]
    old = probe["old_runtime_action_evaluation"]
    assert migrated == {
        "valid": True,
        "authorized_execution": True,
        "decision": "ACCEPTED",
    }
    assert old == {
        "valid": True,
        "authorized_execution": False,
        "decision": "REJECTED_STALE_EPOCH",
    }
    assert probe["migrated_action_result"]["executed"] is True
    assert probe["old_runtime_action_result"]["executed"] is False
    assert probe["exit_codes"]["migrated"] == 0
    assert probe["exit_codes"]["old_runtime_restart"] == 0


def test_capsule_transplant_to_another_episode_is_rejected(probe):
    source_key = probe["launch_receipts"]["source"]["runtime_identity"][
        "public_key_hex"
    ]
    assert not verify_capsule(
        probe["capsule"],
        expected_source_public_key_hex=source_key,
        expected_episode_instance_id="episode-" + ("0" * 32),
        expected_operation_id=probe["arm_view"]["operation_id"],
        expected_public_view_sha256=probe["launch_receipts"]["source"][
            "runtime_identity"
        ]["public_view_sha256"],
    )


def test_capsule_rewrite_is_rejected(probe):
    attacked = copy.deepcopy(probe["capsule"])
    attacked["source_epoch"] = 9
    assert not verify_capsule(
        attacked,
        expected_source_public_key_hex=probe["launch_receipts"]["source"][
            "runtime_identity"
        ]["public_key_hex"],
        expected_episode_instance_id=probe["arm_view"]["episode_instance_id"],
        expected_operation_id=probe["arm_view"]["operation_id"],
        expected_public_view_sha256=probe["launch_receipts"]["source"][
            "runtime_identity"
        ]["public_view_sha256"],
    )


def test_old_runtime_cannot_self_claim_success_after_fence_rejection(probe):
    attacked = copy.deepcopy(probe["old_runtime_action_result"])
    attacked["executed"] = True
    evaluation = evaluate_action_result(attacked, probe["fence_identity"])
    assert evaluation["valid"] is False
    assert evaluation["authorized_execution"] is False


def test_fence_receipt_transplant_between_requests_is_detected(probe):
    attacked = copy.deepcopy(probe["migrated_action_result"])
    attacked["request"] = copy.deepcopy(
        probe["old_runtime_action_result"]["request"]
    )
    evaluation = evaluate_action_result(attacked, probe["fence_identity"])
    assert evaluation["valid"] is False
    assert evaluation["authorized_execution"] is False
