from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
FEATURE_SPEC = PACKAGE.parent
EXPERIMENT = FEATURE_SPEC.parent
F_RUN = EXPERIMENT / "runs" / "smoke-v13-20260801-f"

spec = importlib.util.spec_from_file_location("admission_v11", PACKAGE / "admit_receipt_v1_1.py")
assert spec and spec.loader
admission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admission)


def receipt_paths() -> list[Path]:
    return sorted(F_RUN.glob("slots/*/collector-features.json"))


def load_base() -> dict:
    return json.loads(receipt_paths()[0].read_text(encoding="utf-8"))


def package_sha() -> str:
    return hashlib.sha256((PACKAGE / "PACKAGE-MANIFEST.candidate.json").read_bytes()).hexdigest()


def write_canonical(path: Path, value) -> bytes:
    raw = admission.canonical_bytes(value)
    path.write_bytes(raw)
    return raw


def binding(path: Path, root: Path) -> dict:
    raw = path.read_bytes()
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_g_fixture(root: Path) -> dict:
    root.mkdir()
    challenge = root / "challenge"
    challenge.mkdir()
    config = challenge / "collector-input.json"
    config.write_bytes(b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n')
    subject = challenge / "input.bin"
    subject.write_bytes(b"g-candidate-subject")
    environment_path = root / "launch-environment.json"
    environment_doc = {"schema": "WAVE025_LAUNCH_ENVIRONMENT_V1_1_CANDIDATE", "values": {"MODE": "G"}}
    write_canonical(environment_path, environment_doc)
    challenge_doc, challenge_canaries = admission.snapshot_challenge(challenge, reject_oversize=True)
    challenge_snapshot_path = root / "challenge-snapshot.json"
    write_canonical(challenge_snapshot_path, challenge_doc)

    cmdline = b"node\0/app/collector.js\0"
    status = b"Name:\tagent\nState:\tR (running)\nPPid:\t0\nUid:\t1\t1\t1\t1\nGid:\t2\t2\t2\t2\nThreads:\t1\n"
    self_raw = {"cgroup": b"0::/\n", "mountinfo": b"1 2 3\n", "status": status}
    view = {
        "available": True, "truncated": False,
        "processes": [{
            "pid": 7, "cmdline": ["node", "/app/collector.js"],
            "cmdline_byte_length": len(cmdline), "cmdline_sha256": hashlib.sha256(cmdline).hexdigest(),
            "status": admission.parse_status(status), "pid_namespace": "pid:[7]", "mount_namespace": "mnt:[8]",
        }],
        "self": {
            **{name: {"byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} for name, raw in self_raw.items()},
            "pid_namespace": "pid:[7]", "mount_namespace": "mnt:[8]",
        },
    }
    process_doc = {
        "schema": "WAVE025_PROCESS_SNAPSHOT_V1_1_CANDIDATE", "numeric_pid_names": ["7"],
        "processes": [{
            "pid": 7, "cmdline_base64": __import__("base64").b64encode(cmdline).decode(),
            "status_base64": __import__("base64").b64encode(status).decode(),
            "pid_namespace": "pid:[7]", "mount_namespace": "mnt:[8]",
        }],
        "self": {
            **{name: __import__("base64").b64encode(raw).decode() for name, raw in self_raw.items()},
            "pid_namespace": "pid:[7]", "mount_namespace": "mnt:[8]",
        },
    }
    process_path = root / "process-snapshot.json"
    write_canonical(process_path, process_doc)

    value = load_base()
    value["input_contract"] = {"parsed": {"schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}, "byte_length": config.stat().st_size, "sha256": hashlib.sha256(config.read_bytes()).hexdigest()}
    value["subject_input"] = {"path": "$CHALLENGE/input.bin", "byte_length": subject.stat().st_size, "sha256": hashlib.sha256(subject.read_bytes()).hexdigest()}
    env_rows, env_canaries = admission.environment_rows(environment_doc["values"])
    value["environment"] = env_rows
    value["visible_canaries"] = sorted(env_canaries + challenge_canaries, key=admission.canonical_bytes)
    value["directory_trees"]["challenge"] = challenge_doc["directory_tree"]
    for label in ("cwd", "out", "tmp", "self-fd"):
        if not value["directory_trees"][label]["available"] or value["directory_trees"][label]["errors"]:
            value["directory_trees"][label] = copy.deepcopy(challenge_doc["directory_tree"])
    value["process_view"] = view
    value["identity"]["pid"] = 7
    receipt_path = root / "receipt.json"
    write_canonical(receipt_path, value)

    execution_path = root / "execution-evidence.json"
    execution_doc = {
        "schema": "WAVE025_RUNNER_EXECUTION_EVIDENCE_V1_1_CANDIDATE",
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "package_manifest_sha256": package_sha(), "challenge_read_only": True,
        "controller_domain_worker_writable": False, "network_isolation": "RUNNER_ENFORCED",
        "authority_channel_absent": True,
    }
    write_canonical(execution_path, execution_doc)
    preimage = {
        "schema": "WAVE025_CONTROLLER_MATERIAL_PREIMAGE_V1_1_CANDIDATE", "seal_id": "g-seal",
        "run_id": "g-run", "role": "T", "slot_id": "g-slot",
        "controller_domain": "EXTERNAL_READ_ONLY_TO_WORKER",
        "package_manifest": {"byte_length": (PACKAGE / "PACKAGE-MANIFEST.candidate.json").stat().st_size, "sha256": package_sha()},
        "receipt": binding(receipt_path, root), "collector_input": binding(config, root),
        "subject_input": binding(subject, root), "launch_environment": binding(environment_path, root),
        "challenge_snapshot": binding(challenge_snapshot_path, root), "challenge_root_relative_path": "challenge",
        "process_snapshot": binding(process_path, root), "execution_evidence": binding(execution_path, root),
    }
    preimage_path = root / "controller-preimage.json"
    write_canonical(preimage_path, preimage)
    return locals()


def expect_reject(tmp_path: Path, receipt: dict, code: str) -> None:
    target = tmp_path / f"{code}.json"
    write_canonical(target, receipt)
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(target, package_manifest_sha256=package_sha())
    assert caught.value.code == code


def test_candidate_schemas_are_valid_and_closed_binding_objects():
    for path in [
        PACKAGE / "COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json",
        PACKAGE / "EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json",
    ]:
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    schema = json.loads(
        (PACKAGE / "EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["fileBinding"]["additionalProperties"] is False
    receipt_schema = json.loads(
        (PACKAGE / "COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(receipt_schema).iter_errors(load_base())) == []


def test_historical_f_is_read_only_and_exposes_the_expected_sorting_delta():
    paths = receipt_paths()
    assert len(paths) == 12
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    accepted = 0
    ordering_delta = 0
    for path in paths:
        try:
            report = admission.admit(path, package_manifest_sha256=package_sha())
            accepted += 1
            assert report["status"] == "CANDIDATE_NON_G_ADMISSION_PASS_WITH_UNVERIFIED_CODES"
            assert report["formal_admission"] is False
            assert "CONTROLLER_MATERIAL_PREIMAGE_MISSING" in report["remaining_unknown_codes"]
        except admission.AdmissionError as error:
            assert error.code == "TREE_ENTRY_IDENTITY_ORDER"
            ordering_delta += 1
    # Four D1 receipts preserve the old localeCompare traversal where lowercase
    # names precede an uppercase canary. V1.1 intentionally uses UTF-8 byte order.
    assert (accepted, ordering_delta) == (8, 4)
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda value: value["environment"].insert(
                1, {**value["environment"][0], "value_sha256": "0" * 64}
            ),
            "ENVIRONMENT_IDENTITY_ORDER",
        ),
        (lambda value: value["environment"].reverse(), "ENVIRONMENT_IDENTITY_ORDER"),
        (
            lambda value: value["directory_trees"]["challenge"].update(truncated=True),
            "TREE_TRUNCATED",
        ),
        (
            lambda value: value["directory_trees"]["challenge"]["entries"][1].update(
                path="../escape"
            ),
            "TREE_PATH_GRAMMAR",
        ),
        (
            lambda value: value["process_view"].update(truncated=True),
            "PROCESS_TRUNCATED",
        ),
        (
            lambda value: value["process_view"]["processes"].append(
                {**value["process_view"]["processes"][0], "cmdline_sha256": "0" * 64}
            ),
            "PROCESS_IDENTITY_ORDER",
        ),
        (
            lambda value: value["timing"].update(monotonic_end_ns="0"),
            "MONOTONIC_NESTING",
        ),
    ],
)
def test_redteam_cross_field_mutations_are_rejected(tmp_path: Path, mutate, code: str):
    value = load_base()
    mutate(value)
    expect_reject(tmp_path, value, code)


def test_orphan_environment_canary_is_rejected(tmp_path: Path):
    value = load_base()
    token = "WAVE025_CANARY_TEST_7"
    token_raw = token.encode("utf-8")
    value["visible_canaries"] = [
        {
            "source": "environment-value",
            "location": "NOT_A_LAUNCH_KEY",
            "token_byte_length": len(token_raw),
            "token_sha256": hashlib.sha256(token_raw).hexdigest(),
        }
    ]
    expect_reject(tmp_path, value, "VISIBLE_CANARY_ORPHAN_ENV")


def test_raw_duplicate_member_and_noncanonical_bytes_fail_before_schema(tmp_path: Path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"schema":"x","schema":"y"}\n')
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(duplicate, package_manifest_sha256=package_sha())
    assert caught.value.code == "RAW_DUPLICATE_MEMBER"

    pretty = tmp_path / "pretty.json"
    pretty.write_text(json.dumps(load_base(), indent=2) + "\n", encoding="utf-8")
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(pretty, package_manifest_sha256=package_sha())
    assert caught.value.code == "RAW_NOT_CANONICAL"


def test_external_materials_close_recomputable_relations(tmp_path: Path):
    root = tmp_path / "materials"
    root.mkdir()
    challenge = root / "challenge"
    challenge.mkdir()

    config = challenge / "collector-input.json"
    config.write_bytes(b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n')
    subject = challenge / "input.bin"
    subject.write_bytes(b"candidate-subject\x00bytes")
    environment_path = root / "launch-environment.json"
    environment_doc = {
        "schema": "WAVE025_LAUNCH_ENVIRONMENT_V1_1_CANDIDATE",
        "values": {
            "ALPHA": "ordinary",
            "CANARY_HOLDER": "WAVE025_CANARY_TEST_7",
        },
    }
    write_canonical(environment_path, environment_doc)

    challenge_doc, _ = admission.snapshot_challenge(challenge)
    challenge_snapshot_path = root / "challenge-snapshot.json"
    write_canonical(challenge_snapshot_path, challenge_doc)

    value = load_base()
    value["input_contract"] = {
        "parsed": {"schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"},
        "byte_length": len(config.read_bytes()),
        "sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
    }
    value["subject_input"] = {
        "path": "$CHALLENGE/input.bin",
        "byte_length": len(subject.read_bytes()),
        "sha256": hashlib.sha256(subject.read_bytes()).hexdigest(),
    }
    env_rows, env_canaries = admission.environment_rows(environment_doc["values"])
    _, challenge_canaries = admission.snapshot_challenge(challenge)
    value["environment"] = env_rows
    value["visible_canaries"] = sorted(env_canaries + challenge_canaries, key=admission.canonical_bytes)
    value["directory_trees"]["challenge"] = challenge_doc["directory_tree"]
    value["process_view"] = {
        "available": False,
        "processes": [],
        "self": None,
        "truncated": False,
    }
    receipt_path = root / "receipt.json"
    write_canonical(receipt_path, value)

    execution_path = root / "execution-evidence.json"
    execution_doc = {
        "schema": "WAVE025_RUNNER_EXECUTION_EVIDENCE_V1_1_CANDIDATE",
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "package_manifest_sha256": package_sha(),
        "challenge_read_only": True,
        "controller_domain_worker_writable": False,
        "network_isolation": "RUNNER_ENFORCED",
        "authority_channel_absent": True,
    }
    write_canonical(execution_path, execution_doc)
    binding_doc = {
        "schema": "WAVE025_CONTROLLER_MATERIAL_PREIMAGE_V1_1_CANDIDATE",
        "seal_id": "seal-1",
        "run_id": "run-1",
        "role": "T",
        "slot_id": "slot-1",
        "controller_domain": "EXTERNAL_READ_ONLY_TO_WORKER",
        "package_manifest": {
            "byte_length": (PACKAGE / "PACKAGE-MANIFEST.candidate.json").stat().st_size,
            "sha256": package_sha(),
        },
        "receipt": binding(receipt_path, root),
        "collector_input": binding(config, root),
        "subject_input": binding(subject, root),
        "launch_environment": binding(environment_path, root),
        "challenge_snapshot": binding(challenge_snapshot_path, root),
        "challenge_root_relative_path": "challenge",
        "process_snapshot": None,
        "execution_evidence": binding(execution_path, root),
    }
    binding_path = root / "controller-preimage.json"
    write_canonical(binding_path, binding_doc)

    report = admission.admit(
        receipt_path,
        package_manifest_sha256=package_sha(),
        controller_preimage=binding_path,
        controller_preimage_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
        controller_root=root,
    )
    assert report["status"] == "CANDIDATE_CONTROLLER_MATERIALS_BOUND"
    assert report["formal_admission"] is False

    missing_canary = copy.deepcopy(value)
    missing_canary["visible_canaries"] = []
    write_canonical(receipt_path, missing_canary)
    binding_doc["receipt"] = binding(receipt_path, root)
    execution_doc["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    write_canonical(execution_path, execution_doc)
    binding_doc["execution_evidence"] = binding(execution_path, root)
    write_canonical(binding_path, binding_doc)
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            receipt_path,
            package_manifest_sha256=package_sha(),
            controller_preimage=binding_path,
            controller_preimage_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
            controller_root=root,
        )
    assert caught.value.code == "CONTROLLER_VISIBLE_CANARY_COMPLETENESS"

    forged = copy.deepcopy(value)
    forged["subject_input"]["sha256"] = "0" * 64
    write_canonical(receipt_path, forged)
    binding_doc["receipt"] = binding(receipt_path, root)
    execution_doc["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    write_canonical(execution_path, execution_doc)
    binding_doc["execution_evidence"] = binding(execution_path, root)
    write_canonical(binding_path, binding_doc)
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            receipt_path,
            package_manifest_sha256=package_sha(),
            controller_preimage=binding_path,
            controller_preimage_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest(),
            controller_root=root,
        )
    assert caught.value.code == "CONTROLLER_SUBJECT_MISMATCH"


def test_direct_caps_status_and_timing_sum_counterexamples():
    value = load_base()
    template = value["environment"][0]
    value["environment"] = [
        {**template, "key": f"KEY_{index:04d}"} for index in range(4097)
    ]
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "ENVIRONMENT_CAP"

    value = load_base()
    value["process_view"]["processes"][0]["status"]["ppid"] = "abc"
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "STATUS_GRAMMAR"

    value = load_base()
    start = int(value["timing"]["monotonic_start_ns"])
    value["timing"]["monotonic_end_ns"] = str(start + 1)
    value["collection_window"]["end"]["monotonic_ns"] = str(start + 2)
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "TIMING_SAMPLE_SUM"


def test_depth_and_operation_provenance_counterexamples():
    value = load_base()
    tree = value["directory_trees"]["challenge"]
    root = copy.deepcopy(tree["entries"][0])
    root["type"] = "directory"
    rows = [root]
    for depth in range(1, 6):
        row = copy.deepcopy(root)
        row["path"] = "/".join(["d"] * depth)
        rows.append(row)
    leaf = copy.deepcopy(root)
    leaf["type"] = "file"
    leaf["path"] = "/".join(["d"] * 6)
    rows.append(leaf)
    tree["entries"] = sorted(rows, key=lambda row: row["path"].encode())
    tree["errors"] = []
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "TREE_DEPTH_UNREACHABLE"

    value = load_base()
    value["process_view"]["processes"][0] = {
        "pid": value["process_view"]["processes"][0]["pid"],
        "error": {
            "name": "Error", "code": "ENOENT", "errno": "-2", "syscall": "open",
            "path": f"$PROC/{value['process_view']['processes'][0]['pid']}/not-collected",
            "message": "wrong leaf",
        },
    }
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "PROCESS_ERROR_PATH_PROVENANCE"

    value = load_base()
    value["hostname"]["etc_hostname"] = {
        "error": {"name": "Error", "code": "ENOENT", "errno": "-2", "syscall": "open", "path": "$TMP/unrelated", "message": "wrong"}
    }
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "HOSTNAME_ERROR_PROVENANCE"

    value = load_base()
    challenge = value["directory_trees"]["challenge"]
    challenge["entries"] = [row for row in challenge["entries"] if row["path"] != "input.bin"]
    challenge["errors"] = [{
        "path": "input.bin",
        "error": {"name": "Error", "code": "EACCES", "errno": "-13", "syscall": "connect", "path": "$CHALLENGE/input.bin", "message": "wrong"},
    }]
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_semantics(value)
    assert caught.value.code == "TREE_ERROR_OPERATION_PROVENANCE"


def test_g_requires_process_snapshot_and_rejects_error_unknowns():
    view = load_base()["process_view"]
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_process_snapshot(view, None, g_mode=True)
    assert caught.value.code == "G_PROCESS_SNAPSHOT_REQUIRED"

    error_view = copy.deepcopy(view)
    for row in error_view["processes"]:
        row.clear()
        row.update({
            "pid": 1,
            "error": {"name": "Error", "code": "EIO", "errno": "-5", "syscall": "open", "path": "$PROC/1/cmdline", "message": "x"},
        })
    error_view["processes"] = error_view["processes"][:1]
    error_view["self"] = {
        name: {"error": {"name": "Error", "code": "EIO", "errno": "-5", "syscall": "open", "path": f"$PROC/self/{name}", "message": "x"}}
        for name in ("cgroup", "mountinfo", "status")
    }
    error_view["self"].update({"pid_namespace": None, "mount_namespace": None})
    snapshot = {
        "schema": "WAVE025_PROCESS_SNAPSHOT_V1_1_CANDIDATE",
        "numeric_pid_names": ["1"],
        "processes": [{"pid": 1}],
        "self": {"cgroup": None, "mountinfo": None, "status": None, "pid_namespace": None, "mount_namespace": None},
    }
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_process_snapshot(error_view, snapshot, g_mode=True)
    assert caught.value.code == "G_PROCESS_SNAPSHOT_INCOMPLETE"


def test_g_canary_domain_rejects_large_files(tmp_path: Path):
    challenge = tmp_path / "challenge"
    challenge.mkdir()
    (challenge / "large.bin").write_bytes(b"x" * 65536 + b"WAVE025_CANARY_HIDDEN")
    with pytest.raises(admission.AdmissionError) as caught:
        admission.snapshot_challenge(challenge, reject_oversize=True)
    assert caught.value.code == "G_CANARY_FILE_OVERSIZE"

    for relative in ("cwd", "out", "tmp", "proc/self/fd"):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    source = PACKAGE / "producer-v1.1.candidate.js"
    probe = """
const p=require(process.argv[1]);
p.verifyPackageAtStartup(process.argv[3]);
try {
  p.preflightTreeDomains({challengeRoot:process.argv[2]+'/challenge',cwdRoot:process.argv[2]+'/cwd',outRoot:process.argv[2]+'/out',tmpRoot:process.argv[2]+'/tmp',procRoot:process.argv[2]+'/proc'});
  process.stdout.write('PASS');
} catch (e) { process.stdout.write(e.code); process.exitCode=1; }
"""
    completed = subprocess.run(
        ["node", "-e", probe, str(source), str(tmp_path), package_sha()],
        capture_output=True, text=True,
    )
    assert completed.returncode == 1
    assert completed.stdout == "G_CANARY_FILE_OVERSIZE"


def test_g_controller_sealed_positive_and_sync_forge_regressions(tmp_path: Path):
    fixture = build_g_fixture(tmp_path / "controller")
    report = admission.admit(
        fixture["receipt_path"], package_manifest_sha256=package_sha(),
        controller_preimage=fixture["preimage_path"],
        controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
        controller_root=fixture["root"], g_mode=True,
    )
    assert report["status"] == "CANDIDATE_G_INPUT_ADMISSION_PASS"
    assert report["formal_admission"] is False
    assert report["remaining_unknown_codes"] == ["SAME_PERMISSION_MALICIOUS_PEER_OUT_OF_SCOPE"]

    # Re-sealing mutually forged input bytes is insufficient: strict raw config
    # parsing must still reproduce the receipt's parsed object.
    fixture["config"].write_bytes(b"not-json")
    forged = copy.deepcopy(fixture["value"])
    forged["input_contract"]["byte_length"] = fixture["config"].stat().st_size
    forged["input_contract"]["sha256"] = hashlib.sha256(fixture["config"].read_bytes()).hexdigest()
    write_canonical(fixture["receipt_path"], forged)
    fixture["execution_doc"]["receipt_sha256"] = hashlib.sha256(fixture["receipt_path"].read_bytes()).hexdigest()
    write_canonical(fixture["execution_path"], fixture["execution_doc"])
    fixture["preimage"]["receipt"] = binding(fixture["receipt_path"], fixture["root"])
    fixture["preimage"]["collector_input"] = binding(fixture["config"], fixture["root"])
    fixture["preimage"]["execution_evidence"] = binding(fixture["execution_path"], fixture["root"])
    write_canonical(fixture["preimage_path"], fixture["preimage"])
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            fixture["receipt_path"], package_manifest_sha256=package_sha(),
            controller_preimage=fixture["preimage_path"],
            controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
            controller_root=fixture["root"], g_mode=True,
        )
    assert caught.value.code == "RAW_JSON_INVALID"

    # Restore config, then forge only receipt tree metadata and fully re-seal the
    # output files. Live challenge reconstruction still defeats the forgery.
    fixture = build_g_fixture(tmp_path / "controller-tree")
    forged = copy.deepcopy(fixture["value"])
    forged["directory_trees"]["challenge"]["entries"][0]["size_bytes"] = "999999"
    write_canonical(fixture["receipt_path"], forged)
    fixture["execution_doc"]["receipt_sha256"] = hashlib.sha256(fixture["receipt_path"].read_bytes()).hexdigest()
    write_canonical(fixture["execution_path"], fixture["execution_doc"])
    fixture["preimage"]["receipt"] = binding(fixture["receipt_path"], fixture["root"])
    fixture["preimage"]["execution_evidence"] = binding(fixture["execution_path"], fixture["root"])
    write_canonical(fixture["preimage_path"], fixture["preimage"])
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            fixture["receipt_path"], package_manifest_sha256=package_sha(),
            controller_preimage=fixture["preimage_path"],
            controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
            controller_root=fixture["root"], g_mode=True,
        )
    assert caught.value.code == "CONTROLLER_CHALLENGE_TREE_MISMATCH"


def test_g_exact_role_paths_reject_external_reseal_role_swap_alias_and_spelling(tmp_path: Path):
    # Replay the independent reviewer counterexample with fully valid external
    # role files and a newly sealed, internally consistent preimage.
    fixture = build_g_fixture(tmp_path / "external-role")
    external_config = fixture["root"] / "external-config.json"
    external_config.write_bytes(b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n')
    external_subject = fixture["root"] / "external-subject.bin"
    external_subject.write_bytes(b"different-external-subject")
    fixture["config"].write_bytes(b'{ "schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1" }\n')
    fixture["subject"].write_bytes(b"actual-challenge-subject")
    challenge_doc, challenge_canaries = admission.snapshot_challenge(fixture["challenge"], reject_oversize=True)
    write_canonical(fixture["challenge_snapshot_path"], challenge_doc)
    forged = copy.deepcopy(fixture["value"])
    forged["input_contract"] = {
        "parsed": {"schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"},
        "byte_length": external_config.stat().st_size,
        "sha256": hashlib.sha256(external_config.read_bytes()).hexdigest(),
    }
    forged["subject_input"] = {
        "path": "$CHALLENGE/input.bin", "byte_length": external_subject.stat().st_size,
        "sha256": hashlib.sha256(external_subject.read_bytes()).hexdigest(),
    }
    _, env_canaries = admission.environment_rows(fixture["environment_doc"]["values"])
    forged["visible_canaries"] = sorted(env_canaries + challenge_canaries, key=admission.canonical_bytes)
    forged["directory_trees"]["challenge"] = challenge_doc["directory_tree"]
    write_canonical(fixture["receipt_path"], forged)
    fixture["execution_doc"]["receipt_sha256"] = hashlib.sha256(fixture["receipt_path"].read_bytes()).hexdigest()
    write_canonical(fixture["execution_path"], fixture["execution_doc"])
    fixture["preimage"].update({
        "receipt": binding(fixture["receipt_path"], fixture["root"]),
        "collector_input": binding(external_config, fixture["root"]),
        "subject_input": binding(external_subject, fixture["root"]),
        "challenge_snapshot": binding(fixture["challenge_snapshot_path"], fixture["root"]),
        "execution_evidence": binding(fixture["execution_path"], fixture["root"]),
    })
    write_canonical(fixture["preimage_path"], fixture["preimage"])
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            fixture["receipt_path"], package_manifest_sha256=package_sha(),
            controller_preimage=fixture["preimage_path"],
            controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
            controller_root=fixture["root"], g_mode=True,
        )
    assert caught.value.code == "CONTROLLER_PREIMAGE_SCHEMA_INVALID"

    for index, mutation in enumerate(("role-swap", "dot-spelling", "double-slash")):
        fixture = build_g_fixture(tmp_path / f"mapping-{index}")
        if mutation == "role-swap":
            fixture["preimage"]["collector_input"], fixture["preimage"]["subject_input"] = (
                fixture["preimage"]["subject_input"], fixture["preimage"]["collector_input"]
            )
        elif mutation == "dot-spelling":
            fixture["preimage"]["subject_input"]["relative_path"] = "challenge/./input.bin"
        else:
            fixture["preimage"]["subject_input"]["relative_path"] = "challenge//input.bin"
        write_canonical(fixture["preimage_path"], fixture["preimage"])
        with pytest.raises(admission.AdmissionError) as caught:
            admission.admit(
                fixture["receipt_path"], package_manifest_sha256=package_sha(),
                controller_preimage=fixture["preimage_path"],
                controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
                controller_root=fixture["root"], g_mode=True,
            )
        assert caught.value.code == "CONTROLLER_PREIMAGE_SCHEMA_INVALID"

    fixture = build_g_fixture(tmp_path / "symlink-role")
    external_subject = fixture["root"] / "symlink-target.bin"
    external_subject.write_bytes(fixture["subject"].read_bytes())
    fixture["subject"].unlink()
    fixture["subject"].symlink_to(external_subject)
    fixture["preimage"]["subject_input"] = binding(fixture["subject"], fixture["root"])
    write_canonical(fixture["preimage_path"], fixture["preimage"])
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            fixture["receipt_path"], package_manifest_sha256=package_sha(),
            controller_preimage=fixture["preimage_path"],
            controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
            controller_root=fixture["root"], g_mode=True,
        )
    assert caught.value.code == "BINDING_SYMLINK"

    fixture = build_g_fixture(tmp_path / "hardlink-alias")
    fixture["subject"].unlink()
    __import__("os").link(fixture["config"], fixture["subject"])
    fixture["preimage"]["subject_input"] = binding(fixture["subject"], fixture["root"])
    write_canonical(fixture["preimage_path"], fixture["preimage"])
    with pytest.raises(admission.AdmissionError) as caught:
        admission.admit(
            fixture["receipt_path"], package_manifest_sha256=package_sha(),
            controller_preimage=fixture["preimage_path"],
            controller_preimage_sha256=hashlib.sha256(fixture["preimage_path"].read_bytes()).hexdigest(),
            controller_root=fixture["root"], g_mode=True,
        )
    assert caught.value.code == "CONTROLLER_ROLE_FILE_ALIAS"


def test_controller_seal_hash_cannot_be_synchronously_rewritten(tmp_path: Path):
    preimage = tmp_path / "controller-preimage.json"
    write_canonical(preimage, {"schema": "placeholder"})
    sealed = hashlib.sha256(preimage.read_bytes()).hexdigest()
    write_canonical(preimage, {"schema": "rewritten"})
    receipt = tmp_path / "receipt.json"
    write_canonical(receipt, load_base())
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_controller_preimage(
            receipt, receipt.read_bytes(), load_base(), preimage, sealed, tmp_path,
            package_sha(), g_mode=True,
        )
    assert caught.value.code == "CONTROLLER_SEAL_MISMATCH"


def test_runtime_manifest_missing_and_tampered_source_fail_closed(tmp_path: Path):
    experiment_copy = tmp_path / "experiment"
    package_copy = experiment_copy / "feature-spec" / "collector-v1.1-candidate"
    package_copy.parent.mkdir(parents=True)
    shutil.copytree(PACKAGE, package_copy)
    shutil.copy2(FEATURE_SPEC / "COLLECTOR-RECEIPT-V1.candidate.schema.json", package_copy.parent)
    base_copy = experiment_copy / "attackers" / "leak-only-collector"
    base_copy.mkdir(parents=True)
    shutil.copy2(EXPERIMENT / "attackers" / "leak-only-collector" / "collector.js", base_copy)
    manifest = package_copy / "PACKAGE-MANIFEST.candidate.json"
    expected = hashlib.sha256(manifest.read_bytes()).hexdigest()
    source = package_copy / "producer-v1.1.candidate.js"
    probe = "const p=require(process.argv[1]);try{p.verifyPackageAtStartup(process.argv[2]);process.stdout.write('PASS')}catch(e){process.stdout.write(e.code);process.exitCode=1}"

    manifest.unlink()
    completed = subprocess.run(["node", "-e", probe, str(source), expected], capture_output=True, text=True)
    assert completed.returncode == 1
    assert completed.stdout == "PACKAGE_MANIFEST_MISSING"
    cli = package_copy / "admit_receipt_v1_1.py"
    completed = subprocess.run(
        [__import__("sys").executable, str(cli), "--receipt", str(receipt_paths()[0]), "--package-manifest-sha256", expected],
        capture_output=True, text=True,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["error"]["code"] == "PACKAGE_MANIFEST_MISSING"

    shutil.copy2(PACKAGE / "PACKAGE-MANIFEST.candidate.json", manifest)
    source.write_text(source.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8")
    completed = subprocess.run(["node", "-e", probe, str(source), expected], capture_output=True, text=True)
    assert completed.returncode == 1
    assert completed.stdout == "PACKAGE_FILE_MISMATCH"
    completed = subprocess.run(
        [__import__("sys").executable, str(cli), "--receipt", str(receipt_paths()[0]), "--package-manifest-sha256", expected],
        capture_output=True, text=True,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["error"]["code"] == "PACKAGE_FILE_MISMATCH"

    shutil.copy2(PACKAGE / "producer-v1.1.candidate.js", source)
    (package_copy.parent / "COLLECTOR-RECEIPT-V1.candidate.schema.json").unlink()
    completed = subprocess.run(["node", "-e", probe, str(source), expected], capture_output=True, text=True)
    assert completed.returncode == 1
    assert completed.stdout == "PACKAGE_FILE_MISSING"
    completed = subprocess.run(
        [__import__("sys").executable, str(cli), "--receipt", str(receipt_paths()[0]), "--package-manifest-sha256", expected],
        capture_output=True, text=True,
    )
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["error"]["code"] == "PACKAGE_FILE_MISSING"


def test_proc_provider_total_entries_and_name_bytes_are_incrementally_bounded():
    source = PACKAGE / "producer-v1.1.candidate.js"
    probe = """
const p=require(process.argv[1]);
p.verifyPackageAtStartup(process.argv[2]);
const fs=require('node:fs');
fs.existsSync=()=>true;
const mode=process.argv[3];
fs.opendirSync=()=>({i:0,readSync(){
  this.i+=1;
  if (mode==='entries') return this.i<=4097 ? {name:'nonpid-'+this.i} : null;
  if (mode==='bytes') return this.i===1 ? {name:'x'.repeat(1048577)} : null;
  return this.i<=257 ? {name:String(this.i)} : null;
},closeSync(){}});
try { p.assertCanonicalProcProvider('/synthetic-proc'); process.stdout.write('PASS'); }
catch(e) { process.stdout.write(e.code); process.exitCode=1; }
"""
    for mode, expected in (
        ("entries", "PROC_DIRECTORY_ENTRY_CAP"),
        ("bytes", "PROC_DIRECTORY_NAME_BYTES_CAP"),
        ("numeric", "PROCESS_TRUNCATION"),
    ):
        completed = subprocess.run(
            ["node", "-e", probe, str(source), package_sha(), mode],
            capture_output=True, text=True,
        )
        assert completed.returncode == 1
        assert completed.stdout == expected


def test_g_base_consumes_bounded_proc_snapshot_not_second_full_readdir(tmp_path: Path):
    for relative in ("challenge", "cwd", "out", "tmp", "proc/self/fd"):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    (tmp_path / "challenge/collector-input.json").write_bytes(
        b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n'
    )
    (tmp_path / "challenge/input.bin").write_bytes(b"subject")
    for name, raw in (("cgroup", b"0::/\n"), ("mountinfo", b"1 2 3\n"), ("status", b"Name:\tnode\n")):
        (tmp_path / "proc/self" / name).write_bytes(raw)
    source = PACKAGE / "producer-v1.1.candidate.js"
    probe = """
const fs=require('node:fs'); const path=require('node:path');
const p=require(process.argv[1]); const root=process.argv[2];
const proc=path.resolve(root+'/proc'); const original=fs.readdirSync; let procCalls=0;
fs.readdirSync=function(target,...args){if(path.resolve(String(target))===proc)procCalls+=1;return original.call(fs,target,...args)};
const originalStat=fs.statSync; fs.statSync=function(target,...args){if(String(target)==='/etc/hostname')return {size:0};return originalStat.call(fs,target,...args)};
let code='PASS';
try {p.collectCandidate({challengeRoot:root+'/challenge',configPath:root+'/challenge/collector-input.json',subjectPath:root+'/challenge/input.bin',outRoot:root+'/out',procRoot:root+'/proc',tmpRoot:root+'/tmp',cwdRoot:root+'/cwd',packageManifestSha256:process.argv[3],gMode:true});}
catch(e){code=e.code}
process.stdout.write(JSON.stringify({code,procCalls}));
"""
    completed = subprocess.run(
        ["node", "-e", probe, str(source), str(tmp_path), package_sha()],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {"code": "G_UNVERIFIED_ERROR_BRANCH", "procCalls": 0}


def test_candidate_producer_adapter_executes_its_fail_closed_validator():
    source = PACKAGE / "producer-v1.1.candidate.js"
    receipt = receipt_paths()[0]
    script = """
const fs=require('node:fs');
const producer=require(process.argv[1]);
const value=JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const normalized=producer.normalizeAndValidateReceipt(value, value.visible_canaries);
process.stdout.write(producer.ADAPTER_VERSION + ':' + normalized.schema);
"""
    completed = subprocess.run(
        ["node", "-e", script, str(source), str(receipt)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "1.1.0-candidate:WAVE025_LEAK_ONLY_FEATURES_V1"


def test_candidate_producer_collects_in_an_isolated_minimal_runtime(tmp_path: Path):
    challenge = tmp_path / "challenge"
    challenge.mkdir()
    (tmp_path / "out").mkdir()
    (tmp_path / "cwd").mkdir()
    (tmp_path / "tmp").mkdir()
    (challenge / "collector-input.json").write_bytes(
        b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n'
    )
    (challenge / "input.bin").write_bytes(b"isolated-candidate-subject")
    source = PACKAGE / "producer-v1.1.candidate.js"
    script = """
const producer=require(process.argv[1]);
const root=process.argv[2];
const value=producer.collectCandidate({
  challengeRoot:root+'/challenge',
  configPath:root+'/challenge/collector-input.json',
  subjectPath:root+'/challenge/input.bin',
  outRoot:root+'/out',
  procRoot:root+'/missing-proc',
  tmpRoot:root+'/tmp',
  cwdRoot:root+'/cwd',
  packageManifestSha256:process.argv[3]
});
process.stdout.write(JSON.stringify({schema:value.schema,available:value.process_view.available,truncated:value.directory_trees.challenge.truncated}));
"""
    completed = subprocess.run(
        ["node", "-e", script, str(source), str(tmp_path), package_sha()],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "schema": "WAVE025_LEAK_ONLY_FEATURES_V1",
        "available": False,
        "truncated": False,
    }


def test_process_snapshot_recomputes_raw_cmdline_status_and_self():
    cmdline = b"node\0/app/collector.js\0"
    status = b"Name:\tagent\nState:\tR (running)\nPPid:\t0\nUid:\t1\t1\t1\t1\nGid:\t2\t2\t2\t2\nThreads:\t1\n"
    self_raw = {
        "cgroup": b"0::/\n",
        "mountinfo": b"1 2 3\n",
        "status": status,
    }
    view = {
        "available": True,
        "truncated": False,
        "processes": [
            {
                "pid": 7,
                "cmdline": ["node", "/app/collector.js"],
                "cmdline_byte_length": len(cmdline),
                "cmdline_sha256": hashlib.sha256(cmdline).hexdigest(),
                "status": admission.parse_status(status),
                "pid_namespace": "pid:[7]",
                "mount_namespace": "mnt:[8]",
            }
        ],
        "self": {
            **{
                name: {
                    "byte_length": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
                for name, raw in self_raw.items()
            },
            "pid_namespace": "pid:[7]",
            "mount_namespace": "mnt:[8]",
        },
    }
    snapshot = {
        "schema": "WAVE025_PROCESS_SNAPSHOT_V1_1_CANDIDATE",
        "numeric_pid_names": ["7"],
        "processes": [
            {
                "pid": 7,
                "cmdline_base64": __import__("base64").b64encode(cmdline).decode("ascii"),
                "status_base64": __import__("base64").b64encode(status).decode("ascii"),
                "pid_namespace": "pid:[7]",
                "mount_namespace": "mnt:[8]",
            }
        ],
        "self": {
            **{
                name: __import__("base64").b64encode(raw).decode("ascii")
                for name, raw in self_raw.items()
            },
            "pid_namespace": "pid:[7]",
            "mount_namespace": "mnt:[8]",
        },
    }
    assert admission.validate_process_snapshot(view, snapshot, g_mode=True) == []
    forged = copy.deepcopy(snapshot)
    forged["processes"][0]["cmdline_base64"] = __import__("base64").b64encode(
        b"different\0"
    ).decode("ascii")
    with pytest.raises(admission.AdmissionError) as caught:
        admission.validate_process_snapshot(view, forged, g_mode=True)
    assert caught.value.code == "PROCESS_SNAPSHOT_ROW_MISMATCH"
