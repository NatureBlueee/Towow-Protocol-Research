# Wave 010 G6/G7：现实效力与安全重开的有界组合解

日期：2026-07-29  
状态：`LOCAL_SYNTHETIC DEVELOPMENT RUN / NOT X2 / NO FORMAL PROMOTION`

## 当前答案

在本轮四个本地合成 world 中，没有观察到需要新协议的 G6/G7 残余。

`transaction/outbox + durable workflow + end-to-end causal identity/idempotency +
five-owner readback + immutable history + dependency current-head query` 已同时做到：

- 五层零误晋升；
- 已发生 Effect 零漏报；
- timeout retry 零重复 Effect；
- 零 unsafe continuation；
- 零漏重开和误重开；
- 两个需要恢复的 branch 均在有界步骤内恢复。

同等合法 observation 下，成熟组合与 lawful strong center 的行为完全相同。强中心能负责
计算、编排和缓存，但不能因此成为外部 Effect、Adoption、Acceptance、Settlement 或隐藏
依赖的 owner。

更承重的负结果是：移除 dependency owner query 后，没有一个方法同时获得“安全且精确的
局部重开”。乐观局部重开在隐藏依赖已撤销的 world 中 unsafe；保守全局重开在依赖仍有效的
world 中多重开；人工制度同样只能用更慢、更贵的广域复核换取安全。这个断点首先要求创造
合法 observation，不是要求换一个更强模型或新事件总线。

以上只是同一研究者构造和运行的开发夹具，不是盲测、独立实现、现实 Effect、真人
Acceptance、生产恢复或 X2 结果。

本轮直接继承
[`TASK-TRUTH-CORRECTION-001.md`](./TASK-TRUTH-CORRECTION-001.md)、
[`WAVE-006-AUDIT-INVALIDATION.md`](./WAVE-006-AUDIT-INVALIDATION.md)、
[`WAVE-007-AUDIT-STATUS.md`](./WAVE-007-AUDIT-STATUS.md)、
[`WAVE-009-G4-G6-G7-DESIGN.md`](./WAVE-009-G4-G6-G7-DESIGN.md) 与
[`WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md`](./WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md)
的当前边界；不读取或修改 X1/M01 封包，也不反向创建 X2 ingress。

## 三个任务案例与 truth owners

### T2：买方域只读 AI 试点

证据级别：`ARCHIVAL_ANSWER_LEAKAGE_REPLAY`。

冻结任务仍保留原价值：代码进入买方域，只读、no-training，输出足以进入业务 backlog，
并由买方权威验收；不能把目标降成“服务方 workflow 有一份报告”。

本轮 mutation 是：

```text
服务方 Attempt = TRUE
workflow = COMPLETED
outbox = PUBLISHED
CloudEvent = DELIVERED
买方 sandbox 拒绝目标写入
```

五层 truth 分别属于：

| 层 | 唯一能作数的 owner | 本 world |
|---|---|---|
| Attempt | service execution ledger | `TRUE` |
| Effect | buyer sandbox audit | `FALSE` |
| Adoption | buyer service-operations backlog | `FALSE` |
| Acceptance | buyer business Principal | `REFUSED` |
| Settlement | buyer procurement ledger | `PENDING` |

原案例已经公开 countercondition、probe、v2 和判定结构，因此它只能做回归和反例，不能做
冷启动 coverage。

### T3：非标准 makerspace 资源请求

证据级别：`SYNTHETIC_TASK_SPEC_CANDIDATE`。

`R7_RESOURCE_REQUEST.md` 实际只是未来真实实验所需的资源清单，没有任务前态。故本轮新建
一个不冒充档案或现实事件的任务：

> 独立设计团队请求 makerspace 提供两小时 laser-cutter slot、技术员操作、用途限制、撤销
> 权与一个精确 prototype 的验收。resource owner 可拒绝、counter 或缩小用途；安全 owner、
> slot owner、执行者、受益者与付款方不预设重合。

本轮 mutation 是机器 job 已提交并完成，但 ACK 在 target commit 后超时。若 workflow 以新
causal identity 重试，会制造第二次机器 Effect。

| 层 | 唯一能作数的 owner | 本 world |
|---|---|---|
| Attempt | makerspace job controller | `TRUE` |
| Effect | makerspace machine-job ledger | `TRUE` |
| Adoption | requester prototype inventory | `TRUE` |
| Acceptance | requester design Principal | `TRUE` |
| Settlement | makerspace finance ledger | `PENDING` |

这里“制作完成”“请求方收货”“设计负责人接受”“费用已结”仍是四个事实。

### T6：成功路径重复后的隐藏依赖漂移

证据级别：`MUTATION_REPLAY_SPEC`。

从 T2 成功历史出发，升级执行容器。两个 world 的 workflow、outbox、CloudEvent、历史
readback、public dependency graph、权限表面状态和 method-visible bytes 完全相同。唯一差异
由 private oracle 保存：

- A：未表达的 `sidecar-account` dependency 仍 current；
- B：同一 dependency 已 revoked，并影响 executor 与 buyer sandbox。

五层历史 truth 仍各自来自 current executor、buyer target domain、buyer operational
owner、buyer Principal 和 buyer accounting authority；它们不能签发当前 reopen truth。
当前 affected closure 由 dependency/current-head owners 决定：

```text
A: CONTINUE, closure = {}
B: LOCAL_REOPEN, closure = {
  container-v2, sidecar-account, buyer-sandbox
}
```

它击穿“上次五层都成功，所以这次可以继续”。历史成功不包含未表达依赖的当前状态。

## 两个最强反例

### `workflow success = 现实完成`

T2 中 transaction、outbox、CloudEvent 和 workflow 全绿，而买方 Effect 为假。任何仅凭
这些 execution-domain 事件把五层写成成功的方法都在四个 world 中产生 20 次错误
authority promotion；其中 5 次还把实际 `FALSE/REFUSED/PENDING` 层直接折叠成成功。

hash 只证明 bytes；signature/receipt 只证明某个 signer 对这些 bytes 作了声明；event bus
只证明事件被传送。它们都不能把错误 signer 变成目标域或 Principal authority。

### `重复成功 = 可安全继续`

T6 paired worlds 在 dependency query 前不可区分。对相同 observation：

- `CONTINUE` 或仅重开 public node，会在 B 中漏掉两个承重依赖并 unsafe；
- `GLOBAL_REOPEN` 会在 A 中无谓重开四个节点；
- 更强中心、更多历史、更多同源 receipt 不能增加信息。

只有三种诚实行动：

1. 从 dependency owner 创建 current-head observation；
2. 无法观察时保持 `BOUNDED_UNKNOWN` 并 broad block/global reopen；
3. 由有权主体进行 dependency discovery/amendment。

## 单项能力到成熟组合

下表是局部合同分析，不是对 Temporal、CloudEvents、具体数据库或产品的实际运行。

| 方法 | 直接覆盖 | 仍然停止在哪里 |
|---|---|---|
| transaction + outbox | 本地业务写与事件发布原子化 | 外部 target 是否发生 Effect |
| CloudEvents | 可交换事件 envelope | 事件语义、owner 与现实后置状态 |
| event sourcing | 重建该 store 的历史 | 其他 authority domain 的当前事实 |
| durable workflow | 持久编排、retry、timer、恢复 | workflow green 不等于 Effect |
| Saga | 有界补偿流程 | 补偿不保证世界回到原状态 |
| CDC | 传播数据库变化 | 变化是否是 Adoption/Acceptance/Settlement |
| idempotency key | 在冻结 scope 内去重 | scope/causal id 不统一或 target 不幂等 |
| target readback | 一个目标域 postcondition | Adoption、Acceptance、Settlement 与依赖 |
| human acceptance | 精确对象的 Principal 接受 | Effect、Adoption、Settlement 和隐藏依赖 |

成熟组合只有把这些局部合同按 truth owner 连接后才闭环：

```text
attempt-time authority
→ causal identity/idempotency registry
→ transaction/outbox/workflow transport
→ target-domain Effect readback
→ operational Adoption readback
→ exact-object human Acceptance
→ Settlement readback
→ dependency/current-head check
→ continue | block | recover | affected reopen
```

每条箭头都是非蕴含 evidence gate，不能靠同名 `SUCCESS`、hash、receipt 数量或中心自报补齐。

## 最小 method-neutral simulation

文件：

- [`WAVE-010-G6-G7-FIXTURE.json`](./WAVE-010-G6-G7-FIXTURE.json)
- [`WAVE-010-G6-G7-SIMULATOR.py`](./WAVE-010-G6-G7-SIMULATOR.py)
- [`WAVE-010-G6-G7-RESULTS.json`](./WAVE-010-G6-G7-RESULTS.json)

方法只接收 public packet 与它实际调用的 owner readback；不接收 task label、semantic
case id、world id、expected action 或 private truth。Evaluator 才读取五层 truth、Effect
count 与 full dependency closure。T6 两个 world 的 no-query public transcript 逐字相同。

结果为 4 worlds × 9 方法臂。下表的 `gates` 是本夹具 7 个诊断门，不是 PROGRAM coverage：

| 方法 | gates | 误晋升 | 漏 Effect | 重复 Effect | unsafe continue | 漏/误重开节点 | 失败恢复 | 恢复步 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| event bus only | 0/7 | 20 | 3 | 1 | 1 | 3 / 0 | 2 | 1 |
| workflow + idempotency only | 1/7 | 20 | 3 | 0 | 1 | 3 / 0 | 2 | 2 |
| target Effect readback only | 4/7 | 0 | 0 | 0 | 1 | 3 / 0 | 1 | 1 |
| mature composition, local reopen | 4/7 | 0 | 0 | 0 | 1 | 2 / 1 | 1 | 5 |
| mature composition, conservative | 6/7 | 0 | 0 | 0 | 0 | 0 / 5 | 0 | 13 |
| lawful strong center | 6/7 | 0 | 0 | 0 | 0 | 0 / 5 | 0 | 13 |
| human institution | 6/7 | 0 | 0 | 0 | 0 | 0 / 5 | 0 | 19 |
| mature composition + owner dependency query | 7/7 | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 4 |
| strong center + owner dependency query | 7/7 | 0 | 0 | 0 | 0 | 0 / 0 | 0 | 4 |

人工制度还使用 20 次人工 owner readback；两个 query 组合各使用 20 次五层 readback 与 2 次
dependency query。该数字只用于本 fixture 的相对诊断，不代表真实成本。

六项自检通过：

- T6 hidden-dependency pair 的 public transcript 相同；
- T3 来源校正未被覆盖；
- 同观察下 strong center 与成熟保守组合因果等价；
- 两种 owner-query topology 在本 fixture 中同为 7/7；
- workflow-green 反例同时暴露误晋升、重复副作用和 unsafe reuse；
- opaque identifier 与 world order permutation 不改变聚合结果。

另外重新运行 Wave 007 A2 的 17 项回归均通过，包括 attempt-time idempotency、L3/L4 分离、
changed bytes partial history 和 Unknown/Refuse/Absent 保真。它只复核旧的本地合成修复，
不把 A2 晋升为独立或现实证据。

## 直接进入通爻 G6/G7 层的现成部分

可直接 `ADOPT/COMPOSE`：

- transaction/outbox、durable workflow、bounded Saga；
- CloudEvents/CDC/event sourcing 作为 transport/history，不作为 Effect truth；
- 在首次合法 attempt 原子绑定 causal identity/idempotency；
- target-domain、operational、Principal、settlement 分域 readback；
- immutable contract/version/history 与 dispute/retract/supersede；
- dependency/current-head query、telemetry 与 broad block/global reopen；
- 人工 amendment 作为 Unknown 或高后果 branch 的合法解。

需要 `WRAP`，但尚不是协议创新：

- 一个 conformance layer，把 exact operation、causal id、RelationVersion、owner、head、
  acceptance object version、dispute/retraction 与 dependency edge 绑定；
- connector migration 时保留这些绑定；
- dependency owner adapter 返回 `CURRENT/REVOKED/UNKNOWN/REFUSED`，不能是免费全知 oracle。

当前没有资格 `INVENT`。只有在新鲜任务、同等合法信息和预算下，成熟组合、lawful strong
center 与人工制度仍反复留下以下同一断点，才进入创新：

- owner 无法在不吞并主权的情况下表达/查询跨域依赖；
- 现有迁移格式必然丢失 Authority、Acceptance 或 dependency context；
- broad reopen 的净损失不可接受，而现有 dependency contracts 仍无法给出有界安全闭包；
- 异质 target connector 无法通过 conformance tests 保留五层非蕴含。

## 当前未解决与下一项高价值动作

本轮的 7/7 依赖一个完美、及时、如实的 dependency owner query。它可能只是把 private oracle
包装成 API。最高价值下一步不是增加事件 schema，而是建立一个新鲜 `T3-HW-A`：

1. 独立冻结 makerspace 资源、safety、slot、execution、beneficiary 与 finance truth；
2. dependency owner API 必须真实返回 `CURRENT/REVOKED/UNKNOWN/REFUSED/STALE`，并计披露、
   等待与人工成本；
3. parent broker 持久记录 causal identity、target write 和 retry，但不能代写五层 truth；
4. 在相同 lawful API 下比较 mature composition、strong center 与 human institution；
5. 先攻击 stale head、response loss、changed causal id、wrong-object Acceptance、隐藏 edge
   与 connector migration，再讨论 score。

这会同时修复 T3 当前没有任务前态的历史缺口，并检验“owner dependency query 已解决残余”
究竟是现成 adapter 的真实能力，还是新的答案泄漏。
