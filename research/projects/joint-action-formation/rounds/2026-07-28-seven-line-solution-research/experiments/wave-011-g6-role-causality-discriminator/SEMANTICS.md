# G6 无损语义模型

状态：`LOCAL SYNTHETIC MODEL / NO FORMAL PROMOTION`

本模型落实 G6 Pro return 经独立审计后仍成立的部分，并刻意不把它变成新的五级事实根。
它不读取 private oracle，不产生 method 决策，也不声称 owner claim 等于现实。

## 1. 六个正交对象

同一个现实事件必须能同时保留以下六个判断，任何一个都不能覆盖另一个：

1. `Occurrence`：世界或制度中实际出现的一次 raw occurrence；
2. `EpisodeBinding`：它是否绑定当前 episode、对象、版本和有效时间；
3. `AuthorityAssessment`：相关 actor/issuer 在精确角色和对象上是否有权；
4. `QualificationAssessment`：该 occurrence/claim 是否真的适合被赋予某一角色；
5. `CountsTowardQ`：它是否计入当前冻结 `Q` 的成功；
6. `RecoveryAssessment`：无论是否计入 `Q`，它是否造成需要恢复、补偿或追责的现实后果。

因此，`unauthorized real Effect` 的无损表示是：

```text
Occurrence = PRESENT
RoleAssignment = EFFECT / QUALIFIES
Authority = UNAUTHORIZED
CountsTowardQ = FALSE
Recovery = REQUIRED
```

`wrong-target real damage` 同样保留真实 occurrence 和实际受影响对象；它只是在原 episode
上 `exact_binding=FALSE`、`CountsTowardQ=FALSE`。不允许用“不合格”把损害从历史中删除。

## 2. role 是多对多 assignment

`Attempt / Effect / Adoption / Acceptance / Settlement` 是 episode-relative role，而不是
五种互斥物质，也不是固定 ladder。

`RoleAssignment` 的 subject 可以是一次 occurrence，也可以是 owner claim。同一 occurrence
可以在两个 episode 中承担不同角色；同一 episode 也可以把同一 occurrence 同时解释为本域
Effect 和某项义务的 Settlement。底层 occurrence 仍只保存一次，不能复制两份现实来增加
证据数。

每个 assignment 单独引用：

- binding；
- role qualification；
- Authority（适用时）；
- `CountsTowardQ`；
- recovery；
- obligation（Settlement 适用时）。

这些引用的 episode 和 subject 必须一致。模型拒绝跨 episode 拼接。

## 3. 三个图层

### occurrence/provenance graph

节点只有 raw occurrence，边只表达 `CAUSES / OBSERVES / CORRELATES / REVERSES /
COMPENSATES / SUPERSEDES`。因果边本身带 assertion status；trace 或时间相邻可保持
`UNKNOWN`，不自动升级为 `CAUSES=TRUE`。

### qualification/authority graph

节点是 owner claim、episode binding、role assignment、qualification、Authority、
`CountsTowardQ` 和 recovery assessment。它表达“谁对什么作了什么判断”以及这些判断怎样
支持、反驳、绑定、撤销或争议，不伪装物理变化。

owner ledger 只保存这个层面的 claim/current head。它没有 occurrence、sensor、actuator、
private truth 或 grader 字段。owner service 必须从自己的 store、sensor 或 institutional
act 形成 native response，再把 claim 写入 ledger。

### obligation/control graph

节点是 task gate、obligation 和 scheme phase record，边表达前置、阻断、推进、解除、反转
和 reopen。它可以派生当前控制结果，但不能成为新的事实根，也不能覆盖前两个图层。

三个图层通过显式 ID 引用组合；图内 edge 不允许跨层偷连。`validate_graph_separation()`
检查 node identity 也没有发生碰撞。

## 4. Claim/current head 与一致 cut

`Claim` 是 owner 对 occurrence/current state 的 assertion，不是自动 truth。它必须保存
issuer、scope、object、观察时刻、有效窗口、head sequence、evidence 和 supersession。

`OwnerLedger.current_head(event)` 只回答该 owner ledger 在给定 event 的当前 claim。
`SemanticModel.assess_head_vector()` 进一步检查来自多个 ledger 的 claim 是否曾在同一 event
同时成为 current heads。不存在共同有效切片时返回不一致，禁止把真实但分时的旧/新 head
聚合成伪 `Done`。

这只解决本地模型中的 temporal cut；它不宣称实现分布式 linearizability。

Authority 还显式区分三种不可混算的制度条件：

- `S1_UNIFIED_AUTHORITY`：同一主体真实拥有相关决定权；
- `S2_INDEPENDENT_OWNERS`：各方法只能查询独立 owner，不得代签；
- `S3_LAWFULLY_DELEGATED`：委托链与精确 scope 已冻结，仍保留 expiry、撤销和 recourse。

S3 的 `AUTHORIZED` 记录没有 delegation chain 与 scope ref 时会被模型拒绝。中心化控制本身
既不升级也不降级 Authority；只看实际 owner 和合法委托。

## 5. Settlement 是 obligation/scheme subgraph

全局 `Settlement=true` 不存在。每个 `Obligation` 冻结：

- scheme、债务人与受益人、金额与币种；
- 足以履行该义务的 required phases；
- 会阻断 finality 的 dispute/chargeback/reversal phases；
- 必要时的 finality horizon。

`SchemePhaseRecord` 由对应 owner claim 支撑，可分别表达 authorization、capture、provider
settlement、provider balance、payout、beneficiary receipt、contractual discharge、
dispute、chargeback 和 reversal。

例如：

- provider `Settled` 只有 `SCHEME_SETTLEMENT=TRUE`，若义务要求 `PAYOUT`，结论仍为
  `UNKNOWN`；
- `PAYOUT=TRUE` 但 `CHARGEBACK=TRUE` 时，当前 Settlement 为 `DISPUTED`；
- 冻结为 blocker 的 phase 没有明确 current state 时保持 `UNKNOWN`，不把“没看见争议”
  当作“争议不存在”；
- reversal 不删除历史 payout occurrence，而是增加阻断/反转节点。

## 6. 本模型能与不能说明什么

它能阻止以下表示层坍缩：

- 一个 `role` 字段迫使 occurrence 只能有一种身份；
- 未授权/错对象 Effect 因不计入 Q 而消失；
- signed stale head 被当作 current truth；
- 多个不同时间的 owner head 被拼成伪完成；
- provider settled 被当成 beneficiary paid out；
- payout 后开放的 chargeback/reversal 被压成全局 bool。

它不能证明：

- fixture 中的 occurrence 确实来自现实；
- owner service 没有从 private oracle 复制答案；
- readback 新鲜、对象正确或因果可识别；
- mature composition、strong center 或 human institution 已端到端解决 G6；
- 真人 Acceptance、现实 Effect、付款 finality、生产可靠性或一般化。

这些需要 runner 的 truth-copy、method-alias、wrong-object、read-skew 与
unauthorized-real-effect gates，以及独立 owner-native readback 和 evaluator。
