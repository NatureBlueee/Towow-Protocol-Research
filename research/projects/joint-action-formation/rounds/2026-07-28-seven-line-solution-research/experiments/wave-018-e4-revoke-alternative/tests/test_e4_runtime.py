from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import shutil
import sqlite3
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run import _public_startup, alpha_shape, run_case
from evaluator import evaluate_bundle
from runtime import OWNER_IDS, canonical_bytes, validate_public_startup, verify_signed


@pytest.fixture(scope="module")
def paired_worlds():
    return {
        "main": run_case(alternative_enabled=True),
        "removed": run_case(alternative_enabled=False),
    }


def test_actual_spawn_and_independent_primary_alternative(paired_worlds):
    for bundle in paired_worlds.values():
        services = bundle["service_manifest"]
        assert set(services) == {
            *OWNER_IDS,
            "BROKER",
            "TARGET",
            "ARM",
        }
        assert len({item["process_id"] for item in services.values()}) == 9
        assert len({item["public_key_hex"] for item in services.values()}) == 9
        assert all(item["start_method"] == "spawn" for item in services.values())
        assert all(
            verify_signed(item, item["public_key_hex"])
            for item in services.values()
        )
        assert set(bundle["runtime"]["process_exit_codes"].values()) == {0}
        primary = services["RESOURCE_PRIMARY"]
        alternative = services["RESOURCE_ALTERNATIVE"]
        assert primary["process_id"] != alternative["process_id"]
        assert primary["public_key_hex"] != alternative["public_key_hex"]
        assert primary["principal_id"] != alternative["principal_id"]
        assert primary["state_source_id"] != alternative["state_source_id"]


def test_startup_and_pre_rediscovery_have_no_alternative_answer(paired_worlds):
    for bundle in paired_worlds.values():
        startup = canonical_bytes(bundle["arm_startup"]).decode().lower()
        alternative = bundle["service_manifest"]["RESOURCE_ALTERNATIVE"]
        alt_handle = bundle["broker_native_log"]["private_handle_map"][
            "RESOURCE_ALTERNATIVE"
        ]
        for forbidden in (
            "e4-revoke",
            "e4_remove",
            "remove_alternative",
            "alternative",
            "primary",
            alternative["principal_id"].lower(),
            alternative["public_key_hex"].lower(),
            alt_handle,
        ):
            assert forbidden not in startup
        transcript = bundle["arm_result"]["transcript"]
        discover_indexes = [
            index
            for index, event in enumerate(transcript)
            if event.get("kind") == "BROKER_INTERACTION"
            and event.get("action") == "DISCOVER"
        ]
        assert len(discover_indexes) == 2
        prefix = canonical_bytes(transcript[: discover_indexes[1]]).decode()
        assert alt_handle not in prefix
        assert alternative["principal_id"] not in prefix
        assert alternative["public_key_hex"] not in prefix
    assert alpha_shape(
        paired_worlds["main"]["arm_startup"]
    ) == alpha_shape(paired_worlds["removed"]["arm_startup"])


def test_main_world_recovers_via_actual_legal_alternative(paired_worlds):
    bundle = paired_worlds["main"]
    evaluation = bundle["evaluation"]
    assert evaluation["evidence_valid"] is True
    assert evaluation["ExactTaskSuccess"] is True
    assert evaluation["disposition"] == "RECOVERED_VIA_LEGAL_ALTERNATIVE"
    assert evaluation["PrimaryRevokedBeforeCommit"] is True
    assert evaluation["BoundedLocalReopen"] is True
    assert evaluation["AlternativeActuallyRediscovered"] is True
    assert evaluation["AlternativeCurrentChain"] is True
    assert evaluation["FreshOwnerStatusAtCommit"] is True
    assert evaluation["DurableSQLiteTargetLedger"] is True
    assert evaluation["StandaloneDeleteJournalTarget"] is True
    assert evaluation["PhysicalLogicalDatabaseHashBound"] is True
    assert evaluation["ExactCE001CoordinatesVerified"] is True
    assert evaluation["UniqueExactOccurrence"] is True
    assert evaluation["DualAcceptance"] is True
    assert evaluation["AlternativeBoundFinality"] is True
    assert len(bundle["owner_native_logs"]["RESOURCE_PRIMARY"]["entries"]) == 6
    assert (
        bundle["owner_native_logs"]["RESOURCE_PRIMARY"]["entries"][-2]["kind"]
        == "OWNER_NATIVE_REVOKE"
    )
    assert len(
        bundle["owner_native_logs"]["RESOURCE_ALTERNATIVE"]["entries"]
    ) == 5
    assert len(bundle["target_native_log"]["occurrences"]) == 1
    assert len(bundle["target_native_log"]["readbacks"]) == 1
    occurrence = bundle["target_native_log"]["occurrences"][0]
    assert occurrence["object_id"] == "VenueV:CircuitC7"
    assert (
        occurrence["authority_owner_instance_id"] == "RESOURCE_ALTERNATIVE"
    )
    exact_state = bundle["target_native_log"]["exact_state"]
    assert exact_state["effect_start_minute"] == 10
    assert exact_state["effect_end_minute"] == 55
    assert exact_state["required_duration_minutes"] == 45
    assert exact_state["deadline_minute"] == 90
    assert len(exact_state["samples"]) == 46
    assert [item["offset_minute"] for item in exact_state["samples"]] == list(
        range(46)
    )
    assert all(
        2.85 <= item["power_kw"] <= 3.15
        and item["safety_ok"] is True
        and item["noise_ok"] is True
        and item["other_circuits_energized"] == []
        for item in exact_state["samples"]
    )
    assert len(bundle["target_native_log"]["fresh_status_queries"]) == 5
    assert len(bundle["target_native_log"]["ledger_receipts"]) == 1
    assert len(bundle["target_native_log"]["ledger_readbacks"]) == 1


def test_target_duplicate_probe_does_not_create_second_mutation(paired_worlds):
    bundle = paired_worlds["main"]
    duplicate = bundle["arm_result"]["duplicate_response"]
    assert duplicate["status"] == "ALREADY_COMMITTED"
    assert len(bundle["target_native_log"]["occurrences"]) == 1
    assert sum(
        item["kind"] == "ALREADY_COMMITTED"
        for item in bundle["target_native_log"]["entries"]
    ) == 1


def test_remove_alternative_counterfactual_cannot_use_dormant_process(
    paired_worlds,
):
    bundle = paired_worlds["removed"]
    evaluation = bundle["evaluation"]
    assert evaluation["evidence_valid"] is True
    assert evaluation["ExactTaskSuccess"] is False
    assert evaluation["AlternativeRemoved"] is True
    assert evaluation["StandaloneDeleteJournalTarget"] is True
    assert evaluation["PhysicalLogicalDatabaseHashBound"] is True
    assert evaluation["disposition"] == "BOUNDED_REFUSAL_NO_ALTERNATIVE"
    assert bundle["arm_result"]["rediscovery"]["status"] == "NOT_FOUND"
    assert bundle["owner_native_logs"]["RESOURCE_ALTERNATIVE"]["entries"] == []
    assert bundle["target_native_log"]["occurrences"] == []
    assert bundle["target_native_log"]["readbacks"] == []
    assert bundle["arm_result"].get("acceptances") in (None, [])
    assert bundle["arm_result"].get("finality") is None


@pytest.mark.parametrize(
    ("strategy", "expected_disposition", "expected_reason"),
    [
        (
            "STALE_PRIMARY",
            "REJECTED_STALE_PRIMARY",
            "STALE_PRIMARY_RECEIPTS",
        ),
        (
            "NO_REDISCOVERY",
            "REJECTED_NO_REDISCOVERY",
            "NO_VALID_REDISCOVERY",
        ),
        (
            "WRONG_OWNER_KEY",
            "REJECTED_WRONG_OWNER_OR_KEY",
            "WRONG_OWNER_OR_KEY",
        ),
        (
            "UNBOUNDED_REOPEN",
            "REJECTED_UNBOUNDED_REOPEN",
            "UNBOUNDED_OR_INCOMPLETE_REOPEN",
        ),
    ],
)
def test_target_and_evaluator_reject_attacks(
    strategy, expected_disposition, expected_reason
):
    bundle = run_case(alternative_enabled=True, strategy=strategy)
    evaluation = bundle["evaluation"]
    assert evaluation["evidence_valid"] is True
    assert evaluation["ExactTaskSuccess"] is False
    assert evaluation["disposition"] == expected_disposition
    assert evaluation["target_reason"] == expected_reason
    assert bundle["arm_result"]["target_response"]["status"] == "REJECTED"
    assert bundle["target_native_log"]["occurrences"] == []
    assert bundle["target_native_log"]["readbacks"] == []


def test_controller_preselection_fails_public_startup_gate():
    with pytest.raises(ValueError, match="invalid public startup keys"):
        _public_startup(
            run_binding="7" * 32,
            operation_id="operation-" + ("8" * 20),
            broker_endpoint_handle="9" * 32,
            target_endpoint_handle="a" * 32,
            extra={"alternative_handle": "b" * 32},
        )
    valid = _public_startup(
        run_binding="7" * 32,
        operation_id="operation-" + ("8" * 20),
        broker_endpoint_handle="9" * 32,
        target_endpoint_handle="a" * 32,
    )
    valid["q_version"] = "alternative-preselected"
    with pytest.raises(ValueError, match="private E4 material"):
        validate_public_startup(valid)


def test_bundle_content_hashes(paired_worlds):
    for bundle in paired_worlds.values():
        unsigned = dict(bundle)
        digest = unsigned.pop("bundle_sha256")
        assert digest == __import__("runtime").sha256_value(unsigned)


def test_independent_evaluator_does_not_import_runtime():
    evaluator_source = (ROOT / "evaluator.py").read_text()
    assert "from runtime import" not in evaluator_source
    assert "import runtime" not in evaluator_source


def test_frozen_database_is_standalone_and_wal_or_companions_are_rejected(
    tmp_path,
):
    database_path = tmp_path / "accepted.sqlite3"
    bundle = run_case(
        alternative_enabled=True,
        database_path=database_path,
    )
    truth = bundle["target_truth"]
    assert truth["database_journal_mode"] == "delete"
    assert truth["database_physical_sha256"] == hashlib.sha256(
        database_path.read_bytes()
    ).hexdigest()
    assert len(truth["database_logical_sha256"]) == 64
    immutable_uri = "file:%s?mode=ro&immutable=1" % database_path.as_posix()
    with sqlite3.connect(immutable_uri, uri=True) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    for suffix in ("-wal", "-shm", "-journal"):
        assert not database_path.with_name(database_path.name + suffix).exists()

    companion = database_path.with_name(database_path.name + "-wal")
    companion.touch()
    rejected_companion = evaluate_bundle(
        bundle, database_path=database_path
    )
    assert rejected_companion["evidence_valid"] is False
    assert (
        rejected_companion["reason"]
        == "standalone Target ledger has journal companions"
    )
    companion.unlink()

    wal_path = tmp_path / "adversarial-wal.sqlite3"
    shutil.copy2(database_path, wal_path)
    with sqlite3.connect(wal_path) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    for suffix in ("-wal", "-shm"):
        wal_path.with_name(wal_path.name + suffix).unlink(missing_ok=True)
    wal_bundle = copy.deepcopy(bundle)
    wal_bundle["target_truth"]["database_physical_sha256"] = hashlib.sha256(
        wal_path.read_bytes()
    ).hexdigest()
    rejected_wal = evaluate_bundle(wal_bundle, database_path=wal_path)
    assert rejected_wal["evidence_valid"] is False
    assert (
        rejected_wal["reason"]
        == "standalone Target ledger is not DELETE-journal clean"
    )

    logical_tamper = copy.deepcopy(bundle)
    logical_tamper["target_truth"]["database_logical_sha256"] = "0" * 64
    rejected_logical = evaluate_bundle(
        logical_tamper, database_path=database_path
    )
    assert rejected_logical["evidence_valid"] is False
    assert (
        rejected_logical["reason"]
        == "standalone Target ledger logical hash mismatch"
    )
