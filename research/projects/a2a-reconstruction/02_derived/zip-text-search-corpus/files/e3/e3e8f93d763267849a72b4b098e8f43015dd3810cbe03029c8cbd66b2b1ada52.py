from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDKIT_ROOT = HERE.parent / "towow_fieldkit"
sys.path.insert(0, str(FIELDKIT_ROOT))

from towow_fieldkit.schema_change import classify_change, compile_readiness  # noqa: E402
from towow_fieldkit.store import CaseStore, write_json  # noqa: E402


CASE_ROOT = HERE / "case"
EXPORT_ROOT = HERE / "redacted_export"


def schema_v1() -> dict:
    return {
        "schema_id": "enterprise-ai-readonly-pilot",
        "version": "1",
        "roles": {
            "buyer_business": {"label": "业务与采用权威"},
            "buyer_data": {"label": "数据与安全权威"},
            "provider_business": {"label": "服务商务权威"},
            "provider_tech": {"label": "技术执行权威"},
        },
        "object_types": {
            "source_data": {"sensitivity": "CONFIDENTIAL"},
            "pilot_output": {"sensitivity": "INTERNAL"},
        },
        "actions": {
            "propose_pilot": {"actor_roles": ["provider_business"], "material": True},
            "authorize_raw_export": {"actor_roles": ["buyer_data"], "material": True},
            "commit_budget": {"actor_roles": ["buyer_business"], "material": True},
            "run_probe": {"actor_roles": ["provider_tech"], "material": True, "produces_effect": True},
            "accept": {"actor_roles": ["buyer_business"], "material": True},
            "withdraw": {"actor_roles": ["buyer_business", "buyer_data", "provider_business"], "material": True},
        },
        "transitions": [
            {"from": "FORMING", "action": "propose_pilot", "to": "PROPOSED"},
            {"from": "PROPOSED", "action": "authorize_raw_export", "to": "DATA_AUTHORIZED"},
            {"from": "DATA_AUTHORIZED", "action": "commit_budget", "to": "COMMITTED"},
            {"from": "COMMITTED", "action": "run_probe", "to": "EFFECT_PENDING"},
            {"from": "EFFECT_PENDING", "action": "accept", "to": "ACCEPTED"},
            {"from": "PROPOSED", "action": "withdraw", "to": "WITHDRAWN"},
            {"from": "DATA_AUTHORIZED", "action": "withdraw", "to": "WITHDRAWN"},
            {"from": "COMMITTED", "action": "withdraw", "to": "WITHDRAWN"},
        ],
        "authority_rules": {
            "propose_pilot": ["provider_business"],
            "authorize_raw_export": ["buyer_data"],
            "commit_budget": ["buyer_business"],
            "run_probe": ["provider_tech"],
            "accept": ["buyer_business"],
            "withdraw": ["buyer_business", "buyer_data", "provider_business"],
        },
        "witness_rules": {
            "run_probe": {"source_role": "provider_tech", "evidence": "provider-run-log"}
        },
        "acceptance_rules": {
            "accept": {"required_roles": ["buyer_business"], "requires_effect": True}
        },
        "data_rules": {
            "source_data": {
                "mode": "raw_export",
                "purposes": ["pilot", "model_improvement"],
                "training": True,
                "retention_days": 90,
                "derivatives_may_leave_buyer_domain": True,
            },
            "pilot_output": {"ownership": ["provider_business"], "retention_days": 365},
        },
        "reopen_rules": [
            {"trigger": "data_incident", "affected": ["authorize_raw_export", "run_probe", "accept"]}
        ],
        "metadata": {"label": "Provider default proposal"},
    }


def schema_v2() -> dict:
    return {
        "schema_id": "enterprise-ai-readonly-pilot",
        "version": "2",
        "roles": {
            "buyer_business": {"label": "业务与采用权威"},
            "buyer_data": {"label": "数据与安全权威"},
            "provider_business": {"label": "服务商务权威"},
            "provider_tech": {"label": "技术执行权威"},
        },
        "object_types": {
            "source_data": {"sensitivity": "CONFIDENTIAL", "residency": "BUYER_DOMAIN"},
            "pilot_output": {"sensitivity": "INTERNAL", "contains_raw_rows": False},
            "probe_receipt": {"sensitivity": "INTERNAL"},
        },
        "actions": {
            "propose_pilot": {"actor_roles": ["provider_business"], "material": True},
            "authorize_readonly_probe": {"actor_roles": ["buyer_data"], "material": True},
            "commit_probe_budget": {"actor_roles": ["buyer_business"], "material": True},
            "run_buyer_controlled_probe": {"actor_roles": ["provider_tech"], "target_roles": ["buyer_data"], "material": True, "produces_effect": True},
            "review_output": {"actor_roles": ["buyer_business", "buyer_data"], "material": True},
            "accept_pilot_result": {"actor_roles": ["buyer_business"], "material": True},
            "reject_pilot_result": {"actor_roles": ["buyer_business", "buyer_data"], "material": True},
            "withdraw": {"actor_roles": ["buyer_business", "buyer_data", "provider_business"], "material": True},
        },
        "transitions": [
            {"from": "FORMING", "action": "propose_pilot", "to": "PROPOSED"},
            {"from": "PROPOSED", "action": "authorize_readonly_probe", "to": "PROBE_AUTHORIZED"},
            {"from": "PROBE_AUTHORIZED", "action": "commit_probe_budget", "to": "COMMITTED"},
            {"from": "COMMITTED", "action": "run_buyer_controlled_probe", "to": "EFFECT_PENDING"},
            {"from": "EFFECT_PENDING", "action": "review_output", "to": "REVIEWED"},
            {"from": "REVIEWED", "action": "accept_pilot_result", "to": "ACCEPTED"},
            {"from": "REVIEWED", "action": "reject_pilot_result", "to": "REJECTED"},
            {"from": "PROPOSED", "action": "withdraw", "to": "WITHDRAWN"},
            {"from": "PROBE_AUTHORIZED", "action": "withdraw", "to": "WITHDRAWN"},
            {"from": "COMMITTED", "action": "withdraw", "to": "WITHDRAWN"},
            {"from": "EFFECT_PENDING", "action": "withdraw", "to": "WITHDRAWN"},
        ],
        "authority_rules": {
            "propose_pilot": ["provider_business"],
            "authorize_readonly_probe": ["buyer_data"],
            "commit_probe_budget": ["buyer_business"],
            "run_buyer_controlled_probe": ["provider_tech", "buyer_data"],
            "review_output": ["buyer_business", "buyer_data"],
            "accept_pilot_result": ["buyer_business"],
            "reject_pilot_result": ["buyer_business", "buyer_data"],
            "withdraw": ["buyer_business", "buyer_data", "provider_business"],
        },
        "witness_rules": {
            "run_buyer_controlled_probe": {
                "source_role": "buyer_data",
                "evidence": ["buyer-audit-receipt", "output-hash", "provider-run-log"],
                "producer_self_report_sufficient": False,
            }
        },
        "acceptance_rules": {
            "accept_pilot_result": {
                "required_roles": ["buyer_business"],
                "requires_effect": True,
                "requires_data_gate_pass": True,
                "success_criteria": ["actionable_findings>=3", "raw_rows_exported=0"],
            },
            "reject_pilot_result": {"required_roles": ["buyer_business"], "requires_reason": True},
        },
        "data_rules": {
            "source_data": {
                "mode": "buyer_controlled_readonly_query",
                "purposes": ["pilot_evaluation"],
                "training": False,
                "retention_days": 0,
                "derivatives_may_leave_buyer_domain": False,
                "raw_rows_exported": False,
            },
            "pilot_output": {
                "ownership": ["buyer_business"],
                "provider_license": "evaluation-only",
                "retention_days": 14,
                "contains_raw_rows": False,
            },
            "probe_receipt": {"retention_days": 90, "purpose": "audit"},
        },
        "reopen_rules": [
            {"trigger": "data_rule_changed", "affected": ["authorize_readonly_probe", "run_buyer_controlled_probe", "review_output", "accept_pilot_result"]},
            {"trigger": "success_criteria_changed", "affected": ["review_output", "accept_pilot_result"]},
            {"trigger": "mandate_revoked", "affected": ["all_actions_under_mandate"]},
            {"trigger": "buyer_audit_receipt_missing", "affected": ["run_buyer_controlled_probe", "review_output", "accept_pilot_result"]},
        ],
        "metadata": {"label": "Buyer-controlled countercondition"},
    }


def intake(party: str) -> dict:
    base = {
        "participant_id": party,
        "prestate_frozen": True,
        "acceptable_outcomes": [],
        "unacceptable_outcomes": [],
        "hard_constraints": [],
        "soft_preferences": [],
        "unknowns_that_matter": [],
        "resources_actually_available": [],
        "shareable_projections": [],
        "private_facts_not_shareable": [],
        "walk_away_conditions": [],
    }
    values = {
        "buyer_business": {
            "acceptable_outcomes": ["14-day reversible pilot under CNY 12000", "at least 3 actionable support findings"],
            "hard_constraints": ["no production write access", "business owner keeps final adoption right"],
            "unknowns_that_matter": ["whether source data quality is sufficient"],
            "resources_actually_available": ["CNY 12000 probe budget", "one analyst for review"],
            "shareable_projections": ["budget ceiling", "success criteria"],
            "private_facts_not_shareable": ["internal strategic priority ranking"],
        },
        "buyer_data": {
            "acceptable_outcomes": ["buyer-controlled read-only query", "auditable receipt"],
            "unacceptable_outcomes": ["raw export", "training", "unbounded retention"],
            "hard_constraints": ["raw data stays in buyer domain", "no persistent provider memory"],
            "unknowns_that_matter": ["whether provider code can run in isolated sandbox"],
            "resources_actually_available": ["read-only sandbox", "security reviewer for 60 minutes"],
            "shareable_projections": ["data categories", "allowed query class"],
            "private_facts_not_shareable": ["exact security architecture"],
        },
        "provider_business": {
            "acceptable_outcomes": ["paid discovery", "referenceable aggregate results with separate permission"],
            "hard_constraints": ["scope capped at 14 days", "payment before productionization"],
            "unknowns_that_matter": ["whether buyer can provide usable access within 5 days"],
            "resources_actually_available": ["one technical lead", "fixed-price CNY 9800 pilot"],
            "shareable_projections": ["price", "staff availability", "deliverable structure"],
            "private_facts_not_shareable": ["internal margin"],
        },
        "provider_tech": {
            "acceptable_outcomes": ["read-only execution with schema-level access", "reproducible output hash"],
            "hard_constraints": ["no manual copy of raw rows", "sandbox must expose documented query interface"],
            "unknowns_that_matter": ["schema compatibility", "runtime limits"],
            "resources_actually_available": ["containerized probe", "audit logging"],
            "shareable_projections": ["required APIs", "runtime envelope"],
            "private_facts_not_shareable": ["proprietary ranking implementation"],
        },
    }
    base.update(values[party])
    return base


def mandate(party: str) -> dict:
    scopes = {
        "buyer_business": {
            "may_disclose": ["budget ceiling", "success criteria"],
            "may_ask": ["price", "timeline", "deliverables"],
            "may_reject": ["offers outside budget or no measurable output"],
            "may_conditionally_accept": ["pilot terms"],
            "may_commit": ["probe budget up to CNY 12000"],
            "may_execute": ["pay approved probe"],
            "financial_limit_cny": 12000,
        },
        "buyer_data": {
            "may_disclose": ["data categories", "allowed query interface"],
            "may_ask": ["execution mode", "retention", "training", "audit evidence"],
            "may_reject": ["raw export", "training", "provider-controlled persistent copy"],
            "may_conditionally_accept": ["buyer-controlled read-only probe"],
            "may_commit": ["sandbox access for approved probe"],
            "may_execute": ["create revocable read-only credential"],
            "data_resources": ["source_data"],
            "permitted_purposes": ["pilot_evaluation"],
            "forbidden_purposes": ["training", "general model improvement", "resale"],
            "retention_days": 0,
            "training_allowed": False,
        },
        "provider_business": {
            "may_disclose": ["price", "timeline", "service terms"],
            "may_ask": ["business goal", "decision deadline"],
            "may_reject": ["unpaid custom production work"],
            "may_conditionally_accept": ["fixed-scope pilot"],
            "may_commit": ["14-day pilot at CNY 9800"],
            "financial_limit_cny": 9800,
        },
        "provider_tech": {
            "may_disclose": ["technical prerequisites", "runtime envelope"],
            "may_ask": ["schema", "query interface", "sandbox limits"],
            "may_reject": ["unsupported environment"],
            "may_conditionally_accept": ["documented read-only sandbox"],
            "may_commit": ["containerized probe execution"],
            "may_execute": ["approved read-only probe only"],
            "data_resources": ["source_data"],
            "permitted_purposes": ["pilot_evaluation"],
            "forbidden_purposes": ["training", "copying raw rows"],
            "retention_days": 0,
            "training_allowed": False,
        },
    }
    return {
        "mandate_id": f"mandate-{party}-v1",
        "principal_ref": f"principal:{party}",
        "delegate_entity_ref": f"agent:{party}",
        "valid_from": "2026-07-26T00:00:00Z",
        "valid_until": "2026-08-31T23:59:59Z",
        "scope": scopes[party],
        "must_escalate": ["any term outside scope", "any irreversible action", "any change of objective owner"],
        "revocation_conditions": ["participant withdrawal", "material schema change outside current mandate", "security incident"],
        "status": "ACTIVE",
    }


def add_event(store: CaseStore, event_type: str, actor: str, version: int, authority: str | None, **payload) -> None:
    store.append_event(
        event_type=event_type,
        actor=actor,
        relation_version=version,
        authority_ref=authority,
        payload=payload,
    )


def main() -> None:
    for path in (CASE_ROOT, EXPORT_ROOT):
        if path.exists():
            shutil.rmtree(path)

    store = CaseStore.create(CASE_ROOT, "虚构示例：14 天企业 AI 只读试点", "case-readonly-pilot-demo")
    parties = {
        "buyer_business": ("采购方业务/预算权威", "org:buyer:business"),
        "buyer_data": ("采购方数据/安全权威", "org:buyer:data"),
        "provider_business": ("服务方商务权威", "org:provider:business"),
        "provider_tech": ("服务方技术执行权威", "org:provider:tech"),
    }
    for party, (label, root) in parties.items():
        store.add_party(party, label, root)
        store.set_private_intake(party, intake(party))
        store.issue_mandate(party, mandate(party))

    v1 = {
        "schema": schema_v1(),
        "instance": {
            "state": "FORMING",
            "task_family": "enterprise-ai-pilot",
            "time_horizon_days": 14,
            "risk_class": "MEDIUM",
            "active_roles": list(parties),
            "active_resources": ["source_data", "pilot_output"],
            "parameters": {"price_cny": 9800, "duration_days": 14},
            "required_stances": [],
            "obtained_stances": [],
            "required_mandates": [f"mandate-{p}-v1" for p in parties],
            "valid_mandates": [f"mandate-{p}-v1" for p in parties],
            "unresolved_material_counterexamples": ["buyer_data_refuses_raw_export"],
            "rollback_or_compensation_defined": False,
            "reopen_rules_defined": True,
        },
        "dependencies": {
            "raw_export": ["authorize_raw_export", "run_probe", "accept"],
            "training_permission": ["run_probe", "accept"],
        },
        "status": "FORMING",
    }
    store.add_relation_version(v1)
    add_event(store, "DISCOVERY_PROJECTION", "provider_business", 1, "mandate-provider_business-v1", claim="14-day AI pilot for customer-support analysis", human_minutes=8, sensitive_disclosure_units=1)
    add_event(store, "ASSERTION_MADE", "provider_tech", 1, "mandate-provider_tech-v1", claim="default implementation requires raw export and permits model improvement", evidence_refs=["provider-default-architecture"])
    add_event(store, "REFUSAL", "buyer_data", 1, "mandate-buyer_data-v1", disposition="REJECT", reason="raw export, training and 90-day retention violate data mandate", human_minutes=12, sensitive_disclosure_units=0)
    add_event(store, "COUNTERCONDITION", "buyer_data", 1, "mandate-buyer_data-v1", counterconditions=["buyer-controlled read-only sandbox", "no training", "no raw row export", "buyer audit receipt"], human_minutes=10)
    add_event(store, "PROBE_REQUESTED", "provider_tech", 1, "mandate-provider_tech-v1", claim="test whether container can run against documented read-only query interface", elapsed_seconds=300)
    add_event(store, "PROBE_RESULT", "buyer_data", 1, "mandate-buyer_data-v1", claim="sandbox supports required aggregate query class", evidence_refs=["sandbox-capability-receipt"], human_minutes=20, sensitive_disclosure_units=2, elapsed_seconds=900)
    add_event(store, "CAPABILITY_PATH_FORMED", "research_instrument", 1, None, claim="provider probe can run without raw export or persistent copy", causal_inputs=["buyer_data_refusal", "sandbox_probe", "provider_containerization"])

    change = classify_change(
        schema_v1(),
        schema_v2(),
        current_state="FORMING",
        active_resources=["source_data", "pilot_output"],
        active_roles=list(parties),
    )
    write_json(HERE / "change_report.json", change.to_dict())

    v2_state = {
        "state": "FORMING",
        "task_family": "enterprise-ai-pilot",
        "time_horizon_days": 14,
        "risk_class": "MEDIUM",
        "active_roles": list(parties),
        "active_resources": ["source_data", "pilot_output", "probe_receipt"],
        "parameters": {"price_cny": 9800, "duration_days": 14, "query_limit": 500},
        "required_stances": [
            "buyer_business:COMMIT",
            "buyer_data:CONDITIONAL",
            "provider_business:COMMIT",
            "provider_tech:COMMIT",
        ],
        "obtained_stances": [
            "buyer_business:COMMIT",
            "buyer_data:CONDITIONAL",
            "provider_business:COMMIT",
            "provider_tech:COMMIT",
        ],
        "required_mandates": [f"mandate-{p}-v1" for p in parties],
        "valid_mandates": [f"mandate-{p}-v1" for p in parties],
        "unresolved_material_counterexamples": [],
        "rollback_or_compensation_defined": True,
        "reopen_rules_defined": True,
    }
    v2 = {
        "schema": schema_v2(),
        "instance": v2_state,
        "dependencies": {
            "data_mode": ["authorize_readonly_probe", "run_buyer_controlled_probe", "review_output", "accept_pilot_result"],
            "success_criteria": ["review_output", "accept_pilot_result"],
            "budget": ["commit_probe_budget", "run_buyer_controlled_probe"],
            "provider_runtime": ["run_buyer_controlled_probe"],
        },
        "supersedes_version": 1,
        "change_classification": change.classification,
        "status": "QUALIFIED",
    }
    store.add_relation_version(v2)
    add_event(store, "STANCE_RECORDED", "buyer_business", 2, "mandate-buyer_business-v1", object_ref="relation:v2", disposition="COMMIT", explainback="I approve a CNY 9800 reversible probe; this is not production adoption.", human_minutes=7)
    add_event(store, "STANCE_RECORDED", "buyer_data", 2, "mandate-buyer_data-v1", object_ref="relation:v2", disposition="CONDITIONAL", counterconditions=["no training", "no raw export", "buyer receipt required"], explainback="I authorize only the buyer-controlled read-only mode.", human_minutes=9)
    add_event(store, "STANCE_RECORDED", "provider_business", 2, "mandate-provider_business-v1", object_ref="relation:v2", disposition="COMMIT", explainback="Provider commits to fixed scope and price; production work is excluded.", human_minutes=5)
    add_event(store, "STANCE_RECORDED", "provider_tech", 2, "mandate-provider_tech-v1", object_ref="relation:v2", disposition="COMMIT", explainback="Execution is limited to the approved container and query class.", human_minutes=6)
    add_event(store, "COMMITMENT_RECORDED", "buyer_business", 2, "mandate-buyer_business-v1", claim="CNY 9800 probe budget reserved", evidence_refs=["budget-reservation-demo"])
    add_event(store, "PROBE_AUTHORIZED", "buyer_data", 2, "mandate-buyer_data-v1", claim="revocable read-only credential issued", evidence_refs=["credential-receipt-demo"])

    compile_report = compile_readiness(schema_v2(), v2_state)
    write_json(HERE / "compile_readiness.json", compile_report)

    add_event(store, "OPERATION_ATTEMPT", "provider_tech", 2, "mandate-provider_tech-v1", operation="run_buyer_controlled_probe", elapsed_seconds=1440)
    add_event(store, "EFFECT_WITNESSED", "buyer_data", 2, "mandate-buyer_data-v1", claim="probe executed in buyer sandbox; raw_rows_exported=0; training_updates=0", evidence_refs=["buyer-audit-receipt-demo", "output-hash-demo"], sensitive_disclosure_units=3)
    add_event(store, "ADOPTION_RECORDED", "buyer_business", 2, "mandate-buyer_business-v1", claim="three findings entered into buyer support backlog", evidence_refs=["backlog-items-demo"], disposition="CONDITIONAL", human_minutes=18)
    add_event(store, "ACCEPTANCE_STANCE", "buyer_business", 2, "mandate-buyer_business-v1", disposition="CONDITIONAL", claim="pilot accepted for evaluation; production rollout not accepted", reasons=["success criteria met", "long-term ROI unknown"], human_minutes=10)
    add_event(store, "FOLLOWUP", "buyer_business", 2, "mandate-buyer_business-v1", day=14, disposition="CONDITIONAL", real_effect_still_holds=True, new_defeaters=["production integration cost unknown"], regret_0_to_10=1)

    store.record_adjudication(
        {
            "adjudicator_id": "demo-adjudicator-1",
            "blinded_condition": "TOWOW_FORMATION",
            "case_version_reviewed": 2,
            "stable_disposition": "CONDITIONAL",
            "disposition_correct_at_followup": True,
            "false_commit": False,
            "missed_feasible_relation": False,
            "strict_formation_observed": True,
            "formation_counterfactual_basis": [
                "v1 feasible path required raw export and was refused",
                "v2 buyer-controlled path appeared only after refusal, countercondition and sandbox probe",
                "v2 produced a target-domain effect and adoption record",
            ],
            "authority_integrity": "PASS_WITH_SCOPE",
            "effect_witness_quality": "MULTI_SOURCE",
            "principal_explainback_passed": True,
            "third_party_or_externality_issue": False,
            "confidence": 0.82,
            "reasons": [
                "The demo contains an explicit material schema change and scoped mandates.",
                "This is a synthetic illustration; the strict-formation label is not empirical evidence.",
            ],
            "evidence_refs": ["relation:v1", "relation:v2", "buyer-audit-receipt-demo"],
        }
    )

    write_json(HERE / "validation.json", store.validate())
    write_json(HERE / "metrics.json", store.metrics())
    store.export_redacted(EXPORT_ROOT)

    summary = {
        "case": "case/",
        "redacted_export": "redacted_export/",
        "change_classification": change.classification,
        "compile_ready": compile_report["ready"],
        "validation": store.validate(),
        "metrics": store.metrics(),
        "warning": "All actors, organizations and evidence references in this sample are fictional. This is not a real-principal result.",
    }
    write_json(HERE / "sample_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
