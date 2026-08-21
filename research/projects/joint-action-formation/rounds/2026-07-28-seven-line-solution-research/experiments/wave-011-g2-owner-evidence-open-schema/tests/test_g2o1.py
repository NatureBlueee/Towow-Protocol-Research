"""Adversarial contract for G2-O1.

These tests intentionally score observable owner events and public experiment
outputs.  They do not accept ``private/oracle.json.expected`` as an execution
input: changing or deleting that answer key must not change measured axes.
"""

from __future__ import annotations

import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable

import pytest


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FIXTURE = ROOT / "fixtures" / "public_worlds.json"
PRIVATE_ORACLE = ROOT / "private" / "oracle.json"
RUNNER = ROOT / "runner.py"

FORBIDDEN_PUBLIC_ANSWER_KEYS = {
    "relation_valid",
    "material_change",
    "opposition_preserved",
}
AXES = {"constituted", "understood", "claimed", "authorized", "activated"}
DIAGNOSTICS = {
    "schema_change",
    "private_column_recall",
    "provenance_opposition",
    "stale_revoke",
    "duplicate_reservation",
    "partition_recovery",
    "cost",
}
REQUIRED_ARM_MARKERS = {
    "institution": ("institution", "human"),
    "center": ("center",),
    "mature": ("mature", "component", "composition"),
    "replicated": ("replicated", "signed_replica", "signed-replica"),
}


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, (*path, str(index)))


def _worlds(document: Any) -> list[dict[str, Any]]:
    assert isinstance(document, dict), "fixture must be a JSON object"
    worlds = document.get("worlds")
    assert isinstance(worlds, list), "public fixture must contain worlds[]"
    return worlds


def _family(world: dict[str, Any]) -> str:
    raw = str(world.get("family", "")).upper().replace("-", "_")
    if raw.startswith("AUTH"):
        return "AUTHORITY"
    for family in ("T2", "T4", "T5"):
        if raw.startswith(family):
            return family
    return raw


def _run(
    tmp_path: Path,
    *,
    fixture: Path = PUBLIC_FIXTURE,
    oracle: Path = PRIVATE_ORACLE,
    name: str = "results.json",
) -> dict[str, Any]:
    output = tmp_path / name
    command = [
        sys.executable,
        str(RUNNER),
        "--fixture",
        str(fixture),
        "--oracle",
        str(oracle),
        "--output",
        str(output),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": "17"},
        timeout=180,
    )
    assert completed.returncode == 0, (
        f"runner failed ({completed.returncode})\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    assert output.is_file(), "runner did not write the requested output"
    result = _load(output)
    assert isinstance(result, dict)
    return result


@pytest.fixture(scope="module")
def public_fixture() -> dict[str, Any]:
    return _load(PUBLIC_FIXTURE)


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    return _run(tmp_path_factory.mktemp("g2o1"), name="baseline.json")


def _runs(result: dict[str, Any]) -> list[dict[str, Any]]:
    runs = result.get("runs")
    assert isinstance(runs, list) and runs, "result must contain non-empty runs[]"
    return runs


def _arm_marker(arm: str) -> str | None:
    lowered = arm.lower()
    for canonical, markers in REQUIRED_ARM_MARKERS.items():
        if any(marker in lowered for marker in markers):
            return canonical
    return None


def _events_text(run: dict[str, Any]) -> str:
    return json.dumps(run.get("owner_events", []), ensure_ascii=False).upper()


def _diagnostic_text(run: dict[str, Any], name: str) -> str:
    diagnostics = run.get("diagnostics", {})
    return json.dumps(diagnostics.get(name), ensure_ascii=False).upper()


def test_delivery_surface_and_twelve_world_denominator(public_fixture: dict[str, Any]) -> None:
    assert RUNNER.is_file()
    assert PRIVATE_ORACLE.is_file()
    assert (ROOT / "g2o1" / "actors.py").is_file()
    assert (ROOT / "README.md").is_file()

    worlds = _worlds(public_fixture)
    assert len(worlds) == 12
    world_ids = [world.get("world_id") for world in worlds]
    assert all(isinstance(world_id, str) and world_id for world_id in world_ids)
    assert len(set(world_ids)) == 12

    counts = {"T2": 0, "T4": 0, "T5": 0, "AUTHORITY": 0}
    for world in worlds:
        family = _family(world)
        matched = [name for name in counts if name in family]
        assert len(matched) == 1, f"world family must identify one cohort: {world}"
        counts[matched[0]] += 1
    assert counts == {"T2": 4, "T4": 4, "T5": 2, "AUTHORITY": 2}


def test_public_fixture_contains_no_readable_answer_labels(
    public_fixture: dict[str, Any],
) -> None:
    leaks: list[str] = []
    for path, _value in _walk(public_fixture):
        if path and path[-1].lower() in FORBIDDEN_PUBLIC_ANSWER_KEYS:
            leaks.append(".".join(path))
    assert leaks == [], f"public answer leakage: {leaks}"


def test_schema_delta_is_derived_from_structure_not_fixture_label() -> None:
    kernel = importlib.import_module("g2o1.kernel")
    analyze = getattr(kernel, "analyze_schema_delta")
    base = {
        "schema": {
            "roles": ["buyer", "supplier"],
            "actions": ["read"],
            "evidence": ["readback"],
            "exit_rules": ["revoke"],
            "evaluation_rules": ["no-export"],
            "constraints": [],
        },
        "parameters": {"retention_days": 7},
    }
    parameter_only = copy.deepcopy(base)
    parameter_only["parameters"]["retention_days"] = 14
    schema_change = copy.deepcopy(base)
    schema_change["schema"]["roles"].append("affected-party-representative")
    schema_change["schema"]["actions"].append("challenge")

    parameter_result = analyze(base, parameter_only)
    schema_result = analyze(base, schema_change)
    assert "PARAMETER" in repr(parameter_result).upper()
    assert "SCHEMA" in repr(schema_result).upper()
    schema_paths = repr(schema_result).upper()
    assert "ROLES" in schema_paths
    assert "ACTIONS" in schema_paths


def test_runner_executes_four_arms_for_every_world_and_uses_independent_workers(
    public_fixture: dict[str, Any], result: dict[str, Any]
) -> None:
    assert result.get("world_count") == 12
    runs = _runs(result)
    by_world: dict[str, set[str]] = {}
    for run in runs:
        world_id = run.get("world_id")
        arm = str(run.get("arm", ""))
        marker = _arm_marker(arm)
        assert marker is not None, f"unrecognized arm: {arm!r}"
        by_world.setdefault(str(world_id), set()).add(marker)
    expected_ids = {world["world_id"] for world in _worlds(public_fixture)}
    assert set(by_world) == expected_ids
    assert all(markers == set(REQUIRED_ARM_MARKERS) for markers in by_world.values())

    processes = result.get("worker_processes")
    if isinstance(processes, int):
        assert processes >= 2
    else:
        assert isinstance(processes, (list, dict))
        process_ids = {
            value
            for path, value in _walk(processes)
            if path and path[-1].lower() in {"pid", "process_id"}
        }
        assert len(process_ids) >= 2


def test_controller_and_methods_never_receive_all_owner_keys(result: dict[str, Any]) -> None:
    security = result.get("security")
    assert isinstance(security, dict), "runner must publish key-custody evidence"
    assert security.get("controller_received_owner_keys") is False
    assert security.get("methods_received_owner_keys") is False
    assert security.get("key_material_exported") is False
    key_processes = security.get("owner_key_processes")
    assert isinstance(key_processes, dict) and len(key_processes) >= 3
    pids = {
        value.get("pid") if isinstance(value, dict) else value
        for value in key_processes.values()
    }
    assert None not in pids
    assert len(pids) >= 2

    forbidden_names = {
        "private_key",
        "private_keys",
        "owner_key",
        "owner_keys",
        "signing_secret",
        "key_material",
    }
    leaks = []
    for path, value in _walk(result):
        if path and path[-1].lower() in forbidden_names and value not in (None, False, [], {}):
            leaks.append(".".join(path))
    assert leaks == [], f"result exported owner key material: {leaks}"

    controller_sources = [
        ROOT / "runner.py",
        ROOT / "g2o1" / "methods.py",
        ROOT / "workers" / "method_worker.py",
    ]
    forbidden_source_tokens = ("PrincipalActor(", "_private_seed(", "from_private_bytes(")
    for source in controller_sources:
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden_source_tokens), (
            f"{source.relative_to(ROOT)} can instantiate/reconstruct owner keys"
        )


def test_axes_and_diagnostics_are_separate_and_complete(result: dict[str, Any]) -> None:
    for run in _runs(result):
        axes = run.get("axes")
        diagnostics = run.get("diagnostics")
        assert isinstance(axes, dict)
        assert set(axes) == AXES
        assert all(isinstance(value, bool) for value in axes.values())
        assert isinstance(diagnostics, dict)
        assert DIAGNOSTICS <= set(diagnostics)


def test_oracle_expected_answers_are_not_an_execution_input(
    tmp_path: Path, result: dict[str, Any]
) -> None:
    oracle = _load(PRIVATE_ORACLE)
    mutated = copy.deepcopy(oracle)
    worlds = mutated.get("worlds")
    assert isinstance(worlds, dict) and worlds
    for world in worlds.values():
        assert isinstance(world, dict)
        expected = world.get("expected")
        assert isinstance(expected, dict)
        axes = expected.get("axes")
        assert isinstance(axes, dict) and set(axes) == AXES
        expected["axes"] = {name: not value for name, value in axes.items()}
        expected["diagnostics"] = {"attack_mutation": "MUST_NOT_DRIVE_EXECUTION"}
    mutated_path = tmp_path / "oracle-expected-inverted.json"
    mutated_path.write_text(
        json.dumps(mutated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rerun = _run(tmp_path, oracle=mutated_path, name="expected-inverted.json")

    def measured(document: dict[str, Any]) -> dict[tuple[str, str], tuple[Any, Any]]:
        return {
            (str(run["world_id"]), str(run["arm"])): (
                run.get("axes"),
                run.get("diagnostics"),
            )
            for run in _runs(document)
        }

    assert measured(rerun) == measured(result)


def test_owner_evidence_distinguishes_digest_understanding_refusal_and_opposition(
    result: dict[str, Any],
) -> None:
    saw_wrong_understanding = False
    saw_understood_refusal = False
    saw_partial = False
    saw_silence = False
    saw_opposition = False
    for run in _runs(result):
        events = run.get("owner_events", [])
        axes = run["axes"]
        required = set(run["method_output"].get("required_principals", []))
        understanding_events = [
            event
            for event in events
            if event.get("action") == "UNDERSTANDING"
            and event.get("principal_id") in required
        ]
        stance_events = [
            event
            for event in events
            if event.get("action") == "STANCE"
            and event.get("principal_id") in required
        ]
        if any(
            event.get("body", {}).get("correctness") is False
            for event in understanding_events
        ):
            saw_wrong_understanding = True
            assert axes["understood"] is False
        refusal_events = [
            event
            for event in stance_events
            if str(event.get("body", {}).get("stance", "")).upper()
            in {"REFUSE", "OPPOSE", "WITHDRAW"}
        ]
        if refusal_events and len(understanding_events) == len(required) and all(
            event.get("body", {}).get("correctness") is True
            for event in understanding_events
        ):
            saw_understood_refusal = True
            assert axes["understood"] is True
            assert axes["claimed"] is False
        stance_principals = {event["principal_id"] for event in stance_events}
        if required - stance_principals:
            saw_silence = True
            assert axes["claimed"] is False
        if any(
            str(event.get("body", {}).get("stance", "")).upper() == "PARTIAL"
            for event in stance_events
        ):
            saw_partial = True
        opposition_events = [
            event
            for event in events
            if event.get("action") == "OPPOSITION"
            or (
                event.get("action") == "STANCE"
                and str(event.get("body", {}).get("stance", "")).upper()
                in {"OPPOSE", "PARTIAL", "REFUSE"}
            )
        ]
        if opposition_events:
            saw_opposition = True
            provenance = run["diagnostics"]["provenance_opposition"]
            assert provenance.get("required_opposition_events", 0) > 0
            assert provenance.get("round_trip") is True
    assert saw_wrong_understanding
    assert saw_understood_refusal
    assert saw_partial
    assert saw_silence
    assert saw_opposition


def test_column_absent_and_withheld_are_not_collapsed(result: dict[str, Any]) -> None:
    observed: dict[str, set[str]] = {"ABSENT": set(), "WITHHELD": set()}
    for run in _runs(result):
        diagnostic = run["diagnostics"]["private_column_recall"]
        assert isinstance(diagnostic, dict)
        status = str(diagnostic.get("status", "")).upper()
        for state in observed:
            if status == state:
                observed[state].add(
                    json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)
                )
    assert observed["ABSENT"], "no ABSENT column result was measured"
    assert observed["WITHHELD"], "no WITHHELD column result was measured"
    assert observed["ABSENT"] != observed["WITHHELD"]


def test_stale_revoke_duplicate_partition_and_equivocation_fail_closed(
    result: dict[str, Any],
) -> None:
    seen = {"STALE": False, "REVOK": False, "DUPLICATE": False, "PARTITION": False, "EQUIVOC": False}
    for run in _runs(result):
        axes = run["axes"]
        diagnostics = run["diagnostics"]
        stale_revoke = diagnostics["stale_revoke"]
        duplicate = diagnostics["duplicate_reservation"]
        recovery = diagnostics["partition_recovery"]
        assert isinstance(stale_revoke, dict)
        assert isinstance(duplicate, dict)
        assert isinstance(recovery, dict)
        if stale_revoke.get("stale_present") is True:
            seen["STALE"] = True
            assert axes["authorized"] is False
            assert run["method_output"].get("fail_closed") is True
        if stale_revoke.get("revoked_present") is True:
            seen["REVOK"] = True
            assert axes["authorized"] is False
            assert run["method_output"].get("fail_closed") is True
        if duplicate.get("duplicate_present") is True:
            seen["DUPLICATE"] = True
            assert axes["authorized"] is False
            assert run["method_output"].get("fail_closed") is True
        event_text = _events_text(run)
        if "PARTITION" in event_text:
            seen["PARTITION"] = True
            assert recovery.get("pressure_present") is True
            assert recovery.get("fail_closed_or_recoverable") is True
        if "EQUIVOC" in event_text:
            seen["EQUIVOC"] = True
            assert recovery.get("pressure_present") is True
            assert recovery.get("fail_closed_or_recoverable") is True
    assert all(seen.values()), f"missing adversarial coverage: {seen}"


def test_authority_topology_and_state_placement_are_orthogonal(
    public_fixture: dict[str, Any], result: dict[str, Any]
) -> None:
    topology_by_world = {
        world["world_id"]: str(world.get("authority_topology", "")).upper()
        for world in _worlds(public_fixture)
    }
    assert any("SHARED" in value for value in topology_by_world.values())
    assert any("PLURAL" in value for value in topology_by_world.values())

    placements_by_world: dict[str, set[str]] = {}
    for run in _runs(result):
        method_output = run.get("method_output")
        assert isinstance(method_output, dict)
        topology = str(method_output.get("authority_topology", "")).upper()
        placement = str(method_output.get("state_placement", "")).upper()
        expected_topology = topology_by_world[str(run["world_id"])]
        assert topology == expected_topology
        assert topology
        assert placement
        placements_by_world.setdefault(str(run["world_id"]), set()).add(placement)

    for world_id, placements in placements_by_world.items():
        assert any("CENTRAL" in value for value in placements), world_id
        assert any("REPLICAT" in value for value in placements), world_id


def test_t5_controls_use_platform_direct_without_relation_artifacts(
    public_fixture: dict[str, Any], result: dict[str, Any]
) -> None:
    family_by_world = {
        world["world_id"]: _family(world) for world in _worlds(public_fixture)
    }
    t5_runs = [
        run
        for run in _runs(result)
        if family_by_world[str(run["world_id"])] == "T5"
    ]
    assert len(t5_runs) == 2 * len(REQUIRED_ARM_MARKERS)
    for run in t5_runs:
        output = run.get("method_output")
        assert isinstance(output, dict)
        assert output.get("platform_direct") is True
        assert output.get("relation_artifact_created") is False
        assert output.get("schema_reopen") is False
        assert output.get("schema_deltas") == []
        assert output.get("formed_schema_ids") == []
        assert output.get("proposed_schema") == {}
        assert not any(
            name in output
            for name in (
                "institutional_artifact",
                "central_decision_record",
                "mature_components",
                "replicated_state",
            )
        )
        assert run["diagnostics"]["cost"]["operations"] == 4


def test_false_formation_cannot_be_hidden_in_one_green_status(
    public_fixture: dict[str, Any], result: dict[str, Any]
) -> None:
    family_by_world = {
        world["world_id"]: _family(world) for world in _worlds(public_fixture)
    }
    for run in _runs(result):
        axes = run["axes"]
        output = run.get("method_output")
        assert isinstance(output, dict)
        status = str(output.get("status", output.get("decision", ""))).upper()
        family = family_by_world[str(run["world_id"])]
        if "T5" not in family and (not axes["claimed"] or not axes["constituted"]):
            assert status not in {"FORMED", "ACTIVE", "EXECUTION_READY", "GREEN", "PASS"}
            assert output.get("fail_closed") is True
