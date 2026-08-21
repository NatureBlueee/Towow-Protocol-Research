"""Produce one persistent Wave 015 runner-foundation evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from e6_runtime_probe import run_e6_runtime_probe
from hidden_world import HiddenScenarioController, OwnerTopologyBroker
from target_ledger import (
    ALREADY_SATISFIED,
    COMMITTED,
    CONFLICT,
    TargetOperationLedger,
)
from visibility import (
    PUBLIC_INPUT_SCHEMA,
    ArmViewFactory,
    BlindProcessLauncher,
    canonical_bytes,
    sha256_value,
)


ROOT = pathlib.Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
ARM_ID = "A4-DETERMINISTIC-MATURE-COMPOSITION"
TARGET = "VenueV:CircuitC7"
OFF = {"energized": False, "power_kw": 0.0}
ON = {"energized": True, "power_kw": 3.0}


def public_input() -> dict[str, Any]:
    return {
        "schema": PUBLIC_INPUT_SCHEMA,
        "task": {
            "q_version": "Q@v1",
            "object_id": TARGET,
            "target_id": TARGET,
            "deadline_minute": 90,
            "required_duration_minutes": 45,
            "required_power_kw": 3.0,
            "power_tolerance_percent": 5,
        },
    }


def e4_topology() -> list[dict[str, Any]]:
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


def _apply(
    ledger: TargetOperationLedger,
    *,
    target_id: str,
    actor_id: str,
    request_id: str,
    capability_id: str,
    expected_version: int,
    desired_state: Any,
) -> dict[str, Any]:
    return ledger.apply(
        target_id=target_id,
        actor_id=actor_id,
        request_id=request_id,
        capability_id=capability_id,
        expected_version=expected_version,
        desired_state=desired_state,
    )


def _checkpoint_database(path: pathlib.Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def run_foundation(artifacts_dir: pathlib.Path = ARTIFACTS) -> pathlib.Path:
    run_id = f"foundation-{secrets.token_hex(10)}"
    output_dir = artifacts_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    database_path = output_dir / "target-ledger.sqlite3"

    controller = HiddenScenarioController()
    factory = ArmViewFactory(arm_id=ARM_ID)
    topology = e4_topology()
    private_materials = (
        topology,
        "E3A-ACK-LOST-EFFECT",
        "E3B-ACK-LOST-NO-EFFECT",
        "E4-REVOKE-WITH-ALTERNATIVE",
        "E6-MIGRATION-REPLAY",
    )

    broker = OwnerTopologyBroker()
    e4_view = factory.build(
        public_input(),
        broker_surface=broker.public_surface(),
        private_materials=private_materials,
    )
    frozen_e4 = controller.freeze_e4(
        episode_binding=f"{run_id}-e4",
        base_arm_view=e4_view,
        broker=broker,
        topology=topology,
    )
    launch = BlindProcessLauncher().launch(
        frozen_e4["arm_view"],
        private_materials=private_materials,
    )
    primary = broker.discover("MOBILE_3KW_GENERATOR")
    revoke = broker.revoke_primary(
        native_event_sha256="e" * 64,
        logical_minute=12,
    )
    alternative = broker.discover("MOBILE_3KW_GENERATOR")

    e3_view = factory.build(public_input(), private_materials=private_materials)
    frozen_e3 = controller.freeze_e3_pair(
        episode_binding=f"{run_id}-e3",
        base_arm_view=e3_view,
    )

    e6_view = factory.build(public_input(), private_materials=private_materials)
    frozen_e6 = controller.freeze_e6(
        episode_binding=f"{run_id}-e6",
        base_arm_view=e6_view,
        schedule={
            "trigger_event_sha256": "f" * 64,
            "trigger_logical_minute": 46,
            "crash_cut": "AFTER_TARGET_READBACK_BEFORE_ACCEPTANCE",
            "target_epoch": 2,
            "old_runtime_restart_minute": 49,
        },
    )
    fired_e6 = controller.maybe_fire_e6(
        frozen_e6,
        episode_binding=f"{run_id}-e6",
        native_event_sha256="f" * 64,
        logical_minute=46,
    )
    if fired_e6 is None:
        raise RuntimeError("frozen E6 trigger did not fire")

    ledger = TargetOperationLedger(
        database_path,
        ledger_id=f"{run_id}-target-truth-owner",
    )
    ledger.initialize_target(TARGET, OFF)
    ledger.issue_capability(
        capability_id="cap-h",
        target_id=TARGET,
        actor_id="H",
        allowed_state=ON,
    )
    ledger.issue_capability(
        capability_id="cap-a4",
        target_id=TARGET,
        actor_id="A4",
        allowed_state=ON,
    )
    h_first = _apply(
        ledger,
        target_id=TARGET,
        actor_id="H",
        request_id="request-h",
        capability_id="cap-h",
        expected_version=0,
        desired_state=ON,
    )
    a4_after_h = _apply(
        ledger,
        target_id=TARGET,
        actor_id="A4",
        request_id="request-a4",
        capability_id="cap-a4",
        expected_version=0,
        desired_state=ON,
    )
    a4_readback = ledger.readback(a4_after_h)

    concurrent_target = "VenueV:CircuitC7:concurrency-probe"
    reserve_state = {"energized": True, "power_kw": 2.9}
    ledger.initialize_target(concurrent_target, OFF)
    ledger.issue_capability(
        capability_id="cap-concurrent-a",
        target_id=concurrent_target,
        actor_id="actor-a",
        allowed_state=ON,
    )
    ledger.issue_capability(
        capability_id="cap-concurrent-b",
        target_id=concurrent_target,
        actor_id="actor-b",
        allowed_state=reserve_state,
    )
    barrier = threading.Barrier(2)

    def competing_apply(
        actor_id: str,
        request_id: str,
        capability_id: str,
        desired_state: Any,
    ) -> dict[str, Any]:
        barrier.wait(timeout=5)
        return _apply(
            ledger,
            target_id=concurrent_target,
            actor_id=actor_id,
            request_id=request_id,
            capability_id=capability_id,
            expected_version=0,
            desired_state=desired_state,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(
            competing_apply,
            "actor-a",
            "request-concurrent-a",
            "cap-concurrent-a",
            ON,
        )
        future_b = executor.submit(
            competing_apply,
            "actor-b",
            "request-concurrent-b",
            "cap-concurrent-b",
            reserve_state,
        )
        concurrent_receipts = [
            future_a.result(timeout=10),
            future_b.result(timeout=10),
        ]

    if h_first["decision"] != COMMITTED:
        raise RuntimeError("H-first mutation did not commit")
    if (
        a4_after_h["decision"] != ALREADY_SATISFIED
        or a4_after_h["mutation_applied"] is not False
        or a4_after_h["commit_actor_id"] != "H"
    ):
        raise RuntimeError("H-first attribution was not preserved")
    if not ledger.verify_readback(a4_readback, a4_after_h):
        raise RuntimeError("A4 after H readback failed verification")
    if sorted(item["decision"] for item in concurrent_receipts) != sorted(
        [COMMITTED, CONFLICT]
    ):
        raise RuntimeError("concurrent CAS probe did not yield one commit/one conflict")
    if frozen_e3["raw_prefix_equal"] is not True:
        raise RuntimeError("E3 paired pre-readback public views diverged")
    if launch.visible_surface["view"] != frozen_e4["arm_view"]:
        raise RuntimeError("launched arm view differs from frozen E4 view")
    visible_bytes = canonical_bytes(launch.visible_surface)
    for label in (
        b"E3A-ACK-LOST-EFFECT",
        b"E3B-ACK-LOST-NO-EFFECT",
        b"E4-REVOKE-WITH-ALTERNATIVE",
        b"E6-MIGRATION-REPLAY",
        b"principal-alternative",
    ):
        if label in visible_bytes:
            raise RuntimeError("private semantic material leaked to spawned arm")

    e6_runtime_probe = run_e6_runtime_probe()
    if (
        e6_runtime_probe["same_arm_view_schema"] is not True
        or e6_runtime_probe["same_arm_view_hash"] is not True
    ):
        raise RuntimeError("E6 runtime probe did not preserve one arm view")
    if (
        e6_runtime_probe["migrated_action_evaluation"]["decision"] != "ACCEPTED"
        or e6_runtime_probe["old_runtime_action_evaluation"]["decision"]
        != "REJECTED_STALE_EPOCH"
    ):
        raise RuntimeError("E6 runtime probe fence decisions diverged")

    _checkpoint_database(database_path)
    database_sha256 = hashlib.sha256(database_path.read_bytes()).hexdigest()
    bundle = {
        "schema": "WAVE015_RUNNER_FOUNDATION_BUNDLE_V1",
        "run_id": run_id,
        "controller_identity": {
            "controller_instance_id": controller.controller_instance_id,
            "controller_public_key_hex": controller.public_key_hex,
        },
        "visibility": {
            "e4_arm_view": frozen_e4["arm_view"],
            "launch_receipt": launch.as_dict(),
        },
        "hidden_scenarios": {
            "e3": frozen_e3,
            "e4": {
                "frozen": frozen_e4,
                "primary_discovery": primary,
                "revoke_private_packet": revoke,
                "alternative_discovery": alternative,
                "route_private_packets": broker.private_route_packets(),
            },
            "e6": {
                "frozen": frozen_e6,
                "fired_private_packet": fired_e6,
            },
        },
        "target_ledger": {
            "ledger_id": ledger.ledger_id,
            "database_file": database_path.name,
            "database_sha256": database_sha256,
            "h_first_receipt": h_first,
            "a4_after_h_receipt": a4_after_h,
            "a4_after_h_readback": a4_readback,
            "target_state": ledger.current_state(TARGET),
            "concurrent_receipts": concurrent_receipts,
            "concurrent_target_state": ledger.current_state(concurrent_target),
        },
        "e6_runtime_probe": e6_runtime_probe,
        "claim_boundary": (
            "RUNNER_FOUNDATION_ONLY; E3_E4_E6_TASKS_NOT_RUN; "
            "DIGITAL_TARGET_DIRECT_COMMIT_ATTRIBUTION_ONLY; "
            "E6_ACTUAL_LOCAL_RUNTIME_PROBE_NOT_FULL_E6"
        ),
    }
    bundle["bundle_sha256"] = sha256_value(bundle)
    output_path = output_dir / "foundation-bundle.json"
    output_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", type=pathlib.Path, default=ARTIFACTS)
    args = parser.parse_args()
    path = run_foundation(args.artifacts_dir)
    print(json.dumps({"artifact": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
