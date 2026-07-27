#!/usr/bin/env python3
"""Portable verifier for a Towow R5.2 local research return packet.

Usage:
    python portable_return_verifier.py /path/to/return-packet

The verifier is intentionally generic. It validates byte integrity, manifest
schema, experiment records, claim evidence paths, JSON/YAML syntax, basic secret
patterns, and relocation metadata. Domain-specific result recomputation should
be added inside the returned packet as extra independent review scripts.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sys
from pathlib import Path
import jsonschema, yaml


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()


def find_root(p: Path) -> Path:
    p=p.resolve()
    if (p/'manifests'/'MANIFEST.json').is_file(): return p
    candidates=list(p.glob('*/manifests/MANIFEST.json'))
    if len(candidates)==1: return candidates[0].parents[1]
    raise SystemExit(f'cannot locate unique return-packet root under {p}')


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('packet',nargs='?',default='.')
    args=ap.parse_args(); root=find_root(Path(args.packet))
    errors=[]; warnings=[]; checks={'root':str(root)}

    # Checksums
    cpath=root/'manifests'/'CHECKSUMS.sha256'
    if not cpath.is_file(): errors.append('missing manifests/CHECKSUMS.sha256')
    else:
        n=0
        for line in cpath.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            try: expected,rel=line.split('  ',1)
            except ValueError: errors.append(f'invalid checksum line: {line}'); continue
            p=root/rel; n+=1
            if not p.is_file(): errors.append(f'missing checksummed file: {rel}')
            elif sha256(p)!=expected: errors.append(f'checksum mismatch: {rel}')
        checks['checksummed_files']=n

    # Manifest/schema
    try:
        manifest=json.loads((root/'manifests'/'MANIFEST.json').read_text(encoding='utf-8'))
        schema=json.loads((root/'schemas'/'return_packet_manifest.schema.json').read_text(encoding='utf-8'))
        jsonschema.validate(manifest,schema); checks['manifest_schema_valid']=True
    except Exception as e:
        manifest={}; checks['manifest_schema_valid']=False; errors.append(f'manifest validation: {e}')

    # All JSON/YAML parse
    jp=0
    for p in root.rglob('*.json'):
        try: json.loads(p.read_text(encoding='utf-8-sig')); jp+=1
        except Exception as e: errors.append(f'invalid JSON {p.relative_to(root)}: {e}')
    for p in list(root.rglob('*.yaml'))+list(root.rglob('*.yml')):
        try: yaml.safe_load(p.read_text(encoding='utf-8'))
        except Exception as e: errors.append(f'invalid YAML {p.relative_to(root)}: {e}')
    checks['json_files_parsed']=jp

    # Experiment records and evidence paths relative to run directory
    try: run_schema=json.loads((root/'schemas'/'experiment_record.schema.json').read_text(encoding='utf-8'))
    except Exception as e: run_schema=None; errors.append(f'run schema unavailable: {e}')
    run_files=sorted((root/'experiments').glob('*/run.json')) if (root/'experiments').is_dir() else []
    for p in run_files:
        try:
            obj=json.loads(p.read_text(encoding='utf-8')); jsonschema.validate(obj,run_schema)
            for rel in obj.get('evidence_paths',[]):
                if not (p.parent/rel).exists(): errors.append(f'missing run evidence {p.parent.name}: {rel}')
        except Exception as e: errors.append(f'run validation {p.relative_to(root)}: {e}')
    checks['experiment_records']=len(run_files)

    # Claim refs. Supports artifact_ids plus logical_evidence_paths or legacy evidence_paths.
    claim=root/'CLAIM_EVIDENCE_UPDATE.csv'
    refs=0
    if claim.is_file():
        rows=list(csv.DictReader(claim.open(encoding='utf-8-sig',newline='')))
        for row in rows:
            raw=row.get('logical_evidence_paths') or row.get('evidence_paths') or ''
            paths=[x.strip() for x in raw.split(';') if x.strip()]
            if not paths: warnings.append(f"claim has no packaged evidence path: {row.get('claim_id')}")
            for rel in paths:
                refs+=1
                if not (root/rel).exists(): errors.append(f"claim {row.get('claim_id')} missing evidence: {rel}")
        checks['claim_rows']=len(rows); checks['claim_refs']=refs
    else: errors.append('missing CLAIM_EVIDENCE_UPDATE.csv')

    # Manifest file records
    if manifest:
        for item in manifest.get('files',[]):
            rel=item.get('path'); p=root/rel if rel else None
            if not rel or not p.is_file(): errors.append(f'manifest file missing: {rel}')
            else:
                if item.get('sha256')!=sha256(p): errors.append(f'manifest hash mismatch: {rel}')
                if item.get('bytes') is not None and item.get('bytes')!=p.stat().st_size: errors.append(f'manifest size mismatch: {rel}')

    # Common secret patterns; this is not a complete secret scan.
    key_files=[]; hits=[]
    pats=[('openai',re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b')),('github',re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}\b')),('private_key',re.compile(r'BEGIN [A-Z ]*PRIVATE KEY'))]
    for p in root.rglob('*'):
        if not p.is_file(): continue
        if p.name.endswith('.private') or p.suffix.lower() in {'.pem','.key','.p12','.pfx'}: key_files.append(p.relative_to(root).as_posix())
        if p.suffix.lower() in {'.json','.jsonl','.md','.csv','.yaml','.yml','.py','.log','.txt','.sig','.patch'}:
            text=p.read_text(encoding='utf-8',errors='replace')
            for name,pat in pats:
                if pat.search(text): hits.append(f'{p.relative_to(root)}:{name}')
    if key_files: errors.append(f'private-key-like files: {key_files}')
    if hits: errors.append(f'secret-like content: {hits}')
    checks['secret_hits']=hits

    relocation=manifest.get('relocation_test') if manifest else None
    if relocation and not relocation.get('performed'): warnings.append('manifest says relocation test not performed')
    if relocation and relocation.get('performed') and not relocation.get('passed'): errors.append('manifest says relocation test failed')

    payload={'status':'failed' if errors else 'passed_with_warnings' if warnings else 'passed','checks':checks,'warnings':warnings,'errors':errors}
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__=='__main__': raise SystemExit(main())
