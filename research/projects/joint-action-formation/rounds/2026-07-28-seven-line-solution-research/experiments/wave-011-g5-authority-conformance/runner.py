#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcb_g5.common import load_json, sha256, write_json
from mcb_g5.simulation import (
    OwnerCluster,
    audit_adversarial_corpus,
    run_authority_strata,
    run_fence_matrix,
    run_materiality_standing_migration,
    run_native_conformance,
    run_owner_independence,
    run_races,
)


def build_results() -> dict:
    runtime = ROOT / "artifacts" / "runtime" / "current"
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)

    worlds = load_json(ROOT / "fixtures" / "authority-worlds.json")
    operation_hash = sha256(worlds["operation"])
    cluster = OwnerCluster(ROOT, runtime / "owners")
    try:
        owner_independence = run_owner_independence(cluster)
        authority_strata = run_authority_strata(ROOT, cluster, operation_hash)
        races = run_races(ROOT, cluster, operation_hash, runtime)
    finally:
        cluster.close()

    native = run_native_conformance(ROOT)
    fence = run_fence_matrix(ROOT, runtime, operation_hash)
    closure = run_materiality_standing_migration(ROOT)
    adversarial_corpus = audit_adversarial_corpus(ROOT)

    validations = {
        "four_owner_process_store_key": all(
            [
                owner_independence["distinct_processes"],
                owner_independence["distinct_stores"],
                owner_independence["distinct_public_keys"],
                owner_independence["initial_reads_signed"],
            ]
        ),
        "owner_reject_revoke_outage_fork_exposed": (
            owner_independence["fault_observations"]["program-coordinator"][
                "owner_read_after"
            ]["envelope"]["payload"]["body"]["stance"]
            == "REJECT"
            and owner_independence["fault_observations"]["delta-calibration"][
                "owner_read_after"
            ]["envelope"]["payload"]["body"]["mandate"]
            == "REVOKED"
            and owner_independence["fault_observations"]["independent-validation"][
                "owner_read_after"
            ]["status"]
            == "OUTAGE"
            and bool(
                owner_independence["fault_observations"]["site-data-steward"][
                    "owner_read_after"
                ]["envelope"]["payload"]["body"]["fork_views"]
            )
        ),
        "native_raw_and_mapping_exact": (
            native["all_native_exact"] and native["all_business_exact"]
        ),
        "provider_adapter_shape_corpus_exact": native[
            "provider_adapter_corpus"
        ]["all_business_exact"],
        "fence_failure_modes_exposed": fence["all_failure_modes_exposed"],
        "material_closure_exact": closure["material_operation_closure"]["all_exact"],
        "standing_lifecycle_exact": closure["standing_lifecycle"]["all_exact"],
        "u_p_permission_equal": all(
            row["stratum"]["technical_permissions"] == "IDENTICAL_FULL_CONTROL"
            for row in authority_strata["rows"][:2]
        ),
        "u_p_authority_differs": (
            authority_strata["rows"][0]["stratum"]["normative_authority"]
            != authority_strata["rows"][1]["stratum"]["normative_authority"]
        ),
        "adversarial_corpus_structurally_complete": all(
            [
                adversarial_corpus["unique_ids"],
                adversarial_corpus["families_complete"],
                adversarial_corpus["race_boundaries_complete"],
            ]
        ),
    }

    return {
        "schema": "mcb-g5-v2.discriminator-results.v1",
        "status": (
            "COMPLETE_LOCAL_SYNTHETIC_DISCRIMINATOR"
            if all(validations.values())
            else "HARNESS_FAILURE"
        ),
        "claim": (
            "This run distinguishes candidate G5 failure classes and strategy "
            "guarantee boundaries. It does not establish a canonical IR, stable "
            "residual, production closure, or product comparison."
        ),
        "operation_hash": operation_hash,
        "engine_status": native["engine_runs"],
        "owner_independence": owner_independence,
        "authority_strata": authority_strata,
        "native_outcome_conformance": native,
        "cross_owner_races": races,
        "target_fence": fence,
        "materiality_standing_migration": closure,
        "adversarial_corpus_audit": adversarial_corpus,
        "validations": validations,
        "limitations": [
            "LOCAL_SYNTHETIC",
            "COOPERATIVE_SAME_UID_PROCESS_BOUNDARY",
            "NO_REAL_PRINCIPAL_OR_LEGAL_AUTHORITY",
            "NO_REAL_CLM_OR_HUMAN_DECISION",
            "OPA_NOT_RUN",
            "CEDAR_NOT_RUN",
            "OPENFGA_NOT_RUN",
            "XACML_NOT_RUN",
            "LOCAL_REFERENCE_ENGINE_NOT_PRODUCT_EVIDENCE",
            "MIGRATION_EQUIVALENCE_WITNESSED_CORPUS_ONLY",
            "NO_CANONICAL_IR_CLAIM",
            "NO_STABLE_RESIDUAL_CLAIM",
        ],
    }


def build_manifest(results: dict) -> dict:
    source_paths = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and "artifacts/runtime" not in path.as_posix()
        and path.name != "results.json"
        and path.name != "manifest.json"
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )
    return {
        "schema": "mcb-g5-v2.run-manifest.v1",
        "result_status": results["status"],
        "result_canonical_sha256": sha256(results),
        "result_raw_sha256": sha256(
            (ROOT / "artifacts" / "results.json").read_bytes()
        ),
        "sources": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path.read_bytes()),
            }
            for path in source_paths
        ],
        "engine_truth": results["engine_status"],
        "formal_state_changes": [],
        "not_modified_by_design": [
            "research/NOW.md",
            "PROGRAM.md",
            "Problem",
            "LineContract",
            "MechanismProfile",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the discriminator's internal validations fail",
    )
    args = parser.parse_args()
    results = build_results()
    write_json(ROOT / "artifacts" / "results.json", results)
    write_json(ROOT / "artifacts" / "manifest.json", build_manifest(results))
    print(results["status"])
    print(ROOT / "artifacts" / "results.json")
    if args.check and results["status"] != "COMPLETE_LOCAL_SYNTHETIC_DISCRIMINATOR":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
