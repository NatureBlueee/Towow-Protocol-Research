# 材料环境与查询方法

## 1. 分层

本项目把材料分成五层，避免“整理”变成对原档案的重写。

| 层 | 位置 | 性质 |
|---|---|---|
| L0 原始来源 | `Towow_Complete_Research_Archive_v1.2_2026-07-27/` | 最新完整包；保持不变 |
| L1 物理与 ZIP 目录 | `01_catalog/` | 机器生成的全量索引、散列与分类 |
| L2 ZIP 文本检索语料 | `02_derived/zip-text-search-corpus/` | 按字节散列去重后的可搜索副本 |
| L3 大文档章节视图 | `02_derived/large-docs/` | 带来源、散列和行号的章节片段 |
| L4 人工研究导航 | `00_orientation/`、`03_views/` | 时间线、谱系、证据状态和主题入口 |

L1–L4 都可以从 L0 重建，不承担新的权威事实。

## 2. 稳定寻址

### 物理文件

使用 `physical_files.csv` 的：

```text
relative_path
sha256
size_bytes
phase
material_role
```

### ZIP 成员

使用 `zip_members.csv` 的：

```text
container_path
member_path
sha256
uncompressed_size
nesting_level
```

旧 ZIP 的文件名可能受历史编码影响。遇到乱码时，以容器、成员散列和
`SOURCE_MAP.csv` 的映射为稳定身份，不依赖显示名称猜测来源。

### 大文档片段

每个章节片段头部保存：

```text
source_path
source_sha256
source_line_start
source_line_end
```

片段是阅读视图，不是新的独立主张。校验器会按顺序拼接片段并与原文逐字比较。

## 3. 常用查询

重新生成全部派生视图：

```bash
make research-index
```

验证目录完整性、来源散列、片段可重构性和导航链接：

```bash
make research-view-check
```

在物理 Markdown 中查询概念：

```bash
rg -n "NAC|PEC|PFE|CRA|Effect|Acceptance" \
  Towow_Complete_Research_Archive_v1.2_2026-07-27 \
  -g '*.md'
```

在 ZIP 内历史文本中查询：

```bash
rg -n "NAC|PEC|PFE|CRA|Effect|Acceptance" \
  research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files
```

查找概念出现在哪些章节：

```bash
rg -n "NAC|PEC|PFE|CRA" \
  research/projects/a2a-reconstruction/01_catalog/markdown_sections.csv
```

## 4. 使用纪律

- 原始包与派生视图意见冲突时，以原始包为准。
- 来源材料、重建纪事、评审意见和当前判断必须分开引用。
- 同名文件不能自动视为同一内容；散列相同才可认定为字节级重复。
- 历史阶段的概念应先在其原生问题中理解，再讨论跨阶段整合。
- 从拆分片段得出的判断，必须能回到原文的来源路径、散列和行号。

## 5. 当前边界

这套环境完成的是“材料可寻址、可查询、可追溯”，不是对所有主张的最终审计。
下一层工作应从 `SOURCE_REGISTER.md` 的承重来源出发，建立逐项能力保真与主张谱系，
而不是再次从最终统一文档反推历史。
