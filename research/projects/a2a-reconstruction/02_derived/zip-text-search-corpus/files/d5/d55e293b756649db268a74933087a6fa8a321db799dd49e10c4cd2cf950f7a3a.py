#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, random, re, sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ANALYZER=ROOT/'experiments/qdr_temporal_analysis/analyze_qdr.py'
CODEBOOK=ROOT/'experiments/qdr_temporal_analysis/codebook.json'
EXCERPTS=ROOT/'experiments/qdr_temporal_analysis/outputs/retrieved_excerpts.jsonl'

spec=importlib.util.spec_from_file_location('qdr_analyzer',ANALYZER)
mod=importlib.util.module_from_spec(spec); assert spec.loader; sys.modules[spec.name]=mod; spec.loader.exec_module(mod)


def short(text:str,n:int=520)->str:
    text=re.sub(r'\s+',' ',text).strip()
    return text if len(text)<=n else text[:n-1].rstrip()+'…'


def main():
    codebook=json.loads(CODEBOOK.read_text(encoding='utf-8'))
    hits=[json.loads(x) for x in EXCERPTS.read_text(encoding='utf-8').splitlines() if x.strip()]
    by=defaultdict(list)
    for r in hits: by[r['code']].append(r)

    selected=[]; used_units=set(); used_per_code={}
    for family in ('native_concerns','coordination_mechanisms','agentic_actor_dimensions'):
        for code in codebook[family]:
            seen_interviews=set(); picks=[]
            candidates=sorted(by[code],key=lambda r:(-r['match_count'],r['interview'],r['unit_index']))
            # First pass: maximize interview diversity and avoid duplicate units across codes.
            for r in candidates:
                key=(r['interview'],r['unit_index'])
                if key in used_units or r['interview'] in seen_interviews: continue
                picks.append(r); used_units.add(key); seen_interviews.add(r['interview'])
                if len(picks)==4: break
            # Second pass if a code has too few unique units.
            for r in candidates:
                if len(picks)==4: break
                key=(r['interview'],r['unit_index'])
                if key in used_units: continue
                picks.append(r); used_units.add(key)
            for r in picks:
                selected.append({
                    'origin':'retrieval_candidate','origin_family':family,'origin_code':code,
                    'interview':r['interview'],'date':r['date'],'wave':r['wave'],'unit_index':r['unit_index'],
                    'excerpt':short(r['excerpt']),'match_count':r['match_count'],
                })
            used_per_code[code]=len(picks)

    # Negative/control units contain no refined retrieval hit. They are not assumed
    # to be semantically negative; they test whether human coders discover missed
    # constructs and therefore can reveal false negatives.
    hit_units={(r['interview'],r['unit_index']) for r in hits}
    controls=[]
    for tr in mod.load_transcripts():
        for idx,unit in enumerate(mod.excerpt_units(tr)):
            if (tr.number,idx) in hit_units: continue
            text=short(unit)
            if 140<=len(text)<=520:
                controls.append({
                    'origin':'retrieval_control','origin_family':None,'origin_code':None,
                    'interview':tr.number,'date':tr.date,'wave':tr.wave,'unit_index':idx,
                    'excerpt':text,'match_count':0,
                })
    rng=random.Random(707)
    rng.shuffle(controls)
    chosen=[]; seen=set()
    for r in controls:
        if r['interview'] in seen: continue
        seen.add(r['interview']); chosen.append(r)
        if len(chosen)==18: break
    selected.extend(chosen)

    # Stable opaque IDs preserve pairing while hiding retrieval provenance.
    packet=[]; key_rows=[]
    for row in selected:
        raw=f"{row['interview']}::{row['unit_index']}::{row['date']}"
        item='QDR-'+hashlib.sha256(raw.encode()).hexdigest()[:10].upper()
        packet.append({'item_id':item,'wave':row['wave'],'excerpt':row['excerpt']})
        key_rows.append({'item_id':item,**{k:v for k,v in row.items() if k!='excerpt'}})

    a=list(packet); b=list(packet)
    random.Random(1701).shuffle(a); random.Random(2701).shuffle(b)
    for name,rows in [('A',a),('B',b)]:
        with (HERE/f'coder_packet_{name}.jsonl').open('w',encoding='utf-8') as fh:
            for r in rows: fh.write(json.dumps(r,ensure_ascii=False)+'\n')
        with (HERE/f'coder_form_{name}.csv').open('w',encoding='utf-8',newline='') as fh:
            w=csv.writer(fh)
            w.writerow(['item_id','material_change','gamma_dimensions','authority_locus_present','standing_present','coordination_mechanisms','actor_dimensions','confidence','notes'])
            for r in rows: w.writerow([r['item_id'],'','','','','','','',''])
    with (HERE/'machine_retrieval_key.jsonl').open('w',encoding='utf-8') as fh:
        for r in key_rows: fh.write(json.dumps(r,ensure_ascii=False)+'\n')
    summary={'items':len(packet),'retrieval_candidates':sum(r['origin']=='retrieval_candidate' for r in selected),'retrieval_controls':len(chosen),'per_code':used_per_code,'warning':'The machine key is not a gold standard. Independent coders must not see it before coding.'}
    (HERE/'packet_manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
