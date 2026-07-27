#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
EXTRACTS = HERE.parents[1] / 'evidence' / 'qdr' / 'workbook_extracts'
OUT = HERE / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)

GROUPS = {
    'knowledge': (1, 4, 13),
    'policy_goals': (4, 10, 18),
    'policy_actions': (10, 13, 15),
    'monitoring': (13, 17, 18),
    'oversight': (17, 24, 26),
}
MECH_ORD = {'Ah': 0, 'F': 1, 'C': 2}


def load(name: str) -> dict[str, Any]:
    return json.loads((EXTRACTS / name).read_text(encoding='utf-8'))


def expand_basin_ids(value: Any) -> list[int]:
    if isinstance(value, (int, float)):
        return [int(value)]
    return [int(x.strip()) for x in str(value).split(',') if x.strip()]


def mean(xs: list[float]) -> float:
    return statistics.mean(xs) if xs else float('nan')


def spearman(xs: list[float], ys: list[float]) -> float:
    # Average-rank implementation, sufficient for this small descriptive analysis.
    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i + 1
            while j < len(order) and values[order[j]] == values[order[i]]:
                j += 1
            r = (i + 1 + j) / 2
            for k in range(i, j):
                out[order[k]] = r
            i = j
        return out
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a-mx)*(b-my) for a,b in zip(rx, ry))
    den = math.sqrt(sum((a-mx)**2 for a in rx) * sum((b-my)**2 for b in ry))
    return num/den if den else float('nan')


def main() -> None:
    inst = load('Milman_BasinCoordinationInstitutionsAnalysis.json')
    planning = load('Milman_BasinGroundwaterSustainabilityPlanningCoordinationAnalysis.json')
    concerns = load('Milman_BasinCoordinationConcernsAnalysis.json')

    # Institutional configurations for basins 1..18.
    config_values = inst['sheets']['6. Data Summary Table']['values']
    mechanisms: dict[int, dict[str, str]] = {}
    for row in config_values[6:]:
        if row[2] in (None, ''):
            continue
        for basin in expand_basin_ids(row[2]):
            mechanisms[basin] = {
                'organizational_form': str(row[3]),
                'communication': str(row[4]),
                'boundary_spanning': str(row[5]),
                'evaluation': str(row[6]),
                'approval': str(row[7]),
            }

    # Outcome scores for basins 1..19.
    plan_values = planning['sheets']['Summary of Numerical Data']['values']
    outcomes: dict[int, dict[str, Any]] = {}
    headers = plan_values[1]
    for row in plan_values[3:]:
        if not row[0]:
            continue
        basin = int(str(row[0]).split('#')[-1])
        scores = [float(x) for x in row[1:24]]
        group_scores = {}
        for name, (start, end, max_points) in GROUPS.items():
            raw = sum(float(row[i]) for i in range(start, end))
            group_scores[name] = {'raw': raw, 'max': max_points, 'normalized': raw/max_points}
        outcomes[basin] = {
            'scores': dict(zip(headers[1:24], scores)),
            'total_raw': sum(scores),
            'total_max': 90,
            'total_normalized': sum(scores)/90,
            'groups': group_scores,
        }

    # Aggregate concern flags across multiple rows/plans per basin.
    concern_values = concerns['sheets']['Basin Concerns']['values']
    concern_flags: dict[int, dict[str, int]] = defaultdict(lambda: {'autonomy':0,'distribution':0,'defection':0,'compliance':0})
    evidence_counts: dict[int, dict[str, int]] = defaultdict(lambda: {'interviews':0,'meetings':0,'documents':0})
    for row in concern_values[7:]:
        if row[1] in (None, ''):
            continue
        basin = int(row[1])
        concern_flags[basin]['autonomy'] = max(concern_flags[basin]['autonomy'], int(row[3] or 0))
        concern_flags[basin]['distribution'] = max(concern_flags[basin]['distribution'], int(row[9] or 0))
        concern_flags[basin]['defection'] = max(concern_flags[basin]['defection'], int(row[15] or 0))
        concern_flags[basin]['compliance'] = max(concern_flags[basin]['compliance'], int(row[20] or 0))
        evidence_counts[basin]['interviews'] += int(row[26] or 0)
        evidence_counts[basin]['meetings'] += int(row[27] or 0)
        evidence_counts[basin]['documents'] += int(row[28] or 0)

    matched = sorted(set(mechanisms) & set(outcomes))
    basin_rows: list[dict[str, Any]] = []
    for basin in matched:
        row: dict[str, Any] = {'basin': basin, **mechanisms[basin], **concern_flags[basin]}
        row['outcome_total'] = outcomes[basin]['total_normalized']
        for group, score in outcomes[basin]['groups'].items():
            row[f'outcome_{group}'] = score['normalized']
        row['evidence_interviews'] = evidence_counts[basin]['interviews']
        row['evidence_meetings'] = evidence_counts[basin]['meetings']
        row['evidence_documents'] = evidence_counts[basin]['documents']
        row['configuration'] = '|'.join([
            row['organizational_form'], row['communication'], row['boundary_spanning'], row['evaluation'], row['approval']
        ])
        basin_rows.append(row)

    summaries: dict[str, Any] = {}
    for field in ['organizational_form','communication','boundary_spanning','evaluation','approval']:
        groups: dict[str, list[float]] = defaultdict(list)
        for row in basin_rows:
            groups[row[field]].append(row['outcome_total'])
        summaries[field] = {
            key: {'n': len(vals), 'mean_total_outcome': mean(vals), 'min': min(vals), 'max': max(vals)}
            for key, vals in sorted(groups.items())
        }

    ordinal_correlations = {}
    for field in ['communication','boundary_spanning','evaluation','approval']:
        x = [MECH_ORD[row[field]] for row in basin_rows]
        ordinal_correlations[field] = {
            'total': spearman(x, [row['outcome_total'] for row in basin_rows]),
            **{g: spearman(x, [row[f'outcome_{g}'] for row in basin_rows]) for g in GROUPS},
            'warning': 'Ah/F/C are treated as a heuristic ordinal scale solely for descriptive stress-testing; the original codebook defines distinct configurations, not a universal maturity ladder.'
        }

    concern_combinations = Counter(
        ''.join(k[0].upper() for k,v in [('autonomy',r['autonomy']),('distribution',r['distribution']),('defection',r['defection']),('compliance',r['compliance'])] if v)
        or 'NONE'
        for r in basin_rows
    )
    configurations = Counter(row['configuration'] for row in basin_rows)

    # Leave-one-out nearest concern profile: how often the best outcome comes from
    # the same mechanism as a concern-nearest basin. This is not a causal model;
    # it tests whether concern profiles alone determine mechanism choice.
    loo = []
    for target in basin_rows:
        candidates = [r for r in basin_rows if r['basin'] != target['basin']]
        def dist(r: dict[str, Any]) -> int:
            return sum(int(r[c] != target[c]) for c in ['autonomy','distribution','defection','compliance'])
        min_dist = min(dist(r) for r in candidates)
        nearest = [r for r in candidates if dist(r) == min_dist]
        best = max(nearest, key=lambda r: r['outcome_total'])
        loo.append({
            'basin': target['basin'],
            'nearest_distance': min_dist,
            'actual_configuration': target['configuration'],
            'suggested_configuration': best['configuration'],
            'same_configuration': target['configuration'] == best['configuration'],
            'actual_outcome': target['outcome_total'],
            'reference_outcome': best['outcome_total'],
        })

    result = {
        'matched_basins': len(matched),
        'unique_configurations': len(configurations),
        'configuration_counts': dict(configurations),
        'concern_combination_counts': dict(concern_combinations),
        'mechanism_outcome_summaries': summaries,
        'heuristic_ordinal_correlations': ordinal_correlations,
        'concern_nearest_leave_one_out': {
            'same_configuration_count': sum(x['same_configuration'] for x in loo),
            'n': len(loo),
            'rows': loo,
            'interpretation': 'Concern profile alone rarely reconstructs the observed institutional configuration; mechanism selection requires additional context such as authority topology, resources, history and implementation needs.'
        },
        'top_outcomes': sorted([
            {'basin': r['basin'], 'outcome_total': r['outcome_total'], 'configuration': r['configuration']}
            for r in basin_rows
        ], key=lambda x: -x['outcome_total']),
        'limitations': [
            'Descriptive analysis of a small purposive set; no causal identification.',
            'Mechanism categories are not assumed to be ordinal, despite one explicit heuristic stress test.',
            'Basin-level aggregation can conceal within-basin disagreement and multiple plans.',
            'The QDR setting is intergovernmental groundwater governance, not OPC; transfer is theoretical and must be tested separately.'
        ]
    }
    (OUT/'qdr_tabular_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT/'qdr_basin_level.json').write_text(json.dumps(basin_rows, ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUT/'qdr_basin_level.csv').open('w', encoding='utf-8', newline='') as fh:
        fields = list(basin_rows[0])
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader(); w.writerows(basin_rows)
    print(json.dumps({
        'matched_basins': len(matched),
        'unique_configurations': len(configurations),
        'same_config_from_concerns': sum(x['same_configuration'] for x in loo),
        'output': str(OUT/'qdr_tabular_results.json')
    }))


if __name__ == '__main__':
    main()
