#!/usr/bin/env python3
"""Retrospective, time-censored structural diagnosis.

At each checkpoint the diagnostic sees only prior coded events. It predicts which
Relation-Schema dimensions are likely to be implicated by the next material event.
This is a historical stress test, not a claim of real-world forecasting.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[0] / 'R7P_public_trace_extended' / 'coded_events.jsonl'
OUT = HERE / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
ALL_DIMS = {'R','V','T','A','E','D','O'}
STABLE = {'STABLE','COMPLETE','READY'}


def load() -> dict[str, list[dict[str, Any]]]:
    cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in SOURCE.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            cases[row['case_id']].append(row)
    return cases


def next_material(events: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
    for row in events[index+1:]:
        if row.get('material_schema_change'):
            return row
    return None


def jaccard(pred: set[str], truth: set[str]) -> float:
    return len(pred & truth) / len(pred | truth) if pred | truth else 1.0


def precision(pred: set[str], truth: set[str]) -> float:
    return len(pred & truth) / len(pred) if pred else (1.0 if not truth else 0.0)


def recall(pred: set[str], truth: set[str]) -> float:
    return len(pred & truth) / len(truth) if truth else 1.0


def f1(p: float, r: float) -> float:
    return 2*p*r/(p+r) if p+r else 0.0


def authority_aware(prior: list[dict[str, Any]]) -> tuple[set[str], list[str]]:
    last = prior[-1]
    s = last.get('stability_dimensions', {})
    predicted: set[str] = set()
    reasons: list[str] = []

    if s.get('technical_operational') not in STABLE:
        predicted |= {'V','T','E'}
        reasons.append('technical/operational stability not closed')
    if s.get('authority_governance') not in STABLE:
        predicted |= {'R','A','T'}
        reasons.append('authority/governance stability not closed')
    if s.get('epistemic_assurance') not in STABLE:
        predicted |= {'E','O'}
        reasons.append('assurance not closed')
    norm = s.get('normative_legitimacy')
    if norm in {'OPEN','FAILED','CONDITIONAL'}:
        predicted |= {'R','A','O'}
        reasons.append('standing/legitimacy not closed')
    if s.get('economic_resource') in {'OPEN','FAILED'}:
        predicted |= {'V','T','O'}
        reasons.append('resource viability open or failed')
    if last.get('declared_enacted_gap'):
        predicted |= {'T','A','E'}
        reasons.append('declared/enacted gap observed')
    if last.get('reopen_triggers'):
        predicted |= {'T','E','O'}
        reasons.append('explicit reopen trigger remains')
    standing = ' '.join(last.get('standing_types', []))
    if any(token in standing for token in ('PUBLIC','REGULATORY','AFFECTED','CHALLENGE','ASSURANCE')):
        predicted |= {'R','A','O'}
        reasons.append('external standing or challenge locus active')
    frame = str(last.get('institutional_frame_sufficiency',''))
    if any(token in frame for token in ('PARTIAL','CONTESTED','INCOMPLETE','MANDATED_ENDS')):
        predicted |= {'R','A','T','O'}
        reasons.append('institutional frame is only partially sufficient')

    # Avoid a vacuous all-dimensions forecast. Keep the dimensions with the
    # strongest unresolved support when every dimension was added.
    if predicted == ALL_DIMS:
        counts = Counter()
        maps = {
            'technical_operational': {'V','T','E'},
            'authority_governance': {'R','A','T'},
            'epistemic_assurance': {'E','O'},
            'normative_legitimacy': {'R','A','O'},
            'economic_resource': {'V','T','O'},
        }
        for key,dims in maps.items():
            if s.get(key) not in STABLE and s.get(key) != 'NOT_ASSESSED':
                for dim in dims: counts[dim]+=1
        predicted = {dim for dim,count in counts.items() if count >= 2}
        if not predicted:
            predicted = set(counts.most_common(4)[i][0] for i in range(min(4,len(counts))))
    return predicted, reasons


def model_predictions(prior: list[dict[str, Any]]) -> dict[str, set[str]]:
    last_dims = set(prior[-1].get('schema_dimensions', []))
    freq = Counter(dim for row in prior for dim in row.get('schema_dimensions', []))
    top = {dim for dim,count in freq.items() if count == max(freq.values())} if freq else set()
    aware,_ = authority_aware(prior)
    return {
        'no_change': set(),
        'last_event': last_dims,
        'prior_mode': top,
        'authority_aware': aware,
    }


def main() -> None:
    cases = load()
    rows: list[dict[str, Any]] = []
    fractions = (0.30,0.50,0.70)
    for case_id, events in cases.items():
        n = len(events)
        used: set[int] = set()
        for frac in fractions:
            idx = min(n-2, max(0, round((n-1)*frac)))
            if idx in used: continue
            used.add(idx)
            nxt = next_material(events, idx)
            if not nxt: continue
            prior = events[:idx+1]
            truth = set(nxt.get('schema_dimensions', []))
            aware,reasons = authority_aware(prior)
            for model,pred in model_predictions(prior).items():
                p=precision(pred,truth); r=recall(pred,truth)
                rows.append({
                    'case_id': case_id,
                    'checkpoint_fraction': frac,
                    'checkpoint_event_id': events[idx]['event_id'],
                    'next_material_event_id': nxt['event_id'],
                    'next_material_event_type': nxt['event_type'],
                    'model': model,
                    'predicted_dimensions': sorted(pred),
                    'true_dimensions': sorted(truth),
                    'precision': p,
                    'recall': r,
                    'f1': f1(p,r),
                    'jaccard': jaccard(pred,truth),
                    'diagnostic_reasons': reasons if model=='authority_aware' else [],
                })

    summaries: dict[str, dict[str, Any]] = {}
    for model in sorted({r['model'] for r in rows}):
        subset=[r for r in rows if r['model']==model]
        summaries[model]={
            'n_checkpoints': len(subset),
            'mean_precision': sum(r['precision'] for r in subset)/len(subset),
            'mean_recall': sum(r['recall'] for r in subset)/len(subset),
            'mean_f1': sum(r['f1'] for r in subset)/len(subset),
            'mean_jaccard': sum(r['jaccard'] for r in subset)/len(subset),
            'exact_dimension_set': sum(set(r['predicted_dimensions'])==set(r['true_dimensions']) for r in subset),
        }
    result={
        'method':'time-censored retrospective structural diagnosis over seven public coded event streams',
        'checkpoints': len(rows)//4,
        'models': summaries,
        'rows': rows,
        'limitations':[
            'Coded histories were reconstructed retrospectively and may contain selection bias.',
            'The authority-aware rules were designed after the Relation Schema, not learned on an independent corpus.',
            'The test evaluates structural issue localization, not commercial value, human acceptance, or future event prediction.',
            'All seven cases concern organizations or institutions; OPC transfer remains a design hypothesis.'
        ]
    }
    (OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checkpoints':result['checkpoints'],'models':summaries},ensure_ascii=False))

if __name__=='__main__': main()
