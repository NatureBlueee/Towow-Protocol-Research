# 目录说明

## 文件

| 文件 | 用途 |
|---|---|
| `physical_files.csv` | 最新包全部物理文件；含哈希、轮次、材料类型、证据角色和状态 |
| `zip_members.csv` | 每个物理 ZIP 及一层嵌套 ZIP 的成员；使用 `container_path!/member_path` 定位 |
| `markdown_sections.csv` | 每个物理 Markdown 标题、层级和行号范围 |
| `duplicate_groups.csv` | 跨物理文件和 ZIP 成员的内容重复组 |
| `catalog_summary.json` | 目录覆盖统计 |
| `SOURCE_REGISTER.md` | 关键研究来源的短 ID 与访问入口 |

## 稳定性

`record_id` 在同一源包和同一重建脚本排序下稳定。若源包内容变化，应以内容 SHA-256 而不是
编号作为长期身份。

## 查询示例

```bash
# 找所有 R5C 文件
rg -n "R5C|r5c" research/projects/a2a-reconstruction/01_catalog

# 找所有与 Mandate 相关的物理 Markdown 章节
rg -n "Mandate" research/projects/a2a-reconstruction/01_catalog/markdown_sections.csv

# 查一个文件有哪些重复副本
rg -n "D0105" research/projects/a2a-reconstruction/01_catalog/duplicate_groups.csv
```

