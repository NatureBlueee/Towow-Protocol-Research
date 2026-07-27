#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
SOURCE_TEXT = Path('/mnt/data/qdr_milman/text')
CODEBOOK_PATH = HERE / 'codebook.json'
OUT = HERE / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)

SPEAKER_RE = re.compile(
    r'(?im)^(Interviewer|Interviewee|Respondent|Participant)(?:\s*\[[^\]]*\])?\s*:?\s*'
)
SENTENCE_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z\[])|\n{2,}')


@dataclass
class Transcript:
    number: int
    date: str
    wave: str
    path: Path
    sha256: str
    word_count: int
    interviewee_text: str
    utterances: list[str]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def normalize(text: str) -> str:
    text = text.replace('\f', '\n')
    text = re.sub(r'Page \d+ of \d+', ' ', text, flags=re.I)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_utterances(text: str) -> list[tuple[str, str]]:
    matches = list(SPEAKER_RE.finditer(text.replace('\f', '\n')))
    if not matches:
        return [('unknown', normalize(text))]
    rows: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = normalize(text[start:end])
        if body:
            speaker = match.group(1).lower()
            if speaker in {'respondent', 'participant'}:
                speaker = 'interviewee'
            rows.append((speaker, body))
    return rows


def load_transcripts() -> list[Transcript]:
    rows: list[Transcript] = []
    for path in sorted(SOURCE_TEXT.glob('Milman_Interview_[0-9][0-9]_*.txt')):
        m = re.search(r'Interview_(\d+)_([0-9]{8})', path.name)
        if not m:
            continue
        number = int(m.group(1))
        date_raw = m.group(2)
        date = datetime.strptime(date_raw, '%Y%m%d').date().isoformat()
        wave = 'formation_2019Q1' if date_raw <= '20190331' else 'planning_2019Q4_2020'
        raw = path.read_text(encoding='utf-8', errors='replace')
        parsed = parse_utterances(raw)
        interviewee = [body for speaker, body in parsed if speaker == 'interviewee']
        # Some files use unusual speaker labels. Retain the full text if less than 5% parsed.
        joined = ' '.join(interviewee)
        if len(joined) < max(300, len(raw) * 0.05):
            joined = normalize(raw)
            interviewee = [joined]
        rows.append(Transcript(
            number=number,
            date=date,
            wave=wave,
            path=path,
            sha256=sha256(path),
            word_count=len(re.findall(r"\b[\w'-]+\b", joined)),
            interviewee_text=joined,
            utterances=interviewee,
        ))
    return rows


def compile_patterns(terms: Iterable[str]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for term in terms:
        if term.startswith('re:'):
            patterns.append(re.compile(term[3:], re.I))
            continue
        # Terms ending with a fragment such as "delegat" intentionally use prefix matching.
        escaped = re.escape(term)
        if term and term[-1].isalpha() and term in {'autonom', 'inequit', 'delegat', 'mediat', 'arbitrat'}:
            escaped += r'\w*'
        patterns.append(re.compile(r'(?i)(?<!\w)' + escaped + r'(?!\w)'))
    return patterns


def excerpt_units(transcript: Transcript) -> list[str]:
    units: list[str] = []
    for utterance in transcript.utterances:
        # Keep utterances as the primary unit, then split only very long stretches.
        if len(utterance) <= 900:
            units.append(utterance)
            continue
        sentences = [s.strip() for s in SENTENCE_RE.split(utterance) if s.strip()]
        chunk: list[str] = []
        chars = 0
        for sent in sentences:
            if chunk and chars + len(sent) > 700:
                units.append(' '.join(chunk))
                chunk = []
                chars = 0
            chunk.append(sent)
            chars += len(sent) + 1
        if chunk:
            units.append(' '.join(chunk))
    return units


def trim_excerpt(text: str, match_start: int, width: int = 380) -> str:
    start = max(0, match_start - width // 3)
    end = min(len(text), start + width)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = '…' + snippet
    if end < len(text):
        snippet += '…'
    return snippet


def kappa(binary_a: list[int], binary_b: list[int]) -> float:
    if len(binary_a) != len(binary_b) or not binary_a:
        return float('nan')
    n = len(binary_a)
    agree = sum(a == b for a, b in zip(binary_a, binary_b)) / n
    pa1 = sum(binary_a) / n
    pb1 = sum(binary_b) / n
    expected = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(agree, 1.0) else 0.0
    return (agree - expected) / (1 - expected)


def main() -> None:
    codebook = json.loads(CODEBOOK_PATH.read_text(encoding='utf-8'))
    flattened: dict[str, tuple[str, list[re.Pattern[str]]]] = {}
    for family in ('native_concerns', 'coordination_mechanisms', 'agentic_actor_dimensions'):
        for code, terms in codebook[family].items():
            flattened[code] = (family, compile_patterns(terms))

    transcripts = load_transcripts()
    assert len(transcripts) == 52, f'Expected 52 transcripts, found {len(transcripts)}'

    interview_rows: list[dict] = []
    hit_rows: list[dict] = []
    code_interviews: dict[str, set[int]] = defaultdict(set)
    code_hits: Counter[str] = Counter()
    wave_counts: dict[str, Counter[str]] = defaultdict(Counter)
    cooccurrence: dict[tuple[str, str], int] = Counter()

    for tr in transcripts:
        units = excerpt_units(tr)
        presence: dict[str, int] = {}
        interview_hits: dict[str, int] = Counter()
        for unit_idx, unit in enumerate(units):
            matched_codes: list[str] = []
            for code, (family, patterns) in flattened.items():
                matches = [m for pattern in patterns for m in pattern.finditer(unit)]
                if not matches:
                    continue
                matched_codes.append(code)
                interview_hits[code] += len(matches)
                code_hits[code] += len(matches)
                code_interviews[code].add(tr.number)
                first = min(matches, key=lambda m: m.start())
                hit_rows.append({
                    'interview': tr.number,
                    'date': tr.date,
                    'wave': tr.wave,
                    'family': family,
                    'code': code,
                    'unit_index': unit_idx,
                    'match_count': len(matches),
                    'excerpt': trim_excerpt(unit, first.start()),
                })
            matched_codes = sorted(set(matched_codes))
            for i, left in enumerate(matched_codes):
                for right in matched_codes[i + 1:]:
                    cooccurrence[(left, right)] += 1
        for code in flattened:
            presence[code] = int(code in interview_hits)
            if presence[code]:
                wave_counts[tr.wave][code] += 1
        interview_rows.append({
            'interview': tr.number,
            'date': tr.date,
            'wave': tr.wave,
            'source_filename': tr.path.name,
            'source_sha256': tr.sha256,
            'word_count': tr.word_count,
            'utterance_count': len(tr.utterances),
            'code_presence': presence,
            'code_hits': dict(interview_hits),
        })

    wave_sizes = Counter(tr.wave for tr in transcripts)
    summary_codes = {}
    for code, (family, _) in flattened.items():
        prevalence = len(code_interviews[code]) / len(transcripts)
        wave = {
            w: {
                'interviews': wave_counts[w][code],
                'n': wave_sizes[w],
                'prevalence': wave_counts[w][code] / wave_sizes[w],
            }
            for w in sorted(wave_sizes)
        }
        summary_codes[code] = {
            'family': family,
            'interviews_with_code': len(code_interviews[code]),
            'interview_prevalence': prevalence,
            'screening_hits': code_hits[code],
            'wave': wave,
            'late_minus_early_prevalence': wave['planning_2019Q4_2020']['prevalence'] - wave['formation_2019Q1']['prevalence'],
        }

    # Cross-lens agreement is a stress test, not inter-coder reliability.
    # A native concern is treated as a material concern signal; the structural lens
    # flags materiality when authority, standing, resources, formalization, effect,
    # adaptation or recourse appears.
    native_codes = list(codebook['native_concerns'])
    structural_codes = [
        'authority_scope', 'standing_representation', 'capacity_resource',
        'commitment_formalization', 'effect_implementation', 'reopen_adaptation',
        'dispute_exit_recourse',
    ]
    native_binary = [int(any(row['code_presence'][c] for c in native_codes)) for row in interview_rows]
    structural_binary = [int(any(row['code_presence'][c] for c in structural_codes)) for row in interview_rows]

    top_excerpts: dict[str, list[dict]] = {}
    for code in flattened:
        candidates = [row for row in hit_rows if row['code'] == code]
        candidates.sort(key=lambda r: (-r['match_count'], len(r['excerpt']), r['interview']))
        selected: list[dict] = []
        seen_interviews: set[int] = set()
        for row in candidates:
            if row['interview'] in seen_interviews:
                continue
            selected.append(row)
            seen_interviews.add(row['interview'])
            if len(selected) >= 8:
                break
        top_excerpts[code] = selected

    result = {
        'dataset': {
            'title': 'Ascertaining Intergovernmental Coordination Mechanisms',
            'doi': '10.5064/F6QHVGUI',
            'transcripts': len(transcripts),
            'total_screened_words': sum(t.word_count for t in transcripts),
            'waves': dict(wave_sizes),
            'method_limit': 'Dictionary-based screening of interviewee utterances. Counts indicate retrieval signals, not validated qualitative prevalence or causal effects.',
        },
        'codes': summary_codes,
        'cross_lens_stress_test': {
            'unit': 'interview',
            'native_material_signal_positive': sum(native_binary),
            'structural_material_signal_positive': sum(structural_binary),
            'cohen_kappa': kappa(native_binary, structural_binary),
            'warning': 'This compares two operational lenses executed by one analysis pipeline; it is not independent human inter-coder reliability.'
        },
        'top_cooccurrences': [
            {'left': left, 'right': right, 'units': count}
            for (left, right), count in sorted(cooccurrence.items(), key=lambda x: (-x[1], x[0]))[:60]
        ],
        'top_excerpts': top_excerpts,
    }

    (OUT / 'qdr_screening_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'interview_level_codes.json').write_text(json.dumps(interview_rows, ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUT / 'retrieved_excerpts.jsonl').open('w', encoding='utf-8') as fh:
        for row in hit_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')

    with (OUT / 'code_prevalence.csv').open('w', encoding='utf-8', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['code', 'family', 'interviews_with_code', 'prevalence', 'screening_hits', 'early_prevalence', 'late_prevalence', 'late_minus_early'])
        for code, row in sorted(summary_codes.items(), key=lambda x: (-x[1]['interview_prevalence'], x[0])):
            writer.writerow([
                code, row['family'], row['interviews_with_code'], f"{row['interview_prevalence']:.6f}", row['screening_hits'],
                f"{row['wave']['formation_2019Q1']['prevalence']:.6f}",
                f"{row['wave']['planning_2019Q4_2020']['prevalence']:.6f}",
                f"{row['late_minus_early_prevalence']:.6f}",
            ])

    print(json.dumps({
        'transcripts': len(transcripts),
        'words': result['dataset']['total_screened_words'],
        'hits': len(hit_rows),
        'output': str(OUT),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
