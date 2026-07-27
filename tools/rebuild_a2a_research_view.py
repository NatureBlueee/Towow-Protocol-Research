#!/usr/bin/env python3
"""Rebuild the navigable A2A research view from the immutable v1.2 archive.

The source archive is never modified. This script creates:

- a physical-file catalog;
- a virtual ZIP-member catalog, including one level of nested ZIPs;
- a Markdown section catalog;
- duplicate-content groups;
- provenance-preserving splits of the largest Markdown documents.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "Towow_Complete_Research_Archive_v1.2_2026-07-27"
PROJECT_ROOT = ROOT / "research" / "projects" / "a2a-reconstruction"
CATALOG_ROOT = PROJECT_ROOT / "01_catalog"
DERIVED_ROOT = PROJECT_ROOT / "02_derived" / "large-docs"
SEARCH_CORPUS_ROOT = PROJECT_ROOT / "02_derived" / "zip-text-search-corpus"

SPLIT_TARGETS = [
    (
        SOURCE_ROOT
        / "02_WORKSPACE_SNAPSHOT"
        / "Towow_Unified_Paper_v1.0_formal"
        / "通爻_主权智能主体共同现实形成_正式论文_v1.0.md",
        "monograph-v1.0",
        1,
    ),
    (
        SOURCE_ROOT
        / "02_WORKSPACE_SNAPSHOT"
        / "Towow_R8_OPC_Constructive_Closure_v1.1"
        / "paper"
        / "通爻_主权智能主体共同现实形成_正式论文_v1.1.md",
        "monograph-v1.1",
        1,
    ),
    (
        SOURCE_ROOT
        / "02_WORKSPACE_SNAPSHOT"
        / "Towow_R8_OPC_Constructive_Closure_v1.1"
        / "human_study"
        / "通爻_OPC真人实验完整方案书_v1.1.md",
        "human-study-v1.1",
        1,
    ),
    (
        SEARCH_CORPUS_ROOT
        / "files"
        / "b9"
        / "b93c9b9ac768cbc7852fccbe902a8a46489ffb682d31374df52a9a5985374060.md",
        "original-handoff-manual-v1.0",
        1,
    ),
    (
        SEARCH_CORPUS_ROOT
        / "files"
        / "31"
        / "31403fde5285ce077dc0601738d48bf56872406b14145684d8a6bf0395cda536.md",
        "flowness-harness-v0.1",
        1,
    ),
    (
        SEARCH_CORPUS_ROOT
        / "files"
        / "dd"
        / "dd21711e325de293fa5197e97e8c9dd40b1d6167fb766e6f03d58823874cf3bd.md",
        "pre-rebuild-unified-paper",
        1,
    ),
]

TEXT_EXTENSIONS = {
    ".bib",
    ".csv",
    ".dot",
    ".json",
    ".jsonl",
    ".md",
    ".patch",
    ".py",
    ".sh",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass
class PhysicalRow:
    record_id: str
    relative_path: str
    size_bytes: int
    sha256: str
    extension: str
    phase: str
    artifact_type: str
    evidence_role: str
    status: str
    duplicate_group: str


@dataclass
class ZipRow:
    record_id: str
    container_path: str
    member_path: str
    nested_depth: int
    size_bytes: int
    compressed_bytes: int
    crc32: str
    sha256: str
    extension: str
    phase: str
    artifact_type: str
    evidence_role: str
    status: str
    duplicate_group: str


@dataclass
class SectionRow:
    record_id: str
    source_path: str
    source_sha256: str
    heading_level: int
    heading: str
    line_start: int
    line_end: int
    phase: str
    artifact_type: str


def sha256_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_path(path: Path) -> str:
    with path.open("rb") as handle:
        return sha256_stream(handle)


def slugify(value: str, fallback: str) -> str:
    value = re.sub(r"[`*_#<>:/\\|?\"“”‘’（）()]+", " ", value)
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:80] or fallback


def infer_phase(path: str) -> str:
    lower = path.lower()
    package_metadata = {
        "checksums.sha256",
        "manifest.csv",
        "manifest.json",
        "package_summary.json",
        "source_tree.txt",
    }
    if "/" not in lower and Path(lower).name in package_metadata:
        return "archive-orientation"
    rules = [
        ("towow_v1.2_decision_program", "v1.2-decision-reset"),
        ("constructive_closure_v1.1", "v1.1-executable-closure"),
        ("unified_paper_v1.0", "v1.0-formal-reconstruction"),
        ("independent_research_v0.7", "v0.7-opc-focus"),
        ("towow_a2a_v0.7", "v0.7-opc-focus"),
        ("agentic_opc_research_v0.7", "v0.7-opc-focus"),
        ("主权代理操作系统_统一论文_v0.7", "v0.7-opc-focus"),
        ("independent_research_v0.6", "v0.6-public-process"),
        ("public_evidence_pack_v0.6", "v0.6-public-process"),
        ("independent_research_v0.4", "v0.4-operationalization"),
        ("r7_field_pack_v0.4", "v0.4-operationalization"),
        ("independent_research_v0.3", "v0.3-independent-rebuild"),
        ("独立初步研究判断_v0.1", "v0.1-initial-judgment"),
        ("research_handoff", "pre-rebuild-handoff"),
        ("round5", "r5"),
        ("r5_2", "r5.2"),
        ("r5-2", "r5.2"),
        ("r5c", "r5c"),
        ("r5-4", "r5.4"),
        ("r5_4", "r5.4"),
        ("qdr", "qdr-public-data"),
        ("doi-10.5064", "qdr-public-data"),
        ("agent-to-agent 研究重建", "interaction-correction"),
        ("组织ai大脑构建思考", "interaction-correction"),
        ("正式统一论文_v1.0", "v1.0-formal-reconstruction"),
        ("interaction", "interaction-correction"),
        ("review", "interaction-correction"),
        ("correction", "interaction-correction"),
        ("00_start_here", "archive-orientation"),
    ]
    for marker, phase in rules:
        if marker in lower:
            return phase
    return "unresolved"


def infer_artifact_type(path: str, extension: str) -> str:
    lower = path.lower()
    name = Path(path).name.lower()
    if extension in {".zip", ".gz", ".tgz"}:
        return "archive-container"
    if extension in {".pdf", ".docx"}:
        return "rendered-document"
    if extension in {".png", ".svg"}:
        return "figure-or-render"
    if "checksum" in lower or extension == ".sha256":
        return "integrity-metadata"
    if "manifest" in lower:
        return "manifest"
    if "qa" in lower or "test" in lower:
        return "qa-or-test"
    if "review" in lower or "correction" in lower or "interaction" in lower:
        return "interaction-or-review"
    if "experiment" in lower or "result" in lower or "trace" in lower:
        return "experiment-or-result"
    if "evidence" in lower or "claim" in lower or "ledger" in lower:
        return "evidence-or-decision-ledger"
    if "theory" in lower or "理论" in path:
        return "theory"
    if "spec" in lower or "schema" in lower or "protocol" in lower:
        return "specification-or-protocol"
    if "instrument" in lower or "fieldkit" in lower or extension in {".py", ".sh"}:
        return "instrument-or-code"
    if "paper" in lower or "论文" in path:
        return "paper-or-monograph"
    if "roadmap" in lower or "program" in lower or "mission" in lower:
        return "research-program"
    if name.startswith("readme") or name.startswith("00_"):
        return "orientation"
    if extension in {".csv", ".json", ".jsonl", ".yaml", ".yml"}:
        return "structured-data"
    if extension in TEXT_EXTENSIONS:
        return "text-source"
    return "other"


def infer_evidence_role(path: str, artifact_type: str) -> str:
    lower = path.lower()
    if "r5.2" in infer_phase(path) or infer_phase(path) in {"r5", "r5.2", "r5.4", "r5c"}:
        return "direct-engineering-or-model-evidence"
    if "qdr" in lower or "public" in lower or "case" in lower:
        return "archival-calibration"
    if artifact_type == "experiment-or-result":
        return "mechanism-test-or-result"
    if artifact_type == "qa-or-test":
        return "implementation-assurance"
    if artifact_type in {"theory", "paper-or-monograph"}:
        return "synthesis-or-claim"
    if artifact_type == "interaction-or-review":
        return "direction-change-evidence"
    if artifact_type in {"manifest", "integrity-metadata"}:
        return "provenance-or-integrity"
    if artifact_type == "archive-container":
        return "source-container"
    return "supporting-material"


def infer_status(path: str) -> str:
    phase = infer_phase(path)
    lower = path.lower()
    if phase == "v1.2-decision-reset":
        return "current-program-at-archive-cutoff"
    if phase in {"archive-orientation", "interaction-correction"}:
        return "current-archive-metadata"
    if "qa_render_evidence" in lower:
        return "derived-render-evidence"
    if Path(path).suffix.lower() in {".zip", ".pdf", ".docx"}:
        return "packaged-or-rendered-copy"
    return "historical-source-or-working-artifact"


def write_csv(path: Path, rows: Iterable[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def catalog_physical_files() -> list[PhysicalRow]:
    manifest_path = SOURCE_ROOT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sha_by_archive_path = {
        str(item["archive_path"]): str(item["sha256"]) for item in manifest
    }
    rows: list[PhysicalRow] = []
    for index, path in enumerate(sorted(SOURCE_ROOT.rglob("*")), 1):
        if not path.is_file():
            continue
        rel_repo = path.relative_to(ROOT).as_posix()
        rel_source = path.relative_to(SOURCE_ROOT).as_posix()
        expected = sha_by_archive_path.get(rel_repo)
        digest = expected or sha256_path(path)
        extension = path.suffix.lower()
        artifact_type = infer_artifact_type(rel_source, extension)
        rows.append(
            PhysicalRow(
                record_id=f"P{index:04d}",
                relative_path=rel_source,
                size_bytes=path.stat().st_size,
                sha256=digest,
                extension=extension.lstrip(".") or "[none]",
                phase=infer_phase(rel_source),
                artifact_type=artifact_type,
                evidence_role=infer_evidence_role(rel_source, artifact_type),
                status=infer_status(rel_source),
                duplicate_group="",
            )
        )
    return rows


def extract_zip_text_search_corpus(
    physical: list[PhysicalRow],
) -> list[dict[str, str | int]]:
    """Extract unique searchable text from physical ZIPs without changing sources."""

    if SEARCH_CORPUS_ROOT.exists():
        shutil.rmtree(SEARCH_CORPUS_ROOT)
    files_root = SEARCH_CORPUS_ROOT / "files"
    files_root.mkdir(parents=True, exist_ok=True)

    physical_by_hash: dict[str, list[str]] = defaultdict(list)
    for row in physical:
        if f".{row.extension}" in TEXT_EXTENSIONS:
            physical_by_hash[row.sha256].append(row.relative_path)

    rows: list[dict[str, str | int]] = []
    for archive_path in sorted(SOURCE_ROOT.rglob("*.zip")):
        container = archive_path.relative_to(SOURCE_ROOT).as_posix()
        try:
            archive = zipfile.ZipFile(archive_path)
        except zipfile.BadZipFile:
            continue
        with archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                extension = Path(info.filename).suffix.lower()
                if extension not in TEXT_EXTENSIONS or info.file_size > 8 * 1024 * 1024:
                    continue
                try:
                    data = archive.read(info)
                except (OSError, RuntimeError):
                    continue
                digest = hashlib.sha256(data).hexdigest()
                if digest in physical_by_hash:
                    corpus_path = ""
                    physical_match = " || ".join(physical_by_hash[digest])
                    disposition = "already-searchable-physical"
                else:
                    target = files_root / digest[:2] / f"{digest}{extension}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists():
                        target.write_bytes(data)
                    corpus_path = target.relative_to(PROJECT_ROOT).as_posix()
                    physical_match = ""
                    disposition = "extracted-unique-text"
                rows.append(
                    {
                        "container_path": container,
                        "member_path": info.filename,
                        "size_bytes": info.file_size,
                        "sha256": digest,
                        "extension": extension.lstrip("."),
                        "disposition": disposition,
                        "corpus_path": corpus_path,
                        "physical_match": physical_match,
                        "phase": infer_phase(info.filename),
                        "artifact_type": infer_artifact_type(info.filename, extension),
                    }
                )
    write_csv(
        SEARCH_CORPUS_ROOT / "SOURCE_MAP.csv",
        rows,
        [
            "container_path",
            "member_path",
            "size_bytes",
            "sha256",
            "extension",
            "disposition",
            "corpus_path",
            "physical_match",
            "phase",
            "artifact_type",
        ],
    )
    unique_count = len({str(row["corpus_path"]) for row in rows if row["corpus_path"]})
    readme = [
        "# ZIP 文本检索语料",
        "",
        "本目录把最新 v1.2 包中 ZIP 内、但没有物理解压副本的文本提取为去重检索视图。",
        "它不是新的证据来源；所有引用必须通过 `SOURCE_MAP.csv` 回到原 ZIP 与成员路径。",
        "",
        f"- ZIP 文本成员映射：{len(rows)}",
        f"- 去重后提取文本：{unique_count}",
        "- 二进制、图片、PDF、DOCX 和超过 8 MB 的成员不提取，仍可在 `zip_members.csv` 定位。",
        "",
        "示例：",
        "",
        "```bash",
        "rg -n \"Effect Gateway|NAC|PFE\" research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files",
        "```",
    ]
    (SEARCH_CORPUS_ROOT / "README.md").write_text(
        "\n".join(readme) + "\n", encoding="utf-8"
    )
    return rows


def zip_members(
    archive: zipfile.ZipFile,
    *,
    container_path: str,
    nested_depth: int,
    max_nested_depth: int,
) -> Iterator[ZipRow]:
    counter = 0
    for info in archive.infolist():
        if info.is_dir():
            continue
        counter += 1
        member_path = info.filename
        extension = Path(member_path).suffix.lower()
        digest = ""
        data: bytes | None = None
        try:
            with archive.open(info) as handle:
                if extension == ".zip" and nested_depth < max_nested_depth:
                    data = handle.read()
                    digest = hashlib.sha256(data).hexdigest()
                else:
                    digest = sha256_stream(handle)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            digest = "[unreadable]"
        artifact_type = infer_artifact_type(member_path, extension)
        yield ZipRow(
            record_id="",
            container_path=container_path,
            member_path=member_path,
            nested_depth=nested_depth,
            size_bytes=info.file_size,
            compressed_bytes=info.compress_size,
            crc32=f"{info.CRC:08x}",
            sha256=digest,
            extension=extension.lstrip(".") or "[none]",
            phase=infer_phase(member_path),
            artifact_type=artifact_type,
            evidence_role=infer_evidence_role(member_path, artifact_type),
            status="zip-member",
            duplicate_group="",
        )
        if (
            extension == ".zip"
            and nested_depth < max_nested_depth
            and data is not None
            and len(data) <= 256 * 1024 * 1024
        ):
            nested_container = f"{container_path}!/{member_path}"
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as nested:
                    yield from zip_members(
                        nested,
                        container_path=nested_container,
                        nested_depth=nested_depth + 1,
                        max_nested_depth=max_nested_depth,
                    )
            except zipfile.BadZipFile:
                pass


def catalog_zip_members(max_nested_depth: int = 1) -> list[ZipRow]:
    rows: list[ZipRow] = []
    for path in sorted(SOURCE_ROOT.rglob("*.zip")):
        container = path.relative_to(SOURCE_ROOT).as_posix()
        try:
            with zipfile.ZipFile(path) as archive:
                rows.extend(
                    zip_members(
                        archive,
                        container_path=container,
                        nested_depth=0,
                        max_nested_depth=max_nested_depth,
                    )
                )
        except zipfile.BadZipFile:
            continue
    for index, row in enumerate(rows, 1):
        row.record_id = f"Z{index:06d}"
    return rows


def duplicate_groups(
    physical: list[PhysicalRow], zipped: list[ZipRow]
) -> dict[str, str]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in physical:
        if row.sha256 and not row.sha256.startswith("["):
            by_hash[row.sha256].append(row.record_id)
    for row in zipped:
        if row.sha256 and not row.sha256.startswith("["):
            by_hash[row.sha256].append(row.record_id)
    result: dict[str, str] = {}
    duplicate_index = 0
    for digest, records in sorted(by_hash.items()):
        if len(records) < 2:
            continue
        duplicate_index += 1
        group_id = f"D{duplicate_index:04d}"
        result[digest] = group_id
    return result


def markdown_sections(path: Path) -> list[SectionRow]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []
    for line_number, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append((line_number, len(match.group(1)), match.group(2).strip()))
    source_rel = path.relative_to(SOURCE_ROOT).as_posix()
    source_sha = sha256_path(path)
    rows: list[SectionRow] = []
    for index, (line_start, level, heading) in enumerate(headings):
        line_end = len(lines)
        for next_start, next_level, _ in headings[index + 1 :]:
            if next_level <= level:
                line_end = next_start - 1
                break
        rows.append(
            SectionRow(
                record_id="",
                source_path=source_rel,
                source_sha256=source_sha,
                heading_level=level,
                heading=heading,
                line_start=line_start,
                line_end=line_end,
                phase=infer_phase(source_rel),
                artifact_type=infer_artifact_type(source_rel, ".md"),
            )
        )
    return rows


def catalog_markdown_sections() -> list[SectionRow]:
    rows: list[SectionRow] = []
    for path in sorted(SOURCE_ROOT.rglob("*.md")):
        rows.extend(markdown_sections(path))
    for index, row in enumerate(rows, 1):
        row.record_id = f"S{index:06d}"
    return rows


def split_markdown(path: Path, output_name: str, split_level: int) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(rf"^{'#' * split_level}\s+(.+?)\s*$", line)
        if match:
            starts.append((index, match.group(1).strip()))
    if not starts:
        starts = [(0, path.stem)]
    elif starts[0][0] > 0:
        starts.insert(0, (0, "文首与元数据"))

    output_root = DERIVED_ROOT / output_name
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    source_rel_repo = path.relative_to(ROOT).as_posix()
    source_sha = sha256_path(path)
    entries: list[dict] = []
    for section_index, (start, title) in enumerate(starts, 1):
        end = starts[section_index][0] if section_index < len(starts) else len(lines)
        body = "".join(lines[start:end])
        filename = f"{section_index:02d}_{slugify(title, f'section-{section_index:02d}')}.md"
        target = output_root / filename
        provenance = (
            "---\n"
            "derived_view: true\n"
            f"source_path: {source_rel_repo}\n"
            f"source_sha256: {source_sha}\n"
            f"source_line_start: {start + 1}\n"
            f"source_line_end: {end}\n"
            f"source_heading: {json.dumps(title, ensure_ascii=False)}\n"
            "---\n\n"
            "> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。\n\n"
        )
        target.write_text(provenance + body, encoding="utf-8")
        entries.append(
            {
                "file": filename,
                "title": title,
                "source_line_start": start + 1,
                "source_line_end": end,
                "source_sha256": source_sha,
            }
        )

    index_lines = [
        f"# {path.name} 拆分索引",
        "",
        "本目录仅为导航用派生视图。原始文件是唯一文本来源。",
        "",
        f"- 原始文件：`{source_rel_repo}`",
        f"- SHA-256：`{source_sha}`",
        f"- 拆分粒度：{split_level} 级标题，共 {len(entries)} 段",
        "",
        "| 序号 | 标题 | 源行号 | 派生文件 |",
        "|---:|---|---:|---|",
    ]
    for number, entry in enumerate(entries, 1):
        escaped_title = entry["title"].replace("|", "\\|")
        index_lines.append(
            f"| {number} | {escaped_title} | "
            f"{entry['source_line_start']}–{entry['source_line_end']} | "
            f"[{entry['file']}]({entry['file']}) |"
        )
    (output_root / "INDEX.md").write_text(
        "\n".join(index_lines) + "\n", encoding="utf-8"
    )
    return entries


def build_summary(
    physical: list[PhysicalRow],
    zipped: list[ZipRow],
    sections: list[SectionRow],
    split_results: dict[str, list[dict]],
) -> dict:
    return {
        "source_archive": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        "generated_view": PROJECT_ROOT.relative_to(ROOT).as_posix(),
        "physical_file_count": len(physical),
        "physical_bytes": sum(row.size_bytes for row in physical),
        "zip_member_count": len(zipped),
        "zip_member_uncompressed_bytes": sum(row.size_bytes for row in zipped),
        "markdown_section_count": len(sections),
        "phases": dict(sorted(Counter(row.phase for row in physical).items())),
        "artifact_types": dict(
            sorted(Counter(row.artifact_type for row in physical).items())
        ),
        "evidence_roles": dict(
            sorted(Counter(row.evidence_role for row in physical).items())
        ),
        "split_documents": {
            key: len(value) for key, value in sorted(split_results.items())
        },
        "notes": [
            "Counts describe the latest v1.2 source package and virtual ZIP members.",
            "ZIP members may duplicate extracted physical files; use duplicate_group.",
            "Derived splits are navigation views, not new research sources.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-nested-zip-depth",
        type=int,
        default=1,
        help="Nested ZIP levels to catalog after each physical ZIP.",
    )
    args = parser.parse_args()
    if not SOURCE_ROOT.is_dir():
        raise SystemExit(f"latest source package not found: {SOURCE_ROOT}")

    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    physical = catalog_physical_files()
    zipped = catalog_zip_members(args.max_nested_zip_depth)
    groups = duplicate_groups(physical, zipped)
    for row in physical:
        row.duplicate_group = groups.get(row.sha256, "")
    for row in zipped:
        row.duplicate_group = groups.get(row.sha256, "")
    sections = catalog_markdown_sections()

    write_csv(
        CATALOG_ROOT / "physical_files.csv",
        (asdict(row) for row in physical),
        list(PhysicalRow.__annotations__),
    )
    write_csv(
        CATALOG_ROOT / "zip_members.csv",
        (asdict(row) for row in zipped),
        list(ZipRow.__annotations__),
    )
    write_csv(
        CATALOG_ROOT / "markdown_sections.csv",
        (asdict(row) for row in sections),
        list(SectionRow.__annotations__),
    )

    duplicate_rows = []
    members_by_hash: dict[str, list[str]] = defaultdict(list)
    for row in physical:
        if row.duplicate_group:
            members_by_hash[row.sha256].append(
                f"{row.record_id}:{row.relative_path}"
            )
    for row in zipped:
        if row.duplicate_group:
            members_by_hash[row.sha256].append(
                f"{row.record_id}:{row.container_path}!/{row.member_path}"
            )
    for digest, members in sorted(members_by_hash.items()):
        duplicate_rows.append(
            {
                "duplicate_group": groups[digest],
                "sha256": digest,
                "copy_count": len(members),
                "members": " || ".join(members),
            }
        )
    write_csv(
        CATALOG_ROOT / "duplicate_groups.csv",
        duplicate_rows,
        ["duplicate_group", "sha256", "copy_count", "members"],
    )

    search_corpus_rows = extract_zip_text_search_corpus(physical)

    split_results: dict[str, list[dict]] = {}
    for path, output_name, split_level in SPLIT_TARGETS:
        if path.is_file():
            split_results[output_name] = split_markdown(
                path, output_name, split_level
            )

    summary = build_summary(physical, zipped, sections, split_results)
    summary["zip_text_member_mappings"] = len(search_corpus_rows)
    summary["unique_zip_text_corpus_files"] = len(
        {str(row["corpus_path"]) for row in search_corpus_rows if row["corpus_path"]}
    )
    (CATALOG_ROOT / "catalog_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
