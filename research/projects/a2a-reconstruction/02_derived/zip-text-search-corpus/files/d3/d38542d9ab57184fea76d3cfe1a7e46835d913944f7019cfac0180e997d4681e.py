from __future__ import annotations
import json, hashlib, subprocess, sys, re, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]; checks={}

def run(name, cmd, cwd=ROOT):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    checks[name]={'returncode':p.returncode,'stdout_tail':p.stdout[-2000:],'stderr_tail':p.stderr[-2000:]}
    if p.returncode: errors.append(f'{name} failed')

# Parse all JSON/JSONL.
json_count=jsonl_count=0
for p in ROOT.rglob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8')); json_count+=1
    except Exception as e: errors.append(f'JSON {p.relative_to(ROOT)}: {e}')
for p in ROOT.rglob('*.jsonl'):
    try:
        for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
            if line.strip(): json.loads(line)
        jsonl_count+=1
    except Exception as e: errors.append(f'JSONL {p.relative_to(ROOT)}:{i}: {e}')
checks['parse']={'json_files':json_count,'jsonl_files':jsonl_count}

# Validate v0.6 events manually and with jsonschema when available.
schema=json.loads((ROOT/'instrument/public_trace_extension/public_trace_event_v0.6.schema.json').read_text(encoding='utf-8'))
events=[json.loads(x) for x in (ROOT/'experiments/R7P_public_trace_extended/coded_events.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
req=set(schema['required']); ids=set(); source_ids={s['source_id'] for s in json.loads((ROOT/'public_evidence/source_manifest_v0.6.json').read_text(encoding='utf-8'))}
for e in events:
    miss=req-set(e)
    if miss: errors.append(f'{e.get("event_id")}: missing {sorted(miss)}')
    if e.get('event_id') in ids: errors.append(f'duplicate event {e.get("event_id")}')
    ids.add(e.get('event_id'))
    bad=set(e.get('schema_dimensions',[]))-set('RVT AEDO'.replace(' ',''))
    if bad: errors.append(f'{e.get("event_id")}: bad dimensions {bad}')
    unknown=set(e.get('source_ids',[]))-source_ids
    if unknown: errors.append(f'{e.get("event_id")}: unknown sources {sorted(unknown)}')
try:
    import jsonschema
    for e in events: jsonschema.validate(e,schema)
    checks['jsonschema']={'validated_events':len(events)}
except ImportError:
    warnings.append('jsonschema unavailable; manual schema checks only')
except Exception as ex:
    errors.append(f'jsonschema validation: {ex}')
checks['extended_scope']={'cases':len({e['case_id'] for e in events}),'events':len(events)}
if len({e['case_id'] for e in events})!=7: errors.append('expected 7 unique cases')
if len(events)!=58: errors.append(f'expected 58 events, got {len(events)}')

run('extended_analyzer',[sys.executable,'experiments/R7P_public_trace_extended/analyze.py'])
run('archival_validator',[sys.executable,'instrument/archival_coder/validate_cases.py'])
run('archival_summary',[sys.executable,'instrument/archival_coder/summarize_cases.py'])
run('old_pilot',[sys.executable,'experiments/R7P_public_trace_pilot/analyze.py'])
run('ontology_reduction',[sys.executable,'experiments/ontology_reduction/run.py'])
run('schema_classifier',[sys.executable,'experiments/schema_change_classifier/run.py'])
# Fieldkit tests.
run('fieldkit_tests',[sys.executable,'-m','unittest','discover','-s','tests','-v'],ROOT/'instrument/towow_fieldkit')

# Cached source checksums.
cache_checks=json.loads((ROOT/'public_evidence/source_cache/checksums.json').read_text(encoding='utf-8'))
for c in cache_checks:
    p=ROOT/'public_evidence/source_cache'/c['filename']
    if not p.exists(): errors.append(f'missing cached source {c["filename"]}'); continue
    if hashlib.sha256(p.read_bytes()).hexdigest()!=c['sha256']: errors.append(f'checksum mismatch {c["filename"]}')
checks['source_cache']={'files':len(cache_checks),'bytes':sum(c['bytes'] for c in cache_checks)}

# Local Markdown links.
link_re=re.compile(r'\[[^\]]*\]\(([^)]+)\)')
md_checked=links_checked=0
for p in ROOT.rglob('*.md'):
    txt=p.read_text(encoding='utf-8',errors='replace'); md_checked+=1
    for target in link_re.findall(txt):
        if target.startswith(('http://','https://','mailto:','#','sandbox:')): continue
        target=target.split('#',1)[0]
        if not target: continue
        links_checked+=1
        q=(p.parent/target).resolve()
        if ROOT not in q.parents and q!=ROOT: errors.append(f'link escapes root {p.relative_to(ROOT)} -> {target}')
        elif not q.exists(): errors.append(f'broken link {p.relative_to(ROOT)} -> {target}')
checks['links']={'markdown_files':md_checked,'local_links':links_checked}

out={'release':'v0.6','passed':not errors,'errors':errors,'warnings':warnings,'checks':checks}
(ROOT/'qa/V0_6_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# v0.6 Release QA','',f"**Result:** {'PASS' if out['passed'] else 'FAIL'}",'',f"- JSON files: {json_count}",f"- JSONL files: {jsonl_count}",f"- Extended cases/events: {checks['extended_scope']['cases']}/{checks['extended_scope']['events']}",f"- Cached source files: {checks['source_cache']['files']}",f"- Local links checked: {links_checked}",f"- Errors: {len(errors)}",f"- Warnings: {len(warnings)}",'']
if errors: lines += ['## Errors']+[f'- {x}' for x in errors]+['']
if warnings: lines += ['## Warnings']+[f'- {x}' for x in warnings]+['']
lines += ['## Subprocesses']+[f"- `{k}`: returncode {v['returncode']}" for k,v in checks.items() if isinstance(v,dict) and 'returncode' in v]
(ROOT/'qa/V0_6_QA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(0 if out['passed'] else 1)
