#!/usr/bin/env python3
"""Representational replay over the seven public institutional traces.

This is a structural information-loss experiment, not a model-performance or
real-world-value benchmark. All three representations consume the same coded
history. The authority-aware representation is expected to preserve the fields
that its schema explicitly carries; the useful result is identifying exactly
what the lossy alternatives cannot answer.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'R7P_public_trace_extended'/'coded_events.jsonl'
DIMS=set('RVT AEDO'.replace(' ',''))


def load_events() -> list[dict[str,Any]]:
    return [json.loads(line) for line in SOURCE.read_text(encoding='utf-8').splitlines() if line.strip()]


def outcome_layer(event: dict[str,Any]) -> str | None:
    text=(str(event.get('event_type',''))+' '+str(event.get('stance',''))).upper()
    # More specific states first.
    if any(k in text for k in ('ACCEPT','SETTLED','ADJUDICATED')):
        return 'ACCEPTANCE_OR_SETTLEMENT'
    if 'ADOPT' in text:
        return 'ADOPTION'
    if any(k in text for k in ('EFFECT','PERFORMED','OPERATION')):
        return 'EFFECT_OR_OPERATION'
    if any(k in text for k in ('COMMIT','AWARD','MANDATE')):
        return 'COMMITMENT_OR_MANDATE'
    return None


def gold_facts(events:list[dict[str,Any]]) -> dict[str,set[str]]:
    facts: dict[str,set[str]]=defaultdict(set)
    for e in events:
        if e.get('material_schema_change'):
            facts['material_events'].add(e['event_id'])
        if e.get('critical_turn'):
            facts['critical_turns'].add(e['event_id'])
        for d in e.get('schema_dimensions',[]):
            facts['dimension_links'].add(f"{e['event_id']}::{d}")
        if e.get('authority_locus'):
            facts['authority_links'].add(f"{e['event_id']}::{e['authority_locus']}")
        for s in e.get('standing_types',[]):
            facts['standing_links'].add(f"{e['event_id']}::{s}")
        if e.get('relation_version'):
            facts['version_links'].add(f"{e['event_id']}::{e['relation_version']}")
        for r in e.get('reopen_triggers',[]):
            facts['reopen_links'].add(f"{e['event_id']}::{r}")
        layer=outcome_layer(e)
        if layer:
            facts['outcome_links'].add(f"{e['event_id']}::{layer}")
        if e.get('declared_enacted_gap'):
            facts['enactment_gaps'].add(e['event_id'])
    return facts


def compressed_announcement(events:list[dict[str,Any]]) -> dict[str,set[str]]:
    """Keep only what the coded compressed stream says is publicly visible."""
    facts: dict[str,set[str]]=defaultdict(set)
    for e in events:
        vis=e.get('compressed_stream_visibility')
        if vis not in ('FULL','PARTIAL'):
            continue
        # The announcement may preserve the existence of an outcome/turn but not
        # the full formative path or local authority topology.
        if e.get('material_schema_change'):
            facts['material_events'].add(e['event_id'])
        if e.get('critical_turn'):
            facts['critical_turns'].add(e['event_id'])
        for d in e.get('compressed_stream_visible_dimensions',[]):
            facts['dimension_links'].add(f"{e['event_id']}::{d}")
        layer=outcome_layer(e)
        if layer:
            facts['outcome_links'].add(f"{e['event_id']}::{layer}")
        # Only full visibility keeps the named actor, and even then this is not
        # treated as a verified authority locus unless the archive says so.
        if vis=='FULL' and e.get('authority_locus'):
            facts['authority_links'].add(f"{e['event_id']}::{e['authority_locus']}")
    return facts


def single_global_state(events:list[dict[str,Any]]) -> dict[str,set[str]]:
    """Merge each case into a mutable global state and discard historical versions.

    It can keep the latest value of each dimension and final outcome, but cannot
    answer which local authority changed what, which standing existed, or how a
    prior relation version was reopened.
    """
    facts: dict[str,set[str]]=defaultdict(set)
    by_case: dict[str,list[dict[str,Any]]]=defaultdict(list)
    for e in events:
        by_case[e['case_id']].append(e)
    for case,seq in by_case.items():
        seq=sorted(seq,key=lambda e:(e.get('event_date',''),e['event_id']))
        latest_by_dim:dict[str,dict[str,Any]]={}
        for e in seq:
            for d in e.get('schema_dimensions',[]):
                latest_by_dim[d]=e
        for d,e in latest_by_dim.items():
            facts['dimension_links'].add(f"{e['event_id']}::{d}")
        final=seq[-1]
        if final.get('material_schema_change'):
            facts['material_events'].add(final['event_id'])
        if final.get('critical_turn'):
            facts['critical_turns'].add(final['event_id'])
        layer=outcome_layer(final)
        if layer:
            facts['outcome_links'].add(f"{final['event_id']}::{layer}")
        # Global state records a generic controller rather than the historical
        # locus; this intentionally cannot match gold authority facts.
        facts['authority_links'].add(f"{final['event_id']}::GLOBAL_CONTROLLER")
        if final.get('declared_enacted_gap'):
            facts['enactment_gaps'].add(final['event_id'])
    return facts


def authority_aware_versioned(events:list[dict[str,Any]]) -> dict[str,set[str]]:
    """Replay the fields of the authority-aware versioned event schema."""
    return gold_facts(events)


def score(pred:dict[str,set[str]],gold:dict[str,set[str]]) -> dict[str,Any]:
    per={}
    categories=sorted(gold)
    for c in categories:
        g=gold[c]; p=pred.get(c,set())
        tp=len(g&p)
        precision=tp/len(p) if p else (1.0 if not g else 0.0)
        recall=tp/len(g) if g else 1.0
        f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
        per[c]={'gold':len(g),'predicted':len(p),'true_positive':tp,'precision':precision,'recall':recall,'f1':f1}
    return {
        'macro_recall':mean(v['recall'] for v in per.values()),
        'macro_f1':mean(v['f1'] for v in per.values()),
        'per_category':per,
    }


def case_query_coverage(events:list[dict[str,Any]],rep:dict[str,set[str]]) -> dict[str,Any]:
    """Score whether a representation can answer seven structural query families.

    Query families correspond to material change, critical turn, changed
    dimension, authority locus, standing, relation version, and reopen trigger.
    """
    by_case=defaultdict(list)
    for e in events: by_case[e['case_id']].append(e)
    categories=['material_events','critical_turns','dimension_links','authority_links','standing_links','version_links','reopen_links']
    rows=[]
    for case,seq in sorted(by_case.items()):
        g=gold_facts(seq)
        vals={}
        for c in categories:
            target=g.get(c,set())
            if not target:
                vals[c]=1.0
            else:
                vals[c]=len(target & rep.get(c,set()))/len(target)
        rows.append({'case_id':case,**vals,'mean_query_coverage':mean(vals.values())})
    return {'rows':rows,'mean_case_query_coverage':mean(r['mean_query_coverage'] for r in rows)}


def main():
    events=load_events(); gold=gold_facts(events)
    reps={
        'compressed_announcement':compressed_announcement(events),
        'single_global_state':single_global_state(events),
        'authority_aware_versioned':authority_aware_versioned(events),
    }
    result={
        'event_count':len(events),
        'case_count':len(set(e['case_id'] for e in events)),
        'status':'representational information-loss test on retrospectively coded public histories',
        'representations':{},
        'limitations':[
            'The authority-aware representation uses the same schema as the coded source and therefore tests preservation, not independent predictive superiority.',
            'The compressed and global-state baselines are explicit abstractions, not best commercial systems or expert analysts.',
            'Public histories omit private deliberation and OPC-specific behavior; no result is a transaction, adoption, or business-value estimate.'
        ]
    }
    for name,rep in reps.items():
        result['representations'][name]={
            **score(rep,gold),
            'query_coverage':case_query_coverage(events,rep),
            'fact_counts':{k:len(v) for k,v in rep.items()},
        }
    out=HERE/'outputs'; out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:{'macro_recall':v['macro_recall'],'macro_f1':v['macro_f1'],'mean_case_query_coverage':v['query_coverage']['mean_case_query_coverage']} for k,v in result['representations'].items()},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
