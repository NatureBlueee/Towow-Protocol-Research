# Agent-to-Agent 研究材料环境

本项目把最新源包
`Towow_Complete_Research_Archive_v1.2_2026-07-27/`
转换为可查询、可寻址、可追溯的研究工作视图。

## 边界

- 最新源包是唯一当前来源，原件不改名、不移动、不拆写。
- 本目录中的拆分文档和搜索语料都是派生视图，不是新的研究事实源。
- 历史判断按当时材料保留；“后续版本”不自动使旧结果失效，也不自动证明旧结果成立。
- 目录负责恢复来源关系，不负责替研究者决定哪些理论应当统一。

## 从这里开始

1. [当前全局理解](00_orientation/CURRENT_GLOBAL_VIEW.md)
2. [材料环境与查询方法](00_orientation/MATERIAL_ENVIRONMENT.md)
3. [研究进程时间线](00_orientation/RESEARCH_TIMELINE.md)
4. [漂移与转折点](00_orientation/DRIFT_AND_TURNING_POINTS.md)
5. [研究成果地图](00_orientation/RESULTS_MAP.md)
6. [研究方法地图](00_orientation/METHODS_MAP.md)
7. [概念与系统谱系](00_orientation/CONCEPT_AND_SYSTEM_LINEAGE.md)
8. [证据与主张状态](00_orientation/EVIDENCE_AND_CLAIM_STATUS.md)
9. [开放问题与真实阻塞](00_orientation/OPEN_THREADS.md)
10. [历史设计能力恢复与研究审计](04_audit/README.md)

## 文件环境

- `01_catalog/physical_files.csv`：最新包中的全部物理文件；
- `01_catalog/zip_members.csv`：全部物理 ZIP 及一层嵌套 ZIP 的成员；
- `01_catalog/markdown_sections.csv`：所有物理 Markdown 的章节和源行号；
- `01_catalog/duplicate_groups.csv`：按内容哈希识别的重复副本；
- `01_catalog/SOURCE_REGISTER.md`：关键来源的稳定入口；
- `02_derived/large-docs/`：原始 handoff、Flowness、重建前统一论文、v1.0、
  v1.1 与真人方案的逐章拆分视图；
- `02_derived/zip-text-search-corpus/`：ZIP 内独有文本的去重检索视图；
- `03_views/`：按轮次、主题、材料角色形成的阅读视图。
- `04_audit/`：七条原生研究线、能力保真矩阵、主张/证据/决策账本、正式事实
  owner、当前系统能力图与审计后研究排序。

## 重建与检查

```bash
make research-index
make research-view-check
make research-audit-check
```

重建脚本只读取最新源包，生成机械目录和派生视图。人工撰写的
`00_orientation/` 与 `03_views/` 不会被覆盖。
