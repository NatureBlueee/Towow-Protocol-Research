import base64
import hashlib
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path


FEATURE_SPEC = Path(__file__).resolve().parents[1]
ORACLE_PATH = FEATURE_SPEC / "v2s_primitives_oracle.py"
SPEC = importlib.util.spec_from_file_location("wave025_v2s_primitives_oracle", ORACLE_PATH)
ORACLE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ORACLE
SPEC.loader.exec_module(ORACLE)


def artifacts():
    return ORACLE.build_artifacts()


def golden_cases():
    golden = artifacts()["GOLDEN-V2S-PRIMITIVES.candidate.json"]
    return {case["case_id"]: case for case in golden["cases"]}


def test_all_four_candidate_json_files_are_oracle_exact_and_canonical():
    for filename, expected_object in artifacts().items():
        actual = (FEATURE_SPEC / filename).read_bytes()
        assert actual == ORACLE.canonical_json_bytes(expected_object)
        assert actual.endswith(b"\n")
        assert actual.count(b"\n") == 1
        assert json.loads(actual) == expected_object


def test_golden_binds_exact_primitives_and_non_authoritative_oracle_source():
    golden = artifacts()["GOLDEN-V2S-PRIMITIVES.candidate.json"]
    primitives_bytes = (FEATURE_SPEC / "V2S-PRIMITIVES.candidate.json").read_bytes()
    binding = golden["bindings"]["primitives_candidate"]
    assert binding["byte_length_u64"] == str(len(primitives_bytes))
    assert binding["sha256"] == hashlib.sha256(primitives_bytes).hexdigest()
    oracle_bytes = ORACLE_PATH.read_bytes()
    oracle_binding = golden["bindings"]["oracle_source"]
    assert oracle_binding["authoritative"] is False
    assert oracle_binding["sha256"] == hashlib.sha256(oracle_bytes).hexdigest()
    primitives = artifacts()["V2S-PRIMITIVES.candidate.json"]
    assert primitives["authority"]["oracle_authoritative"] is False
    assert primitives["candidate_status"] == "NOT_ADOPTED__NOT_FORMAL_CANON"


def test_typed_category_hard_constants_and_missing_channel_identity():
    case = golden_cases()["TYPED_STRING_NUMBER_NULL_MISSING"]
    rows = {row["label"]: row for row in case["expected"]["evaluations"]}
    assert rows["string"]["value_sha256"] == "fd49870273bf5b0816211d0e881dab5fd8af15505dc85bdaca1c356638b82f1c"
    assert rows["number"]["value_sha256"] == "15f43bbec9eaf2e6329b4cf8b48f0ed0e24dc53a911f758fbb67fcb8fc9fb3e7"
    assert rows["null"]["row_sha256"] == "ad3011609813cd082cc67a0936f143bd58cead5c7b94f885b019a656b5d13847"
    assert rows["missing"]["row_sha256"] == "d4a4d438b1321d4e548ab82ee82b5dcaec797321957ee90a4f45fe115b3fcdfe"
    assert rows["null"]["atom_hex"] == "00"
    assert rows["missing"]["atom_hex"] == "07"
    assert rows["missing"]["channel_identity_hex"] != rows["null"]["channel_identity_hex"]
    assert len({row["value_sha256"] for row in rows.values()}) == 4
    assert len({row["row_sha256"] for row in rows.values()}) == 4
    assert case["expected"]["categorical_order"][0][:2] == ["MISSING", "EXACT_CATEGORY"]
    assert case["expected"]["output_artifact_sha256"] == "d06f4dc1c745e3f5b2f5b3b8f3195f4749b83787ca1679bd8850c7c819571618"


def test_missing_atom_bidirectional_invariant_and_occurrence_aggregation_goldens():
    cases = golden_cases()
    assert cases["MISSING_CHANNEL_WITH_NONMISSING_ATOM_REJECTED"]["expected"]["failure_code"] == "NOT_QUALIFIED_MISSING_ATOM_MISMATCH"
    assert cases["NONMISSING_CHANNEL_WITH_MISSING2_ATOM_REJECTED"]["expected"]["failure_code"] == "NOT_QUALIFIED_MISSING_ATOM_MISMATCH"
    aggregation = cases["CATEGORICAL_TWO_OCCURRENCES_ONE_ROW"]["expected"]
    assert aggregation["emitted_row_count_u64"] == "1"
    assert aggregation["emitted_count_u64"] == "2"
    output = json.loads(bytes.fromhex(aggregation["output_artifact_bytes_hex"]))
    assert output["features"]["categorical"][0]["count_u64"] == "2"


def test_bag_multiset_removes_item_index_and_is_permutation_invariant():
    case = golden_cases()["BAG_MULTISET_TWO_VALUES"]
    assert case["expected"]["summary"] == {
        "bag.count": {"denominator": "1", "numerator": "2"},
        "bag.lower_middle": {"denominator": "1", "numerator": "1"},
        "bag.max": {"denominator": "1", "numerator": "4"},
        "bag.min": {"denominator": "1", "numerator": "1"},
        "bag.sum": {"denominator": "1", "numerator": "5"},
        "bag.upper_middle": {"denominator": "1", "numerator": "4"},
    }
    assert ORACLE.bag_summary([Fraction(1), Fraction(4)]) == ORACLE.bag_summary(
        [Fraction(4), Fraction(1)]
    )
    raw = bytes.fromhex(case["expected"]["output_artifact_bytes_hex"])
    vector = json.loads(raw)
    identities = [
        (row["family"], row["context_hex"], row["channel"], row["stat"])
        for row in vector["features"]["numeric"]
    ]
    assert len(identities) == len(set(identities)) == 6
    singleton = golden_cases()["BAG_MULTISET_SINGLETON"]["expected"]["summary"]
    assert {singleton[name]["numerator"] for name in singleton if name != "bag.count"} == {"7"}
    assert golden_cases()["EMPTY_BAG_REJECTED"]["expected"]["failure_code"] == "NOT_QUALIFIED_CARDINALITY"


def test_ordered_singleton_has_item_and_all_thirteen_summary_stats():
    case = golden_cases()["ORDERED_SERIES_SINGLETON"]
    raw = bytes.fromhex(case["expected"]["output_artifact_bytes_hex"])
    vector = json.loads(raw)
    rows = vector["features"]["numeric"]
    assert len(rows) == 14
    assert sum(row["channel"] == "ORDERED_ITEM" for row in rows) == 1
    summaries = [row for row in rows if row["channel"] == "ORDERED_SUMMARY"]
    assert {row["stat"] for row in summaries} == set(ORACLE.SERIES_STATS)
    assert all(row["denominator"] == "1" for row in summaries)


def test_route_aware_ngram_hard_constants_distinguish_cwd_and_argv():
    expected = golden_cases()["ROUTE_AWARE_CWD_ARGV_NGRAM"]["expected"]
    assert expected["distinct_digest"] is True
    assert expected["cwd"]["digest_sha256"] == "51b3833f77ac54c3beb831cfd8820835a8baa30c90c73657010b791064f834b9"
    assert expected["cwd"]["bucket_u16"] == "831"
    assert expected["argv0"]["digest_sha256"] == "5ee2cb19daf48d830429d0541cf409e4c4a0ad89280113f1efa58ea53477c333"
    assert expected["argv0"]["bucket_u16"] == "2841"
    assert expected["cwd"]["preimage_hex"] != expected["argv0"]["preimage_hex"]


def test_4097_byte_unicode_windows_split_codepoints_and_have_no_cross_gap_grams():
    case = golden_cases()["UTF8_4097_BYTE_SPLIT_INSIDE_CODEPOINT"]
    raw = base64.b64decode(case["input"]["utf8_base64"], validate=True)
    assert len(raw) == 4097
    assert hashlib.sha256(raw).hexdigest() == "453fe50e8251c07b4952b590042cbdb1802531010c9b68a2cf0089b65f308ff2"
    first, last = raw[:2048], raw[-2048:]
    for span in (first, last):
        try:
            span.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            raise AssertionError("span unexpectedly ended on UTF-8 code point boundaries")
    expected = case["expected"]
    assert expected["first_span_utf8_decodable"] is False
    assert expected["last_span_utf8_decodable"] is False
    assert expected["truncated"] == "TRUE"
    assert sum(int(row["occurrence_count_u64"]) for row in expected["gram_evaluations"]) == 16372
    assert expected["shape"]["shape.byte_length"]["numerator"] == "4097"
    assert expected["shape"]["shape.codepoint_length"]["numerator"] == "1367"
    assert expected["shape"]["shape.non_ascii"]["numerator"] == "1365"


def test_category_frame_collision_pair_has_two_exact_preimages_and_digests():
    expected = golden_cases()["CATEGORY_LENGTH_FRAMING_COLLISION_RESISTANCE"]["expected"]
    assert expected["distinct_row_hash"] is True
    assert expected["first"]["row_preimage_hex"] != expected["second"]["row_preimage_hex"]
    assert expected["first"]["row_sha256"] != expected["second"]["row_sha256"]


def test_bounds_fail_closed_with_exact_codes():
    cases = golden_cases()
    assert cases["INVALID_NUMERIC_EXPONENT_BOUND"]["expected"]["failure_code"] == "NOT_QUALIFIED_NUMERIC_BOUNDS"
    assert cases["INVALID_NUMBER_LEXEME_BYTE_BOUND"]["expected"]["failure_code"] == "NOT_QUALIFIED_NUMERIC_BOUNDS"
    assert cases["INVALID_FRAME_U32_BOUND"]["expected"]["failure_code"] == "NOT_QUALIFIED_FRAME_BOUNDS"
    assert cases["INVALID_COUNT_U64_BOUND"]["expected"]["failure_code"] == "NOT_QUALIFIED_COUNT_BOUNDS"


def test_numeric_resource_boundaries_are_machine_decisive():
    cases = golden_cases()
    leading = cases["LEADING_ZERO_EXPONENT_ACCEPTED"]["expected"]
    assert (leading["numerator"], leading["denominator"]) == ("1", "1")
    assert leading["atom_hex"] == "0300000001310000000131"
    assert cases["SIGNIFICAND_ALL_MANTISSA_DIGITS_BOUND"]["expected"]["failure_code"] == "NOT_QUALIFIED_NUMERIC_BOUNDS"
    assert cases["DERIVED_RATIONAL_4865_DIGITS_REJECTED"]["expected"]["failure_code"] == "NOT_QUALIFIED_NUMERIC_BOUNDS"
    assert cases["JSON_DEPTH_64_INCLUSIVE_ACCEPTED"]["expected"]["atom_sha256"] == "5d2d8a9038937d3abb381f22a94a7bea2dfc136f31cbbe32bbe05db7778b5629"
    assert cases["JSON_DEPTH_65_INCLUSIVE_REJECTED"]["expected"]["failure_code"] == "NOT_QUALIFIED_JSON_DEPTH"


def test_raw_json_boundary_rejects_duplicate_keys_invalid_utf8_and_surrogate():
    cases = golden_cases()
    expected = {
        "DUPLICATE_JSON_KEY_REJECTED_BEFORE_MAP": "NOT_QUALIFIED_DUPLICATE_JSON_KEY",
        "RAW_UTF8_OVERLONG_REJECTED": "NOT_QUALIFIED_INVALID_UNICODE",
        "RAW_UTF8_LONE_CONTINUATION_REJECTED": "NOT_QUALIFIED_INVALID_UNICODE",
        "JSON_LONE_SURROGATE_REJECTED": "NOT_QUALIFIED_INVALID_UNICODE",
    }
    assert {name: cases[name]["expected"]["failure_code"] for name in expected} == expected


def _routing_contract_for(vector):
    numeric = {
        (row["family"], row["channel"], row["stat"])
        for row in vector["features"]["numeric"]
    }
    categorical = {
        (row["family"], row["channel"], row["expected_channel"])
        for row in vector["features"]["categorical"]
    }
    if not numeric:
        numeric.add(("F02_ARGV_ENV_CWD", "RAW_NUMERIC", "raw.value"))
    if not categorical:
        categorical.add(("F02_ARGV_ENV_CWD", "EXACT_CATEGORY", "NONE"))
    return {
        "all_bag_calls_nonempty": True,
        "all_contexts_canonical_ctx2": True,
        "bag_output_owners": [],
        "categorical_matrix": [list(row) for row in sorted(categorical)],
        "categorical_occurrences_preaggregation": True,
        "channel_stat_matrix_complete": True,
        "families": list(ORACLE.FAMILIES),
        "missing_atom_invariant_enforced": True,
        "numeric_matrix": [list(row) for row in sorted(numeric)],
        "scalar_and_union_ownership_complete": True,
    }


def test_feature_semantic_validator_requires_routing_and_rejects_noncanonical_ctx():
    raw = bytes.fromhex(golden_cases()["TYPED_STRING_NUMBER_NULL_MISSING"]["expected"]["output_artifact_bytes_hex"])
    vector = json.loads(raw)
    ORACLE.validate_feature_vector_artifact(raw, _routing_contract_for(vector))
    try:
        ORACLE.validate_feature_vector_artifact(raw, None)
    except ORACLE.V2SError as error:
        assert error.code == "NOT_QUALIFIED_ROUTING_PRECONDITION"
    else:
        raise AssertionError("missing routing contract accepted")
    broken = json.loads(raw)
    broken["features"]["categorical"][0]["context_hex"] = "00"
    broken_raw = ORACLE.canonical_json_bytes(broken)
    try:
        ORACLE.validate_feature_vector_artifact(broken_raw, _routing_contract_for(broken))
    except ORACLE.V2SError as error:
        assert error.code == "NOT_QUALIFIED_CONTEXT"
    else:
        raise AssertionError("invalid CTX2 accepted")
    duplicate = json.loads(raw)
    duplicate["features"]["categorical"].append(dict(duplicate["features"]["categorical"][-1]))
    duplicate_raw = ORACLE.canonical_json_bytes(duplicate)
    try:
        ORACLE.validate_feature_vector_artifact(duplicate_raw, _routing_contract_for(duplicate))
    except ORACLE.V2SError as error:
        assert error.code == "NOT_QUALIFIED_DUPLICATE_CATEGORICAL_ROW"
    else:
        raise AssertionError("duplicate emitted categorical row accepted")
    overflow = json.loads(raw)
    overflow["features"]["categorical"][0]["count_u64"] = str(1 << 64)
    overflow_raw = ORACLE.canonical_json_bytes(overflow)
    try:
        ORACLE.validate_feature_vector_artifact(overflow_raw, _routing_contract_for(overflow))
    except ORACLE.V2SError as error:
        assert error.code == "NOT_QUALIFIED_COUNT_BOUNDS"
    else:
        raise AssertionError("u64 overflow count accepted")


def test_routing_precondition_rejects_nonunique_bag_output_owner():
    vector = json.loads(bytes.fromhex(golden_cases()["TYPED_STRING_NUMBER_NULL_MISSING"]["expected"]["output_artifact_bytes_hex"]))
    contract = _routing_contract_for(vector)
    owner = {
        "bag_child_context_hex": ORACLE.ctx2((("KEY", "environment"), ("BAG_ITEM", None))).hex(),
        "base_stat": "shape.byte_length",
        "family": "F02_ARGV_ENV_CWD",
        "input_channel": "STRING_SHAPE",
    }
    contract["bag_output_owners"] = [owner, dict(owner, input_channel="RAW_NUMERIC")]
    try:
        ORACLE.validate_routing_preconditions(contract)
    except ORACLE.V2SError as error:
        assert error.code == "NOT_QUALIFIED_ROUTING_PRECONDITION"
    else:
        raise AssertionError("two BAG channels collapsing to one output identity accepted")


def test_audit_semantic_validator_directly_checks_order_counts_bindings_and_pair():
    audit, audit_raw, predictor_raw, bound_files, outer = ORACLE._audit_fixture()
    ORACLE.validate_leaf_audit_artifact(
        audit_raw,
        predictor_raw=predictor_raw,
        bound_files=bound_files,
        outer_pair=outer,
    )
    cases = golden_cases()
    expected = {
        "AUDIT_INCLUDED_PERMUTATION_REJECTED": "NOT_QUALIFIED_AUDIT_ARRAY_ORDER",
        "AUDIT_INCLUDED_DUPLICATE_REJECTED": "NOT_QUALIFIED_AUDIT_ARRAY_ORDER",
        "AUDIT_ROUTING_COUNT_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_PAIR_ABSENT_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_PREDICTOR_FILENAME_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_AUDIT_FILENAME_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_PREDICTOR_LENGTH_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_AUDIT_LENGTH_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_PREDICTOR_SHA_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "AUDIT_OUTER_AUDIT_SHA_MISMATCH_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
    }
    assert {name: cases[name]["expected"]["failure_code"] for name in expected} == expected
    positive = cases["AUDIT_SORTED_CROSS_FIELD_AND_OUTER_PAIR"]["expected"]["outer_pair"]
    assert positive["schema"] == ORACLE.OUTER_PAIR_SCHEMA
    assert positive["predictor"]["filename"] == ORACLE.PREDICTOR_FILENAME
    assert positive["audit"]["filename"] == ORACLE.AUDIT_FILENAME
    assert set(positive["predictor"]) == set(positive["audit"]) == {"byte_length_u64", "filename", "sha256"}


def test_not_qualified_is_audit_only_and_forbids_attempted_predictor_or_pair():
    audit, audit_raw, bound_files = ORACLE._not_qualified_audit_fixture()
    ORACLE.validate_leaf_audit_artifact(
        audit_raw,
        predictor_raw=None,
        bound_files=bound_files,
        outer_pair=None,
    )
    assert audit["status"] == "NOT_QUALIFIED"
    assert audit["predictor_binding"] is None
    cases = golden_cases()
    positive = cases["NOT_QUALIFIED_AUDIT_ONLY_NO_PREDICTOR_OR_PAIR"]["expected"]
    assert positive["predictor_binding"] is None
    assert positive["predictor_bytes"] == positive["outer_pair"] == "ABSENT"
    expected = {
        "NOT_QUALIFIED_ATTEMPTED_PREDICTOR_BYTES_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "NOT_QUALIFIED_PREDICTOR_BINDING_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "NOT_QUALIFIED_OUTER_PAIR_REJECTED": "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
    }
    assert {name: cases[name]["expected"]["failure_code"] for name in expected} == expected


def test_predictor_and_audit_schemas_are_physically_separate():
    feature = artifacts()["FEATURE-VECTOR-V2S.candidate.schema.json"]
    audit = artifacts()["FEATURE-LEAF-AUDIT-V2S.candidate.schema.json"]
    assert set(feature["properties"]) == {"features", "schema"}
    assert "bindings" not in feature["properties"]
    assert "receipt_bytes" not in json.dumps(feature, sort_keys=True)
    assert "features" not in audit["properties"]
    assert "predictor_binding" in audit["properties"]
    assert audit["x-v2s-separation"]["sidecar_mutation_changes_predictor"] is False
    assert "MUST NOT be produced" in audit["x-v2s-separation"]["not_qualified"]


def test_oracle_check_command_material_has_stable_output_hashes():
    cases = golden_cases()
    expected = {
        "TYPED_STRING_NUMBER_NULL_MISSING": "d06f4dc1c745e3f5b2f5b3b8f3195f4749b83787ca1679bd8850c7c819571618",
        "CATEGORICAL_TWO_OCCURRENCES_ONE_ROW": "d38b7662873bf97421b4de7d5771d8f809ea5543bf682f3956d001f32513afe5",
        "BAG_MULTISET_TWO_VALUES": "5191f77fb1e12202d4bedb54f2ff24aa05845911d9d08fed82d2fa245c8a96c3",
        "ORDERED_SERIES_SINGLETON": "1e4ef0a2b1a79edb360c34cebe914ee49829f8402af620598fa91c1450671467",
        "ROUTE_AWARE_CWD_ARGV_NGRAM": "a1996d4dab0ba78ab876bbccfb83b12a581022db81acba1c8a55c9da520e0cc4",
        "NGRAM_DISTINCT_ROUTE_DIGEST_BUCKET_COLLISION_MERGED": "fd4d5e2338fb7f3a96a8255a9c2d41fdc7921ad03bd936ed7d7198f2a303a51b",
        "UTF8_4097_BYTE_SPLIT_INSIDE_CODEPOINT": "d5a6ffbeab76be00615ff8e1d073020a7592e5e66ea890028a0d9578d2344c29",
        "CATEGORY_LENGTH_FRAMING_COLLISION_RESISTANCE": "ad19541d2f5bc2e89240a4f934e30bb0b58831e18d7f6de03a51dc2ba4f554ac",
    }
    assert {case_id: cases[case_id]["expected"]["output_artifact_sha256"] for case_id in expected} == expected
