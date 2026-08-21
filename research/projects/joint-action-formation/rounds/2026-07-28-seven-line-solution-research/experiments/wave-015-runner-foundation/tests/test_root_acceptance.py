from __future__ import annotations

import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hidden_world import verify_private_packet
from e6_runtime_probe import (
    RUNTIME_IDS,
    RUNTIME_VIEW_SCHEMA,
    evaluate_action_result,
    verify_capsule,
    verify_fence_receipt,
    verify_signed,
)
from target_ledger import ALREADY_SATISFIED, COMMITTED, CONFLICT, TargetOperationLedger
from visibility import canonical_bytes, sha256_value


RUN_ID = "foundation-2cceea49ee07d0790e48"
ARTIFACT_DIR = ROOT / "artifacts" / RUN_ID
BUNDLE_PATH = ARTIFACT_DIR / "foundation-bundle.json"
DATABASE_PATH = ARTIFACT_DIR / "target-ledger.sqlite3"
BUNDLE_FILE_SHA256 = (
    "97f2551c7ac511848065f5bf8198e3cdaa6ac8f48e70c747a573d8726df5a178"
)
BUNDLE_SHA256 = "8f4ff7825120518d38d23408bf65c5290ab716f605507ec8b2740d6496f54c0b"
DATABASE_SHA256 = "9b2f160d15078e04b6503b14382be087f6077301569f6835044dd3997aaffc69"


def test_frozen_foundation_artifact_recomputes_and_verifies_independently():
    bundle_raw = BUNDLE_PATH.read_bytes()
    assert hashlib.sha256(bundle_raw).hexdigest() == BUNDLE_FILE_SHA256
    assert hashlib.sha256(DATABASE_PATH.read_bytes()).hexdigest() == DATABASE_SHA256
    bundle = json.loads(bundle_raw)
    unsigned = dict(bundle)
    assert unsigned.pop("bundle_sha256") == BUNDLE_SHA256
    assert sha256_value(unsigned) == BUNDLE_SHA256
    assert bundle["run_id"] == RUN_ID

    launch = bundle["visibility"]["launch_receipt"]
    assert launch["status"] == "CHILD_VISIBLE_SURFACE_RECORDED"
    assert launch["process_start_method"] == "spawn"
    assert launch["visible_surface"]["view"] == bundle["visibility"]["e4_arm_view"]
    visible_bytes = canonical_bytes(launch["visible_surface"])
    for forbidden in (
        b"E3A-ACK-LOST-EFFECT",
        b"E3B-ACK-LOST-NO-EFFECT",
        b"E4-REVOKE-WITH-ALTERNATIVE",
        b"E6-MIGRATION-REPLAY",
        b"principal-alternative",
    ):
        assert forbidden not in visible_bytes

    identity = bundle["controller_identity"]

    def verify(packet, kind, episode, public_view):
        assert verify_private_packet(
            packet,
            expected_controller_instance_id=identity["controller_instance_id"],
            expected_controller_public_key_hex=identity[
                "controller_public_key_hex"
            ],
            expected_kind=kind,
            expected_episode_binding=episode,
            expected_public_view=public_view,
        )

    e3 = bundle["hidden_scenarios"]["e3"]
    assert e3["raw_prefix_equal"] is True
    assert e3["alpha_equivalent"] is True
    e3_episode = f"{RUN_ID}-e3"
    for fork in e3["forks"]:
        verify(
            fork["private_packet"],
            "E3_PAIRED_FORK",
            e3_episode,
            e3["shared_pre_readback_public_view"],
        )
    verify(
        e3["pair_private_packet"],
        "E3_PAIR_BINDING",
        e3_episode,
        e3["shared_pre_readback_public_view"],
    )

    e4 = bundle["hidden_scenarios"]["e4"]
    e4_episode = f"{RUN_ID}-e4"
    verify(
        e4["frozen"]["private_packet"],
        "E4_HIDDEN_TOPOLOGY",
        e4_episode,
        e4["frozen"]["arm_view"],
    )
    verify(
        e4["revoke_private_packet"],
        "E4_PRIMARY_REVOKE",
        e4_episode,
        e4["frozen"]["arm_view"],
    )
    for route in e4["route_private_packets"]:
        verify(
            route,
            "E4_BROKER_ROUTE",
            e4_episode,
            e4["frozen"]["arm_view"],
        )
    assert e4["primary_discovery"]["status"] == "FOUND"
    assert e4["alternative_discovery"]["status"] == "FOUND"
    assert (
        e4["primary_discovery"]["owner_handle"]
        != e4["alternative_discovery"]["owner_handle"]
    )

    e6 = bundle["hidden_scenarios"]["e6"]
    e6_episode = f"{RUN_ID}-e6"
    verify(
        e6["frozen"]["private_packet"],
        "E6_CRASH_SCHEDULE",
        e6_episode,
        e6["frozen"]["arm_view"],
    )
    verify(
        e6["fired_private_packet"],
        "E6_TRIGGER_FIRED",
        e6_episode,
        e6["frozen"]["arm_view"],
    )

    target = bundle["target_ledger"]
    assert target["database_sha256"] == DATABASE_SHA256
    ledger = TargetOperationLedger(
        DATABASE_PATH,
        ledger_id=target["ledger_id"],
    )
    h_first = target["h_first_receipt"]
    a4_after_h = target["a4_after_h_receipt"]
    assert h_first["decision"] == COMMITTED
    assert h_first["commit_actor_id"] == "H"
    assert a4_after_h["decision"] == ALREADY_SATISFIED
    assert a4_after_h["mutation_applied"] is False
    assert a4_after_h["commit_id"] == h_first["commit_id"]
    assert a4_after_h["commit_actor_id"] == "H"
    assert ledger.verify_receipt(h_first)
    assert ledger.verify_receipt(a4_after_h)
    assert ledger.verify_readback(target["a4_after_h_readback"], a4_after_h)
    assert sorted(
        receipt["decision"] for receipt in target["concurrent_receipts"]
    ) == sorted([COMMITTED, CONFLICT])
    assert all(
        ledger.verify_receipt(receipt)
        for receipt in target["concurrent_receipts"]
    )

    probe = bundle["e6_runtime_probe"]
    assert probe["arm_view_schema"] == RUNTIME_VIEW_SCHEMA
    assert probe["same_arm_view_schema"] is True
    assert probe["same_arm_view_hash"] is True
    launches = probe["launch_receipts"]
    assert set(launches) == set(RUNTIME_IDS)
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
    assert len(
        {receipt["launcher_instance_id"] for receipt in launches.values()}
    ) == 1
    assert len(
        {receipt["worker_code_sha256"] for receipt in launches.values()}
    ) == 1
    for receipt in launches.values():
        assert receipt["process_start_method"] == "spawn"
        assert receipt["visible_surface"]["view"]["schema"] == RUNTIME_VIEW_SCHEMA
        identity_receipt = receipt["runtime_identity"]
        assert verify_signed(
            identity_receipt, identity_receipt["public_key_hex"]
        )

    probe_controller = probe["controller_identity"]

    def verify_probe_packet(packet, kind):
        assert verify_private_packet(
            packet,
            expected_controller_instance_id=probe_controller[
                "controller_instance_id"
            ],
            expected_controller_public_key_hex=probe_controller[
                "controller_public_key_hex"
            ],
            expected_kind=kind,
            expected_episode_binding=probe["arm_view"][
                "episode_instance_id"
            ],
            expected_public_view=probe["arm_view"],
        )

    verify_probe_packet(
        probe["private_schedule_packet"], "E6_CRASH_SCHEDULE"
    )
    verify_probe_packet(probe["trigger_packet"], "E6_TRIGGER_FIRED")
    schedule = probe["private_schedule_packet"]["private_payload"]["schedule"]
    assert (
        probe["source_native_event"]["body_sha256"]
        == schedule["trigger_event_sha256"]
    )
    assert (
        probe["source_native_event"]["body"]["logical_minute"]
        == schedule["trigger_logical_minute"]
    )
    assert verify_capsule(
        probe["capsule"],
        expected_source_public_key_hex=launches["source"]["runtime_identity"][
            "public_key_hex"
        ],
        expected_episode_instance_id=probe["arm_view"][
            "episode_instance_id"
        ],
        expected_operation_id=probe["arm_view"]["operation_id"],
        expected_public_view_sha256=launches["source"]["runtime_identity"][
            "public_view_sha256"
        ],
    )
    assert verify_fence_receipt(
        probe["fence_advance_receipt"], probe["fence_identity"]
    )
    assert evaluate_action_result(
        probe["migrated_action_result"], probe["fence_identity"]
    ) == {
        "valid": True,
        "authorized_execution": True,
        "decision": "ACCEPTED",
    }
    assert evaluate_action_result(
        probe["old_runtime_action_result"], probe["fence_identity"]
    ) == {
        "valid": True,
        "authorized_execution": False,
        "decision": "REJECTED_STALE_EPOCH",
    }
    assert probe["exit_codes"] == {
        "source": -15,
        "migrated": 0,
        "old_runtime_restart": 0,
    }
    assert [
        event["event"] for event in probe["lifecycle_trace"]
    ] == [
        "SOURCE_NATIVE_EVENT",
        "EXACT_SCHEDULE_TRIGGERED",
        "SOURCE_CAPSULE_EXPORTED",
        "SOURCE_EXTERNALLY_TERMINATED",
        "FENCE_ADVANCED",
        "MIGRATED_EPOCH_DECIDED",
        "OLD_RUNTIME_EPOCH_DECIDED",
    ]
    probe_visible = canonical_bytes(
        {
            runtime_id: receipt["visible_surface"]
            for runtime_id, receipt in launches.items()
        }
    )
    for private_value in (
        b"E6-MIGRATION-REPLAY",
        schedule["crash_cut"].encode(),
        schedule["trigger_event_sha256"].encode(),
        b"old_runtime_restart_minute",
    ):
        assert private_value not in probe_visible
    assert "target_process" not in probe
    assert "target_ledger" not in probe
    assert "target_readback" not in probe
    assert "NO_TARGET_EFFECT_OR_FULL_E6_COMPLETION" in probe[
        "evidence_boundary"
    ]
