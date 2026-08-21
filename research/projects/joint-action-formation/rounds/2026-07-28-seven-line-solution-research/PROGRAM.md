# 七母线解题研究：持续运行纲领

状态：`STARTED / PRODUCT-MECHANISM-REBASE-2026-08-01`  
启动日：2026-07-28  
正式问题：`Problem v2 / ACTIVE`，同时保留并直接读取 `Problem v1 / CANDIDATE`  
Agent 指令：仓库根 `AGENTS.md`。这里所称 Agent Markdown 不指 AgentOS，也不创建第二套指令。

## 本轮唯一目标

找到、组合、实现并检验能够解决 V1/V2 原问题的最好方法。强中心、通用模型、成熟平台、
现有协议、人工制度、adapter、Router、状态收敛或它们的组合，只要可复现、可复用、可迁移
地解决问题，就是通爻的正向成果。只有经过条件匹配、完整任务和组合消融后仍存在稳定断点，
才进入自研；需要创新时要完整解决该有界问题，不做为了保留“原创增量”的表面补丁。

本轮不以七份报告、Agent 数量、形式完整或单个机制胜负为完成。最终产物应是：

- 可执行的解决方案图；
- 每种单项方法与组合方法在同一任务分母上的结果；
- 适用条件、失败、依赖风险、替换和迁移方法；
- 尚未解决的断点与下一项能区分方案的行动。

2026-08-01 新增产品约束：机制比较只是研究工具，不能成为产品内容或连续主目标。每次比较必须
先绑定一个真实用户任务、一个具体产品机制选择以及会导致 `ADOPT / COMPOSE / REMOVE /
INVENT / KEEP_UNKNOWN` 的可观察结果；不能说明结果会改变哪个产品行为、接口或状态时，不启动
比较。Wave025 已定位为按需内部工具，停止无条件补齐而不否定必要设施；能防止重要假绿、区分
具体产品方案且没有更小替代的评测，仍应完整建设。通用 3,200 比较系统当前不再是主线。当前方法纠偏见
`../../studies/product-mechanism-rebase-2026-08-01.md`。

## 启动输入

每个研究单元必须直接读取与自己有关的原始内容，不能只读本文件：

1. `research/NOW.md`；
2. `problem/v2.json`、`problem/v2.md` 与保留的 `problem/v1-candidate.json/.md`；
3. `problem/activation/v2.json` 所冻结的五件激活材料；
4. `research/projects/a2a-reconstruction/04_audit/` 中的来源注册、39 项能力矩阵、系统能力图
   和本线 native dossier；
5. 根 `AGENTS.md`；
6. 机制研究时的正式 profile 和原始档案；NAC 还必须读取
   `nac-seven-archive-manifest.json` 的七件内容。

已激活的旧 LineContract 是历史证据，其中“独立价值”“不可替代增量”“净增量”等表达
不得再作为本轮通爻价值函数，也不得静默改写。局部因果消融仍可测某组件的增量，但只用于
判断组件责任，不用于判断通爻是否有价值。

## 共同研究方法

每条母线都按自己的原生问题组织异质研究群体，至少覆盖六项职责：

1. 问题重建：重新读取 V1/V2、native dossier、正例与 removal failure；
2. 开放发现：持续寻找最新、最强、最可能使当前路线多余的现成方案；
3. 建设性求解：采用、组合、wrap、fork、重实现或完整创新；
4. 反例攻击：寻找隐含前提、假成功、负组合效应和不可达边界；
5. 任务实验：冻结输入和评分后运行单项、组合、留出与迁移；
6. 独立综合：在不知道期待答案的情况下，判断什么真正改变了任务。

并发槽不足时六项职责分波运行；同一 Agent 不能同时生成任务真值、实现方案并给自己评分。
七条线可以共享任务和接口，但不能共享未经各线独立检验的结论。

每轮只返回六项：新变量；当前最佳单项/组合解；任务改变；逐项结果；失败与替代解释；
下一项最能区分方案的行动。

## 冻结任务组合

这些是本轮理论、方法、实现和模拟的共同分母。它们包含现实任务结构，但当前均不能冒充
真实参与者事件或生产结果。

### T1 `DYNAMIC-UNDECLARED-DISCOVERY`

证据级别：`HIGH_FIDELITY_SYNTHETIC`。  
任务：一个主体只有模糊价值目标；需求、角色、能力和关系未被预先写成卡片。多个端侧世界
持续变化，主体不愿完整披露。系统需要发现潜在互补关系，也要允许拒绝与不可发现。

冻结要求：

- R1 不以预制 query、Agent Card 或完整能力声明作为成功前提；
- R2 动态变化能够使旧索引失效并触发正确更新；
- R3 找到任务相关投影，而不是全世界汇聚；
- R4 记录披露内容、接收者、目的、保存期和拒绝；
- R5 区分未表达、未知、不愿披露、确实不存在；
- R6 对至少一类零披露不可发现机会给出诚实边界；
- R7 错误唤醒和结构性漏检可测；
- R8 输出能进入关系构成，而不是停在搜索结果。

### T2 `ENTERPRISE-READONLY-PILOT`

证据级别：`ARCHIVAL_DESIGN_EXAMPLE`，不是已发生事件。  
来源：
`Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/`
`Towow_A2A_Independent_Research_v0.4/real_world_protocol/04_示例案例_企业AI只读试点.md`。
任务：原始 raw export/training 路径被拒，改为代码进入买方域、只读、no-training、买方
权威 readback，并形成可接受结果。

冻结要求：

- R1 保留业务、数据、技术、执行和接受权威的差异；
- R2 拒绝 raw export 后不把目标偷偷降级为“有一份报告”；
- R3 code-to-data 方案的权限、用途、版本、撤销和恢复可表达；
- R4 能力在具体 executor/environment/permission 下先资格化再承诺；
- R5 执行结果由买方目标域独立 readback；
- R6 Effect、Adoption、Acceptance 分别判断；
- R7 失败、重复、回滚和补偿留下可追溯证据；
- R8 第二次运行能安全复用而不沿用失效授权。

### T3 `RESOURCE-REQUEST-COLLABORATION`

证据级别：`NEW_SYNTHETIC_TASK_CANDIDATE / NOT_ARCHIVAL_REAL_WORLD_TASK`。  
真值纠正：`TASK-TRUTH-CORRECTION-001.md` 已确认历史 `R7_RESOURCE_REQUEST.md` 只是未来实验
执行资源清单，没有请求前态；它不能作为本任务的现实来源。以下任务由本纲领新构造，只能用于
产品机制假设与模拟，直到取得独立真实任务材料。
任务：跨独立权威域发起非标准资源请求，允许对方拒绝、反提案、限定用途、撤销，并需要最小
现实后置状态和接受证据。

冻结要求：

- R1 请求、资源 owner、受益者、受影响者和执行者不预设重合；
- R2 允许拒绝、counter、defer、撤销和局部接受；
- R3 形成的关系版本能被双方修改和追溯；
- R4 资源、时间、用途和责任不会被重复承诺；
- R5 能力与授权分别验证；
- R6 现实动作前存在明确 authority gate；
- R7 后置状态和 Acceptance 来自独立权威源；
- R8 与标准平台购买负控相比不增加无谓流程。

### T4 `JOINT-BID`

证据级别：`HIGH_FIDELITY_SYNTHETIC`。  
任务：三个主体分别持有局部能力、容量、价格和风险信息；完整投标方案事前不存在，需要在
有限披露下形成角色、组合能力、资源预留、执行与验收条件。

冻结要求：

- R1 能发现事前未登记的互补组合；
- R2 私有行动集只披露必要 column、界或反例；
- R3 角色、动作、证据、退出和评价规则可共同形成；
- R4 组合能力与稀缺资源在提交前资格化和预留；
- R5 预算与签署权不由能力声明推出；
- R6 提交/受理/采用/接受分别可失败；
- R7 任一成员撤销后只重开受影响路径；
- R8 方案可迁移到不同主体与行业变体。

### T5 `COLLAPSESAFE-SIMPLE`

证据级别：`NEGATIVE_CONTROL`。  
任务：标准 SaaS 购买、标准支付或固定平台内任务。成熟平台/强中心应直接完成；任何复杂
关系构成、formation 或联邦机制都必须能旁路。

冻结要求：

- R1 现成方案能直接被采用；
- R2 不制造第二事实源；
- R3 不增加多余披露和审批；
- R4 总等待、认知、治理和恢复成本不高于平台基线；
- R5 失败仍由原平台权威状态判定；
- R6 通爻方案能明确退化为轻量 adapter 或零新增机制。

### T6 `REPEAT_AND_DRIFT`

证据级别：`MUTATION_REPLAY`。  
任务：重复 T2/T3/T4 的成功路径，再依次注入模型升级、权限撤销、证据失效、账号离线、
目标变化、隐藏依赖、高耦合和低漂移对照。

冻结要求：

- R1 第二次运行降低成本且不增加错误；
- R2 暂时不可用与规范关系失效不会混淆；
- R3 撤销及时阻断依赖动作并保留无关动作；
- R4 证据失效传播到全部未来依赖，不改写历史；
- R5 目标变化回到问题/关系构成而不是由工程反向定义；
- R6 隐藏依赖触发 Unknown、阻断或人工升级；
- R7 高耦合时允许诚实退化为全局重开；
- R8 history/context 可移植，不绑定单一 runtime。

## 评分与组合比较

每个任务的每项要求在运行前冻结，结果只可取：

- `PASS=1`；
- `PARTIAL=0.5`，必须列出未覆盖部分；
- `FAIL=0`；
- `UNKNOWN=0`，另行报告 Unknown 比例，不得因缺证据获得分数；
- `NOT_RUN` 不进入完成声明。

要求覆盖率：

\[
Coverage(M,T)=100\times \frac{\sum_i w_i s_i}{\sum_i w_i}
\]

本轮初始所有要求 `w_i=1`；若以后改变权重，必须生成新任务版本，不能追改旧结果。每种
方法 A、B、C 和组合 A+B、A+B+C 使用同一输入、要求、真值与 evaluator。必须同时报告：

- 关键底线是否通过；
- 要求覆盖率和逐项状态；
- 误闭合、漏掉可行路径、拒绝保真；
- 披露量、询问轮数、模型调用、等待、人工判断和治理负担；
- 恢复、扰动鲁棒性、复现和跨任务迁移；
- 组合增益 `Coverage(A+B)-max(Coverage(A),Coverage(B))` 及负组合效应。

只有覆盖率高不能称为解决。任一任务指定的 authority、privacy、Effect/Acceptance 或
unsafe-continuation 关键底线失败时，结果最高只能是 `PARTIAL_SOLUTION`。一条母线进入
`INTEGRATED_SOLUTION` 至少需要两个异质任务族和一个留出变体通过关键底线，且关键依赖
有替换或迁移路径。

## 七个母线目标

### G1 `DISCOVERY-BEFORE-SEARCH`

目标：在动态、未声明、局部私有的世界中，使潜在互补关系获得足够可见性，并画出最低披露
—可发现性前沿及不可发现边界。ARD/catalog/Agent Card 是“已表达对象索引”基线；RAG 只
处理已表达材料。比较强中心+本地工具、端侧事件检测与任务投影、互惠 probe/local oracle、
隐私计算及 NAC。主任务 T1，迁移 T2/T4，负控 T5。

指标：机会召回、错误唤醒、未表达机会恢复、披露量、询问轮数、更新滞后、拒绝保真和迁移。
若所有现成方案仍预设 query/card，才研究“端侧机会生成器+可协商最小投影+互惠披露+
不可发现性证书”的完整方案。NAC 是独立子研究，不替代母线。

### G2 `RELATION-FROM-TASK`

目标：当参与者、角色、动作、证据、用途、退出和评价规则未给定时，形成可共同修改、保留
局部异议、可版本化并能进入求解/执行的关系表示；私有行动集只贡献必要 column/counterexample。
比较 CMMN/BPMN+HITL、强中心模型、CLM、commitment/negotiation、DCOP/column generation、
开放多作者 workspace 及组合。主任务 T2/T3/T4，负控 T5。

指标：可执行提案率、必要语义覆盖、material change 召回/误报、provenance、异议保留、
泄露、错误无解和迁移。现成方案完整解决就成为通爻 Relation 层；稳定断点才进入自研。

### G3 `FORM-REACHABILITY`

目标：诊断不可达原因并选择 ask/search/probe/tool/partner/authority/task-representation/exit
等动作，把当前不可达变为可达，或给出可行动的不可达解释；区分发现既有路径、创造条件、
降低目标和普通 amendment。比较 planning/POMDP/HTN、action-model learning、CEGIS、
constraint acquisition、program synthesis、tool-using model、HITL 及组合。主任务 T2/T4，
迁移 T1，负控 T5。

指标：新增合格路径、错误 formation、正确下一动作、形成步数/成本、无效循环、错误改写、
越权动作、operator 消融和迁移。只有固定 action/role/schema 的断点反复出现，才研究可共同
扩展 action model、主体集合、任务表示和 probe 的完整 formation planner。

### G4 `CAPABILITY-TO-RELIANCE`

目标：预测具体 operation 在 executor/environment/version/permission/resource/recovery
条件下能否首次完成，并在组合、漂移和恢复中保持可依赖。比较 CI/eval、readiness、IAM、
reservation、telemetry、workflow、attestation/assurance 与强模型动态诊断。主任务 T2/T4/T6，
负控 T5。

指标：首次预测 precision/recall/abstention、误承诺、资源冲突、漂移检测、恢复和迁移。
成熟组合完整通过就直接成为通爻能力层；只有前瞻性跨来源资格化仍稳定误闭合才创新。

### G5 `AUTHORITY-COMPOSITION`

目标：完整解决 identity、capability、Principal/AuthorityLocus、Mandate、versioned stance、
Commitment、Reservation、Standing 之间的非蕴含和状态推进。比较 RBAC/ABAC/ReBAC、
XACML/OPA/Cedar/OpenFGA、OAuth/GNAP/RAR、VC/SD-JWT、delegation、approval/CLM、
reservation 与 commitment protocol 的公平组合。主任务 T2/T3/T4/T6。

指标：false allow/deny、stale stance、撤销传播、重复预留、standing challenge、事实冲突、
维护成本与迁移。成熟栈+adapter 完整解决就纳入；只有跨语义与权威来源的稳定断点才自研。

### G6 `EFFECT-THAT-COUNTS`

目标：使 ActionAttempt、Effect、Adoption、Acceptance、Settlement 在不同 authority domain
下分别成立或失败并可重建。比较 transaction/outbox、CloudEvents、event sourcing、
durable workflow、Saga、CDC、idempotency、独立 readback 和 human acceptance。主任务
T2/T3，迁移 T4/T6。

指标：误晋升、漏 Effect、重复副作用、readback 时延、Adoption/Acceptance 混淆、补偿残差、
追溯和 connector 迁移。现成组合零误晋升并满足迁移即成为通爻 Effect 层；创新只针对跨
authority residual。

### G7 `REUSE-AND-SAFE-REOPEN`

目标：把前六线完整解变成可恢复运行能力；编译稳定子图、生成最小充分 Context、监控依赖/
Defeater，并在漂移时安全选择继续、阻断、恢复或局部重开。比较 immutable contract+人工
amendment、durable workflow/migration+telemetry、dependency/defeater planner 和强中心
运行管理。主任务 T6，复用 T2/T3/T4，负控 T5。

指标：重复成本、unsafe continuation、漏重开、误重开、恢复时延、Context sufficiency、
history 可移植与平台迁移。若成熟 workflow+人工 amendment 完整解决就采用；只有跨 Authority/
Evidence/Effect/Acceptance 依赖不能表达时，才研究 Relation compiler 与 dependency-sensitive
reopen 的完整体系。

## 外部技术采用、自持与创新门

每项候选技术都必须回答：真实覆盖与必要前提；维护组织和 bus factor；release/兼容性；
格式与 V1/V2 状态是否有损；安全、隐私和信任假设；许可、专利、云成本；性能和规模；
observability/replay；退出、替换和双向迁移；adapter 是否制造第二事实源；自持最小替代
实现成本。

选择空间为 `ADOPT / WRAP / FORK / REIMPLEMENT / INVENT / REJECT_FOR_THIS_SCOPE`。不是
“现成=好”或“自研=原创”；关键语义、低成本可自持且外部依赖高风险时，应建设自有内核或
conformance layer。专利机会只能在问题和解法成立后登记。

## 历史错误与防复发门

| 错误 | 原因 | 复发信号 | 阻断动作 |
|---|---|---|---|
| 把现成方案胜出写成通爻价值为零 | 错把独占增量当价值函数 | “最多只是 adapter” | 回到 V1/V2 解题程度；采用与组合正式进入方案 |
| `发现→RAG/目录` | 技术名词先于条件 | 未说明 query、表达和动态世界 | 先冻结任务输入与失败，再准入技术 |
| 把 ARD 索引写成完整发现 | 混淆已表达检索与可能性形成 | 默认 card/Intent/能力已声明 | 单列 search-before-query 和未表达切片 |
| 忽略披露—可能性前沿 | 同时承诺零披露和完整发现 | 没有 disclosure budget/refusal | 记录披露、拒绝、Unknown 和不可发现边界 |
| 漏掉 ARD 等最新工作 | 由旧术语驱动 horizon scan | 只查熟悉技术菜单 | 每线配置开放发现职责，主动寻找使当前路线多余的方案 |
| 单 Agent 代表母线 | 报告代替竞争路径 | 同一主体出题、构造、攻击、评分 | 六职责分离并保留独立返回 |
| 无任务或主观百分比 | 形式对象替代结果 | 没有要求分母和独立真值 | 冻结 T1–T6 与逐项状态后才能计分 |
| 过早形式化 | 合规压力压倒发现 | schema/test 多于新变量和任务改善 | 先任务、异常、组合、原型和反例 |
| 只看外部技术功能标签 | 未审计全寿命依赖 | “支持发现/授权”即采用 | 执行维护、格式、安全、锁定、迁移、自持审计 |
| 用“最小创新”偷懒 | 把避免重复发明误成最小研究深度 | 稳定缺口只补薄 adapter | 缺口确认后完整覆盖失败、恢复、迁移和验证 |
| 为原创/专利制造缺口 | 方案收益污染问题判断 | 因可专利而排斥成熟解 | 同等解题能力后再比较自主性与专利 |
| 把 `agent.markdown` 听成 AgentOS | 擅自扩写未逐字读取的专名 | 出现 AgentOS 或近似体系映射 | 只使用根 `AGENTS.md`；专名不猜 |
| 摘要替代正典 | 为省时只读 NOW/line summary | 原档案、正例、失败未加载 | 按启动输入直接读取，机制需原始闭包 |
| 没有真人就停止理论 | 混淆现实执行与逻辑研究边界 | 把现实资源缺失当全局阻塞 | 继续理论、方法、实现、模拟和故障注入，诚实标证据级别 |

## 当前运行与停止

七个目标均为 `STARTED`，但不再各自建设评价系统。当前以 T1 的问题条件和新构造的
`PT-001-FUZZY-RESOURCE-COLLABORATION` 串成一条从模糊目标到可拒绝、可撤销、可执行、可验收
资源协作的端到端产品旅程；七条母线共同提出产品状态、成熟
机制组合、精确缺口和最小产品实验。Wave025 只在某个产品机制选择确实无法判断时按需恢复。
某条线只有在以下情况进入整合：

- 某组合在两个异质任务族和留出变体上成为可复现完整解；
- 稳定断点已足够清楚，需转入完整创新；
- 结果依赖另一母线的状态，必须跨线整合；
- 继续运行只会重复同一机制，应转交回归。

缺少真人、生产权限或现实部署不是当前理论与模拟的停止条件。需要对外发送材料时另行遵守
disclosure manifest；NAC 专利交底原文保持本地，不进入第三方 payload。
