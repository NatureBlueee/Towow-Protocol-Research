#!/usr/bin/env python3
"""Build ex-post Fieldkit reconstructions for three public archival cases.

The generated cases are structural encodings of public records, not counterfactual
claims that Towow or an Agent caused the historical outcomes.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIELDKIT_ROOT = ROOT / "instrument" / "towow_fieldkit"
sys.path.insert(0, str(FIELDKIT_ROOT))

from towow_fieldkit.schema_change import classify_change, compile_readiness  # noqa: E402
from towow_fieldkit.store import CaseStore, read_json, write_json  # noqa: E402

GENERATED = HERE / "generated"


def base_schema(schema_id: str) -> dict[str, Any]:
    return {
        "schema_id": schema_id,
        "version": "1",
        "roles": {},
        "object_types": {},
        "actions": {},
        "transitions": [],
        "authority_rules": {},
        "witness_rules": {},
        "acceptance_rules": {},
        "data_rules": {},
        "standing_rules": {},
        "jurisdiction_rules": {},
        "challenge_rules": {},
        "settlement_rules": {},
        "metadata": {
            "archival_reconstruction": True,
            "no_causal_claim": True,
            "source_observability": "public formal record only",
        },
    }


def activision_versions() -> list[tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]]:
    v1 = base_schema("shadow-activision")
    v1.update({
        "version": "1",
        "roles": {"microsoft": {}, "activision": {}, "cma": {"external_jurisdiction": True}},
        "object_types": {"full_acquisition": {}, "cloud_streaming_rights": {}},
        "actions": {
            "propose_original": {"actor_roles": ["microsoft", "activision"], "material": True},
            "review_original": {"actor_roles": ["cma"], "material": True},
            "close_original": {"actor_roles": ["microsoft", "activision"], "material": True, "produces_effect": True},
        },
        "transitions": [
            {"from": "PROPOSED", "action": "review_original", "to": "PROHIBITED"},
            {"from": "PROPOSED", "action": "close_original", "to": "EFFECT_PENDING"},
        ],
        "authority_rules": {
            "propose_original": ["microsoft", "activision"],
            "review_original": ["cma"],
            "close_original": ["microsoft", "activision"],
        },
        "witness_rules": {"close_original": {"source": "closing_authorities"}},
        "acceptance_rules": {"original_deal": {"required_roles": ["microsoft", "activision", "cma"]}},
        "data_rules": {"cloud_streaming_rights": {"holder": "microsoft_after_close", "scope": "full"}},
        "standing_rules": {"competition_challenge": ["cma"]},
        "jurisdiction_rules": {"UK_competition": {"required": True, "authority": "cma"}},
        "challenge_rules": {"original_transaction": {"status": "PROHIBITED", "reopen": "new_transaction_only"}},
        "settlement_rules": {"original_transaction": {"requires": ["UK_competition_clearance"]}},
    })
    s1 = {
        "state": "PROHIBITED",
        "required_stances": ["microsoft", "activision", "cma"],
        "obtained_stances": ["microsoft", "activision", "cma"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": ["UK_cloud_gaming_competition_concern"],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": False,
        "required_jurisdictions": ["UK_competition"],
        "covered_jurisdictions": [],
        "required_external_standing": ["cma"],
        "reviewed_external_standing": ["cma"],
        "open_material_challenges": ["CMA_prohibition"],
        "challenge_contingency_defined": False,
        "challenge_horizon": "original_transaction_prohibited",
    }
    e1 = [
        {"type": "EXTERNAL_CHALLENGE_DECIDED", "actor": "cma", "payload": {"disposition": "PROHIBITED", "source_refs": ["AC-CMA-ACTIVISION-ORIGINAL"]}},
    ]

    v2 = json.loads(json.dumps(v1))
    v2.update({
        "version": "2",
        "roles": {"microsoft": {}, "activision": {}, "cma": {"external_jurisdiction": True}, "ubisoft": {"rights_holder": True}},
        "object_types": {"restructured_acquisition": {}, "non_EEA_cloud_streaming_rights": {}, "licence_back": {}},
        "actions": {
            "transfer_streaming_rights": {"actor_roles": ["activision", "ubisoft"], "material": True, "produces_effect": True},
            "review_restructured": {"actor_roles": ["cma"], "material": True},
            "accept_undertakings": {"actor_roles": ["cma", "microsoft", "activision"], "material": True},
            "close_restructured": {"actor_roles": ["microsoft", "activision"], "material": True, "produces_effect": True},
        },
        "transitions": [
            {"from": "RESTRUCTURED", "action": "transfer_streaming_rights", "to": "RIGHTS_TRANSFERRED"},
            {"from": "RIGHTS_TRANSFERRED", "action": "review_restructured", "to": "REVIEWED"},
            {"from": "REVIEWED", "action": "accept_undertakings", "to": "CLEARED"},
            {"from": "CLEARED", "action": "close_restructured", "to": "EFFECT_PENDING"},
        ],
        "authority_rules": {
            "transfer_streaming_rights": ["activision", "ubisoft"],
            "review_restructured": ["cma"],
            "accept_undertakings": ["cma", "microsoft", "activision"],
            "close_restructured": ["microsoft", "activision"],
        },
        "witness_rules": {
            "transfer_streaming_rights": {"source": "rights_transfer_instruments"},
            "close_restructured": {"source": "closing_authorities"},
        },
        "acceptance_rules": {"restructured_deal": {"required_roles": ["microsoft", "activision", "cma", "ubisoft"]}},
        "data_rules": {
            "non_EEA_cloud_streaming_rights": {"holder": "ubisoft", "scope": "exclusive_worldwide_outside_EEA", "duration": "defined_in_transaction"},
            "licence_back": {"holder": "ubisoft", "licensee": "microsoft", "limits": "undertakings_and_transaction_terms"},
        },
        "standing_rules": {"competition_challenge": ["cma"]},
        "jurisdiction_rules": {"UK_competition": {"required": True, "authority": "cma", "clearance": "restructured_scope_only"}},
        "challenge_rules": {"restructured_transaction": {"status": "CLEARED_WITH_UNDERTAKINGS", "reopen": "undertaking_breach_or_new_defeater"}},
        "settlement_rules": {"restructured_transaction": {"scope": "restructured_rights_configuration", "requires": ["rights_transfer", "UK_competition_clearance", "closing_effect"]}},
    })
    s2 = {
        "state": "RESTRUCTURED",
        "required_stances": ["microsoft", "activision", "cma", "ubisoft"],
        "obtained_stances": ["microsoft", "activision", "cma", "ubisoft"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": [],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": True,
        "required_jurisdictions": ["UK_competition"],
        "covered_jurisdictions": ["UK_competition"],
        "required_external_standing": ["cma"],
        "reviewed_external_standing": ["cma"],
        "open_material_challenges": [],
        "challenge_contingency_defined": True,
        "challenge_horizon": "through_clearance_and_observed_closing",
    }
    e2 = [
        {"type": "COUNTERCONDITION_FORMED", "actor": "microsoft_activision", "payload": {"change": "divest_non_EEA_cloud_streaming_rights_to_ubisoft", "source_refs": ["AC-CMA-ACTIVISION-RESTRUCTURED"]}},
        {"type": "EXTERNAL_CLEARANCE_RECORDED", "actor": "cma", "payload": {"scope": "restructured_transaction", "source_refs": ["AC-CMA-ACTIVISION-RESTRUCTURED"]}},
    ]
    return [(v1, s1, e1), (v2, s2, e2)]


def giphy_versions() -> list[tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]]:
    v1 = base_schema("shadow-giphy")
    v1.update({
        "version": "1",
        "roles": {"meta": {}, "giphy": {}, "cma": {"external_jurisdiction": True}, "third_parties": {"affected_standing": True}},
        "object_types": {"ownership": {}, "giphy_data": {}, "advertising_services": {}},
        "actions": {
            "close_bilateral": {"actor_roles": ["meta", "giphy"], "material": True, "produces_effect": True},
        },
        "transitions": [{"from": "COMMITTED", "action": "close_bilateral", "to": "EFFECT_OCCURRED"}],
        "authority_rules": {"close_bilateral": ["meta", "giphy"]},
        "witness_rules": {"close_bilateral": {"source": "corporate_closing_record"}},
        "acceptance_rules": {"bilateral": {"required_roles": ["meta", "giphy"]}},
        "data_rules": {"giphy_data": {"holder": "meta_after_close", "derived_signal_risk": "unreviewed"}},
        "standing_rules": {"competition_challenge": ["cma", "third_parties"]},
        "jurisdiction_rules": {"UK_competition": {"required": True, "authority": "cma"}},
        "challenge_rules": {"post_close_review": {"status": "OPEN"}},
        "settlement_rules": {"bilateral": {"scope": "corporate_effect_only", "excludes": ["UK_competition_clearance"]}},
    })
    s1 = {
        "state": "COMMITTED",
        "required_stances": ["meta", "giphy"], "obtained_stances": ["meta", "giphy"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": [],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": False,
        "required_jurisdictions": ["UK_competition"], "covered_jurisdictions": [],
        "required_external_standing": ["cma", "third_parties"], "reviewed_external_standing": [],
        "open_material_challenges": ["CMA_post_close_review"],
        "challenge_contingency_defined": False,
        "challenge_horizon": "post_close_review_open",
    }
    e1 = [{"type": "EFFECT_WITNESSED", "actor": "closing_authorities", "payload": {"effect": "ownership_changed", "settlement_scope": "bilateral_only", "source_refs": ["AC-CMA-GIPHY"]}}]

    v2 = json.loads(json.dumps(v1))
    v2.update({
        "version": "2",
        "actions": {
            "submit_third_party_evidence": {"actor_roles": ["third_parties"], "material": True},
            "adjudicate_competition": {"actor_roles": ["cma"], "material": True},
            "order_divestiture": {"actor_roles": ["cma"], "material": True},
        },
        "transitions": [
            {"from": "EFFECT_OCCURRED", "action": "submit_third_party_evidence", "to": "CHALLENGED"},
            {"from": "CHALLENGED", "action": "adjudicate_competition", "to": "PROHIBITED"},
            {"from": "PROHIBITED", "action": "order_divestiture", "to": "DIVEST_REQUIRED"},
        ],
        "authority_rules": {
            "submit_third_party_evidence": ["third_parties"],
            "adjudicate_competition": ["cma"],
            "order_divestiture": ["cma"],
        },
        "witness_rules": {},
        "acceptance_rules": {"remedy": {"required_roles": ["cma"]}},
        "data_rules": {"giphy_data": {"holder": "meta", "derived_signal_risk": "material_competition_evidence"}},
        "standing_rules": {"competition_challenge": ["cma", "third_parties"]},
        "jurisdiction_rules": {"UK_competition": {"required": True, "authority": "cma", "disposition": "DIVEST_REQUIRED"}},
        "challenge_rules": {"post_close_review": {"status": "DECIDED", "remedy": "DIVESTITURE"}},
        "settlement_rules": {"transaction": {"status": "NOT_SETTLED_IN_UK_COMPETITION_SCOPE"}},
    })
    s2 = {
        "state": "EFFECT_OCCURRED",
        "required_stances": ["cma"], "obtained_stances": ["cma"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": ["competition_harm_and_data_signal_risk"],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": True,
        "required_jurisdictions": ["UK_competition"], "covered_jurisdictions": ["UK_competition"],
        "required_external_standing": ["cma", "third_parties"], "reviewed_external_standing": ["cma", "third_parties"],
        "open_material_challenges": ["divestiture_not_yet_effected"],
        "challenge_contingency_defined": True,
        "challenge_horizon": "until_divestiture_effect",
    }
    e2 = [
        {"type": "EXTERNAL_CHALLENGE_UPHELD", "actor": "cma", "payload": {"remedy": "DIVESTITURE", "source_refs": ["AC-CMA-GIPHY"]}},
        {"type": "DERIVED_DATA_RISK_ASSERTED", "actor": "third_parties", "payload": {"risk": "aggregate_usage_and_search_signals", "epistemic_status": "reported_in_inquiry", "source_refs": ["AC-CMA-GIPHY"]}},
    ]

    v3 = json.loads(json.dumps(v2))
    v3.update({
        "version": "3",
        "roles": {"meta": {}, "giphy": {}, "purchaser": {}, "cma": {"external_jurisdiction": True}, "third_parties": {"affected_standing": True}},
        "actions": {
            "sell_giphy": {"actor_roles": ["meta", "purchaser"], "material": True, "produces_effect": True},
            "close_case": {"actor_roles": ["cma"], "material": True},
        },
        "transitions": [
            {"from": "DIVEST_REQUIRED", "action": "sell_giphy", "to": "DIVESTED"},
            {"from": "DIVESTED", "action": "close_case", "to": "SCOPED_SETTLED"},
        ],
        "authority_rules": {"sell_giphy": ["meta", "purchaser"], "close_case": ["cma"]},
        "witness_rules": {"sell_giphy": {"source": "divestiture_closing_record"}},
        "acceptance_rules": {"remedy_completion": {"required_roles": ["cma"]}},
        "data_rules": {"giphy_data": {"holder": "purchaser_after_sale", "scope": "observed_divestiture"}},
        "challenge_rules": {"post_close_review": {"status": "CLOSED_WITHIN_OBSERVED_SCOPE", "reopen": "new_defeater_or_noncompliance"}},
        "settlement_rules": {"remedy": {"scope": "UK_competition_case_through_divestiture", "requires": ["divestiture_effect", "CMA_case_closure"]}},
    })
    s3 = {
        "state": "DIVEST_REQUIRED",
        "required_stances": ["meta", "purchaser", "cma"], "obtained_stances": ["meta", "purchaser", "cma"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": [],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": True,
        "required_jurisdictions": ["UK_competition"], "covered_jurisdictions": ["UK_competition"],
        "required_external_standing": ["cma", "third_parties"], "reviewed_external_standing": ["cma", "third_parties"],
        "open_material_challenges": [],
        "challenge_contingency_defined": True,
        "challenge_horizon": "through_observed_divestiture_and_case_closure",
    }
    e3 = [{"type": "DIVESTITURE_EFFECT_WITNESSED", "actor": "divestiture_closing_authorities", "payload": {"effect": "ownership_separated", "source_refs": ["AC-CMA-GIPHY"]}}]
    return [(v1, s1, e1), (v2, s2, e2), (v3, s3, e3)]


def deloitte_versions() -> list[tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]]:
    v1 = base_schema("shadow-deloitte")
    v1.update({
        "version": "1",
        "roles": {"deloitte": {}, "teaming_partner": {}, "agency": {}, "gao": {"adjudicator": True}},
        "object_types": {"proposal": {}, "team_capability": {}, "award": {}},
        "actions": {
            "submit_proposal": {"actor_roles": ["deloitte", "teaming_partner"], "material": True},
            "evaluate_capability": {"actor_roles": ["agency"], "material": True},
            "make_award": {"actor_roles": ["agency"], "material": True, "produces_effect": True},
        },
        "transitions": [
            {"from": "DRAFT", "action": "submit_proposal", "to": "SUBMITTED"},
            {"from": "SUBMITTED", "action": "evaluate_capability", "to": "EVALUATED"},
            {"from": "EVALUATED", "action": "make_award", "to": "AWARDED"},
        ],
        "authority_rules": {"submit_proposal": ["deloitte", "teaming_partner"], "evaluate_capability": ["agency"], "make_award": ["agency"]},
        "witness_rules": {"make_award": {"source": "agency_award_record"}},
        "acceptance_rules": {"award": {"required_roles": ["agency"]}},
        "standing_rules": {"bid_protest": ["eligible_protester", "gao"]},
        "jurisdiction_rules": {"GAO_protest": {"authority": "gao", "required_if_challenged": True}},
        "challenge_rules": {"award": {"status": "challengeable"}},
        "settlement_rules": {"award": {"requires": ["contemporaneous_capability_evaluation", "no_sustained_material_protest"]}},
    })
    s1 = {
        "state": "SUBMITTED",
        "required_stances": ["agency"], "obtained_stances": ["agency"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": [],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": True,
        "required_jurisdictions": [], "covered_jurisdictions": [],
        "required_external_standing": [], "reviewed_external_standing": [],
        "open_material_challenges": [],
        "challenge_contingency_defined": True,
        "challenge_horizon": "through_award_and_protest_window",
    }
    e1 = [{"type": "CAPABILITY_ASSERTION_QUALIFIED", "actor": "agency", "payload": {"dependency": "deloitte_plus_teaming_partner", "source_refs": ["AC-GAO-DELOITTE"]}}]

    v2 = json.loads(json.dumps(v1))
    v2.update({
        "version": "2",
        "roles": {"deloitte": {}, "agency": {}, "gao": {"adjudicator": True}},
        "actions": {
            "notify_team_change": {"actor_roles": ["deloitte"], "material": True},
            "reevaluate_capability": {"actor_roles": ["agency"], "material": True},
            "adjudicate_protest": {"actor_roles": ["gao"], "material": True},
        },
        "transitions": [
            {"from": "AWARDED", "action": "notify_team_change", "to": "CAPABILITY_CHANGED"},
            {"from": "CAPABILITY_CHANGED", "action": "reevaluate_capability", "to": "REEVALUATED"},
            {"from": "CAPABILITY_CHANGED", "action": "adjudicate_protest", "to": "CHALLENGED"},
        ],
        "authority_rules": {"notify_team_change": ["deloitte"], "reevaluate_capability": ["agency"], "adjudicate_protest": ["gao"]},
        "witness_rules": {},
        "acceptance_rules": {"continued_awardability": {"required_roles": ["agency"]}},
        "standing_rules": {"bid_protest": ["eligible_protester", "gao"]},
        "jurisdiction_rules": {"GAO_protest": {"authority": "gao", "required": True}},
        "challenge_rules": {"award": {"status": "SUSTAINED", "required_action": "reevaluation"}},
        "settlement_rules": {"award": {"status": "NOT_SETTLED_UNTIL_REEVALUATION"}},
    })
    s2 = {
        "state": "AWARDED",
        "required_stances": ["agency", "gao"], "obtained_stances": ["gao"],
        "required_mandates": [], "valid_mandates": [],
        "unresolved_material_counterexamples": ["teaming_partner_removed_and_capability_not_reevaluated"],
        "reopen_rules_defined": True,
        "rollback_or_compensation_defined": True,
        "required_jurisdictions": ["GAO_protest"], "covered_jurisdictions": ["GAO_protest"],
        "required_external_standing": ["gao"], "reviewed_external_standing": ["gao"],
        "open_material_challenges": ["sustained_protest_and_reevaluation_pending"],
        "challenge_contingency_defined": True,
        "challenge_horizon": "until_reasonable_reevaluation",
    }
    e2 = [
        {"type": "CAPABILITY_DEPENDENCY_REMOVED", "actor": "deloitte", "payload": {"removed_role": "teaming_partner", "source_refs": ["AC-GAO-DELOITTE"]}},
        {"type": "EXTERNAL_CHALLENGE_UPHELD", "actor": "gao", "payload": {"reason": "agency_did_not_reasonably_consider_material_team_change", "source_refs": ["AC-GAO-DELOITTE"]}},
    ]
    return [(v1, s1, e1), (v2, s2, e2)]


BUILDERS = {
    "SHADOW-ACTIVISION": activision_versions,
    "SHADOW-GIPHY": giphy_versions,
    "SHADOW-DELOITTE": deloitte_versions,
}

AUTHORITY_ROOTS = {
    "SHADOW-ACTIVISION": [
        ("microsoft", "Microsoft transaction authority", "org:microsoft:transaction"),
        ("activision", "Activision transaction authority", "org:activision:transaction"),
        ("cma", "UK competition jurisdiction", "institution:cma"),
        ("ubisoft", "Ubisoft rights-holder authority", "org:ubisoft:rights"),
    ],
    "SHADOW-GIPHY": [
        ("meta", "Meta bilateral authority", "org:meta:transaction"),
        ("giphy", "Giphy bilateral authority", "org:giphy:transaction"),
        ("cma", "UK competition jurisdiction", "institution:cma"),
        ("third_parties", "Affected-interest evidence locus", "affected:third_parties"),
        ("purchaser", "Divestiture purchaser authority", "org:purchaser:transaction"),
    ],
    "SHADOW-DELOITTE": [
        ("deloitte", "Offeror authority", "org:deloitte:proposal"),
        ("teaming_partner", "Teaming partner capability locus", "org:partner:capability"),
        ("agency", "Evaluation and award authority", "institution:agency"),
        ("gao", "Bid protest adjudication", "institution:gao"),
    ],
}


def build_one(shadow: dict[str, Any]) -> dict[str, Any]:
    shadow_id = shadow["shadow_id"]
    out = GENERATED / shadow_id
    if out.exists():
        shutil.rmtree(out)
    store = CaseStore.create(out, f"{shadow_id} public archival reconstruction", shadow_id)
    for pid, label, root in AUTHORITY_ROOTS[shadow_id]:
        store.add_party(pid, label, root)

    versions = BUILDERS[shadow_id]()
    transition_reports: list[dict[str, Any]] = []
    readiness_reports: list[dict[str, Any]] = []
    previous_schema: dict[str, Any] | None = None

    for idx, (schema, state, events) in enumerate(versions, start=1):
        relation = {
            "version": idx,
            "status": state["state"],
            "schema": schema,
            "instance": {
                "state": state["state"],
                "archival_case_id": shadow["case_id"],
                "qualified_revision": shadow["relation_versions"][idx - 1]["qualified_revision"],
                "source_basis": "public formal archive",
                "no_causal_claim": True,
            },
            "research_metadata": {
                "reconstruction": "ex_post_structural_recoding",
                "unobservable": shadow["unobservable"],
                "required_fieldkit_features": shadow["required_fieldkit_features"],
            },
        }
        store.add_relation_version(relation)
        for item in events:
            store.append_event(
                event_type=item["type"], actor=item["actor"], payload=item["payload"], relation_version=idx
            )
        readiness = compile_readiness(schema, state, current_state=state["state"])
        readiness["relation_version"] = idx
        readiness_reports.append(readiness)
        if previous_schema is not None:
            report = classify_change(
                previous_schema,
                schema,
                current_state=versions[idx - 2][1]["state"],
                active_resources=list(previous_schema.get("object_types", {}).keys()),
                active_roles=list(previous_schema.get("roles", {}).keys()),
            ).to_dict()
            report.update({"from_version": idx - 1, "to_version": idx})
            transition_reports.append(report)
        previous_schema = schema

    validation = store.validate()
    write_json(out / "outputs" / "shadow_readiness.json", {"reports": readiness_reports})
    write_json(out / "outputs" / "shadow_change_reports.json", {"reports": transition_reports})
    write_json(out / "outputs" / "shadow_validation.json", validation)

    return {
        "shadow_id": shadow_id,
        "case_id": shadow["case_id"],
        "valid": validation["valid"],
        "relation_version_count": len(versions),
        "event_count": validation["event_count"],
        "change_classifications": [x["classification"] for x in transition_reports],
        "readiness": [x["readiness"] for x in readiness_reports],
        "no_causal_claim": True,
    }


def main() -> int:
    spec = json.loads((HERE / "shadow_cases.json").read_text(encoding="utf-8"))
    GENERATED.mkdir(parents=True, exist_ok=True)
    results = [build_one(case) for case in spec["cases"]]
    report = {
        "version": "0.5",
        "method": "ex-post public archival reconstruction into Towow Fieldkit",
        "case_count": len(results),
        "all_valid": all(x["valid"] for x in results),
        "all_transitions_material": all(
            all(c == "MATERIAL_SCHEMA_CHANGE" for c in x["change_classifications"]) for x in results
        ),
        "cases": results,
        "interpretation": "Structural expressivity test only; no claim that Towow or an Agent caused or would improve the historical outcomes.",
    }
    write_json(HERE / "results.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["all_valid"] and report["all_transitions_material"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
