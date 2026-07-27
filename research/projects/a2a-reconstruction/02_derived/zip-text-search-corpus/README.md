# ZIP 文本检索语料

本目录把最新 v1.2 包中 ZIP 内、但没有物理解压副本的文本提取为去重检索视图。
它不是新的证据来源；所有引用必须通过 `SOURCE_MAP.csv` 回到原 ZIP 与成员路径。

- ZIP 文本成员映射：1569
- 去重后提取文本：984
- 二进制、图片、PDF、DOCX 和超过 8 MB 的成员不提取，仍可在 `zip_members.csv` 定位。

示例：

```bash
rg -n "Effect Gateway|NAC|PFE" research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files
```
