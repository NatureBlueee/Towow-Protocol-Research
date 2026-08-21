# ChatGPT Pro G6 独立敌对审计

日期：2026-07-29  
状态：`INDEPENDENT ADVERSARIAL AUDIT / REVISE BEFORE EXPERIMENT / NO FORMAL STATUS CHANGE`

## 审计对象与总判定

本审计直接检查：

- [`G6-return.md`](./G6-return.md)；
- 同轮独立本地返回 [`codex-cli-cohort-001/G6-final.md`](../codex-cli-cohort-001/G6-final.md)；
- 已执行攻击审计 [`WAVE-010-G6-G7-AUDIT.md`](../../WAVE-010-G6-G7-AUDIT.md)；
- X2 候选输入合同
  [`WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md`](../../WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md)；
- 当前研究边界 [`research/NOW.md`](../../../../../../NOW.md)；
- 原生 G6 保真要求
  [`06_reality_effect.md`](../../../../../a2a-reconstruction/04_audit/native_lines/06_reality_effect.md)。

总判定：

```text
PRO_RETURN_DISPOSITION = REVISE_BEFORE_EXPERIMENT
ROLE_NOT_LADDER_RECONSTRUCTION = VERIFIED_DIRECTION
SINGLE_ROLE_FIELD_AND_SINGLE_TYPED_DAG = OVERSTRONG
RAW_OCCURRENCE_VS_EPISODE_QUALIFICATION = PLAUSIBLE_BUT_UNSAFE_AS_WRITTEN
OWNER_SCOPED_LEDGER = PLAUSIBLE_CLAIM_CARRIER_NOT_TRUTH_ORACLE
TARGET_READBACK = VERIFIED_COMPONENT_BOUNDARY
READBACK_COMPLETELY_COVERS_EFFECT = OVERSTRONG
CAUSAL_ATTRIBUTION = CORRECTLY_SEPARATED_BUT_NOT_OPERATIONALIZED
SETTLEMENT_FINALITY = SCHEME_SPECIFIC_AND_UNRESOLVED_END_TO_END
MATURE_COMPONENT_CAPABILITIES = LARGELY_VERIFIED_IN_NATIVE_SCOPES
MATURE_END_TO_END_COMPOSITION = UNRESOLVED_NOT_RUN
STRONG_CENTER_STRATIFICATION = PLAUSIBLE_BUT_INCOMPLETE
HELD_OUT_TYPED_DAG = OVERSTRONG_IF_INPUT_GRAPH_OR_OWNER_API_IS_COPIED
NOVEL_EFFECT_PROTOCOL_NECESSITY = NOT_DEMONSTRATED
REAL_WORLD_EVIDENCE = NONE
FORMAL_STATUS_CHANGE = NONE
```

这份返回最有价值的修正是：它拒绝把
`Attempt → Effect → Adoption → Acceptance → Settlement` 当作普遍固定流水线，并明确
区分现实、观察、owner 的权威判断与 workflow 派生状态。这比单一 `SUCCESS` 或固定五级
ladder 更保真。

但它又在形式化和实验设计中把这些差异重新压进了：

1. 一条 claim 上的单一 `role` 字段；
2. 一个 task-specific typed DAG；
3. 五个 owner ledger current head；
4. 一个对这些 head 求值的 `Done_e(t)`。

这会把原生研究中仍需分离的三类关系重新统一：**世界中发生的 occurrence、主体作出的
资格/规范判断、episode 的控制与义务依赖**。最危险的后果不是概念不优雅，而是未经授权的
真实 Effect、wrong-object 外部损害、并发因果、旧 head 和结算可逆性可能在
“Qualified=false”之后从恢复与责任链中消失。

因此，本轮应保留 Pro 的问题重建和 baseline 方向，但不能接受“成熟组合已经完整解决 G6”
或“owner-complete composition 已经形成端到端闭包”。当前最强正确表述是：

> 在 exact object/version 可寻址、目标域能给出有界且可验证的 current-state observation、
> owner 的规范行为可合法取得、结算制度和 finality predicate 已冻结、跨域绑定与成本实际
> 通过同一 episode runner 验证的环境中，成熟组合是首要完整解候选；这些条件尚未由同一
> 端到端运行建立。

## 一、逐项主张审计

| Pro 主张 | 判定 | 最强反例或缺口 | 最小修订门 | 对下一实验的改变 |
|---|---|---|---|---|
| 五层不是固定流水线，而是相对于 episode 的角色 | `VERIFIED` | 同一 act 可同时是一个 domain 的 Effect、另一个 episode 的 Acceptance；预付款也可早于 Effect | 保留 role-relative 解释，不恢复固定 ladder | held-out 必须包含 pre-Effect Acceptance、advance Settlement、并行/多 owner、partial/revoked 分支 |
| 单条 claim 的一个 `role` 足以表达这种多角色性 | `OVERSTRONG` | 款项到账同时是银行域 Effect 和义务域 Settlement；若复制成两条 claim，会出现双事实根；若只选一个 role，会丢另一语义 | 将 `role` 改为多对多 `RoleAssignment(claim_or_occurrence, episode, role, qualificationRule)`；底层 occurrence 只保留一次 | grader 先验收 occurrence identity，再验收各 episode role assignment，禁止以复制 claim 增加证据数 |
| 一个 task-specific typed DAG 足以同时承载历史、权威和完成条件 | `OVERSTRONG` | occurrence 的因果/修正历史、Acceptance/Settlement 的规范依赖、workflow 的 admission/reopen 不是同一种 edge；reversal 也不能删除旧 occurrence | 至少分成 occurrence/provenance graph、authority/qualification graph、episode obligation/control graph；typed DAG 只可作为某一投影 | Track A 只冻结 normative/control graph；realized occurrence 和 authority heads 由独立 owner/evaluator 建立 |
| `RawEffect=true, QualifiedEffect=false` 足以处理未经授权的现实改变 | `OVERSTRONG` | 未授权人员改变 CNC 参数时，Effect 对目标世界和安全恢复都真实存在；若 `ApplicablePolicy=false` 使它不进入当前 graph，补偿、责任和 affected closure 会漏掉 | 分开 `OccurredEffect`、`AuthorizedAttempt`、`BoundToEpisode`、`CountsTowardQ`；非法或 wrong-object Effect 仍是必须恢复的事实 | 加入 unauthorized-but-real、wrong-target-but-real、old-version-but-irreversible 三类零容忍 case |
| Evidence、claim 与现实事实必须分离 | `VERIFIED` | 签名、hash、trace 或 receipt 可以完全有效，但 signer 无 Standing、对象错误或数据陈旧 | 保留 `X* / X-hat / evidence`，再增加 observer/source、freshness、conflict 与 qualification provenance | evaluator 不按 receipt 存在评分；必须用独立目标状态和 owner act 检查 claim |
| target-domain readback 是数字域确认 Effect 的最强成熟方法 | `PLAUSIBLE` | readback 可确认当前 postcondition，却不必确认状态发生过变化，更不必确认是本 Attempt 所致 | readback 至少绑定 pre/post、operation token、writer/audit identity、head、freshness；无法归因时 `Effect=true, Cause=UNKNOWN` | 增加“前态已满足 / 并发 actor 建立 / 本 Attempt 建立”三世界，当前 readback 保持相同 |
| 对可权威查询的数字域，readback 可以完整覆盖 Effect | `OVERSTRONG` | 两个世界 current state 完全相同：一个由本 Attempt 改变，一个在 Attempt 前已由第三方建立；单次 current readback 无法区分 change 与 pre-existing state | 将“完整覆盖 Effect”降为“有界确认 current postcondition”；Effect occurrence 和 causal edge 独立验收 | Effect 指标拆成 postcondition、state transition、causal attribution、count delta 四项 |
| owner-scoped ledger 可以成为五层 truth source | `PLAUSIBLE` | ledger 只证明谁写了什么 claim；target-owner adapter 仍可能读 desired state、旧 projection、错误对象或 forked head | owner ledger 定位为权威 claim/current-head carrier，不是自动 truth；API 与 grader 分域并注入 stale/refused/wrong-object/fork | 不得从 private truth 直接复制 owner API response；每次查询记录延迟、拒绝、披露、费用和版本 |
| `Done_e(t)=phi(heads)` 是安全的 episode 完成视图 | `OVERSTRONG` | 五个 head 分时读取后可能组合成一个从未同时存在过的状态：Acceptance 已撤销时读取旧 K，Settlement 仍 pending 时读取新 S | `Done` 必须绑定一致 cut 或带有效时间的 head vector、evaluation event index、conflict policy 与 non-monotone reopen rule | 注入 read-skew、rollback-after-read、late dispute 和 supersession；单次绿色聚合不能通过 |
| 独立 owner Acceptance 的成熟制度可完整构成 Acceptance | `PLAUSIBLE` | 可以完整记录有权主体的 act，但不能自动证明其 Standing 未过期、对象正确、criterion 完整或非 rubber stamp；主观冲突也不会消失 | Acceptance receipt 绑定 principal/delegation、type、object/version、criterion、reservation、有效时间和 dispute lineage | 加入 wrong type、wrong version、expired delegation、partial/conditional/reject 与多 owner disagreement |
| payment/escrow/银行账本可完整覆盖 Settlement | `OVERSTRONG` | provider 的 `Settled` 可能只表示 provider 已收款，不等于 payout；chargeback、reversal、义务拆分和法律 finality 仍属不同状态 | 为每个 obligation 冻结 scheme、party、amount、phase、finality predicate、reversal/dispute horizon；不得用单枚举 `Settlement=true` | 分开 authorization/capture/provider-settled/payout/legal-finality/chargeback，按 obligation graph 评分 |
| 合法全委托强中心可以完整获胜 | `PLAUSIBLE` | 方向正确；但“全委托”本身可能只覆盖部分 acceptance type，且形成、维护、撤销委托有成本；若只给中心额外权威，比较的是制度条件而非架构 | 将 single-authority、equal-permission multi-owner、lawfully delegated 三个 stratum 分开；每个 stratum 内保持能力对等 | 在 delegated stratum 中也允许 mature composition/human process 使用同一合法委托，并计委托成本与撤销延迟 |
| B3 与 B5 的设计已避免 strong center 被故意削弱 | `PLAUSIBLE` | 返回允许全委托正胜出，但没有要求独立实现；本地 Wave010 已证明同一 `method_decision()` 改名只能得到 alias 等价 | baseline 绑定独立 executable identity、实现 owner 和进程；共享 schema/API，不共享决策函数或 expected table | strong center、mature composition、human institution 分开实现；只可报告观察等价，不从相同代码宣称架构等价 |
| Track A 给定 typed DAG，同时用 typed-edge F1 测 topology generalization | `OVERSTRONG` | 若 normative DAG 已作为输入，系统可以逐字复制 edge；typed-edge F1 不测 G6，只测 serialization | Track A 测 realized node status、invalid promotion、控制决策和 recovery；edge F1 只用于 Track B 的 DAG construction，或测 method 未见的 realized causal edges | 把“输入 graph edge”和“需要推断的 realized/causal edge”使用不同 namespace 与 evaluator |
| Gold truth 不可见且不给免费 oracle，足以关闭 held-out 泄漏 | `PLAUSIBLE` | 即使 gold 文件不可见，若同一个 world factory 把 private truth 直接复制为 owner readback，方法仍得到包装后的答案；本地 `7/7` 已实际复现此失败 | owner service 必须从自己的 store/传感器/act 形成 native response，grader 使用独立 source；强制 stale/loss/refusal/wrong binding | 主评分前先运行 truth-to-API direct-copy mutation；若复制仍能满分，整轮 `INVALID` |
| 96 个核心实验条件是合理起点 | `UNRESOLVED` | 组合数来自设计乘法，不是信息独立性或 power；同一生成器复制 96 次仍是同源别名 | 先做 motif orthogonality 与 evaluator mutation；样本量由目标效应、分层相关性和 pilot variance 决定 | 第一轮只需少量高区分 paired worlds；通过 oracle/alias 门后再扩量 |
| 成熟技术组合已经在封闭数字域完整解决 G6 | `UNRESOLVED` | 组件事实大体成立，但跨组件 operation identity、object translation、consistent cut、owner refusal、settlement finality 和 recovery 未在同一 episode 运行 | 改写成带前提的 sufficiency candidate；所有跨合同箭头必须有运行证据 | 先跑一个可逆数字任务的独立多进程 composition，再允许“完整解决” |
| 当前没有充分理由发明专用 Effect 协议 | `VERIFIED` | 这是证据状态判断，不等于 residual 为零；当前 residual 也可能由 adapter、制度或强中心解决 | 使用 `NOVEL_PROTOCOL_NECESSITY=NOT_DEMONSTRATED`，不要写 `NO_RESIDUAL` | 只有成熟组合在同条件多任务上重复留下同一不可修复语义缺口，才重开最小新机制 |

## 二、角色化重建保留了什么，又过度统一了什么

### 可保留：角色不是固定阶段

Pro 对“一个 occurrence 在不同关系中可承担不同角色”的判断是本轮最强理论贡献。它正确
保留了这些历史区别：

- Attempt 可以发生而 Effect 不发生；
- Effect 可以发生但无人采用；
- Adoption 可以早于某种 performance Acceptance；
- Acceptance 可以是前置安全审批，也可以是后置结果验收；
- Settlement 可以是预付款、阶段款、holdback 或最终义务解除；
- compensation、reversal、revocation 和 supersession 应新增历史节点，而不是删除旧事实。

这与原生 G6 的
`ActionAttempt event / Effect receipt / Adoption state / Acceptance Stance`
分离兼容，也比把五者做成五个永久顶层“物质”更准确。

### 必须修订：角色是投影，不是事实身份

Pro 的 claim tuple 只有一个 `role`。但它自己的例子已经证明同一 occurrence 可以同时承担
多个角色。最小无损模型应是：

```text
Occurrence:
  occurrence_id
  domain
  native_object/version
  observed transition or institutional act
  source/provenance/time

Claim:
  issuer + authority_scope
  proposition about occurrence/current state
  evidence + head + freshness + dispute

RoleAssignment:
  occurrence_or_claim_id
  episode_id
  role = Attempt | Effect | Adoption | Acceptance | Settlement
  task_specific_subtype
  qualification_rule_version
  object/obligation binding
  status = QUALIFIES | DOES_NOT_QUALIFY | UNKNOWN | DISPUTED
```

这样，“到账”只是一项银行域 occurrence；它可以被一个 episode 赋予 Settlement 角色，也可
作为另一个监控 episode 的 Effect。不能为两个角色复制两份正式现实，也不能迫使 occurrence
只能选一个角色。

### 必须修订：不能用 qualification 删除现实后果

Pro 的：

```text
Q_X(e) =
  X_raw ∧ ExactBinding ∧ CurrentVersion ∧ ValidTime ∧ ApplicablePolicy
```

适合判断“它是否计入本 episode 的成功”，不适合判断“现实是否发生、需要恢复或追责”。

最强反例：

```text
episode: 维修 CNC-17 / spindle SP-4472
attempt: 未获授权的旧 work order 被 replay
reality: CNC-17 参数真实改变，生产已经受影响
policy: 当前 mandate 已撤销
```

正确结果至少是：

```text
OccurredEffect = TRUE
AuthorizedAttempt = FALSE
CountsTowardQ = FALSE
RecoveryRequired = TRUE
Liability/Standing = OPEN
```

若只保留 `QualifiedEffect=false`，系统会把最需要恢复的现实 Effect 当成“没有 Effect”。
wrong-object 情况更明显：误加工 CNC-71 不计入 CNC-17 的任务成功，但它是新的受影响主体和
不可忽略的目标域 Effect。

### typed DAG 只能是三个图中的一个投影

建议保持三层而不是一个总 DAG：

| 图 | 保存什么 | 不应承担什么 |
|---|---|---|
| occurrence/provenance graph | raw occurrence、状态变化、actor、causal claim、reversal、supersession | 不直接宣布 owner 接受或义务解除 |
| authority/qualification graph | 谁有权对哪个对象、criterion、obligation 作出何种 stance；委托、撤销、争议 | 不伪装物理变化或因果 |
| episode obligation/control graph | 当前任务的前置门、并行/聚合、完成、付款、reopen 规则 | 不成为新的事实根或 gold oracle |

三者可以通过版本化引用组合，但不能由一个 `typed edge` 同时表示“现实导致”“制度要求”和
“workflow 接下来应该走”。

## 三、owner ledger 仍可能只是免费的 truth API

Pro 已明确说 ledger 可以只是同一 PostgreSQL 中按 RBAC 分离的逻辑表，这本身没有问题。
真正问题是它从“只有 owner 能写 claim”跳到了“该 ledger 的 current head 可作为 reality
truth”。两者不等价：

```text
write authority
  ≠ observation accuracy
  ≠ exact-object binding
  ≠ freshness
  ≠ causal attribution
  ≠ settlement finality
```

一个 target owner 可以合法签发：

- desired state，而不是 observed state；
- generation 9 的旧 condition，而当前对象已是 generation 12；
- 同 tenant 内错误 object 的 `TRUE`；
- self-report，而不是独立物理测量；
- provider 内部的 `Settled`，而不是受益人 payout 或法律 finality。

因此 `L_E`、`L_D`、`L_K`、`L_S` 应被称为 **owner-authorized claim/current-head
carriers**。它们是不是充分 truth source，必须由任务内的 source contract 和反例决定。

X2 候选合同已经比 Pro 返回更严格：它要求五个 domain owner 拥有独立 store、signer 和
readback source，并禁止 parent/evaluator 代签；也禁止四个 evaluator 共享
`world_factory`、private truth object 或 expected table。这些要求应保留。

但 X2 仍未运行，因此不能从 schema 上的分域推出 API 已经非 oracle。最小执行门是：

1. owner API 从 owner 自己的状态、传感器或 institutional act 生成 native response；
2. grader 不把自己的 private truth row 复制为该 response；
3. 方法真实面对 `UNKNOWN / REFUSED / STALE / TIMEOUT / CONFLICTING / wrong-object`；
4. signed response 仍需验证 object/version/head/observed_at/expiry；
5. owner query、人工、披露、等待和 dispute 都计成本；
6. owner response 与 private truth 不同不自动视为系统 bug，它可以是本次要测的现实失真。

已执行的本地 Wave010 攻击给出了直接证据：当前 `7/7` 来自
`world["truth"]["layers"] → readbacks` 的 direct copy，且 strong center 与 mature
composition 共用同一决策函数。Pro 的 “no-free-oracle” 原则方向正确，但必须转化成上述
失效测试，不能只写进公平性说明。

## 四、readback、qualified occurrence、causal attribution 与 finality 必须正交

### Target readback

官方文档支持 Pro 对组件边界的多数判断：

- CloudEvents 规范把 event 定义为表达 occurrence 的数据记录；一次 occurrence 可以产生
  多个 event，`source + id` 主要支持 event identity/duplicate 判断，不证明新的现实 Effect。
  [CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)
- AWS transactional outbox 指南说明该模式解决本地数据库写和事件通知的 dual-write，
  同时明确 relay 仍可能产生 duplicate，consumer 需要幂等。
  [AWS transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
- Step Functions 的 `Pass` state 可以“不执行任何工作”而正常给出输出，证明 workflow
  green 不蕴含外部 Effect。
  [AWS Pass state](https://docs.aws.amazon.com/step-functions/latest/dg/state-pass.html)
- Kubernetes 的 `observedGeneration` 明确绑定 condition 记录时的
  `metadata.generation`，支持 freshness 检查，但仍不是跨域因果证明。
  [Kubernetes Pod conditions](https://kubernetes.io/docs/concepts/workloads/pods/pod-condition/)

这些事实支持“readback 比 workflow 自报强”，不支持“单次 current read 完整覆盖 Effect”。

### Qualified occurrence

qualification 回答的是：

> 该 occurrence 是否绑定当前 episode、当前对象、当前规则，并能否计入某个主张？

它不能回答：

> 不合格 occurrence 是否真实发生、造成损害或需要恢复？

因此 precision/recall 应至少并列报告：

- raw/observed occurrence；
- episode binding；
- policy qualification；
- wrong-object external effect；
- current-state postcondition；
- transition count。

### Causal attribution

Pro 正确把 `Cause(A_i,E_j)` 单列，并承认 trace/时间邻近不足。问题是它又把
`readback can completely cover Effect` 写成结论。最小反例是：

```text
W0: postcondition 在 Attempt 前已由第三方建立
W1: exact Attempt 通过 target-side operation token 建立 postcondition
method-visible current readback: 完全相同
```

两者 current Effect-state 相同，episode causal result 不同。正确评分应分开：

```text
CurrentPostcondition
TransitionOccurred
Cause(exact_attempt, transition)
DuplicateTransitionCount
```

缺少排他写窗口、target audit token、可验证 before-state 或干预证据时，允许
`CurrentPostcondition=TRUE / Cause=UNKNOWN`。

### Settlement finality

Pro 自己正确引用了“Settled 不等于 payout”，但随后又写“可以完整覆盖 Settlement”。官方
资料进一步表明：

- Adyen 的 `Settled` 表示资金已由 Adyen 收到，不表示已经 payout 给商户；
  [Adyen payment lifecycle](https://docs.adyen.com/account/payments-lifecycle/)
- settlement report 仍包含 chargeback、settled reversal 和 paid-out reversal 等后续记账；
  [Adyen settlement report](https://docs.adyen.com/reporting/settlement-reconciliation/transaction-level/settlement-details-report)
- ECB 对 final settlement 的定义要求 unconditional、enforceable、irrevocable，并区分
  transfer order finality 与 transfer finality。
  [ECB glossary](https://www.ecb.europa.eu/services/glossary/html/glossf.en.html)

所以一个 PSP/provider ledger 可以完整报告**其自身 scheme 内的一项状态**，不能无条件成为
episode 的单一 Settlement truth。完整任务常需要 obligation subgraph：

```text
authorization
→ capture
→ scheme settlement
→ provider balance credit
→ payout
→ beneficiary receipt
→ legal/contractual discharge
→ dispute/chargeback/reversal horizon
```

哪个节点足以解除哪项义务，必须由冻结的 contract/scheme predicate 决定。

## 五、strong center 的公平比较需要三个 stratum

Pro 明确允许强中心正面获胜，这一点符合当前研究宪章，也必须保留。问题不是“中心有没有
资格”，而是不能把不同 Authority 条件混成一次架构排名。

| stratum | 冻结条件 | 公平比较 |
|---|---|---|
| `S1 SINGLE-AUTHORITY CLOSED DOMAIN` | 一个合法主体实际拥有 target、adoption、acceptance 和 settlement decision，且 action grammar/version closed | direct platform、optimized center、mature composition、人类流程均可使用该权威；中心或平台胜出是完整正解 |
| `S2 INDEPENDENT OWNERS EQUAL PERMISSION` | Authority 不可转移或尚未委托；各方法只拥有相同 owner APIs、HITL、预算和时限 | 比较编排、查询、恢复和成本；任何方法不得代签 owner |
| `S3 LAWFULLY DELEGATED` | 精确 owner、acceptance type、object、期限、撤销和 recourse 已合法委托 | center、composition 和制度流程都可使用同一委托；比较集中控制的净增益，并计委托形成/维护/撤销成本 |

`S3` 不是作弊，也不是应降级的“问题改变”。但它的胜利只支持可委托的精确范围。监管者、
外部银行、独立 buyer 或不可转让的责任仍不能因中心的技术能力被吞并。

Pro 的 B5 已提出“合法全委托 / authority 仍独立”两条件，判定为 `PLAUSIBLE`。它尚缺：

- 委托 receipt、scope、expiry、revocation 和 non-delegable rights 的冻结；
- 同 stratum 内其他 baseline 的能力对等；
- 委托形成和治理成本；
- 独立实现。当前本地同函数 alias 只能证明输出恒等，不能证明架构因果等价。

## 六、held-out typed-DAG 仍有 truth-copy 与无效指标风险

### Track A：给定 normative graph

Pro 为避免把 G2/G5 偷混进 G6，提出主实验直接给定 DAG、owner、criterion 和权限，这个切分
方向是 `VERIFIED`。但在同一轨道又要求系统输出 typed edges 并计算 typed-edge F1。

若 edge 已经在输入 DAG 中，这个指标可以靠复制满分，不测：

- realized occurrence；
- owner current head；
- invalid promotion；
- crash 后重复 Effect；
- wrong-object Acceptance；
- settlement/dispute；
- control action。

Track A 应把输入称为 `NormativeEpisodeGraph`，只评分：

- realized node/stance reconstruction；
- owner/head/object/version binding；
- illegal edge activation；
- execution/recovery decision；
- disagreement、Unknown、refusal 和成本。

### Track B：从合同/SOP 构建 graph

只有 Track B 才适合用 normative node/typed-edge F1。但其 gold contract graph 不能同时成为：

- B3 的 owner ledger schema；
- method-visible task packet；
- evaluator 的 expected row；
- owner API response template。

否则 B3 或模型只是在复制 evaluator ontology。

### realized causal graph

如果要在 Track A 测“新拓扑泛化”，应隐藏的是 realized causal/qualification edges，而不是
已经给定的 normative edges。例如：

- 同一 postcondition 由第三方并发 actor 建立；
- old receipt 指向相同 bytes 但不同 obligation；
- partial adoption 只激活一个 branch；
- acceptance revocation 触发 reopen；
- settlement split 的一条 rail disputed。

这些 edge 只能由运行后的 owner evidence 和 independent grader 确定。

### X2 的必要继承

X2 候选合同已经加入以下正确约束，应作为 Pro 设计的最小修订底座：

- actual X1 finalized outputs 决定 population，不手写成功 relation；
- 每个 arm 继承自己的输出，不能 transplant success；
- truth owner/evaluator 禁止共享 `world_factory`、truth object、expected table 和 keyspace；
- owner commitments 不向 method 暴露 motif/A/B/expected label；
- mature composition 必须实际产生 prediction、current Authority、causal identity、五层
  receipts 和 dependency-aware reopen，产品名不算通过。

但这些仍是 `CANDIDATE / NOT RUN`。完成 schema 不等于 held-out 已经关闭 truth-copy。

## 七、成熟组合：组件边界大体成立，拼装箭头尚未闭合

### `VERIFIED`：组件各自解决真实局部问题

| 组件 | 官方材料支持的能力 | 不能自动推出 |
|---|---|---|
| transactional outbox | 本地业务写和待发布事件的 dual-write 原子性；relay 可恢复 | 外部 target Effect；下游不重复 |
| durable workflow | 持久编排、重试、等待、恢复、人工 task | Activity success 等于现实完成 |
| CloudEvents | event envelope、source/id 和互操作 | occurrence 真值、Authority、一次 occurrence 只有一个 event |
| target readback | 有界目标域 current state 与 freshness observation | 变化由谁造成、跨域 Adoption/Acceptance |
| CLM/e-sign/制度验收 | 有权主体的可追溯 acceptance act | 对象真实合格、Effect 已发生 |
| payment/escrow rails | scheme 内的资金/义务状态 | payout、法律 finality、技术 Effect |
| observability | trace、metric、log 关联和恢复线索 | 干预意义因果、owner authority |

FAR 也明确把政府采购 acceptance 责任放在 contracting officer 或被正式指派的机关，支持
“Acceptance 来自有权主体，不来自 vendor/workflow”的边界。
[FAR 46.502](https://www.acquisition.gov/far/46.502)

### `UNRESOLVED`：端到端箭头

Pro 的“最强无新协议组合”仍是组件清单。以下每个箭头都尚无同一 runner 的运行证据：

```text
exact operation contract
→ target-side idempotency/CAS
→ external target write
→ native current readback
→ state transition and count reconstruction
→ exact-attempt causal attribution
→ adopter behavior qualification
→ owner Acceptance act and disagreement
→ obligation-specific settlement/finality
→ temporally consistent Done view
→ drift/reversal/reopen
```

尤其未闭合的是：

- operation/idempotency identity 能否跨 workflow、connector、target 和 payment rail 保留；
- schema adapter 是否保持 object/version/criterion/obligation 语义；
- owner API 是否允许拒绝、Unknown、旧 head、冲突和延迟；
- 五个 current head 是否属于同一有效时间切片；
- compensation 是否保留不可逆 residual；
- owner query 与人工等待成本是否吞噬净价值；
- connector migration 是否丢 causal identity 或 finality phase。

所以“成熟组合已经完整解决”应降级为：

```text
MATURE_COMPOSITION =
  PRIMARY_END_TO_END_SUFFICIENCY_CANDIDATE
  UNDER_EXPLICIT_CLOSED_DOMAIN_PRECONDITIONS
  NOT_YET_EXECUTED
```

若它在下一实验完整通过，这就是通爻研究的正向完整结果，不需要人为保留 novel residual。
人类制度或合法强中心完整通过同样如此。

## 八、最强反例

### 反例 A：真实但不合格的 Effect

```text
任务：修复 CNC-17
Authority：旧 mandate 已撤销
事件：旧 work order 被 replay，CNC-17 参数真实改变
readback：target sensor 确认 postcondition changed
```

它击穿：

- `ApplicablePolicy=false → QualifiedEffect=false` 足以代表现实；
- 不合格 Effect 可以从 episode graph 中省略；
- G5 deny 后 G6/G7 无需处理现实后果。

正确结果必须同时保存 illegal Attempt、real Effect、not-counting-toward-Q、recovery 和
liability。

### 反例 B：readback 相同、因果相反

```text
W0：目标 postcondition 在 Attempt 前已经存在
W1：本 Attempt 通过 target-side operation token 建立 postcondition
两边 current readback：TRUE、同 object/version/head
```

它击穿“readback 完整覆盖 Effect/episode result”。readback 只确认当前状态；没有
before-state、operation token 或排他 writer 证据时，`Cause=UNKNOWN`。

### 反例 C：五个真实 head 的伪完成

```text
t1：Acceptance(v4)=TRUE
t2：v5 supersede，Acceptance(v4) 不再适用
t3：Settlement(v4)=COMPLETE
controller 分时读取：旧 Acceptance head + 新 Settlement head
```

每个 ledger response 都真实且由正确 owner 签发，但 `phi(heads)=Done` 组合出了一个从未在
同一有效时间成立的 episode 状态。需要有效时间、head vector、一致 cut 和 supersession
规则，不是更多签名。

### 反例 D：owner API 是签名过的旧 projection

```text
private target state：REVOKED / v5
owner readback adapter：signed CURRENT / v4
grader truth：v5
method：只见合法签名的 v4
```

这不是 method 应当凭空猜中的失败，而是 owner observation channel 的质量与成本问题。
若 fixture 从 grader truth 直接复制 API response，就把最承重问题提前解答了。

## 九、最小修订门与下一实验改变

### 修订门

在 G6 设计进入 runner 前，至少完成：

1. 将单一 `role` 改为 occurrence/claim 上的多对多 `RoleAssignment`；
2. 分开 raw occurrence、episode binding、Authority、CountsTowardQ 和 recovery relevance；
3. 将单 typed DAG 拆成 occurrence、authority/qualification、obligation/control 三个可引用层；
4. 将 owner ledger 定位为 claim/current-head carrier，不作为自动 truth；
5. 将 readback 指标拆成 current postcondition、transition、causal edge 和 count；
6. 为多 ledger `Done` 冻结有效时间、一致 cut、supersession/dispute 和 reopen 规则；
7. 将 Settlement 改为 obligation + scheme-specific subgraph，不使用全局 bool；
8. 将 strong center 分成 S1/S2/S3 三个 Authority strata；
9. Track A 不再以复制输入 normative edges 得到 typed-edge F1；
10. owner API 与 grader 独立生成，强制 stale/refused/timeout/wrong-object/fork；
11. strong center、mature composition 和 human institution 使用独立 executable；
12. 先过 truth-copy、method-alias、wrong-object、read-skew 和 unauthorized-real-effect
    invalidation gates，再启用任何 coverage。

### 下一实验怎样改变

下一次最小高信息量运行不是 96 个同源 cells，而是 12 个高区分 paired worlds：

| pair | 唯一承重差异 | 主要判别 |
|---|---|---|
| P1 | authorized no-effect / unauthorized real-effect | occurrence 与 qualification 分离 |
| P2 | current state pre-existing / exact attempt caused | readback 与 causal edge 分离 |
| P3 | correct target / wrong target real damage | wrong-object Effect 与 recovery |
| P4 | fresh head / signed stale head | owner claim 与 current truth |
| P5 | Effect only / Effect + actual Adoption | 非蕴含 |
| P6 | correct Acceptance object / same owner wrong version | exact-object stance |
| P7 | one owner Accept / another Reject | disagreement preservation |
| P8 | provider Settled / beneficiary PaidOut | settlement phase |
| P9 | payout complete / chargeback or reversal open | finality predicate |
| P10 | timeout before commit / timeout after Effect | authoritative recovery 与 duplicate |
| P11 | five heads from consistent cut / read-skew | derived Done safety |
| P12 | independent owners / legally delegated single center | Authority stratum 和净价值 |

每个 pair：

- method-visible packet 不含 realized label；
- owner API 从独立 store/act 生成，不从 grader row 复制；
- strong center、mature composition、human institution 分开运行；
- 评分 raw occurrence、qualified role、Authority、causal edge、duplicate、wrong object、
  Settlement phase、recovery、latency、HITL、披露与治理成本；
- 对信息论不可区分 case，允许 `UNKNOWN`，但受预注册 liveness 和成本 floor 约束。

只有这一小组先关闭 evaluator 与 oracle 问题，扩展 topology 和样本量才有意义。

## 十、最终证据边界

- `VERIFIED`：五层不构成普遍固定 ladder；workflow/event/receipt 不蕴含外部 Effect；
  owner Acceptance 不可由 controller 代签；合法强中心、人类制度和成熟组合都必须被允许
  正面获胜。
- `PLAUSIBLE`：role-relative semantics、exact ObjectRef、claim/evidence 分离、
  owner-scoped ledgers、task-specific control graph 和 held-out motifs 是有价值的候选。
- `OVERSTRONG`：单 role/单 DAG、`QualifiedEffect=false` 足以代表非法真实改变、
  readback 完整覆盖 Effect、单 owner ledger 自动提供 truth、一个 `Done(heads)` 安全聚合、
  单枚举 Settlement 完整覆盖、给定 DAG 后仍用 typed-edge F1、成熟组合已经完整解决。
- `UNRESOLVED`：端到端成熟组合、合法委托强中心相对其他同权限方案的净增益、owner API
  的现实可得性与成本、consistent cut、跨 connector causal identity、义务 finality、
  真实 Adoption/Acceptance 和现实任务外部效度。

本审计不否定 Pro 的零假设。当前仍没有证据要求发明新的 Effect 协议。更准确的结论是：

> Pro 已提供一份高质量的 G6 问题重建和成熟解候选，但把最难的观察、绑定、因果、时序和
> finality 条件装进了 owner ledger/readback 前提。下一步应先验证这些前提如何真实形成和
> 失效；成熟组合、合法强中心或人类制度只要端到端闭合，就是完整正向结果。

本轮只新增本审计文件；未修改 `research/NOW.md`、`PROGRAM.md`、Problem、LineContract、
MechanismProfile 或任何正式研究状态，也未执行生产或现实动作。
