from __future__ import annotations

import copy
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from target_ledger import (  # noqa: E402
    ALREADY_SATISFIED,
    COMMITTED,
    CONFLICT,
    REPLAY_REJECTED,
    TargetOperationLedger,
)


TARGET = "VenueV:CircuitC7"
OFF = {"energized": False, "power_kw": 0.0}
ON = {"energized": True, "power_kw": 3.0}


def canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def make_ledger(tmp_path: Path, name: str = "ledger") -> TargetOperationLedger:
    ledger = TargetOperationLedger(
        tmp_path / f"{name}.sqlite3",
        ledger_id=f"{name}-truth-owner",
    )
    ledger.initialize_target(TARGET, OFF)
    return ledger


def grant(
    ledger: TargetOperationLedger,
    capability_id: str,
    actor_id: str,
    desired_state: object = ON,
) -> None:
    ledger.issue_capability(
        capability_id=capability_id,
        target_id=TARGET,
        actor_id=actor_id,
        allowed_state=desired_state,
    )


def commit(
    ledger: TargetOperationLedger,
    *,
    actor_id: str = "A4",
    capability_id: str = "cap-a4",
    request_id: str = "request-a4",
    expected_version: int = 0,
    desired_state: object = ON,
) -> dict[str, object]:
    return ledger.apply(
        target_id=TARGET,
        actor_id=actor_id,
        request_id=request_id,
        capability_id=capability_id,
        expected_version=expected_version,
        desired_state=desired_state,
    )


def test_atomic_commit_receipt_and_readback_bind_every_identity(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    grant(ledger, "cap-a4", "A4")

    receipt = commit(ledger)

    assert receipt["decision"] == COMMITTED
    assert receipt["mutation_applied"] is True
    assert receipt["actor_id"] == "A4"
    assert receipt["request_id"] == "request-a4"
    assert receipt["capability_id"] == "cap-a4"
    assert receipt["target_id"] == TARGET
    assert receipt["pre_state"] == OFF
    assert receipt["post_state"] == ON
    assert receipt["pre_version"] == 0
    assert receipt["post_version"] == 1
    assert receipt["commit_actor_id"] == "A4"
    assert receipt["commit_id"].startswith("commit-")
    assert ledger.verify_receipt(receipt)

    readback = ledger.readback(receipt)
    assert readback["observed_state"] == ON
    assert readback["observed_version"] == 1
    assert readback["observed_commit_id"] == receipt["commit_id"]
    assert readback["receipt_sha256"] == receipt["receipt_sha256"]
    assert readback["request_sha256"] == receipt["request_sha256"]
    assert readback["actor_id"] == receipt["actor_id"]
    assert readback["capability_id"] == receipt["capability_id"]
    assert readback["attached_to_receipt_commit"] is True
    assert ledger.verify_readback(readback, receipt)


def test_h_first_same_outcome_is_not_attributed_to_a4(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    grant(ledger, "cap-h", "H")
    grant(ledger, "cap-a4", "A4")

    hidden = commit(
        ledger,
        actor_id="H",
        capability_id="cap-h",
        request_id="request-h",
    )
    a4 = commit(ledger)

    assert hidden["decision"] == COMMITTED
    assert a4["decision"] == ALREADY_SATISFIED
    assert a4["mutation_applied"] is False
    assert a4["commit_id"] == hidden["commit_id"]
    assert a4["commit_actor_id"] == "H"
    assert a4["post_state"] == ON

    readback = ledger.readback(a4)
    assert readback["observed_state"] == ON
    assert readback["receipt_mutation_applied"] is False
    assert readback["observed_commit_actor_id"] == "H"
    assert ledger.verify_readback(readback, a4)

    replay_with_new_request = commit(
        ledger,
        request_id="request-a4-second-use",
    )
    assert replay_with_new_request["decision"] == REPLAY_REJECTED
    assert replay_with_new_request["reason"] == "CAPABILITY_ALREADY_CONSUMED"


def test_real_concurrency_serializes_same_desired_state(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    grant(ledger, "cap-a", "actor-a")
    grant(ledger, "cap-b", "actor-b")
    barrier = threading.Barrier(2)

    def run(actor_id: str, capability_id: str, request_id: str) -> dict[str, object]:
        barrier.wait(timeout=5)
        return commit(
            ledger,
            actor_id=actor_id,
            capability_id=capability_id,
            request_id=request_id,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(run, "actor-a", "cap-a", "request-a")
        second = executor.submit(run, "actor-b", "cap-b", "request-b")
        receipts = [first.result(timeout=10), second.result(timeout=10)]

    assert sorted(item["decision"] for item in receipts) == sorted(
        [COMMITTED, ALREADY_SATISFIED]
    )
    committed = next(item for item in receipts if item["decision"] == COMMITTED)
    already = next(
        item for item in receipts if item["decision"] == ALREADY_SATISFIED
    )
    assert already["mutation_applied"] is False
    assert already["commit_id"] == committed["commit_id"]
    assert already["commit_actor_id"] == committed["actor_id"]
    assert ledger.current_state(TARGET)["version"] == 1


def test_real_concurrency_different_states_yields_conflict(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    reserve = {"energized": True, "power_kw": 2.9}
    grant(ledger, "cap-a", "actor-a", ON)
    grant(ledger, "cap-b", "actor-b", reserve)
    barrier = threading.Barrier(2)

    def run(
        actor_id: str,
        capability_id: str,
        request_id: str,
        desired_state: object,
    ) -> dict[str, object]:
        barrier.wait(timeout=5)
        return commit(
            ledger,
            actor_id=actor_id,
            capability_id=capability_id,
            request_id=request_id,
            desired_state=desired_state,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(run, "actor-a", "cap-a", "request-a", ON)
        second = executor.submit(
            run, "actor-b", "cap-b", "request-b", reserve
        )
        receipts = [first.result(timeout=10), second.result(timeout=10)]

    assert sorted(item["decision"] for item in receipts) == sorted(
        [COMMITTED, CONFLICT]
    )
    conflict = next(item for item in receipts if item["decision"] == CONFLICT)
    assert conflict["mutation_applied"] is False
    assert conflict["reason"] == "EXPECTED_VERSION_MISMATCH"
    assert ledger.current_state(TARGET)["version"] == 1


def test_exact_request_is_idempotent_but_capability_replay_is_rejected(
    tmp_path: Path,
) -> None:
    ledger = make_ledger(tmp_path)
    grant(ledger, "cap-a4", "A4")

    original = commit(ledger)
    exact_replay = commit(ledger)
    second_request = commit(ledger, request_id="request-a4-rebound")

    assert exact_replay == original
    assert second_request["decision"] == REPLAY_REJECTED
    assert second_request["reason"] == "CAPABILITY_ALREADY_CONSUMED"
    assert second_request["mutation_applied"] is False
    assert ledger.current_state(TARGET)["version"] == 1


def test_request_id_rebind_and_actor_relabel_are_rejected(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    grant(ledger, "cap-a4", "A4")
    original = commit(ledger)

    rebound = commit(
        ledger,
        actor_id="H",
        request_id="request-a4",
        capability_id="cap-a4",
    )
    assert rebound["decision"] == REPLAY_REJECTED
    assert rebound["reason"] == "REQUEST_ID_REBOUND"

    relabelled = copy.deepcopy(original)
    relabelled["actor_id"] = "H"
    relabelled["receipt_sha256"] = canonical_sha(
        {
            key: value
            for key, value in relabelled.items()
            if key not in {"receipt_sha256", "receipt_auth_hex"}
        }
    )
    assert not ledger.verify_receipt(relabelled)


def test_receipt_transplant_across_truth_owners_is_rejected(tmp_path: Path) -> None:
    first = make_ledger(tmp_path, "ledger-a")
    second = make_ledger(tmp_path, "ledger-b")
    grant(first, "cap-a4", "A4")
    grant(second, "cap-a4", "A4")

    first_receipt = commit(first)

    assert first.verify_receipt(first_receipt)
    assert not second.verify_receipt(first_receipt)
    try:
        second.readback(first_receipt)
    except ValueError as error:
        assert "not authentic" in str(error)
    else:
        raise AssertionError("transplanted receipt unexpectedly produced readback")


def test_readback_detach_and_transplant_are_detected(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path)
    grant(ledger, "cap-on", "A4", ON)
    on_receipt = commit(
        ledger,
        actor_id="A4",
        capability_id="cap-on",
        request_id="request-on",
    )
    grant(ledger, "cap-off", "H", OFF)
    off_receipt = commit(
        ledger,
        actor_id="H",
        capability_id="cap-off",
        request_id="request-off",
        expected_version=1,
        desired_state=OFF,
    )
    assert off_receipt["decision"] == COMMITTED

    detached = ledger.readback(on_receipt)
    assert detached["attached_to_receipt_commit"] is False
    assert not ledger.verify_readback(detached, on_receipt)
    assert ledger.verify_readback(detached, on_receipt, require_attached=False)

    current = ledger.readback(off_receipt)
    assert ledger.verify_readback(current, off_receipt)
    assert not ledger.verify_readback(current, on_receipt)

    altered = copy.deepcopy(current)
    altered["receipt_sha256"] = on_receipt["receipt_sha256"]
    altered["readback_sha256"] = canonical_sha(
        {
            key: value
            for key, value in altered.items()
            if key not in {"readback_sha256", "readback_auth_hex"}
        }
    )
    assert not ledger.verify_readback(altered, on_receipt)
