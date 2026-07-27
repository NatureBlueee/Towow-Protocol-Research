---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_Unified_Paper_v1.0_formal/通爻_主权智能主体共同现实形成_正式论文_v1.0.md
source_sha256: 7f92cd950ddb796f193509529268f22b12ab1de3a6139ee71ffa13d0ecc1a65e
source_line_start: 286
source_line_end: 414
source_heading: "4　主体、世界与权威：Agent Entity 不是模型实例"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 4　主体、世界与权威：Agent Entity 不是模型实例

## 4.1 Principal：能够使规范事实成立的责任主体

**定义 1（Principal）。** Principal 是一个能够在某一制度语境中产生原生认领、授权、拒绝、承诺、接受或申诉，并能够被归责的主体。Principal 可以是自然人、法人、组织、公共机构或经明确程序授权的集体；它不等于任何代表它运行的模型、软件进程或账户。

“原生”并不意味着 Principal 必须亲自点击每个按钮。它表示某个规范事实的最终来源能够追溯到相称的权威程序。例如，公司采购负责人可以通过预先批准的价格带授权 Agent 自动下单；此时单笔 Operation 由 Agent 执行，但其规范效力来自采购负责人的 Mandate。相反，模型从历史邮件推测“老板应该会同意”，并不产生授权。

Principal 具有三个不可由模型置信替代的属性：

1. **权威来源**：谁或什么程序赋予其对某事项作数的地位；
2. **责任归属**：行动后果、救济和争议最终落到哪里；
3. **退出与反条件能力**：它能够拒绝、撤销或提出新的成立条件。

## 4.2 Agent Entity：对外连续，内部复数

**定义 2（Agent Entity）。** 一个 Agent Entity 记为

\[
E = \langle id, roots, loci, mandates, executors, resources, memory, policy, provenance \rangle,
\]

其中：

- `id` 是外部可寻址的连续身份；
- `roots` 是身份、责任与权威的信任根集合；
- `loci` 是内部不同权威位置；
- `mandates` 是版本化委托；
- `executors` 是模型、工作流、人类和工具执行器；
- `resources` 是账户、预算、数据、工具和环境；
- `memory` 是局部历史和长期状态；
- `policy` 是本地规则与风险门；
- `provenance` 记录声明、委托和动作的来源。

Agent Entity 是对外表现为一个可认证、可问责实例的边界，而不是规定其内部必须如何实现。一个 Entity 可以由单个本地模型组成，也可以是“一名创始人 + 多个模型 + 财务账户 + 外包网络 + 审批规则 + 线下判断”的复合体。

这一定义解决两个相反问题。第一，它避免把每个模型会话都当作独立社会主体；第二，它不要求把人的完整心智数字化。Entity 允许保留一个“不被模型化的 Principal 回路”：在高风险、目标变更、价值冲突或无法证明的情形中，系统返回真实主体，而不是假装所有判断都已进入机器状态。

![OPC Agent Entity：一个外部责任根可以承载多个角色、Mandate、执行器和现实效力接口。](figures/fig01_opc_entity.png){width=94%}

## 4.3 Authority Root、Authority Locus 与角色冲突

**定义 3（Authority Root）。** Authority Root 是身份或权威能够被外部验证的来源，例如自然人的认证身份、公司登记和章程、账户所有权、董事会决议、客户授权或特定法律程序。

**定义 4（Authority Locus）。** Authority Locus 是某一 Authority Root 内部，对特定动作、对象、金额、风险、时间或结果拥有决策、签署、见证、采用、接受或申诉权限的位置。

在大型组织中，预算、法务、数据、技术和业务接受通常由不同岗位持有；在 OPC 中，它们可能集中于同一自然人，却仍然不能被语义上合并。原因在于同一个人可以在不同角色下承受不同义务：

- 作为品牌主体，他关注声誉和内容语调；
- 作为公司负责人，他关注收入、交付和合同；
- 作为数据主体，他关注隐私与长期学习；
- 作为个人，他可能拒绝侵占家庭时间；
- 作为服务提供者，他能够报价；作为客户，他却没有替对方接受的权利。

因此，系统中“谁作数”必须由 `locus + scope + version` 表示，而不能仅靠登录身份。

## 4.4 Mandate：能力的可用范围，而不是人格转移

**定义 5（Mandate）。** Mandate 是 Principal 或相称 Authority Locus 对 Agent Entity 或 AgentExecution 的版本化委托：

\[
M = \langle issuer, delegate, objective, actions, objects, bounds, data, evidence,
expiry, escalation, revocation \rangle.
\]

其中 `objective` 说明该代理为了谁的什么目标行动；`actions` 和 `objects` 界定动作与对象；`bounds` 界定金额、时间、风险和不可逆性；`data` 界定读取、推理、保留、训练与再披露；`evidence` 规定行动前后需要什么证明；`escalation` 规定何时必须回到 Principal；`revocation` 规定撤销方式及已发生 Effect 的处置。

Mandate 不是把 Principal 的人格或全部权利转给 Agent。它是一个受条件约束、可撤销、可审计的行动许可。模型能力升级、工具增加或历史成功不自动扩展 Mandate。

## 4.5 AgentExecution：一次运行不是一个主体

**定义 6（AgentExecution）。** AgentExecution 是在特定 Mandate、上下文快照、执行器版本、工具集合和预算下发生的一次代理运行：

\[
X = \langle entity, mandate, context\_ref, executor, tools, budget, start, end, outputs \rangle.
\]

AgentExecution 可以生成候选、主张、问题、Operation Specification 或证据，但不能仅因“成功运行”而产生新的 Authority Root。软件仓库、进程、Consumer、Owner interface 或模型会话在实验中可以代表不同技术状态域，却不应自动被称为真实 Principal。

## 4.6 Sovereign World：不可无损复制的本地行动环境

**定义 7（Sovereign World）。** 对主体 \(i\) 而言，其时刻 \(t\) 的主权世界为

\[
W_i(t)=\langle H_i, G_i, C_i, R_i, U_i, P_i, L_i, E_i \rangle,
\]

其中 \(H_i\) 是历史上下文，\(G_i\) 是目标与认识，\(C_i\) 是能力和工具，\(R_i\) 是资源，\(U_i\) 是权威与责任，\(P_i\) 是政策与偏好，\(L_i\) 是法律/制度约束，\(E_i\) 是执行环境。各分量持续变化，也可能只有在具体任务、现实 probe 或反条件出现时才被主体显式认识。

Sovereign 不等于“所有数据都绝不离开本地”。它表示：

- 完整世界不能被假设为已被中心无损复制；
- 主体保留最终解释、拒绝和授权边界；
- 外部系统只能根据用途获得有限投影、证明、切割、见证或派生结果；
- 中心计算可以存在，但不能把本地权威和责任改写为中心所有。

## 4.7 主体关系图

设系统中有 Principals 集合 \(P\)、Agent Entities 集合 \(E\)、Authority Loci 集合 \(L\)、Mandates 集合 \(M\)、Executions 集合 \(X\)。最小责任关系为：

\[
issuer: M \rightarrow P \cup L,
\quad delegate: M \rightarrow E \cup X,
\]

\[
root: L \rightarrow P,
\quad authorizedBy: X \rightarrow M,
\quad accountableTo: E \rightarrow P.
\]

一个 Execution 的任何现实 Operation 必须存在一条可验证路径：

\[
X \xrightarrow{authorizedBy} M \xrightarrow{issuer} L \xrightarrow{root} P.
\]

如果该路径断裂，系统只能把输出视为候选或未授权 Attempt，不能把它写成 Principal 的承诺或接受。

## 4.8 设计不变量

主体模型导出五项不变量：

- **I-1 身份不推出权威。** 认证某个 Entity 只证明“是谁”，不证明“现在能对什么作数”；
- **I-2 能力不推出 Mandate。** 具备工具和模型能力不产生权限；
- **I-3 Execution 不推出 Principal Stance。** 输出、沉默或默认值不能自动替代认领；
- **I-4 同一自然人内的角色不自动合并。** 高风险角色冲突需要显式选择或优先级；
- **I-5 不可数字化不等于不可接入。** 系统可把不确定判断建模为回到 Principal 的 Gate，而不是伪造完整数字画像。

