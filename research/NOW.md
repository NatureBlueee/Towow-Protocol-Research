# 当前研究现场

<!-- research-state:start -->
```json
{
  "schema_version": "1.0",
  "updated_at": "2026-07-28",
  "current_project": "research/projects/joint-action-formation",
  "seed_problem": "research/projects/joint-action-formation/problem/v0.json",
  "candidate_problem": "research/projects/joint-action-formation/problem/v1-candidate.json",
  "history_alignment": "research/projects/joint-action-formation/problem/v1-history-alignment.json",
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
  "current_batch": null,
  "latest_completed_batch": "research/projects/joint-action-formation/candidates/BATCH-20260728-V0-DEFINITION-R4/finalization-manifest.json",
  "pending_user_decisions": [
    "激活、重写或拒绝 research/projects/joint-action-formation/problem/v1-candidate.json"
  ],
  "canonical_source": "research/sources/archive-v1.2.json"
}
```
<!-- research-state:end -->

更新时间：2026-07-28

## 当前任务

截至 v1.2 的完整研究档案已经完成第一轮材料重建和历史设计能力审计。当前正在建立有界自治
研究环境，并以“共同可行动性构成”作为首个试点。当前长问题只登记为 `Problem v0 / SEED`，
不是统一答案。真实 `v0` 定义批次已经由七条原生研究线在隔离条件下完成；Claude 匿名
盲审也已完成并建议对 v0 `REWRITE_BEFORE_ACTIVATION`。吸收七线真实分歧与盲审反例的
`Problem v1 / CANDIDATE` 已形成，但没有 ACTIVE 问题。

用户随后作出关键校正：`Problem v1` 本身是好的；过度拟合发生在 V1 形成以后，我们围绕
中心成本、Agent 原生环境和人的参与进行的继续讨论。此前一度把“讨论漂移”错误诊断成
“V1 需要重写”，现已纠正。V1 保持原样，历史审计只约束后续研究不得静默缩窄或替换它。

## 历史继承校正

- 当前 v1 文本对 39 项历史设计能力的展开程度为 `EXPLICIT=22`、`PARTIAL=10`、
  `ABSENT=7`；这不是 V1 质量评分，也不要求问题陈述枚举全部机制；
- 未显式展开的能力由七条研究线、场景、机制实验和系统设计继续继承，不能因为后续讨论
  没有提到就被删除；
- 本轮提出的“上下文—智能大脑—工具—执行环境”不是新中心，而是恢复历史中的
  `AgentExecution—Sovereign World—Context Compiler—Harness/World/Desk/Trace` 运行线；
- 研究至少需要并列 `AgentExecution`、`RelationEpisode`、`RelationEcology` 三个尺度；
  单一 episode 不能解释网络发现、路径沉淀、拓扑学习和未来发现成本递减；
- `S0—Q—operator—消融` 在 V1 中严格约束 formation 主张；后续解释不能把它扩张成
  吞并问题、角色、动作和评价语言构成的总本体；
- PFE 的历史机制已经确认，核心是 typed Unknown、形成算子、局部实验/反例、行动空间更新
  以及与 CRA 的资格化循环；PEC/PCC 暂未在档案中找到正式定义；
- 中心、联邦、平台、人类和确定性服务应按层与阶段组合。一个强中心在局部分布胜出，只会
  缩小其他机制的必要域，不会同时推翻 Agent 运行环境、边界、formation、Effect 或编译线；
- 成本是 V1 的重要可证伪经济目标；后续讨论不能把整项研究缩成成本问题，还要共同观察
  可达价值、错误、风险、披露、时间和后悔；
- `CAP-REL-004` 仍是唯一历史审计为 `LOST` 的能力：本地私有 candidate/column generation
  与最小贡献证明目前没有 owner。

完整逐项审计见
`research/projects/joint-action-formation/problem/v1-history-alignment.md`；其机器契约绑定
历史能力矩阵，任何候选或激活问题缺少该继承引用都将被研究治理检查拒绝。这里检查的是
研究程序不失忆，不是要求 ProblemContract 逐字包含所有历史机制。

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

## Claude 盲审改变的候选理解

- 七线都没有排除权威感知强中心等效，不能把联邦拓扑写进问题的预设答案；
- 合同、RBAC、审批链和事务系统可能已经承载候选规范差异，需要证明不是概念重命名；
- 当前 formation 主张没有实际执行冻结前态—operator—消融，可能仍只是发现或披露改进；
- 七线共享底层来源和模型语境，一致意见不能按七次独立验证计算；
- 还需要与单一强研究者直接整合比较，证明多线隔离确实保留了更多判别力且成本合理；
- 因此不激活 v0，也不从七线平均生成答案，而是形成带反事实条件和强基线的 v1 候选。

## 用户成本校正带来的方向补充

- 核心成本不是一两美元的 Agent 调用，而是低频异构关系首次形成时的平台规则建立、跨团队
  高认知判断、会议、等待、合同与审批、集成、验证、错误、机会损失、治理和恢复；
- 数据量不是主要判别变量。真正承重的是关系是否低频、异构、跨领域、开放维度、跨权威、
  难以预估，以及关键判断能否安全复用；
- RAG 主要降低检索成本，专用算法主要降低已知关系语法中的计算成本；它们不自动形成未知
  角色、权威、条件、现实 witness 和接受规则；
- 中心、联邦、平台和人类机制不是互斥立场，而是同一关系不同子问题和阶段的 Router 输出；
- 通爻的关键成本假说是共享形成基础设施能够降低新关系的边际规则形成成本，再把稳定关系
  编译为低判断负担的重复运行；目前不能把该假说当作事实；
- “智能判断需要能量”暂记为决策负担不能凭空消失、只能被承担、转移、容忍为错误或编译
  复用的会计假说，不直接声称为已经建立的热力学定律。

完整成本账本、生命周期公式、Router 变量、反向结果与现实数据要求见
`research/projects/joint-action-formation/economics/lifecycle-cost-model.md`。该模型恢复并
扩展了档案中已有的协调成本、Compiled World、CollapseSafe 与强基线经济模型。

持续研究模型外发已获得有边界授权：只有冻结 disclosure manifest、允许的 Codex/Claude
目的地、允许的研究分类、250 MiB 上限和相应隐私排除同时满足时，才可不再逐批询问。该授权
不覆盖真人私密材料、完整私有档案、现实动作、Problem 激活、稳定主张、部署或公开发布。

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

继续以 `problem/v1-candidate.json` 为锚，把最近讨论分别登记为三个从属研究输入：
AgentExecution 运行环境假说、跨机制 Router 假说、生命周期成本与价值前沿假说。下一轮
讨论或研究必须逐项说明它正在展开 V1 的哪一部分、没有覆盖什么、什么结果会改变设计；
不得再把某个最新输入升格成新的总问题。V1 是否激活仍由用户单独决定。

任何实验开工前必须说明会改变哪个设计、反向结果是什么以及三类结果怎样修改系统；否则转入
CI、实现保障或档案校准。
