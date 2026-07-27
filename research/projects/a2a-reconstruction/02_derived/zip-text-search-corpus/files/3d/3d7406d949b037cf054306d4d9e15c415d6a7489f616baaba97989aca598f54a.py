from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    components=Counter(); operators=Counter(); materiality=Counter(); events={}
    for p in sorted((ROOT/'archival_cases').glob('*/case.json')):
        c=json.loads(p.read_text(encoding='utf-8')); events[c['case_id']]=len(c['timeline'])
        for e in c['timeline']:
            materiality[e['materiality']]+=1
            components.update(e['changed_components']); operators.update(e['formation_operators'])
    out={'case_count':len(events),'event_count':sum(events.values()),'events_by_case':events,
         'schema_component_mentions':dict(sorted(components.items())),
         'formation_operator_mentions':dict(operators.most_common()),'materiality_labels':dict(materiality),
         'coding_status':'single_coder_provisional',
         'interpretation_warning':'Counts describe this coding only; they are not population frequencies or causal estimates.'}
    (ROOT/'instrument'/'archival_coder'/'output'/'summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
