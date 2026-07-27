#!/usr/bin/env python3
"""Run a bounded macOS sandbox-exec sovereign/centralized comparison."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def profile(denied_paths: list[Path]) -> str:
    rules = ["(version 1)", "(allow default)", "(deny network*)"]
    for denied in denied_paths:
        rules.append(f'(deny file-read* (literal "{denied}"))')
        rules.append(f'(deny file-write* (literal "{denied}"))')
    return "\n".join(rules)


def generate_keypair(private_path: Path, public_path: Path) -> None:
    key = Ed25519PrivateKey.generate()
    private_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_path.chmod(0o600)
    public_path.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def run_process(
    command: list[str],
    log_dir: Path,
    name: str,
    sandbox_profile: str | None = None,
) -> dict[str, Any]:
    actual = command
    if sandbox_profile is not None:
        actual = ["/usr/bin/sandbox-exec", "-p", sandbox_profile, *command]
    started = time.monotonic()
    completed = subprocess.run(
        actual,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
    )
    duration_ms = round((time.monotonic() - started) * 1000, 3)
    (log_dir / f"{name}.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (log_dir / f"{name}.stderr.log").write_text(completed.stderr, encoding="utf-8")
    return {
        "name": name,
        "exit_code": completed.returncode,
        "duration_ms": duration_ms,
        "sandboxed": sandbox_profile is not None,
        "stdout_bytes": len(completed.stdout.encode()),
        "stderr_bytes": len(completed.stderr.encode()),
    }


def node_command(
    node: Path,
    role: str,
    packet: Path,
    repo: Path,
    shared: Path,
    output: Path,
    extra: list[str],
) -> list[str]:
    return [
        "/usr/bin/python3",
        str(node),
        role,
        "--packet",
        str(packet),
        "--repo",
        str(repo),
        "--shared",
        str(shared),
        "--output",
        str(output),
        *extra,
    ]


def setup_world(root: Path) -> dict[str, Path]:
    producer_private = root / "producer_private"
    validator_private = root / "validator_private"
    shared = root / "shared"
    for directory in (producer_private, validator_private, shared):
        directory.mkdir(parents=True)
    producer_canary = producer_private / "canary.txt"
    validator_canary = validator_private / "canary.txt"
    producer_canary.write_text("producer-private-canary-r5", encoding="utf-8")
    validator_canary.write_text("validator-private-canary-r5", encoding="utf-8")
    policy = validator_private / "policy.json"
    write_json(
        policy,
        {
            "expected_claims": 18,
            "expected_reachable": 2,
            "expected_missing": 16,
        },
    )
    generate_keypair(
        producer_private / "ed25519.private", shared / "producer.ed25519.public"
    )
    generate_keypair(
        validator_private / "ed25519.private", shared / "validator.ed25519.public"
    )
    write_json(
        shared / "capability_cards.json",
        {
            "producer": ["audit_baseline_reachability", "sign_report"],
            "validator": ["verify_report", "apply_private_acceptance_policy"],
        },
    )
    return {
        "producer_private": producer_private,
        "validator_private": validator_private,
        "shared": shared,
        "producer_canary": producer_canary,
        "validator_canary": validator_canary,
        "policy": policy,
    }


def copy_public(shared: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in shared.iterdir():
        if path.is_file():
            shutil.copy2(path, destination / path.name)
            copied += 1
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    packet = args.packet.resolve()
    node = args.node.resolve()
    output = args.output.resolve()
    logs = output / "logs"
    outputs = output / "outputs"
    logs.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    run_started = time.monotonic()
    records: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="towow-r5-sovereign-") as temp_root:
        # macOS exposes /var as a symlink to /private/var. Sandbox literal
        # filters match the kernel-resolved path, so bind policies to the
        # canonical temporary root rather than the display path.
        temp = Path(temp_root).resolve()

        central_world = setup_world(temp / "central")
        central_out = temp / "central_result.json"
        central_record = run_process(
            node_command(
                node,
                "central",
                packet,
                repo,
                central_world["shared"],
                central_out,
                [
                    "--producer-canary",
                    str(central_world["producer_canary"]),
                    "--validator-canary",
                    str(central_world["validator_canary"]),
                    "--policy",
                    str(central_world["policy"]),
                ],
            ),
            logs,
            "central",
        )
        records["centralized"] = {
            "processes": [central_record],
            "result": json.loads(central_out.read_text(encoding="utf-8")),
        }

        honest_world = setup_world(temp / "honest")
        coord_profile = profile(
            [
                honest_world["producer_canary"],
                honest_world["producer_private"] / "ed25519.private",
                honest_world["validator_canary"],
                honest_world["validator_private"] / "ed25519.private",
                honest_world["policy"],
                packet / "baseline" / "CLAIM_EVIDENCE_BASELINE_R5.csv",
            ]
        )
        producer_profile = profile(
            [
                honest_world["validator_canary"],
                honest_world["validator_private"] / "ed25519.private",
                honest_world["policy"],
            ]
        )
        validator_profile = profile(
            [
                honest_world["producer_canary"],
                honest_world["producer_private"] / "ed25519.private",
            ]
        )
        honest_records: list[dict[str, Any]] = []
        preflight_out = temp / "honest_preflight.json"
        honest_records.append(
            run_process(
                node_command(
                    node,
                    "coordinator_preflight",
                    packet,
                    repo,
                    honest_world["shared"],
                    preflight_out,
                    [
                        "--producer-canary",
                        str(honest_world["producer_canary"]),
                        "--validator-canary",
                        str(honest_world["validator_canary"]),
                        "--producer-private-key-probe",
                        str(honest_world["producer_private"] / "ed25519.private"),
                        "--validator-private-key-probe",
                        str(honest_world["validator_private"] / "ed25519.private"),
                    ],
                ),
                logs,
                "honest_coordinator_preflight",
                coord_profile,
            )
        )
        producer_out = temp / "honest_producer.json"
        honest_records.append(
            run_process(
                node_command(
                    node,
                    "producer",
                    packet,
                    repo,
                    honest_world["shared"],
                    producer_out,
                    [
                        "--private-key",
                        str(honest_world["producer_private"] / "ed25519.private"),
                        "--other-canary",
                        str(honest_world["validator_canary"]),
                        "--other-private-key-probe",
                        str(honest_world["validator_private"] / "ed25519.private"),
                    ],
                ),
                logs,
                "honest_producer",
                producer_profile,
            )
        )
        validator_out = temp / "honest_validator.json"
        honest_records.append(
            run_process(
                node_command(
                    node,
                    "validator",
                    packet,
                    repo,
                    honest_world["shared"],
                    validator_out,
                    [
                        "--private-key",
                        str(honest_world["validator_private"] / "ed25519.private"),
                        "--producer-public-key",
                        str(honest_world["shared"] / "producer.ed25519.public"),
                        "--other-canary",
                        str(honest_world["producer_canary"]),
                        "--other-private-key-probe",
                        str(honest_world["producer_private"] / "ed25519.private"),
                        "--policy",
                        str(honest_world["policy"]),
                    ],
                ),
                logs,
                "honest_validator",
                validator_profile,
            )
        )
        final_out = temp / "honest_final.json"
        honest_records.append(
            run_process(
                node_command(
                    node,
                    "coordinator_finalize",
                    packet,
                    repo,
                    honest_world["shared"],
                    final_out,
                    [
                        "--producer-canary",
                        str(honest_world["producer_canary"]),
                        "--validator-canary",
                        str(honest_world["validator_canary"]),
                        "--producer-private-key-probe",
                        str(honest_world["producer_private"] / "ed25519.private"),
                        "--validator-private-key-probe",
                        str(honest_world["validator_private"] / "ed25519.private"),
                        "--validator-public-key",
                        str(honest_world["shared"] / "validator.ed25519.public"),
                    ],
                ),
                logs,
                "honest_coordinator_finalize",
                coord_profile,
            )
        )
        records["sovereign_honest"] = {
            "processes": honest_records,
            "preflight": json.loads(preflight_out.read_text(encoding="utf-8")),
            "producer": json.loads(producer_out.read_text(encoding="utf-8")),
            "validator": json.loads(validator_out.read_text(encoding="utf-8")),
            "final": json.loads(final_out.read_text(encoding="utf-8")),
            "public_files_copied": copy_public(
                honest_world["shared"], outputs / "honest_public"
            ),
        }

        tamper_world = setup_world(temp / "tamper")
        tamper_coord_profile = profile(
            [
                tamper_world["producer_canary"],
                tamper_world["producer_private"] / "ed25519.private",
                tamper_world["validator_canary"],
                tamper_world["validator_private"] / "ed25519.private",
                tamper_world["policy"],
                packet / "baseline" / "CLAIM_EVIDENCE_BASELINE_R5.csv",
            ]
        )
        tamper_producer_profile = profile(
            [
                tamper_world["validator_canary"],
                tamper_world["validator_private"] / "ed25519.private",
                tamper_world["policy"],
            ]
        )
        tamper_validator_profile = profile(
            [
                tamper_world["producer_canary"],
                tamper_world["producer_private"] / "ed25519.private",
            ]
        )
        tamper_records: list[dict[str, Any]] = []
        tamper_preflight = temp / "tamper_preflight.json"
        tamper_records.append(
            run_process(
                node_command(
                    node,
                    "coordinator_preflight",
                    packet,
                    repo,
                    tamper_world["shared"],
                    tamper_preflight,
                    [
                        "--producer-canary",
                        str(tamper_world["producer_canary"]),
                        "--validator-canary",
                        str(tamper_world["validator_canary"]),
                        "--producer-private-key-probe",
                        str(tamper_world["producer_private"] / "ed25519.private"),
                        "--validator-private-key-probe",
                        str(tamper_world["validator_private"] / "ed25519.private"),
                    ],
                ),
                logs,
                "tamper_coordinator_preflight",
                tamper_coord_profile,
            )
        )
        tamper_producer_out = temp / "tamper_producer.json"
        tamper_records.append(
            run_process(
                node_command(
                    node,
                    "producer",
                    packet,
                    repo,
                    tamper_world["shared"],
                    tamper_producer_out,
                    [
                        "--private-key",
                        str(tamper_world["producer_private"] / "ed25519.private"),
                        "--other-canary",
                        str(tamper_world["validator_canary"]),
                        "--other-private-key-probe",
                        str(tamper_world["validator_private"] / "ed25519.private"),
                    ],
                ),
                logs,
                "tamper_producer",
                tamper_producer_profile,
            )
        )
        report_path = tamper_world["shared"] / "report.json"
        tampered_report = json.loads(report_path.read_text(encoding="utf-8"))
        tampered_report["reachable"] = tampered_report["reachable"] + 1
        write_json(report_path, tampered_report)
        tamper_validator_out = temp / "tamper_validator.json"
        tamper_records.append(
            run_process(
                node_command(
                    node,
                    "validator",
                    packet,
                    repo,
                    tamper_world["shared"],
                    tamper_validator_out,
                    [
                        "--private-key",
                        str(tamper_world["validator_private"] / "ed25519.private"),
                        "--producer-public-key",
                        str(tamper_world["shared"] / "producer.ed25519.public"),
                        "--other-canary",
                        str(tamper_world["producer_canary"]),
                        "--other-private-key-probe",
                        str(tamper_world["producer_private"] / "ed25519.private"),
                        "--policy",
                        str(tamper_world["policy"]),
                    ],
                ),
                logs,
                "tamper_validator",
                tamper_validator_profile,
            )
        )
        tamper_final_out = temp / "tamper_final.json"
        tamper_records.append(
            run_process(
                node_command(
                    node,
                    "coordinator_finalize",
                    packet,
                    repo,
                    tamper_world["shared"],
                    tamper_final_out,
                    [
                        "--producer-canary",
                        str(tamper_world["producer_canary"]),
                        "--validator-canary",
                        str(tamper_world["validator_canary"]),
                        "--producer-private-key-probe",
                        str(tamper_world["producer_private"] / "ed25519.private"),
                        "--validator-private-key-probe",
                        str(tamper_world["validator_private"] / "ed25519.private"),
                        "--validator-public-key",
                        str(tamper_world["shared"] / "validator.ed25519.public"),
                    ],
                ),
                logs,
                "tamper_coordinator_finalize",
                tamper_coord_profile,
            )
        )
        records["sovereign_tampered"] = {
            "processes": tamper_records,
            "intervention": "Controller changed reachable count after producer signature.",
            "validator": json.loads(tamper_validator_out.read_text(encoding="utf-8")),
            "final": json.loads(tamper_final_out.read_text(encoding="utf-8")),
            "public_files_copied": copy_public(
                tamper_world["shared"], outputs / "tampered_public"
            ),
        }

    central_ms = sum(
        process["duration_ms"] for process in records["centralized"]["processes"]
    )
    sovereign_ms = sum(
        process["duration_ms"]
        for process in records["sovereign_honest"]["processes"]
    )
    honest_private_probes = records["sovereign_honest"]["final"][
        "private_and_packet_probes"
    ]
    summary = {
        "schema_version": "towow-r5-sovereign-workspace-lab-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "Audit actual v1.1 baseline artifact reachability and obtain a signed policy verdict without coordinator access to packet or principal private directories.",
        "classification": "partial_sovereign_literal_file_fixture_E3_with_real_workspace_data",
        "centralized": {
            "accepted": records["centralized"]["result"]["accepted"],
            "private_world_exposure": all(
                records["centralized"]["result"]["private_canaries_read"].values()
            ),
            "process_count": 1,
            "cumulative_process_ms": central_ms,
        },
        "static_profile": {
            "accepted": records["sovereign_honest"]["preflight"][
                "static_profile_can_complete"
            ],
            "status": records["sovereign_honest"]["preflight"]["status"],
        },
        "sovereign_honest": {
            "accepted": records["sovereign_honest"]["final"]["accepted"],
            "coordinator_private_or_packet_read_allowed": any(
                probe["allowed"] for probe in honest_private_probes.values()
            ),
            "producer_other_private_read_allowed": records["sovereign_honest"][
                "producer"
            ]["other_private_read"]["allowed"],
            "producer_other_private_key_read_allowed": records[
                "sovereign_honest"
            ]["producer"]["other_private_key_read"]["allowed"],
            "validator_other_private_read_allowed": records["sovereign_honest"][
                "validator"
            ]["other_private_read"]["allowed"],
            "validator_other_private_key_read_allowed": records[
                "sovereign_honest"
            ]["validator"]["other_private_key_read"]["allowed"],
            "validator_signature_valid": records["sovereign_honest"]["final"][
                "validator_signature_valid"
            ],
            "report_hash_matches": records["sovereign_honest"]["final"][
                "report_hash_matches"
            ],
            "process_count": 4,
            "cumulative_process_ms": sovereign_ms,
        },
        "sovereign_tampered": {
            "accepted": records["sovereign_tampered"]["final"]["accepted"],
            "validator_reason": records["sovereign_tampered"]["validator"]["verdict"][
                "reason"
            ],
            "report_hash_matches": records["sovereign_tampered"]["final"][
                "report_hash_matches"
            ],
        },
        "coordination_overhead": {
            "process_ratio_sovereign_to_central": 4.0,
            "cumulative_process_time_ratio": (
                sovereign_ms / central_ms if central_ms else None
            ),
            "approval_gates_to_form_boundary": 4,
            "note": "Three mechanism probes plus one exact lab execution approval.",
        },
        "trusted_test_controller": {
            "omniscient": True,
            "role": "Creates worlds, applies sandbox profiles, and records evidence; it is not the runtime coordinator.",
        },
        "boundary_coverage": {
            "declared_canaries_private_keys_policy_and_packet_baseline": "probed or explicitly denied",
            "dynamic_future_private_files": "not covered by literal rules",
            "directory_listing_confidentiality": "not tested",
        },
        "private_keys_persisted": False,
        "scope_limit": (
            "Deterministic Python roles, one macOS host and one real packet task; "
            "no strong-model behavior, human recognition, production effect, or "
            "cross-organization adversary."
        ),
    }
    write_json(outputs / "records.json", records)
    write_json(outputs / "summary.json", summary)
    write_json(
        outputs / "costs.json",
        {
            "api_cost": 0,
            "external_calls": 0,
            "central_process_ms": central_ms,
            "sovereign_process_ms": sovereign_ms,
            "process_time_ratio": sovereign_ms / central_ms if central_ms else None,
            "central_processes": 1,
            "sovereign_processes": 4,
            "approval_gates_to_form_boundary": 4,
        },
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
