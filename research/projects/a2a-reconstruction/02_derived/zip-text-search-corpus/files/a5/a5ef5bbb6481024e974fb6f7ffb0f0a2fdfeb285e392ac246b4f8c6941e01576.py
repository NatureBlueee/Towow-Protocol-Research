#!/usr/bin/env python3
from pathlib import Path
import json, collections
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EVENTS=[json.loads(x) for x in (HERE/'coded_events.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
PROFILES=json.loads((HERE/'case_profiles.json').read_text(encoding='utf-8'))
SOURCES=json.loads((ROOT/'public_evidence/source_manifest_v0.6.json').read_text(encoding='utf-8'))
CLAIMS=json.loads((ROOT/'public_evidence/claim_requirements_v0.6.json').read_text(encoding='utf-8'))

def source_compatible(src, req): return all(src.get('profile',{}).get(k,0)>=v for k,v in req.items())
def vis(v): return {'FULL':1.0,'PARTIAL':0.5,'NONE':0.0}.get(v)
case_ids=sorted({e['case_id'] for e in EVENTS})
material=[e for e in EVENTS if e['material_schema_change']]
critical=[e for e in EVENTS if e.get('critical_turn')]
complete=[e for e in EVENTS if e.get('operationally_complete')]
residual=[e for e in EVENTS if e.get('structural_residual')]
dims=collections.Counter(d for e in EVENTS for d in e['schema_dimensions'])
scopes=collections.Counter(e['relation_version_scope'] for e in EVENTS)
ops=collections.Counter(x for e in EVENTS for x in e['formation_operators'])
triggers=collections.Counter(x for e in EVENTS for x in e['reopen_triggers'])
compile_modes=collections.Counter(e['compile_mode'] for e in EVENTS)
standing_events=[e for e in EVENTS if any(x in {'AFFECTED_PARTY_STANDING','PUBLIC_INPUT_WITHOUT_FINAL_DECISION_AUTHORITY','EXPERT_CHALLENGE_STANDING','FORMAL_CHALLENGE_STANDING','USER_REPRESENTATION_REQUIREMENT','AUTONOMY_CLAIM'} for x in e['standing_types'])]
gap_events=[e for e in EVENTS if e['declared_enacted_gap']]
partial_stability=[]
for e in EVENTS:
    s=e['stability_dimensions']
    vals={v for v in s.values() if v!='NOT_ASSESSED'}
    if 'STABLE' in vals and ('FAILED' in vals or 'OPEN' in vals or 'CONDITIONAL' in vals): partial_stability.append(e)
non_code_compile=[e for e in EVENTS if not any(x in e['compile_mode'] for x in ['CODE_ONLY'])]
reserved=[e for e in EVENTS if e.get('reserved_contingency')]

case_summary={}
for c in sorted(case_ids):
    es=[e for e in EVENTS if e['case_id']==c]
    case_summary[c]={
      'title':PROFILES[c]['title'],'events':len(es),'material_events':sum(e['material_schema_change'] for e in es),
      'critical_turns':sum(bool(e.get('critical_turn')) for e in es),'operationally_complete_events':sum(bool(e.get('operationally_complete')) for e in es),
      'standing_materiality_events':sum(e in standing_events for e in es),'declared_enacted_gap_events':sum(e in gap_events for e in es),
      'reopen_trigger_events':sum(bool(e['reopen_triggers']) for e in es),'frame_sufficiency':PROFILES[c]['frame_sufficiency'],
      'outcome':PROFILES[c]['outcome'],'research_role':PROFILES[c]['research_role']
    }

# Announcement/compressed-stream ablation is only valid for the original three cases.
ablation=[e for e in EVENTS if e.get('compressed_stream_visibility') in {'FULL','PARTIAL','NONE'}]
ab_material=[e for e in ablation if e['material_schema_change']]
ab_critical=[e for e in ablation if e.get('critical_turn')]
ab_loci={e['authority_locus'] for e in ablation}
ab_vis_loci={e['authority_locus'] for e in ablation if e['compressed_stream_visibility']!='NONE'}
doc_ablation={
 'scope_cases':sorted({e['case_id'] for e in ablation}),'scope_events':len(ablation),
 'compressed_strict_event_recall':sum(e['compressed_stream_visibility']=='FULL' for e in ablation)/len(ablation),
 'compressed_weighted_event_recall':sum(vis(e['compressed_stream_visibility']) for e in ablation)/len(ablation),
 'compressed_strict_material_recall':sum(e['compressed_stream_visibility']=='FULL' for e in ab_material)/len(ab_material),
 'compressed_weighted_material_recall':sum(vis(e['compressed_stream_visibility']) for e in ab_material)/len(ab_material),
 'compressed_strict_critical_recall':sum(e['compressed_stream_visibility']=='FULL' for e in ab_critical)/len(ab_critical),
 'compressed_weighted_critical_recall':sum(vis(e['compressed_stream_visibility']) for e in ab_critical)/len(ab_critical),
 'authority_locus_recall':len(ab_vis_loci)/len(ab_loci), 'all_authority_loci':len(ab_loci),'visible_authority_loci':len(ab_vis_loci)
}
compat={}
for cl in CLAIMS:
    compat[cl['claim_id']]=[s['source_id'] for s in SOURCES if source_compatible(s,cl['requires']) and not cl.get('extra_required')]

pressure_tests={
 'standing_without_signature':{'observed':bool(standing_events),'event_ids':[e['event_id'] for e in standing_events], 'interpretation':'Standing can change evaluation, scope or governance without becoming bilateral signature authority.'},
 'declared_vs_enacted_schema':{'observed':bool(gap_events),'event_ids':[e['event_id'] for e in gap_events], 'interpretation':'A written integration/governance plan does not prove observation, intervention, resources or assurance in operation.'},
 'partial_stability':{'observed':bool(partial_stability),'event_ids':[e['event_id'] for e in partial_stability], 'interpretation':'Technical, authority, assurance, legitimacy and economic stability can diverge.'},
 'compile_is_institutionalization':{'observed':bool(non_code_compile),'compile_modes':dict(compile_modes),'interpretation':'Contracts, standards, approvals, assurance, dispute and exit can compile an open relation into repeatable operation.'},
 'reserved_contingency_negative_control':{'observed':bool(reserved),'event_ids':[e['event_id'] for e in reserved], 'interpretation':'A previously reserved branch can absorb a large parameter shock without material schema revision.'},
 'institutional_frame_sufficiency_negative_case':{'observed':PROFILES['LNK_MS']['frame_sufficiency']=='HIGH','cases':['LNK_MS','NASA_HLS'],'interpretation':'Surface complexity alone is insufficient to justify open-ended formation.'},
 'live_agent_causal_claim_still_open':{'observed':False,'interpretation':'No case contains prospective scoped delegation to the Towow mechanism or a causal comparison with an excellent broker/central Agent.'}
}

out={
 'release':'v0.6','scope':{'unique_cases':len(case_ids),'events':len(EVENTS),'new_archival_cases':4,'original_public_trace_cases':3,'single_coder':True,'independent_inter_rater_reliability':False,'theoretical_sampling_not_population_sample':True},
 'schema_coding':{'dimension_mapped_events':len(EVENTS),'structural_residual_events':len(residual),'operationally_complete_events':len(complete),'operational_completeness_rate':len(complete)/len(EVENTS),'material_schema_events':len(material),'critical_turns':len(critical),'dimension_frequency':dict(sorted(dims.items())),'relation_version_scope_frequency':dict(scopes)},
 'mechanism_codes':{'formation_operator_frequency':dict(ops.most_common()),'reopen_trigger_frequency':dict(triggers.most_common()),'compile_mode_frequency':dict(compile_modes)},
 'boundary_findings':{'standing_materiality_events':len(standing_events),'declared_enacted_gap_events':len(gap_events),'partial_stability_events':len(partial_stability),'reserved_contingency_events':len(reserved)},
 'case_summary':case_summary,'document_ablation_original_three_cases':doc_ablation,'theory_pressure_tests':pressure_tests,
 'claim_source_compatibility':compat,'claims_with_no_compatible_public_source':[c['claim_id'] for c in CLAIMS if not compat[c['claim_id']]],
 'interpretation_limits':[
  'All seven-case event coding remains single-coder and theory-informed; no inter-rater reliability is claimed.',
  'Zero structural residual means the coder could place each event in the current schema, not that the schema is complete or uniquely correct.',
  'The four added cases are theoretical samples selected to stress different mechanisms; event counts are not population frequencies.',
  'Retrospective official records are curated and can omit informal power, private motives and failed alternatives.',
  'Public evidence can calibrate constructs, boundary conditions and instruments, but cannot establish live Agent delegation, prospective Principal acceptance or causal net value versus a strong broker.'
 ]
}
(HERE/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
