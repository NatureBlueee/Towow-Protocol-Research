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
    evaluate_run,
    validate_capability_freshness,
    validate_sequence,
    validate_status_envelope,
    verify_target_signature,
)


ACCEPTED_RUN = (
    ROOT
    / "artifacts"
    / "run-5e3bb50c02a545ed8594c982b5f54c90"
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def public_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def resign(record, private_key: Ed25519PrivateKey):
    candidate = copy.deepcopy(record)
    candidate["target_public_key_hex"] = public_hex(private_key)
    body = {key: value for key, value in candidate.items() if key != "signature_hex"}
    candidate["signature_hex"] = private_key.sign(canonical_bytes(body)).hex()
    return candidate


def copied_run(tmp_path: Path) -> Path:
    target = tmp_path / "attacked-run"
    shutil.copytree(ACCEPTED_RUN, target)
    return target


def test_independent_evaluator_accepts_frozen_root_fix_artifact():
    result = evaluate_run(ACCEPTED_RUN)
    assert result["status"] == "ACCEPTED_SCOPED_LOCAL_DIGITAL_E3_PAIR"
    assert (
        result["artifact_freeze_sha256"]
        == "3059bdc91c09bd1e71a5f6827453bbc157290f45967bdffa7f589e6e856b2abe"
    )
    assert result["worlds"]["world-a"]["target_mutation_count"] == 1
    assert result["worlds"]["world-b"]["target_mutation_count"] == 1


def test_attack_incomplete_current_head_coverage_is_rejected_even_if_resigned():
    view = load(ACCEPTED_RUN / "shared-startup-view.json")
    arm = load(ACCEPTED_RUN / "world-b" / "arm-result.json")
    query = arm["transcript"][2]["message"]
    negative = arm["transcript"][3]["message"]["status_envelope"]
    attacker_target = Ed25519PrivateKey.generate()
    tampered = copy.deepcopy(negative)
    tampered["covered_ledger_range"]["through_version"] = -1
    tampered = resign(tampered, attacker_target)

    with pytest.raises(
        AcceptanceError,
        match="coverage is not complete",
    ):
        validate_status_envelope(
            tampered,
            query,
            view,
            public_hex(attacker_target),
        )


def test_attack_consumed_capability_claiming_current_is_rejected_even_if_resigned():
    view = load(ACCEPTED_RUN / "shared-startup-view.json")
    arm = load(ACCEPTED_RUN / "world-b" / "arm-result.json")
    negative = arm["transcript"][3]["message"]["status_envelope"]
    freshness = arm["transcript"][5]["message"]["capability_freshness"]
    attacker_target = Ed25519PrivateKey.generate()
    tampered = copy.deepcopy(freshness)
    tampered["capability_consumed_by_request_id"] = "already-consumed"
    tampered = resign(tampered, attacker_target)

    with pytest.raises(AcceptanceError, match="consumed capability"):
        validate_capability_freshness(
            tampered,
            view,
            public_hex(attacker_target),
            negative["current_head"],
            freshness["capability_allowed_state_sha256"],
        )


def test_attack_missing_real_historical_decoy_commit_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    db_path = (
        attacked
        / "ROOT-FROZEN-SQLITE"
        / "world-b"
        / "historical-decoy-ledger.sqlite3"
    )
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("DELETE FROM commit_events")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(AcceptanceError, match="mutation count"):
        evaluate_run(attacked)


def test_attack_target_endpoint_key_replacement_is_rejected():
    arm = load(ACCEPTED_RUN / "world-b" / "arm-result.json")
    broker = load(ACCEPTED_RUN / "world-b" / "broker-private-result.json")
    negative = arm["transcript"][3]["message"]["status_envelope"]
    attacker_target = Ed25519PrivateKey.generate()
    replaced = resign(negative, attacker_target)

    with pytest.raises(AcceptanceError, match="key replacement"):
        verify_target_signature(replaced, broker["target_public_key_hex"])


def test_attack_retry_before_freshness_is_rejected():
    arm = load(ACCEPTED_RUN / "world-b" / "arm-result.json")
    transcript = copy.deepcopy(arm["transcript"])
    transcript[4:8] = transcript[6:8] + transcript[4:6]

    with pytest.raises(AcceptanceError, match="retry may precede freshness"):
        validate_sequence("world-b", transcript)


def test_attack_more_than_one_target_mutation_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    db_path = (
        attacked
        / "ROOT-FROZEN-SQLITE"
        / "world-a"
        / "target-ledger.sqlite3"
    )
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        event = dict(connection.execute("SELECT * FROM commit_events").fetchone())
        event["commit_id"] = "attack-extra-commit"
        columns = list(event)
        connection.execute(
            "INSERT INTO commit_events(%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [event[column] for column in columns],
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(AcceptanceError, match="mutation count"):
        evaluate_run(attacked)


def test_attack_pre_readback_prefix_difference_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    arm_path = attacked / "world-b" / "arm-result.json"
    arm = load(arm_path)
    arm["transcript"][0]["message"]["object_id"] = "VenueV:CircuitC8"
    arm_path.write_text(
        json.dumps(arm, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(AcceptanceError, match="pre-readback paired prefix differs"):
        evaluate_run(attacked)


def test_attack_frozen_database_in_wal_mode_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    db_path = (
        attacked
        / "ROOT-FROZEN-SQLITE"
        / "world-a"
        / "target-ledger.sqlite3"
    )
    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.execute("CREATE TABLE attack_wal_dependency(value TEXT)")
        connection.execute("INSERT INTO attack_wal_dependency VALUES ('x')")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        AcceptanceError,
        match="not DELETE-journal|unbound WAL/SHM",
    ):
        evaluate_run(attacked)
