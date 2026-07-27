---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_R8_OPC_Constructive_Closure_v1.1/paper/通爻_主权智能主体共同现实形成_正式论文_v1.1.md
source_sha256: 42b3c6fa1da3a56ce07a20be6283d1efcfa4b15e9069b84d0634934067f86b6c
source_line_start: 2944
source_line_end: 3050
source_heading: "23　前瞻性 OPC 真人实验：数据标准、实验设计、现实效力与多 Agent 基础设施"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 23　前瞻性 OPC 真人实验：数据标准、实验设计、现实效力与多 Agent 基础设施

## 23.1 证据缺口：为什么必须做真人实验，但不能让真人替我们调试基本理论

公开材料已经说明真实 OPC 会组合平台、软件、社区、承包商、伙伴与人类经纪；形式模型已经说明某些错误可由 Mandate、版本、资源与 Effect Gate 阻断；OPCBench 已经把语义价值、拓扑价值、形成价值和编译价值拆开。然而，这些证据都不能回答四个只能由真实责任主体承担的问题：Principal 是否真正理解并愿意委托；某条新路径是否由形成动作因果地产生；Operation 是否改变了目标世界并被相称主体接受；系统相对平台、强中心 Agent 和优秀人类经纪是否有正净值。

因此，真人实验不重新证明静态画像不完备、Attempt 不等于 Effect 或版本图能保存历史。它只承担公开档案、代码和 sandbox 无法替代的主张。完整执行方案、表单和 Schema 随论文作为独立现场包发布；本节给出足以审查研究完整性的正式协议。

## 23.2 五阶段、逐步升级的研究程序

| 阶段 | 样本与事项 | 现实权限 | 主要问题 | 进入下一阶段的 Gate |
|---|---|---|---|---|
| H0 历史校准 | 12–20 个公开或授权 OPC 事项 | 无新增 Effect | 数据能否恢复 Authority、版本、关键转折与真实结果 | 核心事件可定位，编码缺失不系统偏向某一机制 |
| H1 前瞻性 shadow | 6–8 个 OPC、每个 3–5 个真实事项 | 只观察和建议 | Mandate、角色冲突、Router 与注意力成本是否可测 | 事件链完整率、explain-back 与零外发 Gate |
| H2 低风险可逆 Effect | 8–12 个事项 | 人工批准、金额/范围封顶 | Operation、目标域 Effect、Adoption 与 Acceptance 能否闭合 | 零未经授权 Effect；全部 Effect 可 readback 与撤销/补救 |
| H3 跨责任根形成 | 4–8 个双边或临时联盟 | 各方独立 Mandate 与拒绝 | 本地权威、countercondition 和能力组装是否产生新路径 | 至少一条可消融形成路径；拒绝、权利、质量与退出可追溯 |
| H4 重复、编译与漂移 | 至少 6 条完成关系 | 稳定局部可确定性运行 | 第二/三次运行是否降本；Defeater 是否只局部重开 | 复用价值为正且错误不增；under/over-reopen 可审计 |

H0 已由本轮 20 案例、59 过程事件的公开语料启动，但单编码者公开档案不能代替 H1–H4。各阶段均允许返回设计：失败必须转化为 Schema、Router、界面、安全机制或适用域的 Design Delta，而不是被归咎于“用户不会用”。

![真人实验的五阶段递进与停止门。](../figures/fig12_human_trial_phases.png){width=96%}

## 23.3 参与者与事项纳入标准

OPC/超级个体参与者必须对至少一个真实经营域拥有原生决定权，例如品牌、预算、数据、账户、时间、交付或最终接受；可以有承包商和小团队，但必须能够识别外部责任根。跨责任根事项至少有两个不能互相代行的 Principal 或 Authority Locus。

一个 live matter 必须同时满足：正在发生或 30 天内发生；至少一个 material condition 不能被固定平台字段无损表达，或明确作为 CollapseSafe 负控制；首轮 Operation 低风险、可逆、可补偿或风险封顶；存在目标世界 before/after readback；参与者允许最少 T+7/T+30 随访；数据边界可以被分级。

标准付款、普通日历安排和已有成熟 SOP 的事项作为负控制；高风险医疗、重大法律/金融行动、未成年人、不可逆公开发布、重大自动支付、未经授权数据访问及无法获得真实决定者的事项排除。

## 23.4 数据标准：D0–D8、Q0–Q5 与 P0–P4

研究的最小单位不是聊天消息，而是一个带来源、时间、版本、权威和现实后果的 `Case Episode`。每个 material event 至少保存：`event_id`、`case_id`、Entity/Authority Locus、RelationVersion、Mandate、事件类型、发生/观察/记录时间、actor/issuer、输入引用、输出或声明、provenance、Effect 引用、隐私级别和前序哈希。

数据分为九类：D0 招募/同意；D1 Entity 与 Authority Map；D2 冻结的协调前私有前态；D3 Mandate 与策略；D4 RelationVersion 与 Stance；D5 Agent/模型/工具轨迹；D6 Operation、Effect 与目标世界证据；D7 Adoption、Acceptance、Settlement 与后悔；D8 成本、注意力、披露与体验。任何因果形成主张必须具有 D2、D4、D5、D6；任何真人闭环主张还必须具有 D3、D7 和随访。

数据充分性采用 Q0–Q5：Q0 只有叙事线索；Q1 可追溯事项；Q2 权威可判定；Q3 现实闭合；Q4 反事实可比较；Q5 有纵向复用和后悔。核心 H2/H3 结果至少达到 Q4，关于长期接受与编译价值的主张必须达到 Q5。

隐私采用 P0 Public、P1 Research-shareable、P2 Restricted、P3 Local-only 与 P4 Non-recordable。P3/P4 不因“模型需要上下文”而集中；系统保存相称主体已评估某边界的事件、cut、证明或聚合，不复制其内容。传输、计算、保留、派生、训练和再披露权分别记录。

![真人实验的数据充分性阶梯。](../figures/fig11_human_data_quality_ladder.png){width=90%}

## 23.5 每个事项必须产生的研究制品

每个事项至少产生：Case Screening；Participant/Entity/Authority Map；Frozen Pre-state；Mandate 与人工 Gate；RelationVersion 历史；Unknown/Defeater/Countercondition；Coordination Plan；Agent/工具/人工事件链；资源预留与 Commitment；Operation Specification；目标世界 Effect readback；Adoption/Acceptance/Reject/Defer/Dispute；成本与披露指标；独立 Outcome Adjudication；T+7/T+30（必要时 T+90）随访；以及本事项产生的 Design Delta。

参与者不需要填写一张巨大表单。典型投入是 20–35 分钟前态访谈、10–15 分钟 Mandate explain-back、每个 material change 5–10 分钟差异确认、一次低风险 Operation 决定、Effect 后 5–10 分钟接受判断，以及短随访。系统负责结构化和指出缺口；参与者只负责原生事实、授权、拒绝、承诺与接受。

## 23.6 五个强基线与公平性

真人研究使用五个条件：A 固定平台/标准表单；B 扁平强中心 Agent；C 权威感知中心 Hub；D 本地世界 + 联邦 Relation；E 有真实经验的人类经纪。A 必须是事项所在领域真实可用的平台流程；B 可以主动提问、调用相同工具和提出 probe，不能被故意削弱；C 保留 Authority、Mandate、RelationVersion、Effect/Acceptance，但部署集中；D 只在信息不可集中或 Hub 不可信时检验拓扑增量；E 不能由普通 LLM 角色扮演冒充。

各机器条件冻结同一前态，使用同一模型、temperature、工具、现实权限、token/提问/时间预算、重试和停止规则。研究系统不得独占更高质量的人工帮助。由于同一真实世界无法并行复制，首轮采用 live 运行 + 时间冻结离线 replay + 匹配事项/次序平衡 + 盲化独立裁决；不伪装成大样本随机对照。

## 23.7 预注册假设与形成因果判据

主要假设为：`H_sem` 权威语义减少 wrong authority、false commitment 与 Effect/Acceptance 混淆；`H_topology` 在不可集中条件下减少敏感披露而不显著损失处置；`H_formation` 至少存在一条路径在可消融 formation operator 后才进入合格行动空间；`H_routing` 标准事项旁路重型形成；`H_compile` 重复运行降低高认知成本且 material change 只局部重开；`H_explain` Participant 能正确解释 Mandate、版本、下一 Operation、Effect witness 和撤销方法。

一条路径只有同时满足七项条件，才记为 `causal formation candidate`：冻结前态中不可达或不合格；形成动作可定位；动作后至少一个真实资格条件变化；相称 Authority 对新版本作出 Stance；进入 sandbox 或现实 Effect；移除该动作/伙伴/工具/授权/反条件后路径消失或降级；并记录“优秀经纪本可发现”“原信息遗漏”与“后见重写”等竞争解释。

## 23.8 主要指标

主要终点不是成交率，而是：

1. `T_truth`：到达有证据的 `COMMIT / REJECT / CONDITIONAL / DEFER_UNKNOWN / WITHDRAWN / DISPUTED` 的时间；
2. `H_cog`：需要理解、判断风险、授权和处理例外的人工分钟；
3. material condition recall；
4. 加权敏感披露、接收范围与重建风险；
5. false commit、false reject、wrong authority、unauthorized Effect、stale-version action 和 Effect/Acceptance conflation；
6. explain-back 核心字段正确率；
7. causal formation gain 与消融结果；
8. Router 的 false collapse、false heavy-route、late reopen 与 over-reopen；
9. 第二/第三次运行的注意力、披露、轮次、成本、错误和后悔变化；
10. 在 Participant 明确权重下的净值，而非研究者未经授权的单一总分。

首轮报告配对差异、区间、过程追踪、负例和 Design Delta，不用小样本 p 值包装普遍性。

## 23.9 多 Agent 拓扑与基础设施

每个责任根拥有逻辑本地节点，内部可由 Interview、Mandate Compiler、Context Compiler、Boundary Oracle、Formation Planner、Router、Capability Assurance、Commitment、Operation 与 Observer 等角色协作。角色是权限和职责边界，不要求十个长期自治进程。Agent 之间交换的是 Entity/Mandate 引用、RelationVersion、Assertion、Unknown、countercondition、evidence reference、Capability assurance、Commitment、reservation receipt、Operation、Effect receipt、Acceptance 与 Defeater；自然语言是解释层，不是唯一权威状态。

![R8 真人实验与纵向参考实现的技术—观测架构。](../figures/fig10_r8_trial_architecture.png){width=96%}

最小基础设施包括：可认证 Entity 与工作负载身份；版本化 Mandate/Policy Store；本地世界与 Oracle；Relation Workspace；组合 Router；Reservation/Commitment Ledger；durable workflow；目标世界 Effect Connector；Acceptance Console；hash-chained Event Graph；模型/Prompt/Tool registry；成本与可观测性；隐私感知导出；撤销、冻结和补偿路径。

A2A 可以承载 Agent 的发现、Message/Task/Artifact；MCP/OAuth 可以承载工具和资源访问；VC/SPIFFE 可承担声明与工作负载身份；Cedar/OpenFGA 可作为策略和关系授权适配器；CloudEvents 可作为事件外壳；Temporal 可承担长周期可恢复工作流；OpenTelemetry 可采集 traces、metrics 和 logs。它们都是可替换组件，不替代 Principal、Mandate、RelationVersion、Commitment、Effect 或 Acceptance 的本文语义。

要验证的不是“消息能否互发”，而是：本地 Agent 是否只暴露任务相关边界；Coordinator 是否不能代替各方认领；Mandate 撤销是否传播；资源是否避免双重承诺；Operation 是否引用精确版本；Effect 是否由目标域而非执行方自证；同一关系中拒绝、退出和争议是否保持；稳定子图是否能被编译而 material Defeater 只重开依赖闭包。

## 23.10 首个建设性案例

推荐首例为三名 OPC 的受限数据联合交付。A 拥有客户关系和最终责任，B 提供数据处理，C 提供设计与演示；客户数据不得离开指定域、不得训练、预算和署名受限，最终验收尚未完全定义。固定平台能发现候选或支付；中心优化可排期；人类经纪可解释高语境；联邦形成负责本地数据边界、反条件与独立认领；确定性服务执行只读凭证和工单；目标域 connector 验证分析结果进入客户 backlog；最终 Acceptance 由 A 或客户权威完成。

建设性形成可能是：B 最初要求原始数据，数据 Authority 拒绝；系统提出“代码进入客户域、只读 query、禁止训练、结果脱敏、凭证自动过期”的 RelationVersion；sandbox probe 证明 B 的容器能在该边界运行；各方预留时间和预算后执行。若移除本地 Oracle、probe 或数据使用授权，路径不再合格，才支持形成主张。若权威感知中心 Hub 可以在相同披露边界下等价完成，则结论应是该事项不需要联邦拓扑。

## 23.11 安全、停止和独立裁决

首轮默认 shadow 或 human-in-the-loop；禁止自动重大付款、法律签署、删除、不可逆发布和未授权训练；凭证短期、最小权限、可撤销；P3 数据不出域。出现无法解释 Mandate、未经授权 Effect、预算超限、第三方被隐瞒、Effect 无法 readback、凭证无法撤销、严重角色胁迫或无法恢复时，立即停止，冻结新 Operation，撤销凭证和预留，保存事件链并进入事故复盘。

独立裁决者在盲化机制名称的条件下判断 truthful disposition、material conditions、正确 Authority、Effect、Acceptance、形成增量、竞争解释、第三方影响和 Q0–Q5 证据等级。系统输出不能同时充当结果真值。

## 23.12 实验价值、成立 Gate 与 Owner 资源

该研究的理论价值是检验真实 Mandate、形成因果、Effect/Acceptance 与编译复用；技术价值是校准 Router、界面、Effect Connector、事件图、策略和重开；产品价值是识别用户真正愿意委托的边界、何时系统应退场以及价值主要来自形成还是复用。高价值负结果包括：人类经纪更优、中心部署已足够、用户无法维护显式 Mandate、Router 不可靠或重复运行不能降本；每一种都收缩适用域并改变架构。

进入扩大研究前至少要求：事件与版本可重放；零未经批准 Effect；explain-back 安全关键字段通过；至少一条可消融形成候选；标准任务不过度路由；第二次运行在至少一种真实成本上下降且错误不增。首轮 Owner 最小资源为：3–5 个可授权历史事项；6–8 位愿意参加 shadow 的 OPC，或先以 Owner 自身 10–20 个事项启动；2 个 30 天内可发生的低风险 live candidate；每个事项的真实决定者；可撤销 Effect 环境；一至两名独立裁决者；以及事件结构、耗时和脱敏结果的记录授权。

