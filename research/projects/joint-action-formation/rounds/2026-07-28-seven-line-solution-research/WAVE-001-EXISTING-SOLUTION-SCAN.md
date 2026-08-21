# WAVE-001：七母线现成方案与最强组合扫描

状态：`HORIZON_SCAN_COMPLETE / TASK_VALIDATION_PENDING`  
日期：2026-07-28  
作用域：第一波开放发现；只比较可能使既有专有路线多余的通用模型、强中心、标准、平台、
算法、制度流程与 adapter。  
证据边界：本文件记录来源事实、候选组合与待检验责任断点，不报告任务覆盖率，不证明任何
候选已经解决 V1/V2，也不登记或改变正式机制状态。未向第三方发送任何专利交底原文。

## 一、任务分母资格校正

在任何单项或组合计分之前，必须先修正当前任务材料：

- `T2 ENTERPRISE-READONLY-PILOT`：原案例已经泄漏 counter、probe 和 V2 解法，不能作为盲测
  输入。须从更早的 raw material 构造 `blind/raw variant`，冻结独立真值后才能运行。
- `T3 RESOURCE-REQUEST-COLLABORATION`：当前所指 R7 材料实为执行资源清单，不是非标准资源
  请求的 task instance。它只能帮助构造新任务，不能直接运行或计算 coverage。
- `T1 DYNAMIC-UNDECLARED-DISCOVERY` 与 `T4 JOINT-BID`：当前是
  `SYNTHETIC_TASK_SPEC`，须生成冻结实例、隐藏变量和独立真值。
- `T6 REPEAT_AND_DRIFT`：当前是 `MUTATION_REPLAY_SPEC`。必须先有一条经前序研究线判定合格
  的 base trace，才能注入漂移并评价安全继续、恢复或重开。
- `T5 COLLAPSESAFE-SIMPLE`：可以作为标准平台/强中心旁路负控，但仍需建立具体平台实例与
  同一任务分母。

因此，本波只形成候选 `A`、`B`、`A+B` 与首个责任断点。任何百分比、`PASS`、完整解或稳定
缺口，都必须等合格任务实例运行后再写。

## 二、G1 `DISCOVERY-BEFORE-SEARCH`

### V1/V2 条件

主体只有模糊价值目标；需求、角色、能力和关系未被预先声明；多个端侧世界持续变化且局部
私有；不能全量汇聚、广播或让高级模型遍历所有节点。系统还必须区分未表达、未知、不愿披露
和确实不存在，并使发现结果进入关系构成，而不是停在搜索列表。

### 候选 A：ARD + A2A Agent Card

- ARD v0.9 是 2026-05-28 的 Draft/Proposal；Google 于 2026-06-17 宣布该开放规范，
  Apache 2.0，由 Linux Foundation AI Catalog Working Group 推进。
- 格式为 `ai-catalog.json`、JSON Schema、CDDL、OpenAPI 与 REST registry search；
  publisher 需显式发布 manifest，资源可引用 MCP、A2A、OpenAPI 和嵌套 catalog。
- A2A v1.0 Agent Card 用 JSON 声明 endpoint、capabilities、security 与 skills；发现方式包括
  well-known URI、registry 和直接配置。
- 官方范围明确是 `search-first`：ARD 需要 query text/filter，且建议资源提供 2–5 条
  `representativeQueries`。A2A 当前不规定统一 registry API，并建议依据 Card 通常低频变化
  进行缓存。

来源：

- [ARD v0.9 Specification](https://agenticresourcediscovery.org/spec/)
- [Google ARD announcement](https://developers.googleblog.com/announcing-the-agentic-resource-discovery-specification/)
- [A2A Agent Discovery](https://a2a-protocol.org/latest/topics/agent-discovery/)

### 候选 B：MCP + 本地强模型 + 可拒绝的 active elicitation/local oracle

- MCP 2025-11-25 通过 JSON-RPC 与 JSON Schema 提供 `tools/list`、`resources/list`、
  `listChanged` 和按授权过滤的能力枚举；适合连接内动态世界。
- MCP 已于 2025-12 捐给 Linux Foundation 下的 AAIF；官方称已有 10,000+ active public
  servers 和主要平台采用。Tasks 在 2025-11-25 版本仍是 experimental。
- 本地模型可依据端侧事件形成最小 task projection，再通过用户可拒绝的探问生成 query。

来源：

- [MCP Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [MCP Resources 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [MCP Tasks 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)
- [MCP donation to AAIF](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)

### 候选 A+B

端侧 MCP/事件检测先形成最小任务投影；强模型通过 reciprocal probe 生成可审查 query；
ARD/A2A 只检索已表达的公网或组织目录；候选返回本地后再逐步披露并形成关系提案。若该组合
完整通过任务，它本身就是通爻的发现层成果，不需要 NAC 才算成功。

### 维护、格式、锁定与自持

ARD 仍是 Draft，media type 尚待正式登记；Google 托管 registry 路线存在 egress、pinning
和产品锁定风险。A2A/ARD 格式开放，但只覆盖显式声明。MCP 治理较中立、SDK 与生态活跃，
但 tool/server 信任、prompt injection 和供应链攻击面较大；本地部署减少外泄，不消除相关
信息必须先被 surface 才能判断的事实。ARD/A2A 可 `WRAP` 并自建兼容 registry；MCP 可
`ADOPT`，最小 client/server 可自持；端侧机会生成与可协商披露若成为稳定断点，自研成本高。

### 首个责任断点

在 T1 冻结实例中隐藏一个没有 query、Card、representative query 且主体不愿初始披露的互补
机会。分别检验 A、B、A+B 是恢复、误唤醒，还是诚实标为不可发现；零披露机会本身不判算法
失败，关键是能否画出披露—召回前沿，并区分拒绝、未知与不存在。

## 三、G2 `RELATION-FROM-TASK`

### V1/V2 条件

参与者、角色、动作、证据、用途、退出和评价规则事前未给定。关系表示须可共同修改、版本化、
保存局部异议并进入求解和执行；私有行动集只贡献必要 column 或 counterexample。

### 候选 A：FIPA + commitment/information protocols

- FIPA Contract Net H 是 2002-12-06 的 Standard，使用 ACL、XML 与 AUML，支持 CFP、
  propose、refuse、accept、reject、failure、cancel 和 conversation ID。
- FIPA 原文明确真实应用仍需 elaboration；异步、取消效果、异常终止与 nested protocol
  没有被完整解决。
- Tosca（IJCAI 2017）从 commitment specification 合成 information protocol，并追求去中心
  commitment alignment。
- 组合研究给出重要负结果：两个分别可验证 enact 的协议，组合后不自动可验证，需要额外
  设计规则。Mambo（IJCAI 2025）继续研究 declarative information protocol 的 requirement
  patterns 与 verification。

来源：

- [FIPA Contract Net](https://www.fipa.org/specs/fipa00029/SC00029H.html)
- [Tosca, IJCAI 2017](https://www.ijcai.org/proceedings/2017/37)
- [Composing and Verifying Commitment Protocols, IJCAI 2015](https://www.ijcai.org/Abstract/15/009)
- [Mambo, IJCAI 2025](https://www.ijcai.org/proceedings/2025/0005.pdf)

### 候选 B：CMMN/BPMN/DMN + 强中心 Agent Framework + HITL workspace

- CMMN 1.1（2016-12）、BPMN 2.0.2（2014-01）与 DMN 1.5（2024-08；1.7 beta）提供
  XML、XSD、XMI 等标准表示。
- Camunda Modeler 5.49.0 于 2026-07-14 发布，项目仍活跃。
- Microsoft Agent Framework 在 2026 年把 AutoGen/Semantic Kernel 路线收敛为 Python/.NET
  agents、graph workflows、session、checkpoint、HITL 和 telemetry；官方同时建议确定性
  任务使用 functions。

来源：

- [OMG CMMN](https://www.omg.org/spec/CMMN/)
- [OMG BPMN](https://www.omg.org/spec/BPMN/)
- [OMG Specifications index](https://www.omg.org/spec)
- [Camunda Modeler releases](https://camunda.com/download/modeler/)
- [Microsoft Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/)
- [Microsoft Agent Framework repository](https://github.com/microsoft/agent-framework)

### 候选 A+B

强中心模型从 raw task/counterexample 生成候选 CMMN/BPMN/DMN case；各 Principal 本地保留
权威与私有 action view；commitment protocol 只表达双方可观察的 social state、异议、
amend/cancel；workflow 负责执行，不成为新的权威事实源。

### 维护、格式、锁定与自持

FIPA/commitment 核心稳定但维护低活跃，且要求显式任务、角色和 message semantics。OMG
标准成熟但版本较老，跨引擎 portability 通常只覆盖标准子集；Camunda extension、runtime 和
云服务形成锁定。Microsoft Agent Framework 活跃但 API 与编排仍在演进。标准 schema 可
`ADOPT`；引擎宜 `WRAP` 并保留 export/conformance；自建完整 workflow engine 成本高，
自建有界 relation kernel/adapter 成本中等。

### 首个责任断点

从 T2 blind/raw variant 或新造 T3 task instance 出发，不提供角色、退出和 Acceptance
schema，让 A、B、A+B 形成可执行提案。首测不是“是否生成文档”，而是 material change 后
能否保存双方异议、精确重开，并避免把能力或提案误当授权。

## 四、G3 `FORM-REACHABILITY`

### V1/V2 条件

不可达可能来自路径未发现、缺工具、伙伴、权限或条件、任务表示错误，或原则性不可能。
系统须选择 ask/search/probe/tool/partner/authority/task-representation/exit，不能把降低目标
或普通 amendment 冒充 formation。

### 候选 A：incomplete-domain planning + action-model learning

- DeFault/Goalie（ICAPS 2011）在 incomplete domain 下规避失败，并从执行中学习 action
  precondition/effect。
- AAAI 2024 的 safe PDDL action-model learning 在 partial observability 下讨论安全性、
  probabilistic completeness 与 sample complexity。
- SoCS 2024 将缺 action 的 hierarchical domain correction 编译为 planning。
- REPOA（2025）探索 open-world planning、adaptive dependency learning 与 failure-aware
  memory。

来源：

- [Planning and Acting in Incomplete Domains, ICAPS 2011](https://ojs.aaai.org/index.php/ICAPS/article/view/13463)
- [Learning Safe Action Models, AAAI 2024](https://ojs.aaai.org/index.php/AAAI/article/view/29995)
- [Hierarchical Planning with Missing Actions, SoCS 2024](https://ojs.aaai.org/index.php/SOCS/article/view/31542)
- [REPOA, 2025](https://arxiv.org/abs/2505.24157)

### 候选 B：tool-using general model + Agent Framework + AutoAgents + HITL

AutoAgents（IJCAI 2024）动态生成 specialized roles、agents 和 plan，并使用 observer
reflection；Microsoft Agent Framework 提供 graph、checkpoint 与 HITL。该组合可能让固定
角色或固定 solver 变得多余，但现有 benchmark 不能代替 V1/V2 任务。

来源：

- [AutoAgents, IJCAI 2024](https://www.ijcai.org/proceedings/2024/0003)
- [Microsoft Agent Framework repository](https://github.com/microsoft/agent-framework)

### 候选 A+B

模型和多 Agent 提出新 operator、ask、probe、tool、partner 或 representation；安全 planner
或 constraint learner 验证前提、比较成本并避免循环；Authority Gate 把信息增益 probe 与
可执行动作分开；HITL 只在价值、风险和责任点裁决。

### 维护、格式、锁定与自持

论文算法多要求显式 goal、state/action formalism，或至少可学习 observation；REPOA 和
AutoAgents 较新，证据主要来自 benchmark。Agent Framework provider-flexible，但 runtime
和 API 仍有漂移。Planner 可 `REIMPLEMENT` 有界内核，成本中高；Framework 宜 `WRAP`。
只有共同扩展 action model、主体集合或 task representation 的断点反复出现，才进入完整
formation planner 的 `INVENT`。

### 首个责任断点

在 T2 blind/raw 或 T4 frozen instance 中隐藏一个必要 partner/tool/authority，同时放入一个
表面相似但不可行的 operator。比较 A、B、A+B 能否选择正确下一动作、避免越权和无效循环，
并在确实不可达时给出可行动解释。

## 五、G4 `CAPABILITY-TO-RELIANCE`

### V1/V2 条件

Capability 不能推出具体 operation 在 executor、environment、version、permission、resource
与 recovery 条件下首次完成。研究对象是执行前预测、资格化或诚实 abstain，以及组合、漂移
和恢复中的持续可依赖性。

### 候选 A：CI/eval + Kubernetes + Temporal + OpenTelemetry

- Kubernetes startup、readiness、liveness probes 的语义不同；官方明确错误 probe 可触发
  级联失败。
- OpenTelemetry 当前规范为 1.59.0，提供 traces、metrics、logs 和 OTLP；telemetry 是观察，
  不是完成证明。
- Temporal 当前 server release 为 v1.31.2（2026-07-08），提供 durable workflow、
  checkpoint/replay 与 retry。

来源：

- [Kubernetes probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-probes/)
- [OpenTelemetry Specification 1.59.0](https://opentelemetry.io/docs/specs/otel/)
- [Temporal Workflows](https://docs.temporal.io/workflows)
- [Temporal releases](https://github.com/temporalio/temporal/releases)

### 候选 B：in-toto + SLSA + SACM + 强模型动态诊断

- in-toto 是 CNCF Graduated 项目，以开放 metadata 和 Apache-licensed tooling 描述供应链
  步骤、执行者与顺序。
- SLSA 1.2 在 2026 年是 Approved specification，提供 provenance 与 verification summary
  结构。
- OMG SACM 2.2（2021）用 EMOF/XML 表达 assurance argument、evidence 与 terminology。

来源：

- [in-toto](https://in-toto.io/)
- [SLSA 1.2](https://slsa.dev/spec/v1.2/)
- [OMG SACM 2.2](https://www.omg.org/spec/SACM/2.2)

### 候选 A+B

为 operation 建立 conditional qualification envelope：CI/probe/IAM/quota/reservation 采集
当前条件；in-toto/SLSA 绑定 artifact/build provenance；Temporal 运行；OpenTelemetry 观察；
目标 authority 独立 readback。SACM 和模型只生成可审计 inference，不能晋升权威状态。

### 维护、格式、锁定与自持

Kubernetes、OpenTelemetry 与 in-toto 成熟且可替换；SLSA/SACM主要保真来源与 argument，
不是 runtime truth。Temporal 可自托管，但 deterministic replay、数据库 schema upgrade 与
Event History 上限形成迁移成本。优先 `ADOPT` 开放标准、`WRAP` runtime，并保留 workflow
export/readback adapter；自建 durable runtime 成本高，自建 qualification/readback layer
成本中等。

### 首个责任断点

在 T2 blind/raw 与 T4 frozen instance 中制造“同能力名、不同 permission/version/resource/
recovery”的 executor，测首次预测的 precision、recall 与 abstention。对只能在执行后获知的
unique/destructive side effect，候选必须 abstain 或进入 Authority Gate。

## 六、G5 `AUTHORITY-COMPOSITION`

### V1/V2 条件

Identity、Capability、Principal/AuthorityLocus、Mandate、versioned stance、Commitment、
Reservation 与 Standing 互不蕴含。系统须处理撤销、冲突、重复预留和不同 authority source。

### 候选 A：GNAP + RAR + AuthZEN + PDP

- GNAP RFC 9635 是 2024-10 的 IETF Standards Track，使用 JSON grant negotiation、
  continuation 与 key-bound token。
- OAuth RAR RFC 9396（2023-05）用 `authorization_details` 表达 action、location、data、
  amount 等细粒度授权。
- OpenID AuthZEN Authorization API 1.0 于 2026-01 成为 Final，统一 PEP 与 PDP 间的
  evaluation/search API，但把 policy language、architecture 和 state management 留在范围外。
- OPA 是 CNCF Graduated 项目，以 Rego 和 JSON 输入输出；Cedar 当前文档版本为 4.5，
  使用 principal/action/resource/context/schema。

来源：

- [GNAP RFC 9635](https://www.ietf.org/rfc/rfc9635.html)
- [OAuth RAR RFC 9396](https://www.rfc-editor.org/rfc/rfc9396.html)
- [AuthZEN Authorization API 1.0](https://openid.net/specs/authorization-api-1_0.html)
- [Open Policy Agent](https://www.openpolicyagent.org/docs)
- [Cedar 4.5](https://docs.cedarpolicy.com/)

### 候选 B：VC + status/revocation + approval/reservation + commitment

W3C VC Data Model 2.0 与 Bitstring Status List 1.0 均在 2025-05-15 成为 Recommendation；
它们可承载可验证、隐私友好的资格与状态声明。OAuth Token Revocation RFC 7009 明确撤销传播
可能延迟，自包含 token 的即时撤销需要额外 backend 或短寿命 token。human approval、
reservation 和 commitment protocol 分别承接不可代行判断、稀缺资源与双方承诺。

来源：

- [VC Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)
- [Bitstring Status List 1.0](https://www.w3.org/TR/vc-bitstring-status-list/)
- [OAuth Token Revocation RFC 7009](https://www.rfc-editor.org/rfc/rfc7009.html)

### 候选 A+B

VC/identity 只提供有来源的声明；GNAP/RAR 形成具体用途、动作、资源和时限的 grant；
AuthZEN+OPA/Cedar 在各 Authority Locus 决策；reservation 单独占用稀缺资源；commitment
只在 stance/acceptance 后产生；依赖动作使用在线检查或短 TTL，并订阅撤销。

### 维护、格式、锁定与自持

这些技术都要求 authority、policy、resource、action 与 context 被显式表示；它们解决授权，
不生成未声明意图或关系。OPA/Rego 通用但有语言与数据同步成本；Cedar 是开放语言，而 AWS
Verified Permissions 是托管锁定路线；AuthZEN Final 中立但不管理 policy state。标准可
`ADOPT`，PDP 可双实现；自建完整 auth stack 成本高，自建 semantic adapter/receipt 成本中。

### 首个责任断点

在 T2/T4/T6 的合格实例中注入 Principal 不等于 Intent generator、capable-but-unmandated、
授权撤销、重复 reservation 与 stale stance，检验 false allow/deny 和撤销传播。没有合格
base trace 时，T6 不能直接运行。

## 七、G6 `EFFECT-THAT-COUNTS`

### V1/V2 条件

ActionAttempt、Effect、Adoption、Acceptance 与 Settlement 位于不同 Authority Domain，
可分别成功或失败。系统须避免 retry 重复副作用、把 event/trace 当 Effect，或把 Effect 当
Acceptance。

### 候选 A：outbox/CDC + CloudEvents + Temporal/Saga

- Debezium stable Outbox Event Router 从数据库 outbox insert 捕获变化，支持 JSON/Avro、
  event ID 去重与 aggregate key 保序；当前文档示例 source version 为 3.6.0.Final。
- CloudEvents v1.0.2 于 2022-02-05 发布，并在 2024-01-25成为 CNCF Graduated 项目。
- Temporal Event History 是 durable append-only execution source；Activity result 是 workflow
  的 source of truth，不自动成为外部目标域的权威 Effect。

来源：

- [Debezium Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
- [CloudEvents](https://cloudevents.io/)
- [Temporal Events and Event History](https://docs.temporal.io/workflow-execution/event)

### 候选 B：独立 readback + provenance/assurance + human acceptance

目标系统以自己的 authoritative state 提供 readback 或 consumer acknowledgement；SACM、
provenance 与 telemetry 只重建证据链；Adoption、Acceptance 与 Settlement 分别由相应
Principal 或结算权威出具 receipt。

### 候选 A+B

本地 transaction 将 command 与 outbox 原子化，CloudEvents 传播，Temporal 编排 retry 与
compensation；每一跳绑定 idempotency key。Effect 必须由目标 authority readback，
Adoption/Acceptance/Settlement 各自使用独立事件和 actor；OpenTelemetry/SLSA 不承担晋升。

### 维护、格式、锁定与自持

CloudEvents 只标准化 envelope；Debezium 依赖数据库、Kafka/connector 运维，payload 与
schema governance 仍由部署者负责；Temporal retry 不保证外部 side effect exactly-once，
补偿也可能有残差。CloudEvents 可 `ADOPT`；outbox 可用小型自持实现替换 CDC；Temporal
宜 `WRAP`；authoritative readback connector 是关键自持层，成本中等。

### 首个责任断点

在合格 T2 blind/raw 或新 T3 task instance 中注入 timeout-after-effect、重复投递、目标拒绝
采用、执行成功但验收失败、补偿不完全，检验 A、B、A+B 是否出现误晋升。当前 T3 不是
task instance，不能直接评分。

## 八、G7 `REUSE-AND-SAFE-REOPEN`

### V1/V2 条件

稳定子图应被编译复用；Context 须最小充分且可移植；系统监控真实 dependency/defeater，
并在漂移时选择继续、阻断、恢复、局部或全局重开。暂时不可用不能被误判为关系失效，旧授权
也不能被无条件沿用。

### 候选 A：Temporal Worker Versioning + OpenTelemetry + OpenFeature

- Temporal 官方在 2026 文档中把 Worker Versioning 作为生产默认建议，支持 pinned
  execution、auto-upgrade、ramping、blue-green/rainbow 与 rollback；当前 server 为 v1.31.2。
- OpenTelemetry 提供跨组件 observation。
- OpenFeature 自 2023-11-21 为 CNCF Incubating，提供 vendor-neutral feature flag API。

来源：

- [Temporal Worker Versioning](https://docs.temporal.io/production-deployment/worker-deployments/worker-versioning)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [OpenFeature at CNCF](https://www.cncf.io/projects/openfeature/)

### 候选 B：immutable contract + dependency/defeater graph + human amendment

版本化 relation contract 保存 Authority、Evidence、Effect 与 Acceptance 依赖；强中心模型
只生成 minimal Context 与 reopen 候选；material amendment 由相应 authority 或人批准。
Open Workflow Specification v1.0.0 于 2026-01-27成为最新 release，使用 YAML/JSON，可作为
portable export 候选；当前实现生态与引擎互操作性仍须实测。

来源：

- [Open Workflow Specification](https://open-workflow-specification.org/)
- [Open Workflow Specification releases](https://github.com/open-workflow-specification/specification/releases)

### 候选 A+B

每个 run 绑定 relation、evidence、authority、artifact 与 worker version；dependency graph
声明未来动作的事实依赖；OpenTelemetry/事件源发现 drift，OpenFeature/Worker Versioning
做 canary；强中心只生成候选。撤销或证据失效先阻断依赖边，material amendment 再由相应
authority 批准；高耦合时诚实退化为全局重开。

### 维护、格式、锁定与自持

Temporal pinning 解决代码版本，不自动理解跨 Authority/Evidence/Effect/Acceptance 的语义
依赖；OpenFeature 只处理 flag evaluation；OpenTelemetry 只观察；Open Workflow 1.0 较新，
引擎互操作尚未知。Temporal history、replay 与版本路由形成迁移成本，须保留 canonical
contract/event export 与双写迁移演练。A 可 `ADOPT/WRAP`；dependency contract 宜自持；
自建版本/重开判定成本中等，自建 durable engine 成本高。

### 首个责任断点

从一条经 G2–G6 判定合格的 base trace 生成 T6 replay，依次注入 model upgrade、permission
revoke、evidence expiry、account offline、goal change、hidden dependency 与高低 coupling，
检验 unsafe continuation、漏重开、误重开和 history portability。

## 九、跨线最强现成组合

当前最强的“可能让大部分专有路线多余”的候选链是：

> 本地强模型/MCP active elicitation  
> → ARD/A2A 显式目录  
> → CMMN/BPMN/DMN + commitment protocol 关系形成  
> → incomplete-domain planner + Agent Framework/HITL  
> → Kubernetes/CI/IAM/reservation + SLSA/in-toto 资格化  
> → GNAP/RAR/AuthZEN + OPA/Cedar + VC 授权  
> → Temporal + outbox/CloudEvents 执行  
> → authoritative readback 与独立 Acceptance/Settlement  
> → Temporal Versioning + OpenTelemetry + dependency contract 安全重开

若该组合在同一任务分母、两个异质任务族和留出变体上通过关键底线，它就是通爻的正向完整
成果。若失败，责任应缩到经实验确认的断点，而不是为了原创先造一套完整新协议。

可能需要自持、但仍待验证的最小内核候选只有：

1. 跨层语义无损的 receipt/adapter；
2. authority-specific authoritative readback；
3. dependency/defeater contract；
4. 外部组件的 conformance 与 exit/migration layer。

标准优先 `ADOPT`；runtime 优先 `WRAP` 并保留双向导出；关键语义低成本且外部锁定高时
`REIMPLEMENT`；只有组合在合格任务上稳定断裂才 `INVENT`。

## 十、两个最承重的待检验接口

现成技术对“显式之后”的链条已经覆盖很广：ARD/A2A 索引已声明资源，MCP 枚举连接内动态
能力，流程与 commitment 技术表达已形成关系，GNAP/RAR/AuthZEN/PDP 处理已表达授权，
Temporal/outbox/CloudEvents 处理执行传播，readback/acceptance gate 处理权威判定，版本化与
telemetry 处理运行演化。

真正决定后续是否需要完整创新的两个接口是：

1. **搜索之前的机会生成**：query、Card、角色和动作形成之前，怎样在局部私有世界里产生
   值得探问的机会，并诚实量化披露—可发现前沿与不可发现边界。
2. **事件之后的跨权威晋升**：执行 event 之后，怎样跨独立 Authority Domain 避免误推
   `Effect → Adoption → Acceptance → Settlement`，并在 retry、补偿和漂移中保持可重建。

若强中心、本地模型和上述开放栈在这两处也通过，完整采用就是通爻成功；若失败，再围绕实际
责任断点做彻底创新，而不是先证明通爻必须特殊。
