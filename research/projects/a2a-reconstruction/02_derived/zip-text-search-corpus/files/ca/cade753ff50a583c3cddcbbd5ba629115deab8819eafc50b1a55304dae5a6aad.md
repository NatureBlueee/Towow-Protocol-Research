# 通爻 A2A 统一理论重建 v0.5

**状态：** 公开现实证据校准后的当前最佳理论。它不是最终真理，也不把公开档案冒充 Agent 干预实验。

## 摘要

通爻研究的不是消息怎样从一个 Agent 传到另一个 Agent，也不是怎样把一个已定义任务分配给多个执行器。它研究的是：

> 当多个不可互相代行的实体拥有私有、变化且不能被一个中心无损复制的世界，并分别控制事实、资源、工具、权威、责任与接受权时，怎样构成并持续修订一个**合格的联合行动空间**，使一项关系能够被发现、解释、拒绝、重构、认领、承诺、执行、见证、采用、接受、挑战和局部重开。

v0.5 对 v0.4 的关键修订是：通爻不应只把“形成”理解为增加一条原本不存在的路径。现实中的有效构成还可能是：重新安排一条路径的角色、权利和证据；删除一条未授权、不可验证或向第三方转嫁风险的路径；或者把一个误以为已经结清的关系重新置于适用的挑战范围内。

因此，通爻的目标不是最大化行动数量、成交率或 Agent 自主性，而是让可行动空间更接近现实，并让进入现实的每一步具有相称来源。

---

## 1. 研究对象：合格联合行动空间

设主体集合为 `P`，实体包络集合为 `E`，关系模式为 `Γ`，当前实例为 `x`，各主体私有世界为 `W_i`，证据状态为 `K`，适用权威与 jurisdiction 为 `J`。

定义时点 `t` 的合格联合行动空间：

```text
Q_t(Γ, x, W, K, J)
  = { a |
        Executable(a)
        ∧ ValidlyAuthorized(a)
        ∧ EvidenceQualified(a)
        ∧ RightsCompatible(a)
        ∧ JurisdictionallyAdmissible(a)
        ∧ RequiredStandingAddressed(a)
        ∧ ¬EffectivelyProhibited(a)
    }
```

这里的行动身份不能只按“业务目标”或 API 名称判断。只要角色、授权、证据、数据权利、责任、退出或 Effect witness 不同，就可能是不同的合格路径。

这一定义把几个经常混在一起的东西分开：

- **想得到**：模型能描述一种可能性；
- **做得到**：当前执行器、环境、资源和恢复条件支持；
- **有权做**：相称 Mandate 和责任链存在；
- **有理由相信做成**：证据与目标世界 witness 足够；
- **可以合法进入现实**：适用制度与受影响者 standing 已得到处理；
- **主体愿意承担**：必要 Stance 与 Commitment 指向精确版本；
- **世界已经改变**：Operation 产生了可验证 Effect；
- **关系真的被采用和接受**：目标域和有权主体分别作出 Adoption/Acceptance。

通爻的基本产物不是“一个答案”，而是 `Q_t` 及其依据、版本和可反驳条件。

## 2. 四种空间修订

公开档案迫使研究放弃“形成必然等于扩张”的偏见。当前将对 `Q_t` 的修订分为四类。

### 2.1 Expansion

出现此前不在 `Q_t` 中、后来通过工具、授权、伙伴、任务重构、现实 probe 或新证据进入的合格路径。

这仍是最强的“新能力/新关系形成”候选，但必须区分：路径原本不存在，还是只是不在研究者的记录里。

### 2.2 Transformation

目标相近，但行动的角色、对象、权利、授权、证据、数据边界、风险分配或 Effect path 被替换。形式上可以写为：

```text
remove(q_old) + add(q_new)
```

而不是把它误写成同一路径的参数调整。

### 2.3 Protective contraction

一条行动因未授权、证据不足、身份不明、能力依赖失效、外部性、适用禁止或不可接受风险而退出 `Q_t`。

保护性收缩不是系统失败。它可能是“真实优先于成交率”的直接体现。其价值仍需比较避免损失、机会损失与治理成本，不能仅凭禁止或拒绝自动宣称净收益。

### 2.4 Epistemic clarification

系统更清楚地描述了候选、理由或风险，但尚无足够证据证明 `Q_t` 改变。更多条款、更多 token、更完整会议纪要和更一致的语言都可能只属于这一类。

只有前三类构成严格的 qualified-space revision；第四类是重要的认知增量，但不能冒充现实形成。

## 3. Agent Entity、Principal 与 Authority

### 3.1 Agent Entity 是可归因实体包络

Agent Entity 是一个对外可寻址、可认证、具有行为连续性和治理入口的实体包络。内部可以包含：

- 一个人或组织；
- 多个模型和子 Agent；
- 人工审批和委员会；
- 工作流、账户、预算与工具；
- 本地记忆、私有数据和现实资源；
- 无法完全数字化、必须回到现实主体确认的判断。

它不是由内部模型品牌或框架定义的。Claude、GPT、LangChain、一个仓库或一个进程都可能只是 Entity 的组成部分或执行环境。

### 3.2 Principal 是规范主体

Principal 是能够产生原生认领、拒绝、承诺或接受，并对后果承担责任的主体。一个 Entity 可以代表多个 Principal，也可以只拥有非常窄的制度角色；同一个人或组织内部也可能存在多个不能互相代行的 Authority Locus。

必须保持四个正交轴：

```text
Identity             行为归因给谁
Capability           在当前条件下能做什么
Authority            在当前版本下有权做什么
Objective ownership  代表谁的目标进行选择
```

认证、能力、授权和目标忠实之间不存在一般蕴含。模型升级只能直接改变 Capability，不能静默扩大 Mandate 或替换 Objective source。

### 3.3 Authority topology 是功能图，不是主体计数

现实案例表明，同一权威根内部仍需区分：

```text
proposal
negotiation
recommendation
ratification
execution
effect_witness
adoption
acceptance
external_jurisdiction_or_standing
```

这些是 Mandate/RelationVersion 上的功能边，不应各自成为顶层对象。研究要问的是“谁在什么范围、对哪个版本、凭什么让哪一步作数”，而不是简单数有几个 Agent。

## 4. RelationVersion 与 Relation Schema

一项共同关系通过版本化 `RelationVersion` 被表达。它不复制各方完整私有世界，只保存当前联合行动所需的共享事实、条件、引用和差异。

Relation Schema 仍定义为：

```text
Γ = <R, V, T, A, E, D, O>
```

- `R`：角色、参与拓扑、责任以及受影响者 representation；
- `V`：对象和动作词汇；
- `T`：状态、退出、恢复、争议和 challenge 路径；
- `A`：提出、谈判、批准、执行、见证、采用、接受、standing 与 jurisdiction；
- `E`：证据资格、来源、对抗检验、Effect witness 与 Defeater；
- `D`：披露、用途、派生、保留、学习和再传递；
- `O`：Commit、Reject、Conditional、Unknown、Adoption、Acceptance 与 scoped Settlement 的成立方式。

standing、jurisdiction、challenge 和 settlement 不新增四个本体根；它们是 `R/A/T/O` 中不可遗漏的规则组。

### 4.1 Institutional frame 与 relation-specific version

现实关系并非从零开始。法律、行业标准、平台规则、公司章程和采购制度提供一个制度框架；具体主体在其中形成当前 RelationVersion。

两者不需要两套本体。系统只需明确：

```text
applicable_frames
frame_version
relation_specific_overrides
unresolved_frame_conflicts
```

“平台已经定义了规则”不意味着所有协调问题都被解决；“需要形成关系”也不意味着可以无视既有制度。

### 4.2 参数变化与 material schema change

在现有角色、动作、权威、证据、数据和结果语义内改变价格、数量、日期或资源值，通常是参数变化。

以下变化默认具有 materiality：

- 新增或删除必要角色、批准、challenge standing 或 jurisdiction；
- 改变可达动作、退出、恢复或争议路径；
- 改变谁能够让 Operation、Effect、Adoption 或 Acceptance 作数；
- 改变证据来源、验证标准或 producer self-report 是否充分；
- 改变数据用途、训练、派生、保留或再披露；
- 改变最终处置的范围或挑战窗口。

是否 material 必须相对于任务族、当前状态、风险、时间窗和活跃资源判断。JSON diff 既不是必要条件，也不是充分条件。

## 5. 三个构成循环与一个挑战面

### 5.1 可能性—能力循环

它回答“我们可能共同做什么，以及怎样让它真的做得到”。包括发现、问题重构、局部提问、拒绝、countercondition、工具/伙伴/授权引入、现实 probe、能力资格化和路径消融。

NAC、SJAC、PFE、CRA 等历史结构更适合作为这一循环中的方法族，而不是并列的世界本体。

### 5.2 权威—认领循环

它回答“谁能让什么作数，谁愿意承担什么”。包括范围化 Mandate、Stance、Commitment、资源预留、撤回、退出、争议、representation 和责任归属。

### 5.3 Operation—Effect 循环

它回答“世界实际发生了什么，以及谁采用和接受了什么”。包括 Operation、authoritative readback、Effect Assertion、Adoption、Acceptance、Settlement view 和长期 Defeater。

### 5.4 Challenge 面

公开监管和采购争议表明，挑战不是运行结束后的异常附录。外部 jurisdiction、受影响者 standing、审计、申诉和新证据可能在签署、授标甚至 Effect 已发生后重开关系。

Challenge 面贯穿三个循环：它可以否定候选、改变权威、要求新证据、禁止 Effect、迫使转化或触发补偿。系统不能把“双方同意”写成对所有世界都有效。

## 6. 严格形成判据

一项严格形成主张至少需要：

1. **冻结前态**：在协调前保存各方已知候选、约束、授权和可用工具；
2. **类型化操作**：指出何种 probe、拒绝、反条件、授权、工具或现实动作造成变化；
3. **合格空间差异**：证明出现 Expansion、Transformation 或 Protective contraction；
4. **相称来源**：关键差异由有权主体、目标世界 witness 或适用制度确认；
5. **现实可执行性**：形成后的路径产生 Effect，或至少达到有证据、可授权执行的 readiness；
6. **竞争解释**：与静态表单、优秀人类中介、同权限中心 Agent 或既有制度流程比较；
7. **消融或过程证据**：说明哪些形成操作是必要的，哪些只是附带表述。

公开档案可以强力观察第 3、4、5 项的一部分，也能重建制度过程；通常无法冻结真实私有前态，无法观察 Agent 介入，更不能完成第 6、7 项的 Towow 因果识别。因此它是现实结构证据，不是产品效果证据。

## 7. 真实目标：稳定处置保真

合法处置至少包括：

```text
COMMIT
REJECT
CONDITIONAL
DEFER_UNKNOWN
WITHDRAWN
DISPUTED
REOPEN
```

系统目标不是最大化 `COMMIT`，而是在尽量低的披露、认知、验证、等待和执行成本下，使处置与现实状态一致，并保留来源、挑战和重开的可能。

可以将损失写成：

```text
DispositionLoss
 = false_commit
 + missed_feasible_opportunity
 + unauthorized_effect
 + premature_reject
 + unknown_misclassification
 + externalized_harm
 + rights_violation
 + challenge_and_reversal_cost
```

“正确 NoDeal 有价值”获得了现实制度案例的范围化支持，但净价值仍依赖反事实：被避免的损失、错失机会和治理成本分别是多少。禁止本身不是福利证明。

## 8. Settlement 不是布尔值

`Effect=true`、双方完成、合同签署或采购授标都不等于关系在所有范围结清。

当前定义：

```text
Settled(
  RelationVersion,
  JurisdictionSet,
  StandingSet,
  ChallengeHorizon,
  EvidenceState
)
```

Settlement 是派生视图，不是新的 aggregate root。它必须能表达：

- 在双边执行层已完成；
- 在某个监管或申诉范围仍开放；
- 在当前 challenge horizon 内稳定；
- 若特定 Defeater 出现则局部 reopen；
- 哪些外部性或长期接受仍未观察。

这使系统避免把“发生过 Effect”误写成“所有必要主体与制度都已接受”。

## 9. 数据流动、派生与来源资格

数据使用会产生新数据：推论、评分、聚合趋势、联合制品、决策边界、长期记忆或模型更新。治理不能止于“读权限”。

但 v0.5 不新增 UsageGrant、DataUseEvent、DerivationRecord、JointArtifactRights、LearningUpdate 等顶层根。默认映射保持：

- 使用权限进入 `Mandate`/Relation policy；
- 实际使用进入 typed Event；
- 派生链进入 Assertion/Artifact provenance edge；
- 多方独立权利进入 conditional Commitment；
- 持久学习进入 Effect subtype，并在高风险时提升治理强度。

公开来源同样需要 provenance。每条档案 Assertion 至少记录：来源角色、同期性、激励或冲突、是否经过对抗/复核、删节和完整性、可证明的主张类型、交叉支持。

`SourceRecord` 是 Assertion 的来源结构，不是第七个业务根。

## 10. 中心化、A2A 与 CollapseSafe

通爻不追求所有运行都去中心化。索引、路由、候选生成、公共计算、共享对象托管和确定性执行都可以集中。

真正不能被中心默认代行的是：

- 不可长期复制和同步的完整私有世界；
- 受隐私、商业秘密或安全限制的信息；
- 原生事实的最终来源；
- 拒绝、授权、责任、承诺和接受；
- 策略位置、议价权和外部性代表；
- 独立故障、恢复和追责边界。

`CollapseSafe` 不是部署判断，而是反事实保真判断。中心机制只有在 outcome、披露与派生、拒绝/退出、权威/责任、激励/议价、更新/学习、故障/恢复和受影响者权利上与主权机制等价时，才可无损折叠。

若等价成立，使用更简单的中心机制；若只有部分维度不等价，则中心仍可承担计算，差异部分保留独立 authority gate。

## 11. 形成、编译、运行与局部重开

### 11.1 局部稳定

稳定不是全局终点，而是相对于任务、状态、风险、资源、权威、jurisdiction 和时间窗的局部性质。一个子图至少需要：

- 可达 material action 有明确 Authority；
- Effect-producing action 有目标世界 witness；
- 必要 Mandate 与 Stance 指向精确版本；
- 关键证据和数据规则足够；
- 必要 jurisdiction/standing 已覆盖；
- material challenge 已解决，或存在明确 contingency；
- exit、rollback/compensation 和 reopen 规则存在。

### 11.2 编译

编译把稳定子图压成最小权限、确定性、可审计的运行机制。其输出可以是代码、工作流、合同条款、凭证 scope、审批路径、预算锁、审计和挑战程序。

编译器不得创造新 Mandate、Stance、Commitment、Effect、jurisdictional clearance 或 Settlement claim。

### 11.3 READY_WITH_CONTINGENCY

现实中并非所有 open challenge 都要求停止一切行动。若 challenge 已知、范围有限、不会造成不可逆外部 Effect，且触发、暂停、补偿和升级规则明确，子图可以被标记为 `READY_WITH_CONTINGENCY`。否则必须 `NOT_READY`。

### 11.4 局部重开

Defeater 只重开依赖它的闭包。历史事实不被删除；旧 RelationVersion 保留其当时来源，新版本明确写出何种世界事实、Authority、Evidence、standing 或 objective 失效。

## 12. 最小事实内核

v0.5 仍建议六类 canonical aggregate roots：

```text
Entity
Mandate
RelationVersion
Assertion
Commitment
Operation
```

`EventEnvelope` 是传输与审计封套。Effect、Adoption 等是相应来源的 Assertion；Recognition、Reject、Conditional、Acceptance、Challenge 等是针对精确对象/版本的 Stance 或 typed Event；Settlement、CapabilityEnvelope、AssuranceCase、CurrentDisposition 和 CompiledWorld 是派生视图。

公开案例没有提供增加顶层对象的充分反例。它提供的是：现有对象必须承载 standing、jurisdiction、challenge、settlement scope 和 source provenance。

## 13. 当前证据结构

### 相对稳定

- 身份、能力、权威、目标所有权正交；
- Attempt、Effect、Adoption、Acceptance 不可混合；
- 静态投影不能穷尽开放未来任务；
- 权威拓扑比网络拓扑更能决定 A2A 必要性；
- 已发生 Effect 的关系仍可能在其他 jurisdiction 或 challenge horizon 中重开；
- 合格空间的转化和保护性收缩是现实构成的一部分；
- 来源资格是证据治理的一部分。

### 局部支持

- 动态边界、现实 probe、拒绝和 countercondition 可以在合成或技术权威域中改变可达路径；
- Relation Schema materiality 可以被部分形式化；
- 六根本体在当前查询集合下足够；
- 局部编译与 reopen 是有力候选架构。

### 仍然未知

- Agent 互动是否让真实人形成了本来不会形成的联合行动；
- 真实人能否理解并自由作出范围化认领；
- 通爻是否优于优秀经纪人、项目经理或同权限中心 Agent；
- 真实经济净剩余；
- 长期策略行为、操纵、依赖、串谋与权力不对称；
- 公共档案之外未记录的候选与被压制声音。

## 14. 系统架构含义

一个现实 Towow 系统不应首先做成“Agent 聊天大厅”，而应由以下能力构成：

1. **Entity/Mandate Registry**：身份、范围化授权、撤销和目标来源；
2. **Local Boundary Interface**：query、refuse、unknown、countercondition、witness、contribution；
3. **Relation Workspace**：版本化 Schema、实例、Stance、Commitment、依赖和差异；
4. **Qualification Engine**：能力、证据、rights、standing 和 jurisdiction 门；
5. **Formation Operators**：探问、probe、角色/工具/授权引入、scope 重构和候选生成；
6. **Effect Gateway**：Operation 与目标世界 readback；
7. **Challenge/Reopen Engine**：外部 standing、争议、Defeater 和依赖闭包；
8. **Compiler/Runtime**：把稳定局部变成最小权限确定性运行；
9. **Assurance and Provenance**：来源资格、审计、redacted export 和独立裁决。

Agent-to-Agent 直接对话只是其中一种可替换的交互实现。

## 15. 当前最深问题

> 在既有制度框架不足、但关系可以通过有限的形成操作推进时，具备范围化 Mandate 的 Agent Entity，能否以更低的披露与协调成本，帮助真实 Principal 构成或修订一个更真实的合格联合行动空间，并产生同权限强基线无法无损得到的现实路径或正确 NoDeal？

公开档案已经使“更真实”获得了可操作含义，却没有回答“Agent 是否造成了它”。下一阶段应继续使用公开材料扩大现实反例和校准仪器，同时明确保留真人前瞻性实验作为最终因果门。

## 16. 可反驳条件

这套理论应被以下发现限定或推翻：

- 封闭或开放任务中，静态/中心表示持续以更低成本无损保留全部相关事实、权威、拒绝和长期更新；
- 关系模式无法以任何有限任务相关结构操作化；
- 形成操作只产生更长文本，从不稳定改变 qualified action set 或现实 Effect；
- standing、jurisdiction 和 challenge 在目标问题中对结果没有独立影响；
- 真实主体无法理解版本化 Stance，或结构化过程系统性增加操纵；
- 编译与局部 reopen 比持续人工/Agent 协调更脆弱、更昂贵；
- 优秀人类中介或同权限中心 Agent 在所有不可折叠维度上实现同等结果且成本更低。

理论价值不来自难以证伪，而来自每个失败都能具体改变系统设计。
