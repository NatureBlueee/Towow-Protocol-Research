# PT-001 产品机制组合图：从模糊目标到可验收资源协作

日期：2026-08-01  
状态：`PRODUCT DESIGN CANDIDATE / SYNTHETIC TASK ONLY / NO MECHANISM PROMOTION`

## 0. 结论先行

当前最合理的产品不是七套新引擎，也不是一套通用比较平台，而是一条**条件化组合链**：

1. 能由标准平台直接完成的请求立即旁路；
2. 通用模型承担访谈、摘要、候选生成和解释，但不成为 Capability、Authority、Effect 或
   Acceptance 的事实源；
3. 强中心在能够合法获得必要输入、拥有清楚权威边界且成本更低时直接协调；
4. 不能汇聚的局部世界由本地工具或人工 owner 返回任务相关投影、typed response、候选或
   反例，不上传完整世界；
5. 关系协商复用版本化 case/workflow、合同 workspace、审批、policy、reservation 与事件历史；
6. 执行复用平台原生动作、durable workflow、幂等、outbox 和补偿；
7. Effect 只从目标权威域 readback，Acceptance 只由相应主体或 Authority Locus 对精确结果
   版本给出；
8. 拒绝、撤销和漂移先由不可变版本、监控、撤销源与人工 amendment 安全处理；只有真实任务
   证明局部重开优于保守重审时，才增加 dependency/Defeater planner。

这张图当前没有 `INVENT` 决定。开放世界中的未表达机会生成、跨组件证据门、以及依赖敏感的
局部重开仍可能存在精确缺口，但现有证据不足以证明需要新的独立机制。产品先采用成熟组合和
保守人工 fallback；只有同一真实任务上的重复残余才转为 `INVENT`。

## 1. 任务真值边界

本图不是把历史 T3 继续包装成现实任务。

`TASK-TRUTH-CORRECTION-001.md` 已确认：历史 `R7_RESOURCE_REQUEST.md` 只是未来实验所需的
资源清单，没有资源请求的 (S_0)、角色、资源、动作或权威后置状态。因此本图处理的是：

> `T1 SYNTHETIC_TASK_SPEC + 新构造的非标准资源协作产品任务候选`

证据级别统一为：

`NEW_SYNTHETIC_PRODUCT_TASK_CANDIDATE / NOT_ARCHIVAL_REAL_WORLD_TASK / NOT_USER-VALIDATED`

### 1.1 用于画机制图的合成迁移变体

本文件用 `PT-001-B / SYNTHETIC_TRANSFER_VARIANT` 检查机制图能否迁移，而不把它冒充第二份
现实证据。一个活动发起人只表达：“下周想为约十二人的小型社区分享找到一个安静、带投影、能临时使用
两小时的空间，最好有人协助交接。”发起人暂不愿公开完整参与者名单和预算。

潜在空间 owner、设备 owner、现场执行者和最终受益者可能不重合：

- 场地方只在用途、时间、人数和责任边界足够清楚后才愿意回应；
- 设备可能由另一位保管人操作，不能从“空间可用”推出“投影可用”；
- owner 可以拒绝、defer、提出不同时间、限定用途或在承诺前撤回；
- 发起人可以拒绝反提案，也可以只接受空间、不接受设备或现场协助；
- 建筑管理者或其他受影响方可能拥有规则或 challenge 入口，但不因此自动拥有最终签字权；
- 只有资源被有效预留、现场动作实际发生、目标状态得到 owner 域 readback，且发起人对精确
  结果作出 Acceptance，才可称本次候选协作完成。

这个案例只提供一条可讨论的产品任务骨架。它没有独立 world truth，也没有证明这些角色或
需求来自真实用户。未来真实任务可以替换资源类型，但不能静默删掉拒绝、最小披露、分离权威、
Effect 和 Acceptance。

### 1.2 当前冻结的产品结果

为避免把“生成了一份方案”当完成，本图暂用以下产品结果 (Q_c)：

- 原始价值底线未被悄悄改成“收到若干推荐”或“生成一份文本”；
- 必要角色、资源、用途、时间、责任、退出和验收条件形成可修改的精确版本；
- Capability、Authority、Commitment、Reservation 分别有相应来源；
- 对方可以拒绝、counter、defer、撤销或局部接受；
- 有界动作由获准 executor 执行，且没有重复占用或重复 Effect；
- Effect 来自目标域 readback，Acceptance 来自相称的主体或 Authority Locus；
- 拒绝、撤销、失败或变化不会被覆盖，且只在证据支持时局部重开；
- 相比标准预订平台、合法强中心、通用模型加人工经纪，新增协调成本没有吞噬任务价值。

`Q_c` 是产品候选的设计约束，不是已经冻结的实验 oracle，也不能用于报告 coverage。

## 2. 产品状态链与事实边界

```text
GOAL_SEED
  → GOAL_DRAFT
  → CONDITIONS_UNKNOWN
  → DISCLOSURE_NEGOTIATING
  → OPPORTUNITY_CANDIDATES
  → ENGAGEMENT_PENDING
  → PROPOSAL_VERSIONED
  → CAPABILITY_QUALIFIED | CAPABILITY_UNKNOWN
  → AUTHORITY_PENDING
  → COMMITTED_AND_RESERVED
  → EXECUTING
  → EFFECT_CONFIRMED | EFFECT_NOT_CONFIRMED
  → ACCEPTED | PARTIALLY_ACCEPTED | REJECTED | UNKNOWN
  → COMPILED_FOR_REUSE | REOPEN_SCOPED | REOPEN_BROAD | EXITED
```

任何箭头都不能靠上游文本自动穿透：

```text
相关候选
  ≠ 对方愿意接洽
  ≠ 能力可依赖
  ≠ 有权承诺
  ≠ 资源已预留
  ≠ 动作已执行
  ≠ 目标 Effect 已发生
  ≠ 结果被采用
  ≠ Principal 已接受
```

产品可以用一个界面呈现这条链，但不得用一个 `success=true` 抹平这些事实来源。

## 3. 总体组合决定

| 节点 | 当前最小产品决定 | 产品内核选择 | 当前不做 |
|---|---|---|---|
| N0 标准路径旁路 | `ADOPT` | 平台直达 + 轻量路由 | 不让 formation 成为所有请求必经层 |
| N1 模糊目标成稿 | `COMPOSE` | 通用模型访谈 + 可修改 Intent draft + 人确认 material items | 不把摘要当授权 |
| N2 发现缺失条件 | `COMPOSE` | schema/checklist + 强模型/人工判断 + typed Unknown/Refuse | 不先建通用 Boundary ontology |
| N3 受控请求信息 | `COMPOSE` | 渐进式 consent + 本地投影 + 可验证选择性披露 adapter | 不要求完整画像或全量上下文 |
| N4 生成合作可能性 | `COMPOSE`，精确 residual `KEEP_UNKNOWN` | 平台/目录优先，合法中心与人工经纪，本地事件投影和 reciprocal probe 按需 | 不把 RAG/ARD/Agent Card 当未表达机会的完整解 |
| N5 找到或培养能力 | `COMPOSE` | planning/tool-use + HITL + 有界 probe + 成熟 readiness/eval | 不从历史成功或模型自信推出可依赖 |
| N6 同意与授权 | `COMPOSE` | IAM/policy + scoped delegation + approval + 人的权威决定 | 不建第二授权事实源 |
| N7 关系与承诺 | `COMPOSE` | CMMN/workflow/CLM + versioned proposal + reservation + event history | 不预注册独立 Relation Constitution Engine |
| N8 执行真实动作 | `COMPOSE` | 平台原生执行优先；跨域用 durable workflow、幂等、outbox、Saga | 不用模型文本或消息 ACK 代替执行 |
| N9 验证 Effect | `COMPOSE` | 目标域 authoritative readback + 最小跨域映射 Gate | 不复制目标数据库，不设五个平行事实根 |
| N10 获得 Acceptance | `COMPOSE` | 精确结果版本 + 人/相称 Authority 的 accept/reject/partial/unknown stance | 不由系统替主体接受 |
| N11 拒绝、撤销、失败与变化 | `COMPOSE`，自动局部重开 `KEEP_UNKNOWN` | 不可变版本 + telemetry + revocation + 人工 amendment；依赖图只在有净值时启用 | 不默认自动 scoped reopen，也不改写历史 |
| N12 稳定路径复用 | `ADOPT` | 把稳定子路径编译为平台流程/adapter，保留版本和重新准入 Gate | 不每次从零 formation，也不沿用失效授权 |

## 4. 逐节点机制组合

### N0 标准路径旁路

**输入前提**

只知道一个初步目标；尚不确定它是标准商品/场地预订，还是需要形成非标准关系。此时最重要的
不是马上展开多 Agent 协作，而是先判断是否存在已编译的直接路径。

**候选单项与组合**

- 成熟机制：垂直预订/采购平台、固定审批流程、商品目录和原平台客服；
- 强中心：拥有合法输入的中央调度员直接匹配并完成预订；
- 通用模型：只做意图归类和平台入口解释；
- 人工流程：前台或经纪人一次判断“标准路径/非标准路径/未知”；
- adapter：把已确认的标准请求映射到平台字段，并从平台状态回读；
- 最强组合：确定性规则优先，通用模型只处理语言变体，低置信或高后果转人工；一旦标准平台
  覆盖 (Q_c)，立即旁路后续 formation 链。

**能解决什么**

避免为了“开放协作”给普通预订增加披露、问答、版本、审批和治理成本，也保留强中心或成熟
平台真正更简单时的正向结果。

**不能解决什么**

不能仅凭文本相似判断一个路径是否真实可用，也不能从目录存在推出资源当前可用、owner 愿意、
最终结果会被接受。

**维护、迁移与格式风险**

平台字段和库存语义会变化；模型路由可能把非标准请求错误压进固定表单；adapter 容易复制平台
状态成为第二事实源。adapter 只保存映射和平台引用，不保存竞争状态。

**产品决定：`ADOPT`**

把 `PLATFORM_DIRECT / STRONG_CENTER_DIRECT / OPEN_FORMATION / UNKNOWN` 作为前门路由结果，
标准路径直接采用。

**会改变决定的真实任务结果**

若真实用户在标准平台内能以更少步骤完成精确目标、得到权威 readback 和 Acceptance，则继续
旁路并删除该类任务的额外机制。若被路由到标准平台后反复因用途、角色、隐私或反提案无法表达而
失败，则将该分布重开到 N1，而不是扩建全局 formation。

### N1 模糊目标形成可修改草稿

**输入前提**

用户只有价值方向和少量约束；Intent 生成者、Principal、受益者、受影响者和最终决定者可能
不重合。入口相关性不是授权。

**候选单项与组合**

- 成熟机制：结构化 intake、表单、case-management intake、CRM/service desk；
- 强中心：协调员读取合法可用的上下文，形成目标草稿；
- 通用模型：访谈、归纳目标、暴露歧义、生成多个可修正解释；
- 人工流程：用户或代理人确认 material items，必要时由人工 facilitator 处理价值冲突；
- adapter：把自由文本映射为带 provenance、scope、version 和 `authority_status` 的 Intent draft；
- 最强组合：模型先生成“目标/底线/未知/不愿披露/谁能决定”的短草稿，用户只确认会改变后续
  行动的内容；未确认部分保持 `UNKNOWN`。

**能解决什么**

把模糊叙述变成可继续探问的候选输入，减少反复复述，并保留谁说了什么、哪些只是模型推断。

**不能解决什么**

不能证明目标完整、偏好稳定或用户愿意承担后果；不能替未出现的受影响方发言；不能把模型生成
的合理解释当 Principal mandate。

**维护、迁移与格式风险**

模型升级会改变摘要；结构化字段可能压掉例外、语气和未决冲突；跨产品迁移可能只带字段不带
来源。应保存可回读原文引用与差异，而不是只保存最终 JSON。

**产品决定：`COMPOSE`**

采用通用模型 + 结构化 intake + material-change 人确认，不建设独立“意图真值引擎”。

**会改变决定的真实任务结果**

若用户在行动前频繁纠正会改变伙伴、资源、风险或验收的内容，说明模型草稿不能独立推进，需把
更多节点交给人工或改为受限表单；若简单表单在相同任务上得到相同完成结果且认知成本更低，则
`REMOVE` 模型访谈层。

### N2 发现缺失条件

**输入前提**

已有 Intent draft，但尚不清楚缺的是信息、伙伴、能力、Authority、资源、可执行表示、现实
probe，还是目标本身不相容。

**候选单项与组合**

- 成熟机制：schema/checklist、CMMN case plan、constraint validation、XACML 风格 typed
  decisions、active information gathering；
- 强中心：在合法上下文内用工具检查已知缺口并安排下一问；
- 通用模型：提出竞争解释、识别歧义和生成下一步候选；
- 人工流程：用户/owner 对价值冲突、原则性拒绝和不可逆风险作判断；
- adapter：把本地响应统一映射为 `WITNESS / CUT / UNKNOWN / REFUSE / NOT_APPLICABLE / STALE`，
  同时保留本地来源；
- 最强组合：以少量稳定 schema 保底，强模型或人工选择下一问，本地工具返回 typed response，
  充分信息后停止追问。

**能解决什么**

区分“资料不完整”和“对当前决定已经充分”，防止把拒绝写成不存在，也防止统一追问造成无限
对话。

**不能解决什么**

不能观察主体不愿表达且没有可授权 probe 的事实；不能保证 typed response 诚实或完整；不能
从局部 witness 推出全局可行、授权或承诺。

**维护、迁移与格式风险**

缺口类型可能膨胀成重本体；不同 provider 对 `UNKNOWN/REFUSE` 的映射会失真；停止规则可能随
任务漂移。只保留会改变产品动作的最小状态，未映射语义附带原始说明。

**产品决定：`COMPOSE`**

把 typed response 和充分性停止规则实现为 intake/orchestrator 的策略与 adapter，不先建立
新的权威事实对象。

**会改变决定的真实任务结果**

若通用模型 + 本地查询 + 普通审批在真实任务中以更少披露获得相同完成结果，`REMOVE` 独立
sufficiency/Boundary 对象；若反复发生追问错误、拒绝丢失或把局部证据误闭合，则保留 typed
语义，并只对产生错误的停止/路由缺口考虑 `INVENT`。

### N3 有控制地请求必要信息

**输入前提**

系统已说明某个具体决定还缺什么、为何需要、向谁披露；主体保留不披露和撤回许可的选择。

**候选单项与组合**

- 成熟机制：渐进 consent、GNAP 式 continuation、VC/SD-JWT 选择性披露、现有隐私/保留期
  管理和审批流程；
- 强中心：只在有合法基础时聚合已获准字段，并记录接收者和用途；
- 通用模型：把请求解释成易懂语言，建议较低披露的替代项；
- 人工流程：主体批准、拒绝、缩窄或选择可信中介；
- adapter：把任务所需字段映射到本地 credential、文档或人工回答，并绑定目的、接收者、
  版本和 expiry；
- 最强组合：先请求最小 task-relative projection；不足时逐步升级，拒绝后尝试改变条件或退出，
  不把完整画像作为默认输入。

**能解决什么**

让披露成为可理解、可拒绝、可追溯的产品动作，并把“最小信息”与当前产品决定绑定，而不是
抽象承诺零披露。

**不能解决什么**

不能同时保证零披露和完整发现；不能保证接收方未来行为，也不能从 credential 有效推出 claim
真实、当前充分或 Principal 已接受合作。

**维护、迁移与格式风险**

credential/claim 格式、issuer 和保留期策略会变化；跨 recipient 多轮披露的累计暴露容易被
低估；adapter 可能丢失 purpose 和 refusal。身份、凭据、token、数据保留与隐私保证统一标记
`SECURITY_REVIEW_REQUIRED / NO_SECURITY_CLAIM`，本图不作安全有效性判断。

**产品决定：`COMPOSE`**

采用成熟 consent/credential 能力和本地 projection adapter；产品必须显示目的、接收者、保存期、
可拒绝项及继续路径。

**会改变决定的真实任务结果**

若用户因披露负担放弃，或为了完成任务被迫给出与决定无关的上下文，当前组合失败；应缩窄请求、
引入人工中介或改变方案。若普通平台 consent 已无损承担全部必要语义，则 `ADOPT` 原平台并
`REMOVE` 专用披露层。

### N4 生成新的合作可能性

**输入前提**

目标和最小可披露投影已形成，但伙伴、资源、角色或组合路径尚未明确；有些对象已登记，有些只在
本地事件或人际知识中可见。

**候选单项与组合**

- 成熟机制：平台目录、ARD/Agent Card、RAG/搜索、marketplace、matching、FIPA brokering；
- 强中心：合法获得必要投影后用搜索、规划和工具生成候选；
- 通用模型：跨表述联想候选、生成 search/probe/partner hypotheses；
- 人工流程：经纪人、社区协调员、熟人介绍，尤其处理未登记资源和关系语境；
- adapter：端侧事件检测/任务投影、目录格式转换、candidate handoff、receipt-backed
  reciprocal probe；NAC 只在“已有投影怎样表示和匹配”切片作为候选；
- 最强组合：标准平台/目录先行；未覆盖时，由本地工具或人工返回最小候选投影，合法强中心做
  跨候选整合，只有必要时向少数对手方发 reciprocal probe，并允许 honest-undiscoverable。

**能解决什么**

同时利用已编译市场、中央协调能力、通用模型的开放联想和本地世界，不把所有机会都假定已写成
卡片；候选可进入接洽，而不是停在相似度结果。

**不能解决什么**

目录/RAG 不能检索未表达对象；本地投影也无法恢复拒绝披露或原则上零信息的机会；候选相关性
不能推出 Capability、willingness、Authority 或可达路径。当前 T1 证据仍是本地合成，不能证明
现实机会召回。

**维护、迁移与格式风险**

目录过期、embedding/model 漂移、SEEK/OFFER 方向丢失、同一资源重复、probe 语义不兼容、
人工经纪扩展成本，以及 adapter 把局部候选变成中心事实。任何网络、隔离、认证或隐私安全判断
均为 `SECURITY_REVIEW_REQUIRED`。

**产品决定：`COMPOSE`；精确 residual：`KEEP_UNKNOWN`**

MVP 采用“平台/目录 → 合法强中心或人工经纪 → 本地最小投影/probe”的分层组合。是否需要一个
独立的未表达机会协议、NAC 扩展或 reciprocal-discovery 机制保持 Unknown；当前不发明。

**会改变决定的真实任务结果**

若未来真实任务中，平台/强中心/人工经纪已经以更低成本找到并促成同一可接受合作，删除本地
协议复杂度。若多项完成的真实合作都依赖事前未登记、由本地动态事件或互惠 probe 才出现的伙伴，
且该增益在留出任务上重现，再把精确 residual 转为 `INVENT` 或固化 adapter。若零披露机会始终
不可发现，则产品应诚实退出，而不是继续扩建评测。

### N5 找到或培养可依赖能力

**输入前提**

已有一个或多个合作候选，但当前阻塞可能是工具、技能、环境、权限、资源、伙伴或任务表示；即使
有历史能力声明，也尚未证明本次 operation 可兑现。

**候选单项与组合**

- 成熟机制：planning/replanning、action-model learning、CEGIS、workflow amendment、CI/eval、
  provenance、readiness、quota/reservation 和 telemetry；
- 强中心：在相同权限和工具下选择 ask/search/probe/tool/partner/reframe/exit；
- 通用模型：诊断 blocker、生成操作步骤、调用工具、解释替代路径；
- 人工流程：培训、引入专家、批准 probe、改变执行条件或判定不值得继续；
- adapter：把 source/version、executor/environment、permission、resource、probe、expiry、
  recovery 组合成 action-specific 派生 readiness view；
- 最强组合：typed blocker router 只作为 orchestration 策略；低风险可逆 probe 先行，随后以
  成熟 eval/readiness/IAM/reservation 和实际 readback 资格化精确 operation。

**能解决什么**

区分“找到候选”与“可依赖地完成本次动作”，并允许通过工具、训练、伙伴、权限申请或任务重表示
创造条件，而不是把当前不能做当最终不能做。

**不能解决什么**

不能从修复后成功回填干预前的能力；不能从 readiness/CI 推出 Authority、Commitment 或目标
Effect；全部 `UNKNOWN` 虽安全但没有行动覆盖。

**维护、迁移与格式风险**

运行环境、版本、账户和资源状态快速漂移；派生 capability object 易成为第二事实源；vendor
telemetry 和 eval 格式难迁移。派生 view 必须引用原始 owner 状态、带 freshness/expiry，并可
重建而非长期手工同步。权限与执行环境部分标记 `SECURITY_REVIEW_REQUIRED`。

**产品决定：`COMPOSE`**

复用成熟 readiness/eval/IAM/reservation/telemetry，Capability 只作为带时效的派生视图；不注册
新的能力事实根。typed router 暂作为强中心/人工流程内的策略。

**会改变决定的真实任务结果**

若成熟组合已稳定预测首次执行、资源冲突和恢复，则 `REMOVE` 独立 capability view，只保留查询
adapter。若真实任务反复出现“所有底层信号各自为绿、最终 operation 仍失败”的跨来源误闭合，
且派生 view 能在行动前阻止这些失败，再保留或完整创新该精确资格化缺口。

### N6 取得同意与授权

**输入前提**

合作候选与精确 operation 已可描述，但请求者、资源 owner、执行者、受益者、受影响者和最终
Acceptance authority 不预设重合；Capability 不产生 Authority。

**候选单项与组合**

- 成熟机制：RBAC/ABAC/ReBAC、Cedar/OPA/OpenFGA、OAuth RAR/token exchange、delegation、
  VC/capability、approval workflow 和 CLM；
- 强中心：policy decision point 汇集被授权的当前事实并执行 allow/deny/escalate；
- 通用模型：解释请求、生成 policy input、发现冲突，但不作最终 authority decision；
- 人工流程：相称 Authority Locus 对用途、时间、责任、例外和不可逆风险作决定；受影响方获得
  challenge/recourse 而不冒充签字权；
- adapter：把 proposal version、Principal、locus、purpose、resource、expiry、redelegation、
  stance 与底层 policy/token/approval 绑定；
- 最强组合：成熟 IAM/policy 做 enforcement，短期 scoped delegation/approval 提供当前授权，
  高后果或价值冲突由人决定，adapter 只补 version/purpose/standing 映射。

**能解决什么**

阻止同一 Agent/账户的不同角色相互代行，保留拒绝、撤销、版本失效和受影响方 challenge，并
把系统允许与人的同意分开。

**不能解决什么**

policy `Permit` 不等于 Commitment、Reservation、Effect 或 Acceptance；credential 可验证也
不等于 claim 真实；系统不能替 Principal 理解或认领责任。

**维护、迁移与格式风险**

policy、关系 tuple、token、合同版本和 approval 状态可能重复；映射失真会制造 false allow 或
stale stance；真实 Principal 的认知负担可能高于任务价值。所有 identity、credential、token、
policy enforcement 和 revocation 安全性质均标记 `SECURITY_REVIEW_REQUIRED / NO_SECURITY_CLAIM`。

**产品决定：`COMPOSE`**

采用成熟 authority stack，加最小 versioned-purpose adapter 和人工 Gate；不建立一套竞争的
Mandate/Authority 世界数据库。

**会改变决定的真实任务结果**

若成熟 stack 在真实任务中无误处理角色、用途、版本、撤销、challenge 和 resource gate，并且
用户可理解，则 `ADOPT` 原栈、删除新增对象。若反复发生旧 stance 穿透新版本、错误 locus 承诺、
撤销后继续或受影响方无入口，才保留最小 adapter；只有 adapter 仍不能表达的精确差异才进入
`INVENT`。

### N7 形成关系版本、承诺与资源预留

**输入前提**

各方已获得可接洽地位并可修改提案，但尚未形成对精确资源、时间、用途、动作、证据、退出和
验收条件的共同可执行版本。

**候选单项与组合**

- 成熟机制：CMMN/BPMN、case management、SharedPlans、FIPA propose/contract-net、CLM、
  versioned workspace、event sourcing、reservation/booking ledger；
- 强中心：有权的协调者维护唯一 proposal version，收集 counter 和局部 stance；
- 通用模型：起草提案、比较版本、发现 material changes、解释未解决冲突；
- 人工流程：双方修改、反提案、局部接受、拒绝、defer，并由相应 owner 作最终承诺；
- adapter：把多种消息/合同/平台状态映射到 `proposal version + contribution provenance +
  stance + commitment + reservation`，但 owner store 保持权威；
- 最强组合：CMMN/CLM 式可变 case + immutable version/event history + 人工/owner stance；只有
  精确版本获承诺并且 reservation 成功后才进入执行。

**能解决什么**

保留双方 counter、局部异议和 material change，避免旧版本同意自动继承；防止资源、时间和责任
被重复承诺；固定平台已预编译时可直接压缩为普通预订。

**不能解决什么**

版本存在不等于 materiality 判别正确，消息握手不等于双方理解；关系文本不能替 Capability、
Authority、Reservation 或实际执行。

**维护、迁移与格式风险**

过度版本化会制造审批爆炸；不同 workflow/CLM 的状态语义难无损映射；多处复制 stance 和
reservation 会竞争。应以资源 owner 的 reservation ledger 和各方 stance store 为事实源，关系
workspace 只持引用和不可覆盖历史。

**产品决定：`COMPOSE`**

复用 case/workflow/CLM、事件历史和 reservation；RelationVersion 是互操作/可读视图，不预先
成为独立运行引擎。

**会改变决定的真实任务结果**

若一个成熟平台或有权强中心已经无损处理 counter、版本、局部接受、撤销和 reservation，直接
`ADOPT` 并 `REMOVE` 通用关系层。若真实协作反复因 material change 继承旧 stance、来源丢失或
不同 owner 的 reservation 冲突失败，才增加最小 version/provenance adapter；不从格式漂亮推出
必要性。

### N8 执行有界真实动作

**输入前提**

精确 proposal version 已获相称授权和承诺，所需资源已预留，operation、executor、目标对象、
幂等 identity、失败/补偿边界和 readback query 已确定。

**候选单项与组合**

- 成熟机制：平台原生 API/操作、durable workflow、transactional outbox、幂等键、event sourcing、
  Saga/compensation、retry；
- 强中心：在同一权威域内直接原子执行；跨域时只编排，不伪造 owner 状态；
- 通用模型：只生成或选择已获准 tool call、解释失败，不成为 executor receipt；
- 人工流程：现场交接、手工确认、例外处置和必要补偿；
- adapter：把版本化 commitment 转换成平台原生 operation，并把 native receipt 原样引用回来；
- 最强组合：单权威平台原生执行优先；跨域使用 durable workflow + outbox/idempotency + native
  receipt/readback；不可自动补偿的动作转人工。

**能解决什么**

让协作真正改变目标世界，处理超时、重复、部分失败和恢复，并保持谁执行了哪个精确 operation。

**不能解决什么**

workflow completed、消息 ACK、exit code 或模型 `PASS` 不能证明目标 Effect；Saga compensation
不保证世界回到原状态；执行成功不推出 Adoption 或 Acceptance。

**维护、迁移与格式风险**

workflow vendor lock-in、operation identity 语义不一致、重试造成重复副作用、connector 变更、
补偿残差和人工 handoff 丢失。connector 必须以原生 target 状态为准，不能自报完成。执行权限和
运行环境安全部分标记 `SECURITY_REVIEW_REQUIRED`。

**产品决定：`COMPOSE`**

产品不自造通用执行 runtime；按目标系统选择平台原生执行或成熟 durable workflow，并强制幂等、
原生 receipt 和后续 readback。

**会改变决定的真实任务结果**

若单一平台在同等失败条件下完成动作、恢复和 readback，且成本更低，路由为 `PLATFORM_DIRECT`。
若真实任务出现重复资源占用、ACK 丢失后二次 Effect、补偿掩盖残差或 connector 自证完成，则当前
组合不合格；只补对应执行/恢复缺口，不建立泛化评价平台。

### N9 从目标权威域验证 Effect

**输入前提**

已有 ActionAttempt/native receipt，但执行域、目标状态权威、采用者和 Acceptance authority
可能不同；必须回答“目标世界是否按精确 operation 改变”。

**候选单项与组合**

- 成熟机制：数据库事务结果、authoritative status API、CDC/event sourcing、独立 readback、
  幂等 operation ledger；
- 强中心：若本身就是合法 target/reference monitor，可原子提交并 readback；否则不能自证；
- 通用模型：解释 readback 或辅助定位，但不生成 Effect truth；
- 人工流程：物理或难机器化目标由相称 owner 观察并提供可追溯确认；
- adapter：把 native receipt/readback 映射为带 target、object、version、operation 和 source 的
  Effect record，不复制目标事实；
- 最强组合：目标域 native transaction/readback 为唯一 Effect 根，跨域只加最小 interop Gate，
  明确 `ATTEMPTED / EFFECT_CONFIRMED / EFFECT_NOT_CONFIRMED / UNKNOWN`。

**能解决什么**

阻止 producer、controller、transport 或模型把自己的成功标签晋升成现实完成；支持超时后的安全
reconcile 和 exactly-once outcome 判断。

**不能解决什么**

Effect 不等于工作流 Adoption、Principal Acceptance、长期价值或 Settlement；数字 readback
不能自动证明物理世界的完整因果性。

**维护、迁移与格式风险**

target API 演化、object/version alias、readback 时延、事件乱序、跨 connector 语义丢失，以及
Gate 重复保存目标状态。只保存权威引用、判别所需 metadata 和不可覆盖历史。

**产品决定：`COMPOSE`**

采用目标域 authoritative readback + 最小映射 Gate。独立 Effect/readback 同时是产品真值机制
和必要评测设施，因为没有它就无法判断合作是否真的完成。

**会改变决定的真实任务结果**

若真实目标域显示未改变，而执行器或 orchestrator 报成功，当前产品链必须判失败并保留该假绿；
若单一强平台能以原生原子状态无损给出 Effect，则 `ADOPT` 平台 readback、`REMOVE` 跨域 Gate。
若没有任何独立权威 readback，可保持 `UNKNOWN`，不能用更复杂评分器补出 Effect。

### N10 获得 Adoption 与 Acceptance

**输入前提**

精确 Effect 已被目标域确认；仍需区分结果是否被工作流实际采用，以及有权主体是否接受该精确
结果版本。主体可以 partial、reject、defer、retract 或保持 Unknown。

**候选单项与组合**

- 成熟机制：case/workflow adoption state、approval/sign-off、CLM acceptance、issue resolution、
  settlement/receipt；
- 强中心：只有自身拥有相称 Acceptance authority 时才能记录接受，否则只转交请求；
- 通用模型：生成结果摘要、差异和验收证据索引，不能替主体作出 stance；
- 人工流程：Principal/Authority Locus explain-back 并选择 accept/partial/reject/unknown，说明
  仍需修正的 material item；
- adapter：把 acceptance stance 绑定到精确 Effect、proposal version、scope 和时间，不把平台
  “已读/已完成”误映射为接受；
- 最强组合：目标工作流记录 Adoption，相称主体对精确结果给独立 Acceptance；低风险、单权威
  平台若已经无损保存两者可内部压缩。

**能解决什么**

让“技术上做到了”和“这正是我接受的结果”保持可区分；允许局部接受和拒绝产生下一步，而不是
把用户沉默当成功。

**不能解决什么**

一次 Acceptance 不证明永久接受、无后悔、商业净值或公平；模型共识、自动评分和操作完成都不
能替代相称主体的认领。

**维护、迁移与格式风险**

平台 `done/approved/accepted` 语义不同；结果更新后旧 Acceptance 可能被错误继承；人工确认过多
会吞噬任务价值。只在 material result/version 变化时重新确认，并保留原 stance。

**产品决定：`COMPOSE`**

采用成熟 workflow/approval + 精确版本 Acceptance stance。独立 Acceptance readback 是核心产品
与评测设施，不纳入通用模型自动 promotion。

**会改变决定的真实任务结果**

若真实用户看到 Effect 后拒绝、部分接受或提出此前未表达的底线，系统必须重开相应 proposal，
而不能保留“已完成”。若单一平台已有相称 authority、版本绑定和 reject/retract，则直接采用；若
用户无法理解验收对象，先改善解释和人工流程，不发明更多状态。

### N11 拒绝、撤销、失败与变化时重新开放

**输入前提**

任一阶段出现 refusal、defer、counter、capability drift、resource loss、Mandate revocation、
证据失效、目标变化、Effect failure 或 Acceptance rejection。旧历史不可覆盖。

**候选单项与组合**

- 成熟机制：immutable contract/version、event sourcing、Temporal/Camunda/Step Functions
  version/migration、telemetry、token revocation、Saga、manual amendment；
- 强中心：在掌握完整合法依赖时计算 affected scope；不确定时扩大阻断；
- 通用模型：解释变化、提出替代伙伴/时间/工具/方案，不拥有恢复决定；
- 人工流程：高耦合、隐藏依赖、高后果或价值变化时全局/局部重审；
- adapter：把 authority/evidence/resource/target/acceptance 的 change event 映射到版本化依赖，
  生成 `BLOCK / UNKNOWN / CONTINUE / REOPEN / EXIT` 候选；
- 最强组合：默认采用不可变版本 + 原生监控/撤销 + 保守人工 amendment；只有依赖显式且可验证时
  才做局部重开，隐藏依赖或高耦合时扩大阻断。

**能解决什么**

保留拒绝和失败，把暂时离线与规范失效区分开；避免一个伙伴撤销后无关工作全部丢失，也避免陈旧
授权、证据或目标继续穿透。

**不能解决什么**

workflow replay 不证明关系仍有效；依赖图永远可能遗漏真实边；补偿不能删除历史 Effect；模型
无法替 Authority 决定新版本。

**维护、迁移与格式风险**

dependency graph 成本和隐藏边可能使“精确局部重开”成为假精确；跨 workflow 迁移会丢失 event
semantics；自动恢复可能沿用旧 token、reservation 或 Acceptance。权限撤销与运行安全性质标记
`SECURITY_REVIEW_REQUIRED`。

**产品决定：`COMPOSE`；自动 scoped reopen：`KEEP_UNKNOWN`**

先交付成熟版本/监控/撤销/人工 amendment 的安全组合。显式 dependency/Defeater 只作为候选
辅助，不作为总 runtime；遇 Unknown 默认扩大阻断。

**会改变决定的真实任务结果**

若真实重复任务中人工/全局重审与成熟 workflow 同样安全且成本更低，`REMOVE` 自动 planner。
若在依赖可声明的多个真实任务中，局部重开显著减少无关返工，同时没有 stale continuation，才
保留；若隐藏依赖导致错误继续，立即退回 broad reopen，而不是补一个更大的本体。

### N12 将稳定子路径编译为可复用能力

**输入前提**

至少一次 episode 已得到 Effect 与 Acceptance，且能区分哪些步骤、字段和权威边界稳定，哪些仍
依赖具体任务或主体判断。一次合成成功本身不足以编译为正式路径。

**候选单项与组合**

- 成熟机制：workflow template、platform configuration、case model、contract template、policy
  bundle、connector、runbook；
- 强中心：对重复请求直接执行已批准模板，在 material change 时退回 N1/N2/N7；
- 通用模型：填充非承重字段、解释差异和迁移 context；
- 人工流程：owner 审批模板边界、例外和再准入条件；
- adapter：保存稳定路径的接口映射、owner 引用、版本、expiry 和 Defeater，不复制原系统事实；
- 最强组合：把高频稳定部分下沉到平台/workflow，保留 authority、readback、Acceptance 和变化 Gate；
  新差异只重开必要节点。

**能解决什么**

降低重复关系的问答、规则建立和人工协调成本，让首次高成本判断真正沉淀，而不是每次重跑开放
formation。

**不能解决什么**

不能从一次成功推断跨行业泛化；模板不能沿用过期 capability、授权、资源、证据或目标；Context
摘要不能替原始 provenance。

**维护、迁移与格式风险**

平台锁定、template drift、旧字段继续生效、迁移只保格式不保语义、connector 停更，以及编译路径
压掉例外。每次运行仍从 owner truth 刷新承重输入，并保留可回退到开放链的入口。

**产品决定：`ADOPT`**

采用成熟 workflow/template/adapter 编译稳定子路径；不建立一个总 Relation Ecology runtime。

**会改变决定的真实任务结果**

若第二次真实运行没有降低等待、询问和人工成本，或因复用旧状态增加错误，停止编译并回到显式
case。若稳定模板在不同资源 owner 或平台迁移后仍无损保持权威、Effect 和 Acceptance，则扩大
复用范围；否则只保留局部 adapter。

## 5. 评测设施是否必要：只保留会决定产品机制的部分

这里的评测不是用户产品，也不再扩建通用 blind-comparison 实验室。必要设施只负责判别上述
产品决定是否在真实任务中成立。

| 设施 | 必要性 | 直接决定的产品机制 | 充分条件与停止点 |
|---|---|---|---|
| 独立 Effect readback + Acceptance source + 假绿回归 | `CORE_NECESSARY` | N9/N10 是否允许显示“已完成” | 能稳定拒绝 producer/controller/transport 自证，并从真实 target/Principal 回读后停止扩建 |
| 具体任务的拒绝、撤销、重复、ACK 丢失、失败恢复 replay | `CORE_NECESSARY` | N8/N11 的幂等、补偿和 reopen 选择 | 已覆盖该任务最可能改变用户结果的失败，能决定采用平台、组合或重开；不扩成通用所有故障平台 |
| 披露内容/接收者/目的、询问轮次、候选来源、真实完成结果 | `CORE_NECESSARY` | N2–N4 选择表单、模型、人工、目录、本地投影或 probe | 能说明哪一层真正带来可接受合作，以及其披露和等待代价；决定后停止 |
| Capability/Authority/Reservation 的原生 source readback | `CORE_NECESSARY` | N5–N7 是否可进入执行 | 能阻止历史声明、模型自信、policy allow 或文本承诺单独穿透；不建立第二事实库 |
| 通用 3,200 blind comparison、C01–C05、通用 classifier/model-input | `CONDITIONAL_NOT_CURRENTLY_JUSTIFIED` | 当前没有一个节点必须依赖它作决定 | 只有更小真实任务比较无法区分两个候选、错误选择代价显著更高时，按该节点所需范围恢复 |
| byte-level 通用数学与自动 receipt promotion/deletion gate | `CONDITIONAL` | 只在跨 provider 精确复现或自动改变正式状态会影响产品机制时需要 | 精确产品决定完成即停止；用户/外部权威决定状态时不建设自动 promotion |

最小产品研究顺序应是：先找一个独立真实的低风险资源协作任务，冻结其用户价值、owner、行动、
Effect 和 Acceptance；运行 `平台/强中心/通用模型+成熟栈/人工经纪/上述组合`；只有直接任务结果
无法解释哪个组件造成差异时，再启用相应窄评测。评测设施不能先于其负责的产品决定扩张。

## 6. 当前产品架构含义

### 6.1 一个协调层，多个事实 owner

产品可以有一个强中心 orchestrator，但它只维护 episode 的引用、版本、待决问题和路由状态。
以下事实继续由原生 owner 持有：

- 用户/Principal：目标、拒绝、stance、Acceptance；
- 资源 owner：availability、counter、reservation、revocation；
- execution environment：实际 operation result；
- target domain：Effect/readback；
- policy/authority source：当前 permit/deny/delegation；
- workflow/event store：不可覆盖的执行与恢复历史。

中心能合法取得这些输入且完整解决时，强中心就是产品正确机制；局部化不是意识形态目标。

### 6.2 通用模型的固定边界

通用模型可做：访谈、摘要、候选、问题解释、proposal draft、差异比较、工具选择和恢复建议。

通用模型不可单独创建：Principal 归属、Capability、Authority、Commitment、Reservation、Effect、
Adoption、Acceptance 或 Settlement。模型升级不应改写既有事实，只能触发重新评估其生成部分。

### 6.3 adapter 的成功条件

adapter 是当前组合中最可能成为通爻自有工程内核的部分，但它只有在以下条件满足时才有价值：

- 保留 source、scope、object、version、expiry 和 refusal；
- 不把上游状态静默晋升为下游状态；
- 不复制 owner truth 成为第二事实源；
- 能被另一平台/格式替换，并可从原生来源重建；
- 在真实任务中减少语义丢失或人工搬运，而不是只增加字段。

如果普通映射已无损，直接采用；如果格式间存在稳定语义残余，先做窄 adapter；只有 adapter 仍
不能解决且残余改变真实任务结果，才 `INVENT`。

## 7. 尚未解决、但已经被精确定位的问题

1. **未表达机会是否需要产品级新机制**：目录、RAG、ARD 和 Agent Card 只覆盖已表达对象；
   但当前只有合成证据支持本地投影/reciprocal probe，现实净增益和采用成本未知。
2. **跨组件证据门是否只需 adapter**：从 discovery 到 capability、authority、commitment、
   Effect、Acceptance 的不蕴含边界明确存在；现成组合能否在一个真实任务上无损贯通尚未运行。
3. **局部重开是否有净值**：成熟 workflow + 人工 amendment 是强基线；dependency/Defeater
   planner 只有在依赖可声明、漂移适中且减少返工而不增加 unsafe continuation 时才值得保留。
4. **真人是否理解并愿意认领状态**：合成 policy、schema 和 readback 无法回答真实主体对请求、
   反提案、责任、验收和退出的理解成本。
5. **新 T3 产品候选是否对应真实需求**：目前没有独立真实前态。取得真实任务后，若其角色、
   价值底线和失败结构与本图不同，应修改产品链，而不是把现实压入当前案例。

## 8. 下一项会真正改变产品的行动

不是继续 Wave025，也不是先实现整张状态图。下一步应取得或共创一个**低风险、可撤销、带独立
资源 owner 和 Acceptance authority 的真实资源请求**，然后只实现最薄闭环：

```text
模糊目标 intake
→ 一次受控澄清/披露
→ 平台、强中心或人工经纪产生候选
→ 一轮可拒绝/counter 的版本化提案
→ 原生 capability/authority/reservation Gate
→ 一个有界动作
→ target readback
→ user Acceptance
→ 一次拒绝或变化后的恢复
```

这个任务若由成熟平台或有权强中心完整解决，就是产品决定：收敛到平台/中心并删除多余机制。
若组合解决，则把组合、adapter 和路由条件固化为产品。只有同一真实分母上出现可重复、不能由
更简单组合关闭的断点，才登记精确 `INVENT`，并只为该断点建设必要评测。

## 9. 来源与不受影响边界

本图直接依据：

- `problem/v1-candidate.md`；
- `problem/v2.md`；
- `rounds/2026-07-28-seven-line-solution-research/PROGRAM.md` 的 T1/T3 与七线目标；
- `rounds/2026-07-28-seven-line-solution-research/TASK-TRUTH-CORRECTION-001.md`；
- `studies/product-mechanism-rebase-2026-08-01.md`；
- `studies/solution-first-composition-method-correction-2026-07-28.md`；
- `studies/full-line-startup/01-discovery-boundary-audit-2026-07-28.md`；
- `studies/full-line-startup/02-03-audit-2026-07-28.md`；
- `studies/full-line-startup/04-05-audit-2026-07-28.md`；
- `studies/full-line-startup/06-07-audit-2026-07-28.md`。

本图不注册或晋升 NAC、PFE、CRA、Mandate、RelationVersion、Effect Gate、Defeater planner 或
任何其他机制；不改变 V1/V2、LineContract、场景或历史证据状态；不证明中心、联邦、平台、
人工或通爻的普遍优越性；不声称真实参与者已经提出、授权、执行或接受本任务；不对网络、容器、
权限、身份、凭据或隐私安全作结论，相关内容均为
`SECURITY_REVIEW_REQUIRED / NO_SECURITY_CLAIM`。
