#!/usr/bin/env python3
from pathlib import Path
import shutil,sys
root=Path(__file__).resolve().parents[1]
dest=Path(sys.argv[1] if len(sys.argv)>1 else './new-prse-project')
if dest.exists(): raise SystemExit(f'{dest} exists')
shutil.copytree(root/'14_PROJECT_TEMPLATE',dest)
print(f'Created {dest}')
