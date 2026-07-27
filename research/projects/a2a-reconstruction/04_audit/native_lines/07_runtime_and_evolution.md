# 原生研究线 07：运行与演化

## 当时面对的真实问题

研究结论如果不能进入可恢复执行、证据闭合和变更管理，就不会成为系统能力。Harness 线把
Problem、Design、Engineering IR 分开，并通过 Context Compiler、证据入口、独立 verifier 和
reflow 维护长期任务。后续 Compiled World、Defeater 和 scoped reopen 处理“开放形成何时结束、
环境变化后重开什么”。[SRC-HARNESS:380-430] [SRC-HARNESS:545-590]

## 原生机制与能力

### CAP-RUN-001：Problem/Design/Engineering IR 分离

- 区分：用户要解决的现实问题、选择的设计和实际落地实现。
- 机制：三类 IR 保存各自来源、假设、接口和验收关系。
- 关键决定：实现完成不能倒写成原问题已经解决。
- 正例：工程修复通过，但 Acceptance 仍可因未覆盖原价值而拒绝。
- 移除失败：设计或实现目标不断缩小，最后以局部绿灯冒充原问题闭环。
- 来源：[SRC-HARNESS:380-430] [SRC-HARNESS:545-590] [SRC-HARNESS:799-835]

### CAP-RUN-002：Context Compiler

- 区分：把全部历史塞给执行者与为当前任务编译最小充分上下文。
- 机制：从证据、决策、接口和当前状态生成任务相关 context，并保留回源引用。
- 关键决定：编译视图不是新的事实源。
- 正例：执行 Agent 获得当前约束和证据入口，而不是长文摘要。
- 移除失败：上下文窗口被历史噪声淹没，或压缩摘要丢失关键边界。
- 来源：[SRC-HARNESS:70-118] [SRC-HARNESS:220-280]

### CAP-RUN-003：形成到确定性运行的局部编译

- 区分：尚需开放判断的关系部分与已稳定、可重复执行的局部。
- 机制：满足权威、证据、资源、Effect、退出和恢复 Gate 后，将局部关系编译为最小权限流程。
- 关键决定：编译对象是稳定子图，不是整个世界或永久协议。
- 正例：首次形成后相同 adapter 路径由确定性 readback/recovery 运行。
- 移除失败：每次重复协商产生高成本；或过早全局冻结使新反例无法进入。
- 来源：[SRC-R5C-METHOD:36-53] [SRC-R5C-SUMMARY:69-84]

### CAP-RUN-004：Defeater 与依赖闭包重开

- 区分：局部假设失效与整个关系全部失效。
- 机制：Defeater 引用被击败的 Assertion/Mandate/Effect/RelationVersion，沿依赖闭包重开。
- 关键决定：既不能永不重开，也不能任何变化全局重开。
- 正例：数据用途变化只重开数据授权、相关 Operation 和 Acceptance，不停止无关排期。
- 移除失败：陈旧编译继续执行，或一个局部变化导致系统全面停摆。
- 来源：[SRC-R5C-PATCH:1-53] [SRC-V11-MONOGRAPH:2810-2865]

### CAP-RUN-005：证据闭合而非产物闭合

- 区分：文件、测试或 Agent 报告存在，与关键主张有足够来源和验收。
- 机制：Evidence Closure 把主张、验证器、目标 readback、失败和 Acceptance 连接。
- 关键决定：独立 verifier 读取权威结果，不只检查产物存在。
- 正例：目标域结果与 manifest、日志和验收链一致后才关闭。
- 移除失败：checksum、测试绿灯或报告页数被当成现实成功。
- 来源：[SRC-HARNESS:1455-1506] [SRC-HARNESS:2714-2765]

### CAP-RUN-006：多机制 Router

- 区分：平台、中心 Agent、本地 Oracle、双边形成、联邦关系、确定性服务和人工裁决的适用条件。
- 机制：按制度充分性、信息可集中性、权威拓扑、不可逆性、witness 和漂移选择机制组合。
- 关键决定：A2A/联邦不是默认路线；简单机制能无损完成时主动旁路。
- 正例：标准支付走平台；非标准数据关系保留本地权威；争议进入人工裁决。
- 移除失败：所有任务重型联邦化，或全部压入中心 Agent 吞掉主权差异。
- 来源：[SRC-V07-OPC:75-102] [SRC-V11-MONOGRAPH:2970-3030]

### CAP-RUN-007：中心与联邦是条件选择

- 区分：部署分布式与权威真正不可折叠。
- 机制：中心可承担索引、计算、路由和确定性执行；不可代行的 Stance 留在责任根。
- 关键决定：用权威拓扑而不是网络拓扑判断联邦必要性。
- 正例：Authority-aware Hub 保留语义即可完成的任务不建联邦层。
- 移除失败：把“多个进程”误当 A2A 必要性，或把中心算力误当全面代理权。
- 来源：[SRC-R54-NET:1-64] [SRC-R5C-ABLATION:28-38]

## 后续解释与整合结果

- 六 roots 是关系运行时的最小正式事实范围，不是 Harness 全部研究/工程 IR 的替代物。
  v0.4 的映射没有为 Problem IR、Design IR、Context Compiler 和 Evidence Closure 指定完整承担者。
  [SRC-V04-ONTOLOGY:197-297]
- v0.7 把十二阶段生命周期和多机制 Router 纳入系统，恢复了运行全景，但其构造场景主要是
  自洽压力测试。[SRC-V07-OPC:56-145]
- v1.1 把运行组件写得更完整；Router 从真实原材料冷启动、编译复用净值和 scoped reopen
  的现实精度仍未证明。[SRC-V11-MONOGRAPH:2970-3030]

## 当前保留建议

- 异构研究内核：Harness 三类 IR、Context Compiler、Evidence Closure 独立保留。
- 共享运行接口：身份引用、版本、事件、证据、依赖。
- 关系运行时：六 roots、Effect/Acceptance Gate、Defeater/reopen。
- 决策工具：Router 先作为人机 checklist 和风险扫描器，自动化能力保持未检验。

