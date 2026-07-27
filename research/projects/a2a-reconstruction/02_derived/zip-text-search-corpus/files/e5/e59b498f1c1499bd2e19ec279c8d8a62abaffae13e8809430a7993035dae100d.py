#!/usr/bin/env python3
from pathlib import Path
import json, collections
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
payload=json.loads((BASE/'cases.json').read_text(encoding='utf-8'))
cases=payload['cases']
obs_keys=list(cases[0]['observations'])
primary=collections.Counter(c['qualified_space_revision']['primary'] for c in cases)
secondary=collections.Counter(s for c in cases for s in c['qualified_space_revision']['secondary'])
obs={k:sum(bool(c['observations'][k]) for c in cases) for k in obs_keys}
dims=collections.Counter(d for c in cases for delta in c['schema_deltas'] for d in delta['dimensions'])
result={'version':'0.5','case_count':len(cases),'selection':payload['design'],'coder':payload['coder'],'primary_revision_counts':dict(sorted(primary.items())),'secondary_revision_counts':dict(sorted(secondary.items())),'observation_counts':obs,'relation_schema_dimension_counts':dict(sorted(dims.items())),'hard_nonfindings':{k:obs[k] for k in ['agent_mediated_causality_observed','subjective_acceptance_observed','comparable_net_surplus_observed']},'interpretation_rule':'Counts describe this purposively selected contrast corpus only; they are not population estimates.'}
(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
