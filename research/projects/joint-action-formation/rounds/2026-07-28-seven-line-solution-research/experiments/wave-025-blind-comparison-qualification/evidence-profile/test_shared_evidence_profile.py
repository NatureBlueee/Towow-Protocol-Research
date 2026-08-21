from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import unittest
from pathlib import Path

import jsonschema


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
F_BATCH = EXPERIMENT / "runs" / "smoke-v13-20260801-f"
PROFILE_PATH = HERE / "SHARED-EVIDENCE-PROFILE.candidate.json"
PROFILE_SCHEMA_PATH = HERE / "SHARED-EVIDENCE-PROFILE.schema.json"
OBJECT_SCHEMA_PATH = HERE / "RUNNER-EVIDENCE-OBJECTS.schema.json"


def read_json(path: Path):
    return json.loads(path.read_bytes())


def canonical_bytes(value) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


class HmacStream:
    """Independent reconstruction of the byte stream declared by the profile."""

    def __init__(self, key: bytes, label: bytes):
        self.key = key
        self.label = label
        self.counter = 0
        self.buffer = b""

    def read(self, size: int) -> bytes:
        while len(self.buffer) < size:
            self.buffer += hmac.new(
                self.key,
                self.label + b"\x00" + self.counter.to_bytes(8, "big"),
                hashlib.sha256,
            ).digest()
            self.counter += 1
        result, self.buffer = self.buffer[:size], self.buffer[size:]
        return result

    def randbelow(self, upper: int) -> int:
        width = max(1, ((upper - 1).bit_length() + 7) // 8)
        ceiling = 1 << (8 * width)
        limit = ceiling - (ceiling % upper)
        while True:
            value = int.from_bytes(self.read(width), "big")
            if value < limit:
                return value % upper


def shuffled(values, seed: bytes, label: str):
    result = list(values)
    stream = HmacStream(seed, label.encode("utf-8"))
    for index in range(len(result) - 1, 0, -1):
        selected = stream.randbelow(index + 1)
        result[index], result[selected] = result[selected], result[index]
    return result


def smoke_layout(per_split: int):
    layout = []
    for challenge in ("D0-HOST-LEAK", "D1-OCI-CANARY", "T-OCI-ISOLATED"):
        for phase in ("calibration", "holdout"):
            block = f"{challenge}:{phase}:000"
            for within_block in range(per_split):
                layout.append(
                    {
                        "challenge": challenge,
                        "phase": phase,
                        "block": block,
                        "within_block": within_block,
                    }
                )
    return layout


def opaque_slot_id(seed: bytes, index: int) -> str:
    digest = hmac.new(
        seed,
        b"W025-PUBLIC-ID-V1\x00" + index.to_bytes(8, "big"),
        hashlib.sha256,
    ).hexdigest()
    return "s_" + digest[:32]


def private_token(seed: bytes, family: str, role: str) -> str:
    digest = hmac.new(
        seed,
        f"W025-{family}-TOKEN-V1\x00{role}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"WAVE025_CANARY_{family}_{digest[:24]}"


def padding_value(seed: bytes, slot_id: str) -> int:
    return HmacStream(seed, f"W025-PADDING-V1\x00{slot_id}".encode("utf-8")).randbelow(257)


def reconstruct_mapping(layout, assignment_seed: bytes, public_seed: bytes, padding_seed: bytes):
    by_block = {}
    for index, item in enumerate(layout):
        by_block.setdefault(item["block"], []).append(index)
    roles = {}
    for block, indexes in sorted(by_block.items()):
        base = ["S"] * (len(indexes) // 2) + ["R"] * (len(indexes) // 2)
        roles.update(zip(indexes, shuffled(base, assignment_seed, f"roles\x00{block}")))
    mapping = []
    for index, item in enumerate(layout):
        slot_id = opaque_slot_id(public_seed, index)
        role = roles[index]
        if item["challenge"] == "D0-HOST-LEAK":
            token = private_token(assignment_seed, "D0_RESIDUE", role)
        elif item["challenge"] == "D1-OCI-CANARY":
            token = private_token(assignment_seed, "D1_CURRENT", role)
        else:
            token = None
        mapping.append(
            {
                "opaque_slot_id": slot_id,
                "challenge": item["challenge"],
                "phase": item["phase"],
                "block": item["block"],
                "role": role,
                "private_canary_token_or_null": token,
                "measurement_padding_bytes": padding_value(padding_seed, slot_id),
            }
        )
    order = shuffled(
        [item["opaque_slot_id"] for item in mapping], assignment_seed, "execution-order"
    )
    return mapping, order


def commitment(domain: str, seed: bytes, nonce: bytes, public_plan_bytes: bytes) -> str:
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\x00"
        + seed
        + b"\x00"
        + nonce
        + b"\x00"
        + public_plan_bytes
    )


def merkle_v1(receipt_hashes: list[str]) -> str | None:
    if not receipt_hashes:
        return None
    level = [bytes.fromhex(value) for value in receipt_hashes]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


class SharedEvidenceProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = read_json(PROFILE_PATH)
        cls.profile_schema = read_json(PROFILE_SCHEMA_PATH)
        cls.object_schema = read_json(OBJECT_SCHEMA_PATH)
        cls.precommit = read_json(F_BATCH / "precommit.json")
        cls.public_plan = read_json(F_BATCH / "public-plan.json")
        cls.private_state = read_json(F_BATCH / "runner-private-state.json")
        cls.anchor = read_json(F_BATCH / "anchor-receipt.json")
        cls.closed = read_json(F_BATCH / "closed.json")
        cls.reveal = read_json(F_BATCH / "reveal.json")
        cls.slot_dirs = sorted(path for path in (F_BATCH / "slots").iterdir() if path.is_dir())

    def test_schemas_and_profile_are_closed_and_valid(self):
        jsonschema.Draft202012Validator.check_schema(self.profile_schema)
        jsonschema.Draft202012Validator.check_schema(self.object_schema)
        jsonschema.Draft202012Validator(self.profile_schema).validate(self.profile)
        invalid = copy.deepcopy(self.profile)
        invalid["post_cut_profile"]["event_semantic_projection"]["surprise"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(self.profile_schema).validate(invalid)

    def test_all_runner_owned_objects_validate_exact_recursively(self):
        validator = jsonschema.Draft202012Validator(self.object_schema)
        root_objects = [
            self.precommit,
            self.public_plan,
            self.private_state,
            self.anchor,
            self.closed,
            self.reveal,
        ]
        for value in root_objects:
            validator.validate(value)
        for slot_dir in self.slot_dirs:
            validator.validate(read_json(slot_dir / "host-launch.json"))
            validator.validate(read_json(slot_dir / "slot-receipt.json"))
        invalid = copy.deepcopy(read_json(self.slot_dirs[0] / "host-launch.json"))
        invalid["diagnostics"]["post_observation_extraction"]["surprise"] = True
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(invalid)

    def test_registry_resolves_all_exact_object_schemas(self):
        definitions = self.object_schema["$defs"]
        schemas = set()
        for entry in self.profile["runner_owned_object_registry"]:
            self.assertEqual(entry["field_policy"], "EXACT_RECURSIVE")
            definition = entry["schema_ref"].rsplit("/", 1)[-1]
            self.assertIn(definition, definitions)
            schemas.add(entry["schema"])
        self.assertEqual(
            schemas,
            {
                "WAVE025_BATCH_PRECOMMIT_V1",
                "WAVE025_PUBLIC_PLAN_V1",
                "WAVE025_RUNNER_PRIVATE_STATE_V1",
                "WAVE025_ANCHOR_RECEIPT_V1",
                "WAVE025_HOST_LAUNCH_V1",
                "WAVE025_SLOT_RECEIPT_V1",
                "WAVE025_BATCH_CLOSED_V1",
                "WAVE025_BATCH_REVEAL_V1",
            },
        )

    def test_source_locks_match_exact_bytes(self):
        locks = self.profile["source_locks"]
        for name in (
            "runner",
            "qualification_contract",
            "batch_contract",
            "collector_source",
            "collector_dockerfile",
        ):
            self.assertEqual(sha256_file(EXPERIMENT / locks[name]["path"]), locks[name]["sha256"])
        for name, expected in locks["f_root_objects"].items():
            self.assertEqual(sha256_file(F_BATCH / name), expected)

    def test_runner_json_is_canonical_but_daemon_json_is_raw(self):
        runner_paths = [
            F_BATCH / "precommit.json",
            F_BATCH / "public-plan.json",
            F_BATCH / "runner-private-state.json",
            F_BATCH / "anchor-receipt.json",
            F_BATCH / "closed.json",
            F_BATCH / "reveal.json",
        ]
        for slot_dir in self.slot_dirs:
            runner_paths += [slot_dir / "host-launch.json", slot_dir / "slot-receipt.json"]
        for path in runner_paths:
            self.assertEqual(path.read_bytes(), canonical_bytes(read_json(path)), path)
        for slot_dir in self.slot_dirs:
            for name in ("docker-inspect-pre.json", "docker-inspect-post.json"):
                raw = (slot_dir / name).read_bytes()
                value = json.loads(raw)
                self.assertIsInstance(value, list)
                self.assertEqual(len(value), 1)
                self.assertNotEqual(raw, canonical_bytes(value))
            event_lines = [line for line in (slot_dir / "docker-events.jsonl").read_bytes().splitlines() if line]
            self.assertEqual(len(event_lines), 19)
            self.assertTrue(all(isinstance(json.loads(line), dict) for line in event_lines))

    def test_command_receipts_have_exact_fields_base64_and_monotonic_order(self):
        exact_fields = set(self.profile["command_receipt_profile"]["exact_fields"])
        all_receipts = [
            self.private_state["final_image_inspect_receipt"],
            self.private_state["base_image_inspect_receipt"],
            self.closed["docker_daemon"]["diagnostics"]["command"],
        ]
        for slot_dir in self.slot_dirs:
            host = read_json(slot_dir / "host-launch.json")
            all_receipts.append(host["diagnostics"]["docker_version_command"])
            receipts = host["diagnostics"]["host_command_receipts"]
            all_receipts.extend(receipts)
            for previous, current in zip(receipts, receipts[1:]):
                self.assertGreaterEqual(current["monotonic_start_ns"], previous["monotonic_finish_ns"])
        for receipt in all_receipts:
            self.assertEqual(set(receipt), exact_fields)
            self.assertLessEqual(receipt["monotonic_start_ns"], receipt["monotonic_finish_ns"])
            base64.b64decode(receipt["stdout_base64"], validate=True)
            base64.b64decode(receipt["stderr_base64"], validate=True)

    def test_three_domain_commitments_and_all_randomization_reconstruct(self):
        public_raw = (F_BATCH / "public-plan.json").read_bytes()
        secrets = self.private_state["domains"]
        expected_commitment_fields = {
            "PRIVATE_ASSIGNMENT_ORDER": "assignment_commitment",
            "PUBLIC_ID": "public_id_commitment",
            "MEASUREMENT_PADDING": "padding_commitment",
        }
        for domain, field in expected_commitment_fields.items():
            seed = bytes.fromhex(secrets[domain]["seed_hex"])
            nonce = bytes.fromhex(secrets[domain]["nonce_hex"])
            self.assertEqual(commitment(domain, seed, nonce, public_raw), self.precommit[field])
        per_split = self.precommit["sample_plan"]["D0-HOST-LEAK"]["calibration"]
        mapping, order = reconstruct_mapping(
            smoke_layout(per_split),
            bytes.fromhex(secrets["PRIVATE_ASSIGNMENT_ORDER"]["seed_hex"]),
            bytes.fromhex(secrets["PUBLIC_ID"]["seed_hex"]),
            bytes.fromhex(secrets["MEASUREMENT_PADDING"]["seed_hex"]),
        )
        self.assertEqual(mapping, self.private_state["mapping"])
        self.assertEqual(order, self.private_state["execution_order"])
        self.assertEqual(self.reveal["domains"], self.private_state["domains"])
        reveal_mapping = [
            {
                "opaque_slot_id": item["opaque_slot_id"],
                "challenge": item["challenge"],
                "phase": item["phase"],
                "block": item["block"],
                "role": item["role"],
                "canary_token_or_null": item["private_canary_token_or_null"],
                "measurement_padding_bytes": item["measurement_padding_bytes"],
            }
            for item in mapping
        ]
        self.assertEqual(reveal_mapping, self.reveal["mapping"])
        self.assertEqual(order, self.reveal["execution_order"])
        self.assertEqual(
            sorted((item["opaque_slot_id"], item["challenge"]) for item in mapping),
            sorted((item["opaque_slot_id"], item["challenge"]) for item in self.public_plan["slots"]),
        )

    def test_control_registry_keeps_role_and_secrets_out_of_public_evidence(self):
        controls = self.profile["control_registry"]
        ids = [item["control_id"] for item in controls]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {item["control_id"]: item for item in controls}
        for control_id in ("hidden_role", "execution_order", "domain_secrets", "measurement_padding"):
            self.assertFalse(by_id[control_id]["public_before_reveal"])
            self.assertFalse(by_id[control_id]["classifier_feature_eligible"])
        self.assertEqual(
            {item["control_id"] for item in controls if item["classifier_feature_eligible"]},
            {"private_canary_token", "collector_feature_receipt"},
        )
        public_text = json.dumps(self.public_plan, sort_keys=True)
        for forbidden_key in ("private_canary_token_or_null", '"role"', '"seed_hex"', '"nonce_hex"'):
            self.assertNotIn(forbidden_key, public_text)

    def test_merkle_v1_matches_f_and_is_scoped_to_full_set_verification(self):
        closed_ids = [item["opaque_slot_id"] for item in self.closed["slots"]]
        expected_ids = sorted(item["opaque_slot_id"] for item in self.public_plan["slots"])
        self.assertEqual(closed_ids, expected_ids)
        self.assertEqual(self.closed["expected_slot_count"], len(expected_ids))
        self.assertEqual(self.closed["actual_slot_directory_count"], len(expected_ids))
        leaf_hashes = []
        for closed_slot in self.closed["slots"]:
            slot_dir = F_BATCH / "slots" / closed_slot["opaque_slot_id"]
            receipt_bytes = (slot_dir / "slot-receipt.json").read_bytes()
            receipt_hash = sha256_bytes(receipt_bytes)
            self.assertEqual(receipt_hash, closed_slot["files"]["slot-receipt.json"])
            receipt = json.loads(receipt_bytes)
            self.assertEqual(closed_slot["files"] | {}, receipt["files"] | {"slot-receipt.json": receipt_hash})
            for name, digest in closed_slot["files"].items():
                self.assertEqual(sha256_file(slot_dir / name), digest)
            leaf_hashes.append(receipt_hash)
        self.assertEqual(merkle_v1(leaf_hashes), self.closed["batch_merkle_root"])
        merkle_profile = self.profile["merkle_profile"]
        self.assertFalse(merkle_profile["current_v1"]["domain_separation"])
        self.assertEqual(
            merkle_profile["current_v1"]["status"],
            "ACCEPTABLE_FOR_F_FULL_SET_VERIFICATION_ONLY",
        )
        hardening = {item["code"]: item for item in self.profile["conditional_hardening"]}
        self.assertIn("MERKLE_V1_NO_DOMAIN_SEPARATION", hardening)
        self.assertIn("standalone", hardening["MERKLE_V1_NO_DOMAIN_SEPARATION"]["scope"])
        self.assertIn("0x00", merkle_profile["proposed_v2"]["leaf"])
        self.assertIn("0x01", merkle_profile["proposed_v2"]["node"])

    def test_feature_and_profile_bytes_are_located_and_bound_truthfully(self):
        section = self.profile["feature_and_profile_bytes"]
        feature = section["full_feature_spec"]
        self.assertEqual(sha256_file(EXPERIMENT / feature["path"]), feature["sha256"])
        self.assertEqual(self.precommit["feature_spec_sha256"], feature["sha256"])
        self.assertFalse((F_BATCH / "FEATURE-SPEC.json").exists())
        extraction_hash = sha256_bytes(canonical_bytes(self.precommit["evidence_extraction_profile"]))
        self.assertEqual(
            extraction_hash,
            section["post_cut_extraction_profile"]["canonical_subobject_sha256"],
        )
        attack = section["executable_attack_profile"]
        self.assertEqual(sha256_file(EXPERIMENT / attack["selected_path"]), attack["selected_sha256"])
        self.assertEqual(sha256_file(EXPERIMENT / attack["candidate_path"]), attack["candidate_sha256"])
        self.assertIsNone(attack["precommit_binding"])
        self.assertNotIn(attack["selected_sha256"], json.dumps(self.precommit, sort_keys=True))
        self.assertNotIn(attack["candidate_sha256"], json.dumps(self.precommit, sort_keys=True))
        for slot_dir in self.slot_dirs:
            features = (slot_dir / "collector-features.json").read_bytes()
            self.assertEqual(features, (slot_dir / "collector-out.bin").read_bytes())
            self.assertEqual(features, (slot_dir / "collector-stdout.bin").read_bytes())
            self.assertEqual(features, canonical_bytes(json.loads(features)))
            self.assertEqual(json.loads(features)["schema"], "WAVE025_LEAK_ONLY_FEATURES_V1")

    def test_post_cut_commands_events_and_exact_projection(self):
        post = self.profile["post_cut_profile"]
        raw_event_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": self.object_schema["$defs"],
            "$ref": "#/$defs/fObservedRawDockerEvent",
        }
        projection_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": self.object_schema["$defs"],
            "$ref": "#/$defs/postCutEventProjection",
        }
        raw_event_validator = jsonschema.Draft202012Validator(raw_event_schema)
        projection_validator = jsonschema.Draft202012Validator(projection_schema)
        expected_top = set(post["f_observed_raw_event_envelope"]["exact_top_level_fields"])
        expected_actor = set(post["f_observed_raw_event_envelope"]["exact_actor_fields"])
        consumed = set(post["f_observed_raw_event_envelope"]["consumed_attribute_fields"])
        projection_fields = set(post["event_semantic_projection"]["exact_fields"])
        self.assertEqual(
            post["f_observed_raw_event_envelope"]["portability_status"],
            "NON_BLOCKING_OPEN_WORLD_RAW_WITH_FROZEN_PROJECTION",
        )
        for slot_dir in self.slot_dirs:
            host = read_json(slot_dir / "host-launch.json")
            audit = host["diagnostics"]["post_observation_extraction"]
            self.assertTrue(audit["valid"])
            self.assertEqual(audit["failures"], [])
            self.assertEqual(audit["daemon_event_count"], 19)
            self.assertEqual(audit["registered_exec_count"], 5)
            self.assertEqual(audit["daemon_event_actions"], post["complete_event_action_sequence"])
            self.assertEqual(len({group["exec_id"] for group in audit["exec_groups"]}), 5)
            self.assertEqual((slot_dir / "supervisor-control-stdout.bin").read_bytes(), post["ready_frame_utf8"].encode())
            self.assertEqual((slot_dir / "supervisor-control-stderr.bin").read_bytes(), b"")
            self.assertEqual((slot_dir / "collector-ready.bin").read_bytes(), b"READY\n")
            self.assertEqual((slot_dir / "collector-stderr.bin").read_bytes(), b"")
            slot_receipt = read_json(slot_dir / "slot-receipt.json")
            self.assertEqual(
                (slot_dir / "collector-exit-code.bin").read_bytes(),
                f"{slot_receipt['collector_exit_code']}\n".encode(),
            )
            receipts = host["diagnostics"]["host_command_receipts"]
            for declared, group in zip(post["ordered_reads"], audit["exec_groups"]):
                expected_suffix = [
                    host["container_name"] if item == "<exact-container-name>" else item
                    for item in declared["command_suffix"]
                ]
                matches = [receipt for receipt in receipts if receipt["command"][-len(expected_suffix):] == expected_suffix]
                self.assertEqual(len(matches), 1)
                self.assertEqual(group["ordinal"], declared["ordinal"])
                self.assertEqual(group["evidence_file"], declared["evidence_file"])
                self.assertEqual(group["out_path"], expected_suffix[-1])
            events = [json.loads(line) for line in (slot_dir / "docker-events.jsonl").read_bytes().splitlines() if line]
            self.assertEqual([event["Action"] for event in events], post["complete_event_action_sequence"])
            unknown_seen = False
            for event in events:
                raw_event_validator.validate(event)
                self.assertEqual(set(event), expected_top)
                self.assertEqual(set(event["Actor"]), expected_actor)
                attributes = event["Actor"]["Attributes"]
                unknown_seen = unknown_seen or bool(set(attributes) - consumed)
                self.assertEqual(event["Type"], "container")
                self.assertEqual(event["Actor"]["ID"], host["container_id"])
                self.assertEqual(attributes["name"], host["container_name"])
                self.assertIsInstance(event["timeNano"], int)
                if ": " in event["Action"]:
                    action, command = event["Action"].split(": ", 1)
                else:
                    action, command = event["Action"], None
                projection = {
                    "type": event["Type"],
                    "action": action,
                    "command_or_null": command,
                    "container_id": event["Actor"]["ID"],
                    "container_name": attributes["name"],
                    "exec_id_or_null": attributes.get("execID"),
                    "exit_code_or_null": attributes.get("exitCode"),
                    "signal_or_null": attributes.get("signal"),
                    "time_nano": event["timeNano"],
                }
                self.assertEqual(set(projection), projection_fields)
                projection_validator.validate(projection)
            self.assertTrue(unknown_seen)

    def test_only_truthful_blockers_remain_unconditional(self):
        blockers = {item["code"] for item in self.profile["blocking_issues"]}
        self.assertEqual(
            blockers,
            {
                "EXECUTABLE_ATTACK_PROFILE_NOT_PRECOMMITTED",
                "FEATURE_SPEC_BYTES_NOT_EMBEDDED_IN_BATCH",
            },
        )
        conditional = {item["code"] for item in self.profile["conditional_hardening"]}
        self.assertEqual(
            conditional,
            {"MERKLE_V1_NO_DOMAIN_SEPARATION", "RAW_DOCKER_EVENT_ATTRIBUTES_OPEN_WORLD"},
        )


if __name__ == "__main__":
    unittest.main()
