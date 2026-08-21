from __future__ import annotations

import copy
import json
import pathlib
import shutil
import sqlite3
import sys
import uuid

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import independent_evaluator as evaluator  # noqa: E402


def latest_case(name: str) -> pathlib.Path:
    suite = (ARTIFACTS / "latest-suite.txt").read_text().strip()
    return ARTIFACTS / suite / name


def copied_case(tmp_path: pathlib.Path, name: str = "case-001") -> pathlib.Path:
    destination = tmp_path / name
    shutil.copytree(latest_case(name), destination)
    return destination


def load_artifact(case: pathlib.Path) -> dict:
    return json.loads((case / "artifact.json").read_text())


def save_artifact(case: pathlib.Path, artifact: dict) -> None:
    artifact.pop("artifact_sha256", None)
    artifact["artifact_sha256"] = evaluator.sha256_value(artifact)
    (case / "artifact.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    )


def refresh_database(case: pathlib.Path, relative: str) -> None:
    artifact = load_artifact(case)
    path = case / relative
    metadata = artifact["database_artifacts"][relative]
    logical = evaluator.sha256_value(evaluator.sqlite_logical_snapshot(path))
    metadata["formal_physical_sha256"] = evaluator.file_sha256(path)
    metadata["formal_logical_sha256"] = logical
    metadata["source_runtime_logical_sha256"] = logical
    metadata["header_versions"] = evaluator.sqlite_header_versions(path)
    save_artifact(case, artifact)


def rejected(case: pathlib.Path) -> bool:
    return evaluator.audit_run(case / "artifact.json")["accepted"] is False


def test_actual_pair_is_independently_accepted() -> None:
    audit = evaluator.audit_pair(ARTIFACTS / "actual-e6-migration-replay.json")
    assert audit["accepted"] is True
    assert audit["source_prefix_startups_capsule_equivalent"] is True


@pytest.mark.parametrize("name", ["case-001", "case-002"])
def test_migrated_interface_cannot_read_full_source_capsule(name: str) -> None:
    case = latest_case(name)
    artifact = load_artifact(case)
    durable = case / artifact["formal_database_paths"]["durable"]
    connection = sqlite3.connect(durable)
    try:
        assert connection.execute("SELECT COUNT(*) FROM capsules").fetchone()[0] == 0
        probe = json.loads(
            connection.execute("SELECT probe_json FROM runtime_probes").fetchone()[0]
        )
    finally:
        connection.close()
    assert probe["full_source_capsule_rows_visible"] == 0
    assert probe["source_capsule_file_input_present"] is False
    assert probe["controller_private_path_input_present"] is False


def test_exact_task_distinguishes_object_from_operation() -> None:
    task = evaluator.exact_task()
    assert task["object_id"] == "VenueV:CircuitC7"
    assert task["operation_id"] != task["object_id"]


def test_opaque_random_token_containing_e6_is_not_a_false_leak() -> None:
    case = latest_case("case-001")
    artifact = load_artifact(case)
    durable = evaluator.read_durable(
        case / artifact["formal_database_paths"]["durable"]
    )
    startups = copy.deepcopy(durable["startups"])
    startups[0]["visibility"]["cwd"] = (
        "/tmp/opaque-worker-" + "e6" + "a" * 18
    )
    assert evaluator.verify_startups(
        startups,
        frozen=artifact["frozen_input"],
    )["valid"]


@pytest.mark.parametrize("surface", ["argv", "environment", "input_fields"])
def test_semantic_e6_label_in_startup_is_rejected(surface: str) -> None:
    case = latest_case("case-001")
    artifact = load_artifact(case)
    durable = evaluator.read_durable(
        case / artifact["formal_database_paths"]["durable"]
    )
    startups = copy.deepcopy(durable["startups"])
    if surface == "argv":
        startups[0]["visibility"]["argv"] = ["opaque-runtime-worker-e6"]
    elif surface == "environment":
        startups[0]["visibility"]["environment"]["EXPERIMENT"] = "E6"
    else:
        startups[0]["visibility"]["input_fields"].append("e6_case_label")
    assert not evaluator.verify_startups(
        startups,
        frozen=artifact["frozen_input"],
    )["valid"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_id", "VenueV:WrongCircuit"),
        ("other_circuits_energized", ["VenueV:CircuitC8"]),
        ("safety_ok", False),
        ("noise_ok", False),
    ],
)
def test_per_sample_coordinate_attacks_are_rejected(field: str, value: object) -> None:
    state = {
        **evaluator.exact_task(),
        "target_id": evaluator.TARGET_ID,
        "energized": True,
        "power_kw": 3.0,
        "duration_minutes": 45,
        "safety_ok": True,
        "noise_ok": True,
        "power_samples": [
            {
                "offset_minute": offset,
                "observed_at_minute": offset,
                "target_id": evaluator.TARGET_ID,
                "power_kw": 3.0,
                "safety_ok": True,
                "noise_ok": True,
                "other_circuits_energized": [],
            }
            for offset in range(46)
        ],
    }
    state["power_samples"][23][field] = value
    assert evaluator.target_state_is_exact(state) is False


def test_wal_header_attack_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    relative = "formal/target-ledger.sqlite3"
    path = case / relative
    payload = bytearray(path.read_bytes())
    payload[18] = payload[19] = 2
    path.write_bytes(payload)
    refresh_database(case, relative)
    assert rejected(case)


def test_sqlite_companion_attack_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    path = case / "formal/durable.sqlite3-shm"
    path.write_bytes(b"not-a-valid-sidecar")
    assert rejected(case)


def test_full_source_capsule_leak_into_migrated_store_is_rejected(
    tmp_path: pathlib.Path,
) -> None:
    case = copied_case(tmp_path, "case-002")
    artifact = load_artifact(case)
    durable_relative = artifact["formal_database_paths"]["durable"]
    source_cut_relative = artifact["formal_database_paths"]["source_cut"]
    source_connection = sqlite3.connect(case / source_cut_relative)
    try:
        capsule_row = source_connection.execute(
            "SELECT * FROM capsules"
        ).fetchone()
    finally:
        source_connection.close()
    durable_connection = sqlite3.connect(case / durable_relative)
    try:
        durable_connection.execute(
            "INSERT INTO capsules VALUES(?,?,?,?,?,?)",
            capsule_row,
        )
        durable_connection.commit()
    finally:
        durable_connection.close()
    refresh_database(case, durable_relative)
    assert rejected(case)


def test_migrated_execute_attack_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["durable"]
    path = case / relative
    frozen = artifact["frozen_input"]
    authentication = {
        "schema": "RUNTIME_TABLE_BINDING_V1",
        "runtime_id": frozen["migrated_runtime_id"],
        "public_key_hex": frozen["migrated_public_key_hex"],
        "state_identity": "migrated-state.sqlite3",
        "state_reopened": False,
    }
    connection = sqlite3.connect(path)
    connection.execute(
        "INSERT INTO fence_actions VALUES(?,?,?,?,?,?,?,?)",
        (
            f"attack-{uuid.uuid4().hex}",
            frozen["migrated_runtime_handle"],
            2,
            "EXECUTE",
            "ACCEPTED",
            "CURRENT_EPOCH",
            999999,
            json.dumps(authentication, sort_keys=True, separators=(",", ":")),
        ),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_old_epoch_accepted_attack_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["durable"]
    path = case / relative
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE fence_actions SET decision='ACCEPTED', reason='CURRENT_EPOCH' "
        "WHERE action='EXECUTE' AND claimed_epoch=1 AND decision='REJECTED'"
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_duplicate_target_occurrence_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    relative = "formal/target-ledger.sqlite3"
    path = case / relative
    connection = sqlite3.connect(path)
    row = connection.execute("SELECT * FROM commit_events").fetchone()
    connection.execute(
        "INSERT INTO commit_events VALUES(?,?,?,?,?,?,?,?,?,?)",
        (f"duplicate-{uuid.uuid4().hex}", *row[1:]),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_capsule_rewrite_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    path = case / artifact["capsule_file"]
    capsule = json.loads(path.read_text())
    capsule["source_epoch"] = 99
    path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n")
    artifact["capsule_file_sha256"] = evaluator.file_sha256(path)
    save_artifact(case, artifact)
    assert rejected(case)


def test_history_rewrite_and_precrash_acceptance_are_rejected(
    tmp_path: pathlib.Path,
) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["durable"]
    path = case / relative
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT event_json FROM history WHERE sequence=2"
    ).fetchone()
    event = json.loads(row[0])
    event["event_type"] = "O_Q_POST_MIGRATION_ACCEPTANCE"
    connection.execute(
        "UPDATE history SET event_json=? WHERE sequence=2",
        (json.dumps(event, sort_keys=True, separators=(",", ":")),),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_owner_head_stale_attack_is_rejected(tmp_path: pathlib.Path) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["owners"]["O_Q"]
    path = case / relative
    connection = sqlite3.connect(path)
    connection.execute(
        "UPDATE owner_state SET head_hash=?",
        ("f" * 64,),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_fence_memory_only_reopen_attack_is_rejected(
    tmp_path: pathlib.Path,
) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["durable"]
    path = case / relative
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT rowid, authentication_json FROM fence_actions "
        "WHERE decision='REJECTED' AND reason='STALE_EPOCH'"
    ).fetchone()
    authentication = json.loads(row[1])
    authentication["state_reopened"] = False
    connection.execute(
        "UPDATE fence_actions SET authentication_json=? WHERE rowid=?",
        (json.dumps(authentication, sort_keys=True), row[0]),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_cut_snapshot_claiming_precrash_acceptance_is_rejected(
    tmp_path: pathlib.Path,
) -> None:
    case = copied_case(tmp_path)
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["durable"]
    path = case / relative
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT sequence, payload_json FROM controller_events "
        "WHERE event_type='CUT_OWNER_NATIVE_SNAPSHOT_BOUND'"
    ).fetchone()
    payload = json.loads(row[1])
    payload["owners"]["O_Q"]["acceptance_count"] = 1
    connection.execute(
        "UPDATE controller_events SET payload_json=? WHERE sequence=?",
        (json.dumps(payload, sort_keys=True), row[0]),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_no_target_ledger_cannot_be_upgraded_to_success(
    tmp_path: pathlib.Path,
) -> None:
    case = copied_case(tmp_path, "case-002")
    artifact = load_artifact(case)
    relative = artifact["formal_database_paths"]["durable"]
    path = case / relative
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT runtime_handle, outcome_json FROM migration_outcomes"
    ).fetchone()
    outcome = json.loads(row[1])
    outcome.update(
        disposition="POSTCONDITIONS_READY",
        postconditions_ready=True,
    )
    connection.execute(
        "UPDATE migration_outcomes SET disposition=?, outcome_json=? "
        "WHERE runtime_handle=?",
        (
            outcome["disposition"],
            json.dumps(outcome, sort_keys=True, separators=(",", ":")),
            row[0],
        ),
    )
    connection.commit()
    connection.close()
    refresh_database(case, relative)
    assert rejected(case)


def test_capsule_view_transplant_between_arms_is_rejected(
    tmp_path: pathlib.Path,
) -> None:
    removal = copied_case(tmp_path, "case-002")
    baseline_view = latest_case("case-001") / "migration-input-view.json"
    artifact = load_artifact(removal)
    target = removal / artifact["migration_view_file"]
    shutil.copy2(baseline_view, target)
    view = json.loads(target.read_text())
    artifact["migration_view_file_sha256"] = evaluator.file_sha256(target)
    artifact["migration_view_hash"] = view["view_hash"]
    save_artifact(removal, artifact)
    assert rejected(removal)
