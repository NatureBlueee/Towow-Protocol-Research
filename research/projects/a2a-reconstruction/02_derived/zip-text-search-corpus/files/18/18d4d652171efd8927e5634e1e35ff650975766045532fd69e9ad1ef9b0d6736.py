#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
PKG=HERE.parents[1]/'instrument'/'opc_fieldkit_v0.7'
sys.path.insert(0,str(PKG))

from towow_fieldkit.opc import CoordinationContext, CoordinationMode
from towow_fieldkit.router import route_coordination


def expected_policy(expected: list[str]) -> str:
    if ('HUMAN_BROKER' in expected and len(expected)>1) or ('DETERMINISTIC_SERVICE' in expected and any(x in expected for x in ('BILATERAL_FORMATION','TEMPORARY_COALITION'))):
        return 'ALL'
    return 'ANY'


def modes_ok(pred: list[str], expected: list[str]) -> bool:
    policy=expected_policy(expected)
    return set(expected).issubset(pred) if policy=='ALL' else bool(set(expected)&set(pred))


def required_invariants(c: CoordinationContext) -> dict[str,bool]:
    return {
        'schema_fidelity': c.schema_completeness < .80,
        'local_authority': c.authority_plurality > 1 or c.human_acceptance_required,
        'minimal_disclosure': c.private_context_intensity >= .50 and not c.centralizable_within_grants,
        'affected_party_standing': c.externality_risk >= .35,
        'reversibility_guard': c.irreversibility >= .50 and c.schema_completeness < .80,
        'local_reopen': c.volatility >= .50 or c.repeated_relation,
        'resource_reservation': c.capacity_pressure >= .65 or c.participants > 2 or c.repeated_relation,
        'effect_acceptance_separation': c.participants > 1 or c.human_acceptance_required,
        'recourse': c.dispute_active or c.externality_risk >= .35,
    }

CONTROL_MAP={
 'schema_fidelity': {'versioned relation schema','versioned operation specification','countercondition and refusal'},
 'local_authority': {'scoped mandate','acceptance gate','do not mutate local authority'},
 'minimal_disclosure': {'minimal disclosure / local oracle'},
 'affected_party_standing': {'affected-party standing and recourse'},
 'reversibility_guard': {'staged probe before irreversible effect','freeze irreversible operations','provisional remedy / staged evidence review'},
 'local_reopen': {'local reopen','defeater-triggered local reopen','reopen trigger'},
 'resource_reservation': {'resource reservation'},
 'effect_acceptance_separation': {'effect/acceptance separation','acceptance gate','target-world effect witness'},
 'recourse': {'affected-party standing and recourse','record standing and remedy scope'},
}


def fixed_platform(c: CoordinationContext) -> dict[str,Any]:
    if c.marketplace_available:
        modes=['PLATFORM_MARKET']
    elif c.deterministic_interface_available:
        modes=['DETERMINISTIC_SERVICE']
    elif c.optimization_problem:
        modes=['CENTRAL_OPTIMIZER']
    else:
        modes=['PLATFORM_MARKET']
    controls={'effect/acceptance separation'} if c.platform_frame_sufficient else set()
    if c.platform_frame_sufficient:
        controls|={'reopen trigger'}
    return {'modes':modes,'controls':controls,'overhead':1.0}


def central_agent(c: CoordinationContext) -> dict[str,Any]:
    modes=['CENTRAL_OPTIMIZER']
    controls={'return ranked candidates with evidence'}
    if c.evidence_burden>=.7:
        controls.add('target-world effect witness')
    if c.irreversibility>=.7:
        controls.add('staged probe before irreversible effect')
    return {'modes':modes,'controls':controls,'overhead':2.0}


def portfolio(c: CoordinationContext) -> dict[str,Any]:
    decision=route_coordination(c)
    modes=[s.mode.value for s in decision.steps]
    controls=set(x for s in decision.steps for x in s.mandatory_controls)
    return {'modes':modes,'controls':controls,'overhead':len(decision.steps)+.12*len(controls),'decision':decision.to_dict()}


def evaluate(system: str, outcome: dict[str,Any], c: CoordinationContext, fixture: dict[str,Any]) -> dict[str,Any]:
    inv=required_invariants(c)
    missing=[]
    for name,needed in inv.items():
        if not needed: continue
        if not (CONTROL_MAP[name]&set(outcome['controls'])):
            missing.append(name)
    mode_match=modes_ok(outcome['modes'],fixture['acceptable_modes'])
    return {
        'system':system,
        'modes':outcome['modes'],
        'controls':sorted(outcome['controls']),
        'mode_match':mode_match,
        'mode_policy':expected_policy(fixture['acceptable_modes']),
        'missing_invariants':missing,
        'invariant_coverage': 1-len(missing)/max(1,sum(inv.values())),
        'structurally_valid': mode_match and not missing,
        'overhead_units':outcome['overhead'],
        'decision':outcome.get('decision'),
    }


def main():
    payload=json.loads((HERE/'fixtures.json').read_text(encoding='utf-8'))
    rows=[]
    systems={'fixed_platform':fixed_platform,'single_global_agent':central_agent,'portfolio_router':portfolio}
    for fixture in payload['cases']:
        c=CoordinationContext(**fixture['context'])
        for name,fn in systems.items():
            out=fn(c)
            ev=evaluate(name,out,c,fixture)
            ev.update({'case_id':fixture['id'],'title':fixture['title'],'expected_modes':fixture['acceptable_modes'],'required_controls':fixture['required_controls']})
            rows.append(ev)
    summary={}
    for name in systems:
        sub=[r for r in rows if r['system']==name]
        misses=Counter(x for r in sub for x in r['missing_invariants'])
        summary[name]={
          'cases':len(sub),
          'mode_match_rate':sum(r['mode_match'] for r in sub)/len(sub),
          'mean_invariant_coverage':sum(r['invariant_coverage'] for r in sub)/len(sub),
          'structurally_valid_cases':sum(r['structurally_valid'] for r in sub),
          'mean_overhead_units':sum(r['overhead_units'] for r in sub)/len(sub),
          'missing_invariants':dict(misses),
        }
    result={
      'fixture_count':len(payload['cases']),
      'fixture_status':'constructed design benchmark, not empirical OPC evidence',
      'summary':summary,
      'rows':rows,
      'limitations':[
        'Fixtures and expected controls were authored from the same theory that produced the router; results test consistency and reveal omissions, not external validity.',
        'The platform and central-agent baselines are deliberately minimal structural implementations, not best commercial products or expert human brokers.',
        'No simulated score is interpreted as a real transaction, revenue, acceptance, or safety rate.'
      ]
    }
    outdir=HERE/'outputs'; outdir.mkdir(exist_ok=True)
    (outdir/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
