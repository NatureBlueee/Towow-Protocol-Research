from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import jsonschema
import pytest


FEATURE_SPEC = Path(__file__).resolve().parents[1]
WAVE = FEATURE_SPEC.parent
RUN_F = WAVE / "runs" / "smoke-v13-20260801-f" / "slots"

sys.path.insert(0, str(FEATURE_SPEC))
import routing_v2s_coverage as coverage


ROUTING_BYTES = coverage.DEFAULT_ROUTING.read_bytes()
ROUTING_SCHEMA_BYTES = coverage.DEFAULT_ROUTING_SCHEMA.read_bytes()
RECEIPT_SCHEMA_BYTES = coverage.DEFAULT_RECEIPT_SCHEMA.read_bytes()
PRIMITIVES_BYTES = coverage.DEFAULT_PRIMITIVES.read_bytes()
ROUTING = json.loads(ROUTING_BYTES)
ROUTING_SCHEMA = json.loads(ROUTING_SCHEMA_BYTES)
RECEIPT_SCHEMA = json.loads(RECEIPT_SCHEMA_BYTES)
PRIMITIVES = json.loads(PRIMITIVES_BYTES)
F_RECEIPTS = sorted(RUN_F.glob("*/collector-features.json"))


def row(route_id: str, routing=ROUTING):
    return next(item for item in routing["rows"] if item["id"] == route_id)


def spec(spec_id: str, routing=ROUTING):
    return next(item for item in routing["pseudo_event_specs"] if item["id"] == spec_id)


def canonical(value) -> bytes:
    return coverage.canonical_bytes(value)


def refresh_matrix(routing) -> None:
    matrix = coverage.derive_channel_stat_matrix(routing)
    routing["channel_stat_matrix"]["entry_count"] = len(matrix)
    routing["channel_stat_matrix"]["sha256"] = coverage.sha256_bytes(canonical(matrix))


def bind_receipt_schema(routing, receipt_schema_bytes: bytes) -> None:
    routing["input_schema"]["sha256"] = coverage.sha256_bytes(receipt_schema_bytes)
    routing["input_schema"]["byte_length"] = len(receipt_schema_bytes)


def verify(
    routing=ROUTING,
    *,
    routing_bytes: bytes | None = None,
    routing_schema_bytes: bytes = ROUTING_SCHEMA_BYTES,
    receipt_schema_bytes: bytes = RECEIPT_SCHEMA_BYTES,
    primitives_bytes: bytes = PRIMITIVES_BYTES,
):
    return coverage.verify_candidate_bytes(
        canonical(routing) if routing_bytes is None else routing_bytes,
        routing_schema_bytes,
        receipt_schema_bytes,
        primitives_bytes,
    )


def first_tree_entry(receipt):
    for tree in receipt["directory_trees"].values():
        if isinstance(tree, dict) and tree.get("entries"):
            return tree["entries"][0]
    raise AssertionError("fixture has no tree entry")


def test_candidate_is_canonical_and_exactly_binds_actual_schema_and_primitives_bytes():
    assert ROUTING_BYTES == canonical(ROUTING)
    assert ROUTING_SCHEMA_BYTES == canonical(ROUTING_SCHEMA)
    assert ROUTING["input_schema"]["sha256"] == coverage.sha256_bytes(RECEIPT_SCHEMA_BYTES)
    assert ROUTING["input_schema"]["byte_length"] == len(RECEIPT_SCHEMA_BYTES)
    assert ROUTING["primitives_binding"]["sha256"] == coverage.sha256_bytes(PRIMITIVES_BYTES)
    assert ROUTING["primitives_binding"]["byte_length"] == len(PRIMITIVES_BYTES)
    assert ROUTING["primitives_binding"]["sha256"] == "2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b"
    assert len(PRIMITIVES_BYTES) == 12178


def test_candidate_schema_and_generated_manifests_have_exact_structural_ownership():
    _, _, report = verify()
    assert report == {
        "route_count": 109,
        "family_counts": {
            "F01_PUBLIC_INPUT_BYTES": 9,
            "F02_ARGV_ENV_CWD": 7,
            "F03_HOSTNAME_IDENTITY": 21,
            "F04_DIRECTORY_AND_SHARED_STATE": 16,
            "F05_PROCESS_NAMESPACE_FD": 31,
            "F06_TIMING_AND_ERRORS": 19,
            "F07_VISIBLE_CANARY": 6,
        },
        "manifest_leaf_variants": 454,
        "manifest_unique_path_atom": 371,
        "unowned": [],
        "multiply_owned": [],
        "pseudo_event_spec_counts": {
            "UNION_BRANCH": 9,
            "CONTAINER": 7,
            "CLOSED_RECORD": 5,
            "ABSENCE": 3,
        },
        "channel_stat_matrix_entries": 641,
        "bag_numeric_identity_owners": 1140,
        "structural_ownership": "PASS",
        "admission_or_semantic_completeness": "NOT_PROVEN",
    }


@pytest.mark.parametrize("receipt_path", F_RECEIPTS, ids=lambda path: path.parent.name)
def test_each_of_twelve_f_receipts_has_zero_runtime_routing_failures(receipt_path: Path):
    assert len(F_RECEIPTS) == 12
    result = coverage.classify_receipt(ROUTING, RECEIPT_SCHEMA, coverage.load_json(receipt_path))
    assert result["status"] == "ZERO_UNCLASSIFIED"
    assert (result["scalar_leaf_count"], result["pseudo_event_count"]) in {(528, 71), (547, 74)}
    assert result["unknown"] == []
    assert result["multiply_owned"] == []
    assert result["scalar_one_identity_collisions"] == []
    assert result["admission_or_semantic_completeness"] == "NOT_PROVEN"


def test_named_capture_grammar_constructs_distinct_exact_ctx2_bytes():
    target = row("R028")
    pid = coverage.resolve_context(target, coverage.match_pattern(target["path_pattern"], "/identity/pid"), "ROW")
    ppid = coverage.resolve_context(target, coverage.match_pattern(target["path_pattern"], "/identity/ppid"), "ROW")
    assert pid != ppid
    assert pid.startswith(coverage.frame32(b"WAVE025_CONTEXT_V2S"))
    tree = row("R038")
    contexts = {
        coverage.resolve_context(tree, coverage.match_pattern(tree["path_pattern"], f"/directory_trees/{name}"), "ROW")
        for name in ["challenge", "cwd", "out", "tmp", "self-fd"]
    }
    assert len(contexts) == 5


def test_ordered_index_is_preserved_only_in_ordered_views():
    target = row("R064")
    zero = coverage.match_pattern(target["path_pattern"], "/process_view/processes/0/cmdline/0")
    one = coverage.match_pattern(target["path_pattern"], "/process_view/processes/0/cmdline/1")
    assert coverage.resolve_context(target, zero, "ORDERED") != coverage.resolve_context(target, one, "ORDERED")
    assert coverage.resolve_context(target, zero, "BAG") == coverage.resolve_context(target, one, "BAG")
    assert coverage.resolve_context(target, zero, "LEXICAL_BAG") == coverage.resolve_context(target, one, "LEXICAL_BAG")


@pytest.mark.parametrize(
    ("route_id", "first", "second", "different_parent"),
    [
        ("R032", "/identity/groups/0", "/identity/groups/1", None),
        (
            "R093",
            "/timing/immediate_delta_ns/0",
            "/timing/immediate_delta_ns/1",
            "/timing/input_stat_elapsed_ns/0",
        ),
    ],
)
def test_parent_view_drops_item_index_but_keeps_series_identity(route_id, first, second, different_parent):
    target = row(route_id)
    first_captures = coverage.match_pattern(target["path_pattern"], first)
    second_captures = coverage.match_pattern(target["path_pattern"], second)
    assert coverage.resolve_context(target, first_captures, "ORDERED") != coverage.resolve_context(target, second_captures, "ORDERED")
    assert coverage.resolve_context(target, first_captures, "PARENT") == coverage.resolve_context(target, second_captures, "PARENT")
    if different_parent is not None:
        other_captures = coverage.match_pattern(target["path_pattern"], different_parent)
        assert coverage.resolve_context(target, first_captures, "PARENT") != coverage.resolve_context(target, other_captures, "PARENT")


def test_legacy_placeholders_are_absent_from_all_context_templates():
    assert all("$" not in segment for item in ROUTING["rows"] for segment in item["context_segments"])


def test_unbound_context_capture_fails_closed():
    mutant = copy.deepcopy(ROUTING)
    row("R028", mutant)["context_segments"][1] = "KEY:{unknown}"
    with pytest.raises(coverage.CoverageError, match="unbound context capture"):
        verify(mutant)


@pytest.mark.parametrize("replacement", [None, "KEY:collapsed"])
def test_deleting_or_literalizing_a_required_capture_reference_fails_statically(replacement):
    mutant = copy.deepcopy(ROUTING)
    target = row("R028", mutant)
    if replacement is None:
        del target["context_segments"][1]
    else:
        target["context_segments"][1] = replacement
    with pytest.raises(coverage.CoverageError, match="required capture field"):
        verify(mutant)


def test_duplicate_named_path_capture_fails_closed():
    mutant = copy.deepcopy(ROUTING)
    row("R028", mutant)["path_pattern"] = "/identity/{field:pid|ppid}/{field:*}"
    with pytest.raises(coverage.CoverageError, match="duplicate capture"):
        verify(mutant)


def test_noncanonical_array_index_does_not_match_or_encode():
    target = row("R064")
    assert coverage.match_pattern(target["path_pattern"], "/process_view/processes/0/cmdline/01") is None
    with pytest.raises(coverage.CoverageError, match="noncanonical ORDERED"):
        coverage.resolve_context(target, {"item1": "0", "index": "01"}, "ORDERED")


def test_pseudo_specs_are_bijective_with_all_non_scalar_owner_rows():
    pseudo_rows = {item["id"] for item in ROUTING["rows"] if item["event_kind"] != "SCALAR_LEAF"}
    pseudo_owners = [item["owner_route_id"] for item in ROUTING["pseudo_event_specs"]]
    assert len(pseudo_owners) == len(set(pseudo_owners)) == 24
    assert set(pseudo_owners) == pseudo_rows


def test_removing_process_branch_owner_is_rejected():
    mutant = copy.deepcopy(ROUTING)
    mutant["rows"] = [item for item in mutant["rows"] if item["id"] != "R053"]
    with pytest.raises(coverage.CoverageError, match="owner route missing"):
        verify(mutant)


def test_duplicating_process_branch_owner_is_rejected():
    mutant = copy.deepcopy(ROUTING)
    duplicate = copy.deepcopy(row("R053", mutant))
    duplicate["id"] = "R999"
    mutant["rows"].append(duplicate)
    with pytest.raises(coverage.CoverageError, match="not bijective"):
        verify(mutant)


def test_misrouting_process_branch_owner_is_rejected():
    mutant = copy.deepcopy(ROUTING)
    row("R053", mutant)["path_pattern"] = "/invented/process_view"
    with pytest.raises(coverage.CoverageError, match="owner path_pattern mismatch"):
        verify(mutant)


def test_pseudo_selector_definition_mutation_breaks_exact_binding():
    mutant = copy.deepcopy(ROUTING)
    mutant["variant_registry"]["PROCESS_AVAILABLE"]["runtime_selector"] = {"op": "ALWAYS"}
    with pytest.raises(coverage.CoverageError, match="selector binding mismatch"):
        verify(mutant)


def test_every_pseudo_selector_binding_recomputes_from_referenced_registry_entries():
    for item in ROUTING["pseudo_event_specs"]:
        names = sorted({name for conjunction in item["variant_expression"]["any_of"] for name in conjunction})
        projection = {name: ROUTING["variant_registry"][name] for name in names}
        assert item["selector_binding_sha256"] == coverage.sha256_bytes(canonical(projection))


def test_pseudo_expected_universe_matches_frozen_schema_derived_digest():
    universe = coverage.derive_pseudo_expected_universe(ROUTING)
    assert len(universe) == coverage.EXPECTED_PSEUDO_UNIVERSE_COUNT == 24
    assert coverage.sha256_bytes(canonical(universe)) == coverage.EXPECTED_PSEUDO_UNIVERSE_SHA256
    assert ROUTING["pseudo_event_expected_universe"] == {
        "derivation": ROUTING["pseudo_event_expected_universe"]["derivation"],
        "entry_count": 24,
        "sha256": coverage.EXPECTED_PSEUDO_UNIVERSE_SHA256,
    }


def test_synchronized_extra_pseudo_row_spec_and_matrix_cannot_self_authorize():
    mutant = copy.deepcopy(ROUTING)
    duplicate_row = copy.deepcopy(row("R053", mutant))
    duplicate_row["id"] = "R999"
    mutant["rows"].append(duplicate_row)
    duplicate_spec = copy.deepcopy(spec("PBR005", mutant))
    duplicate_spec["id"] = "PBR999"
    duplicate_spec["owner_route_id"] = "R999"
    mutant["pseudo_event_specs"].append(duplicate_spec)
    refresh_matrix(mutant)
    attacker_universe = coverage.derive_pseudo_expected_universe(mutant)
    mutant["pseudo_event_expected_universe"]["entry_count"] = len(attacker_universe)
    mutant["pseudo_event_expected_universe"]["sha256"] = coverage.sha256_bytes(canonical(attacker_universe))

    # Even a caller-supplied schema loosened in the same mutation cannot change
    # the checker's separately frozen expected universe.
    attacker_schema = copy.deepcopy(ROUTING_SCHEMA)
    attacker_schema["properties"]["pseudo_event_specs"]["maxItems"] = 25
    binding_schema = attacker_schema["properties"]["pseudo_event_expected_universe"]["properties"]
    binding_schema["entry_count"] = {"type": "integer", "minimum": 1}
    binding_schema["sha256"] = {"$ref": "#/$defs/sha256"}
    with pytest.raises(coverage.CoverageError, match="pseudo expected universe"):
        verify(mutant, routing_schema_bytes=canonical(attacker_schema))


def test_nonexistent_closed_record_definition_cannot_replace_frozen_expected_record():
    mutant = copy.deepcopy(ROUTING)
    spec("PRE005", mutant)["schema_def"] = "#/$defs/DOES_NOT_EXIST"
    row("R104", mutant)["closed_projection"]["schema_def"] = "#/$defs/DOES_NOT_EXIST"
    with pytest.raises(coverage.CoverageError, match="pseudo expected universe"):
        verify(mutant)


def test_reachable_closed_record_definition_must_itself_be_closed():
    mutated_schema = copy.deepcopy(RECEIPT_SCHEMA)
    mutated_schema["$defs"]["environmentEntry"]["additionalProperties"] = True
    mutated_schema_bytes = canonical(mutated_schema)
    mutant = copy.deepcopy(ROUTING)
    bind_receipt_schema(mutant, mutated_schema_bytes)
    with pytest.raises(coverage.CoverageError, match="missing or open record definition"):
        verify(mutant, receipt_schema_bytes=mutated_schema_bytes)


def test_signed_zero_is_schema_legal_normalized_and_routed_as_integer():
    receipt = coverage.load_json(F_RECEIPTS[0])
    entry = first_tree_entry(receipt)
    entry["mtime_ns"] = "-0"
    jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(receipt)
    assert coverage.input_atom_for_value("-0", "/directory_trees/challenge/entries/0/mtime_ns") == "SIGNED_DECIMAL_INT_STRING"
    assert coverage.normalize_signed_decimal("-0") == "0"
    result = coverage.classify_receipt(ROUTING, RECEIPT_SCHEMA, receipt)
    assert result["status"] == "ZERO_UNCLASSIFIED"
    classified = next(item for item in result["classified"] if item["path"].endswith("/mtime_ns") and entry["mtime_ns"] == "-0")
    assert classified["row"] == "R109"


def test_signed_positive_timestamp_uses_the_same_explicit_signed_route():
    assert coverage.input_atom_for_value("17", "/directory_trees/challenge/entries/0/ctime_ns") == "SIGNED_DECIMAL_INT_STRING"
    assert coverage.normalize_signed_decimal("17") == "17"


def test_union_trace_changes_static_owner_selection():
    success = coverage.ManifestLeaf("/hostname/os_hostname/value", "UTF8_STRING", ("oneOf[0]",))
    wrong_branch = coverage.ManifestLeaf("/hostname/os_hostname/value", "UTF8_STRING", ("oneOf[1]",))
    null_branch = coverage.ManifestLeaf("/hostname/os_hostname/value", "JSON_NULL", ("oneOf[1]",))
    assert [item["id"] for item in coverage.matching_rows_static(ROUTING, success)] == ["R019"]
    assert coverage.matching_rows_static(ROUTING, wrong_branch) == []
    assert [item["id"] for item in coverage.matching_rows_static(ROUTING, null_branch)] == ["R020"]


def test_unknown_union_variant_label_is_rejected():
    mutant = copy.deepcopy(ROUTING)
    row("R019", mutant)["variant_expression"] = {"any_of": [["BOGUS_BRANCH"]]}
    with pytest.raises(coverage.CoverageError, match="unknown union variant"):
        verify(mutant)


@pytest.mark.parametrize(
    ("route_id", "expected"),
    [
        ("R068", {"EXACT_CATEGORY", "STRING_SHAPE", "LEXICAL_FULL_BYTE_LENGTH", "LEXICAL_TRUNCATED", "LEXICAL_NGRAM"}),
        ("R070", {"NUMERIC_SCALAR", "INTEGER_RESIDUE"}),
        ("R072", {"ORDERED_FOUR_ID_ITEMS", "ORDERED_FOUR_ID_SERIES", "INTEGER_RESIDUE"}),
    ],
)
def test_missing_routes_name_exact_expected_channels_and_stats(route_id: str, expected: set[str]):
    target = row(route_id)
    assert {channel["expected_channel"] for channel in target["channels"]} == expected
    for channel in target["channels"]:
        assert channel["channel"] == "MISSING"
        assert channel["expected_stats"] == ROUTING["channel_stat_registry"][channel["expected_channel"]]["stats"]


def test_missing_channel_without_expected_channel_is_schema_rejected():
    mutant = copy.deepcopy(ROUTING)
    del row("R070", mutant)["channels"][0]["expected_channel"]
    with pytest.raises(coverage.CoverageError, match="routing schema failure"):
        verify(mutant)


def test_missing_channel_with_wrong_expected_stats_is_rejected():
    mutant = copy.deepcopy(ROUTING)
    row("R070", mutant)["channels"][0]["expected_stats"] = ["wrong.stat"]
    with pytest.raises(coverage.CoverageError, match="expected_stats mismatch"):
        verify(mutant)


def test_missing_field_capture_prevents_name_state_identity_collapse():
    target = row("R068")
    name = coverage.resolve_context(target, coverage.match_pattern(target["path_pattern"], "/process_view/processes/0/status/name"), "BAG")
    state = coverage.resolve_context(target, coverage.match_pattern(target["path_pattern"], "/process_view/processes/0/status/state"), "BAG")
    assert name != state


def test_checker_hashes_actual_passed_receipt_schema_bytes():
    mutated_schema = copy.deepcopy(RECEIPT_SCHEMA)
    del mutated_schema["properties"]["cwd"]
    mutated_schema_bytes = canonical(mutated_schema)
    with pytest.raises(coverage.CoverageError, match="input_schema exact byte binding mismatch"):
        verify(receipt_schema_bytes=mutated_schema_bytes)


def test_checker_hashes_actual_passed_primitives_bytes():
    mutated_primitives = copy.deepcopy(PRIMITIVES)
    mutated_primitives["candidate_status"] = "ATTACKER_REPLACEMENT"
    with pytest.raises(coverage.CoverageError, match="primitives_binding exact byte binding mismatch"):
        verify(primitives_bytes=canonical(mutated_primitives))


def test_sha_routes_enforce_exact_category_allowlist_not_transform_name_heuristics():
    mutant = copy.deepcopy(ROUTING)
    row("R002", mutant)["channels"].append({"channel": "DIGEST_PREFIX", "transform": "HEX_PREFIX_8", "context": "ROW"})
    with pytest.raises(coverage.CoverageError, match="SHA exact-only allowlist"):
        verify(mutant)


def test_recursive_wildcard_is_forbidden_on_include_rows():
    mutant = copy.deepcopy(ROUTING)
    row("R028", mutant)["path_pattern"] = "/identity/**"
    with pytest.raises(coverage.CoverageError, match="recursive pattern is not EXCLUDE"):
        verify(mutant)


def test_all_rows_and_primitives_share_the_full_seven_family_identifiers():
    expected = [
        "F01_PUBLIC_INPUT_BYTES",
        "F02_ARGV_ENV_CWD",
        "F03_HOSTNAME_IDENTITY",
        "F04_DIRECTORY_AND_SHARED_STATE",
        "F05_PROCESS_NAMESPACE_FD",
        "F06_TIMING_AND_ERRORS",
        "F07_VISIBLE_CANARY",
    ]
    assert ROUTING["families"] == expected
    assert ROUTING["primitives_binding"]["exact_families"] == expected
    assert PRIMITIVES["dependencies"]["routing_contract"]["exact_families"] == expected
    assert {item["family"] for item in ROUTING["rows"]} == set(expected)


def test_channel_stat_matrix_detects_channel_mutation():
    mutant = copy.deepcopy(ROUTING)
    row("R028", mutant)["channels"][0]["channel"] = "INTEGER_RESIDUE"
    with pytest.raises(coverage.CoverageError, match="channel/stat matrix binding mismatch"):
        verify(mutant)


def test_bag_numeric_identity_collision_is_rejected_even_with_refreshed_matrix():
    mutant = copy.deepcopy(ROUTING)
    duplicate = copy.deepcopy(row("R109", mutant))
    duplicate["id"] = "R999"
    mutant["rows"].append(duplicate)
    refresh_matrix(mutant)
    with pytest.raises(coverage.CoverageError, match="BAG exactly-one-input-channel collision"):
        verify(mutant)


def test_second_bag_input_channel_for_same_family_context_base_stat_is_rejected():
    mutant = copy.deepcopy(ROUTING)
    mutant["channel_stat_registry"]["ALT_NUMERIC"] = {"kind": "NUMERIC", "stats": ["value"]}
    row("R109", mutant)["channels"].append({"channel": "ALT_NUMERIC", "transform": "ATTACKER_ALT_VALUE", "context": "BAG"})
    refresh_matrix(mutant)
    with pytest.raises(coverage.CoverageError, match="BAG exactly-one-input-channel collision"):
        verify(mutant)


def test_pretty_printed_candidate_bytes_are_rejected():
    pretty = json.dumps(ROUTING, ensure_ascii=False, indent=2).encode("utf-8")
    with pytest.raises(coverage.CoverageError, match="not canonical compact"):
        verify(routing_bytes=pretty)


def test_pretty_printed_routing_schema_bytes_are_rejected():
    pretty_schema = json.dumps(ROUTING_SCHEMA, ensure_ascii=False, indent=2).encode("utf-8")
    with pytest.raises(coverage.CoverageError, match="routing schema is not canonical compact"):
        verify(routing_schema_bytes=pretty_schema)


def test_schema_valid_but_backwards_wall_clock_remains_structural_only_not_admitted():
    receipt = coverage.load_json(F_RECEIPTS[0])
    receipt["timing"]["wall_clock_end_ms"] = 0
    jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(receipt)
    result = coverage.classify_receipt(ROUTING, RECEIPT_SCHEMA, receipt)
    assert result["status"] == "ZERO_UNCLASSIFIED"
    assert result["admission_or_semantic_completeness"] == "NOT_PROVEN"


def test_candidate_does_not_claim_adoption_model_layout_g_or_independent_acceptance():
    assert ROUTING["candidate_status"] == "NOT_ADOPTED__NOT_FORMAL_CANON"
    limits = "\n".join(ROUTING["known_static_proof_limits"])
    assert "semantic admission" in limits
    assert "C01-C05 model" in limits
    assert " G " in limits
    assert "independent feature-provider" in limits
