#!/usr/bin/env python3
"""Independent byte oracle for the non-canonical Wave025 V2S primitives candidate.

This module deliberately contains no collector routing and no C01--C05 layout.
It builds the four machine artifacts in this package and recomputes every public
golden from byte operations implemented with the Python standard library only.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence


U32_MAX = (1 << 32) - 1
U64_MAX = (1 << 64) - 1
MAX_FRAME_BYTES = 16_777_216
MAX_INPUT_BYTES = 67_108_864
MAX_JSON_DEPTH = 64
MAX_CONTAINER_ITEMS = 1_000_000
MAX_NUMBER_LEXEME_BYTES = 1_024
MAX_SIGNIFICAND_DIGITS = 768
MAX_ABS_EXP10 = 4_096
MAX_RATIONAL_DECIMAL_DIGITS = 4_864
NGRAM_BUCKETS = 4_096
PREDICTOR_FILENAME = "feature-vector.v2s.json"
AUDIT_FILENAME = "feature-leaf-audit.v2s.json"
OUTER_PAIR_SCHEMA = "WAVE025_PREDICTOR_AUDIT_PAIR_V2S_CANDIDATE"

FAMILIES = (
    "F01_PUBLIC_INPUT_BYTES",
    "F02_ARGV_ENV_CWD",
    "F03_HOSTNAME_IDENTITY",
    "F04_DIRECTORY_AND_SHARED_STATE",
    "F05_PROCESS_NAMESPACE_FD",
    "F06_TIMING_AND_ERRORS",
    "F07_VISIBLE_CANARY",
)

NUMBER_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?\Z")
INTEGER_STRING_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")
DECIMAL_RE = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
POSITIVE_DECIMAL_RE = re.compile(r"(?:[1-9][0-9]*)\Z")
U64_DEC_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")


class V2SError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class JsonNumber:
    lexeme: str


class _Missing:
    pass


MISSING = _Missing()


def _numeric_digit_count(value: int) -> int:
    """Count canonical decimal magnitude digits; the sign is never a digit."""
    return len(str(abs(value)))


def validate_rational_bounds(value: Fraction) -> Fraction:
    """Apply the same bound to parsed and every derived/emitted rational."""
    if _numeric_digit_count(value.numerator) > MAX_RATIONAL_DECIMAL_DIGITS:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "canonical numerator digit ceiling")
    if _numeric_digit_count(value.denominator) > MAX_RATIONAL_DECIMAL_DIGITS:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "canonical denominator digit ceiling")
    return value


def validate_decoded_input_bytes(raw: bytes) -> str:
    """Validate the exact post-transport, pre-JSON-parse document bytes."""
    if len(raw) > MAX_INPUT_BYTES:
        raise V2SError("NOT_QUALIFIED_INPUT_BYTES", "decoded input byte ceiling")
    try:
        return raw.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise V2SError("NOT_QUALIFIED_INVALID_UNICODE", "invalid raw UTF-8") from error


def parse_json_document(raw: bytes) -> Any:
    """Parse exact raw JSON while retaining number lexemes and rejecting duplicate keys."""
    text = validate_decoded_input_bytes(raw)

    def object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            valid_scalar_text(key)
            if key in output:
                raise V2SError("NOT_QUALIFIED_DUPLICATE_JSON_KEY", key)
            output[key] = value
        return output

    def reject_constant(value: str) -> Any:
        raise V2SError("NOT_QUALIFIED_INVALID_JSON_NUMBER", value)

    try:
        return json.loads(
            text,
            object_pairs_hook=object_from_pairs,
            parse_int=JsonNumber,
            parse_float=JsonNumber,
            parse_constant=reject_constant,
        )
    except V2SError:
        raise
    except json.JSONDecodeError as error:
        raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", "invalid JSON document") from error


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u32(value: int) -> bytes:
    if not 0 <= value <= U32_MAX:
        raise V2SError("NOT_QUALIFIED_FRAME_BOUNDS", f"u32:{value}")
    return value.to_bytes(4, "big")


def validate_frame_length(value: int) -> None:
    if not 0 <= value <= U32_MAX or value > MAX_FRAME_BYTES:
        raise V2SError("NOT_QUALIFIED_FRAME_BOUNDS", f"frame_length:{value}")


def frame32(data: bytes) -> bytes:
    validate_frame_length(len(data))
    return u32(len(data)) + data


def valid_scalar_text(value: str) -> bytes:
    for char in value:
        cp = ord(char)
        if 0xD800 <= cp <= 0xDFFF:
            raise V2SError("NOT_QUALIFIED_INVALID_UNICODE", "lone surrogate")
    data = value.encode("utf-8")
    if len(data) > MAX_FRAME_BYTES:
        raise V2SError("NOT_QUALIFIED_FRAME_BOUNDS", "utf8 scalar exceeds frame ceiling")
    return data


def parse_json_number_lexeme(lexeme: str) -> Fraction:
    raw = lexeme.encode("ascii", "strict")
    if len(raw) > MAX_NUMBER_LEXEME_BYTES:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "number lexeme byte ceiling")
    match = NUMBER_RE.fullmatch(lexeme)
    if not match:
        raise V2SError("NOT_QUALIFIED_INVALID_JSON_NUMBER", lexeme)
    mantissa, exponent_text = lexeme, match.group(2)
    if "e" in mantissa.lower():
        mantissa = re.split("[eE]", mantissa, maxsplit=1)[0]
    signless = mantissa[1:] if mantissa.startswith("-") else mantissa
    integer_part, dot, fraction_part = signless.partition(".")
    # Every mantissa digit counts, including leading/trailing zeroes. Signs,
    # decimal punctuation and exponent syntax do not count.
    significand_digits = len(integer_part) + len(fraction_part)
    if significand_digits > MAX_SIGNIFICAND_DIGITS:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "significand digit ceiling")
    if exponent_text is None:
        exponent = 0
    else:
        exponent_digits = exponent_text.lstrip("+-")
        magnitude_text = exponent_digits.lstrip("0") or "0"
        if len(magnitude_text) > len(str(MAX_ABS_EXP10)) or (
            len(magnitude_text) == len(str(MAX_ABS_EXP10))
            and magnitude_text > str(MAX_ABS_EXP10)
        ):
            raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "absolute exponent ceiling")
        exponent = int(exponent_text)
    if abs(exponent) > MAX_ABS_EXP10:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "absolute exponent ceiling")
    digits = int(integer_part + fraction_part)
    if lexeme.startswith("-"):
        digits = -digits
    scale = len(fraction_part) - exponent
    if scale >= 0:
        result = Fraction(digits, 10**scale)
    else:
        result = Fraction(digits * (10 ** (-scale)), 1)
    return validate_rational_bounds(result)


def parse_decimal_integer_string(value: str) -> Fraction:
    if len(value.encode("ascii", "strict")) > MAX_NUMBER_LEXEME_BYTES:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "integer string byte ceiling")
    if not INTEGER_STRING_RE.fullmatch(value):
        raise V2SError("NOT_QUALIFIED_INVALID_DECIMAL_INTEGER_STRING", value)
    if len(value.lstrip("-")) > MAX_SIGNIFICAND_DIGITS:
        raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "integer string digit ceiling")
    return validate_rational_bounds(Fraction(int(value), 1))


def rational_pair(value: Fraction) -> tuple[str, str]:
    validate_rational_bounds(value)
    return str(value.numerator), str(value.denominator)


def tve2(value: Any, depth: int = 1) -> bytes:
    # JSON depth is the inclusive root-to-value count: the root is depth 1.
    if depth > MAX_JSON_DEPTH:
        raise V2SError("NOT_QUALIFIED_JSON_DEPTH", f"depth:{depth}")
    if value is MISSING:
        return b"\x07"
    if value is None:
        return b"\x00"
    if value is False:
        return b"\x01"
    if value is True:
        return b"\x02"
    if isinstance(value, JsonNumber):
        fraction = parse_json_number_lexeme(value.lexeme)
        numerator, denominator = rational_pair(fraction)
        return b"\x03" + frame32(numerator.encode("ascii")) + frame32(denominator.encode("ascii"))
    if isinstance(value, str):
        return b"\x04" + frame32(valid_scalar_text(value))
    if isinstance(value, list):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise V2SError("NOT_QUALIFIED_CONTAINER_BOUNDS", "array item ceiling")
        parts = [b"\x05", u32(len(value))]
        parts.extend(frame32(tve2(item, depth + 1)) for item in value)
        result = b"".join(parts)
        validate_frame_length(len(result))
        return result
    if isinstance(value, dict):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise V2SError("NOT_QUALIFIED_CONTAINER_BOUNDS", "object item ceiling")
        keyed = [(valid_scalar_text(key), key, item) for key, item in value.items()]
        keyed.sort(key=lambda row: row[0])
        parts = [b"\x06", u32(len(keyed))]
        for key_bytes, _, item in keyed:
            parts.append(frame32(key_bytes))
            parts.append(frame32(tve2(item, depth + 1)))
        result = b"".join(parts)
        validate_frame_length(len(result))
        return result
    raise TypeError(f"unsupported TVE2 type: {type(value)!r}")


def ctx2(segments: Sequence[tuple[str, Any]]) -> bytes:
    encoded = [frame32(b"WAVE025_CONTEXT_V2S"), u32(len(segments))]
    for kind, value in segments:
        if kind == "KEY":
            encoded.append(b"\x01" + frame32(valid_scalar_text(value)))
        elif kind == "ORDERED":
            encoded.append(b"\x02" + u32(value))
        elif kind == "BAG_ITEM":
            encoded.append(b"\x03")
        elif kind == "DERIVED":
            raw = value.encode("ascii", "strict")
            encoded.append(b"\x04" + frame32(raw))
        else:
            raise V2SError("NOT_QUALIFIED_CONTEXT", f"unknown segment:{kind}")
    return b"".join(encoded)


def _read_u32(raw: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(raw):
        raise V2SError("NOT_QUALIFIED_CONTEXT", "truncated u32")
    return int.from_bytes(raw[offset : offset + 4], "big"), offset + 4


def _read_frame32(raw: bytes, offset: int) -> tuple[bytes, int]:
    size, offset = _read_u32(raw, offset)
    validate_frame_length(size)
    if offset + size > len(raw):
        raise V2SError("NOT_QUALIFIED_CONTEXT", "truncated frame")
    return raw[offset : offset + size], offset + size


def validate_ctx2_bytes(raw: bytes) -> None:
    domain, offset = _read_frame32(raw, 0)
    if domain != b"WAVE025_CONTEXT_V2S":
        raise V2SError("NOT_QUALIFIED_CONTEXT", "wrong CTX2 domain")
    count, offset = _read_u32(raw, offset)
    for _ in range(count):
        if offset >= len(raw):
            raise V2SError("NOT_QUALIFIED_CONTEXT", "missing CTX2 segment")
        tag = raw[offset]
        offset += 1
        if tag == 1:
            key, offset = _read_frame32(raw, offset)
            try:
                valid_scalar_text(key.decode("utf-8", "strict"))
            except (UnicodeDecodeError, V2SError) as error:
                raise V2SError("NOT_QUALIFIED_CONTEXT", "invalid KEY segment") from error
        elif tag == 2:
            _, offset = _read_u32(raw, offset)
        elif tag == 3:
            pass
        elif tag == 4:
            name, offset = _read_frame32(raw, offset)
            try:
                name.decode("ascii", "strict")
            except UnicodeDecodeError as error:
                raise V2SError("NOT_QUALIFIED_CONTEXT", "non-ASCII DERIVED segment") from error
        else:
            raise V2SError("NOT_QUALIFIED_CONTEXT", f"unknown CTX2 tag:{tag}")
    if offset != len(raw):
        raise V2SError("NOT_QUALIFIED_CONTEXT", "trailing CTX2 bytes")


CATEGORY_CHANNELS = (
    "BRANCH_CATEGORY",
    "EXACT_CATEGORY",
    "INTEGER_RESIDUE_CATEGORY",
    "MISSING",
    "RECORD_BAG_CATEGORY",
    "TYPED_NUMBER_CATEGORY",
)

EXPECTED_CHANNELS = (
    "BRANCH_CATEGORY",
    "EXACT_CATEGORY",
    "INTEGER_RESIDUE_CATEGORY",
    "NONE",
    "RECORD_BAG_CATEGORY",
    "TYPED_NUMBER_CATEGORY",
)


def channel_identity(channel: str, expected_channel: str = "NONE") -> bytes:
    if channel not in CATEGORY_CHANNELS and channel != "LEXICAL_NGRAM":
        raise V2SError("NOT_QUALIFIED_CHANNEL", channel)
    if expected_channel not in EXPECTED_CHANNELS:
        raise V2SError("NOT_QUALIFIED_CHANNEL", expected_channel)
    if channel == "MISSING" and expected_channel == "NONE":
        raise V2SError("NOT_QUALIFIED_MISSING_CHANNEL", "missing requires expected channel")
    if channel != "MISSING" and expected_channel != "NONE":
        raise V2SError("NOT_QUALIFIED_MISSING_CHANNEL", "non-missing forbids expected channel")
    return (
        frame32(b"WAVE025_CHANNEL_V2S")
        + frame32(channel.encode("ascii"))
        + frame32(expected_channel.encode("ascii"))
    )


def category_eval(
    family: str,
    context: bytes,
    channel: str,
    value: Any,
    expected_channel: str = "NONE",
) -> dict[str, str]:
    validate_family(family)
    if (channel == "MISSING") != (value is MISSING):
        raise V2SError(
            "NOT_QUALIFIED_MISSING_ATOM_MISMATCH",
            "channel=MISSING iff atom=MISSING2",
        )
    atom = tve2(value)
    channel_bytes = channel_identity(channel, expected_channel)
    value_preimage = frame32(b"WAVE025_TYPED_VALUE_V2S") + frame32(atom)
    value_digest = hashlib.sha256(value_preimage).digest()
    row_preimage = (
        frame32(b"WAVE025_CATEGORY_ROW_V2S")
        + frame32(family.encode("utf-8"))
        + frame32(context)
        + frame32(channel_bytes)
        + frame32(value_digest)
    )
    return {
        "atom_hex": atom.hex(),
        "channel_identity_hex": channel_bytes.hex(),
        "context_hex": context.hex(),
        "row_preimage_hex": row_preimage.hex(),
        "row_sha256": sha256_hex(row_preimage),
        "value_preimage_hex": value_preimage.hex(),
        "value_sha256": value_digest.hex(),
    }


def ngram_spans(raw: bytes) -> tuple[list[tuple[int, int, bytes]], bool]:
    if len(raw) <= 4096:
        return [(0, len(raw), raw)], False
    return [(0, 2048, raw[:2048]), (len(raw) - 2048, len(raw), raw[-2048:])], True


def ngram_eval(family: str, context: bytes, n: int, gram: bytes) -> dict[str, Any]:
    validate_family(family)
    if n not in (1, 2, 3, 4) or len(gram) != n:
        raise V2SError("NOT_QUALIFIED_NGRAM", "n/gram length mismatch")
    channel_bytes = channel_identity("LEXICAL_NGRAM", "NONE")
    preimage = (
        frame32(b"WAVE025_UTF8_NGRAM_V2S")
        + frame32(family.encode("utf-8"))
        + frame32(context)
        + frame32(channel_bytes)
        + frame32(bytes([n]))
        + frame32(gram)
    )
    digest = hashlib.sha256(preimage).digest()
    return {
        "bucket_u16": str(int.from_bytes(digest[:4], "big") % NGRAM_BUCKETS),
        "digest_sha256": digest.hex(),
        "gram_hex": gram.hex(),
        "n_u8": str(n),
        "preimage_hex": preimage.hex(),
    }


def scan_ngrams(family: str, context: bytes, text: str) -> dict[str, Any]:
    raw = valid_scalar_text(text)
    spans, truncated = ngram_spans(raw)
    gram_counts: dict[tuple[int, bytes], int] = {}
    bucket_counts: dict[int, int] = {}
    evaluations: list[dict[str, Any]] = []
    for _, _, span in spans:
        for n in (1, 2, 3, 4):
            for index in range(0, max(0, len(span) - n + 1)):
                key = (n, span[index : index + n])
                gram_counts[key] = gram_counts.get(key, 0) + 1
    for (n, gram), count in sorted(gram_counts.items(), key=lambda row: (row[0], row[1])):
        row = ngram_eval(family, context, n, gram)
        row["occurrence_count_u64"] = str(count)
        evaluations.append(row)
        bucket = int(row["bucket_u16"])
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + count
    return {
        "bucket_counts": bucket_counts,
        "full_byte_length_u64": str(len(raw)),
        "gram_evaluations": evaluations,
        "spans": [
            {
                "end_exclusive_u64": str(end),
                "sha256": sha256_hex(span),
                "start_u64": str(start),
            }
            for start, end, span in spans
        ],
        "truncated": "TRUE" if truncated else "FALSE",
    }


def string_shape(text: str) -> dict[str, Fraction]:
    raw = valid_scalar_text(text)
    return {
        "shape.ascii_alpha": Fraction(sum((65 <= byte <= 90) or (97 <= byte <= 122) for byte in raw), 1),
        "shape.ascii_digit": Fraction(sum(48 <= byte <= 57 for byte in raw), 1),
        "shape.byte_length": Fraction(len(raw), 1),
        "shape.codepoint_length": Fraction(len(text), 1),
        "shape.colon": Fraction(raw.count(b":"), 1),
        "shape.dash": Fraction(raw.count(b"-"), 1),
        "shape.dot": Fraction(raw.count(b"."), 1),
        "shape.non_ascii": Fraction(sum(ord(char) > 0x7F for char in text), 1),
        "shape.slash": Fraction(raw.count(b"/"), 1),
        "shape.truncated": Fraction(int(len(raw) > 4096), 1),
        "shape.underscore": Fraction(raw.count(b"_"), 1),
        "shape.whitespace": Fraction(sum(byte in {9, 10, 11, 12, 13, 32} for byte in raw), 1),
    }


def fraction_sort(values: Iterable[Fraction]) -> list[Fraction]:
    return sorted(values)


def bag_summary(values: Sequence[Fraction]) -> dict[str, Fraction]:
    if not values:
        raise V2SError("NOT_QUALIFIED_CARDINALITY", "BAG_MULTISET requires at least one value")
    ordered = fraction_sort(values)
    count = len(ordered)
    summary = {
        "bag.count": Fraction(count, 1),
        "bag.lower_middle": ordered[(count - 1) // 2],
        "bag.max": ordered[-1],
        "bag.min": ordered[0],
        "bag.sum": sum(ordered, Fraction(0, 1)),
        "bag.upper_middle": ordered[count // 2],
    }
    for value in summary.values():
        validate_rational_bounds(value)
    return summary


SERIES_STATS = (
    "series.count",
    "series.sum",
    "series.min",
    "series.max",
    "series.first",
    "series.last",
    "series.lower_middle",
    "series.upper_middle",
    "series.adjacent_absolute_delta_sum",
    "series.adjacent_absolute_delta_max",
    "series.positive_step_count",
    "series.negative_step_count",
    "series.zero_step_count",
)


def series_summary(values: Sequence[Fraction]) -> dict[str, Fraction]:
    count = len(values)
    if count == 0:
        return {"series.count": validate_rational_bounds(Fraction(0, 1))}
    ordered = sorted(values)
    deltas = [values[index] - values[index - 1] for index in range(1, count)]
    abs_deltas = [abs(value) for value in deltas]
    summary = {
        "series.adjacent_absolute_delta_max": max(abs_deltas, default=Fraction(0, 1)),
        "series.adjacent_absolute_delta_sum": sum(abs_deltas, Fraction(0, 1)),
        "series.count": Fraction(count, 1),
        "series.first": values[0],
        "series.last": values[-1],
        "series.lower_middle": ordered[(count - 1) // 2],
        "series.max": ordered[-1],
        "series.min": ordered[0],
        "series.negative_step_count": Fraction(sum(value < 0 for value in deltas), 1),
        "series.positive_step_count": Fraction(sum(value > 0 for value in deltas), 1),
        "series.sum": sum(values, Fraction(0, 1)),
        "series.upper_middle": ordered[count // 2],
        "series.zero_step_count": Fraction(sum(value == 0 for value in deltas), 1),
    }
    for value in summary.values():
        validate_rational_bounds(value)
    return summary


NUMERIC_CHANNELS = (
    "BAG_SUMMARY",
    "CONTAINER_COUNT",
    "LEXICAL_META",
    "ORDERED_ITEM",
    "ORDERED_SUMMARY",
    "RAW_NUMERIC",
    "STRING_SHAPE",
)


NUMERIC_STATS = (
    "bag.count",
    "bag.lower_middle",
    "bag.max",
    "bag.min",
    "bag.sum",
    "bag.upper_middle",
    "container.count",
    "lexical.full_byte_length",
    "lexical.truncated",
    "raw.value",
    *SERIES_STATS,
    "shape.ascii_alpha",
    "shape.ascii_digit",
    "shape.byte_length",
    "shape.codepoint_length",
    "shape.colon",
    "shape.dash",
    "shape.dot",
    "shape.non_ascii",
    "shape.slash",
    "shape.truncated",
    "shape.underscore",
    "shape.whitespace",
)


def validate_family(family: str) -> None:
    if family not in FAMILIES:
        raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", f"unknown family:{family}")


def numeric_entry(family: str, context: bytes, channel: str, stat: str, value: Fraction) -> dict[str, str]:
    validate_family(family)
    if channel not in NUMERIC_CHANNELS:
        raise V2SError("NOT_QUALIFIED_CHANNEL", channel)
    if stat not in NUMERIC_STATS:
        raise V2SError("NOT_QUALIFIED_STAT", stat)
    numerator, denominator = rational_pair(value)
    return {
        "channel": channel,
        "context_hex": context.hex(),
        "denominator": denominator,
        "family": family,
        "numerator": numerator,
        "stat": stat,
    }


def categorical_entry(
    family: str,
    context: bytes,
    channel: str,
    expected_channel: str,
    value: Any,
    count: int = 1,
) -> dict[str, str]:
    validate_family(family)
    if not 1 <= count <= U64_MAX:
        raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", f"count:{count}")
    evaluated = category_eval(family, context, channel, value, expected_channel)
    return {
        "channel": channel,
        "context_hex": context.hex(),
        "count_u64": str(count),
        "expected_channel": expected_channel,
        "family": family,
        "value_sha256": evaluated["value_sha256"],
    }


def ngram_entry(family: str, bucket: int, count: int) -> dict[str, str]:
    validate_family(family)
    if not 0 <= bucket < NGRAM_BUCKETS:
        raise V2SError("NOT_QUALIFIED_NGRAM", f"bucket:{bucket}")
    if not 1 <= count <= U64_MAX:
        raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", f"count:{count}")
    return {"bucket_u16": str(bucket), "count_u64": str(count), "family": family}


def vector(
    numeric: Sequence[dict[str, str]] = (),
    categorical: Sequence[dict[str, str]] = (),
    ngram_counts: Sequence[dict[str, str]] = (),
) -> dict[str, Any]:
    # Categorical inputs are occurrences. Normalize identical identities by
    # summing counts; a zero-occurrence identity is absent and is never emitted.
    categorical_aggregated: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in categorical:
        identity = (
            row["family"],
            row["context_hex"],
            row["channel"],
            row["expected_channel"],
            row["value_sha256"],
        )
        count = int(row["count_u64"])
        if not 1 <= count <= U64_MAX:
            raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", f"count:{count}")
        if identity not in categorical_aggregated:
            categorical_aggregated[identity] = dict(row)
        else:
            combined = int(categorical_aggregated[identity]["count_u64"]) + count
            if combined > U64_MAX:
                raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", f"categorical aggregate:{combined}")
            categorical_aggregated[identity]["count_u64"] = str(combined)
    numeric_sorted = sorted(
        numeric,
        key=lambda row: (
            row["family"].encode("utf-8"),
            bytes.fromhex(row["context_hex"]),
            row["channel"].encode("ascii"),
            row["stat"].encode("ascii"),
        ),
    )
    categorical_sorted = sorted(
        categorical_aggregated.values(),
        key=lambda row: (
            row["family"].encode("utf-8"),
            bytes.fromhex(row["context_hex"]),
            channel_identity(row["channel"], row["expected_channel"]),
            bytes.fromhex(row["value_sha256"]),
        ),
    )
    ngram_sorted = sorted(ngram_counts, key=lambda row: (row["family"].encode("utf-8"), int(row["bucket_u16"])))
    numeric_ids = [
        (row["family"], row["context_hex"], row["channel"], row["stat"]) for row in numeric_sorted
    ]
    category_ids = [
        (
            row["family"],
            row["context_hex"],
            row["channel"],
            row["expected_channel"],
            row["value_sha256"],
        )
        for row in categorical_sorted
    ]
    ngram_ids = [(row["family"], row["bucket_u16"]) for row in ngram_sorted]
    if len(numeric_ids) != len(set(numeric_ids)):
        raise V2SError("NOT_QUALIFIED_DUPLICATE_NUMERIC_IDENTITY", "duplicate numeric identity")
    # Duplicates cannot survive occurrence normalization; a decoder of an
    # already-emitted vector must still reject duplicate normalized rows.
    if len(category_ids) != len(set(category_ids)):
        raise V2SError("NOT_QUALIFIED_DUPLICATE_CATEGORICAL_ROW", "duplicate normalized categorical row")
    if len(ngram_ids) != len(set(ngram_ids)):
        raise V2SError("NOT_QUALIFIED_DUPLICATE_NGRAM_BUCKET", "duplicate ngram bucket row")
    return {
        "features": {
            "categorical": categorical_sorted,
            "ngram_counts": ngram_sorted,
            "numeric": numeric_sorted,
        },
        "schema": "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE",
    }


def _checked_u64(text: str, *, positive: bool = False) -> int:
    if not U64_DEC_RE.fullmatch(text) or len(text) > 20 or (len(text) == 20 and text > str(U64_MAX)):
        raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", text)
    value = int(text)
    if positive and value == 0:
        raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", text)
    return value


def _int_from_canonical_decimal(text: str) -> int:
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    value = 0
    for offset in range(0, len(digits), 9):
        chunk = digits[offset : offset + 9]
        value = value * (10 ** len(chunk)) + int(chunk)
    return -value if negative else value


def _require_strict_order(rows: Sequence[dict[str, Any]], key, label: str) -> None:
    identities = [key(row) for row in rows]
    if identities != sorted(identities) or len(identities) != len(set(identities)):
        raise V2SError("NOT_QUALIFIED_AUDIT_ARRAY_ORDER", label)


def _require_feature_order(rows: Sequence[dict[str, Any]], key, label: str, duplicate_code: str) -> None:
    identities = [key(row) for row in rows]
    if len(identities) != len(set(identities)):
        raise V2SError(duplicate_code, label)
    if identities != sorted(identities):
        raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", f"feature row order:{label}")


def validate_routing_preconditions(contract: dict[str, Any] | None) -> None:
    if not isinstance(contract, dict):
        raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "routing contract absent")
    required_true = (
        "all_bag_calls_nonempty",
        "all_contexts_canonical_ctx2",
        "categorical_occurrences_preaggregation",
        "channel_stat_matrix_complete",
        "missing_atom_invariant_enforced",
        "scalar_and_union_ownership_complete",
    )
    if any(contract.get(name) is not True for name in required_true):
        raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "routing claim absent or false")
    if contract.get("families") != list(FAMILIES):
        raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "exact family enum mismatch")
    for name, width in (("numeric_matrix", 3), ("categorical_matrix", 3)):
        rows = contract.get(name)
        if not isinstance(rows, list) or not rows:
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", f"{name} absent")
        tuples = [tuple(row) for row in rows if isinstance(row, list) and len(row) == width]
        if len(tuples) != len(rows) or tuples != sorted(tuples) or len(tuples) != len(set(tuples)):
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", f"{name} not canonical unique")
    owners = contract.get("bag_output_owners")
    if not isinstance(owners, list):
        raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "bag_output_owners absent")
    owner_ids: list[tuple[str, bytes, str]] = []
    for row in owners:
        try:
            identity = (row["family"], bytes.fromhex(row["bag_child_context_hex"]), row["base_stat"])
            input_channel = row["input_channel"]
        except (KeyError, TypeError, ValueError) as error:
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "invalid bag owner") from error
        validate_family(identity[0])
        validate_ctx2_bytes(identity[1])
        if not isinstance(input_channel, str) or not input_channel:
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "invalid bag input channel")
        owner_ids.append(identity)
    if owner_ids != sorted(owner_ids) or len(owner_ids) != len(set(owner_ids)):
        raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "bag output identity not unique")


def validate_feature_vector_semantics(value: dict[str, Any], routing_contract: dict[str, Any] | None) -> None:
    validate_routing_preconditions(routing_contract)
    if value.get("schema") != "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE":
        raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", "feature schema discriminator")
    try:
        features = value["features"]
        numeric = features["numeric"]
        categorical = features["categorical"]
        ngrams = features["ngram_counts"]
    except (KeyError, TypeError) as error:
        raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", "feature shape") from error
    numeric_matrix = {tuple(row) for row in routing_contract["numeric_matrix"]}
    categorical_matrix = {tuple(row) for row in routing_contract["categorical_matrix"]}

    def numeric_key(row: dict[str, str]) -> tuple[bytes, bytes, bytes, bytes]:
        return (
            row["family"].encode("utf-8"),
            bytes.fromhex(row["context_hex"]),
            row["channel"].encode("ascii"),
            row["stat"].encode("ascii"),
        )

    def category_key(row: dict[str, str]) -> tuple[bytes, bytes, bytes, bytes]:
        return (
            row["family"].encode("utf-8"),
            bytes.fromhex(row["context_hex"]),
            channel_identity(row["channel"], row["expected_channel"]),
            bytes.fromhex(row["value_sha256"]),
        )

    for row in numeric:
        validate_family(row["family"])
        context = bytes.fromhex(row["context_hex"])
        validate_ctx2_bytes(context)
        if row["channel"] not in NUMERIC_CHANNELS or row["stat"] not in NUMERIC_STATS:
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "unknown numeric channel/stat")
        if (row["family"], row["channel"], row["stat"]) not in numeric_matrix:
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "numeric matrix rejection")
        if not DECIMAL_RE.fullmatch(row["numerator"]) or not POSITIVE_DECIMAL_RE.fullmatch(row["denominator"]):
            raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "noncanonical rational strings")
        numerator = _int_from_canonical_decimal(row["numerator"])
        denominator = _int_from_canonical_decimal(row["denominator"])
        if math.gcd(abs(numerator), denominator) != 1:
            raise V2SError("NOT_QUALIFIED_NUMERIC_BOUNDS", "unreduced rational")
        validate_rational_bounds(Fraction(numerator, denominator))
    _require_feature_order(numeric, numeric_key, "numeric", "NOT_QUALIFIED_DUPLICATE_NUMERIC_IDENTITY")

    for row in categorical:
        validate_family(row["family"])
        validate_ctx2_bytes(bytes.fromhex(row["context_hex"]))
        channel_identity(row["channel"], row["expected_channel"])
        if (row["family"], row["channel"], row["expected_channel"]) not in categorical_matrix:
            raise V2SError("NOT_QUALIFIED_ROUTING_PRECONDITION", "categorical matrix rejection")
        _checked_u64(row["count_u64"], positive=True)
        if not re.fullmatch(r"[0-9a-f]{64}", row["value_sha256"]):
            raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", "value digest")
    _require_feature_order(categorical, category_key, "categorical", "NOT_QUALIFIED_DUPLICATE_CATEGORICAL_ROW")

    def ngram_key(row: dict[str, str]) -> tuple[bytes, int]:
        return row["family"].encode("utf-8"), int(row["bucket_u16"])

    for row in ngrams:
        validate_family(row["family"])
        bucket = int(row["bucket_u16"])
        if not 0 <= bucket < NGRAM_BUCKETS:
            raise V2SError("NOT_QUALIFIED_NGRAM", "bucket")
        _checked_u64(row["count_u64"], positive=True)
    _require_feature_order(ngrams, ngram_key, "ngram_counts", "NOT_QUALIFIED_DUPLICATE_NGRAM_BUCKET")


def validate_feature_vector_artifact(raw: bytes, routing_contract: dict[str, Any] | None) -> dict[str, Any]:
    value = parse_json_document(raw)
    if canonical_json_bytes(value) != raw:
        raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", "feature bytes")
    validate_feature_vector_semantics(value, routing_contract)
    return value


def _binding_matches(binding: dict[str, str], raw: bytes) -> bool:
    return (
        binding.get("byte_length_u64") == str(len(raw))
        and binding.get("sha256") == sha256_hex(raw)
    )


def _outer_binding_matches(binding: dict[str, str], filename: str, raw: bytes) -> bool:
    return binding.get("filename") == filename and _binding_matches(binding, raw)


def validate_leaf_audit_semantics(
    audit: dict[str, Any],
    *,
    audit_raw: bytes,
    predictor_raw: bytes | None,
    bound_files: dict[str, bytes],
    outer_pair: dict[str, Any] | None,
) -> None:
    included = audit["included"]
    excluded = audit["excluded"]
    routing_counts = audit["routing_counts"]
    truncation = audit["truncation_audit"]
    unknown = audit["unknown_paths"]
    failures = audit["failure_codes"]

    def included_key(row):
        context = bytes.fromhex(row["context_hex"])
        validate_ctx2_bytes(context)
        validate_family(row["family"])
        _checked_u64(row["multiplicity_u64"], positive=True)
        return (
            row["family"].encode("utf-8"),
            context,
            row["route_id"].encode("ascii"),
            row["path_json_pointer"].encode("utf-8"),
            row["channel"].encode("ascii"),
        )

    def excluded_key(row):
        _checked_u64(row["multiplicity_u64"], positive=True)
        return row["path_json_pointer"].encode("utf-8"), row["reason_code"].encode("ascii")

    def routing_key(row):
        _checked_u64(row["included_multiplicity_u64"], positive=True)
        return (row["route_id"].encode("ascii"),)

    def truncation_key(row):
        validate_family(row["family"])
        context = bytes.fromhex(row["context_hex"])
        validate_ctx2_bytes(context)
        full = _checked_u64(row["full_byte_length_u64"])
        spans = [
            (_checked_u64(span["start_u64"]), _checked_u64(span["end_exclusive_u64"]))
            for span in row["spans"]
        ]
        expected = [(0, full)] if full <= 4096 else [(0, 2048), (full - 2048, full)]
        expected_flag = "FALSE" if full <= 4096 else "TRUE"
        if spans != expected or row["truncated"] != expected_flag:
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "truncation spans")
        return row["family"].encode("utf-8"), context

    def unknown_key(row):
        _checked_u64(row["multiplicity_u64"], positive=True)
        return (row["path_json_pointer"].encode("utf-8"),)

    _require_strict_order(included, included_key, "included")
    _require_strict_order(excluded, excluded_key, "excluded")
    _require_strict_order(routing_counts, routing_key, "routing_counts")
    _require_strict_order(truncation, truncation_key, "truncation_audit")
    _require_strict_order(unknown, unknown_key, "unknown_paths")
    if failures != sorted(failures) or len(failures) != len(set(failures)) or any(
        code not in failure_codes() for code in failures
    ):
        raise V2SError("NOT_QUALIFIED_AUDIT_ARRAY_ORDER", "failure_codes")

    sums: dict[str, int] = {}
    for row in included:
        route = row["route_id"]
        sums[route] = sums.get(route, 0) + _checked_u64(row["multiplicity_u64"], positive=True)
        if sums[route] > U64_MAX:
            raise V2SError("NOT_QUALIFIED_COUNT_BOUNDS", "routing count sum")
    declared = {row["route_id"]: _checked_u64(row["included_multiplicity_u64"], positive=True) for row in routing_counts}
    if declared != sums:
        raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "routing counts")

    for binding in audit["bindings"].values():
        filename = binding["filename"]
        if filename not in bound_files or not _binding_matches(binding, bound_files[filename]):
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", f"binding readback:{filename}")

    qualified = audit["status"] == "QUALIFIED_FEATURE_EXTRACTION"
    predictor_binding = audit["predictor_binding"]
    if qualified:
        if failures or unknown or predictor_binding is None or predictor_raw is None:
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "qualified closure")
        if not _binding_matches(predictor_binding, predictor_raw):
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "predictor binding")
        if not isinstance(outer_pair, dict) or outer_pair.get("schema") != OUTER_PAIR_SCHEMA:
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "outer pair absent or schema mismatch")
        if not _outer_binding_matches(outer_pair.get("audit", {}), AUDIT_FILENAME, audit_raw):
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "outer audit filename/length/sha binding")
        if not _outer_binding_matches(outer_pair.get("predictor", {}), PREDICTOR_FILENAME, predictor_raw):
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "outer predictor filename/length/sha binding")
    else:
        if not failures or predictor_binding is not None:
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "not-qualified closure")
        if predictor_raw is not None:
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "not-qualified attempted predictor bytes forbidden")
        if outer_pair is not None:
            raise V2SError("NOT_QUALIFIED_AUDIT_CROSS_FIELD", "not-qualified outer pair forbidden")


def validate_leaf_audit_artifact(
    raw: bytes,
    *,
    predictor_raw: bytes | None,
    bound_files: dict[str, bytes],
    outer_pair: dict[str, Any] | None,
) -> dict[str, Any]:
    audit = parse_json_document(raw)
    if canonical_json_bytes(audit) != raw:
        raise V2SError("NOT_QUALIFIED_CANONICAL_BYTES", "audit bytes")
    validate_leaf_audit_semantics(
        audit,
        audit_raw=raw,
        predictor_raw=predictor_raw,
        bound_files=bound_files,
        outer_pair=outer_pair,
    )
    return audit


def _escape_string(value: str) -> bytes:
    valid_scalar_text(value)
    pieces = [b'"']
    short = {8: b"\\b", 9: b"\\t", 10: b"\\n", 12: b"\\f", 13: b"\\r"}
    for char in value:
        cp = ord(char)
        if cp == 0x22:
            pieces.append(b'\\"')
        elif cp == 0x5C:
            pieces.append(b"\\\\")
        elif cp in short:
            pieces.append(short[cp])
        elif cp <= 0x1F:
            pieces.append(f"\\u00{cp:02x}".encode("ascii"))
        else:
            pieces.append(char.encode("utf-8"))
    pieces.append(b'"')
    return b"".join(pieces)


def canonical_json_value(value: Any) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, int):
        return str(value).encode("ascii")
    if isinstance(value, list):
        return b"[" + b",".join(canonical_json_value(item) for item in value) + b"]"
    if isinstance(value, dict):
        ordered = sorted(value.items(), key=lambda item: valid_scalar_text(item[0]))
        return b"{" + b",".join(
            _escape_string(key) + b":" + canonical_json_value(item) for key, item in ordered
        ) + b"}"
    raise TypeError(f"not canonical JSON: {type(value)!r}")


def canonical_json_bytes(value: Any) -> bytes:
    return canonical_json_value(value) + b"\n"


def artifact_binding(value: dict[str, Any]) -> dict[str, str]:
    raw = canonical_json_bytes(value)
    return {
        "output_artifact_bytes_hex": raw.hex(),
        "output_artifact_length_u64": str(len(raw)),
        "output_artifact_sha256": sha256_hex(raw),
    }


def feature_vector_schema() -> dict[str, Any]:
    family = {"enum": list(FAMILIES)}
    context = {"pattern": "^(?:[0-9a-f]{2})+$", "type": "string"}
    decimal_rational = {"maxLength": MAX_RATIONAL_DECIMAL_DIGITS + 1, "pattern": "^(?:0|-?[1-9][0-9]*)$", "type": "string"}
    positive_rational = {"maxLength": MAX_RATIONAL_DECIMAL_DIGITS, "pattern": "^[1-9][0-9]*$", "type": "string"}
    positive_u64 = {"maxLength": 20, "pattern": "^[1-9][0-9]*$", "type": "string", "x-v2s-maximum": str(U64_MAX)}
    category = {
        "additionalProperties": False,
        "allOf": [
            {
                "if": {"properties": {"channel": {"const": "MISSING"}}},
                "then": {"properties": {"expected_channel": {"not": {"const": "NONE"}}}},
                "else": {"properties": {"expected_channel": {"const": "NONE"}}},
            }
        ],
        "properties": {
            "channel": {"enum": list(CATEGORY_CHANNELS)},
            "context_hex": context,
            "count_u64": positive_u64,
            "expected_channel": {"enum": list(EXPECTED_CHANNELS)},
            "family": family,
            "value_sha256": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
        },
        "required": ["channel", "context_hex", "count_u64", "expected_channel", "family", "value_sha256"],
        "type": "object",
    }
    numeric = {
        "additionalProperties": False,
        "properties": {
            "channel": {"enum": list(NUMERIC_CHANNELS)},
            "context_hex": context,
            "denominator": positive_rational,
            "family": family,
            "numerator": decimal_rational,
            "stat": {"enum": sorted(NUMERIC_STATS)},
        },
        "required": ["channel", "context_hex", "denominator", "family", "numerator", "stat"],
        "type": "object",
    }
    ngram = {
        "additionalProperties": False,
        "properties": {
            "bucket_u16": {
                "pattern": "^(?:0|[1-9][0-9]{0,2}|[1-3][0-9]{3}|40[0-8][0-9]|409[0-5])$",
                "type": "string",
            },
            "count_u64": positive_u64,
            "family": family,
        },
        "required": ["bucket_u16", "count_u64", "family"],
        "type": "object",
    }
    return {
        "$id": "urn:towow:wave025:feature-vector:v2s:candidate",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "features": {
                "additionalProperties": False,
                "properties": {
                    "categorical": {"items": category, "type": "array"},
                    "ngram_counts": {"items": ngram, "type": "array"},
                    "numeric": {"items": numeric, "type": "array"},
                },
                "required": ["categorical", "ngram_counts", "numeric"],
                "type": "object",
            },
            "schema": {"const": "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE"},
        },
        "required": ["features", "schema"],
        "title": "FeatureVectorV2S candidate; predictor-only and not adopted",
        "type": "object",
        "x-v2s-semantic-rules": {
            "categorical_row_identity": ["family_utf8", "raw_CTX2", "channel_identity", "raw_value_sha256"],
            "categorical_occurrences": "identical occurrence identities aggregate by checked u64 addition before emission; zero occurrence means no row; emitted count is 1..18446744073709551615",
            "count_bounds": "emitted counts are 1..18446744073709551615 and must be checked numerically, not only by JSON Schema",
            "context_validation": "each context_hex must decode as exactly one canonical CTX2 value",
            "family_set": list(FAMILIES),
            "ngram_row_identity": ["family_utf8", "bucket_u16_numeric"],
            "numeric_identity": ["family_utf8", "raw_CTX2", "channel_ascii", "stat_ascii"],
            "numeric_rational_bounds": "denominator positive; numerator and denominator canonical; sign excluded from the 4864 magnitude-digit limit",
            "recursive_object_key_order": "raw_utf8_ascending",
            "row_order": "numeric identity raw tuple; categorical uses complete framed channel_identity bytes; ngram family then numeric bucket",
            "routing_matrix_required": "exact allowed family/channel/stat and categorical expected-channel matrix must be supplied by the bound routing contract; absence or violation is NOT_QUALIFIED_ROUTING_PRECONDITION",
            "serialization": "compact UTF-8 JSON plus exactly one LF",
            "unique_rows_required": True,
            "validator_required": "Draft 2020-12 structural validation is insufficient; the bound provider must execute all x-v2s-semantic-rules and emit the audit sidecar",
        },
    }


def leaf_audit_schema() -> dict[str, Any]:
    digest = {"pattern": "^[0-9a-f]{64}$", "type": "string"}
    u64_decimal = {"maxLength": 20, "pattern": "^(?:0|[1-9][0-9]*)$", "type": "string", "x-v2s-maximum": str(U64_MAX)}
    positive_u64_decimal = {"maxLength": 20, "pattern": "^[1-9][0-9]*$", "type": "string", "x-v2s-maximum": str(U64_MAX)}
    context = {"pattern": "^(?:[0-9a-f]{2})+$", "type": "string"}
    included = {
        "additionalProperties": False,
        "properties": {
            "channel": {"pattern": "^[A-Z][A-Z0-9_]*$", "type": "string"},
            "context_hex": context,
            "family": {"enum": list(FAMILIES)},
            "multiplicity_u64": positive_u64_decimal,
            "path_json_pointer": {"type": "string"},
            "route_id": {"pattern": "^[A-Z0-9_.-]+$", "type": "string"},
        },
        "required": ["channel", "context_hex", "family", "multiplicity_u64", "path_json_pointer", "route_id"],
        "type": "object",
    }
    excluded = {
        "additionalProperties": False,
        "properties": {
            "multiplicity_u64": positive_u64_decimal,
            "path_json_pointer": {"type": "string"},
            "reason_code": {
                "enum": [
                    "AUDIT_ONLY_FIELD",
                    "EXPLICIT_HOST_ONLY_EXCLUSION",
                    "ROUTE_DECLARED_EXCLUSION",
                    "SCHEMA_NONPREDICTOR_FIELD",
                ]
            },
        },
        "required": ["multiplicity_u64", "path_json_pointer", "reason_code"],
        "type": "object",
    }
    binding = {
        "additionalProperties": False,
        "properties": {"byte_length_u64": u64_decimal, "filename": {"type": "string"}, "sha256": digest},
        "required": ["byte_length_u64", "filename", "sha256"],
        "type": "object",
    }
    return {
        "$id": "urn:towow:wave025:feature-leaf-audit:v2s:candidate",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "allOf": [
            {
                "if": {"properties": {"status": {"const": "QUALIFIED_FEATURE_EXTRACTION"}}},
                "then": {
                    "properties": {
                        "failure_codes": {"maxItems": 0},
                        "predictor_binding": {"type": "object"},
                        "unknown_paths": {"maxItems": 0},
                    }
                },
                "else": {
                    "properties": {
                        "failure_codes": {"minItems": 1},
                        "predictor_binding": {"type": "null"},
                    }
                },
            }
        ],
        "properties": {
            "bindings": {
                "additionalProperties": False,
                "properties": {
                    "feature_primitives": binding,
                    "feature_routing": binding,
                    "feature_vector_schema": binding,
                    "provider_source_manifest": binding,
                    "receipt_bytes": binding,
                    "receipt_schema": binding,
                },
                "required": [
                    "feature_primitives",
                    "feature_routing",
                    "feature_vector_schema",
                    "provider_source_manifest",
                    "receipt_bytes",
                    "receipt_schema",
                ],
                "type": "object",
            },
            "excluded": {"items": excluded, "type": "array", "uniqueItems": True},
            "failure_codes": {
                "items": {"enum": failure_codes()},
                "type": "array",
                "uniqueItems": True,
            },
            "included": {"items": included, "type": "array", "uniqueItems": True},
            "predictor_binding": {
                "oneOf": [
                    {"type": "null"},
                    {
                        "additionalProperties": False,
                        "properties": {
                            "byte_length_u64": u64_decimal,
                            "schema": {"const": "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE"},
                            "sha256": digest,
                        },
                        "required": ["byte_length_u64", "schema", "sha256"],
                        "type": "object",
                    },
                ]
            },
            "routing_counts": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "included_multiplicity_u64": positive_u64_decimal,
                        "route_id": {"pattern": "^[A-Z0-9_.-]+$", "type": "string"},
                    },
                    "required": ["included_multiplicity_u64", "route_id"],
                    "type": "object",
                },
                "type": "array",
                "uniqueItems": True,
            },
            "schema": {"const": "WAVE025_FEATURE_LEAF_AUDIT_V2S_CANDIDATE"},
            "status": {"enum": ["NOT_QUALIFIED", "QUALIFIED_FEATURE_EXTRACTION"]},
            "truncation_audit": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "context_hex": context,
                        "family": {"enum": list(FAMILIES)},
                        "full_byte_length_u64": u64_decimal,
                        "spans": {
                            "items": {
                                "additionalProperties": False,
                                "properties": {
                                    "end_exclusive_u64": u64_decimal,
                                    "start_u64": u64_decimal,
                                },
                                "required": ["end_exclusive_u64", "start_u64"],
                                "type": "object",
                            },
                            "maxItems": 2,
                            "minItems": 1,
                            "type": "array",
                        },
                        "truncated": {"enum": ["FALSE", "TRUE"]},
                    },
                    "required": ["context_hex", "family", "full_byte_length_u64", "spans", "truncated"],
                    "type": "object",
                },
                "type": "array",
                "uniqueItems": True,
            },
            "unknown_paths": {
                "items": {
                    "additionalProperties": False,
                    "properties": {
                        "multiplicity_u64": positive_u64_decimal,
                        "path_json_pointer": {"type": "string"},
                    },
                    "required": ["multiplicity_u64", "path_json_pointer"],
                    "type": "object",
                },
                "type": "array",
                "uniqueItems": True,
            },
        },
        "required": [
            "bindings",
            "excluded",
            "failure_codes",
            "included",
            "predictor_binding",
            "routing_counts",
            "schema",
            "status",
            "truncation_audit",
            "unknown_paths",
        ],
        "title": "FeatureLeafAuditV2S candidate; evidence-only and classifier-ineligible",
        "type": "object",
        "x-v2s-separation": {
            "classifier_must_not_read": "this artifact or any binding except predictor_binding verification",
            "not_qualified": "predictor_binding is null; classifier-readable predictor bytes MUST NOT be produced; diagnostics remain only in this audit-only artifact and MUST NOT enter an outer predictor/audit pair",
            "predictor_must_not_embed": "audit path, receipt hash, provenance, exclusion, host fact, or debug data",
            "sidecar_binds_predictor": True,
            "sidecar_mutation_changes_predictor": False,
        },
        "x-v2s-semantic-rules": {
            "array_identity_and_order": {
                "excluded": ["path_json_pointer_utf8", "reason_code_ascii"],
                "failure_codes": ["failure_code_ascii"],
                "included": ["family_utf8", "raw_CTX2", "route_id_ascii", "path_json_pointer_utf8", "channel_ascii"],
                "routing_counts": ["route_id_ascii"],
                "truncation_audit": ["family_utf8", "raw_CTX2"],
                "unknown_paths": ["path_json_pointer_utf8"],
            },
            "array_rule": "every listed identity is unique and arrays are strictly ascending by the listed raw identity",
            "binding_readback": "every binding filename, byte length and sha256 must match the exact bytes read by the provider",
            "outer_pair_binding": "QUALIFIED requires external WAVE025_PREDICTOR_AUDIT_PAIR_V2S_CANDIDATE with predictor filename feature-vector.v2s.json and audit filename feature-leaf-audit.v2s.json plus exact byte length and sha256 for each; NOT_QUALIFIED forbids the pair",
            "not_qualified_outputs": "predictor_binding=null, no predictor bytes, no outer pair; only the classifier-ineligible audit sidecar may contain diagnostics",
            "qualified_closure": "qualified status requires empty failure_codes and unknown_paths plus non-null predictor_binding",
            "routing_counts": "for each route_id exactly equal the checked-u64 sum of included.multiplicity_u64; no missing or extra route",
            "truncation": "length<=4096 exactly one [0,length) span and FALSE; length>4096 exactly [0,2048) and [length-2048,length) in order and TRUE",
            "validator_required": "Draft 2020-12 structural validation is insufficient; all semantic rules are mandatory and fail closed",
        },
    }


def failure_codes() -> list[str]:
    return sorted([
        "NOT_QUALIFIED_AUDIT_ARRAY_ORDER",
        "NOT_QUALIFIED_AUDIT_CROSS_FIELD",
        "NOT_QUALIFIED_CANONICAL_BYTES",
        "NOT_QUALIFIED_CARDINALITY",
        "NOT_QUALIFIED_CHANNEL",
        "NOT_QUALIFIED_CONTAINER_BOUNDS",
        "NOT_QUALIFIED_COUNT_BOUNDS",
        "NOT_QUALIFIED_DUPLICATE_CATEGORICAL_ROW",
        "NOT_QUALIFIED_DUPLICATE_JSON_KEY",
        "NOT_QUALIFIED_DUPLICATE_NGRAM_BUCKET",
        "NOT_QUALIFIED_DUPLICATE_NUMERIC_IDENTITY",
        "NOT_QUALIFIED_FRAME_BOUNDS",
        "NOT_QUALIFIED_INPUT_BYTES",
        "NOT_QUALIFIED_INVALID_DECIMAL_INTEGER_STRING",
        "NOT_QUALIFIED_INVALID_JSON_NUMBER",
        "NOT_QUALIFIED_INVALID_UNICODE",
        "NOT_QUALIFIED_JSON_DEPTH",
        "NOT_QUALIFIED_CONTEXT",
        "NOT_QUALIFIED_MISSING_ATOM_MISMATCH",
        "NOT_QUALIFIED_MISSING_CHANNEL",
        "NOT_QUALIFIED_NGRAM",
        "NOT_QUALIFIED_NUMERIC_BOUNDS",
        "NOT_QUALIFIED_ROUTING_PRECONDITION",
        "NOT_QUALIFIED_STAT",
        "NOT_QUALIFIED_UNKNOWN_PATH",
    ])


def primitives_candidate() -> dict[str, Any]:
    return {
        "authority": {
            "machine_semantics_source": "this exact candidate JSON byte artifact",
            "oracle_authoritative": False,
            "oracle_role": "fixture generation and independent byte recomputation only",
            "promotion": "requires root decision, clean-room byte conformance, holdback agreement, and separate routing/model decisions",
        },
        "candidate_status": "NOT_ADOPTED__NOT_FORMAL_CANON",
        "cardinality": {
            "BAG_MULTISET": {
                "call_precondition": "bound routing must prove at least one routed occurrence; otherwise NOT_QUALIFIED_CARDINALITY",
                "input_identity": ["family", "bag_child_context", "channel", "base_stat"],
                "item_index_in_predictor": False,
                "output_context": "bag_child_context + DERIVED('bag.' + base_stat)",
                "output_stats": [
                    "bag.count",
                    "bag.sum",
                    "bag.min",
                    "bag.max",
                    "bag.lower_middle",
                    "bag.upper_middle",
                ],
                "routing_uniqueness_precondition": "for each family, bag_child_context and base_stat, routing authorizes exactly one input channel; otherwise NOT_QUALIFIED_ROUTING_PRECONDITION",
                "rule": "sort exact rationals ascending; aggregate all values before emission; apply rational bounds to every derived output",
            },
            "CONTAINER_COUNT": {
                "output_channel": "CONTAINER_COUNT",
                "output_stat": "container.count",
                "rule": "only a machine routing row can authorize this count; generic recursion cannot",
            },
            "ORDERED_SERIES": {
                "item_output": "each item retains ORDERED(index) context, channel ORDERED_ITEM, and base_stat",
                "output_context": "parent_context + DERIVED('series.' + base_stat)",
                "output_stats": list(SERIES_STATS),
                "singleton": "emit item plus all 13 summary stats; deltas and step counts are zero",
                "zero": "emit series.count only",
            },
            "SCALAR_ONE": {
                "allowed_occurrences": "exactly_one",
                "duplicate_failure": "NOT_QUALIFIED_DUPLICATE_NUMERIC_IDENTITY",
                "output": "one exact-rational numeric row",
            },
        },
        "canonical_json": {
            "array_order": "already-normalized semantic row order",
            "final_bytes": "compact UTF-8 JSON plus exactly one LF",
            "forbidden": ["JSON floating token", "ASCII escaping of directly encodable scalar", "solidus escape"],
            "object_key_order": "decoded key raw UTF-8 byte ascending, recursively",
            "string_escape": "quote/backslash; short escapes for 08,09,0a,0c,0d; other controls lowercase \\u00xx",
        },
        "category": {
            "emitted_count": "1..18446744073709551615; zero occurrences emit no row; checked-u64 overflow is NOT_QUALIFIED_COUNT_BOUNDS",
            "atom": "TVE2(value); MISSING uses reserved MISSING2 byte 07",
            "atom_channel_invariant": "channel=MISSING iff atom=MISSING2; violation is NOT_QUALIFIED_MISSING_ATOM_MISMATCH",
            "channel_identity": "FRAME32(WAVE025_CHANNEL_V2S)||FRAME32(channel_ascii)||FRAME32(expected_channel_ascii)",
            "context_identity_term": ["family", "raw_CTX2", "channel_identity"],
            "missing_rule": "channel=MISSING requires expected_channel != NONE; all nonmissing channels require expected_channel=NONE",
            "occurrence_normalization": "aggregate identical row_identity_term occurrences by checked-u64 addition before emission; duplicate rows in an emitted vector are NOT_QUALIFIED_DUPLICATE_CATEGORICAL_ROW",
            "row_identity_term": ["family", "raw_CTX2", "channel_identity", "raw_32_byte_value_sha256"],
            "row_preimage": "FRAME32(WAVE025_CATEGORY_ROW_V2S)||FRAME32(family_utf8)||FRAME32(raw_CTX2)||FRAME32(channel_identity)||FRAME32(raw_32_byte_value_sha256)",
            "row_sha256": "lowercase_hex(SHA256(row_preimage)); derived check value, not an additional predictor member",
            "typed_value_preimage": "FRAME32(WAVE025_TYPED_VALUE_V2S)||FRAME32(atom)",
            "value_sha256": "lowercase_hex(SHA256(typed_value_preimage)); this is the typed value digest, not the row hash",
        },
        "context": {
            "CTX2": "FRAME32(WAVE025_CONTEXT_V2S)||U32_BE(segment_count)||segments",
            "segments": {
                "BAG_ITEM": "03",
                "DERIVED": "04||FRAME32(name_ascii)",
                "KEY": "01||FRAME32(name_utf8)",
                "ORDERED": "02||U32_BE(index)",
            },
        },
        "dependencies": {
            "model_input": {
                "required": True,
                "rule": "no model may depend on this candidate until it binds exact primitives, routing, feature-vector schema, predictor bytes and audit bytes",
            },
            "outer_predictor_audit_pair": {
                "audit_filename": AUDIT_FILENAME,
                "binding_fields_each": ["filename", "byte_length_u64", "sha256"],
                "failure_state": "NOT_QUALIFIED requires predictor_binding=null, no predictor bytes, and no outer pair; audit-only diagnostics remain classifier-ineligible",
                "forbidden_when": "NOT_QUALIFIED",
                "predictor_filename": PREDICTOR_FILENAME,
                "required_when": "QUALIFIED_FEATURE_EXTRACTION",
                "rule": "a QUALIFIED receipt-specific outer slot/leaf manifest must bind exact filename, length and sha256 for both artifacts; any mismatch is NOT_QUALIFIED_AUDIT_CROSS_FIELD",
                "schema": OUTER_PAIR_SCHEMA,
            },
            "routing_contract": {
                "exact_families": list(FAMILIES),
                "failure_on_absence": "NOT_QUALIFIED_ROUTING_PRECONDITION",
                "required": True,
                "required_machine_claims": [
                    "exact seven-family enum",
                    "complete family/channel/stat and expected-channel matrix",
                    "every context is canonical CTX2",
                    "every BAG call is nonempty",
                    "each BAG output numeric identity has exactly one authorized input channel",
                    "every scalar and active union leaf has exactly one include or exclude owner",
                    "categorical occurrences are passed before aggregation",
                ],
            },
            "semantic_validator": {
                "failure_on_absence": "NOT_QUALIFIED_ROUTING_PRECONDITION",
                "required": True,
                "rule": "standard JSON Schema is structural only; the bound provider source must implement the normative semantic rules and fail closed",
            },
        },
        "exclusions": {
            "collector_path_routing": "not decided by this primitives candidate",
            "model_layout_C01_C05": "not decided by this primitives candidate",
            "receipt_schema": "not decided by this primitives candidate",
        },
        "failure_codes": failure_codes(),
        "framing": {
            "FRAME32": "U32_BE(byte_length)||bytes",
            "U32_BE": "unsigned 32-bit big-endian",
            "all_hash_fields_framed": True,
        },
        "limits": {
            "max_abs_decimal_exponent": str(MAX_ABS_EXP10),
            "max_canonical_numerator_or_denominator_digits": str(MAX_RATIONAL_DECIMAL_DIGITS),
            "max_container_items": str(MAX_CONTAINER_ITEMS),
            "max_decoded_input_bytes": str(MAX_INPUT_BYTES),
            "max_frame_bytes": str(MAX_FRAME_BYTES),
            "max_json_depth": str(MAX_JSON_DEPTH),
            "max_json_depth_unit": "inclusive root-to-value count; root is depth 1",
            "max_number_lexeme_bytes": str(MAX_NUMBER_LEXEME_BYTES),
            "max_number_lexeme_bytes_unit": "all ASCII bytes of the JSON number token including sign, dot, e/E and exponent sign/digits",
            "max_significand_digits": str(MAX_SIGNIFICAND_DIGITS),
            "max_significand_digits_unit": "all mantissa digits including leading and trailing zeroes; excludes signs, decimal point and exponent syntax",
            "max_decoded_input_bytes_unit": "exact post-transport, pre-JSON-parse document bytes including whitespace and escape syntax",
            "wire_frame_u32_max": str(U32_MAX),
        },
        "ngram": {
            "bucket": "U32_BE(SHA256(preimage)[0:4]) mod 4096",
            "channel_identity": "CHANNEL_IDENTITY(LEXICAL_NGRAM,NONE)",
            "companion_numeric": ["lexical.full_byte_length", "lexical.truncated"],
            "direct_output": "aggregate by family and bucket only after route-aware hashing",
            "n": ["1", "2", "3", "4"],
            "preimage": "FRAME32(WAVE025_UTF8_NGRAM_V2S)||FRAME32(family_utf8)||FRAME32(raw_lexical_route_CTX2)||FRAME32(channel_identity)||FRAME32(single_unsigned_n_byte)||FRAME32(gram_bytes)",
            "scan": "raw UTF-8 bytes; overlapping windows",
            "truncation": "length<=4096 one full span; otherwise bytes[0:2048] and bytes[len-2048:len] independently; no decode/repair and no cross-gap gram",
        },
        "numeric": {
            "decimal_integer_string": "only routing-declared parser; grammar 0|-?[1-9][0-9]*",
            "derived_bounds": "the 4864 magnitude-digit ceiling is reapplied after every sum, delta, interpolation and other derived operation before emission",
            "digit_limit_sign": "minus sign is not a digit and does not count toward the 4864 numerator/denominator magnitude-digit ceiling",
            "exact_rational": "parse JSON number token as decimal mathematical value; reduce gcd; denominator positive; all signed zero becomes 0/1",
            "exponent_text": "leading exponent zeroes are allowed and do not create a separate digit limit; compare the mathematical signed exponent to abs<=4096 without unbounded integer conversion",
            "predictor_representation": "numerator and denominator are canonical decimal strings; no JSON float",
            "quantile_type7": "exact rational h=(m-1)*p; linear interpolation; m=1 returns sole value; m=0 undefined",
            "resource_failures": "any number limit violation is NOT_QUALIFIED_NUMERIC_BOUNDS",
        },
        "output": {
            "categorical_row_identity": ["family_utf8", "raw_CTX2", "channel_identity", "raw_value_digest"],
            "categorical_sort": "categorical row identity raw tuple ascending",
            "feature_vector_schema": "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE",
            "members": ["numeric", "categorical", "ngram_counts"],
            "ngram_sort": "family_utf8 then bucket numeric ascending",
            "numeric_identity": ["family_utf8", "raw_CTX2", "channel_ascii", "stat_ascii"],
            "numeric_sort": "numeric identity raw tuple ascending",
            "predictor_audit_physical_separation": "predictor contains no receipt/source/path/provenance/debug; audit sidecar binds predictor but predictor does not bind audit; external exact-pair binding is mandatory",
        },
        "raw_json_input": {
            "duplicate_key_boundary": "parse exact raw JSON bytes with an order-preserving object-pairs callback; reject a repeated decoded key before conversion to a map",
            "invalid_utf8": "reject any non-shortest or otherwise invalid raw UTF-8 before JSON parsing",
            "lone_surrogate": "reject decoded strings or keys containing U+D800..U+DFFF",
        },
        "semantic_validation": {
            "audit_arrays": {
                "excluded": ["path_json_pointer_utf8", "reason_code_ascii"],
                "failure_codes": ["failure_code_ascii"],
                "included": ["family_utf8", "raw_CTX2", "route_id_ascii", "path_json_pointer_utf8", "channel_ascii"],
                "routing_counts": ["route_id_ascii"],
                "truncation_audit": ["family_utf8", "raw_CTX2"],
                "unknown_paths": ["path_json_pointer_utf8"],
            },
            "audit_cross_fields": [
                "routing_counts exactly equal checked-u64 included multiplicity sums by route",
                "truncation spans exactly match full length and threshold",
                "all bindings are verified by exact byte readback",
                "qualified status has empty failure_codes and unknown_paths and an exact predictor binding",
            ],
            "feature_vector": [
                "all arrays are strictly sorted and identity-unique",
                "every CTX2 decodes canonically",
                "all counts and rational bounds are enforced numerically",
                "bound routing family/channel/stat matrix accepts every row",
                "MISSING channel/value bidirectional invariant was enforced before digesting",
            ],
        },
        "schema": "WAVE025_V2S_PRIMITIVES_CANDIDATE",
        "shape": {
            "ascii_classes": "count raw bytes only",
            "non_ascii": "count Unicode scalar values > U+007F",
            "stats": [
                "shape.byte_length",
                "shape.codepoint_length",
                "shape.ascii_alpha",
                "shape.ascii_digit",
                "shape.slash",
                "shape.dot",
                "shape.dash",
                "shape.underscore",
                "shape.colon",
                "shape.whitespace",
                "shape.non_ascii",
                "shape.truncated",
            ],
            "truncated": "1 iff full raw UTF-8 byte length > 4096 else 0",
        },
        "tve2": {
            "array": "05||U32_BE(count)||FRAME32(TVE2(item_0))... preserving order",
            "boolean_false": "01",
            "boolean_true": "02",
            "missing2_non_json": "07",
            "null": "00",
            "number": "03||FRAME32(numerator_ascii)||FRAME32(denominator_ascii)",
            "object": "06||U32_BE(count)||FRAME32(key_utf8)||FRAME32(TVE2(value))... with keys raw-UTF8 ascending; duplicate key fails",
            "string": "04||FRAME32(raw_utf8)",
        },
        "unicode": {
            "normalization": "none",
            "scalar_requirement": "lone surrogate fails",
            "utf8": "shortest legal encoding",
        },
    }


def _case_typed_categories() -> dict[str, Any]:
    family = "F02_ARGV_ENV_CWD"
    context = ctx2((("KEY", "value"),))
    cases = [
        ("string", "EXACT_CATEGORY", "NONE", "1"),
        ("number", "TYPED_NUMBER_CATEGORY", "NONE", JsonNumber("1.0")),
        ("null", "EXACT_CATEGORY", "NONE", None),
        ("missing", "MISSING", "EXACT_CATEGORY", MISSING),
    ]
    entries = []
    evaluations = []
    for label, channel, expected, value in cases:
        evaluation = category_eval(family, context, channel, value, expected)
        evaluation["label"] = label
        evaluations.append(evaluation)
        entries.append(categorical_entry(family, context, channel, expected, value))
    output = vector(categorical=entries)
    return {
        "case_id": "TYPED_STRING_NUMBER_NULL_MISSING",
        "expected": {
            "categorical_order": [
                [row["channel"], row["expected_channel"], row["value_sha256"]]
                for row in output["features"]["categorical"]
            ],
            "evaluations": evaluations,
            **artifact_binding(output),
        },
        "input": {
            "context_segments": [{"kind": "KEY", "value": "value"}],
            "family": family,
            "values": ["JSON_STRING_1", "JSON_NUMBER_1.0", "JSON_NULL", "MISSING2_FOR_EXPECTED_EXACT_CATEGORY"],
        },
        "operation": "CATEGORY_ROWS",
    }


def _case_bag_multiset() -> dict[str, Any]:
    family = "F02_ARGV_ENV_CWD"
    base_context = ctx2((("KEY", "environment"), ("BAG_ITEM", None), ("KEY", "key")))
    output_context = ctx2(
        (("KEY", "environment"), ("BAG_ITEM", None), ("KEY", "key"), ("DERIVED", "bag.shape.byte_length"))
    )
    values = [Fraction(1, 1), Fraction(4, 1)]
    summary = bag_summary(values)
    entries = [numeric_entry(family, output_context, "BAG_SUMMARY", stat, value) for stat, value in summary.items()]
    output = vector(numeric=entries)
    return {
        "case_id": "BAG_MULTISET_TWO_VALUES",
        "expected": {
            "base_context_hex": base_context.hex(),
            "output_context_hex": output_context.hex(),
            "summary": {key: {"denominator": str(value.denominator), "numerator": str(value.numerator)} for key, value in sorted(summary.items())},
            **artifact_binding(output),
        },
        "input": {"base_stat": "shape.byte_length", "cardinality": "BAG_MULTISET", "values": ["1/1", "4/1"]},
        "operation": "NUMERIC_CARDINALITY",
    }


def _case_ordered_singleton() -> dict[str, Any]:
    family = "F06_TIMING_AND_ERRORS"
    parent = ctx2((("KEY", "timing"), ("KEY", "immediate_delta_ns")))
    item_context = ctx2((("KEY", "timing"), ("KEY", "immediate_delta_ns"), ("ORDERED", 0)))
    summary_context = ctx2(
        (("KEY", "timing"), ("KEY", "immediate_delta_ns"), ("DERIVED", "series.raw.value"))
    )
    value = Fraction(7, 1)
    entries = [numeric_entry(family, item_context, "ORDERED_ITEM", "raw.value", value)]
    summary = series_summary([value])
    entries.extend(
        numeric_entry(family, summary_context, "ORDERED_SUMMARY", stat, result) for stat, result in summary.items()
    )
    output = vector(numeric=entries)
    return {
        "case_id": "ORDERED_SERIES_SINGLETON",
        "expected": {
            "item_context_hex": item_context.hex(),
            "parent_context_hex": parent.hex(),
            "summary_context_hex": summary_context.hex(),
            "summary": {key: {"denominator": str(result.denominator), "numerator": str(result.numerator)} for key, result in sorted(summary.items())},
            **artifact_binding(output),
        },
        "input": {"base_stat": "raw.value", "cardinality": "ORDERED_SERIES", "values": ["7/1"]},
        "operation": "NUMERIC_CARDINALITY",
    }


def _case_route_aware_ngram() -> dict[str, Any]:
    family = "F02_ARGV_ENV_CWD"
    cwd = ctx2((("KEY", "cwd"),))
    argv0 = ctx2((("KEY", "argv"), ("ORDERED", 0)))
    cwd_eval = ngram_eval(family, cwd, 2, b"ab")
    argv_eval = ngram_eval(family, argv0, 2, b"ab")
    buckets: dict[int, int] = {}
    for row in (cwd_eval, argv_eval):
        bucket = int(row["bucket_u16"])
        buckets[bucket] = buckets.get(bucket, 0) + 1
    output = vector(ngram_counts=[ngram_entry(family, bucket, count) for bucket, count in buckets.items()])
    return {
        "case_id": "ROUTE_AWARE_CWD_ARGV_NGRAM",
        "expected": {
            "argv0": argv_eval,
            "cwd": cwd_eval,
            "distinct_digest": cwd_eval["digest_sha256"] != argv_eval["digest_sha256"],
            **artifact_binding(output),
        },
        "input": {"family": family, "gram_utf8_hex": "6162", "n_u8": "2", "routes": ["cwd", "argv[0]"]},
        "operation": "NGRAM_HASH",
    }


def _case_unicode_split() -> dict[str, Any]:
    family = "F07_VISIBLE_CANARY"
    context = ctx2((("KEY", "visible_canaries"), ("BAG_ITEM", None), ("KEY", "source")))
    text = "A" + ("€" * 1365) + "B"
    raw = text.encode("utf-8")
    scan = scan_ngrams(family, context, text)
    output = vector(
        numeric=[
            numeric_entry(family, context, "LEXICAL_META", "lexical.full_byte_length", Fraction(len(raw), 1)),
            numeric_entry(family, context, "LEXICAL_META", "lexical.truncated", Fraction(1, 1)),
        ],
        ngram_counts=[ngram_entry(family, bucket, count) for bucket, count in scan["bucket_counts"].items()],
    )
    return {
        "case_id": "UTF8_4097_BYTE_SPLIT_INSIDE_CODEPOINT",
        "expected": {
            "first_span_utf8_decodable": False,
            "full_input_sha256": sha256_hex(raw),
            "gram_evaluations": scan["gram_evaluations"],
            "last_span_utf8_decodable": False,
            "shape": {
                key: {"denominator": str(value.denominator), "numerator": str(value.numerator)}
                for key, value in sorted(string_shape(text).items())
            },
            "spans": scan["spans"],
            "truncated": scan["truncated"],
            **artifact_binding(output),
        },
        "input": {
            "construction": "ASCII A || U+20AC repeated 1365 || ASCII B",
            "full_byte_length_u64": str(len(raw)),
            "utf8_base64": base64.b64encode(raw).decode("ascii"),
        },
        "operation": "BOUNDED_RAW_UTF8_NGRAM",
    }


def _case_category_framing() -> dict[str, Any]:
    family = "F02_ARGV_ENV_CWD"
    first_context = ctx2((("KEY", "a"),))
    second_context = ctx2((("KEY", "ab"),))
    first = category_eval(family, first_context, "EXACT_CATEGORY", "bc")
    second = category_eval(family, second_context, "EXACT_CATEGORY", "c")
    output = vector(
        categorical=[
            categorical_entry(family, first_context, "EXACT_CATEGORY", "NONE", "bc"),
            categorical_entry(family, second_context, "EXACT_CATEGORY", "NONE", "c"),
        ]
    )
    return {
        "case_id": "CATEGORY_LENGTH_FRAMING_COLLISION_RESISTANCE",
        "expected": {
            "distinct_row_hash": first["row_sha256"] != second["row_sha256"],
            "first": first,
            "second": second,
            **artifact_binding(output),
        },
        "input": {
            "naive_payload_both_ascii": "abc",
            "tuple_1": ["KEY(a)", "STRING(bc)"],
            "tuple_2": ["KEY(ab)", "STRING(c)"],
        },
        "operation": "CATEGORY_FRAMING",
    }


def _case_categorical_occurrence_aggregation() -> dict[str, Any]:
    family = "F02_ARGV_ENV_CWD"
    context = ctx2((("KEY", "cwd"),))
    occurrence = categorical_entry(family, context, "EXACT_CATEGORY", "NONE", "/work")
    output = vector(categorical=[occurrence, occurrence])
    return {
        "case_id": "CATEGORICAL_TWO_OCCURRENCES_ONE_ROW",
        "expected": {
            "emitted_count_u64": "2",
            "emitted_row_count_u64": "1",
            **artifact_binding(output),
        },
        "input": {"identical_occurrence_count_u64": "2", "zero_occurrence_rule": "OMIT_ROW"},
        "operation": "CATEGORICAL_OCCURRENCE_NORMALIZATION",
    }


def _case_bag_singleton() -> dict[str, Any]:
    summary = bag_summary([Fraction(7, 1)])
    return {
        "case_id": "BAG_MULTISET_SINGLETON",
        "expected": {
            "summary": {
                key: {"denominator": str(value.denominator), "numerator": str(value.numerator)}
                for key, value in sorted(summary.items())
            }
        },
        "input": {"values": ["7/1"]},
        "operation": "NUMERIC_CARDINALITY",
    }


def _case_leading_zero_exponent() -> dict[str, Any]:
    result = parse_json_number_lexeme("1e0000000")
    atom = tve2(JsonNumber("1e0000000"))
    return {
        "case_id": "LEADING_ZERO_EXPONENT_ACCEPTED",
        "expected": {
            "atom_hex": atom.hex(),
            "denominator": str(result.denominator),
            "numerator": str(result.numerator),
            "sha256": sha256_hex(atom),
        },
        "input": {"json_number_lexeme": "1e0000000"},
        "operation": "EXACT_RATIONAL_PARSE",
    }


def _case_ngram_collision_merge() -> dict[str, Any]:
    family = "F02_ARGV_ENV_CWD"
    first = ngram_eval(family, ctx2((("KEY", "r1"),)), 1, b"a")
    second = ngram_eval(family, ctx2((("KEY", "r16"),)), 1, b"a")
    if first["bucket_u16"] != second["bucket_u16"]:
        raise AssertionError("registered collision pair drift")
    output = vector(ngram_counts=[ngram_entry(family, int(first["bucket_u16"]), 2)])
    return {
        "case_id": "NGRAM_DISTINCT_ROUTE_DIGEST_BUCKET_COLLISION_MERGED",
        "expected": {
            "bucket_u16": first["bucket_u16"],
            "distinct_digest": first["digest_sha256"] != second["digest_sha256"],
            "emitted_count_u64": "2",
            "first_digest_sha256": first["digest_sha256"],
            "second_digest_sha256": second["digest_sha256"],
            **artifact_binding(output),
        },
        "input": {"gram_hex": "61", "routes": ["KEY(r1)", "KEY(r16)"]},
        "operation": "NGRAM_HASH_THEN_BUCKET_AGGREGATION",
    }


def _nested_array(levels: int) -> Any:
    value: Any = None
    for _ in range(levels):
        value = [value]
    return value


def _audit_fixture() -> tuple[dict[str, Any], bytes, bytes, dict[str, bytes], dict[str, Any]]:
    predictor_raw = canonical_json_bytes(vector())
    bound_files = {
        "FEATURE-VECTOR-V2S.candidate.schema.json": b"feature-schema\n",
        "PROVIDER-SOURCE-MANIFEST.json": b"provider\n",
        "RECEIPT.json": b"receipt\n",
        "RECEIPT-SCHEMA.json": b"receipt-schema\n",
        "ROUTING.json": b"routing\n",
        "V2S-PRIMITIVES.candidate.json": b"primitives\n",
    }

    def binding(filename: str) -> dict[str, str]:
        raw = bound_files[filename]
        return {"byte_length_u64": str(len(raw)), "filename": filename, "sha256": sha256_hex(raw)}

    audit = {
        "bindings": {
            "feature_primitives": binding("V2S-PRIMITIVES.candidate.json"),
            "feature_routing": binding("ROUTING.json"),
            "feature_vector_schema": binding("FEATURE-VECTOR-V2S.candidate.schema.json"),
            "provider_source_manifest": binding("PROVIDER-SOURCE-MANIFEST.json"),
            "receipt_bytes": binding("RECEIPT.json"),
            "receipt_schema": binding("RECEIPT-SCHEMA.json"),
        },
        "excluded": [],
        "failure_codes": [],
        "included": [
            {
                "channel": "EXACT_CATEGORY",
                "context_hex": ctx2((("KEY", "a"),)).hex(),
                "family": "F02_ARGV_ENV_CWD",
                "multiplicity_u64": "1",
                "path_json_pointer": "/a",
                "route_id": "R001",
            },
            {
                "channel": "EXACT_CATEGORY",
                "context_hex": ctx2((("KEY", "b"),)).hex(),
                "family": "F02_ARGV_ENV_CWD",
                "multiplicity_u64": "1",
                "path_json_pointer": "/b",
                "route_id": "R001",
            },
        ],
        "predictor_binding": {
            "byte_length_u64": str(len(predictor_raw)),
            "schema": "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE",
            "sha256": sha256_hex(predictor_raw),
        },
        "routing_counts": [{"included_multiplicity_u64": "2", "route_id": "R001"}],
        "schema": "WAVE025_FEATURE_LEAF_AUDIT_V2S_CANDIDATE",
        "status": "QUALIFIED_FEATURE_EXTRACTION",
        "truncation_audit": [],
        "unknown_paths": [],
    }
    audit_raw = canonical_json_bytes(audit)
    outer = {
        "audit": {"byte_length_u64": str(len(audit_raw)), "filename": AUDIT_FILENAME, "sha256": sha256_hex(audit_raw)},
        "predictor": {"byte_length_u64": str(len(predictor_raw)), "filename": PREDICTOR_FILENAME, "sha256": sha256_hex(predictor_raw)},
        "schema": OUTER_PAIR_SCHEMA,
    }
    return audit, audit_raw, predictor_raw, bound_files, outer


def _case_audit_pair_binding() -> dict[str, Any]:
    audit, audit_raw, predictor_raw, bound_files, outer = _audit_fixture()
    validate_leaf_audit_semantics(
        audit,
        audit_raw=audit_raw,
        predictor_raw=predictor_raw,
        bound_files=bound_files,
        outer_pair=outer,
    )
    return {
        "case_id": "AUDIT_SORTED_CROSS_FIELD_AND_OUTER_PAIR",
        "expected": {
            "audit_length_u64": str(len(audit_raw)),
            "audit_sha256": sha256_hex(audit_raw),
            "outer_pair": outer,
            "predictor_length_u64": str(len(predictor_raw)),
            "predictor_sha256": sha256_hex(predictor_raw),
            "status": "QUALIFIED_FEATURE_EXTRACTION",
        },
        "input": {"included_multiplicity_sum_u64": "2", "outer_pair": "EXACT_BOTH_ARTIFACTS"},
        "operation": "AUDIT_SEMANTIC_VALIDATION",
    }


def _not_qualified_audit_fixture() -> tuple[dict[str, Any], bytes, dict[str, bytes]]:
    audit, _, _, bound_files, _ = _audit_fixture()
    audit["failure_codes"] = ["NOT_QUALIFIED_UNKNOWN_PATH"]
    audit["predictor_binding"] = None
    audit["status"] = "NOT_QUALIFIED"
    audit_raw = canonical_json_bytes(audit)
    validate_leaf_audit_semantics(
        audit,
        audit_raw=audit_raw,
        predictor_raw=None,
        bound_files=bound_files,
        outer_pair=None,
    )
    return audit, audit_raw, bound_files


def _case_not_qualified_no_predictor() -> dict[str, Any]:
    audit, audit_raw, _ = _not_qualified_audit_fixture()
    return {
        "case_id": "NOT_QUALIFIED_AUDIT_ONLY_NO_PREDICTOR_OR_PAIR",
        "expected": {
            "audit_filename": AUDIT_FILENAME,
            "audit_length_u64": str(len(audit_raw)),
            "audit_sha256": sha256_hex(audit_raw),
            "outer_pair": "ABSENT",
            "predictor_binding": audit["predictor_binding"],
            "predictor_bytes": "ABSENT",
            "status": "NOT_QUALIFIED",
        },
        "input": {"failure_code": "NOT_QUALIFIED_UNKNOWN_PATH"},
        "operation": "AUDIT_SEMANTIC_VALIDATION",
    }


def _not_qualified_mutation(kind: str) -> None:
    audit, _, bound_files = _not_qualified_audit_fixture()
    predictor_raw = None
    outer = None
    if kind == "attempted_predictor_bytes":
        predictor_raw = canonical_json_bytes(vector())
    elif kind == "predictor_binding":
        attempted = canonical_json_bytes(vector())
        audit["predictor_binding"] = {
            "byte_length_u64": str(len(attempted)),
            "schema": "WAVE025_FEATURE_VECTOR_V2S_CANDIDATE",
            "sha256": sha256_hex(attempted),
        }
    elif kind == "outer_pair":
        attempted = canonical_json_bytes(vector())
        outer = {
            "audit": {"byte_length_u64": "0", "filename": AUDIT_FILENAME, "sha256": "0" * 64},
            "predictor": {
                "byte_length_u64": str(len(attempted)),
                "filename": PREDICTOR_FILENAME,
                "sha256": sha256_hex(attempted),
            },
            "schema": OUTER_PAIR_SCHEMA,
        }
    else:
        raise AssertionError(kind)
    audit_raw = canonical_json_bytes(audit)
    validate_leaf_audit_semantics(
        audit,
        audit_raw=audit_raw,
        predictor_raw=predictor_raw,
        bound_files=bound_files,
        outer_pair=outer,
    )


def _audit_mutation(kind: str) -> None:
    audit, _, predictor_raw, bound_files, outer = _audit_fixture()
    if kind == "permutation":
        audit["included"] = list(reversed(audit["included"]))
    elif kind == "duplicate":
        audit["included"].append(copy.deepcopy(audit["included"][-1]))
        audit["routing_counts"][0]["included_multiplicity_u64"] = "3"
    elif kind == "routing_count":
        audit["routing_counts"][0]["included_multiplicity_u64"] = "1"
    elif kind == "outer_pair_absent":
        pass
    elif kind == "outer_predictor_filename":
        outer["predictor"]["filename"] = "wrong-predictor.json"
    elif kind == "outer_audit_filename":
        outer["audit"]["filename"] = "wrong-audit.json"
    elif kind == "outer_predictor_length":
        outer["predictor"]["byte_length_u64"] = str(len(predictor_raw) + 1)
    elif kind == "outer_audit_length":
        outer["audit"]["byte_length_u64"] = "0"
    elif kind == "outer_predictor_sha":
        outer["predictor"]["sha256"] = "0" * 64
    elif kind == "outer_audit_sha":
        outer["audit"]["sha256"] = "0" * 64
    else:
        raise AssertionError(kind)
    audit_raw = canonical_json_bytes(audit)
    if kind == "outer_pair_absent":
        outer = None
    else:
        if kind not in {"outer_audit_length", "outer_audit_sha"}:
            outer["audit"]["byte_length_u64"] = str(len(audit_raw))
            outer["audit"]["sha256"] = sha256_hex(audit_raw)
    validate_leaf_audit_semantics(
        audit,
        audit_raw=audit_raw,
        predictor_raw=predictor_raw,
        bound_files=bound_files,
        outer_pair=outer,
    )


def _case_depth_boundary() -> dict[str, Any]:
    atom = tve2(_nested_array(63))
    return {
        "case_id": "JSON_DEPTH_64_INCLUSIVE_ACCEPTED",
        "expected": {"atom_length_u64": str(len(atom)), "atom_sha256": sha256_hex(atom)},
        "input": {"array_container_levels": "63", "leaf_inclusive_depth": "64"},
        "operation": "TVE2",
    }


def _negative_case(case_id: str, operation: str, input_value: dict[str, str], function) -> dict[str, Any]:
    try:
        function()
    except V2SError as error:
        return {
            "case_id": case_id,
            "expected": {"failure_code": error.code},
            "input": input_value,
            "operation": operation,
        }
    raise AssertionError(f"negative golden did not fail: {case_id}")


def golden_candidate(primitives: dict[str, Any]) -> dict[str, Any]:
    cases = [
        _case_typed_categories(),
        _case_categorical_occurrence_aggregation(),
        _case_bag_multiset(),
        _case_bag_singleton(),
        _case_ordered_singleton(),
        _case_leading_zero_exponent(),
        _case_route_aware_ngram(),
        _case_ngram_collision_merge(),
        _case_unicode_split(),
        _case_category_framing(),
        _case_depth_boundary(),
        _case_audit_pair_binding(),
        _case_not_qualified_no_predictor(),
        _negative_case(
            "EMPTY_BAG_REJECTED",
            "NUMERIC_CARDINALITY",
            {"values": []},
            lambda: bag_summary([]),
        ),
        _negative_case(
            "MISSING_CHANNEL_WITH_NONMISSING_ATOM_REJECTED",
            "CATEGORY_ROWS",
            {"channel": "MISSING", "atom": "TVE2_NUMBER_1", "expected_channel": "EXACT_CATEGORY"},
            lambda: category_eval("F02_ARGV_ENV_CWD", ctx2((("KEY", "x"),)), "MISSING", JsonNumber("1"), "EXACT_CATEGORY"),
        ),
        _negative_case(
            "NONMISSING_CHANNEL_WITH_MISSING2_ATOM_REJECTED",
            "CATEGORY_ROWS",
            {"channel": "EXACT_CATEGORY", "atom": "MISSING2", "expected_channel": "NONE"},
            lambda: category_eval("F02_ARGV_ENV_CWD", ctx2((("KEY", "x"),)), "EXACT_CATEGORY", MISSING, "NONE"),
        ),
        _negative_case(
            "SIGNIFICAND_ALL_MANTISSA_DIGITS_BOUND",
            "EXACT_RATIONAL_PARSE",
            {"construction": "0. plus 767 zeroes plus 1", "mantissa_digit_count_u64": "769"},
            lambda: parse_json_number_lexeme("0." + ("0" * 767) + "1"),
        ),
        _negative_case(
            "DERIVED_RATIONAL_4865_DIGITS_REJECTED",
            "NUMERIC_CARDINALITY",
            {"construction": "sum of two individually 4864-digit all-nine integers"},
            lambda: bag_summary([Fraction(int("9" * 4864), 1), Fraction(int("9" * 4864), 1)]),
        ),
        _negative_case(
            "JSON_DEPTH_65_INCLUSIVE_REJECTED",
            "TVE2",
            {"array_container_levels": "64", "leaf_inclusive_depth": "65"},
            lambda: tve2(_nested_array(64)),
        ),
        _negative_case(
            "UNKNOWN_CTX2_SEGMENT_REJECTED",
            "CTX2_VALIDATE",
            {"construction": "valid domain and count one followed by tag ff"},
            lambda: validate_ctx2_bytes(frame32(b"WAVE025_CONTEXT_V2S") + u32(1) + b"\xff"),
        ),
        _negative_case(
            "DUPLICATE_JSON_KEY_REJECTED_BEFORE_MAP",
            "RAW_JSON_PARSE",
            {"raw_utf8_hex": b'{"a":1,"a":2}'.hex()},
            lambda: parse_json_document(b'{"a":1,"a":2}'),
        ),
        _negative_case(
            "RAW_UTF8_OVERLONG_REJECTED",
            "RAW_JSON_PARSE",
            {"raw_hex": b'"\xc0\xaf"'.hex()},
            lambda: parse_json_document(b'"\xc0\xaf"'),
        ),
        _negative_case(
            "RAW_UTF8_LONE_CONTINUATION_REJECTED",
            "RAW_JSON_PARSE",
            {"raw_hex": b'"\x80"'.hex()},
            lambda: parse_json_document(b'"\x80"'),
        ),
        _negative_case(
            "JSON_LONE_SURROGATE_REJECTED",
            "TVE2",
            {"raw_utf8": "JSON string escape for U+D800"},
            lambda: tve2(parse_json_document(b'"\\ud800"')),
        ),
        _negative_case(
            "AUDIT_INCLUDED_PERMUTATION_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "reverse included array"},
            lambda: _audit_mutation("permutation"),
        ),
        _negative_case(
            "AUDIT_INCLUDED_DUPLICATE_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "duplicate included identity"},
            lambda: _audit_mutation("duplicate"),
        ),
        _negative_case(
            "AUDIT_ROUTING_COUNT_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"declared": "1", "included_sum": "2"},
            lambda: _audit_mutation("routing_count"),
        ),
        _negative_case(
            "AUDIT_OUTER_PAIR_ABSENT_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"outer_pair": "ABSENT"},
            lambda: _audit_mutation("outer_pair_absent"),
        ),
        _negative_case(
            "AUDIT_OUTER_PREDICTOR_FILENAME_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "predictor filename"},
            lambda: _audit_mutation("outer_predictor_filename"),
        ),
        _negative_case(
            "AUDIT_OUTER_AUDIT_FILENAME_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "audit filename"},
            lambda: _audit_mutation("outer_audit_filename"),
        ),
        _negative_case(
            "AUDIT_OUTER_PREDICTOR_LENGTH_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "predictor byte length"},
            lambda: _audit_mutation("outer_predictor_length"),
        ),
        _negative_case(
            "AUDIT_OUTER_AUDIT_LENGTH_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "audit byte length"},
            lambda: _audit_mutation("outer_audit_length"),
        ),
        _negative_case(
            "AUDIT_OUTER_PREDICTOR_SHA_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "predictor sha256"},
            lambda: _audit_mutation("outer_predictor_sha"),
        ),
        _negative_case(
            "AUDIT_OUTER_AUDIT_SHA_MISMATCH_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "audit sha256"},
            lambda: _audit_mutation("outer_audit_sha"),
        ),
        _negative_case(
            "NOT_QUALIFIED_ATTEMPTED_PREDICTOR_BYTES_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "predictor bytes present while NOT_QUALIFIED"},
            lambda: _not_qualified_mutation("attempted_predictor_bytes"),
        ),
        _negative_case(
            "NOT_QUALIFIED_PREDICTOR_BINDING_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "predictor_binding non-null while NOT_QUALIFIED"},
            lambda: _not_qualified_mutation("predictor_binding"),
        ),
        _negative_case(
            "NOT_QUALIFIED_OUTER_PAIR_REJECTED",
            "AUDIT_SEMANTIC_VALIDATION",
            {"mutation": "outer pair present while NOT_QUALIFIED"},
            lambda: _not_qualified_mutation("outer_pair"),
        ),
        _negative_case(
            "INVALID_NUMERIC_EXPONENT_BOUND",
            "EXACT_RATIONAL_PARSE",
            {"json_number_lexeme": "1e4097"},
            lambda: parse_json_number_lexeme("1e4097"),
        ),
        _negative_case(
            "INVALID_NUMBER_LEXEME_BYTE_BOUND",
            "EXACT_RATIONAL_PARSE",
            {"construction": "1025 ASCII digits '1'", "input_sha256": sha256_hex(b"1" * 1025)},
            lambda: parse_json_number_lexeme("1" * 1025),
        ),
        _negative_case(
            "INVALID_FRAME_U32_BOUND",
            "FRAME32_LENGTH_CHECK",
            {"declared_byte_length_u64": str(1 << 32)},
            lambda: validate_frame_length(1 << 32),
        ),
        _negative_case(
            "INVALID_COUNT_U64_BOUND",
            "CATEGORICAL_COUNT_CHECK",
            {"declared_count": str(1 << 64)},
            lambda: categorical_entry(
                "F02_ARGV_ENV_CWD", ctx2((("KEY", "x"),)), "EXACT_CATEGORY", "NONE", "x", 1 << 64
            ),
        ),
    ]
    primitives_bytes = canonical_json_bytes(primitives)
    oracle_bytes = Path(__file__).resolve().read_bytes()
    return {
        "bindings": {
            "oracle_source": {
                "authoritative": False,
                "byte_length_u64": str(len(oracle_bytes)),
                "filename": "v2s_primitives_oracle.py",
                "role": "non-authoritative fixture generator and byte verifier",
                "sha256": sha256_hex(oracle_bytes),
            },
            "primitives_candidate": {
                "byte_length_u64": str(len(primitives_bytes)),
                "filename": "V2S-PRIMITIVES.candidate.json",
                "sha256": sha256_hex(primitives_bytes),
            },
        },
        "candidate_status": "NOT_ADOPTED__PUBLIC_PRIMITIVE_GOLDENS_ONLY",
        "cases": cases,
        "schema": "WAVE025_GOLDEN_V2S_PRIMITIVES_CANDIDATE",
    }


def build_artifacts() -> dict[str, dict[str, Any]]:
    primitives = primitives_candidate()
    return {
        "FEATURE-LEAF-AUDIT-V2S.candidate.schema.json": leaf_audit_schema(),
        "FEATURE-VECTOR-V2S.candidate.schema.json": feature_vector_schema(),
        "GOLDEN-V2S-PRIMITIVES.candidate.json": golden_candidate(primitives),
        "V2S-PRIMITIVES.candidate.json": primitives,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-bundle", action="store_true", help="emit filename -> canonical UTF-8 content JSON")
    parser.add_argument("--check", action="store_true", help="check candidate artifacts beside this script")
    parser.add_argument("--write", action="store_true", help="regenerate the four canonical candidate JSON artifacts")
    args = parser.parse_args()
    artifacts = build_artifacts()
    if args.emit_bundle:
        bundle = {name: canonical_json_bytes(value).decode("utf-8") for name, value in artifacts.items()}
        print(json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if args.check:
        base = Path(__file__).resolve().parent
        for name, value in artifacts.items():
            actual = (base / name).read_bytes()
            expected = canonical_json_bytes(value)
            if actual != expected:
                raise SystemExit(f"MISMATCH:{name}")
        print("V2S primitive candidate artifacts: byte-exact")
    if args.write:
        base = Path(__file__).resolve().parent
        for name, value in artifacts.items():
            (base / name).write_bytes(canonical_json_bytes(value))
        print("V2S primitive candidate artifacts: regenerated")
    if not args.emit_bundle and not args.check and not args.write:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
