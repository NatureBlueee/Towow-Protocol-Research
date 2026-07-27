# 当前研究现场

更新时间：2026-07-27

## 当前任务

截至 v1.2 的完整研究档案已经完成第一轮材料重建和历史设计能力审计。当前不继续统一理论、
启动新实验或修改原始成果；先把审计结果作为后续研究的真实导航环境。

## 唯一最新源包

`Towow_Complete_Research_Archive_v1.2_2026-07-27/`

它是本轮唯一的最新归档来源。根目录的 R5 v1.1 seed packet 仍可作为历史材料，但不再与完整
源包竞争“当前研究状态”。

## 当前工作入口

`research/projects/a2a-reconstruction/README.md`

重点入口：

1. `00_orientation/CURRENT_GLOBAL_VIEW.md`
2. `00_orientation/MATERIAL_ENVIRONMENT.md`
3. `00_orientation/RESEARCH_TIMELINE.md`
4. `00_orientation/DRIFT_AND_TURNING_POINTS.md`
5. `00_orientation/RESULTS_MAP.md`
6. `00_orientation/METHODS_MAP.md`
7. `01_catalog/physical_files.csv`
8. `01_catalog/zip_members.csv`
9. `02_derived/large-docs/`
10. `04_audit/README.md`
11. `04_audit/ledgers/capability_preservation_matrix.csv`
12. `04_audit/current_system_capability_map.md`

## 已完成

- 最新包物理文件、ZIP 成员、Markdown 章节与重复内容目录；
- ZIP 内独有文本的去重检索语料；
- v1.0、v1.1 和真人实验方案的逐章可逆拆分；
- 研究时间线、成果、方法、概念谱系、证据状态、漂移转折与开放问题初版；
- 关键 R5/R5.2/R5.4/R5C 来源短 ID。
- 七条原生研究线的独立能力档案；
- 39 项“能力—设计—证据—当前 owner”保真判断；
- 22 条主张、16 个证据族、15 次 Design Delta 的互相引用账本；
- 当前组件到历史能力、历史能力到当前组件的双向索引；
- 正式事实唯一 owner 表和审计自动校验；
- 明确的能力损失清单：本地 column generation 当前无 owner；
- 18 项部分保留能力的恢复要求。

## 当前边界

- 原始源包保持不变；
- 派生文档只用于导航，引用必须回到源路径、哈希和行号；
- 目录覆盖不代表研究结论正确；
- v1.2 中 Q1–Q5 是待执行程序，不是已完成结果；
- 历史上大量合成实验当前只承担 CI、保障或机制校准角色。
- `PRESERVED` 表示档案中的人工行为重建通过，不表示生产或真人验证通过；
- 审计现状为 `PRESERVED=15`、`TRANSFORMED=5`、`PARTIAL=18`、`LOST=1`。

## 审计后的下一条高价值线索

研究顺序已收束为 Q1 强中心基线、Q4 Router 冷启动、Q2 Mandate explain-back、Q3 单案
causal formation、Q5 真实复用。它们只是后续排序，本阶段没有启动。

任何实验开工前必须说明会改变哪个设计、反向结果是什么以及三类结果怎样修改系统；否则转入
CI、实现保障或档案校准。
