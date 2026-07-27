#!/usr/bin/env python3
"""Extract selected QDR workbook ranges with artifact_tool.

This preserves source values without using pandas/openpyxl and emits JSON suitable
for transparent downstream analysis. The source workbooks remain outside the
release because the QDR data agreement governs redistribution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from artifact_tool import Blob, SpreadsheetFile

SOURCE = Path('/mnt/data/qdr_milman/TabularData')
OUT = Path(__file__).resolve().parent / 'workbook_extracts'
OUT.mkdir(parents=True, exist_ok=True)

SELECTIONS = {
    'Milman_BasinCoordinationConcernsAnalysis.xlsx': {
        'Coding': 'A1:C74',
        'Basin Concerns': 'A1:AC26',
    },
    'Milman_BasinCoordinationInstitutionsAnalysis.xlsx': {
        'Table of Contents': 'A1:E17',
        'i. Introduction': 'A1:C5',
        '1. Organizational Form': 'A1:R27',
        '2. Platform for Communication': 'A1:O27',
        '3. Boundary Spanning Agents': 'A1:L29',
        '4. Policy Evaluation': 'A1:L27',
        '5. Planning Review & Approval': 'A1:O27',
        '6. Data Summary Table': 'A1:H21',
    },
    'Milman_BasinGroundwaterSustainabilityPlanningCoordinationAnalysis.xlsx': {
        'Readme': 'A1:D34',
        'Summary of Numerical Data': 'A1:X22',
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def clean(values: list[list[Any]]) -> list[list[Any]]:
    # artifact_tool already returns JSON-compatible primitives for these sheets.
    return [[cell for cell in row] for row in values]


def main() -> None:
    manifest: list[dict[str, Any]] = []
    for filename, sheets in SELECTIONS.items():
        source = SOURCE / filename
        wb = SpreadsheetFile.import_xlsx(Blob.load(str(source)))
        payload: dict[str, Any] = {
            'source_filename': filename,
            'source_sha256': sha256(source),
            'sheets': {},
        }
        for sheet_name, address in sheets.items():
            sheet = wb.worksheets.get_item(sheet_name)
            values = clean(sheet.get_range(address).values)
            payload['sheets'][sheet_name] = {
                'address': address,
                'rows': len(values),
                'columns': max((len(row) for row in values), default=0),
                'values': values,
            }
        target = OUT / f'{source.stem}.json'
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        manifest.append({
            'source': str(source),
            'filename': filename,
            'sha256': payload['source_sha256'],
            'extract': str(target.relative_to(Path(__file__).resolve().parents[2])),
            'sheet_count': len(sheets),
        })
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'workbooks': len(manifest), 'output': str(OUT)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
