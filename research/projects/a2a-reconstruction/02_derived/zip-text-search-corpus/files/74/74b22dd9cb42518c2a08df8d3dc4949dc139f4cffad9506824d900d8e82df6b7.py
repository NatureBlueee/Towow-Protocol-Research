#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
# JSON/JSONL parse
for p in ROOT.rglob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'JSON {p.relative_to(ROOT)}: {e}')
for p in ROOT.rglob('*.jsonl'):
    try:
        for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
            if line.strip(): json.loads(line)
    except Exception as e: errors.append(f'JSONL {p.relative_to(ROOT)}:{i}: {e}')
# rerun analysis
r=subprocess.run([sys.executable,str(ROOT/'experiments/R7P_public_trace_pilot/analyze.py')],capture_output=True,text=True)
if r.returncode: errors.append('analysis rerun failed: '+r.stderr)
# rerun importer
r=subprocess.run([sys.executable,str(ROOT/'instrument/public_trace_extension/import_public_trace.py'),str(ROOT/'instrument/public_trace_extension/sample_public_trace.jsonl'),str(ROOT/'instrument/public_trace_extension/_qa_chain.jsonl')],capture_output=True,text=True)
if r.returncode: errors.append('importer failed: '+r.stderr)
else:
    lines=[json.loads(x) for x in (ROOT/'instrument/public_trace_extension/_qa_chain.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    prev='0'*64
    for i,x in enumerate(lines):
        payload=json.dumps(x['event'],ensure_ascii=False,sort_keys=True,separators=(',',':'))
        h=hashlib.sha256((prev+payload).encode()).hexdigest()
        if x['prev_hash']!=prev or x['hash']!=h: errors.append(f'hash chain break {i}')
        prev=h
    (ROOT/'instrument/public_trace_extension/_qa_chain.jsonl').unlink(missing_ok=True)
# required files
required=['public_evidence/00_EXECUTIVE_SYNTHESIS.md','experiments/R7P_public_trace_pilot/results.json','theory/05_证据拓扑与公开材料边界_v0.5.md','instrument/public_trace_extension/public_trace_event.schema.json']
for rel in required:
    if not (ROOT/rel).exists(): errors.append('missing '+rel)
result={'passed':not errors,'errors':errors}
(ROOT/'qa/V0_5_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
