from __future__ import annotations

import ast
import copy
import json
import pathlib
import shutil
import sqlite3
import sys


WAVE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(WAVE_DIR) not in sys.path:
    sys.path.insert(0, str(WAVE_DIR))

import independent_evaluator as evaluator  # noqa: E402


FROZEN_RUN = WAVE_DIR / "artifacts" / "twin-91591fa0c44344839e6c3a23b5dca258"
FROZEN_RUNTIME_SHA256 = (
    "006e2346115143d2e253396a5442814e6064ae17c9e3151713ba9f2e6b4092f9"
)
FROZEN_TWIN_SHA256 = (
    "15b806743e79e9c8588b7c7e9db2af1433587fd17485c860ccb3440f311422b9"
)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: pathlib.Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def copied_run(tmp_path: pathlib.Path) -> pathlib.Path:
    destination = tmp_path / "attacked-run"
    shutil.copytree(FROZEN_RUN, destination)
    return destination


def rehash_world(world_path: pathlib.Path, world: dict) -> None:
    world.pop("world_artifact_sha256", None)
    world["world_artifact_sha256"] = evaluator.sha256_value(world)
    write(world_path, world)


def rehash_twin(run_dir: pathlib.Path, twin: dict) -> None:
    twin.pop("twin_artifact_sha256", None)
    twin["twin_artifact_sha256"] = evaluator.sha256_value(twin)
    write(run_dir / "TWIN-ARTIFACT.json", twin)


def test_evaluator_accepts_three_scoped_claims_but_fails_full_blindness():
    result = evaluator.evaluate_run(FROZEN_RUN)

    assert result["status"] == (
        "EVALUATED_MIXED_SCOPED_LOCAL_SYNTHETIC_DISCRIMINATOR"
    )
    assert result["root_evidence"]["twin_artifact_sha256"] == FROZEN_TWIN_SHA256
    assert evaluator.file_sha256(WAVE_DIR / "twin_runtime.py") == FROZEN_RUNTIME_SHA256
    assert result["claims"]["CL-024-TARGET-CONSUMED-AUTHORITY-FENCE"][
        "status"
    ] == "SUPPORT_SCOPED"
    assert result["claims"]["CL-024-EXACTLY-ONCE-RECOVERY"]["status"] == (
        "SUPPORT_SCOPED"
    )
    assert result["claims"]["CL-024-NATIVE-POSTCONDITIONS"]["status"] == (
        "SUPPORT_SCOPED"
    )
    assert result["claims"]["CL-024-ISOMORPHIC-BLINDNESS"]["status"] == "FAIL"
    assert result["claims"]["CL-024-GLOBAL-AUTHORITY-CURRENTNESS"][
        "status"
    ] == "NOT_TESTED"


def test_u_is_native_commit_with_postconditions_but_remains_unscored():
    result = evaluator.evaluate_run(FROZEN_RUN)
    twin = load(FROZEN_RUN / "TWIN-ARTIFACT.json")

    assert result["worlds"]["U"]["decision"] == "COMMITTED"
    assert result["worlds"]["U"]["effect_count"] == 1
    assert result["worlds"]["U"]["acceptance_count"] == 2
    assert result["worlds"]["U"]["finality_count"] == 1
    assert twin["results"]["U"]["scoring_status"] == (
        "CONCURRENT_OR_UNORDERED/NOT_SCORED"
    )
    assert twin["results"]["U"]["target_matching_fence_ack_exists"] is False


def test_evaluator_source_does_not_import_runtime_or_twin_summary_code():
    source_path = WAVE_DIR / "independent_evaluator.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert "twin_runtime" not in imported


def test_attack_twin_self_hash_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    twin_path = attacked / "TWIN-ARTIFACT.json"
    twin = load(twin_path)
    twin["status"] = "ATTACKER_ACCEPTED"
    write(twin_path, twin)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "TWIN root self-hash mismatch" in result["errors"][0]
    assert all(
        result["claims"][claim]["status"] == "FAIL"
        for claim in evaluator.SCOPED_CLAIMS
    )


def test_attack_world_self_hash_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    world_path = attacked / "world-r" / "WORLD-ARTIFACT.json"
    world = load(world_path)
    world["claim_boundary"] = "ATTACKER_REWRITTEN"
    write(world_path, world)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "world R self-hash mismatch" in result["errors"][0]


def test_attack_native_effect_removed_is_rejected_even_after_rehash(tmp_path):
    attacked = copied_run(tmp_path)
    world_path = attacked / "world-s" / "WORLD-ARTIFACT.json"
    world = load(world_path)
    target_path = attacked / "world-s" / world["files"]["target_db"]
    with sqlite3.connect(target_path) as connection:
        connection.execute("DELETE FROM effects")
        connection.commit()
    world["files"]["target_db_sha256"] = evaluator.file_sha256(target_path)
    rehash_world(world_path, world)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "effects table count mismatch" in result["errors"][0]


def test_attack_target_signature_is_rejected_after_consistent_json_db_rewrite(
    tmp_path,
):
    attacked = copied_run(tmp_path)
    world_path = attacked / "world-s" / "WORLD-ARTIFACT.json"
    world = load(world_path)
    forged_signature = "00" * 64
    world["target_execute_receipt"]["signature_hex"] = forged_signature
    world["candidate_recovery_result"]["target_status"]["receipt"][
        "signature_hex"
    ] = forged_signature
    target_path = attacked / "world-s" / world["files"]["target_db"]
    with sqlite3.connect(target_path) as connection:
        row = connection.execute("SELECT receipt_json FROM requests").fetchone()
        receipt = json.loads(row[0])
        receipt["signature_hex"] = forged_signature
        connection.execute(
            "UPDATE requests SET receipt_json=?",
            (evaluator.canonical_bytes(receipt).decode("utf-8"),),
        )
        connection.commit()
    world["files"]["target_db_sha256"] = evaluator.file_sha256(target_path)
    rehash_world(world_path, world)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "Target execute receipt Ed25519 signature invalid" in result["errors"][0]


def test_attack_op_finality_peer_key_replacement_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    world_path = attacked / "world-s" / "WORLD-ARTIFACT.json"
    world = load(world_path)
    owner_path = attacked / "world-s" / "owners" / "o_p.sqlite3"
    forged_peers = json.dumps(
        {"O_Q": "11" * 32, "O_V": "22" * 32},
        sort_keys=True,
        separators=(",", ":"),
    )
    with sqlite3.connect(owner_path) as connection:
        connection.execute(
            "UPDATE owner_identity SET pinned_acceptance_keys_json=?",
            (forged_peers,),
        )
        connection.commit()
    world["files"]["owner_db_sha256"]["O_P"] = evaluator.file_sha256(owner_path)
    world["owner_store_audits"]["O_P"]["identity"][
        "pinned_acceptance_keys_json"
    ] = forged_peers
    rehash_world(world_path, world)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "O_P pinned Acceptance keys mismatch" in result["errors"][0]


def test_attack_authority_timing_summary_cannot_replace_native_causal_link(tmp_path):
    attacked = copied_run(tmp_path)
    twin = load(attacked / "TWIN-ARTIFACT.json")
    twin["authority_timing"]["s_target_receipt_sha256"] = "ff" * 32
    rehash_twin(attacked, twin)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "Authority timing summary/native causal evidence mismatch" in result[
        "errors"
    ][0]


def test_attack_missing_authority_signed_s_predecessor_is_rejected(tmp_path):
    attacked = copied_run(tmp_path)
    revocation_path = attacked / "AUTHORITY-REVOCATION.json"
    revocation = load(revocation_path)
    revocation.pop("experiment_predecessor_s_target_receipt_sha256")
    write(revocation_path, revocation)

    result = evaluator.evaluate_run(attacked)
    assert result["status"] == "REJECTED_EVIDENCE_PACKAGE"
    assert "revocation file/DB mismatch" in result["errors"][0]
