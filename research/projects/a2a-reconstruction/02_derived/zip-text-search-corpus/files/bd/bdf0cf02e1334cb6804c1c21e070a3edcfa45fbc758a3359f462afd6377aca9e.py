from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CASE_ROOT=ROOT/'archival_cases'
SOURCE_INDEX=ROOT/'sources'/'SOURCE_INDEX.json'
REQ={'case_id','title','domain','period','outcome','research_role','coding_status','source_ids','evidence_coverage','initial_relation_frame','authority_topology','timeline','supports','does_not_support','competing_explanations','design_delta','unknowns'}
EVENT_REQ={'event_id','date','label','event_type','materiality','changed_components','formation_operators','description','source_ids','confidence','epistemic_status'}
FRAME_REQ={'frame_scope','R','V','T','A','E','D','O'}
COVER_REQ={'source_proximity','process_granularity','authority_visibility','effect_observability','participant_voice_coverage','counterfactual_support','triangulation','selection_bias_risk'}
ALLOWED_COMPONENTS=set('RVT AEDO'.replace(' ',''))

def main():
    errors=[]; warnings=[]
    idx=json.loads(SOURCE_INDEX.read_text(encoding='utf-8'))
    source_ids={s['source_id'] for s in idx['sources']}
    case_ids=set(); event_ids=set(); files=sorted(CASE_ROOT.glob('*/case.json'))
    for p in files:
        c=json.loads(p.read_text(encoding='utf-8'))
        missing=REQ-set(c)
        if missing: errors.append(f'{p}: missing {sorted(missing)}'); continue
        if c['case_id'] in case_ids: errors.append(f'duplicate case_id {c["case_id"]}')
        case_ids.add(c['case_id'])
        if c['coding_status'] not in {'single_coder_provisional','double_coded','adjudicated'}: errors.append(f'{c["case_id"]}: invalid coding_status')
        if FRAME_REQ-set(c['initial_relation_frame']): errors.append(f'{c["case_id"]}: incomplete frame')
        if COVER_REQ-set(c['evidence_coverage']): errors.append(f'{c["case_id"]}: incomplete evidence coverage')
        for k,v in c['evidence_coverage'].items():
            if k!='selection_bias_risk' and (not isinstance(v,int) or v not in (0,1,2)): errors.append(f'{c["case_id"]}: coverage {k} must be 0..2')
        for sid in c['source_ids']:
            if sid not in source_ids: errors.append(f'{c["case_id"]}: unknown source {sid}')
        if len(c['authority_topology'])<2: errors.append(f'{c["case_id"]}: too few authority loci')
        if len(c['timeline'])<3: errors.append(f'{c["case_id"]}: too few events')
        for e in c['timeline']:
            miss=EVENT_REQ-set(e)
            if miss: errors.append(f'{c["case_id"]}/{e.get("event_id")}: missing {sorted(miss)}'); continue
            if e['event_id'] in event_ids: errors.append(f'duplicate event_id {e["event_id"]}')
            event_ids.add(e['event_id'])
            bad=set(e['changed_components'])-ALLOWED_COMPONENTS
            if bad: errors.append(f'{e["event_id"]}: invalid schema components {sorted(bad)}')
            for sid in e['source_ids']:
                if sid not in source_ids: errors.append(f'{e["event_id"]}: unknown source {sid}')
        if not c['does_not_support'] or not c['competing_explanations']:
            errors.append(f'{c["case_id"]}: must record non-support and competing explanations')
        if c['coding_status']=='single_coder_provisional': warnings.append(f'{c["case_id"]}: requires independent recoding before adjudicated evidence')
    out={'valid':not errors,'case_count':len(files),'event_count':len(event_ids),'errors':errors,'warnings':warnings}
    outp=ROOT/'instrument'/'archival_coder'/'output'/'validation.json'
    outp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
    return 0 if not errors else 1
if __name__=='__main__': raise SystemExit(main())
