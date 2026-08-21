# G4 ChatGPT Pro 返回：独立敌对审计

日期：2026-07-29
审计对象：[`G4-return.md`](./G4-return.md)
正式问题入口：[`research/NOW.md`](../../../../../../NOW.md)
当前 G4 合同：[`lines/04-capability-realization-v2.json`](../../../../lines/04-capability-realization-v2.json)
本地对照：[`WAVE-010-G4-AUDIT-RESPONSE-V2.md`](../../WAVE-010-G4-AUDIT-RESPONSE-V2.md)
状态：`INDEPENDENT_ADVERSARIAL_AUDIT / NO_FORMAL_PROMOTION / NO_MECHANISM_STATUS_CHANGE`

## 总判定

```text
USEFUL_METHOD_CORE
MATERIAL_SCOPE_MUTATION
MATURE_COMPONENT_FACTS_PARTLY_VERIFIED
MATURE_COMPOSITE_NOT_EXECUTED
STRONG_CENTER_NOT_EXECUTED
PACKET_IMPOSSIBILITY_REQUIRES_STRONGER_ASSUMPTIONS
PROPOSED_SCALE_NOT_JUSTIFIED
```

这份返回最有价值的部分不是“闭合世界已经基本解决”，而是三个较窄的判断：

1. capability、history、readiness、IAM、reservation、attestation、Authority 与 recovery
   彼此不自动蕴含；
2. 可依赖性经常需要通过 current read、Authority、reservation/fence 和 readback 被构造，
   不能只靠分类器从旧 packet 猜出；
3. 如果一个方法在整个允许交互期内都无法取得会区分两个相反世界的新观察或新约束，它就
   不能同时获得零误依赖和满安全召回。

但返回没有完成原 G4 的判别。最严重的问题是它把“冻结操作能否在首次尝试中成功兑现”
部分改写成“截止时间前能否到达某个 authoritative terminal state”。后者是重要且可用的
G4/G6/G7 交叉合同，却不是前者的同义改写。一个退款被权威地拒绝且确认无副作用，可以满足
bounded terminal contract，却仍然是“退款首次兑现失败”。

它也没有证明成熟组合或强中心已经取得所需的 current read、Authority、fencing 与
authoritative readback。返回列出的成熟构件大多真实存在，但“构件存在”与“在同一 exact
operation 上完成跨合同闭包”之间仍隔着尚未运行的系统。

因此，总判定不是否定 Pro 返回，而是：

> 可保留为 G4 的候选问题重建、成熟基线设计和实验攻击清单；不可登记为 G4 已解决、成熟
> 组合已胜出、强中心已公平比较、packet-identical 已形成无条件不可能性，或 17,280 条
> trajectory 已具有必要信息增益。

## 审计依据与证据边界

本审计直接读取了：

- 当前 `PROGRAM.md` 对 G4 的定义：预测 exact operation 在给定条件下能否首次完成；
- ACTIVE `LINE-04-CAPABILITY-REALIZATION-V2`：要求首次尝试前冻结预测，并用 executor
  result、authoritative postcondition 与独立 readback 分别验收；
- Pro 的完整本地转写；
- 本地 G4 v1/v2 fixture、worker、oracle、simulator 与审计回应。

本地 v2 self-test 已实际复跑并以 `SELF_TEST_PASS` 结束，复现：

```text
worlds = 12
safe / unsafe = 4 / 8
REFERENCE_COMPOSITION_HITL = TP 3 / FP 0 / TN 8 / FN 1
safe recall = 3/4
unsafe false RELY = 0/8
abstention = 5/12
strong center = NOT IMPLEMENTED
recovery = LABEL MATCH ONLY
```

这些数字只证明当前代码对当前手写 oracle 的一致行为，不证明现实频率、成熟产品组合、
strong center、恢复正确性或实际能力兑现。

外部技术断言只用官方文档或原始论文抽查。抽查能确认若干构件事实，但不能把构件事实提升成
组合有效性证据。

## 逐项审计

### A1. exact operation 而非“主体固有能力”

**判定：VERIFIED**

把依赖命题绑定到 operation、executor、environment、version、arguments、target、Authority、
deadline、recovery 与 acceptance rule，和当前 G4 合同一致，也能阻止“服务总体健康”
冒充“本次操作可兑现”。

最强反例是同一服务、同一版本对两个参数或两个目标分别成功和失败；服务级 capability label
无法区分。

最小修订门：

- 保留 Pro 的 exact-operation tuple；
- 再明确它是预测单位，不自动成为 G5 Authority、G6 Effect 或 G7 recovery 的共同成功状态；
- `acceptance_rule` 只能作为本次预测的输入，不能让 G4 直接宣告 Acceptance 已发生。

对下一实验的改变：所有臂必须收到同一个冻结 tuple；任何改变参数、权限、资源或恢复路径的
动作都生成新 tuple，不允许把修复后成功回填为旧 tuple 的首次预测正确。

### A2. “成功兑现”被换成“有界终态”

**判定：OVERSTRONG**

Pro 明确区分了 `SUCCESS_BY_DEADLINE` 与
`AUTHORITATIVE_TERMINAL_STATE_BY_DEADLINE`，这是优点；但它随后把 D 作为生产默认，并在
最终问题重写中把 G4 的目标中心改成“有界终态契约”。这没有保留原问题的完整判别。

最强反例：

```text
Refund(127.43 USD)
→ processor authoritative DECLINED_NO_EFFECT
→ 300 秒内无未知副作用
```

它对“结果可决性”是成功，对“退款首次兑现”是失败。若两者只共享一个 `SAFE` label，
成熟组合会因正确失败而被算成“能力兑现成功”，首次成功 precision/recall 随之失真。

最小修订门：冻结两个互不替代的 outcome：

```text
Y_success:
  首次 attempt 是否在 horizon 内形成预注册的成功 executor result
  与 authoritative postcondition

Y_resolution:
  是否在 horizon 内到达一个预注册、可权威重建、无未识别副作用的 terminal state
```

另行记录 `Y_effect / Y_acceptance`，但不得由 G4 自动填充。只有用户或正式合同明确把
“有界可决性”定为任务价值时，`Y_resolution=1` 才能作为该任务的最终成功；它仍不把
`Y_success=0` 改成 1。

对下一实验的改变：每个 case 分别报告 success prediction 与 resolution prediction 的
confusion matrix。成熟组合可能在 resolution 上胜出、在 success 上仍 Unknown；这仍是
正向且更准确的结果。

### A3. “判断”与“使其变得可依赖”之分

**判定：VERIFIED**

current query 是观察；取得 reservation、Authority commitment 或 target fence 是改变世界。
Pro 对这一差异的识别比单一 capability classifier 更准确。

但这也暴露了其指标的一个未闭合点：如果 policy 可以在评估中改变世界，那么
`safe_to_rely` 不能总是一个与 policy trace 无关的冻结布尔标签。

最强反例：

```text
t0: resource 未预留，Y_success_pre = false
policy: 合法 request_reservation，目标端返回 binding fence
t1: 同一业务意图已形成新的可执行状态，Y_success_post 可能为 true
```

若 oracle 固定使用 t0 label，主动形成条件的好方法会被误判；若 oracle只看 t1，又会把
intervention 成功回填成 t0 预测正确。

最小修订门：

- `P0`：任何形成动作前的 prospective prediction；
- `I`：实际 query/commitment/reservation/fence 操作及成本；
- `P1`：形成动作后重新冻结的新 prediction；
- 分别验收 `P0 correctness`、`formation success` 与 `P1 correctness`。

对下一实验的改变：oracle 必须是 trace-dependent，且保留 t0/t1 两个事实快照；不得只用一个
`safe_to_rely` 覆盖预测与构造。

### A4. 成熟构件分别提供的能力与边界

**判定：VERIFIED**

代表性技术事实经一手来源抽查成立：

- RFC 9334 明确说明 attestation freshness 只能缩小窗口，生成后状态或 policy 仍可能立刻
  改变；
- Kubernetes 官方文档明确区分可移动 tag 与不可变 digest；
- etcd 官方文档明确说明 lease 本身不保证互斥，etcd lock 不能单独保护外部资源，外部目标
  需要版本校验/fencing；
- AWS 官方工程文档用响应超时说明“已执行/未执行”歧义，并要求 reconciliation 或幂等
  request identity；
- PostgreSQL 官方文档确认 SERIALIZABLE 只对成功提交的数据库事务提供序列化语义，冲突时
  应重试整个事务。

这些来源支持 Pro 的“非蕴含矩阵”，不支持“把这些名字连起来就已经形成 G4 solution”。

最强反例：PostgreSQL 中的 intent/outbox 原子提交成功，外部机器却在 fence 检查前执行了旧
命令；本地 serializability 没有自动扩张到外部物理效果。

最小修订门：每个构件必须声明其 authority domain、原子域、freshness、外部副作用边界与
实际 readback owner；跨域箭头需由运行证据而不是产品名闭合。

对下一实验的改变：把构件能力作为可调用 primitive，不把 `current=true`、`fenced=true`
或 `readback=authoritative` 直接写进 method packet。

### A5. “闭合世界已经基本解决”

**判定：OVERSTRONG**

如果“闭合世界”被定义为所有关键状态可查询、所有 Authority 已可调用、所有资源可被目标端
fence、所有副作用幂等或可安全补偿、所有结果都有 authoritative status API，那么“可以用
成熟技术闭合”接近按前提重述结论。它尚未说明真实 T2/T4/T6 中这些条件是否成立，也没有
运行组合失败。

最强反例：同一组织内仍可能有数据库、支付处理方、PLC、人工批准与 QA 五个不同事实域。
组织归属相同不等于一个原子域，也不保证 readback owner、撤销传播和物理 fence 已存在。

最小修订门：把结论改成：

> 成熟构件覆盖了闭包所需的大部分 primitive；在一个明确列出并实际满足 current read、
> Authority、target fence、idempotency 和 readback 前提的有界环境中，成熟组合是首要
> 候选，而不是已验证解。

对下一实验的改变：先选一个真实可执行但可逆的 operation，实际记录每个 primitive 的
request/response、head、延迟、失败和成本；缺失接口本身作为结果，不允许用 fixture 常量
补齐。

### A6. mature composite 是否免费获得 current read / Authority / fencing / readback

**判定：PLAUSIBLE**

Pro 在文字上知道这些能力不能免费获得：它提出 no-free-oracle、调用计费、披露/时延向量，
也承认目标系统必须真实执行 fence。因此它的实验规范方向正确。

但它的“最强成熟组合”算法直接写成：

```text
authoritative_query
validate Authority
acquire reservations and fencing tokens
authoritative readback
```

尚未说明这些调用在 T2/T4/T6 是否存在、由谁实现、失败率多高、何时拒绝，以及为组合提供
这些服务是否已经等于建成待研究的新基础设施。

最强反例：处理方提供 IAM、health 和 submit，却不提供 operation-keyed status；此时
`authoritative readback` 不是配置项，而是不存在的能力。把它加入 MCB 输入会提前消除最承重
残差。

最小修订门：

- baseline 只能调用任务环境原生存在的 primitive；
- 若需新建 current-query、commitment、fence 或 readback adapter，必须计入该 arm 的代码、
  权限、披露、人工、时延和维护成本；
- adapter 自身必须接受故障注入；
- 不允许 evaluator 把原始 revision 与 policy 先解释成 `head_current=true` 再交给方法。

对下一实验的改变：parent broker 记录不可由候选改写的 operation log；比较的是合法地取得
这些事实和约束的全过程，而不是谁更会读取预裁决布尔字段。

### A7. 同权限 strong center 的公平性

**判定：PLAUSIBLE**

Pro 要求 strong center 与其他方案拥有相同 query API、freshness、rate limit、披露预算和
Authority，这是一条正确的公平性方向。它也正确指出集中计算不会凭空获得未披露事实。

但“中心拥有所有 Authority 就改变了问题”不能作为通用排除规则。Problem v2 明确把强中心、
平台和人工制度视为正向候选；在某些真实制度中，主体可能合法地把精确、有限、可撤销的权限
委托给中心。只要委托成本、退出权和失败边界被计入，这仍可能是原问题的完整解，而不是作弊。

最强反例：

- 成熟组合臂可调用三个 owner HITL 并取得 binding commitment；
- strong center 臂只被允许读取相同旧 packet，却不允许调用相同 owner；
- 结果会人为证明组合优于中心。

反方向也同样成立：若中心可直接读私有数据库而组合只能走公开 API，中心胜出也不公平。

最小修订门：测试前冻结逐项权限—动作矩阵：

| 能力 | MCB | strong center | model/hybrid |
|---|---:|---:|---:|
| 原始 current query | 同配额 | 同配额 | 同配额 |
| request Authority | 同 owner / SLA | 同 owner / SLA | 同 owner / SLA |
| acquire commitment/fence | 同接口 | 同接口 | 同接口 |
| readback | 同 source / freshness | 同 source / freshness | 同 source / freshness |
| lawful delegation | 同样允许并计成本 | 同样允许并计成本 | 同样允许并计成本 |

strong center 必须由不同实现者只读 public contract 实现，不能再像本地 v1 那样直接调用
`mature_composition(packet)`。

对下一实验的改变：同时保留两个场景族：

1. 单一真实 Authority 可合法集中；
2. 多个独立 Authority 仅提供有限接口。

若中心在第一类完整解决，它就是正向解；第二类失败只能限定到第二类。

### A8. 完整交互不可区分时的不可能性

**判定：VERIFIED**

在下列更强前提下，Pro 的数学核心成立：

```text
对任一允许 policy π 和决策前任一合法 action history，
W+ 与 W- 产生的 lawful observation distribution 相同；
允许动作也不能在决策前改变两个世界的依赖真值；
但预注册 ground truth 相反。
```

此时确定性 policy 给出同一 decision，随机 policy 给出同一 decision distribution，不可能
同时对这对世界实现零 unsafe false reliance 与满 safe recall。

最强反例不存在于这些前提内；任何“突破”都意味着新增了观察、约束、Authority、风险预算
或不同的目标合同。这一结论不证明需要新协议。

最小修订门：把 Pro 的结论明确限定为
`full-lawful-interaction-equivalent paired worlds`，并声明适用 horizon、允许动作和
ground-truth 时间点。

对下一实验的改变：auditor 不只比较初始 packet hash，还应比较每个允许 action 在两个世界
中的 response distribution；发现合法分流接口时，该 pair 不再是 impossibility pair，而是
query-planning case。

### A9. 初始 packet 字节相同就足以推出不可能

**判定：OVERSTRONG**

初始 packet 相同只证明静态分类器不能区分，不证明可交互系统不能区分，也不证明合法形成
动作不能把 unsafe world 变成 safe world。

最强反例：

```text
initial packet(W+) == initial packet(W-)
request_reservation(X):
  W+ → BINDING_COMMITMENT(token=7)
  W- → REFUSED
```

一个合法查询/形成动作已能区分。另一个反例是两世界都能在请求后形成有效 commitment：
此时 ground truth 因 policy trace 改变，不能继续使用初始相反 label 评价。

最小修订门：

- passive pair：所有允许 read 的 transcript 相同，测试静态/只读不可区分；
- active pair：允许 request/probe/commitment，truth 按 trace 计算；
- hard pair：所有允许交互仍等价，才用于不可能性结论。

对下一实验的改变：三类 pair 分开计分，不能用初始 byte-identical 一列同时支撑三种结论。

### A10. `2160 / 17280` 运行规模

**判定：UNRESOLVED**

`3 domains × 6 fault families × 12 paired templates × 5 seeds × 8 repeats` 是数量展开，不是
信息增益或统计功效论证。目前没有：

- 已实现的六个独立比较臂；
- 每个 template 所区分的竞争机制；
- seed 是否真的改变 decision-relevant trace 的证明；
- 目标 effect size、预期 RELY rate 或成本预算；
- 对 template/domain/seed 聚类相关性的处理；
- 运行 2,160 个 deterministic world 后相对 20 个高区分 world 的边际信息。

最强反例：确定性 MCB 对 100 个只改随机 ID、但所有 decision features 相同的 world 给出同一
结果。重复 100 次增加运行数，不增加机制判别。

最小修订门采用顺序设计：

1. 先跑 `6 fault families × 2 causally distinct timings` 的 12 对开发 pair；
2. 再用一个完整 held-out domain 各取 1 对，共 6 对；
3. 共 18 对 / 36 cases 作为 harness 与 arm-survival gate；
4. deterministic arm 对同一 trace class 只跑一次；
5. stochastic arm 可每 world 重复 8 次，但这些重复只估计 within-world consistency；
6. 只有出现新的 decision-boundary crossing 或未闭合 failure interaction，才扩展 template；
7. 通过 gate 后，再按目标 UFR、实际 RELY rate、cluster design effect 和预算做正式样本量。

这不是把最终安全验证缩到 36 cases，而是防止在 arm、oracle 和 truth 定义尚未成立时先生成
17,280 条低信息 trajectory。

对下一实验的改变：当前下一步不是扩量，而是先让 MCB 与 strong center 成为真实独立 arm，
把 primitive acquisition 和 post-run readback 跑通。

### A11. 零失败时 `3/n` 规则

**判定：PLAUSIBLE**

零事件的 95% 单侧上界近似 `3/n` 是常用 binomial rule-of-three；作为量级提示合理。

但这里的 `n` 必须是适用抽样假设下的独立 `RELY` 暴露，不是全部 task 数，也不是同一 hidden
world 的八次相关 trajectory。一个几乎总 abstain 的方法可能运行 17,280 次却只有很少 RELY，
仍无法支持低 UFR 上界。

最强反例：3,000 次 RELY 全来自同一个 template 的重复 seed；共同遗漏的故障会让名义上界
极小，但对新 template 没有任何保证。

最小修订门：

- 预注册估计对象：fixture population、task family 还是现实分布；
- 分别报告 raw RELY exposure 与独立 pair/template/domain 数；
- 使用分层或 cluster-aware interval；
- UFR conditional、safe recall、abstention 与成本同时报告；
- 不把合成分布的区间外推为现实事故率。

对下一实验的改变：8 次重复只进入 stochastic consistency；安全覆盖主要由新的因果 template
与跨域 held-out 提供。

### A12. 模型与人工的定位

**判定：PLAUSIBLE**

把通用模型放在解析、query planning、异常解释与 escalation，而不让它从同一 packet 创造
Authority 或 truth，方向合理。把具有真实 Authority、独立信息和拒绝权的人工制度视为完整
候选，也符合本研究的 solution-first 原则。

原始论文抽查支持两个较窄事实：

- τ-bench 原始论文报告当时强 function-calling agent 在其任务中成功率低于 50%，并提出
  `pass^k` 测量重复一致性；
- AgentAbstain 预印本确实报告 17 个模型、4 种 harness、最佳 paired accuracy 59.5%。

这些任务特定结果只能说明“模型强 ≠ 自动安全依赖门”，不能证明未来模型、所有任务或 G4
本身的能力上界。

最强反例：模型通过选择一次合法 current query 发现撤销，而固定规则未查询；模型可以改善
获取证据的策略，但改善来自新 observation，不是模型从旧 packet 猜中 hidden truth。

最小修订门：模型与人工只通过同一 broker 调用 primitive；所有 query、披露、时延、owner
打断与拒绝都计费；commit gate 的最终依据必须可重建。

对下一实验的改变：报告“模型选择了什么合法信息/约束”与“在没有新信息时如何决策”，不要
只报告最终 success。

### A13. “真正 residual”已被穷尽

**判定：OVERSTRONG**

Pro 列出的低披露 current query、binding commitment、跨域 fencing、authoritative outcome
receipt 和撤销语义都是高价值候选 residual，但当前材料没有证明它们穷尽了 G4。

最强反例是原 G4 的核心比较对象 `DERIVED-CLAIM`：即使所有 primitive 存在，跨来源派生视图
是否在 held-out operation 上有不可由更小查询重建的增益仍未运行。另一个未穷尽变量是
capability 本身对新输入分布的技术泛化，而不是 Authority 或 recovery。

最小修订门：把“真正剩余”改为“当前最承重的候选残余”，并保留至少三类竞争解释：

1. primitive 缺失；
2. primitive 都存在但组合/维护错误；
3. 技术 capability 对 held-out operation 本身不能前瞻泛化。

对下一实验的改变：先做消融归因。若增益只来自 readback，就归 readback；若只来自 reservation，
就归 reservation；若更小 primitive 组合重建全部结果，派生 claim 降为 adapter。

### A14. “不需要新协议”作为科学零假设

**判定：VERIFIED**

这是合理且与当前研究宪章一致的默认：成熟组合、同权限强中心、平台或人工制度若完整解决，
就是正向结果，应直接采用；不能以证明通爻独特为目标。

最强反例不会否定零假设的设置，而只会拒绝它：在公平权限和成本下，成熟臂持续无法取得某项
必要 observation/constraint，而候选以可独立验证的新 primitive 闭合它。

最小修订门：零假设的“失败”必须定位到精确环境、任务、primitive、权限、成本和 horizon，
不能从一个 cross-Authority case 推到所有闭合世界。

对下一实验的改变：若 MCB 或 strong center 达标，停止发明并将其登记为解决方案候选；若
不达标，只开放实际受检验的 residual。

## 与本地 G4 v2 审计 / simulator 的冲突与互补

### B1. 信号非蕴含

**判定：VERIFIED**

两者互补。Pro 给出广义工程解释；本地 v2 用 12 个合成 case 可运行地显示 declaration、
readiness、probe/IAM、reservation、current head、recovery 与 hidden dependency 不能互相
替代。

但本地结果只支持“当前手写规则能区分这些标签”，不支持成熟组合已经运行。

### B2. no-free-oracle

**判定：OVERSTRONG**

本地 v2 没把 `safe_to_rely` 或 case id 交给 worker，这是实际改进；但 method packet 已包含：

```text
exact_probe.status
exact_probe.head_current
permission.status
permission.head_current
reservation.status
reservation.current
recovery_evidence
dependency.query_result
human.owner_stance
```

这些不是 ground-truth oracle，却是已被上游裁决的高价值特征。worker 没有执行 current read、
验证 Authority、获取 fence、支付披露/时延成本或做 readback。因此 `REFERENCE_COMPOSITION`
不能被解释成 Pro 的 MCB 实现。

最小修订门：公开 fixture 只提供 primitive endpoint/initial evidence；各 arm 自己选择查询、
请求 commitment、取得 raw receipt，再由固定 verifier 检查 receipt 与 revision。

### B3. packet-identical

**判定：PLAUSIBLE**

本地 v2 的 hidden valid/revoked pair 确实产生相同 method packet，能证明当前固定只读 worker
必须给同一 decision。它与 Pro 的 passive indistinguishability 互补。

但 simulator 没有允许 query/commitment action，也没证明完整交互等价；所以它不能支持 Pro
更广的“任何算法”表述。

最小修订门：新增 active-query pair 和 full-interaction-equivalent pair，分开结论。

### B4. strong center

**判定：VERIFIED**

本地 v2 已正确撤回 v1 的“因果等价”：v1 只是函数别名；v2 完全没有实现或评分 strong
center。Pro 把 independently implemented same-permission center 列为必选臂，正好补上这个
缺口。

下一步不能再用函数别名；必须由不同实现者只读 public primitive contract 构建。

### B5. recovery

**判定：VERIFIED**

两者一致：本地 `8/8 unsafe label-match` 不是 recovery correctness。Pro 要求实际 action、
readback、duplicate effect、wrong compensation 与 resolution latency；这是正确补强。

下一步必须把 `REAUTHORIZE / RE_RESERVE / RECOVERY_REHEARSAL / GLOBAL_REOPEN` 至少一项从
字符串变成状态转换，并由独立 owner 读回。

### B6. success contract

**判定：OVERSTRONG**

本地 v2 把 `T2-RECOVERY-UNKNOWN` 标为 `safe_to_rely=false`，即使当前 exact operation 的
probe、permission、reservation、telemetry 与 attestation 都为绿色。这个 label 对“强恢复
合同”可能正确，但不能单独证明“首次执行会失败”。

因此本地 v2 已部分继承 Pro 的 outcome-strength 混合。修订时必须拆成 `Y_success` 与
`Y_resolution`，否则会继续偏离 ACTIVE G4 line。

### B7. 是否应立即扩到 17,280 trajectories

**判定：VERIFIED**

本地 v2 的结论“不要继续扩充同作者标签 fixture，先实现独立 arm 或真实 recovery”比 Pro
直接给出的规模更符合当前信息状态。两者并不根本冲突：Pro 的规模可保留为正式验证候选上限，
但只能在 arm、oracle、primitive broker 和 truth 定义通过最小门之后启动。

## 最强综合反例

以下单一反例同时攻击 scope、free input、center fairness、packet theorem 与统计规模：

```text
任务：首次退款 127.43 USD

t0 public packet:
  capability declared
  service healthy
  IAM token active
  history 99.99%
  no operation-keyed processor status

允许动作:
  Q1 query merchant Authority
  Q2 request processor idempotency commitment K
  Q3 submit(K)
  Q4 read_status(K) -- 当前环境原生不提供

W+:
  Q1 approves, Q2 returns binding receipt, submit executes once

W-:
  Q1 refuses, Q2 refuses, no effect
```

结论：

1. 初始 packet 相同，不代表完整交互不可区分；
2. 一个合法 query 已能分流，所以 byte-identical 不是绝对不可能性；
3. 若 mature arm 被免费给出 `Authority=APPROVE` 和 `readback=available`，它获得了环境中
   不存在的 primitive；
4. 若 strong center 不准调用 Q1/Q2 而 MCB 可以，比较不公平；
5. W- 达到 `REFUSED_NO_EFFECT` 是 bounded terminal success，却是退款 success failure；
6. 把同一模板重复 8 次只能估计随机一致性，不能弥补缺失的 read_status 世界；
7. 真正研究结果可能是：现有 MCB 对 W+ 完整解决、对 W- 正确拒绝，但不能在 submit ACK
   丢失后 authoritative resolution；残差只归 operation-keyed readback，不归新 capability
   schema。

## 可执行的最小修订门

在启动大规模实验前，必须同时满足以下六门。

### G0 — 双 outcome 与 intervention 谱系

**判定：VERIFIED**

冻结 `Y_success`、`Y_resolution`、P0、intervention trace、P1。任何 reservation、Authority、
新权限或恢复动作不能回填旧预测。

### G1 — primitive broker

**判定：VERIFIED**

方法只能获得原始 primitive 与 receipt：

```text
read_revision
read_policy
get_token_state
run_exact_probe
request_authority
request_reservation
submit_operation
read_operation_status
```

每次调用记录 source、revision、latency、bytes、sensitivity、human interruption、failure。
禁止免费 `is_safe_to_rely`，也禁止上游直接提供未经成本核算的 `head_current=true`。

### G2 — 三个独立必选 arm

**判定：VERIFIED**

至少实现：

```text
STATIC
MATURE_COMPOSITE
SAME_PERMISSION_STRONG_CENTER
```

本轮研究若仍要检验派生视图，再加入 `DERIVED_CLAIM`。实现不得共享 decision function；只
共享 public primitive schema。成熟组合或 strong center 完整解决就是正向结果。

### G3 — trajectory-dependent oracle 与独立 readback

**判定：VERIFIED**

controller 冻结隐藏事件；方法完成后，独立 auditor 从 immutable world log 与目标 owner
readback 重建：

- 首次 executor result；
- authoritative success postcondition；
- terminal resolution；
- duplicate/unauthorized effect；
- 实际 reservation/fence；
- recovery 后状态。

controller 与 auditor 不一致标记 harness defect，不计候选成绩。

### G4 — 18 对信息增益 pilot

**判定：PLAUSIBLE**

先用 12 对开发 pair 覆盖 6 个 failure family 与两个真正不同的 timing，再用 6 对完整 held-out
domain 检验迁移。只有每对都写清“区分哪两个机制”且至少一次穿过 decision boundary，才进入
正式扩量。

### G5 — 公平权限与成本矩阵

**判定：VERIFIED**

所有 arm 在同一 task 上获得相同初始信息、primitive、Authority channel、资源预算、human
SLA 与 horizon。允许 lawful delegation，但成本和退出条件必须计入。不得故意削弱中心，也
不得给组合隐藏 oracle。

### G6 — 启动大样本的判据

**判定：VERIFIED**

只有在以下条件成立后，才根据功效与安全目标决定是否运行 2,160/17,280：

- 三个 arm 实际运行；
- P0/P1 与双 outcome 无歧义；
- primitive broker 无免费裁决字段；
- 至少一个 recovery/readback 状态转换已执行；
- 18 对 pilot 暴露了不止同一固定规则；
- `n`、聚类单位、目标 UFR、预期 RELY rate 和成本已预注册。

## 对下一实验的实际改变

当前最高信息增益动作不是新增协议，也不是扩到 17,280 trajectory，而是：

> 选一个可逆 exact operation，先实现同权限 MCB 与 strong center 两个独立 arm；两者只通过
> primitive broker 获取 current read、Authority、reservation/fence 与 readback。冻结 P0，
> 实际运行一次形成动作与一次 attempt，再由独立 owner 同时读回 `Y_success` 与
> `Y_resolution`。

若成熟组合或中心完整通过，应直接采用并停止重复创造。如果二者失败，只能把结论定位到实际
缺失的 primitive、Authority 或跨域闭包；不能用这次失败推广到 G4 全域。

## 外部一手来源

以下来源只用于核实代表性技术事实，不是组合有效性证据：

- [RFC 9334 — Remote ATtestation procedureS Architecture](https://www.rfc-editor.org/rfc/rfc9334.html)
- [Kubernetes — Images](https://kubernetes.io/docs/concepts/containers/images/)
- [Kubernetes — API Concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/)
- [etcd — Notes on the usage of lock and lease](https://etcd.io/docs/v3.5/learning/why/#notes-on-the-usage-of-lock-and-lease)
- [AWS Builders’ Library — Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
- [PostgreSQL — Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [τ-bench 原始论文](https://arxiv.org/abs/2406.12045)
- [AgentAbstain 原始预印本](https://arxiv.org/abs/2607.10059)
- [OSHA 29 CFR 1910.147 — Lockout/Tagout](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147)

Pro 转写中的 Temporal、Debezium、Consul、SPIFFE、OAuth/IAM propagation、NIST dual
authorization 与 automation-bias 等来源只保留了站点标签，没有保存具体 URL、版本与定位。
本审计未用这些未定位陈述支撑总判定；若它们要进入正式研究材料，应补齐一手来源、版本、
精确段落与实际适用边界。

## 不支持的结论

本审计不支持：

- G4 已解决；
- mature composite 已在 T2/T4/T6 实际闭合；
- strong center 与 mature composite 等价、优于或劣于；
- bounded terminal contract 等于首次成功兑现；
- 初始 packet hash 相同足以证明交互式不可能性；
- 本地 12-case v2 是 Pro MCB 的实现；
- `8/8` recovery label match 是恢复成功；
- 2,160/17,280 是当前必要或充分样本量；
- 需要通爻专属新协议；
- 不需要任何新 primitive；
- 任一正式 MechanismProfile、LineContract、NOW 或 PROGRAM 状态应因此改变。
