from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_json() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"JSON {path.relative_to(ROOT)}: {exc}")
    for path in sorted(ROOT.rglob("*.jsonl")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except Exception as exc:
                errors.append(f"JSONL {path.relative_to(ROOT)}:{i}: {exc}")
    return errors


LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def check_markdown_links() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = raw.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#", "sandbox:", "plugin:")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(f"LINK {path.relative_to(ROOT)} -> escapes root: {raw}")
                continue
            if not resolved.exists():
                errors.append(f"LINK {path.relative_to(ROOT)} -> missing: {raw}")
    return errors


def check_release_invariants() -> list[str]:
    errors: list[str] = []
    ontology = json.loads((ROOT / "experiments/ontology_reduction/results.json").read_text(encoding="utf-8"))
    if ontology["scenario_count"] != 50000 or ontology["reduced_total_query_errors"] != 0:
        errors.append("Ontology experiment invariant failed")
    if ontology["naive_total_query_errors"] != 48926:
        errors.append("Ontology experiment expected negative-control result changed")

    schema = json.loads((ROOT / "experiments/schema_change_classifier/results.json").read_text(encoding="utf-8"))
    if schema["case_count"] != 30000 or schema["policies"]["typed_materiality"]["decision_error_rate"] != 0.0:
        errors.append("Schema materiality experiment invariant failed")

    sample = json.loads((ROOT / "instrument/sample_case/sample_summary.json").read_text(encoding="utf-8"))
    if not sample["validation"]["valid"]:
        errors.append("Sample case validation failed")
    if sample["change_classification"] != "MATERIAL_SCHEMA_CHANGE":
        errors.append("Sample change classification changed")
    if not sample["compile_ready"]:
        errors.append("Sample stable subgraph is not compile-ready")
    if sample["metrics"]["event_count"] != 21 or sample["metrics"]["relation_versions"] != 2:
        errors.append("Sample event/version count changed")

    private = ROOT / "instrument/sample_case/redacted_export/private"
    if private.exists():
        errors.append("Redacted sample export contains private directory")

    forbidden_cache = list(ROOT.rglob("__pycache__")) + list(ROOT.rglob("*.pyc"))
    if forbidden_cache:
        errors.append("Python cache artifacts present: " + ", ".join(str(x.relative_to(ROOT)) for x in forbidden_cache[:10]))
    return errors


def run_command(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.returncode == 0, result.stdout


def main() -> int:
    checks: dict[str, dict[str, object]] = {}
    all_errors: list[str] = []

    errors = check_json()
    checks["json_and_jsonl"] = {"passed": not errors, "errors": errors}
    all_errors.extend(errors)

    errors = check_markdown_links()
    checks["markdown_links"] = {"passed": not errors, "errors": errors}
    all_errors.extend(errors)

    errors = check_release_invariants()
    checks["release_invariants"] = {"passed": not errors, "errors": errors}
    all_errors.extend(errors)

    ok, output = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], ROOT / "instrument/towow_fieldkit")
    checks["fieldkit_tests"] = {"passed": ok, "output": output}
    if not ok:
        all_errors.append("Fieldkit tests failed")

    ok, output = run_command([sys.executable, "-m", "compileall", "-q", "towow_fieldkit"], ROOT / "instrument/towow_fieldkit")
    checks["python_compile"] = {"passed": ok, "output": output}
    if not ok:
        all_errors.append("Python compileall failed")

    # compileall creates cache files; remove them before packaging.
    for cache in ROOT.rglob("__pycache__"):
        for child in cache.iterdir():
            child.unlink()
        cache.rmdir()

    report = {
        "release": "Towow_A2A_Independent_Research_v0.4",
        "valid": not all_errors,
        "error_count": len(all_errors),
        "errors": all_errors,
        "checks": checks,
        "file_count_before_manifest": sum(1 for p in ROOT.rglob("*") if p.is_file()),
    }
    (ROOT / "qa/release_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
