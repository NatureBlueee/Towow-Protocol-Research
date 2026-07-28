# 当前研究现场

<!-- research-state:start -->
```json
{
  "schema_version": "1.0",
  "updated_at": "2026-07-28",
  "current_project": "research/projects/joint-action-formation",
  "seed_problem": "research/projects/joint-action-formation/problem/v0.json",
  "candidate_problem": "research/projects/joint-action-formation/problem/v2-candidate.json",
  "history_alignment": "research/projects/joint-action-formation/problem/v2-history-alignment.json",
  "active_problem": null,
  "preserved_problem_versions": [
    {
      "version": "v1",
      "path": "research/projects/joint-action-formation/problem/v1-candidate.json",
      "sha256": "9a59de81ac7c5ca0a42ff012bbade98b4be60978742b3c81d26f9024a3e9b408",
      "artifacts": [
        {
          "role": "problem_contract",
          "path": "research/projects/joint-action-formation/problem/v1-candidate.json",
          "sha256": "9a59de81ac7c5ca0a42ff012bbade98b4be60978742b3c81d26f9024a3e9b408"
        },
        {
          "role": "problem_companion",
          "path": "research/projects/joint-action-formation/problem/v1-candidate.md",
          "sha256": "7982aa908ce4e457e655fbe553db228f2ab9a09fdaa1202309df261d1bdc4a56"
        },
        {
          "role": "inheritance_audit",
          "path": "research/projects/joint-action-formation/problem/v1-history-alignment.json",
          "sha256": "ed98af1e8ce8d6fd1494e6881ab47bb7c63eea2b1d1cf003f343f869eac39381"
        },
        {
          "role": "inheritance_companion",
          "path": "research/projects/joint-action-formation/problem/v1-history-alignment.md",
          "sha256": "11a25e60edbfad0ec53f92c038356150ee3685dff349b1869148abf54acc1784"
        }
      ]
    }
  ],
  "validated_scenario": "research/projects/joint-action-formation/scenarios/problem-definition-archive-v0.json",
  "active_mechanism_scenario": null,
  "mechanism_profiles": [
    "research/projects/joint-action-formation/mechanisms/nac.json"
  ],
  "active_lines": [],
  "lines_by_problem": {
    "PRB-JOINT-ACTION-FORMATION@v0": {
      "status": "PRESERVED_CONTRACTS",
      "lines": [
        "LINE-01-DISCOVERY-BOUNDARY",
        "LINE-02-RELATION-CONSTITUTION",
        "LINE-03-POSSIBILITY-FORMATION",
        "LINE-04-CAPABILITY-REALIZATION",
        "LINE-05-AUTHORITY-NORMS",
        "LINE-06-REALITY-EFFECT",
        "LINE-07-RUNTIME-EVOLUTION"
      ]
    },
    "PRB-JOINT-ACTION-FORMATION@v2": {
      "status": "DRAFT",
      "lines": [
        "LINE-01-NAC"
      ]
    }
  },
  "current_batch": null,
  "latest_completed_batch": "research/projects/joint-action-formation/candidates/BATCH-20260728-V0-DEFINITION-R4/finalization-manifest.json",
  "pending_user_decisions": [
    "审阅、重写或激活 V2 五件材料闭包 research/projects/joint-action-formation/problem/activation/v2.json",
    "V2 激活后决定何时把 LINE-01-NAC 从 DRAFT 迁入首个按需机制批次"
  ],
  "canonical_source": "research/sources/archive-v1.2.json"
}
```
<!-- research-state:end -->

更新时间：2026-07-28

## 当前任务

截至 v1.2 的完整研究档案已经完成第一轮材料重建和历史设计能力审计。`Problem v0 / SEED`
的七线隔离定义批次与 Claude 匿名盲审已经完成；吸收其分歧与反例的 `Problem v1 /
CANDIDATE` 已形成并按精确哈希保存。

本轮新增了 `Problem v2` 加法式候选快照。它不修改、不判错也不 supersede V1，只把 V1
与历史中已有、但独立研究者容易遗漏的世界前提、服务对象、评价框架和有界机制研究范式显式
冻结为共同知识底座。V2 专属继承审计已经完成并给出 `REVIEWED / READY`；候选正文、说明、
继承审计、审计说明和 39 项能力矩阵也已组成待用户决定的五件材料闭包。其当前是否仍为候选、
是否已经激活，以及哪些研究线实际生效，只以本页顶部结构化状态块为准；
`v2-candidate.*` 始终保留为不可覆写的候选来源。

用户已经采用有界机制研究范式：每个机制按自己的环境、问题、能力、要求、非目标、证据和
反例独立推进；作用域外未覆盖不构成否定，负结果只改变受检验主张，已有方案能用就复用，
确认真实缺口才新增机制。NAC 的权威研究状态以 `mechanisms/nac.json` 为准；任何激活、
rebase、refute 或 supersede 都必须经过内容绑定的用户决定，不能从本段叙述推断。

## V1 存档与 V2 继承校正

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

V1 的完整逐项审计见
`research/projects/joint-action-formation/problem/v1-history-alignment.md`；V2 的当前版本审计
见 `research/projects/joint-action-formation/problem/v2-history-alignment.md`。两份机器契约
都绑定同一正典能力矩阵，但 V2 审计拥有独立 ID、路径、说明和 `problem_coverage`，不能靠给
V1 审计改标签穿透。这里检查的是研究程序不失忆，不是要求 ProblemContract 逐字包含所有
历史机制。

V2 以 `ADDITIVE_SNAPSHOT` 关系继承 V1。V1 的 Problem JSON、Problem Markdown、历史继承
审计 JSON 与审计 Markdown 四份文件的 SHA-256 都已写入 V2 lineage；任一文件被静默改动
时，治理检查会失败。V2 另有与自身精确同版本、状态为 `REVIEWED` 且建议为 `READY` 的
继承审计。正式激活决定还必须绑定
`research/projects/joint-action-formation/problem/activation/v2.json` 的精确 SHA-256；
该 bundle 同时冻结候选 JSON/Markdown、V2 审计 JSON/Markdown 和能力矩阵。V2 新增的显式
边界主要是：

- 本研究所考察的协调输入在接口处均表示为 Intent；显式输入和上游系统产生的隐式输入只是
  来源不同，上游怎样推断不属于本研究对象；已有 authority status 应被保留和验证，未知则
  保持 Unknown；
- Intent 生成者、所代表 Principal、受益者、受影响者和有权决定者不预设重合；
- 目标世界允许亿级、异构、动态、局部私有主体网络与低频长尾关系，默认方案不能依赖全量
  广播、完整世界汇聚或每个高级模型逐一判断；
- 平台、中心、制度、人类和确定性服务是既有能力、adapter 或稳定关系的编译结果，不是
  需要击败的阵营；
- `AgentExecution`、`RelationEpisode` 与 `RelationEcology` 是不能互相代替的三个分析
  尺度；人的参与按权威、价值与风险重新配置，而不是被全局最小化；
- `Clarification`、`Protective Contraction`、`Reject` 与 `Defer` 即使没有形成关系，也
  可以产生独立的保护性或信息价值；
- 七条原生线是问题家族，NAC、PFE、CRA 等机制可以在母线下独立研究，不要求提前统一。

完整共同底座见 `research/projects/joint-action-formation/problem/v2-candidate.md`。

## 有界机制研究现场

`MEC-NAC / v1` 恢复了 NAC 的原始尖锐问题：海量、异构、私有网络中的方向性 Intent
信号、跨模型锚点、渐进前缀、自描述和版本迁移，目标是在高级智能调用前缩小候选。

历史核验确认 NAC 有独立问题、冻结 IF-2、专利设计、M1/M3 配套、E-H1′ 预注册和失败门；
同时也明确记录 H1–H8 未运行。故当前状态是“正式持续研究”，不是“已经有效”或“可以因
不负责授权、Effect 等作用域外问题而整体降级”。

V2 LineContract 现在要求每项机制线绑定 scoped claims、历史与现成方案检查、未覆盖要求和
结果影响范围。现有七份 v0 LineContract 不被追溯改写；运行器只选择与本批 Problem 精确
同版本的 `ACTIVE` 线，并允许按需选择一条或多条线，防止 V2 文档与 v0 worker 静默混跑。

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

## 当前下一条高价值线索

先由用户审阅或重写 `problem/v2-candidate.md`；只有显式决定后才能激活 V2。V2 激活后，
首个 `LINE-01-NAC / v1` 只冻结 `E-H1′ → MC-NAC-ANCHOR`：按原门槛比较跨厂商召回与
vec2vec，并把自然语言加稳定 Schema 明确标成 V2 新增臂。H2–H8、方向性、自描述和迁移
分别建立后续有界线；传统索引、平台路由、强中心与混合方案在相应 M3/端到端线公平比较，
不能把它们的效果算作 NAC 坐标已经通过。

其他机制按相同范式逐个恢复为 profile 或新版本研究线。任何实验开工前必须说明受检验的
scoped claim、已有方案、反向结果只会改变什么、哪些主张不受影响，以及三类结果怎样修改
设计；否则转入 CI、实现保障或档案校准。
