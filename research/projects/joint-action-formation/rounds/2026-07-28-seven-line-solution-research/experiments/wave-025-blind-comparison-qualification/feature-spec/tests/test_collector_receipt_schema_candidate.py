from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator


FEATURE_SPEC_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ROOT = FEATURE_SPEC_ROOT.parent
SCHEMA_PATH = FEATURE_SPEC_ROOT / "COLLECTOR-RECEIPT-V1.candidate.schema.json"
COLLECTOR_SOURCE_PATH = EXPERIMENT_ROOT / "attackers" / "leak-only-collector" / "collector.js"
F_RUN_ROOT = EXPERIMENT_ROOT / "runs" / "smoke-v13-20260801-f"
F_CLOSED_PATH = F_RUN_ROOT / "closed.json"
F_PRECOMMIT_PATH = F_RUN_ROOT / "precommit.json"
F_SLOTS_ROOT = F_RUN_ROOT / "slots"

EXPECTED_SCHEMA_SHA256 = "a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209"
EXPECTED_COLLECTOR_SOURCE_SHA256 = "bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699"
EXPECTED_F_CLOSED_SHA256 = "26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e"
EXPECTED_F_PRECOMMIT_SHA256 = "d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e"

Mutation = Callable[[dict[str, Any]], None]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def f_receipt_paths() -> list[Path]:
    return sorted(F_SLOTS_ROOT.glob("*/collector-features.json"))


def normalized_error(receipt: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(receipt["timing"]["error_shape_probes"][0]["error"])


def changed(receipt: dict[str, Any], mutation: Mutation) -> dict[str, Any]:
    candidate = copy.deepcopy(receipt)
    mutation(candidate)
    return candidate


def first_tree_entry(receipt: dict[str, Any], entry_type: str) -> dict[str, Any]:
    for tree in receipt["directory_trees"].values():
        for entry in tree["entries"]:
            if entry["type"] == entry_type:
                return entry
    raise AssertionError(f"F fixture has no tree entry of type {entry_type}")


def legal_branch_cases(receipt: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    error = normalized_error(receipt)
    cases: list[tuple[str, dict[str, Any]]] = []

    cases.append(
        (
            "os_hostname_failure",
            changed(
                receipt,
                lambda value: value["hostname"].__setitem__(
                    "os_hostname",
                    {"ok": False, "value": None, "error": copy.deepcopy(error)},
                ),
            ),
        )
    )
    cases.append(
        (
            "etc_hostname_failure",
            changed(
                receipt,
                lambda value: value["hostname"].__setitem__(
                    "etc_hostname", {"error": copy.deepcopy(error)}
                ),
            ),
        )
    )
    cases.append(
        (
            "user_info_failure",
            changed(
                receipt,
                lambda value: value["identity"].__setitem__(
                    "user_info", {"error": copy.deepcopy(error)}
                ),
            ),
        )
    )
    cases.append(
        (
            "tree_unavailable",
            changed(
                receipt,
                lambda value: value["directory_trees"].__setitem__(
                    "tmp",
                    {"available": False, "entries": [], "errors": [], "truncated": False},
                ),
            ),
        )
    )
    cases.append(
        (
            "process_view_unavailable",
            changed(
                receipt,
                lambda value: value.__setitem__(
                    "process_view",
                    {"available": False, "processes": [], "self": None, "truncated": False},
                ),
            ),
        )
    )
    cases.append(
        (
            "process_view_read_error",
            changed(
                receipt,
                lambda value: value.__setitem__(
                    "process_view",
                    {
                        "available": False,
                        "processes": [],
                        "self": None,
                        "truncated": False,
                        "error": copy.deepcopy(error),
                    },
                ),
            ),
        )
    )

    def process_entry_error(value: dict[str, Any]) -> None:
        pid = value["process_view"]["processes"][0]["pid"]
        value["process_view"]["processes"][0] = {
            "pid": pid,
            "error": copy.deepcopy(error),
        }

    cases.append(("process_entry_error", changed(receipt, process_entry_error)))
    cases.append(
        (
            "process_self_file_error",
            changed(
                receipt,
                lambda value: value["process_view"]["self"].__setitem__(
                    "status", {"error": copy.deepcopy(error)}
                ),
            ),
        )
    )
    cases.append(
        (
            "process_status_partial_or_empty",
            changed(
                receipt,
                lambda value: value["process_view"]["processes"][0].__setitem__("status", {}),
            ),
        )
    )
    cases.append(
        (
            "uptime_capture_failure",
            changed(
                receipt,
                lambda value: value["timing"].__setitem__(
                    "process_uptime_seconds",
                    {"ok": False, "value": None, "error": copy.deepcopy(error)},
                ),
            ),
        )
    )
    cases.append(
        (
            "timing_probe_success",
            changed(
                receipt,
                lambda value: value["timing"]["error_shape_probes"].__setitem__(
                    2,
                    {
                        "name": "read-challenge-directory-as-file",
                        "ok": True,
                        "elapsed_ns": "1",
                        "error": None,
                    },
                ),
            ),
        )
    )
    assert len(cases) == 11
    return cases


def invalid_mutation_cases(
    receipt: dict[str, Any], canary_receipt: dict[str, Any]
) -> list[tuple[str, dict[str, Any]]]:
    error = normalized_error(receipt)
    cases: list[tuple[str, dict[str, Any]]] = []

    cases.append(("unknown_top", changed(receipt, lambda value: value.__setitem__("role", "R"))))
    cases.append(("missing_top", changed(receipt, lambda value: value.pop("cwd"))))
    cases.append(
        (
            "unknown_nested",
            changed(receipt, lambda value: value["contract"].__setitem__("score", 0)),
        )
    )
    cases.append(
        (
            "duplicate_environment_item",
            changed(
                receipt,
                lambda value: value["environment"].append(copy.deepcopy(value["environment"][0])),
            ),
        )
    )
    cases.append(
        (
            "os_hostname_union_contradiction",
            changed(
                receipt,
                lambda value: value["hostname"]["os_hostname"].__setitem__(
                    "error", copy.deepcopy(error)
                ),
            ),
        )
    )
    cases.append(
        (
            "etc_hostname_wrong_capture_shape",
            changed(
                receipt,
                lambda value: value["hostname"].__setitem__(
                    "etc_hostname", {"ok": True, "value": "h", "error": None}
                ),
            ),
        )
    )
    cases.append(
        (
            "user_info_union_contradiction",
            changed(
                receipt,
                lambda value: value["identity"]["user_info"].__setitem__(
                    "error", copy.deepcopy(error)
                ),
            ),
        )
    )

    def nonsymlink_with_target(value: dict[str, Any]) -> None:
        first_tree_entry(value, "file")["symlink_target"] = "unexpected"

    cases.append(("nonsymlink_with_target", changed(receipt, nonsymlink_with_target)))

    def symlink_without_target(value: dict[str, Any]) -> None:
        first_tree_entry(value, "symlink").pop("symlink_target")

    cases.append(("symlink_without_target", changed(receipt, symlink_without_target)))
    cases.append(
        (
            "tree_unavailable_with_entries",
            changed(
                receipt,
                lambda value: value["directory_trees"]["tmp"].__setitem__("available", False),
            ),
        )
    )
    cases.append(
        (
            "duplicate_tree_entry",
            changed(
                receipt,
                lambda value: value["directory_trees"]["tmp"]["entries"].append(
                    copy.deepcopy(value["directory_trees"]["tmp"]["entries"][0])
                ),
            ),
        )
    )
    cases.append(
        (
            "process_success_error_mix",
            changed(
                receipt,
                lambda value: value["process_view"]["processes"][0].__setitem__(
                    "error", copy.deepcopy(error)
                ),
            ),
        )
    )
    cases.append(
        (
            "process_uid_space_vector",
            changed(
                receipt,
                lambda value: value["process_view"]["processes"][0]["status"].__setitem__(
                    "uid", "65534 65534 65534 65534"
                ),
            ),
        )
    )
    cases.append(
        (
            "process_uid_three_tab_fields",
            changed(
                receipt,
                lambda value: value["process_view"]["processes"][0]["status"].__setitem__(
                    "uid", "65534\t65534\t65534"
                ),
            ),
        )
    )
    cases.append(
        (
            "self_digest_union_contradiction",
            changed(
                receipt,
                lambda value: value["process_view"]["self"]["status"].__setitem__(
                    "error", copy.deepcopy(error)
                ),
            ),
        )
    )
    cases.append(
        (
            "uptime_capture_contradiction",
            changed(
                receipt,
                lambda value: value["timing"].__setitem__(
                    "process_uptime_seconds",
                    {"ok": False, "value": 1, "error": copy.deepcopy(error)},
                ),
            ),
        )
    )

    def swap_probes(value: dict[str, Any]) -> None:
        probes = value["timing"]["error_shape_probes"]
        probes[0], probes[1] = probes[1], probes[0]

    cases.append(("probe_order_swapped", changed(receipt, swap_probes)))
    cases.append(
        (
            "timing_vector_short",
            changed(receipt, lambda value: value["timing"]["immediate_delta_ns"].pop()),
        )
    )
    cases.append(
        (
            "collection_unknown",
            changed(
                receipt,
                lambda value: value["collection_window"]["start"].__setitem__("host_order", 1),
            ),
        )
    )
    cases.append(
        (
            "normalized_error_missing_field",
            changed(
                receipt,
                lambda value: value["timing"]["error_shape_probes"][0]["error"].pop("path"),
            ),
        )
    )
    cases.append(
        (
            "duplicate_visible_canary",
            changed(
                canary_receipt,
                lambda value: value["visible_canaries"].append(
                    copy.deepcopy(value["visible_canaries"][0])
                ),
            ),
        )
    )
    assert len(cases) == 21
    return cases


def iter_schema_nodes(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from iter_schema_nodes(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_schema_nodes(child, f"{path}/{index}")


def test_schema_source_and_f_receipt_manifests_are_bound() -> None:
    assert sha256_file(SCHEMA_PATH) == EXPECTED_SCHEMA_SHA256
    assert sha256_file(COLLECTOR_SOURCE_PATH) == EXPECTED_COLLECTOR_SOURCE_SHA256
    assert sha256_file(F_CLOSED_PATH) == EXPECTED_F_CLOSED_SHA256
    assert sha256_file(F_PRECOMMIT_PATH) == EXPECTED_F_PRECOMMIT_SHA256

    precommit = load_json(F_PRECOMMIT_PATH)
    closed = load_json(F_CLOSED_PATH)
    assert precommit["collector_source_sha256"] == EXPECTED_COLLECTOR_SOURCE_SHA256
    assert closed["precommit_sha256"] == EXPECTED_F_PRECOMMIT_SHA256
    assert closed["expected_slot_count"] == 12
    assert closed["actual_slot_directory_count"] == 12
    assert len(closed["slots"]) == 12

    manifested_ids: set[str] = set()
    for slot in closed["slots"]:
        slot_id = slot["opaque_slot_id"]
        assert slot_id not in manifested_ids
        manifested_ids.add(slot_id)
        slot_root = F_SLOTS_ROOT / slot_id
        slot_receipt_path = slot_root / "slot-receipt.json"
        collector_receipt_path = slot_root / "collector-features.json"
        assert sha256_file(slot_receipt_path) == slot["files"]["slot-receipt.json"]
        assert sha256_file(collector_receipt_path) == slot["files"]["collector-features.json"]
        slot_receipt = load_json(slot_receipt_path)
        assert slot_receipt["schema"] == "WAVE025_SLOT_RECEIPT_V1"
        assert slot_receipt["opaque_slot_id"] == slot_id
        assert slot_receipt["infrastructure_classification"] == "COMPLETE"
        assert (
            slot_receipt["files"]["collector-features.json"]
            == slot["files"]["collector-features.json"]
        )

    assert manifested_ids == {path.parent.name for path in f_receipt_paths()}


def test_meta_schema_and_every_declared_object_is_closed() -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    for path, node in iter_schema_nodes(schema):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, path


def test_all_twelve_f_receipts_validate_without_writing_f() -> None:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    paths = f_receipt_paths()
    assert len(paths) == 12
    before = {path: sha256_file(path) for path in paths}
    for path in paths:
        validator.validate(load_json(path))
    after = {path: sha256_file(path) for path in paths}
    assert after == before


def test_eleven_source_reachable_legal_branches_validate() -> None:
    validator = Draft202012Validator(load_json(SCHEMA_PATH))
    receipt = load_json(f_receipt_paths()[0])
    cases = legal_branch_cases(receipt)
    assert len(cases) == 11
    for name, candidate in cases:
        errors = list(validator.iter_errors(candidate))
        assert not errors, f"legal source branch rejected: {name}: {errors[0].message if errors else ''}"


def test_twenty_one_fixed_invalid_mutations_are_rejected() -> None:
    validator = Draft202012Validator(load_json(SCHEMA_PATH))
    receipts = [load_json(path) for path in f_receipt_paths()]
    receipt = receipts[0]
    canary_receipt = next(value for value in receipts if value["visible_canaries"])
    cases = invalid_mutation_cases(receipt, canary_receipt)
    assert len(cases) == 21
    for name, candidate in cases:
        errors = list(validator.iter_errors(candidate))
        assert errors, f"invalid mutation accepted: {name}"
