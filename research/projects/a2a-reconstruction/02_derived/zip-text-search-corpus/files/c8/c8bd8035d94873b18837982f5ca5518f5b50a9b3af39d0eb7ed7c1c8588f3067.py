#!/usr/bin/env python3
from pathlib import Path
import json, sys, hashlib
try:
    import yaml
except Exception:
    yaml=None

root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
errors=[]; warnings=[]
manifest=root/'package.manifest.yaml'
if not manifest.exists(): errors.append('missing package.manifest.yaml')
else:
    if yaml:
        data=yaml.safe_load(manifest.read_text(encoding='utf-8'))
        for name,rel in data.get('entrypoints',{}).items():
            if not (root/rel).exists(): errors.append(f'missing entrypoint {name}: {rel}')
for p in root.rglob('*'):
    if not p.is_file(): continue
    if p.stat().st_size==0: warnings.append(f'empty file: {p.relative_to(root)}')
    try:
        if p.suffix=='.json': json.loads(p.read_text(encoding='utf-8'))
        elif p.suffix in ('.yaml','.yml') and yaml: yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception as e: errors.append(f'parse error {p.relative_to(root)}: {e}')
# duplicate summon node ids
node_file=root/'11_SUMMON_REFERENCE/spec/constitution.yaml'
if node_file.exists() and yaml:
    d=yaml.safe_load(node_file.read_text(encoding='utf-8')) or {}
    ids=[n.get('id') for n in d.get('nodes',[])]
    dup={x for x in ids if ids.count(x)>1}
    if dup: errors.append(f'duplicate spec node ids: {sorted(dup)}')
print(f'Files: {sum(1 for p in root.rglob("*") if p.is_file())}')
print(f'Errors: {len(errors)}; Warnings: {len(warnings)}')
for x in errors: print('ERROR',x)
for x in warnings: print('WARN',x)
sys.exit(1 if errors else 0)
