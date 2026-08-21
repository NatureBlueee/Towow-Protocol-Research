# 全线启动审计 01：发现与边界

日期：2026-07-28

状态：`STARTUP AUDIT / NO MECHANISM RESULT`

## 当前真实状态

`LINE-01-DISCOVERY-BOUNDARY / v0` 是已完成问题定义批次使用过的历史母线契约，仍绑定
`Problem v0`。它的 `ACTIVE` 只表示该历史批次的运行输入，不能据此宣称这条母线已经在
`Problem v2` 下正式启动。

当前 V2 已实际启动的只有 `LINE-01-NAC`，且只冻结
`E-H1-PRIME → MC-NAC-ANCHOR / CAP-DISC-003`。它不覆盖：

- `CAP-DISC-001` 任务相关投影；
- `CAP-DISC-002` HDC/FHRR 角色绑定；
- `CAP-DISC-004` 前缀式渐进披露；
- `CAP-DISC-005` SEEK/OFFER 方向性；
- `CAP-DISC-006` BIC 交互式充分性；
- `CAP-DISC-007` 类型化 Boundary Oracle。

因此“发现与边界母线已经启动”目前只在 NAC 坐标子主张上成立。

## 应继续独立研究的承重问题

下一条 V2 子线不应继续扩大 NAC，而应冻结：

> 在本地世界不完整公开、任务条件逐步显现的情况下，任务相关投影与类型化本地响应能否用
> 更少披露和更少误闭合，达到与完整表单或强模型自由问答相同的可行性判断；系统何时有
> 足够信息继续、拒绝或保持 Unknown？

这条问题区分的是：

- “没有完整资料”与“对当前决定已经充分”；
- `UNKNOWN` 与 `REFUSE`；
- 局部 witness/cut 与全局授权或承诺；
- 固定静态画像与随任务、风险和候选变化的投影。

去掉这些差异后，系统会重新把自由文本当作完整事实、把拒绝当不可行、把局部证据提升为
全局决定，或为了避免漏配要求完整披露。

## 现成方案与历史覆盖

本轮能够直接核验的权威材料是本地正典，而不是未审计的外部类比：

- 原生线审计已重建 task projection、prefix disclosure、BIC 与 typed Boundary Oracle；
- 能力矩阵将 `CAP-DISC-006` 标为 `TRANSFORMED / HIGH`，将 `CAP-DISC-007` 标为
  `PARTIAL / HIGH`；
- 当前系统保留 Boundary Oracle 角色，但没有把 cut/witness/unknown/refuse、本地权威和
  披露预算完整强制为运行时行为；
- NAC 一手方案复核只覆盖坐标、强中心检索和对齐基线，不能替代交互式充分性判断。

用户随后明确允许向第三方发送内部研究概念，并进一步要求改用环境自带网络通道。本轮据此
核验了以下一手来源：

- [OASIS XACML 3.0](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-cos01-en.html)
  正式区分 `Permit`、`Deny`、`Indeterminate` 与 `NotApplicable`，并保留不同来源的
  Indeterminate 语义；它强力覆盖 typed authorization decision，但不回答如何主动取得
  任务相关信息、何时信息充分或如何产生可行 witness/infeasibility cut。
- [IETF GNAP RFC 9635](https://www.ietf.org/rfc/rfc9635.html) 区分 pending、approved、
  denied/finalized，并给出交互、continuation、更新请求与 token/subject information
  暂缓释放；它覆盖渐进授权交互和拒绝，但不解决一般联合行动的隐藏约束、披露效用或充分性。
- [W3C Verifiable Credentials Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/)
  与 [VC Implementation Guidelines](https://www.w3.org/TR/vc-imp-guide/) 明确支持 data
  minimization、selective disclosure、predicate proof 和 progressive trust；它们覆盖
  “只披露当前交易所需信息”，但不规定协调器怎样选择下一 probe、何时停止或怎样区分
  local cut/witness。
- [SD-JWT RFC 9901](https://www.rfc-editor.org/rfc/rfc9901.html) 提供可验证的选择性
  JSON claim 披露；它是披露传输与完整性机制，不是任务充分性或关系求解器。
- [Online Active Perception for POMDPs with Limited Budget](https://arxiv.org/abs/1910.02130)
  与 [Active Information Gathering for Long-Horizon Navigation](https://arxiv.org/abs/2403.03269)
  直接研究有限预算下为了决策价值而取得信息；它们支持 value-of-information/probe
  基线，但场景是已定义状态/奖励的感知规划，不承担跨 Principal 权威、拒绝或证据语义。
- [Distributed Constraint Optimization Under Stochastic Uncertainty](https://ojs.aaai.org/index.php/AAAI/article/view/7812)
  证明分布式约束优化能够在信息交换成本与解质量间形成明确曲线；它覆盖局部信息与不完整
  算法基线，但没有把 `UNKNOWN`、`REFUSE`、授权和 disclosure provenance 统一为协议语义。

这些来源共同说明 Boundary Oracle/BIC 不是从零出现，但没有一个来源完整替代组合问题。

当前 disposition 应为 `COMPOSE/EXTEND`，不是 `GAP_CONFIRMED`：

- 历史机制已存在，不能把它重命名成新缺口；
- XACML/GNAP 已覆盖 typed authorization 与渐进交互；
- VC/SD-JWT 已覆盖可验证选择性披露；
- active information gathering 与 DCOP 已覆盖 probe value、局部信息和信息交换成本；
- 仍没有一项一手方案同时保存 typed local response、局部权威、渐进披露预算、任务充分性、
  witness/cut 与拒绝权；研究重点应是这些成熟能力的最小组合是否已经足够。

## 最强反例

最强反例不是“自然语言不够形式化”，而是：

> 一个稳定 Schema 加强模型，在本地域内调用普通查询工具，按当前任务自适应追问，并由
> 现有审批/RBAC 决定披露；它以更低实现和治理成本达到相同判断质量。

若该组合在同一隐藏约束分布、probe 预算和披露预算下不劣于专门 Boundary Oracle/BIC，
独立机制应降级为交互策略或 adapter，而不是继续维护新的正式对象。

## 最小可证伪判别

建议 V2 子线冻结 `DISC-H-BOUNDARY-SUFFICIENCY`：

1. 构造带隐藏局部约束、可行 witness、不可行 cut、Unknown 与拒绝的任务族；
2. 所有臂获得相同的公开 Schema、任务目标、最大 probe 数和披露成本函数；
3. 比较：
   - 固定静态表单；
   - 强模型自由问答加本地工具；
   - 类型化 Boundary Oracle 加充分性停止规则；
4. 同时报出正确继续/停止、误判可行、误判不可行、Unknown 保留、拒绝旁路、披露量、
   probe 数和总生命周期成本；
5. 合成世界只能校验机制是否可能区分这些状态；正式价值需要真实任务或独立标注材料。

反向结果：

- typed oracle 无精度、披露或恢复优势：将 BIC/Oracle 降为策略或 provider；
- 只有 typed response 有价值：保留响应语义，放弃独立充分性对象；
- 只有任务投影有价值：把投影编译进 Context Compiler；
- 所有臂都不能可靠闭合：保持 Unknown，并把问题推进到数据形成或现实边界获取。

## 建议 V2 绑定

- 建议 ID：`LINE-01-BOUNDARY-SUFFICIENCY-V2`
- `research_target.kind`：`EXISTING_SOLUTION`
- `mechanism_ref`：`null`，在判明哪些能力必须共同拥有前不提前注册大一统机制
- scoped claim：`SC-DISC-BOUNDARY-SUFFICIENCY`
- hypothesis：`DISC-H-BOUNDARY-SUFFICIENCY`
- capability scope：`CAP-DISC-001`、`CAP-DISC-004`、`CAP-DISC-005`、
  `CAP-DISC-006`、`CAP-DISC-007`
- 建议状态：`ACTIVE`，但只允许本地理论、数据契约、合成反例与公开来源研究
- `CAP-DISC-002`：`DEFERRED`。角色绑定表示当前优先级低，除非后续角色交换反例证明
  Schema/方向字段无法保真，否则不与本线一起启动。

## 不受影响

这条线无论正负都不能改变：

- `MC-NAC-ANCHOR` 与 NAC 其他 H2–H8；
- 关系是否构成、Principal 是否授权；
- 能力是否兑现；
- 现实 Effect、Adoption、Acceptance；
- PFE 是否真正形成新路径；
- 完整通爻或联邦拓扑的净价值。

## 来源

- `research/projects/joint-action-formation/lines/01-discovery-boundary.json`
- `research/projects/a2a-reconstruction/04_audit/native_lines/01_discovery_and_boundary.md`
- `research/projects/a2a-reconstruction/04_audit/ledgers/capability_preservation_matrix.csv`
- `research/projects/joint-action-formation/problem/v2.json`
- `research/projects/joint-action-formation/lines/01-nac.json`
- `research/projects/joint-action-formation/prior-art/nac-h1-existing-solutions-2026-07-28.md`
