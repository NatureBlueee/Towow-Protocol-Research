from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hidden_world import (
    HiddenScenarioController,
    OwnerTopologyBroker,
    alpha_shape,
    arm_key_violations,
    canonical_bytes,
    verify_private_packet,
)
from visibility import (
    PUBLIC_INPUT_SCHEMA,
    ArmViewFactory,
    VisibilityViolation,
)


def public_input(**extra):
    task = {
        "q_version": "Q@v1",
        "object_id": "VenueV:CircuitC7",
        "target_id": "VenueV:CircuitC7",
        "deadline_minute": 90,
        "required_duration_minutes": 45,
        "required_power_kw": 3.0,
        "power_tolerance_percent": 5,
    }
    task.update(extra)
    return {"schema": PUBLIC_INPUT_SCHEMA, "task": task}


def base_arm_view(broker_surface=None):
    return ArmViewFactory(
        arm_id="A4-DETERMINISTIC-MATURE-COMPOSITION"
    ).build(public_input(), broker_surface=broker_surface)


def e4_topology():
    return [
        {
            "owner_instance_id": "O_R:primary",
            "owner_role": "RESOURCE_PRIMARY",
            "principal_id": "principal-primary",
            "authority_locus": "P",
            "resource_kind": "MOBILE_3KW_GENERATOR",
            "discoverability_condition": "INITIAL",
            "current_head": "a" * 64,
            "epoch": 1,
        },
        {
            "owner_instance_id": "O_R:alternative",
            "owner_role": "RESOURCE_ALTERNATIVE",
            "principal_id": "principal-alternative",
            "authority_locus": "P",
            "resource_kind": "MOBILE_3KW_GENERATOR",
            "discoverability_condition": "AFTER_PRIMARY_REVOKE",
            "current_head": "b" * 64,
            "epoch": 1,
        },
    ]


def test_hidden_controller_accepts_only_the_canonical_validated_arm_view():
    controller = HiddenScenarioController()
    view = controller.arm_view(base_arm_view())
    encoded = json.dumps(view, sort_keys=True)
    assert view["schema"] == "CE001_ARM_VIEW_V1"
    assert "broker_surface" in view
    assert arm_key_violations(view) == []
    attacked = base_arm_view()
    attacked["scenario_label"] = "E4-REVOKE-WITH-ALTERNATIVE"
    with pytest.raises(VisibilityViolation):
        controller.arm_view(attacked)


def test_broker_surface_unknown_field_fails_closed():
    with pytest.raises(VisibilityViolation):
        ArmViewFactory(
            arm_id="A4-DETERMINISTIC-MATURE-COMPOSITION"
        ).build(
            public_input(),
            broker_surface={
                "endpoint_handle": "a" * 32,
                "capabilities": ["DISCOVER", "REQUEST", "STATUS"],
                "surface_version": 1,
                "topology_sha256": "b" * 64,
            },
        )


def test_e3_paired_fork_replays_identical_pre_readback_view():
    controller = HiddenScenarioController()
    frozen = controller.freeze_e3_pair(
        episode_binding="episode-e3-pair",
        base_arm_view=base_arm_view(),
    )
    first, second = frozen["forks"]
    assert frozen["raw_prefix_equal"] is True
    assert frozen["alpha_equivalent"] is True
    assert canonical_bytes(first["arm_view"]) == canonical_bytes(second["arm_view"])
    assert alpha_shape(first["arm_view"]) == alpha_shape(second["arm_view"])
    assert (
        first["private_packet"]["private_payload"][
            "target_commit_before_readback"
        ]
        is True
    )
    assert (
        second["private_packet"]["private_payload"][
            "target_commit_before_readback"
        ]
        is False
    )
    assert controller.verify_private_packet(
        frozen["pair_private_packet"],
        expected_kind="E3_PAIR_BINDING",
        expected_episode_binding="episode-e3-pair",
        expected_public_view=frozen["shared_pre_readback_public_view"],
    )


def test_e3_private_labels_and_outcomes_are_absent_from_arm():
    controller = HiddenScenarioController()
    frozen = controller.freeze_e3_pair(
        episode_binding="episode-e3-hidden",
        base_arm_view=base_arm_view(),
    )
    for fork in frozen["forks"]:
        arm_bytes = json.dumps(fork["arm_view"], sort_keys=True)
        assert "E3A" not in arm_bytes
        assert "E3B" not in arm_bytes
        assert "target_commit_before_readback" not in arm_bytes
        assert "ACK-LOST" not in arm_bytes
        assert controller.verify_private_packet(
            fork["private_packet"],
            expected_kind="E3_PAIRED_FORK",
            expected_episode_binding="episode-e3-hidden",
            expected_public_view=frozen["shared_pre_readback_public_view"],
        )


def test_e4_topology_is_hidden_behind_fixed_broker_surface():
    controller = HiddenScenarioController()
    broker = OwnerTopologyBroker()
    frozen = controller.freeze_e4(
        episode_binding="episode-e4",
        base_arm_view=base_arm_view(broker.public_surface()),
        broker=broker,
        topology=e4_topology(),
    )
    encoded = json.dumps(frozen["arm_view"], sort_keys=True)
    for forbidden in (
        "O_R:primary",
        "O_R:alternative",
        "principal-primary",
        "principal-alternative",
        "RESOURCE_ALTERNATIVE",
        "topology_candidate_sha256",
        "owner_count",
    ):
        assert forbidden not in encoded
    surface = frozen["arm_view"]["broker_surface"]
    assert set(surface) == {"endpoint_handle", "capabilities", "surface_version"}
    assert len(surface["endpoint_handle"]) == 32
    assert arm_key_violations(frozen["arm_view"]) == []
    assert controller.verify_private_packet(
        frozen["private_packet"],
        expected_kind="E4_HIDDEN_TOPOLOGY",
        expected_episode_binding="episode-e4",
        expected_public_view=frozen["arm_view"],
    )


def test_e4_alternative_appears_only_after_revoke_and_new_discovery():
    controller = HiddenScenarioController()
    broker = OwnerTopologyBroker()
    frozen = controller.freeze_e4(
        episode_binding="episode-e4-query",
        base_arm_view=base_arm_view(broker.public_surface()),
        broker=broker,
        topology=e4_topology(),
    )
    primary = broker.discover("MOBILE_3KW_GENERATOR")
    assert primary["status"] == "FOUND"
    primary_private = broker.resolve_private(primary["owner_handle"])
    assert primary_private["owner_instance_id"] == "O_R:primary"

    revoke = broker.revoke_primary(
        native_event_sha256="e" * 64, logical_minute=12
    )
    assert controller.verify_private_packet(
        revoke,
        expected_kind="E4_PRIMARY_REVOKE",
        expected_episode_binding="episode-e4-query",
        expected_public_view=frozen["arm_view"],
    )
    alternative = broker.discover("MOBILE_3KW_GENERATOR")
    assert alternative["status"] == "FOUND"
    assert alternative["owner_handle"] != primary["owner_handle"]
    alternative_private = broker.resolve_private(alternative["owner_handle"])
    assert alternative_private["owner_instance_id"] == "O_R:alternative"
    assert "alternative" not in json.dumps(alternative, sort_keys=True).lower()
    route_packets = broker.private_route_packets()
    assert len(route_packets) == 2
    assert all(
        controller.verify_private_packet(
            packet,
            expected_kind="E4_BROKER_ROUTE",
            expected_episode_binding="episode-e4-query",
            expected_public_view=frozen["arm_view"],
        )
        for packet in route_packets
    )


def test_distinct_private_topology_keeps_same_public_surface_alpha_shape():
    first = OwnerTopologyBroker()
    second = OwnerTopologyBroker()
    assert alpha_shape(first.public_surface()) == alpha_shape(second.public_surface())
    assert set(first.public_surface()) == set(second.public_surface())
    assert len(first.public_surface()["capabilities"]) == len(
        second.public_surface()["capabilities"]
    )


def test_e6_crash_schedule_is_hidden_and_fires_only_on_exact_trigger():
    controller = HiddenScenarioController()
    schedule = {
        "trigger_event_sha256": "f" * 64,
        "trigger_logical_minute": 46,
        "crash_cut": "AFTER_TARGET_READBACK_BEFORE_ACCEPTANCE",
        "target_epoch": 2,
        "old_runtime_restart_minute": 49,
    }
    frozen = controller.freeze_e6(
        episode_binding="episode-e6",
        base_arm_view=base_arm_view(),
        schedule=schedule,
    )
    arm_bytes = json.dumps(frozen["arm_view"], sort_keys=True)
    for forbidden in (
        "will_migrate",
        "target_epoch",
        "fault_schedule_sha256",
        "AFTER_TARGET_READBACK_BEFORE_ACCEPTANCE",
        "old_runtime_restart_minute",
        "E6-MIGRATION-REPLAY",
    ):
        assert forbidden not in arm_bytes
    assert arm_key_violations(frozen["arm_view"]) == []
    assert (
        controller.maybe_fire_e6(
            frozen,
            episode_binding="episode-e6",
            native_event_sha256="0" * 64,
            logical_minute=46,
        )
        is None
    )
    assert (
        controller.maybe_fire_e6(
            frozen,
            episode_binding="episode-e6",
            native_event_sha256="f" * 64,
            logical_minute=45,
        )
        is None
    )
    fired = controller.maybe_fire_e6(
        frozen,
        episode_binding="episode-e6",
        native_event_sha256="f" * 64,
        logical_minute=46,
    )
    assert fired is not None
    assert controller.verify_private_packet(
        fired,
        expected_kind="E6_TRIGGER_FIRED",
        expected_episode_binding="episode-e6",
        expected_public_view=frozen["arm_view"],
    )
    assert (
        controller.maybe_fire_e6(
            frozen,
            episode_binding="episode-e6",
            native_event_sha256="f" * 64,
            logical_minute=46,
        )
        is None
    )


def test_private_receipt_payload_rewrite_is_detected():
    controller = HiddenScenarioController()
    frozen = controller.freeze_e6(
        episode_binding="episode-rewrite",
        base_arm_view=base_arm_view(),
        schedule={
            "trigger_event_sha256": "1" * 64,
            "trigger_logical_minute": 10,
            "crash_cut": "CUT-A",
            "target_epoch": 2,
            "old_runtime_restart_minute": 12,
        },
    )
    attacked = copy.deepcopy(frozen["private_packet"])
    attacked["private_payload"]["schedule"]["target_epoch"] = 9
    assert not controller.verify_private_packet(
        attacked,
        expected_kind="E6_CRASH_SCHEDULE",
        expected_episode_binding="episode-rewrite",
        expected_public_view=frozen["arm_view"],
    )


def test_private_receipt_transplant_between_episode_is_detected():
    controller = HiddenScenarioController()
    frozen = controller.freeze_e3_pair(
        episode_binding="episode-source",
        base_arm_view=base_arm_view(),
    )
    packet = frozen["forks"][0]["private_packet"]
    assert not controller.verify_private_packet(
        packet,
        expected_kind="E3_PAIRED_FORK",
        expected_episode_binding="episode-destination",
        expected_public_view=frozen["shared_pre_readback_public_view"],
    )


def test_private_receipt_transplant_between_controller_is_detected():
    source = HiddenScenarioController()
    destination = HiddenScenarioController()
    frozen = source.freeze_e3_pair(
        episode_binding="episode-controller-source",
        base_arm_view=base_arm_view(),
    )
    packet = frozen["forks"][0]["private_packet"]
    assert not destination.verify_private_packet(
        packet,
        expected_kind="E3_PAIRED_FORK",
        expected_episode_binding="episode-controller-source",
        expected_public_view=frozen["shared_pre_readback_public_view"],
    )


def test_persisted_packet_has_an_independent_public_key_verifier():
    controller = HiddenScenarioController()
    frozen = controller.freeze_e6(
        episode_binding="episode-independent-verifier",
        base_arm_view=base_arm_view(),
        schedule={
            "trigger_event_sha256": "9" * 64,
            "trigger_logical_minute": 21,
            "crash_cut": "CUT-B",
            "target_epoch": 3,
            "old_runtime_restart_minute": 24,
        },
    )
    assert verify_private_packet(
        frozen["private_packet"],
        expected_controller_instance_id=controller.controller_instance_id,
        expected_controller_public_key_hex=controller.public_key_hex,
        expected_kind="E6_CRASH_SCHEDULE",
        expected_episode_binding="episode-independent-verifier",
        expected_public_view=frozen["arm_view"],
    )


def test_public_view_rewrite_breaks_receipt_binding():
    controller = HiddenScenarioController()
    broker = OwnerTopologyBroker()
    frozen = controller.freeze_e4(
        episode_binding="episode-public-rewrite",
        base_arm_view=base_arm_view(broker.public_surface()),
        broker=broker,
        topology=e4_topology(),
    )
    attacked_view = copy.deepcopy(frozen["arm_view"])
    attacked_view["deadline_minute"] = 120
    assert not controller.verify_private_packet(
        frozen["private_packet"],
        expected_kind="E4_HIDDEN_TOPOLOGY",
        expected_episode_binding="episode-public-rewrite",
        expected_public_view=attacked_view,
    )
