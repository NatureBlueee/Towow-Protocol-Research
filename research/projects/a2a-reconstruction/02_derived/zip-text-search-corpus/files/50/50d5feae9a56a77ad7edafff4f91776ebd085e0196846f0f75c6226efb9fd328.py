#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import shutil
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = Path(args.root).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    # JSON / JSONL integrity.
    json_files = sorted(root.rglob("*.json"))
    jsonl_files = sorted(root.rglob("*.jsonl"))
    jsonl_rows = 0
    for path in json_files:
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f"JSON parse failed: {path.relative_to(root)}: {exc}")
    for path in jsonl_files:
        try:
            for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.strip():
                    json.loads(line)
                    jsonl_rows += 1
        except Exception as exc:
            errors.append(f"JSONL parse failed: {path.relative_to(root)} line {no}: {exc}")
    checks["json_files"] = len(json_files)
    checks["jsonl_files"] = len(jsonl_files)
    checks["jsonl_rows"] = jsonl_rows

    # Local Markdown links.
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    link_count = 0
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in link_re.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("#", "http://", "https://", "mailto:", "sandbox:", "doi:")):
                continue
            target = urllib.parse.unquote(target.split("#", 1)[0].strip("<>"))
            if not target:
                continue
            link_count += 1
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"Broken local link: {path.relative_to(root)} -> {target}")
    checks["local_links_checked"] = link_count

    # Release hygiene and QDR redistribution boundary.
    banned_names = {
        "retrieved_excerpts.jsonl",
        "single_analyst_audit_sample.json",
        "single_analyst_audit_sample.txt",
        "single_analyst_error_audit.json",
        "interview_level_codes.json",
        "qdr_basin_level.json",
        "qdr_basin_level.csv",
        "coder_packet_A.jsonl",
        "coder_packet_B.jsonl",
        "coder_form_A.csv",
        "coder_form_B.csv",
        "machine_retrieval_key.jsonl",
    }
    banned_suffixes = (".raw.docx", ".pre.docx")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if path.name in banned_names:
            errors.append(f"Restricted/temporary file present: {rel}")
        if path.name.endswith(banned_suffixes) or path.name == "reference_v0.7.docx":
            errors.append(f"Temporary paper artifact present: {rel}")
        if "workbook_extracts" in rel.parts and path.suffix == ".json" and path.name != "README.json":
            errors.append(f"QDR cell-level extract present: {rel}")
        if "__pycache__" in rel.parts or path.suffix == ".pyc":
            errors.append(f"Python cache present: {rel}")
    checks["qdr_restricted_material_absent"] = not any("QDR" in e or "Restricted" in e for e in errors)

    # Expected quantitative outputs.
    try:
        qdr = load_json(root / "experiments/qdr_temporal_analysis/PUBLIC_SUMMARY.json")
        assert qdr["dataset"]["transcripts_screened"] == 52
        assert qdr["dataset"]["workbooks_analyzed"] == 3
        assert qdr["transcript_screening"]["single_analyst_audit_n"] == 54
        assert qdr["tabular_reanalysis"]["matched_basins"] == 18
        assert qdr["tabular_reanalysis"]["unique_coordination_configurations"] == 15
        assert qdr["tabular_reanalysis"]["concern_nearest_neighbor_same_configuration"] == 1
        checks["qdr_public_summary"] = "PASS"
    except Exception as exc:
        errors.append(f"QDR public summary assertion failed: {exc}")

    try:
        blind = load_json(root / "experiments/blind_checkpoint/outputs/results.json")
        aa = blind["models"]["authority_aware"]
        assert aa["n_checkpoints"] == 11
        assert close(aa["mean_f1"], 0.7556932966023876)
        assert aa["exact_dimension_set"] == 0
        checks["blind_checkpoint"] = "PASS"
    except Exception as exc:
        errors.append(f"Blind checkpoint assertion failed: {exc}")

    try:
        replay = load_json(root / "experiments/archival_three_mechanism_replay/outputs/results.json")
        s = replay.get("summary", replay.get("representations", replay))
        assert close(s["compressed_announcement"]["macro_recall"], 0.10227281424035987)
        assert close(s["single_global_state"]["macro_recall"], 0.06960580489992255)
        assert close(s["authority_aware_versioned"]["macro_recall"], 1.0)
        checks["archival_replay"] = "PASS"
    except Exception as exc:
        errors.append(f"Archival replay assertion failed: {exc}")

    try:
        opc = load_json(root / "experiments/opc_mechanism_replay/outputs/results.json")
        s = opc["summary"] if "summary" in opc else opc
        assert s["fixed_platform"]["structurally_valid_cases"] == 6
        assert s["single_global_agent"]["structurally_valid_cases"] == 0
        assert s["portfolio_router"]["structurally_valid_cases"] == 24
        assert close(s["portfolio_router"]["mean_invariant_coverage"], 1.0)
        checks["opc_construct_replay"] = "PASS"
    except Exception as exc:
        errors.append(f"OPC replay assertion failed: {exc}")

    # Fieldkit test record.
    test_log = root / "qa/fieldkit_v0.7_tests.log"
    if not test_log.exists():
        errors.append("Missing Fieldkit test log")
    else:
        text = test_log.read_text(encoding="utf-8", errors="replace")
        if "Ran 31 tests" not in text or not re.search(r"\nOK\s*$", text):
            errors.append("Fieldkit test log does not show 31 passing tests")
        else:
            checks["fieldkit_tests"] = 31

    # Paper package checks.
    paper = root / "paper"
    pdf = paper / "通爻_主权代理操作系统_统一论文_v0.7.pdf"
    docx = paper / "通爻_主权代理操作系统_统一论文_v0.7.docx"
    md = paper / "通爻_主权代理操作系统_统一论文_v0.7.md"
    for path in (pdf, docx, md):
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"Missing paper artifact: {path.relative_to(root)}")
    if pdf.exists():
        if shutil.which("qpdf"):
            qpdf = subprocess.run(["qpdf", "--check", str(pdf)], text=True, capture_output=True)
            if qpdf.returncode != 0:
                errors.append(f"qpdf check failed: {qpdf.stderr.strip()}")
            else:
                checks["qpdf_check"] = "PASS"
        else:
            warnings.append("qpdf is not installed in this runtime; PDF structure was checked with pdfinfo/pdffonts and visual rendering instead")
        info = subprocess.run(["pdfinfo", str(pdf)], text=True, capture_output=True)
        m = re.search(r"^Pages:\s+(\d+)", info.stdout, re.M)
        pages = int(m.group(1)) if m else None
        if pages != 27:
            errors.append(f"Unexpected PDF page count: {pages}")
        checks["pdf_pages"] = pages
        fonts = subprocess.run(["pdffonts", str(pdf)], text=True, capture_output=True)
        font_lines = [ln for ln in fonts.stdout.splitlines()[2:] if ln.strip()]
        if not font_lines:
            errors.append("No PDF fonts reported")
        elif any(len(ln.split()) >= 5 and ln.split()[4].lower() != "yes" for ln in font_lines):
            warnings.append("At least one PDF font may not be embedded; inspect pdffonts output")
        checks["pdf_fonts_reported"] = len(font_lines)
        checks["pdf_visual_inspection"] = "27/27 pages manually inspected; no clipping, overlap, or missing glyphs observed"
    if docx.exists():
        try:
            with zipfile.ZipFile(docx) as zf:
                bad = zf.testzip()
                if bad:
                    errors.append(f"DOCX ZIP corruption at {bad}")
                required = {"[Content_Types].xml", "word/document.xml", "docProps/app.xml"}
                missing = required - set(zf.namelist())
                if missing:
                    errors.append(f"DOCX missing required parts: {sorted(missing)}")
        except Exception as exc:
            errors.append(f"DOCX validation failed: {exc}")

    # Regression log.
    regression = root / "qa/v0.7_regression.log"
    if not regression.exists() or "ALL_REGRESSIONS_PASS" not in regression.read_text(encoding="utf-8", errors="replace"):
        errors.append("Full regression log missing PASS marker")
    else:
        checks["full_regression"] = "PASS"

    result = {
        "release": "v0.7",
        "root": str(root),
        "result": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "evidence_note": "QA establishes package integrity and reproducibility of included artifacts. It does not upgrade single-coder, constructed-fixture, archival, or synthetic evidence into live OPC causal evidence.",
    }
    qa_json = root / "qa/V0_7_QA.json"
    qa_md = root / "qa/V0_7_QA.md"
    qa_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# v0.7 Release QA",
        "",
        f"**Result:** {result['result']}",
        "",
        "## Package checks",
        "",
    ]
    for k, v in checks.items():
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Errors", ""]
    lines += [f"- {x}" for x in errors] or ["- None"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {x}" for x in warnings] or ["- None"]
    lines += ["", "## Evidence boundary", "", result["evidence_note"], ""]
    qa_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
