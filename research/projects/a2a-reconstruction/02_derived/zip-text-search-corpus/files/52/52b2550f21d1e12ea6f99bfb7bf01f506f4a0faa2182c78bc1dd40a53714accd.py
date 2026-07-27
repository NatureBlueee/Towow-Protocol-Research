#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path


def labels(s:str)->set[str]:
    return {x.strip() for x in (s or '').replace(';',',').split(',') if x.strip()}

def binary(s:str)->int|None:
    t=(s or '').strip().upper()
    if t in {'YES','Y','1','TRUE','PRESENT'}: return 1
    if t in {'NO','N','0','FALSE','ABSENT'}: return 0
    return None

def kappa(a:list[int],b:list[int])->float|None:
    if not a or len(a)!=len(b): return None
    n=len(a); po=sum(x==y for x,y in zip(a,b))/n
    pa=sum(a)/n; pb=sum(b)/n; pe=pa*pb+(1-pa)*(1-pb)
    if math.isclose(pe,1): return 1.0 if math.isclose(po,1) else 0.0
    return (po-pe)/(1-pe)

def mean(xs): return sum(xs)/len(xs) if xs else None

def load(path:Path):
    with path.open(encoding='utf-8-sig',newline='') as f: return {r['item_id']:r for r in csv.DictReader(f)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('coder_a',type=Path); ap.add_argument('coder_b',type=Path); ap.add_argument('--out',type=Path,default=Path('agreement_results.json')); args=ap.parse_args()
    A=load(args.coder_a); B=load(args.coder_b); ids=sorted(set(A)&set(B))
    result={'paired_items':len(ids),'missing_in_a':sorted(set(B)-set(A)),'missing_in_b':sorted(set(A)-set(B))}
    for field in ['material_change','authority_locus_present','standing_present']:
        pairs=[(binary(A[i].get(field,'')),binary(B[i].get(field,''))) for i in ids]
        pairs=[p for p in pairs if None not in p]
        result[field]={'paired_nonmissing':len(pairs),'cohen_kappa':kappa([p[0] for p in pairs],[p[1] for p in pairs]),'raw_agreement':mean([int(p[0]==p[1]) for p in pairs])}
    for field in ['gamma_dimensions','coordination_mechanisms','actor_dimensions']:
        rows=[]; universe=set()
        for i in ids:
            a=labels(A[i].get(field,'')); b=labels(B[i].get(field,'')); universe|=a|b
            rows.append((a,b))
        j=[len(a&b)/len(a|b) if a|b else 1.0 for a,b in rows]
        per={}
        for label in sorted(universe):
            aa=[int(label in a) for a,b in rows]; bb=[int(label in b) for a,b in rows]
            per[label]={'cohen_kappa':kappa(aa,bb),'raw_agreement':mean([int(x==y) for x,y in zip(aa,bb)])}
        result[field]={'mean_jaccard':mean(j),'per_label':per}
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
