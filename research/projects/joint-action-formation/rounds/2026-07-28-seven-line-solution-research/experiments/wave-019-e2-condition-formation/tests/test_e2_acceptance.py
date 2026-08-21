from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator import (  # noqa: E402
    AcceptanceError,
    canonical_bytes,
    evaluate_suite,
    validate_case_sequence,
    validate_occurrence_coordinates,
    validate_owner_response,
    verify_owner_record,
)


SUITE = ROOT / "artifacts" / "suite-5909e01158ad4e6f9f765f2aa45909fc"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def resign(record, key: Ed25519PrivateKey):
    candidate = copy.deepcopy(record)
    candidate["owner_public_key_hex"] = public_hex(key)
    body = {name: value for name, value in candidate.items() if name != "signature_hex"}
    candidate["signature_hex"] = key.sign(canonical_bytes(body)).hex()
    return candidate


def copied_suite(tmp_path: Path) -> Path:
    target = tmp_path / "attacked-suite"
    shutil.copytree(SUITE, target)
    return target


def baseline_material():
    arm = load(SUITE / "baseline" / "arm-result.json")
    ready = load(SUITE / "baseline" / "owner-ready.json")
    proposal = arm["proposal"]
    response = next(
        item for item in arm["owner_responses"] if item["owner_role"] == "O_Q"
    )
    return arm, ready, proposal, response


def test_independent_acceptance_of_frozen_suite():
    result = evaluate_suite(SUITE)
    assert (
        result["status"]
        == "ACCEPTED_LOCAL_SYNTHETIC_E2_MATURE_WORKFLOW_HITL_SCOPED"
    )
    assert (
        result["artifact_freeze_sha256"]
        == "49154f083738a2c244424e8bcacb74a0fb46b23a9f310358407e4c49e3823684"
    )
    assert result["cases"]["baseline"]["target_mutation_count"] == 1
    assert result["cases"]["remove"]["target_mutation_count"] == 0
    assert result["cases"]["refuse"]["target_mutation_count"] == 0


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("owner_head", "stale-head", "stale owner response"),
        ("owner_id", "wrong-owner", "wrong-owner response"),
        ("scope_sha256", "wrong-scope", "wrong-scope owner response"),
    ],
)
def test_attacks_stale_wrong_owner_and_wrong_scope_responses_are_rejected(
    field,
    replacement,
    message,
):
    _, ready, proposal, response = baseline_material()
    key = Ed25519PrivateKey.generate()
    synthetic_ready = copy.deepcopy(ready["O_Q"])
    synthetic_ready["public_key_hex"] = public_hex(key)
    tampered = copy.deepcopy(response)
    tampered[field] = replacement
    tampered = resign(tampered, key)

    with pytest.raises(AcceptanceError, match=message):
        validate_owner_response(
            tampered,
            synthetic_ready,
            proposal,
            response["owner_head"],
        )


def test_attack_execute_before_formation_is_rejected():
    arm = load(SUITE / "baseline" / "arm-result.json")
    transcript = copy.deepcopy(arm["transcript"])
    transcript[2:6] = transcript[4:6] + transcript[2:4]
    with pytest.raises(AcceptanceError, match="formation-before-execute"):
        validate_case_sequence("baseline", transcript)


def test_attack_controller_forged_owner_act_is_rejected():
    arm = load(SUITE / "baseline" / "arm-result.json")
    ready = load(SUITE / "baseline" / "owner-ready.json")
    act = next(item for item in arm["owner_acts"] if item["owner_role"] == "O_V")
    controller_key = Ed25519PrivateKey.generate()
    forged = resign(act, controller_key)
    with pytest.raises(AcceptanceError, match="controller-forged"):
        verify_owner_record(forged, ready["O_V"]["public_key_hex"])


def test_attack_remove_run_still_forms_owner_fact_is_rejected(tmp_path):
    attacked = copied_suite(tmp_path)
    db_path = (
        attacked
        / "ROOT-FROZEN-SQLITE"
        / "remove"
        / "owners"
        / "o_q.sqlite3"
    )
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "INSERT INTO facts VALUES(?,?,?,?,?)",
            ("PURPOSE_TOKEN", "scope", "proposal", 90, "{}"),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(AcceptanceError, match="audit differs|formed owner"):
        evaluate_suite(attacked)


@pytest.mark.parametrize(
    "wrong_disposition",
    ["BOUNDED_UNKNOWN_OWNER_DEFER", "SUCCEEDED_AFTER_FORMATION"],
)
def test_attack_signed_refusal_miswritten_unknown_or_success_is_rejected(
    tmp_path,
    wrong_disposition,
):
    attacked = copied_suite(tmp_path)
    path = attacked / "refuse" / "arm-result.json"
    arm = load(path)
    arm["disposition"] = wrong_disposition
    path.write_text(
        json.dumps(arm, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    launch_path = attacked / "refuse" / "arm-launch.json"
    launch = load(launch_path)
    launch["worker_result"] = arm
    launch_path.write_text(
        json.dumps(launch, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(AcceptanceError, match="misclassified"):
        evaluate_suite(attacked)


def test_attack_duplicate_target_mutation_is_rejected(tmp_path):
    attacked = copied_suite(tmp_path)
    db_path = (
        attacked
        / "ROOT-FROZEN-SQLITE"
        / "baseline"
        / "target-ledger.sqlite3"
    )
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        event = dict(connection.execute("SELECT * FROM commit_events").fetchone())
        event["commit_id"] = "attack-duplicate-commit"
        columns = list(event)
        connection.execute(
            "INSERT INTO commit_events(%s) VALUES(%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [event[column] for column in columns],
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(AcceptanceError, match="duplicate or missing"):
        evaluate_suite(attacked)


def test_attack_frozen_db_with_wal_dependency_is_rejected(tmp_path):
    attacked = copied_suite(tmp_path)
    db_path = (
        attacked
        / "ROOT-FROZEN-SQLITE"
        / "remove"
        / "owners"
        / "o_s.sqlite3"
    )
    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.execute("CREATE TABLE wal_attack(value TEXT)")
        connection.execute("INSERT INTO wal_attack VALUES('x')")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(AcceptanceError, match="WAL/SHM|DELETE journal"):
        evaluate_suite(attacked)


@pytest.mark.parametrize(
    ("attack", "message"),
    [
        ("unsafe", "unsafe/noisy"),
        ("noisy", "unsafe/noisy"),
        ("other_circuit", "other circuit"),
        ("duration_gap", "duration gap"),
        ("wrong_sample_target", "sample wrong target"),
        ("sample_other_circuit", "sample other circuit"),
    ],
)
def test_attacks_ce001_effect_coordinates_are_rejected(attack, message):
    arm = load(SUITE / "baseline" / "arm-result.json")
    occurrence = copy.deepcopy(
        arm["readback"]["observed_state"]["occurrences"][0]
    )
    if attack == "unsafe":
        occurrence["samples"][7]["safety_ok"] = False
    elif attack == "noisy":
        occurrence["samples"][9]["noise_ok"] = False
    elif attack == "other_circuit":
        occurrence["other_circuits_energized"] = ["VenueV:CircuitC8"]
    elif attack == "duration_gap":
        occurrence["duration_minutes"] = 44
    elif attack == "wrong_sample_target":
        occurrence["samples"][11]["target_id"] = "VenueV:CircuitC8"
    elif attack == "sample_other_circuit":
        occurrence["samples"][13]["other_circuits_energized"] = [
            "VenueV:CircuitC8"
        ]
    with pytest.raises(AcceptanceError, match=message):
        validate_occurrence_coordinates(occurrence)
