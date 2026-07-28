# 当前研究现场

<!-- research-state:start -->
```json
{
  "schema_version": "1.0",
  "updated_at": "2026-07-28",
  "current_project": "research/projects/joint-action-formation",
  "seed_problem": "research/projects/joint-action-formation/problem/v0.json",
  "active_problem": null,
  "validated_scenario": "research/projects/joint-action-formation/scenarios/problem-definition-archive-v0.json",
  "active_mechanism_scenario": null,
  "active_lines": [
    "LINE-01-DISCOVERY-BOUNDARY",
    "LINE-02-RELATION-CONSTITUTION",
    "LINE-03-POSSIBILITY-FORMATION",
    "LINE-04-CAPABILITY-REALIZATION",
    "LINE-05-AUTHORITY-NORMS",
    "LINE-06-REALITY-EFFECT",
    "LINE-07-RUNTIME-EVOLUTION"
  ],
  "current_batch": ".research-runtime/BATCH-20260728-V0-DEFINITION-R4/plan.json",
  "pending_user_decisions": [
    "是否批准将 BATCH-20260728-V0-DEFINITION-R4 的 109078 字节 NON_PUBLIC_DERIVED_RESEARCH 匿名盲审包（SHA-256: 26590d5dca63ab062364110a01ab4b32d4d7698f85bb194533ce8a1cd80aae73）发送给 Anthropic Claude",
    "在七线问题定义批次和盲审完成后，选择、重写或拒绝 Problem v1"
  ],
  "canonical_source": "research/sources/archive-v1.2.json"
}
```
<!-- research-state:end -->

更新时间：2026-07-28

## 当前任务

截至 v1.2 的完整研究档案已经完成第一轮材料重建和历史设计能力审计。当前正在建立有界自治
研究环境，并以“共同可行动性构成”作为首个试点。当前长问题只登记为 `Problem v0 / SEED`，
不是统一答案。真实 `v0` 定义批次已经由七条原生研究线在隔离条件下完成，并形成候选分歧
矩阵；匿名 Claude 盲审包已在本地冻结，尚未获得外发授权。

## 本批次改变的候选理解

这些只是 `Problem v1` 的输入，不是已经激活的统一结论：

- 当前 v0 同时容纳发现、关系构成、可能性形成、能力兑现、规范权威、现实效力和持续运行，
  但没有形式化说明这些层之间哪些不蕴含、何时发生状态转换，因此仍可能被漂亮叙事满足；
- “中心或联邦”不是充分判别器。强中心、平台或人类经纪只要保留来源范围、局部拒绝权、
  版本失效和 Authority Gate，就可能成为可信实现；通爻必须在公平条件下证明额外净价值；
- 形成主张需要预先冻结路径资格谓词与世界前态，并指出哪个获得授权的 operator 改变了
  状态；若等价路径原已存在，只能支持发现，不能支持 formation；
- 能力、授权、承诺、执行、目标域 Effect、Domain Adoption、Principal Acceptance 和
  Settlement 必须允许分别失败，不能由上游成功自动推出下游成立；
- 漂移不是一个统一事件。Mandate 撤销、证据失效、目标变化、组件升级和暂时离线需要不同
  的失效传播、阻断、复核、退出和局部重开语义；
- 任何候选机制都必须接受增强静态声明、权威感知强中心、成熟平台流程和人类经纪的公平
  对照，并把披露、等待、验证、治理、恢复及认知负担计入净价值。

本批次只分析既有档案，没有观察到真人授权、真实 Effect、Adoption、Acceptance、长期运行
或商业净价值；七线也没有证明 NAC、PFE、ledger、对象数量或联邦拓扑是唯一必要实现。

## 唯一最新源包

`Towow_Complete_Research_Archive_v1.2_2026-07-27/`

它是本轮唯一的最新归档来源。根目录的 R5 v1.1 seed packet 仍可作为历史材料，但不再与完整
源包竞争“当前研究状态”。

## 当前工作入口

当前试点：`research/projects/joint-action-formation/README.md`

历史档案与能力审计：`research/projects/a2a-reconstruction/README.md`

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

在用户精确批准后，对已冻结的匿名包执行 Claude 盲审；然后把七线候选、真实分歧和盲审
反例交给用户，选择、重写或拒绝唯一 `Problem v1 / ACTIVE`。只有用户明确激活 v1 后，
才从 Q1 强中心基线、Q4 Router 冷启动、Q2 Mandate explain-back、Q3 单案 causal
formation、Q5 真实复用中选择机制实验。

任何实验开工前必须说明会改变哪个设计、反向结果是什么以及三类结果怎样修改系统；否则转入
CI、实现保障或档案校准。
