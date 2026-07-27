#!/usr/bin/env python3
from pathlib import Path
import json, collections
HERE=Path(__file__).resolve().parent
EVENTS=[json.loads(x) for x in (HERE/'coded_events.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
ROOT=HERE.parents[1]
SOURCES=json.loads((ROOT/'public_evidence/source_manifest.json').read_text(encoding='utf-8'))
CLAIMS=json.loads((ROOT/'public_evidence/claim_requirements.json').read_text(encoding='utf-8'))

def visibility_value(v): return {'FULL':1.0,'PARTIAL':0.5,'NONE':0.0}[v]

def source_compatible(src, req):
    return all(src['profile'].get(k,0)>=v for k,v in req.items())

case_ids=sorted({e['case_id'] for e in EVENTS})
material=[e for e in EVENTS if e['material_schema_change']]
critical=[e for e in EVENTS if e['critical_turn']]
complete=[e for e in EVENTS if e['operationally_complete']]
residual=[e for e in EVENTS if e['structural_residual']]
full=[e for e in EVENTS if e['compressed_stream_visibility']=='FULL']
weighted=sum(visibility_value(e['compressed_stream_visibility']) for e in EVENTS)
crit_full=[e for e in critical if e['compressed_stream_visibility']=='FULL']
crit_weighted=sum(visibility_value(e['compressed_stream_visibility']) for e in critical)
mat_full=[e for e in material if e['compressed_stream_visibility']=='FULL']
mat_weighted=sum(visibility_value(e['compressed_stream_visibility']) for e in material)
all_loci={e['authority_locus'] for e in EVENTS}
visible_loci={e['authority_locus'] for e in EVENTS if e['compressed_stream_visibility']!='NONE'}
dims=collections.Counter(d for e in EVENTS for d in e['schema_dimensions'])
case_summary={}
for c in case_ids:
    es=[e for e in EVENTS if e['case_id']==c]
    ms=[e for e in es if e['material_schema_change']]
    cs=[e for e in es if e['critical_turn']]
    case_summary[c]={
        'events':len(es),'material':len(ms),'critical':len(cs),
        'operationally_complete':sum(e['operationally_complete'] for e in es),
        'compressed_strict_recall':sum(e['compressed_stream_visibility']=='FULL' for e in es)/len(es),
        'compressed_weighted_recall':sum(visibility_value(e['compressed_stream_visibility']) for e in es)/len(es),
        'critical_weighted_recall':sum(visibility_value(e['compressed_stream_visibility']) for e in cs)/len(cs) if cs else None,
    }
compat={}
for cl in CLAIMS:
    compat[cl['claim_id']]=[s['source_id'] for s in SOURCES if source_compatible(s,cl['requires']) and not cl.get('extra_required')]
result={
    'pilot_scope':{'cases':len(case_ids),'events':len(EVENTS),'single_coder':True,'independent_inter_rater_reliability':False},
    'schema_coding':{
        'dimension_mapped_events':len(EVENTS),
        'structural_residual_events':len(residual),
        'operationally_complete_events':len(complete),
        'operational_completeness_rate':len(complete)/len(EVENTS),
        'material_schema_events':len(material),
        'critical_turns':len(critical),
        'dimension_frequency':dict(sorted(dims.items()))
    },
    'document_ablation':{
        'compressed_strict_event_recall':len(full)/len(EVENTS),
        'compressed_weighted_event_recall':weighted/len(EVENTS),
        'compressed_strict_material_recall':len(mat_full)/len(material),
        'compressed_weighted_material_recall':mat_weighted/len(material),
        'compressed_strict_critical_recall':len(crit_full)/len(critical),
        'compressed_weighted_critical_recall':crit_weighted/len(critical),
        'authority_locus_recall':len(visible_loci)/len(all_loci),
        'all_authority_loci':len(all_loci),
        'visible_authority_loci':len(visible_loci)
    },
    'case_summary':case_summary,
    'claim_source_compatibility':compat,
    'claims_with_no_compatible_public_source':[c['claim_id'] for c in CLAIMS if not compat[c['claim_id']]],
    'interpretation_limits':[
        'All event coding is a single-coder pilot; zero structural residual is not inter-rater validation.',
        'Compressed-stream recall uses manually adjudicated FULL/PARTIAL/NONE visibility labels.',
        'Formal records are retrospective and selected; missing private states cannot be inferred as absent.',
        'Public sources cannot satisfy live Agent delegation, prospective acceptance, or causal net-value claims.'
    ]
}
(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
