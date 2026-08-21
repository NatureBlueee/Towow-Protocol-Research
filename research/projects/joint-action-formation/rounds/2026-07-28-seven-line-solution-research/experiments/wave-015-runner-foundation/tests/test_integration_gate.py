from __future__ import annotations

import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hidden_world import HiddenScenarioController, OwnerTopologyBroker
from visibility import (
    PUBLIC_INPUT_SCHEMA,
    ArmViewFactory,
    BlindProcessLauncher,
    canonical_bytes,
)


def public_input():
    return {
        "schema": PUBLIC_INPUT_SCHEMA,
        "task": {
            "q_version": "Q@v1",
            "object_id": "VenueV:CircuitC7",
            "target_id": "VenueV:CircuitC7",
            "deadline_minute": 90,
            "required_duration_minutes": 45,
            "required_power_kw": 3.0,
            "power_tolerance_percent": 5,
        },
    }


def topology():
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


def test_hidden_e4_view_is_the_same_view_launched_by_real_spawn():
    private_topology = topology()
    private_materials = (
        private_topology,
        "E4-REVOKE-WITH-ALTERNATIVE",
        "principal-alternative",
    )
    broker = OwnerTopologyBroker()
    view = ArmViewFactory(
        arm_id="A4-DETERMINISTIC-MATURE-COMPOSITION"
    ).build(
        public_input(),
        broker_surface=broker.public_surface(),
        private_materials=private_materials,
    )
    frozen = HiddenScenarioController().freeze_e4(
        episode_binding="episode-integration-e4",
        base_arm_view=view,
        broker=broker,
        topology=private_topology,
    )

    assert frozen["arm_view"] == view
    receipt = BlindProcessLauncher().launch(
        frozen["arm_view"],
        private_materials=private_materials,
    )
    child_view = receipt.visible_surface["view"]
    assert child_view == view
    assert child_view["broker_surface"] == broker.public_surface()
    child_bytes = canonical_bytes(receipt.visible_surface)
    assert b"E4-REVOKE-WITH-ALTERNATIVE" not in child_bytes
    assert b"principal-alternative" not in child_bytes
    assert b"O_R:alternative" not in child_bytes


def test_hidden_controller_rejects_view_bound_to_another_broker():
    source_broker = OwnerTopologyBroker()
    destination_broker = OwnerTopologyBroker()
    view = ArmViewFactory(
        arm_id="A4-DETERMINISTIC-MATURE-COMPOSITION"
    ).build(public_input(), broker_surface=source_broker.public_surface())

    with pytest.raises(ValueError, match="not bound to this Broker"):
        HiddenScenarioController().freeze_e4(
            episode_binding="episode-broker-transplant",
            base_arm_view=view,
            broker=destination_broker,
            topology=topology(),
        )


def test_e3_startup_view_remains_launcher_compatible_and_prefix_is_separate():
    view = ArmViewFactory(
        arm_id="A4-DETERMINISTIC-MATURE-COMPOSITION"
    ).build(public_input())
    frozen = HiddenScenarioController().freeze_e3_pair(
        episode_binding="episode-integration-e3",
        base_arm_view=view,
    )
    first, second = frozen["forks"]

    assert first["arm_view"] == second["arm_view"] == view
    assert first["public_prefix"] == second["public_prefix"]
    assert "public_prefix" not in first["arm_view"]
    receipt = BlindProcessLauncher().launch(first["arm_view"])
    assert receipt.visible_surface["view"] == view
    assert json.loads(receipt.visible_surface["view_bytes"]) == view
