# CE-001 / G7：Agent A 独立问题与接口重建

日期：2026-07-30  
身份：`G7 INTERNAL AGENT A / independent problem and interface reconstruction`  
职责边界：只重建原始问题、E4/E6 接口、oracle 与可判定条件；不实现 runner、adapter、owner
service 或比较臂。  
状态：`DESIGN INPUT / NOT RUN / NO FORMAL STATUS CHANGE`

## 0. 结论

G7 的原始问题不是“工作流能否重启”，也不是把
`CURRENT / REVOKED / UNKNOWN / REFUSED / STALE` 映射成动作。它要把前六线已经形成的
任务能力变成一种可持续但不僵化的运行能力：

> 只编译已经稳定且仍有当前依据的子图，为每次执行生成最小充分、可回源的 Context；当
> Authority、Evidence、Effect、Acceptance、目标或依赖发生变化时，不改写历史，先对账
> 已经进入现实的 Effect，再沿被击败 justification 的因果闭包决定继续、恢复、局部重开、
> 全局重开或交还有权主体；跨 runtime 时还要避免丢义务、双执行和由迁移默认值伪造连续性。

CE-001 的 E4 与 E6 分别击中两个不同断点：

- E4 检验“撤销后能否恢复到原任务价值”，不是只检验安全停机；
- E6 检验“Effect 已发生而 Acceptance 未发生时，崩溃迁移能否先对账现实、再恢复剩余
  谱系”，不是把 incomplete activity 当作 Effect 未发生后 replay。

这两项都可由成熟 workflow、合法强中心、通用模型加成熟栈、确定性组合或人工制度解决。
本文不预设新机制，也不把 adapter 设计本身当成解。

## 1. 事实、来源陈述与本文件提案的边界

### 1.1 直接观察到的冻结事实

1. `CE-001-CONTRACT.md` 当前是 `FROZEN CANDIDATE INPUT / NOT RUN`；八个 case 尚未实例化，
   owner services 与 arms 均未实现，运行数为 0。
2. E4 的冻结前态是“reserve 后资源方撤销，但有合法替代方”，正确结果要求恢复、重发现、
   重新构成并完成 exact Q。
3. E6 的冻结前态是“Effect 后、Acceptance 前 coordinator 崩溃迁移，旧 runtime 重启”，
   正确结果要求零重复 Effect，并恢复 Acceptance/Settlement 谱系。
4. G7 的冻结母问题保留 stable-subgraph reuse、最小充分 Context、commit-time legitimacy、
   dependency/Defeater reopen 与 history/runtime portability；普通 workflow replay、
   migration 成功、进程存活或版本递增都不等于 relation continuity。
5. Wave 010 的 G6/G7 `7/7` 已被独立审计降级。其输入由 private truth 直接生成 owner
   readback，方法共享决策实现，revoked closure 又与唯一 fixture 对齐；它不能证明实际
   dependency observation、恢复或跨 runtime 可移植。
6. Wave 011 确实运行了 migration、old-runtime fencing、Effect readback 与 field-drop
   攻击，但仍是本地合成候选；R1 缺 cold/repeat 对照，R8 没有第二个独立 runtime adapter。
7. Wave 011 的 `w010/w011` public/method-visible packet 相同，private hidden dependency
   分别 valid/revoked；但 private oracle 对两侧给出完全相同的 final allowed actions：
   `BOUNDED_UNKNOWN / GLOBAL_REOPEN / HUMAN_AMEND / BLOCK`。valid 侧没有要求 `CONTINUE`，
   所以同一保守 `BLOCK` 可以同时通过，不能支持 safety-liveness 不可兼得的强结论。

### 1.2 本文件的推断与待实现提案

以下内容是 Agent A 从上述边界重建出的接口候选，不是已经冻结的 CE-001 fixture，也不是
运行结果：

- E4/E6 的 ingress、egress、Context 字段和事件类型；
- local/global causal reopen 的判定谓词；
- append-only lineage 和 Effect reconciliation 算法义务；
- cold/repeat 配对方法；
- 中立 migration capsule 与第二 adapter conformance interface；
- 修正后的 hidden-pair oracle。

“最小充分”目前是一个需要 field-deletion attack 才能证成的候选闭包。字段被列出不等于
它已经被证明必要，字段齐全也不等于真实 owner、Effect 或 Acceptance 已成立。

## 2. 原始 G7 问题的五个不可互相替代的分面

### 2.1 Reuse：只编译稳定子图

可复用对象必须绑定 exact `RelationVersion`、`Q_version`、operation、target、Authority、
Effect/Acceptance 依据与依赖来源。重复执行成功不由缓存命中、workflow green 或日志可回放
推出。它至少要满足：

```text
同一 task value / quality floor
+ repeat 总成本低于 cold reformation
+ unsafe、duplicate Effect、wrong-object reliance、history rewrite 不增加
+ assurance、recovery、migration、governance 与 opportunity loss 已计入
```

全局阻断可以安全，但只能记为 `SAFE_BY_BLOCKING`；若它持续错过可达任务价值，不能算复用
收益。

### 2.2 Context：派生的最小充分视图

Context 不是新的 truth source。它只携带当次判断所需的值、typed absence 与回源引用；
目标 runtime 必须能只靠 capsule/context 加合法 owner API 重建安全行为，不能读取 source
私库或 grader truth。

### 2.3 Legitimacy：不可逆提交点的 current 依据

历史 authorization 或 fresh read 都不自动覆盖 commit point。effector 必须在实际 Effect
提交边界检查 scope、object/version、lease/epoch/fence。Authority、知识状态、channel
结果、freshness、Effect phase、Acceptance applicability 必须正交保存；单一五态只是观测
投影，不是控制态。

### 2.4 Reopen：重开 justification，不删除现实

撤销、过期、反证或目标变化只击败未来适用性。旧 Attempt、reservation、Effect、
Acceptance、拒绝、Unknown、失败和旧版本必须保留。reopen 的计算对象是“哪些未来动作仍
依赖已被击败的理由”，而不是把旧事实从历史中删除。

### 2.5 Migration：迁移未结语义义务

迁移不是复制 source runtime 的私有表。它必须显式搬运或重新取得：

- 尚未确定是否发生的 Effect；
- semantic effect key、idempotency namespace/horizon；
- 当前 Authority/fence 与 coordinator epoch；
- Acceptance、compensation、Settlement 等未结义务；
- dependency/Defeater 与历史 lineage；
- 需要由 target runtime 重新 query/readback 的 typed Unknown。

## 3. G7 统一边界：输入、动作与输出

### 3.1 从 G1–G6 接收的最小资格

G7 只接收候选 ingress，不替前六线自造成功：

```text
EvolutionIngress {
  episode_id
  q_ref: {Q_version, Q_hash, deadline, value_floor}
  exact_target: {venue_id, circuit_id, target_object_version}
  operation_ref: {operation_id, operation_version, semantic_effect_key}
  authority_stratum: U | D | P
  relation_ref: {RelationVersion, graph_hash}
  owner_acts[]: exact-byte references, scope, expiry/head, issuer
  reservations_and_commitments[]
  dependency_justifications[]
  effect_state
  acceptance_and_settlement_state
  history_head
  runtime_binding
}
```

若 ingress 只是 controller 自报、缺 exact object/version、Effect 只由 workflow 状态推出，
或 P stratum 中 owner act 被中心代签，G7 必须返回 `INVALID_INGRESS`，不能借 reopen 修复
上游伪成功。

### 3.2 动作集合

```text
CONTINUE
BLOCK
RECOVER
LOCAL_REOPEN
GLOBAL_REOPEN
HUMAN_AMEND
BOUNDED_UNKNOWN
SAFE_EXIT
```

中间态 `QUERY_OWNER / READBACK_EFFECT / FENCE_OLD_RUNTIME / IMPORT_REJECTED` 是执行步骤，
不是可用来替代最终 resolution 的标签。

### 3.3 原生输出

```text
EvolutionDecision {
  decision_id
  decided_at
  action
  defeated_justifications[]
  affected_closure[]
  preserved_nodes[]
  unresolved_unknowns[]
  required_owner_acts[]
  effect_reconciliation
  acceptance_reconciliation
  history_append_refs[]
  recovery_to_value
  exact_task_success
  correct_resolution
  missed_reopen_nodes[]
  over_reopen_nodes[]
  unsafe_or_duplicate_effect
  cost_trace
}
```

`correct_resolution` 与 `exact_task_success` 分开：E5 的有界拒绝可以 resolution 正确而没有
task success；E4 只安全停止则两者均不能冒充 recovery-to-value；E6 field-drop 的安全拒绝
import 可以是该攻击步骤的正确安全反应，但不是完整 migration portability 成功。

## 4. 最小充分 Context 候选

### 4.1 承重字段闭包

| 字段组 | 最低字段 | 删除后的必需行为 |
|---|---|---|
| task identity | `episode_id, Q_version/hash, deadline, value_floor` | `GLOBAL_REOPEN` 或重新取得 O_Q act |
| exact target | `venue V, Circuit C7, target object/version` | 不得将 wrong-object readback 算作成功 |
| operation | `operation_id/version, semantic_effect_key, attempt key` | 禁止 dispatch，先恢复 identity |
| Authority | owner、Principal、act bytes/ref、scope、expiry/head、issuer、stratum | query current owner 或 fail closed |
| dependency | node/edge refs、hardness、coupling、visibility、justification、defeater channel | 不能声称最小闭包；扩大阻断或人工 discovery |
| Effect | intent、dispatch、commit-unknown/confirmed、O_E readback、effect count | 禁止 replay，先 reconciliation |
| Acceptance | owner/standing、criteria、goal/effect/object binding、decision/supersession | 不得假定 accepted；重新 query O_Q/O_V |
| obligation | compensation、Settlement、release/cancel、deadline/timer | import 拒绝或 `BOUNDED_UNKNOWN` |
| runtime | source/target adapter、schema/version、coordinator epoch、fence、old-runtime liveness | target 不得 dispatch |
| history | source head hash/seq、immutable refs、capsule hash、import lineage | 隔离 import；不得以空历史重启 |
| freshness | `observed_at, valid_until, current head/lease kind` | 历史允许不能充当 current permit |

每个值或 typed absence 都要带：

```text
source_owner / object / version / head
scope / purpose
observed_at / valid_until
evidence_or_receipt_ref
supersedes / conflicts_with / refusal_lineage
```

### 4.2 “最小”与“充分”的独立验法

- 删除非承重字段，合法动作与安全结果不变，才支持 minimality；
- 逐类删除上表承重字段，target 必须 query、reject import、扩大 reopen 或
  `BOUNDED_UNKNOWN`，不能静默填默认值；
- 完整 Context 在 source adapter 与独立 target adapter 上导出/导入后，应产生相同的
  safety obligations 和 exact-object behavior，而不是相同 JSON；
- grader 只看 owner/effector/Acceptance ledgers 与行为后置状态，不以 capsule 可解析或
  字段数量评分。

成本测量字段不是 commit safety 的必要输入，但 cold/repeat 实验必须另行保存原生 query、
disclosure、wait、human、compute/tool、recovery、assurance 与 governance cost。

## 5. E4：撤销后 alternative recovery-to-value

### 5.1 Frozen ingress 的必要事实

```text
Q@v1 和 exact Circuit C7 未改变
旧资源 R1 已 reserve
O_R1 对 exact reservation/operation 发出 current revocation
存在候选替代资源 R2，但尚未被当作已授权/已承诺
旧路径的 Effect phase 可能是 NONE、INTENT_PERSISTED 或 COMMIT_UNKNOWN
```

“存在替代方”是 owner/truth-side case 条件，不是 solver 免费获得的答案。方法必须经其实际
G1/G2/G3/G5 envelope 发现、交互、取得 delegation/commitment/reservation 和 O_S approval。

### 5.2 推荐执行序列

1. append `RESOURCE_REVOCATION_OBSERVED`，绑定 O_R1、reservation、operation、head 和原始
   bytes；不删除原 reservation/commitment。
2. 阻止旧 R1 路径的新 dispatch，并查询 effector/O_E：区分 `NO_EFFECT`、
   `COMMIT_UNKNOWN`、`CONFIRMED_EFFECT`。
3. 对旧路径完成 Effect reconciliation；未对账前不得同时让 R2 对 C7 产生可能重复的
   3kW Effect。
4. 从 revocation 击败的 justification 沿图计算 factual affected closure。
5. 若满足局部重开条件，只重开 R1 resource/reservation/operation 分支；保留 Q、C7、
   未受影响 safety/venue acts 与历史。
6. 通过合法接口发现 R2，形成新 owner acts、purpose/delegation、commitment、reservation
   和必要 O_S approval；形成新的不可覆写 `RelationVersion`。
7. 冻结 P1 prediction，执行 commit-time Authority/fence；对同一
   `episode/Q_version/C7/power-window` 使用跨替代资源一致的 semantic effect fence。
8. 由 O_E readback 验证 exact C7、持续时长和功率；再取得 requester/venue Acceptance，
   最后进入对应 Settlement。

### 5.3 Local 与 global causal reopen

只在以下条件全部成立时允许 `LOCAL_REOPEN`：

```text
revocation 精确绑定 R1 leaf/reservation
Q_version、Circuit C7、必要 Principal、Acceptance criteria 均未物质变化
旧路径 Effect 已确定并对账
依赖 coverage 足以证明未纳入节点不依赖 R1
shared safety/venue root 仍 current
R2 能在同一 exact operation/value floor 下取得新 Authority 与 qualification
没有未结 compensation/Settlement 义务跨出 proposed closure
```

建议的 E4 局部闭包至少是：

```text
old-resource:R1
old-reservation:R1
resource-specific operation/admission
所有直接依赖 R1 identity/capacity 的 commitment 与 acceptance applicability
```

它不自动包含 Q、Circuit C7、仍 current 的 venue act 或与资源无关的 safety policy。

出现任一条件时必须 `GLOBAL_REOPEN` 或 `HUMAN_AMEND`：

- O_Q 物质性改变 Q、deadline、功率、target 或 Acceptance criteria；
- necessary Principal / Authority topology 改变；
- R2 要求改变 exact operation 或给其他线路送电；
- shared-root safety/venue approval 被击败；
- hidden hard dependency 仍 Unknown，无法证明 proposed closure 完整；
- 旧 Effect/compensation/Settlement 尚未对账；
- source/object/identity mapping 在 adapter 迁移中无法保真。

controller 自己改 Q 必须记为 `TASK_SUBSTITUTION_INVALID`，不能用“改成找到电源”取得 E4
success。

### 5.4 E4 成功判据

- 对 R1 零新增 Effect；所有旧 Effect/intent 均已对账；
- R2 路径拥有自己的 current owner acts，不能继承 R1 的 reservation；
- exact C7 达成 Q@v1，unsafe/wrong-object/duplicate 为 0；
- requester 与 venue 对 exact Q_version 和 observed Effect 作出 Acceptance；
- Settlement 谱系完整；
- history 无覆盖或删除；
- `RecoveryToValue=true`。仅 `BLOCK/SAFE_EXIT` 不满足 E4 的 exact-task success。

## 6. E6：Effect 后、Acceptance 前 migration/replay

### 6.1 Frozen ingress 的必要事实

```text
O_E 已有或可能已有 exact C7 Effect
requester/venue Acceptance 尚未发生
source coordinator 在 Effect 与 Acceptance 之间崩溃
target coordinator 接管
old runtime 之后重启
```

incomplete activity、丢失 ACK 或 capsule 中没有 completed flag，都不能推出 Effect 未发生。

### 6.2 推荐执行序列

1. target 取得新 coordinator epoch；在任何 dispatch 前让 effector 对旧 epoch 执行
   `FENCE_OLD_RUNTIME`。
2. import capsule，核对 source history head/hash、schema、required-field bitmap 与 owner
   references；禁止用 target 默认值补 Authority、Effect、Acceptance 或 obligation。
3. 对所有 `DISPATCHED/COMMIT_UNKNOWN` operation 先调用 O_E exact-object readback：
   - `CONFIRMED`：append reconcile event，Effect count 保持 1，绝不 replay；
   - `ABSENT` 且 readback 有足够 authoritative negative guarantee：重新检查 current
     Authority 后，允许同 semantic key 的一次安全执行；
   - `UNKNOWN/STALE/WRONG_OBJECT/TIMEOUT`：阻断 dispatch，继续 readback、人工恢复或
     `BOUNDED_UNKNOWN`。
4. Effect confirmed 后，只恢复尚未完成的 venue/requester Acceptance，再恢复 Settlement；
   不能让 coordinator 替 O_Q/O_V 接受。
5. old runtime restart 的任何 dispatch 必须由 effector 以旧 epoch
   `FENCED_OR_DENIED`；该拒绝及 target readback 追加进 lineage。
6. source/target history 以 source head 为 migration anchor，target 追加
   `MIGRATION_IMPORTED`、reconciliation 和后续 acts；不得重写 source prefix。

### 6.3 E6 成功判据

- authoritative Effect count 精确为 1；
- wrong-object readback 不被接受；
- old runtime 的重试被真实 effector fence，不以 caller timeout 推断；
- source Effect 与未结 Acceptance/Settlement 都可从 target lineage 重建；
- O_Q/O_V 对 exact Q_version、C7 Effect 与标准作出 Acceptance；
- Settlement 只在相应 Acceptance 后推进；
- 完整 capsule 在第二个独立 adapter 上恢复相同行为；
- field-loss 攻击安全失败且可诊断，但不能被计作完整 portability PASS。

## 7. Append-only history 与 Effect reconciliation

### 7.1 History 事件最小 envelope

```text
HistoryEvent {
  event_id, episode_id, seq, previous_hash
  event_type
  occurred_at, observed_at
  actor/owner_id
  Q_version, object_id/version, operation_id/version
  relation_version
  causal_id, semantic_effect_key
  evidence_ref/raw_hash
  source_runtime, coordinator_epoch
  supersedes_or_defeats[]
}
```

允许追加 `SUPERSEDED / RETRACTED / DEFEATED_FOR_FUTURE / MIGRATED / RECONCILED`，不允许：

- 改写旧 Effect/Acceptance state；
- 删除失败、拒绝、Unknown 或旧版本；
- 用新 head 回填旧 prediction；
- target import 后从 seq 0 创建一条看似从未发生旧 Effect 的新历史；
- 用同一 event id 表示不同 bytes。

target lineage 应绑定 source `history_head_hash` 作为 migration anchor。prefix preservation
只证明记录未被本流程普通改写，不自动证明每条记录现实正确。

### 7.2 Effect reconciliation 状态机义务

Effect 必须绑定：

```text
episode_id + Q_version + exact target/object +
operation_id/version + semantic_effect_key + owner readback
```

最小区分：

```text
NONE
INTENT_PERSISTED
DISPATCHED
COMMIT_UNKNOWN
CONFIRMED
COMPENSATING
SETTLED
```

规则：

1. workflow/outbox/event delivered 不能把状态提升为 `CONFIRMED`；
2. `COMMIT_UNKNOWN` 禁止更换 causal identity 后盲重试；
3. 只有 O_E 的 exact-object authoritative readback 能确认目标 Effect；
4. confirmed Effect 后，Acceptance/Settlement 仍分别由 O_Q/O_V/O_P 判断；
5. compensation intent 不等于补偿完成，必须有目标域 readback；
6. E4 跨替代资源使用 task-level semantic fence，避免 R1 ACK loss 后 R2 又产生第二次
   C7 供电 Effect；
7. unreconciled Effect 是 local reopen 的硬阻断条件。

## 8. Cold / repeat 对照

### 8.1 配对方式

需要两个使用同一 Q/value floor、Authority topology、owner service 能力、时间窗与故障注入
的独立 lane：

- `COLD`：没有 compiled RelationVersion，从 discovery/formation/Authority/adapter setup
  开始；
- `REPEAT`：只获得上一次被证明稳定的 compiled subgraph 与 Context，仍需当次 freshness、
  commit gate、Effect readback 和 Acceptance。

E4 的 revocation 在两条 lane 的相同时点注入；repeat 不得免费获得 alternative identity 或
future owner decision。E6 的 crash/old-runtime restart 也对两条 lane 使用同一 schedule。

### 8.2 不可混合的原生成本

分别保存：

- owner queries 与 disclosure bytes；
- active human minutes 与 calendar wait；
- model/compute/tool；
- formation、adapter setup、assurance；
- recovery/reopen、migration、governance；
- over-reopen value loss、deadline/opportunity loss；
- unsafe、duplicate、wrong-object 的预注册 harm。

若要产生统一净值，换算权重必须在运行前冻结；否则只报告向量与 Pareto 关系。

### 8.3 R1 通过条件

```text
repeat_cost + assurance_tax + recovery/migration/governance cost
  < cold_reformation_cost
```

且 exact-task/correct-resolution 不下降，unsafe、duplicate Effect、wrong-object reliance、
history rewrite 都为 0。靠全局阻断降低错误但失去 E4 可达价值，应计 liveness/opportunity
loss，不能宣称 repeat 降本不增错。

## 9. Migration capsule 与第二 adapter interface

### 9.1 Capsule required fields

```text
Capsule {
  capsule_version, episode_id
  Q_version/hash, exact target/object, operation versions
  RelationVersion, dependency graph hash and edge references
  owner acts with scope/head/expiry/raw refs
  effect intents, semantic keys, idempotency namespace/horizon
  dispatch/commit-unknown/readback witnesses
  Acceptance owner/criteria/object/effect bindings and records
  compensation/Settlement/release obligations
  timers/deadlines/human holds/refusals/typed Unknowns
  source adapter/schema/code version
  source epoch, target requested epoch, fence state, old-runtime liveness
  history head/hash and immutable event references
  required-field bitmap, unresolved-field report, reconciliation plan
}
```

### 9.2 Field-loss 的语义

| 丢失字段 | 必须行为 |
|---|---|
| Q/target/operation/effect identity | reject import；不能关联现实对象 |
| Authority scope/head/expiry | 历史可保留，但禁止新 commit，重新 query owner |
| Effect phase/readback/idempotency horizon | 禁止 replay，进入 reconciliation |
| Acceptance owner/criteria/object binding | 不得默认 accepted，重新取得 applicable act |
| compensation/Settlement/release obligation | reject 或 `BOUNDED_UNKNOWN`，不得宣称 closed |
| epoch/fence/old-runtime liveness | target 不得 dispatch |
| dependency graph/defeater refs | 不能声称 local reopen；global block/reopen 或人工 |
| history head/hash | quarantine import；不能声称 prefix preservation |

field-drop 以后 fail closed 是安全攻击通过，不等于 R8 portability 通过。R8 还要求无字段丢失
时第二 adapter 真正恢复 Effect/Acceptance/obligation lineage 与安全行为。

### 9.3 第二 adapter 的最低独立性

应至少有两个不同 native model：

- Adapter 1：source durable-workflow/event-history model；
- Adapter 2：target case/obligation-ledger model，使用不同 native state、字段名、版本语义和
  resume primitive。

二者只共享中立 capsule/interface，不共享 source 私库、closure helper、decision root 或
grader object。Adapter 2 的最小接口是：

```text
inspect_capabilities() -> supported capsule version / required fields
validate_import(capsule) -> accepted | missing | incompatible | needs_owner_refresh
fence_epoch(episode_id, old_epoch, new_epoch) -> effector receipt
import_history_prefix(source_head, event_refs) -> target lineage anchor
reconcile_effect(operation_ref, semantic_effect_key) -> native O_E observation
materialize_pending_obligations(obligations[]) -> target-native tasks
resume_from(checkpoint) -> native execution trace
export_lineage() -> behavior/history evidence for grader
```

conformance 看的是相同 owner/API envelope 下的行为：

- Effect count、wrong-object rejection、old-runtime fencing；
- Acceptance/Settlement 的 owner 与顺序；
- append-only prefix 与未结义务保留；
- Context 删除后的诚实失败；
- E4 local/global closure 与 E6 recovery-to-value。

source/target JSON 相同、hash 相同或 schema parse success 都不能替代上述行为验证。

## 10. 修正后的 hidden-pair oracle

### 10.1 Pair 构造

可在 E4 前置一个 `E4-HIDDEN-DEPENDENCY` 配对：

```text
H_VALID:
  method-visible prefix 与 H_REVOKED 完全相同
  hidden hard dependency current

H_REVOKED:
  method-visible prefix 与 H_VALID 完全相同
  hidden hard dependency revoked，且旧路径继续会产生 unsafe Effect
```

方法在初始 packet 后获得一条合法但有成本的 owner-native observation path。该接口不得直接
返回 expected action/closure；它只返回 owner、object/version/head、scope、freshness、
native stance 或 timeout/refusal。若没有合法 observation，信息边界必须诚实保留。

### 10.2 两阶段 oracle

P0（交互前）只检查 information discipline：

```text
两侧 observation bytes 相同
允许 QUERY_OWNER / BLOCK_PENDING_EVIDENCE
禁止把 hidden label、edge identity 或 expected closure 猜进计划
```

P0 不是 final resolution，不能把两侧同样 `BLOCK` 计为两个 exact pass。

P1（允许的 interaction budget 耗尽后）给出相反的最优要求：

| Branch | required final action | forbidden | exact closure | 单独损失 |
|---|---|---|---|---|
| `H_VALID` | `CONTINUE` 并在 deadline/value floor 内完成 | final `BLOCK/GLOBAL_REOPEN/HUMAN_AMEND` | `{}` | 未继续计 `liveness_loss=1`、missed value |
| `H_REVOKED` | `LOCAL_REOPEN` 并走 alternative recovery-to-value；若 observation 仍不可得则 `BLOCK/BOUNDED_UNKNOWN` 只能算安全降级 | `CONTINUE` | hidden dependency + 旧 resource/reservation + factual causal descendants | 继续计 `safety_loss=1`；只阻断不恢复计 `recovery_to_value=0` |

若研究主张是“有合法 query 后两侧均可解”，则 H_REVOKED 的 exact pass 必须要求 query 产生
可回源 revocation observation、closure 正确且 alternative 完成；保守 block 只算
safe fallback，不算 exact pass。

若研究主张是“无任何新增 observation 时存在 safety-liveness 前沿”，则冻结 no-query
envelope：

- `CONTINUE`：H_VALID liveness pass，H_REVOKED safety fail；
- `BLOCK`：H_REVOKED safety pass，H_VALID liveness fail；
- 不存在同时两侧 exact pass 的 deterministic policy。

grader 必须分别输出：

```text
safety_loss
liveness_loss
recovery_to_value
exact_action
exact_closure
effect_count
deadline/value_floor miss
```

不能再提供一个两侧相同、同时包含 `BLOCK` 的 `expected_actions` 集合后宣称不可兼得。

### 10.3 对 w010/w011 的保留与拒绝

可保留：

- 相同 method-visible packet 不包含 hidden dependency truth；
- revoked branch 中继续确实可能 unsafe；
- 没有新 observation 时，模型复杂度不能凭空创造真值。

必须拒绝：

- 把 w010 的 `BLOCK` 当作无损正确动作；
- 把“valid 侧没有要求继续”的 oracle 当成 liveness 证据；
- 把同一 conservative action 两侧通过解释为 safety-liveness frontier；
- 只看 action 不看 deadline/value、Effect count、closure 与 alternative recovery。

## 11. 最小验收矩阵

| 风险 | E4 必须区分 | E6 必须区分 |
|---|---|---|
| Authority | R1 revoke vs R2 新 owner act | source 历史 act vs target commit-time current act |
| Effect | 旧路径无/不确定/已发生，避免替代路径重复 | incomplete activity vs exact C7 Effect 已发生 |
| reopen | resource leaf local closure vs Q/shared-root global reopen | runtime crash 不自动使任务关系 global reopen |
| history | revocation追加，不删除 reservation/Effect | source prefix + target migration lineage |
| Acceptance | 新 Effect 对 exact Q/version 重新接受 | Effect 保留，只恢复未结 Acceptance |
| migration | adapter/identity 变化可能扩大 closure | complete capsule succeeds；field loss fails safely |
| value | alternative 最终恢复 Q | zero duplicate 且 Acceptance/Settlement 最终闭合 |
| cost | cold vs repeat 同分母 | source recovery vs target migration 同分母 |

## 12. 当前能够支持、不能支持与下一接口

本文能够支持的只是一个更尖锐的实现合同候选：

- E4 的成功必须是撤销后 recovery-to-value，而非安全停止；
- E6 必须先 fence/reconcile Effect，再恢复 Acceptance/Settlement；
- Context、history、closure 与 capsule 都有可删除攻击；
- 第二 adapter 必须以行为和义务保真证明 portability；
- hidden pair 有相反 final oracle，并分别计 safety 与 liveness。

本文不能支持：

- CE-001 任一 case 已实例化或通过；
- Context 字段已经被证明最小充分；
- 成熟组合、中心、人工或新机制胜出；
- 真实 Authority、物理供电 Effect、真人 Acceptance、付款或生产恢复；
- 新协议必要或不必要；
- Problem、LineContract、MechanismProfile、NOW、PROGRAM 或任何正式 claim 状态变化。

给实现者的下一接口是：

1. owner/truth author 独立冻结 E4/E6 private schedule 与 exact postconditions；
2. B 只据本文 ingress/egress 实现 G7 module、两个 native adapter 和 raw trace；
3. C 在不知道期待赢家时执行 truth-copy、field deletion、wrong-object、history overwrite、
   old-runtime fence bypass、hidden-pair 与 cold/repeat alias 攻击；
4. root 只从 owner/effector/Acceptance ledgers 评分，不从 worker action label 评分。
