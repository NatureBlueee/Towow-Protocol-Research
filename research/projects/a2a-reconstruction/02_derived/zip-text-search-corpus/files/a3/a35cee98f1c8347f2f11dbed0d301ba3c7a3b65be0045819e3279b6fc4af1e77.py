#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1] if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
rows=[]
for p in sorted(root.rglob('*')):
    if p.is_file() and p.name!='PACKAGE_INVENTORY.json':
        b=p.read_bytes(); rows.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(root/'PACKAGE_INVENTORY.json').write_text(json.dumps({'files':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print(len(rows))
