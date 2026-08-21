"""Independent evaluator for the local-synthetic E4 common world.

This module deliberately does not import the runtime.  It independently
implements canonicalization, hashing, Ed25519 verification, state-coordinate
checks, and SQLite fact inspection.  It reuses only the already-audited Wave
015 durable ledger class to authenticate the standalone ledger artifact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import sqlite3
import tempfile
from typing import Any, Dict, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


OWNER_IDS = (
    "RESOURCE_PRIMARY",
    "RESOURCE_ALTERNATIVE",
    "O_V",
    "O_S",
    "O_Q",
    "O_P",
)
HERE = pathlib.Path(__file__).resolve().parent
LEDGER_SOURCE = HERE.parent / "wave-015-runner-foundation" / "target_ledger.py"
_LEDGER_SPEC = importlib.util.spec_from_file_location(
    "wave015_target_ledger_for_independent_e4_evaluation", LEDGER_SOURCE
)
if _LEDGER_SPEC is None or _LEDGER_SPEC.loader is None:
    raise RuntimeError("Wave 015 TargetOperationLedger is unavailable")
_LEDGER_MODULE = importlib.util.module_from_spec(_LEDGER_SPEC)
_LEDGER_SPEC.loader.exec_module(_LEDGER_MODULE)
IndependentTargetOperationLedger = _LEDGER_MODULE.TargetOperationLedger


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def verify_signed(value: Mapping[str, Any], public_key_hex: str) -> bool:
    try:
        signature_hex = value["signature_hex"]
        unsigned = dict(value)
        unsigned.pop("signature_hex")
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(public_key_hex)
        ).verify(bytes.fromhex(signature_hex), canonical_bytes(unsigned))
        return True
    except (KeyError, TypeError, ValueError, InvalidSignature):
        return False


def _fail(reason: str, disposition: str = "INVALID_EVIDENCE") -> Dict[str, Any]:
    return {
        "evidence_valid": False,
        "ExactTaskSuccess": False,
        "TargetStateSatisfied": False,
        "disposition": disposition,
        "reason": reason,
        "scope": "LOCAL_SYNTHETIC_E4_EXISTING_COMPOSITION",
    }


def _owner_receipt_valid(
    receipt: Mapping[str, Any],
    identity: Mapping[str, Any],
    expected_kind: str,
) -> bool:
    return (
        receipt.get("kind") == expected_kind
        and receipt.get("owner_instance_id") == identity.get("service_id")
        and receipt.get("principal_id") == identity.get("principal_id")
        and receipt.get("owner_public_key_hex") == identity.get("public_key_hex")
        and verify_signed(receipt, str(identity.get("public_key_hex", "")))
    )


def _sqlite_header_journal_mode(database_path: pathlib.Path) -> str:
    header = database_path.read_bytes()[:100]
    if len(header) != 100 or header[:16] != b"SQLite format 3\x00":
        return "invalid"
    write_version, read_version = header[18], header[19]
    if (write_version, read_version) == (1, 1):
        return "delete"
    if (write_version, read_version) == (2, 2):
        return "wal"
    return "mixed-or-unknown"


def _sqlite_logical_payload(database_path: pathlib.Path) -> Dict[str, Any]:
    database_uri = "file:%s?mode=ro&immutable=1" % database_path.as_posix()
    with sqlite3.connect(database_uri, uri=True) as connection:
        tables = connection.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        logical_tables = []
        for table_name, create_sql in tables:
            quoted_name = '"%s"' % table_name.replace('"', '""')
            columns = connection.execute(
                "PRAGMA table_info(%s)" % quoted_name
            ).fetchall()
            column_names = [item[1] for item in columns]
            primary_key_columns = [
                item[1]
                for item in sorted(columns, key=lambda item: item[5])
                if item[5] > 0
            ]
            order_columns = primary_key_columns or column_names
            order_sql = ", ".join(
                '"%s"' % item.replace('"', '""') for item in order_columns
            )
            rows = connection.execute(
                "SELECT * FROM %s ORDER BY %s" % (quoted_name, order_sql)
            ).fetchall()
            logical_tables.append(
                {
                    "name": table_name,
                    "create_sql": create_sql,
                    "columns": column_names,
                    "rows": [list(row) for row in rows],
                }
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "schema": "E4_SQLITE_LOGICAL_SNAPSHOT_V1",
        "journal_mode": _sqlite_header_journal_mode(database_path),
        "integrity_check": integrity,
        "tables": logical_tables,
    }


def _database_facts(database_path: pathlib.Path) -> Dict[str, Any]:
    database_uri = "file:%s?mode=ro&immutable=1" % database_path.as_posix()
    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        counts = {
            table: connection.execute(
                "SELECT COUNT(*) FROM %s" % table
            ).fetchone()[0]
            for table in ("commit_events", "readbacks", "requests", "receipts")
        }
        capability = connection.execute(
            "SELECT capability_id, consumed_by_request_id, "
            "consumed_by_receipt_id FROM capabilities"
        ).fetchone()
        target = connection.execute(
            "SELECT target_id, state_json, state_sha256, version, "
            "last_commit_id, last_commit_actor_id FROM targets"
        ).fetchone()
    return {
        "counts": counts,
        "capability": dict(capability) if capability is not None else None,
        "target": (
            {
                **dict(target),
                "state": json.loads(target["state_json"]),
            }
            if target is not None
            else None
        ),
    }


def _exact_c7_coordinates_valid(
    state: Mapping[str, Any],
    *,
    deadline_minute: int,
) -> bool:
    try:
        samples = state["samples"]
        start = state["effect_start_minute"]
        end = state["effect_end_minute"]
        duration = state["required_duration_minutes"]
        return (
            state["energized"] is True
            and state["power_kw"] == 3.0
            and start == 10
            and end == 55
            and duration == 45
            and end - start == duration
            and state["deadline_minute"] == deadline_minute == 90
            and end <= deadline_minute
            and len(samples) == 46
            and [sample["offset_minute"] for sample in samples]
            == list(range(46))
            and all(
                sample["minute"] == start + sample["offset_minute"]
                and 2.85 <= sample["power_kw"] <= 3.15
                and sample["safety_ok"] is True
                and sample["noise_ok"] is True
                and sample["other_circuits_energized"] == []
                for sample in samples
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_bundle(
    bundle: Mapping[str, Any],
    *,
    database_path: pathlib.Path | str | None = None,
) -> Dict[str, Any]:
    try:
        services = bundle["service_manifest"]
        owners = bundle["owner_native_logs"]
        arm = bundle["arm_result"]
        broker = bundle["broker_native_log"]
        target = bundle["target_native_log"]
        private_case = bundle["private_case"]
        target_truth = bundle["target_truth"]
        startup = bundle["arm_startup"]
    except (KeyError, TypeError):
        return _fail("required bundle section missing")

    if database_path is None:
        return _fail("standalone Target ledger path missing")
    database_path = pathlib.Path(database_path)
    if not database_path.is_file():
        return _fail("standalone Target ledger artifact missing")
    companions = [
        database_path.with_name(database_path.name + suffix)
        for suffix in ("-wal", "-shm", "-journal")
    ]
    if any(path.exists() for path in companions):
        return _fail("standalone Target ledger has journal companions")
    if target_truth.get("database_journal_mode") != "delete":
        return _fail("bundle does not require DELETE-journal freeze")
    if (
        hashlib.sha256(database_path.read_bytes()).hexdigest()
        != target_truth.get("database_physical_sha256")
    ):
        return _fail("standalone Target ledger physical hash mismatch")

    try:
        logical_payload = _sqlite_logical_payload(database_path)
        database_facts = _database_facts(database_path)
    except (sqlite3.Error, OSError, ValueError):
        return _fail("standalone Target ledger unreadable")
    if (
        logical_payload["journal_mode"] != "delete"
        or logical_payload["integrity_check"] != "ok"
    ):
        return _fail("standalone Target ledger is not DELETE-journal clean")
    if (
        hashlib.sha256(canonical_bytes(logical_payload)).hexdigest()
        != target_truth.get("database_logical_sha256")
    ):
        return _fail("standalone Target ledger logical hash mismatch")
    if database_facts["target"] is None:
        return _fail("Target ledger has no target")
    if database_facts["target"]["target_id"] != startup.get("object_id"):
        return _fail("Target ledger object mismatch")

    if set(owners) != set(OWNER_IDS):
        return _fail("owner log set incomplete")
    required_services = {*OWNER_IDS, "BROKER", "TARGET", "ARM"}
    if set(services) != required_services:
        return _fail("service manifest set incomplete")
    all_identities = [services[key] for key in services]
    if len({identity["process_id"] for identity in all_identities}) != 9:
        return _fail("process identity collision")
    if len({identity["public_key_hex"] for identity in all_identities}) != 9:
        return _fail("process key collision")
    for identity in all_identities:
        if not verify_signed(identity, str(identity.get("public_key_hex", ""))):
            return _fail("process identity signature invalid")
        if identity.get("start_method") != "spawn":
            return _fail("non-spawn process")

    for owner_id, native in owners.items():
        identity = services[owner_id]
        if native["identity"] != identity:
            return _fail("owner identity/log mismatch")
        for receipt in native["entries"]:
            if not verify_signed(receipt, identity["public_key_hex"]):
                return _fail("owner native receipt signature invalid")
    for receipt in broker["entries"]:
        if not verify_signed(receipt, services["BROKER"]["public_key_hex"]):
            return _fail("broker receipt signature invalid")
    for receipt in target["entries"]:
        if not verify_signed(receipt, services["TARGET"]["public_key_hex"]):
            return _fail("Target native receipt signature invalid")

    startup_bytes = canonical_bytes(startup).decode("utf-8").lower()
    for forbidden in (
        "e4-revoke",
        "e4_remove",
        "remove_alternative",
        "alternative",
        "primary",
        "scenario",
        "expected",
        services["RESOURCE_ALTERNATIVE"]["principal_id"].lower(),
        services["RESOURCE_ALTERNATIVE"]["public_key_hex"].lower(),
    ):
        if forbidden in startup_bytes:
            return _fail("alternative or E4 material leaked at startup")

    alt_handle = broker["private_handle_map"]["RESOURCE_ALTERNATIVE"]
    transcript = arm["transcript"]
    revelation_indexes = [
        index
        for index, event in enumerate(transcript)
        if event.get("kind") == "BROKER_INTERACTION"
        and (
            event.get("action") == "BYPASS_REDISCOVERY"
            or (
                event.get("action") == "DISCOVER"
                and sum(
                    prior.get("kind") == "BROKER_INTERACTION"
                    and prior.get("action") == "DISCOVER"
                    for prior in transcript[:index]
                )
                == 1
            )
        )
    ]
    prefix = (
        transcript
        if not revelation_indexes
        else transcript[: revelation_indexes[0]]
    )
    prefix_bytes = canonical_bytes(prefix).decode("utf-8")
    for forbidden in (
        alt_handle,
        "RESOURCE_ALTERNATIVE",
        services["RESOURCE_ALTERNATIVE"]["principal_id"],
        services["RESOURCE_ALTERNATIVE"]["public_key_hex"],
    ):
        if forbidden in prefix_bytes:
            return _fail("alternative prewritten before rediscovery")

    primary_identity = services["RESOURCE_PRIMARY"]
    alt_identity = services["RESOURCE_ALTERNATIVE"]
    if primary_identity["principal_id"] == alt_identity["principal_id"]:
        return _fail("primary/alternative principal alias")
    if primary_identity["public_key_hex"] == alt_identity["public_key_hex"]:
        return _fail("primary/alternative key alias")
    if primary_identity["state_source_id"] == alt_identity["state_source_id"]:
        return _fail("primary/alternative state alias")

    primary = arm["primary"]
    for key, kind in (
        ("offer", "RESOURCE_OFFER"),
        ("grant", "CURRENT_PURPOSE_GRANT"),
        ("commitment", "CURRENT_COMMITMENT"),
        ("reservation", "CURRENT_RESERVATION"),
        ("revoke", "OWNER_NATIVE_REVOKE"),
    ):
        if not _owner_receipt_valid(primary[key], primary_identity, kind):
            return _fail("primary native chain invalid: %s" % key)
    if primary["revoke"]["payload"].get("reservation_sha256") != sha256_value(
        primary["reservation"]
    ):
        return _fail("primary revoke detached from reservation")
    if not _owner_receipt_valid(
        primary["compensation"],
        services["O_P"],
        "PRIMARY_CANCEL_COMPENSATION",
    ):
        return _fail("primary compensation invalid")

    alternative_enabled = private_case["alternative_enabled"]
    if not alternative_enabled:
        if arm["disposition"] != "BOUNDED_REFUSAL_NO_ALTERNATIVE":
            return _fail(
                "REMOVE_ALTERNATIVE still reported success",
                "COUNTERFACTUAL_VIOLATION",
            )
        if target["occurrences"] or target["readbacks"]:
            return _fail(
                "REMOVE_ALTERNATIVE produced Target mutation",
                "COUNTERFACTUAL_VIOLATION",
            )
        if owners["RESOURCE_ALTERNATIVE"]["entries"]:
            return _fail(
                "removed alternative was still used",
                "COUNTERFACTUAL_VIOLATION",
            )
        if arm.get("rediscovery", {}).get("status") != "NOT_FOUND":
            return _fail("counterfactual rediscovery not exhausted")
        if (
            database_facts["target"]["version"] != 0
            or database_facts["counts"]["commit_events"] != 0
            or database_facts["counts"]["readbacks"] != 0
            or database_facts["capability"]["consumed_by_request_id"] is not None
        ):
            return _fail(
                "REMOVE_ALTERNATIVE mutated durable Target truth",
                "COUNTERFACTUAL_VIOLATION",
            )
        return {
            "evidence_valid": True,
            "ExactTaskSuccess": False,
            "TargetStateSatisfied": False,
            "AlternativeRemoved": True,
            "DurableTargetUnchanged": True,
            "StandaloneDeleteJournalTarget": True,
            "PhysicalLogicalDatabaseHashBound": True,
            "disposition": "BOUNDED_REFUSAL_NO_ALTERNATIVE",
            "scope": "LOCAL_SYNTHETIC_E4_REMOVE_ALTERNATIVE",
            "non_claims": [
                "NO_LEGAL_AUTHORITY_PROOF",
                "NO_PHYSICAL_EFFECT",
                "NOT_FULL_E4_GENERALIZATION",
            ],
        }

    target_response = arm.get("target_response")
    if not isinstance(target_response, Mapping):
        return _fail("missing Target response")
    if target_response.get("status") != "COMMITTED":
        reason = target_response.get("reason")
        disposition_by_reason = {
            "NO_VALID_REDISCOVERY": "REJECTED_NO_REDISCOVERY",
            "STALE_PRIMARY_RECEIPTS": "REJECTED_STALE_PRIMARY",
            "WRONG_DISCOVERED_OWNER": "REJECTED_STALE_PRIMARY",
            "WRONG_OWNER_OR_KEY": "REJECTED_WRONG_OWNER_OR_KEY",
            "UNBOUNDED_OR_INCOMPLETE_REOPEN": "REJECTED_UNBOUNDED_REOPEN",
        }
        if target["occurrences"] or target["readbacks"]:
            return _fail("rejected Target attempt mutated wrapper state")
        if (
            database_facts["target"]["version"] != 0
            or database_facts["counts"]["commit_events"] != 0
            or database_facts["counts"]["readbacks"] != 0
            or database_facts["capability"]["consumed_by_request_id"] is not None
        ):
            return _fail("rejected Target attempt mutated durable state")
        return {
            "evidence_valid": True,
            "ExactTaskSuccess": False,
            "TargetStateSatisfied": False,
            "DurableTargetUnchanged": True,
            "StandaloneDeleteJournalTarget": True,
            "PhysicalLogicalDatabaseHashBound": True,
            "disposition": disposition_by_reason.get(reason, "TARGET_REJECTED"),
            "target_reason": reason,
            "scope": "LOCAL_SYNTHETIC_E4_ATTACK",
        }

    rediscovery = arm.get("rediscovery_receipt")
    if not isinstance(rediscovery, Mapping) or not verify_signed(
        rediscovery, services["BROKER"]["public_key_hex"]
    ):
        return _fail("rediscovery receipt invalid")
    if rediscovery.get("kind") != "DISCOVERY_AFTER_REVOKE":
        return _fail("alternative not discovered after revoke")
    if rediscovery.get("payload", {}).get("owner_handle") != alt_handle:
        return _fail("rediscovery handle not alternative")
    if rediscovery.get("payload", {}).get(
        "after_revoke_receipt_sha256"
    ) != sha256_value(primary["revoke"]):
        return _fail("rediscovery not causally after current revoke")

    chain = arm["selected_chain"]
    for key, kind in (
        ("offer", "RESOURCE_OFFER"),
        ("grant", "CURRENT_PURPOSE_GRANT"),
        ("commitment", "CURRENT_COMMITMENT"),
        ("reservation", "CURRENT_RESERVATION"),
    ):
        if not _owner_receipt_valid(chain[key], alt_identity, kind):
            return _fail("alternative native chain invalid: %s" % key)
    if chain["grant"]["payload"].get("offer_sha256") != sha256_value(
        chain["offer"]
    ):
        return _fail("alternative grant detached")
    if chain["commitment"]["payload"].get("grant_sha256") != sha256_value(
        chain["grant"]
    ):
        return _fail("alternative commitment detached")
    if chain["reservation"]["payload"].get(
        "commitment_sha256"
    ) != sha256_value(chain["commitment"]):
        return _fail("alternative reservation detached")

    reopen = arm["reopen_evidence"]
    if not verify_signed(reopen, services["ARM"]["public_key_hex"]):
        return _fail("reopen evidence signature invalid")
    if reopen.get("arm_public_key_hex") != services["ARM"]["public_key_hex"]:
        return _fail("reopen evidence not bound to ARM identity")
    if reopen["payload"].get("revoke_sha256") != sha256_value(primary["revoke"]):
        return _fail("reopen evidence detached from revoke")
    if reopen["payload"].get("revoke_state_head_after") != primary[
        "revoke"
    ].get("state_head_after"):
        return _fail("reopen evidence detached from revoke owner head")
    if set(reopen["payload"].get("invalidated", [])) != {
        "primary_offer",
        "primary_grant",
        "primary_commitment",
        "primary_reservation",
        "venue_approval",
        "safety_approval",
        "primary_obligation",
    }:
        return _fail("reopen invalidation not exactly bounded")
    if set(reopen["payload"].get("preserved", [])) != {
        "Q",
        "object_id",
        "deadline",
    }:
        return _fail("reopen did not preserve unaffected coordinates")

    for key, owner, kind in (
        ("venue_reapproval", "O_V", "VENUE_EXACT_REAPPROVAL"),
        ("safety_reapproval", "O_S", "SAFETY_EXACT_REAPPROVAL"),
        ("alternative_binding", "O_P", "ALTERNATIVE_OBLIGATION_BINDING"),
    ):
        if not _owner_receipt_valid(arm[key], services[owner], kind):
            return _fail("%s invalid" % key)
    if (
        arm["alternative_binding"].get("state_head_before")
        != primary["compensation"].get("state_head_after")
    ):
        return _fail("O_P compensation/binding chain is not contiguous")

    if len(target["fresh_status_queries"]) != 5:
        return _fail("commit-time owner status query set incomplete")
    statuses = {
        item.get("owner_instance_id"): item
        for item in target["fresh_status_queries"]
    }
    if set(statuses) != {
        "RESOURCE_ALTERNATIVE",
        "RESOURCE_PRIMARY",
        "O_V",
        "O_S",
        "O_P",
    }:
        return _fail("commit-time status owner set mismatch")
    status_requirements = {
        "RESOURCE_ALTERNATIVE": (
            chain["reservation"]["state_head_after"],
            {
                "current": True,
                "granted": True,
                "committed": True,
                "reserved": True,
                "revoked": False,
            },
        ),
        "RESOURCE_PRIMARY": (
            primary["revoke"]["state_head_after"],
            {"current": False, "revoked": True},
        ),
        "O_V": (
            arm["venue_reapproval"]["state_head_after"],
            {"current": True, "revoked": False},
        ),
        "O_S": (
            arm["safety_reapproval"]["state_head_after"],
            {"current": True, "revoked": False},
        ),
        "O_P": (
            arm["alternative_binding"]["state_head_after"],
            {"current": True, "revoked": False},
        ),
    }
    for owner_id, (expected_head, expected_flags) in status_requirements.items():
        status = statuses[owner_id]
        if not _owner_receipt_valid(
            status, services[owner_id], "OWNER_CURRENT_STATUS"
        ):
            return _fail("commit-time status signature invalid: %s" % owner_id)
        if (
            status.get("state_head_before") != expected_head
            or status.get("payload", {}).get("observed_state_head")
            != expected_head
            or any(
                status.get("payload", {}).get(key) != value
                for key, value in expected_flags.items()
            )
        ):
            return _fail("commit-time status stale or wrong: %s" % owner_id)

    if len(target["ledger_receipts"]) != 1:
        return _fail("durable ledger receipt count not exactly one")
    if len(target["ledger_readbacks"]) != 1:
        return _fail("durable ledger readback count not exactly one")
    ledger_receipt = target["ledger_receipts"][0]
    ledger_readback = target["ledger_readbacks"][0]
    try:
        with tempfile.TemporaryDirectory(prefix="e4-independent-ledger-") as temp:
            evaluation_copy = pathlib.Path(temp) / "target-ledger.sqlite3"
            shutil.copy2(database_path, evaluation_copy)
            ledger = IndependentTargetOperationLedger(
                evaluation_copy, ledger_id=target_truth["ledger_id"]
            )
            if not ledger.verify_receipt(ledger_receipt):
                return _fail("durable ledger receipt authentication failed")
            if not ledger.verify_readback(ledger_readback, ledger_receipt):
                return _fail("durable ledger readback authentication failed")
    except (OSError, sqlite3.Error, ValueError):
        return _fail("durable ledger identity invalid")
    exact_state = target_truth["exact_state"]
    if not _exact_c7_coordinates_valid(
        exact_state, deadline_minute=startup["deadline_minute"]
    ):
        return _fail("CE-001 exact state coordinates invalid")
    if (
        target.get("exact_state") != exact_state
        or database_facts["target"]["state"] != exact_state
        or ledger_receipt.get("post_state") != exact_state
        or ledger_readback.get("observed_state") != exact_state
    ):
        return _fail("exact state not identical across Target truth surfaces")
    if (
        database_facts["target"]["version"] != 1
        or database_facts["counts"]["commit_events"] != 1
        or database_facts["counts"]["readbacks"] != 1
        or database_facts["counts"]["requests"] != 1
        or database_facts["counts"]["receipts"] != 1
        or database_facts["capability"]["capability_id"]
        != target_truth["capability_id"]
        or database_facts["capability"]["consumed_by_request_id"]
        != ledger_receipt["request_id"]
        or database_facts["capability"]["consumed_by_receipt_id"]
        != ledger_receipt["receipt_id"]
    ):
        return _fail("durable ledger exact-once facts invalid")

    if len(target["occurrences"]) != 1 or len(target["readbacks"]) != 1:
        return _fail("Target did not contain exactly one occurrence/readback")
    occurrence = target["occurrences"][0]
    readback = target["readbacks"][0]
    if occurrence.get("authority_owner_instance_id") != "RESOURCE_ALTERNATIVE":
        return _fail("Target consumed non-alternative authority")
    if occurrence.get("object_id") != startup["object_id"]:
        return _fail("Target wrong object")
    if occurrence.get("operation_id") != startup["operation_id"]:
        return _fail("Target wrong operation")
    if occurrence.get("exact_state_sha256") != sha256_value(exact_state):
        return _fail("Target occurrence exact state hash mismatch")
    if occurrence.get("ledger_receipt_sha256") != sha256_value(ledger_receipt):
        return _fail("Target occurrence detached from durable receipt")
    if occurrence.get("ledger_readback_sha256") != sha256_value(ledger_readback):
        return _fail("Target occurrence detached from durable readback")
    if occurrence.get("reopen_evidence_sha256") != sha256_value(reopen):
        return _fail("Target occurrence detached from bounded reopen")
    if occurrence.get("fresh_status_sha256") != {
        owner_id: sha256_value(status)
        for owner_id, status in statuses.items()
    }:
        return _fail("Target occurrence detached from fresh status set")
    if readback.get("occurrence_sha256") != sha256_value(occurrence):
        return _fail("Target wrapper readback detached")
    if readback.get("state") != exact_state:
        return _fail("Target wrapper readback not exact state")
    if not verify_signed(occurrence, services["TARGET"]["public_key_hex"]):
        return _fail("Target occurrence signature invalid")
    if not verify_signed(readback, services["TARGET"]["public_key_hex"]):
        return _fail("Target readback signature invalid")

    duplicate = arm.get("duplicate_response")
    if (
        not isinstance(duplicate, Mapping)
        or duplicate.get("status") != "ALREADY_COMMITTED"
        or duplicate.get("occurrence", {}).get("commit_id")
        != occurrence["commit_id"]
        or database_facts["counts"]["commit_events"] != 1
    ):
        return _fail("duplicate mutation was not idempotently blocked")

    acceptances = arm.get("acceptances", [])
    if len(acceptances) != 2:
        return _fail("dual Acceptance missing")
    expected_acceptance = {
        "O_Q": "OWNER_ACCEPTANCE",
        "O_V": "VENUE_ACCEPTANCE",
    }
    for acceptance in acceptances:
        owner_id = acceptance.get("owner_instance_id")
        if owner_id not in expected_acceptance or not _owner_receipt_valid(
            acceptance, services[owner_id], expected_acceptance[owner_id]
        ):
            return _fail("Acceptance invalid")
        if acceptance["payload"].get("readback_sha256") != sha256_value(
            readback
        ):
            return _fail("Acceptance detached from readback")
        if acceptance["payload"].get("resource_handle") != alt_handle:
            return _fail("Acceptance not alternative-bound")

    finality = arm.get("finality")
    if not isinstance(finality, Mapping) or not _owner_receipt_valid(
        finality, services["O_P"], "ALTERNATIVE_BOUND_FINALITY"
    ):
        return _fail("alternative-bound finality invalid")
    if set(finality["payload"].get("acceptance_sha256", [])) != {
        sha256_value(item) for item in acceptances
    }:
        return _fail("finality Acceptance set mismatch")
    if finality["payload"].get("resource_handle") != alt_handle:
        return _fail("finality not alternative-bound")

    return {
        "evidence_valid": True,
        "ExactTaskSuccess": True,
        "TargetStateSatisfied": True,
        "PrimaryRevokedBeforeCommit": True,
        "BoundedLocalReopen": True,
        "AlternativeActuallyRediscovered": True,
        "AlternativeCurrentChain": True,
        "FreshOwnerStatusAtCommit": True,
        "DurableSQLiteTargetLedger": True,
        "StandaloneDeleteJournalTarget": True,
        "PhysicalLogicalDatabaseHashBound": True,
        "ExactCE001CoordinatesVerified": True,
        "UniqueExactOccurrence": True,
        "DualAcceptance": True,
        "AlternativeBoundFinality": True,
        "disposition": "RECOVERED_VIA_LEGAL_ALTERNATIVE",
        "scope": "LOCAL_SYNTHETIC_E4_EXISTING_COMPOSITION",
        "solution_class": (
            "EXISTING_COMPOSITION: LEASE_REVOCATION + BOUNDED_REOPEN + "
            "REDISCOVERY + OWNER_RECEIPTS + FRESH OWNER STATUS + "
            "DURABLE TARGET COMMIT GATE + IDEMPOTENT LEDGER"
        ),
        "non_claims": [
            "NO_LEGAL_AUTHORITY_PROOF",
            "NO_PHYSICAL_EFFECT",
            "NO_CROSS_DOMAIN_GENERALIZATION",
            "NOT_FULL_TOWOW_SOLUTION",
        ],
    }
