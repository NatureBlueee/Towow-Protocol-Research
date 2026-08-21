#!/usr/bin/env python3
"""Read-only, fail-closed Wave025 V1.3 F batch adapter.

This module is deliberately independent of the runner, collector, and prior
evaluator.  It verifies runner-owned evidence from the published contract,
shared evidence profile/schema, and raw batch bytes, then constructs records
for ``engine.py``.  It never writes into a batch and never emits a qualification
verdict.

Only the observed V1.3 F interface is supported.  A future V1.4 interface that
embeds self-contained feature/profile bytes must receive a new explicit adapter
version; this implementation fails closed on it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import pathlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


WAVE_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROFILE_DIR = WAVE_ROOT / "evidence-profile"
DEFAULT_PROFILE = PROFILE_DIR / "SHARED-EVIDENCE-PROFILE.candidate.json"
DEFAULT_PROFILE_SCHEMA = PROFILE_DIR / "SHARED-EVIDENCE-PROFILE.schema.json"
DEFAULT_OBJECT_SCHEMA = PROFILE_DIR / "RUNNER-EVIDENCE-OBJECTS.schema.json"
DEFAULT_FEATURE_SPEC = WAVE_ROOT / "feature-spec" / "FEATURE-SPEC.json"
DEFAULT_BATCH_CONTRACT = WAVE_ROOT / "BATCH-EVIDENCE-CONTRACT.md"

ROOT_JSON = {
    "precommit.json": "precommit",
    "public-plan.json": "publicPlan",
    "runner-private-state.json": "privateState",
    "anchor-receipt.json": "anchor",
    "closed.json": "closed",
    "reveal.json": "reveal",
}
ROOT_ALLOWED = set(ROOT_JSON) | {"evaluation.json", "slots"}
SLOT_FILES = {
    "collector-exit-code.bin",
    "collector-features.json",
    "collector-out.bin",
    "collector-ready.bin",
    "collector-stderr.bin",
    "collector-stdout.bin",
    "docker-events.jsonl",
    "docker-inspect-post.json",
    "docker-inspect-pre.json",
    "host-launch.json",
    "slot-receipt.json",
    "supervisor-control-stderr.bin",
    "supervisor-control-stdout.bin",
}


class BatchAdapterError(RuntimeError):
    """Base fail-closed adapter error."""


class UnsupportedBatchVersion(BatchAdapterError):
    pass


class CanonicalJSONError(BatchAdapterError):
    pass


class SchemaValidationError(BatchAdapterError):
    pass


class EvidenceIntegrityError(BatchAdapterError):
    pass


@dataclass(frozen=True)
class BatchAdapterResult:
    records: Tuple[Mapping[str, Any], ...]
    host_only_rows: Tuple[Mapping[str, Any], ...]
    evidence_receipt: Mapping[str, Any]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _reject_duplicates(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalJSONError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(raw: bytes, where: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicates,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              CanonicalJSONError(f"non-finite JSON value at {where}: {value}")))
    except BatchAdapterError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalJSONError(f"invalid UTF-8 JSON at {where}: {exc}") from exc


def _read_bytes(path: pathlib.Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise EvidenceIntegrityError(f"required regular file missing or symlinked: {path}")
    return path.read_bytes()


def _read_json(path: pathlib.Path, *, canonical: bool) -> Tuple[Any, bytes]:
    raw = _read_bytes(path)
    value = _parse_json(raw, str(path))
    if canonical and raw != canonical_bytes(value):
        raise CanonicalJSONError(f"non-canonical JSON bytes: {path}")
    return value, raw


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceIntegrityError(message)


def _decode64(value: str, where: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise EvidenceIntegrityError(f"invalid base64 at {where}") from exc


class _HmacStream:
    def __init__(self, seed: bytes, label: bytes):
        self.seed = seed
        self.label = label
        self.counter = 0
        self.buffer = bytearray()

    def _fill(self, count: int) -> None:
        while len(self.buffer) < count:
            message = self.label + b"\x00" + self.counter.to_bytes(8, "big")
            self.buffer.extend(hmac.new(self.seed, message, hashlib.sha256).digest())
            self.counter += 1

    def take(self, count: int) -> bytes:
        self._fill(count)
        value = bytes(self.buffer[:count])
        del self.buffer[:count]
        return value

    def randbelow(self, upper: int) -> int:
        if upper <= 0:
            raise ValueError("upper must be positive")
        width = max(1, ((upper - 1).bit_length() + 7) // 8)
        ceiling = 1 << (8 * width)
        limit = ceiling - ceiling % upper
        while True:
            draw = int.from_bytes(self.take(width), "big")
            if draw < limit:
                return draw % upper


def _shuffle(values: Sequence[Any], seed: bytes, label: bytes) -> List[Any]:
    result = list(values)
    stream = _HmacStream(seed, label)
    for index in range(len(result) - 1, 0, -1):
        other = stream.randbelow(index + 1)
        result[index], result[other] = result[other], result[index]
    return result


def _mapping_public(private_item: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "block": private_item["block"],
        "canary_token_or_null": private_item["private_canary_token_or_null"],
        "challenge": private_item["challenge"],
        "measurement_padding_bytes": private_item["measurement_padding_bytes"],
        "opaque_slot_id": private_item["opaque_slot_id"],
        "phase": private_item["phase"],
        "role": private_item["role"],
    }


def _merkle(slot_receipts: Sequence[Tuple[str, bytes]]) -> str:
    level = [hashlib.sha256(raw).digest() for _, raw in sorted(slot_receipts)]
    if not level:
        raise EvidenceIntegrityError("V1 Merkle tree may not be empty")
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                 for i in range(0, len(level), 2)]
    return level[0].hex()


class BatchAdapter:
    """Verify an observed V1.3 F batch and construct engine records."""

    def __init__(self, *, profile_path: pathlib.Path = DEFAULT_PROFILE,
                 profile_schema_path: pathlib.Path = DEFAULT_PROFILE_SCHEMA,
                 object_schema_path: pathlib.Path = DEFAULT_OBJECT_SCHEMA,
                 feature_spec_path: pathlib.Path = DEFAULT_FEATURE_SPEC,
                 batch_contract_path: pathlib.Path = DEFAULT_BATCH_CONTRACT,
                 enforce_f_root_locks: bool = True):
        self.profile, self.profile_raw = _read_json(pathlib.Path(profile_path), canonical=False)
        profile_schema, _ = _read_json(pathlib.Path(profile_schema_path), canonical=False)
        self.object_schema, _ = _read_json(pathlib.Path(object_schema_path), canonical=False)
        try:
            Draft202012Validator(profile_schema).validate(self.profile)
        except ValidationError as exc:
            raise SchemaValidationError(f"shared evidence profile schema failure: {exc.message}") from exc
        self.validators = {
            name: Draft202012Validator({"$ref": f"#/$defs/{name}",
                                        "$defs": self.object_schema["$defs"]})
            for name in ROOT_JSON.values()
        }
        self.validators.update({
            "hostLaunch": Draft202012Validator({"$ref": "#/$defs/hostLaunch",
                                                  "$defs": self.object_schema["$defs"]}),
            "slotReceipt": Draft202012Validator({"$ref": "#/$defs/slotReceipt",
                                                   "$defs": self.object_schema["$defs"]}),
        })
        self.feature_spec_path = pathlib.Path(feature_spec_path)
        self.batch_contract_path = pathlib.Path(batch_contract_path)
        self.enforce_f_root_locks = enforce_f_root_locks

    def _validate(self, value: Any, name: str, where: str) -> None:
        errors = sorted(self.validators[name].iter_errors(value), key=lambda e: list(e.absolute_path))
        if errors:
            error = errors[0]
            path = "/" + "/".join(str(x) for x in error.absolute_path)
            raise SchemaValidationError(f"{where}{path}: {error.message}")

    def _check_external_locks(self, precommit: Mapping[str, Any]) -> Dict[str, str]:
        contract_raw = _read_bytes(self.batch_contract_path)
        feature_raw = _read_bytes(self.feature_spec_path)
        contract_hash = sha256_bytes(contract_raw)
        feature_hash = sha256_bytes(feature_raw)
        _assert(contract_hash == precommit["batch_contract_sha256"],
                "batch contract bytes do not match precommit")
        _assert(feature_hash == precommit["feature_spec_sha256"],
                "external FEATURE-SPEC bytes do not match precommit")
        locks = self.profile["source_locks"]
        _assert(contract_hash == locks["batch_contract"]["sha256"],
                "batch contract bytes do not match shared profile")
        _assert(feature_hash == self.profile["feature_and_profile_bytes"]["full_feature_spec"]["sha256"],
                "FEATURE-SPEC bytes do not match shared profile")
        for field, lock_name in (
            ("runner_source_sha256", "runner"),
            ("qualification_contract_sha256", "qualification_contract"),
            ("collector_source_sha256", "collector_source"),
            ("collector_dockerfile_sha256", "collector_dockerfile"),
        ):
            _assert(precommit[field] == locks[lock_name]["sha256"],
                    f"precommitted {field} differs from shared profile lock")
        return {"batch_contract_sha256": contract_hash, "feature_spec_sha256": feature_hash}

    def _reconstruct(self, precommit: Mapping[str, Any], public: Mapping[str, Any],
                     private: Mapping[str, Any], reveal: Mapping[str, Any],
                     public_raw: bytes) -> List[Dict[str, Any]]:
        domains = reveal["domains"]
        _assert(domains == private["domains"], "private/reveal domain secrets differ")
        decoded: Dict[str, Tuple[bytes, bytes]] = {}
        for name in ("PRIVATE_ASSIGNMENT_ORDER", "PUBLIC_ID", "MEASUREMENT_PADDING"):
            item = domains[name]
            try:
                seed = bytes.fromhex(item["seed_hex"])
                nonce = bytes.fromhex(item["nonce_hex"])
            except ValueError as exc:
                raise EvidenceIntegrityError(f"invalid hex in domain {name}") from exc
            _assert(len(seed) == len(nonce) == 32, f"wrong secret size in {name}")
            decoded[name] = seed, nonce

        commitment_fields = {
            "PRIVATE_ASSIGNMENT_ORDER": "assignment_commitment",
            "PUBLIC_ID": "public_id_commitment",
            "MEASUREMENT_PADDING": "padding_commitment",
        }
        for name, field in commitment_fields.items():
            seed, nonce = decoded[name]
            actual = sha256_bytes(name.encode() + b"\x00" + seed + b"\x00" + nonce + b"\x00" + public_raw)
            _assert(actual == precommit[field], f"{name} commitment mismatch")

        assignment_seed = decoded["PRIVATE_ASSIGNMENT_ORDER"][0]
        public_seed = decoded["PUBLIC_ID"][0]
        padding_seed = decoded["MEASUREMENT_PADDING"][0]
        block_lookup = {item["block"]: item for item in precommit["block_plan"]["blocks"]}
        expected: List[Dict[str, Any]] = []
        layout_index = 0
        family_by_challenge = {"D0-HOST-LEAK": "D0_RESIDUE",
                               "D1-OCI-CANARY": "D1_CURRENT",
                               "T-OCI-ISOLATED": None}
        for challenge in precommit["challenges"]:
            for phase in ("calibration", "holdout"):
                blocks = sorted(key for key in block_lookup
                                if key.startswith(f"{challenge}:{phase}:") )
                _assert(len(blocks) == 1, "V1.3 smoke requires exactly one block per split")
                block = blocks[0]
                block_item = block_lookup[block]
                size = precommit["sample_plan"][challenge][phase]
                _assert(size == block_item["size"] and size % 2 == 0,
                        f"invalid block/sample size for {block}")
                roles = ["S"] * (size // 2) + ["R"] * (size // 2)
                roles = _shuffle(roles, assignment_seed, b"roles\x00" + block.encode())
                for role in roles:
                    slot_id = "s_" + hmac.new(
                        public_seed,
                        b"W025-PUBLIC-ID-V1\x00" + layout_index.to_bytes(8, "big"),
                        hashlib.sha256,
                    ).hexdigest()[:32]
                    padding = _HmacStream(
                        padding_seed, b"W025-PADDING-V1\x00" + slot_id.encode()
                    ).randbelow(257)
                    family = family_by_challenge[challenge]
                    token = None
                    if family is not None:
                        token = "WAVE025_CANARY_" + family + "_" + hmac.new(
                            assignment_seed,
                            f"W025-{family}-TOKEN-V1".encode() + b"\x00" + role.encode(),
                            hashlib.sha256,
                        ).hexdigest()[:24]
                    expected.append({
                        "block": block,
                        "challenge": challenge,
                        "measurement_padding_bytes": padding,
                        "opaque_slot_id": slot_id,
                        "phase": phase,
                        "private_canary_token_or_null": token,
                        "role": role,
                    })
                    layout_index += 1

        _assert(expected == private["mapping"], "private mapping does not match deterministic reconstruction")
        _assert([_mapping_public(x) for x in expected] == reveal["mapping"],
                "reveal mapping does not match deterministic reconstruction")
        ids = [item["opaque_slot_id"] for item in expected]
        _assert(len(ids) == len(set(ids)) == public["slot_count"],
                "population count or opaque ID uniqueness mismatch")
        expected_order = _shuffle(ids, assignment_seed, b"execution-order")
        _assert(expected_order == private["execution_order"] == reveal["execution_order"],
                "execution order does not match deterministic reconstruction")
        public_slots = sorted((x["opaque_slot_id"], x["challenge"]) for x in public["slots"])
        expected_slots = sorted((x["opaque_slot_id"], x["challenge"]) for x in expected)
        _assert(public_slots == expected_slots, "public slot population/mapping mismatch")
        for block in block_lookup:
            block_roles = [x["role"] for x in expected if x["block"] == block]
            _assert(block_roles.count("S") == block_roles.count("R") == len(block_roles) // 2,
                    f"strict block balance failure: {block}")
        return expected

    def _event_projection(self, raw: bytes, host: Mapping[str, Any], slot_id: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceIntegrityError(f"non-UTF8 docker event stream: {slot_id}") from exc
        lines = [line for line in text.splitlines() if line]
        _assert(len(lines) == 19, f"docker event count must be exactly 19 for {slot_id}")
        objects = [_parse_json(line.encode(), f"{slot_id}/docker-events.jsonl:{i + 1}")
                   for i, line in enumerate(lines)]
        expected_actions = self.profile["post_cut_profile"]["complete_event_action_sequence"]
        actions: List[str] = []
        projections: List[Dict[str, Any]] = []
        last_time = -1
        for index, obj in enumerate(objects):
            _assert(set(obj) == {"Type", "Action", "Actor", "scope", "time", "timeNano"},
                    f"unknown/missing docker event envelope field at {slot_id}:{index + 1}")
            _assert(set(obj["Actor"]) == {"ID", "Attributes"},
                    f"unknown/missing Docker Actor field at {slot_id}:{index + 1}")
            attrs = obj["Actor"]["Attributes"]
            _assert(isinstance(attrs, dict), f"Docker Actor.Attributes is not an object: {slot_id}")
            _assert(obj["Type"] == "container" and obj["Actor"]["ID"] == host["container_id"],
                    f"Docker event container identity mismatch: {slot_id}")
            _assert(attrs.get("name") == host["container_name"],
                    f"Docker event container name mismatch: {slot_id}")
            _assert(isinstance(obj["timeNano"], int) and obj["timeNano"] > last_time,
                    f"Docker event timeNano not strictly increasing: {slot_id}")
            last_time = obj["timeNano"]
            action_text = obj["Action"]
            action, command = (action_text.split(": ", 1) + [None])[:2] if ": " in action_text else (action_text, None)
            actions.append(action_text)
            projection = {
                "type": obj["Type"], "action": action, "command_or_null": command,
                "container_id": obj["Actor"]["ID"], "container_name": attrs.get("name"),
                "exec_id_or_null": attrs.get("execID"), "exit_code_or_null": attrs.get("exitCode"),
                "signal_or_null": attrs.get("signal"), "time_nano": obj["timeNano"],
            }
            projections.append(projection)
        _assert(actions == expected_actions, f"Docker event action projection mismatch: {slot_id}")
        for ordinal in range(5):
            triple = projections[2 + ordinal * 3:5 + ordinal * 3]
            exec_ids = [x["exec_id_or_null"] for x in triple]
            _assert(len(set(exec_ids)) == 1 and exec_ids[0], f"exec ID triple mismatch: {slot_id}")
            _assert(triple[2]["exit_code_or_null"] == "0", f"exec_die nonzero: {slot_id}")
        distinct = {projections[2 + ordinal * 3]["exec_id_or_null"] for ordinal in range(5)}
        _assert(len(distinct) == 5, f"post-cut exec IDs not distinct: {slot_id}")
        _assert(projections[-2]["signal_or_null"] == "15", f"TERM signal missing: {slot_id}")
        _assert(projections[-1]["exit_code_or_null"] == "0", f"container die nonzero: {slot_id}")
        return actions, projections

    def _inspect(self, raw: bytes, host: Mapping[str, Any], *, pre: bool, slot_id: str) -> Mapping[str, Any]:
        value = _parse_json(raw, f"{slot_id}/docker-inspect-{'pre' if pre else 'post'}.json")
        _assert(isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict),
                f"Docker inspect must be one-object array: {slot_id}")
        obj = value[0]
        _assert(obj.get("Id") == host["container_id"] and obj.get("Name") == "/" + host["container_name"],
                f"Docker inspect identity mismatch: {slot_id}")
        _assert(obj.get("Image") == host["image_id"] and obj.get("Created") == host["created_at"],
                f"Docker inspect image/created mismatch: {slot_id}")
        state = obj.get("State", {})
        if pre:
            _assert(state.get("Status") == "created" and state.get("Running") is False,
                    f"pre-inspect state mismatch: {slot_id}")
        else:
            _assert(state.get("Status") == "exited" and state.get("Running") is False and
                    state.get("ExitCode") == 0 and state.get("OOMKilled") is False,
                    f"post-inspect state mismatch: {slot_id}")
            _assert(state.get("StartedAt") == host["started_at"] and state.get("FinishedAt") == host["finished_at"],
                    f"post-inspect timestamps mismatch: {slot_id}")
        config = obj.get("Config", {})
        host_config = obj.get("HostConfig", {})
        argv = list(config.get("Entrypoint") or []) + list(config.get("Cmd") or [])
        _assert(argv == host["argv"], f"Docker inspect argv mismatch: {slot_id}")
        _assert(config.get("User") == host["user"] and config.get("WorkingDir") == host["working_dir"],
                f"Docker inspect user/cwd mismatch: {slot_id}")
        env_hashes = []
        for entry in sorted(config.get("Env") or []):
            _assert("=" in entry, f"malformed Docker env entry: {slot_id}")
            key, value_text = entry.split("=", 1)
            value_bytes = value_text.encode()
            env_hashes.append({"key": key, "value_byte_length": str(len(value_bytes)),
                               "value_sha256": sha256_bytes(value_bytes)})
        env_hashes.sort(key=lambda x: x["key"])
        _assert(env_hashes == host["env_key_value_hashes"], f"Docker env hashes mismatch: {slot_id}")
        _assert(host_config.get("NetworkMode") == host["network_mode"] == "none",
                f"network mode mismatch: {slot_id}")
        _assert(host_config.get("ReadonlyRootfs") is host["readonly_rootfs"] is True,
                f"read-only rootfs mismatch: {slot_id}")
        _assert(host_config.get("CapDrop") == host["cap_drop"] and "ALL" in host["cap_drop"],
                f"cap drop mismatch: {slot_id}")
        _assert(host_config.get("SecurityOpt") == host["security_opt"] and
                "no-new-privileges=true" in host["security_opt"], f"security opt mismatch: {slot_id}")
        for raw_key, host_key in (("PidsLimit", "pids_limit"), ("Memory", "memory_limit_bytes"),
                                  ("NanoCpus", "nano_cpus")):
            _assert(host_config.get(raw_key) == host[host_key] and host[host_key] > 0,
                    f"resource limit mismatch {raw_key}: {slot_id}")
        mounts = obj.get("Mounts") or []
        observed = [(x.get("Destination"), x.get("Type"), not bool(x.get("RW"))) for x in mounts]
        observed.extend((destination, "tmpfs", False)
                        for destination in (host_config.get("Tmpfs") or {}))
        observed.sort()
        recorded = sorted((x["destination"], x["type"], x["readonly"]) for x in host["mounts"])
        _assert(observed == recorded, f"Docker mount projection mismatch: {slot_id}")
        _assert(all("docker.sock" not in str(x.get("Source", "")) and
                    "docker.sock" not in str(x.get("Destination", "")) for x in mounts),
                f"Docker socket mounted: {slot_id}")
        return obj

    def _slot(self, slot_dir: pathlib.Path, mapping: Mapping[str, Any],
              closed_slot: Mapping[str, Any], execution_index: int,
              precommit: Mapping[str, Any], public: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], bytes]:
        slot_id = mapping["opaque_slot_id"]
        _assert(slot_dir.is_dir() and not slot_dir.is_symlink(), f"missing/symlinked slot directory: {slot_id}")
        names = {x.name for x in slot_dir.iterdir()}
        _assert(names == SLOT_FILES, f"slot file inventory mismatch for {slot_id}: {sorted(names ^ SLOT_FILES)}")
        raw = {name: _read_bytes(slot_dir / name) for name in SLOT_FILES}
        host = _parse_json(raw["host-launch.json"], f"{slot_id}/host-launch.json")
        receipt = _parse_json(raw["slot-receipt.json"], f"{slot_id}/slot-receipt.json")
        _assert(raw["host-launch.json"] == canonical_bytes(host), f"non-canonical host launch: {slot_id}")
        _assert(raw["slot-receipt.json"] == canonical_bytes(receipt), f"non-canonical slot receipt: {slot_id}")
        self._validate(host, "hostLaunch", f"{slot_id}/host-launch.json")
        self._validate(receipt, "slotReceipt", f"{slot_id}/slot-receipt.json")
        _assert(host["opaque_slot_id"] == receipt["opaque_slot_id"] == slot_id,
                f"slot identity mismatch: {slot_id}")
        _assert(receipt["challenge"] == closed_slot["challenge"] == mapping["challenge"],
                f"slot challenge mismatch: {slot_id}")
        _assert(receipt["execution_index"] == closed_slot["execution_index"] == execution_index,
                f"slot execution index mismatch: {slot_id}")
        _assert(receipt["attempt_count"] == closed_slot["attempt_count"] == 1 and
                receipt["infrastructure_classification"] == closed_slot["status"] == "COMPLETE",
                f"slot is not a single COMPLETE attempt: {slot_id}")
        _assert(receipt["collector_exit_code"] == receipt["exit_code"] == host["exit_code"] == 0 and
                host["oom_killed"] is False and host["daemon_error"] is None,
                f"slot exit/infrastructure failure: {slot_id}")
        envelope = public["resource_envelope"]
        _assert(host["image_id"] == precommit["collector_image_id"] and
                host["base_repo_digest"] == precommit["collector_base_repo_digest"] and
                host["repo_digest_or_null"] == precommit["collector_image_repo_digest_or_null"],
                f"host image/base digest differs from precommit: {slot_id}")
        _assert(host["argv"] == public["startup_templates"][mapping["challenge"]]["supervisor_argv"] and
                host["user"] == envelope["candidate_uid_gid"] and
                host["network_mode"] == envelope["network"] and
                host["readonly_rootfs"] is envelope["readonly_rootfs"] and
                host["pids_limit"] == envelope["pids_limit"] and
                host["memory_limit_bytes"] == envelope["memory_bytes"] and
                host["nano_cpus"] == int(float(envelope["cpu_limit"]) * 1_000_000_000),
                f"host launch differs from public resource/startup envelope: {slot_id}")
        _assert(host["pid_namespace_mode"] == host["ipc_namespace_mode"] ==
                host["uts_namespace_mode"] == "private" and
                host["user_namespace_mode"] == "daemon-default",
                f"host namespace projection mismatch: {slot_id}")

        # Raw semantics are checked before manifests so counterexamples fail on
        # the violated invariant, not merely on their resulting digest drift.
        actions, projections = self._event_projection(raw["docker-events.jsonl"], host, slot_id)
        self._inspect(raw["docker-inspect-pre.json"], host, pre=True, slot_id=slot_id)
        self._inspect(raw["docker-inspect-post.json"], host, pre=False, slot_id=slot_id)

        post = host["diagnostics"]["post_observation_extraction"]
        _assert(post["valid"] is True and post["failures"] == [] and
                post["registered_exec_count"] == 5 and post["daemon_event_count"] == 19,
                f"post-cut extraction audit invalid: {slot_id}")
        _assert(post["daemon_event_actions"] == actions, f"post-cut action audit mismatch: {slot_id}")
        _assert(post["ready_frame_sha256"] == self.profile["post_cut_profile"]["ready_frame_sha256"],
                f"ready frame audit mismatch: {slot_id}")
        expected_reads = self.profile["post_cut_profile"]["ordered_reads"]
        commands = host["diagnostics"]["host_command_receipts"]
        for left, right in zip(commands, commands[1:]):
            _assert(left["monotonic_finish_ns"] <= right["monotonic_start_ns"],
                    f"overlapping/reordered host command receipts: {slot_id}")
        exec_commands = []
        for read in expected_reads:
            expected_command = ["docker"] + [
                host["container_name"] if token == "<exact-container-name>" else token
                for token in read["command_suffix"]
            ]
            matches = [cmd for cmd in commands if cmd["command"] == expected_command]
            _assert(len(matches) == 1, f"missing/duplicate registered exec read: {slot_id}/{read['evidence_file']}")
            command = matches[0]
            _assert(command["returncode"] == 0 and _decode64(command["stderr_base64"], slot_id) == b"",
                    f"registered exec command failed: {slot_id}/{read['evidence_file']}")
            _assert(_decode64(command["stdout_base64"], slot_id) == raw[read["evidence_file"]],
                    f"registered exec stdout/channel mismatch: {slot_id}/{read['evidence_file']}")
            exec_commands.append(command)
        _assert(post["ready_observed_monotonic_ns"] <= exec_commands[0]["monotonic_start_ns"],
                f"post-cut read began before ready: {slot_id}")
        expected_kill = ["docker"] + [
            host["container_name"] if token == "<exact-container-name>" else token
            for token in self.profile["post_cut_profile"]["termination_command_suffix"]
        ]
        kills = [cmd for cmd in commands if cmd["command"] == expected_kill]
        _assert(len(kills) == 1 and kills[0]["returncode"] == 0,
                f"missing/failed exact TERM command: {slot_id}")
        event_exec_ids = [projections[2 + i * 3]["exec_id_or_null"] for i in range(5)]
        expected_groups = [{"evidence_file": read["evidence_file"], "exec_id": event_exec_ids[i],
                            "ordinal": i + 1, "out_path": read["command_suffix"][-1]}
                           for i, read in enumerate(expected_reads)]
        _assert(post["exec_groups"] == expected_groups, f"post-cut exec group audit mismatch: {slot_id}")

        _assert(raw["supervisor-control-stdout.bin"] == b"WAVE025_SUPERVISOR_READY_V1\n" and
                raw["supervisor-control-stderr.bin"] == b"", f"supervisor control channel mismatch: {slot_id}")
        _assert(raw["collector-ready.bin"] == b"READY\n" and raw["collector-exit-code.bin"] == b"0\n" and
                raw["collector-stderr.bin"] == b"", f"collector fixed channel mismatch: {slot_id}")
        _assert(raw["collector-stdout.bin"] == raw["collector-out.bin"] == raw["collector-features.json"],
                f"collector feature channel equality mismatch: {slot_id}")
        feature = _parse_json(raw["collector-features.json"], f"{slot_id}/collector-features.json")
        _assert(raw["collector-features.json"] == canonical_bytes(feature),
                f"collector feature receipt not canonical: {slot_id}")
        _assert(isinstance(feature, dict) and feature.get("schema") == "WAVE025_LEAK_ONLY_FEATURES_V1",
                f"wrong collector feature receipt schema: {slot_id}")

        required_checks = {
            "image_id", "frozen_supervisor_argv", "network_none", "readonly_rootfs", "non_root",
            "cap_drop_all", "no_new_privileges", "pid_private", "ipc_private", "uts_private",
            "pids_limited", "memory_limited", "cpu_limited", "challenge_readonly_bind",
            "out_exclusive_tmpfs", "no_docker_socket",
        }
        suffix = {"D0-HOST-LEAK": {"D0_shared_residue_bind", "D0_shared_residue_cwd"},
                  "D1-OCI-CANARY": {"D1_only_challenge_bind", "D1_fixed_workdir"},
                  "T-OCI-ISOLATED": {"T_only_challenge_bind", "T_fixed_workdir", "T_role_free_container_name"}}
        checks = host["diagnostics"]["actual_configuration_checks"]
        _assert(all(x["passed"] is True for x in checks), f"failed actual configuration check: {slot_id}")
        _assert(required_checks | suffix[mapping["challenge"]] <= {x["check"] for x in checks},
                f"missing actual configuration checks: {slot_id}")
        mounts = {x["destination"]: x for x in host["mounts"]}
        _assert(mounts.get("/challenge", {}).get("readonly") is True and
                mounts.get("/out", {}).get("type") == "tmpfs", f"required mounts missing: {slot_id}")
        if mapping["challenge"] == "D0-HOST-LEAK":
            _assert(set(mounts) == {"/challenge", "/out", "/shared-residue"} and
                    mounts["/shared-residue"]["readonly"] is True and host["working_dir"] == "/shared-residue",
                    f"D0 launch surface mismatch: {slot_id}")
        else:
            _assert(set(mounts) == {"/challenge", "/out"} and host["working_dir"] == "/app",
                    f"OCI cell launch surface mismatch: {slot_id}")
        if mapping["challenge"] == "T-OCI-ISOLATED":
            host_metadata = host["container_name"] + json.dumps(host["argv"]) + json.dumps(host["env_key_value_hashes"])
            _assert("WAVE025_CANARY_" not in host_metadata,
                    f"T role leaked into host launch metadata: {slot_id}")

        calculated = {name: sha256_bytes(value) for name, value in raw.items() if name != "slot-receipt.json"}
        _assert(calculated == receipt["files"], f"slot receipt file hashes mismatch: {slot_id}")
        closed_files = dict(calculated)
        closed_files["slot-receipt.json"] = sha256_bytes(raw["slot-receipt.json"])
        _assert(closed_files == closed_slot["files"], f"closed slot file hashes mismatch: {slot_id}")
        _assert(receipt["host_monotonic_start_ns"] < receipt["host_monotonic_finish_ns"] and
                receipt["host_started_at"] <= receipt["host_finished_at"], f"slot host timing invalid: {slot_id}")

        host_only = {
            "execution_index": receipt["execution_index"],
            "host_monotonic_start_ns": receipt["host_monotonic_start_ns"],
            "host_monotonic_finish_ns": receipt["host_monotonic_finish_ns"],
            "host_started_at": receipt["host_started_at"],
            "host_finished_at": receipt["host_finished_at"],
            "container_id": host["container_id"], "container_name": host["container_name"],
            "created_at": host["created_at"], "started_at": host["started_at"],
            "finished_at": host["finished_at"], "image_id": host["image_id"],
            "network_mode": host["network_mode"],
            "host_launch_sha256": sha256_bytes(raw["host-launch.json"]),
        }
        record = {
            "receipt": feature,
            "challenge": mapping["challenge"],
            "phase": "fresh_holdout" if mapping["phase"] == "holdout" else "calibration",
            "block": mapping["block"],
            "opaque_slot_id": slot_id,
            "role": mapping["role"],
            "host_only": host_only,
        }
        return record, host_only, raw["slot-receipt.json"]

    def adapt(self, batch_dir: pathlib.Path) -> BatchAdapterResult:
        batch = pathlib.Path(batch_dir)
        _assert(batch.is_dir() and not batch.is_symlink(), f"batch is missing or symlinked: {batch}")
        root_names = {entry.name for entry in batch.iterdir()}
        if "shared-evidence-profile.json" in root_names:
            raise UnsupportedBatchVersion("V1.4 self-contained profile bytes are not supported")
        unknown = root_names - ROOT_ALLOWED
        required = set(ROOT_JSON) | {"slots"}
        _assert(not unknown and required <= root_names,
                f"batch root inventory mismatch unknown={sorted(unknown)} missing={sorted(required-root_names)}")
        roots: Dict[str, Any] = {}
        root_raw: Dict[str, bytes] = {}
        for filename, schema_name in ROOT_JSON.items():
            roots[filename], root_raw[filename] = _read_json(batch / filename, canonical=True)
            if filename == "precommit.json" and roots[filename].get("schema") != "WAVE025_BATCH_PRECOMMIT_V1":
                raise UnsupportedBatchVersion("only observed Wave025 V1.3 F runner objects are supported")
            self._validate(roots[filename], schema_name, filename)

        precommit = roots["precommit.json"]
        public = roots["public-plan.json"]
        private = roots["runner-private-state.json"]
        anchor = roots["anchor-receipt.json"]
        closed = roots["closed.json"]
        reveal = roots["reveal.json"]
        batch_id = precommit["batch_id"]
        _assert(all(root["batch_id"] == batch_id for root in roots.values()), "top-level batch IDs differ")
        _assert(precommit["mode"] == public["mode"] == "smoke" and
                precommit["challenges"] == public["challenges"], "top-level plan linkage mismatch")
        expected_block_shape = [{"block": item["block"], "size": item["size"]}
                                for item in precommit["block_plan"]["blocks"]]
        _assert(public["block_shape"] == {"blocks": expected_block_shape,
                                           "count": precommit["block_plan"]["count"]},
                "public/precommit block shape mismatch")
        extraction_hash = sha256_bytes(canonical_bytes(precommit["evidence_extraction_profile"]))
        _assert(extraction_hash == self.profile["feature_and_profile_bytes"]
                ["post_cut_extraction_profile"]["canonical_subobject_sha256"],
                "precommitted post-cut extraction profile differs from shared profile")
        hashes = {name: sha256_bytes(raw) for name, raw in root_raw.items()}
        _assert(private["precommit_sha256"] == anchor["precommit_sha256"] ==
                closed["precommit_sha256"] == hashes["precommit.json"], "precommit hash link mismatch")
        _assert(private["public_plan_sha256"] == hashes["public-plan.json"], "public-plan hash link mismatch")
        _assert(closed["anchor_receipt_sha256"] == hashes["anchor-receipt.json"], "anchor hash link mismatch")
        _assert(reveal["closed_sha256"] == hashes["closed.json"], "closed/reveal hash link mismatch")
        _assert(anchor["qualifying_external_anchor_present"] is True and anchor["root_receipts"],
                "qualifying external anchor absent")
        _assert(all(x["precommit_sha256"] == hashes["precommit.json"] for x in anchor["root_receipts"]),
                "anchor receipt precommit mismatch")
        external = self._check_external_locks(precommit)
        mapping = self._reconstruct(precommit, public, private, reveal, root_raw["public-plan.json"])

        _assert(closed["merkle_algorithm"] == "SHA256-PAIR-CONCAT-DUPLICATE-LAST-W025-V1",
                "unsupported Merkle algorithm")
        _assert(closed["expected_slot_count"] == closed["actual_slot_directory_count"] ==
                public["slot_count"] == len(mapping), "closed population mismatch")
        slot_dirs = batch / "slots"
        _assert(slot_dirs.is_dir() and not slot_dirs.is_symlink(), "slots directory missing or symlinked")
        actual_slot_ids = {entry.name for entry in slot_dirs.iterdir()}
        expected_slot_ids = {x["opaque_slot_id"] for x in mapping}
        _assert(actual_slot_ids == expected_slot_ids, "slot directory population mismatch")
        closed_by_id = {x["opaque_slot_id"]: x for x in closed["slots"]}
        _assert(set(closed_by_id) == expected_slot_ids and len(closed_by_id) == len(closed["slots"]),
                "closed slot population/duplicate mismatch")
        execution_index = {slot_id: index + 1 for index, slot_id in enumerate(reveal["execution_order"])}
        _assert([x["opaque_slot_id"] for x in public["slots"]] == sorted(expected_slot_ids),
                "public slot inventory order is not canonical")
        _assert([x["opaque_slot_id"] for x in closed["slots"]] == sorted(expected_slot_ids),
                "closed slot inventory order is not canonical")
        records: List[Mapping[str, Any]] = []
        host_rows: List[Mapping[str, Any]] = []
        receipt_bytes: List[Tuple[str, bytes]] = []
        for item in mapping:
            slot_id = item["opaque_slot_id"]
            record, host_only, raw_receipt = self._slot(
                slot_dirs / slot_id, item, closed_by_id[slot_id], execution_index[slot_id], precommit, public
            )
            records.append(record)
            host_rows.append(host_only)
            receipt_bytes.append((slot_id, raw_receipt))
        merkle = _merkle(receipt_bytes)
        _assert(merkle == closed["batch_merkle_root"], "batch Merkle root mismatch")
        _assert(closed["first_host_time"] == min(x["host_started_at"] for x in host_rows) and
                closed["last_host_time"] == max(x["host_finished_at"] for x in host_rows),
                "closed host time envelope mismatch")

        reconstruction = reveal["reconstruction"]
        _assert(reveal["reconstruction_complete"] is True and all(reconstruction["commitments"].values()) and
                all(reconstruction[key] is True for key in (
                    "execution_order_exactly_rebuilt", "mapping_exactly_rebuilt",
                    "opaque_ids_unique_and_rebuilt", "padding_exactly_rebuilt", "strict_block_balance")),
                "runner reveal did not declare complete reconstruction")
        if self.enforce_f_root_locks:
            locks = self.profile["source_locks"]["f_root_objects"]
            _assert(hashes == locks, "F root object bytes differ from shared-profile exact locks")

        host_hash = sha256_bytes(canonical_bytes(host_rows))
        receipt = {
            "schema": "WAVE025_FULL_ENGINE_BATCH_ADAPTER_RECEIPT_V1",
            "adapter_scope": "READ_ONLY_V1_3_F_EXACT",
            "batch_id": batch_id,
            "root_sha256": hashes,
            "external_bound_bytes": external,
            "slot_count": len(records),
            "slot_ids_sha256": sha256_bytes(canonical_bytes(sorted(expected_slot_ids))),
            "batch_merkle_root": merkle,
            "host_only_rows_sha256": host_hash,
            "holdout_phase_mapping": "holdout->fresh_holdout",
            "feature_profile_bytes": "V1.3_EXTERNAL_HASH_BOUND_NOT_SELF_CONTAINED",
            "future_v1_4_self_contained_profile_bytes_supported": False,
            "evaluation_json_read": False,
            "batch_writes_performed": False,
            "qualification_verdict_produced": False,
            "treatment_score_or_ranking_produced": False,
        }
        return BatchAdapterResult(tuple(records), tuple(host_rows), receipt)


def adapt_f_batch(batch_dir: pathlib.Path) -> BatchAdapterResult:
    return BatchAdapter().adapt(batch_dir)


__all__ = [
    "BatchAdapter", "BatchAdapterResult", "BatchAdapterError", "CanonicalJSONError",
    "SchemaValidationError", "EvidenceIntegrityError", "UnsupportedBatchVersion", "adapt_f_batch",
]
