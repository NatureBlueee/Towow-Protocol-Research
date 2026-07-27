#!/usr/bin/env python3
from pathlib import Path
import json, sys, hashlib
ALLOWED=set('RVT AEDO'.replace(' ',''))

def validate(e):
    req=['case_id','event_id','event_date','actor','authority_locus','event_type','relation_version','schema_dimensions','source_ids']
    missing=[k for k in req if k not in e]
    if missing: raise ValueError(f"missing {missing}")
    bad=set(e['schema_dimensions'])-ALLOWED
    if bad: raise ValueError(f"bad dimensions {bad}")
    if not e['source_ids']: raise ValueError('source_ids empty')
    return True

def import_trace(src,dst):
    events=[]
    for line in Path(src).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        e=json.loads(line); validate(e); events.append(e)
    events.sort(key=lambda x:(x['case_id'],x['event_date'],x['event_id']))
    prev='0'*64; out=[]
    for e in events:
        payload=json.dumps(e,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        h=hashlib.sha256((prev+payload).encode()).hexdigest()
        out.append({'event':e,'prev_hash':prev,'hash':h}); prev=h
    Path(dst).write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in out)+'\n',encoding='utf-8')
    return len(out)
if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: import_public_trace.py input.jsonl output.jsonl')
    print(import_trace(sys.argv[1],sys.argv[2]))
