# Wave 024：跨 Authority / Target 域的原子性模型

日期：2026-08-01  
状态：`INDEPENDENT THEORY REVIEW / IMPLEMENTATION NOT READ / RUN NOT OBSERVED`

## 结论先行

Wave 024 当前最值得保留的机制不是新的跨域事务协议，而是一个更窄、成熟且可实现的组合：

> **Target-consumed durable monotonic fence + Target-local atomic gate/effect transaction。**

它足够解决本轮已经在红队前置条件中冻结的问题：当 exact revocation 已经被 exact Target
持久消费并 ACK 后，旧 epoch 请求不能越过该 Target 的 mutation linearization point；当该
Target 尚未消费任何 superseding fence 时，同一请求可以在该 Target 的原子事务中提交一次，
随后通过 authoritative status/readback 从 ACK 丢失中恢复。

但 `QUESTION.md` 中的 `commit-time current Authority` 和
`CL-024-AUTHORITY-CURRENTNESS` 仍有过强歧义。若它们表示：

> owner/Authority 域一旦在线性化点记录 revoke，此后所有独立 Target 的任何 commit 都必须
> 立即知道并拒绝，即使 Authority—Target 之间发生网络分区，

那么单独的 Target fence 不提供该保证；在异步跨域系统里，同时要求这种安全性、分区期间的
Target 可用性、以及无需共同事务或有效期假设，是不可实现的。

因此本轮应把主 claim 精确降级为：

> **在 exact Target 的本地 mutation linearization point，提交只相对于该 Target 已原生、
> 持久消费的 Authority view 判定；matching superseding fence 若先于该点安装，则旧 epoch
> 必须拒绝，否则请求可以按原有 grant 与 scope 判定。**

这不是降低本轮价值，而是把一个跨域、未定义共同时间的叙述改成可实现、可攻击、可复现的
保证。若成熟的 Target fence 完整通过本轮，它就是正向 Towow 方案结果；不需要为保持原创而
增加 2PC、共识或新协议。

## 审查边界

本文只读取：

- 根 `AGENTS.md`；
- `research/NOW.md`；
- Wave 024 `QUESTION.md`；
- Wave 024 `RED-TEAM-PREFLIGHT.md`。

本文没有读取 Wave 024 实现、测试、fixture、Pro 返回或 `TRANSFER`。以下判断是独立语义与
分布式系统模型，不是对当前代码通过与否的判断，也不是实验结果。

## 先区分四个过去被“current”混在一起的事实

对 delegation `D@e`、Authority 域 `A` 和 Target `T`，至少存在四个不同事件：

1. `REVOKE_RECORDED_A(D,e+1)`：Authority 域已在自己的线性化日志中记录撤销；
2. `FENCE_INSTALLED_T(D,e+1)`：exact Target 已持久消费匹配 scope 的新 fence；
3. `REVOKE_EFFECTIVE_AT_T(D,e+1)`：从 `T` 的 mutation reference monitor 看，旧 epoch
   已不能产生新的 Effect；
4. `GLOBALLY_EFFECTIVE(D,e+1)`：所有可能接受 `D@e` 的 mutation boundary 都已失效。

`1` 不自动蕴含 `2`；`2` 在 Target 的所有 mutation endpoint 都由同一 reference monitor
覆盖时可以蕴含 `3`；单个 Target 的 `3` 不蕴含 `4`。

Wave 024 的本地 twin 有能力检验 `2 → 3`，没有能力从单个本地 Target 推出 `1 → 4`。

因此 evaluator 不应只有 `CURRENT / REVOKED` 两值。至少应区分：

| 状态 | 可观察事实 | 能否对本轮 currentness claim 评分 |
|---|---|---|
| `NO_SUPERSEDING_FENCE_AT_T_LP` | execute LP 时 `T` 的 durable fence 尚未超过 `e` | 可以，表示 Target-view eligible，不表示 A-global current |
| `SUPERSEDING_FENCE_BEFORE_T_LP` | matching fence install LP 先于 execute LP | 可以，旧 epoch 必须拒绝 |
| `A_REVOKED_BUT_T_NOT_ACKED` | A 已记录 revoke，但 T 未持久 ACK；两域没有完整传播顺序 | `UNORDERED / NOT SCORED` |
| `SCOPE_OR_HEAD_INCOMPARABLE` | fence 不绑定同一 delegation/scope/head，或有 successor grant | `INVALID / NOT SCORED` |

第三种状态不是实现错误，而是跨域事实不足。把它按预期标签补写成 R，才是研究错误。

## 需要线性化的对象究竟是什么

### 过强版本：A-global current at T commit

设：

- `LP_A(revoke)` 是 Authority 日志记录撤销的线性化点；
- `LP_T(effect)` 是 Target 产生不可重复语义 Effect 的线性化点。

过强安全性质是：

```text
LP_A(revoke(D,e+1)) < LP_T(effect(req,D@e))
    => effect(req,D@e) must not commit
```

这个性质跨越两个独立线性化对象。若 A 和 T 不共享事务、共识日志、受约束的 permit/lease
语义或同步假设，就没有一个本地原子步骤可以同时读取 `A` 的“此刻”状态并提交 `T` 的 Effect。

一次 online check 也没有消除该问题：check response 与 Target commit 之间仍有窗口，revoke
可以在窗口内发生。

### 本轮可实现版本：Target-consumed currentness

令 `F_T[D,scope]` 是 exact Target 已持久消费的最大 matching revocation fence。可实现性质为：

```text
at LP_T(execute(req,D@e)):
    if e < F_T[D,scope]: reject stale authority and commit zero new Effect
    else: evaluate grant signature, exact scope, expiry, head and operation constraints
```

关键不是在日志里先后写两条记录，而是：

> `F_T` 的读取、旧 epoch 的拒绝或通过、semantic occurrence 的唯一性判断和 Effect commit，
> 必须属于同一个 Target-local serializable transaction / state-machine transition。

这样，fence install 和 effect execute 在同一 Target 上一定有唯一顺序：

```text
LP_T(fence-install) < LP_T(execute)  => stale request rejected
LP_T(execute) < LP_T(fence-install)  => exact Effect may commit once
```

并发本身不再需要 wall clock 裁决；两种顺序都是规格允许的明确结果。

## 最小状态机

### Authority 域

对 exact delegation/scope：

```text
A.ACTIVE(D, epoch=e, head=h_e)
    -- revoke at LP_A -->
A.REVOKED(D, fence=e+1, head=h_r)
    -- authenticated propagation -->
A.WAITING_FOR_TARGET_ACK(D,T,e+1)
    -- consumes Target-native durable ACK -->
A.REVOCATION_EFFECTIVE_AT_TARGET(D,T,e+1)
```

最后一个状态只表示对 exact `T` 生效，不是 global revocation。若产品要向调用者返回
“撤销已全局完成”，它必须另行定义 Target closure、ACK 策略和离线 Target 处理；不能把第一步
的 Authority 日志成功冒充第四步。

### Target 域

Target 的权威状态至少为：

```text
TState = <
  Fence[delegation, scope],
  Decision[request_id],
  Occurrence[semantic_key],
  HistoryHead
>
```

`INSTALL_FENCE` 是一个 Target-native 原子 transition：

```text
INSTALL_FENCE(signed_authority_head h_r, fence f_new):
  verify pre-anchored Authority root
  verify exact D / Principal / delegate / Q / object / Target /
         operation / scope / expiry / predecessor head
  require f_new >= Fence[D,scope]
  atomically:
    Fence[D,scope] := f_new
    append FENCE_INSTALLED receipt and new HistoryHead
  only after durability: emit ACK(D,T,f_new,h_r,HistoryHead)
```

`EXECUTE` 也是同一 Target state machine 上的一个原子 transition：

```text
EXECUTE(req, D@e, semantic_key k):
  atomically:
    if Decision[req.id] exists:
      return the existing decision; create no new Effect

    if Occurrence[k] already committed for this exact operation:
      return authoritative existing outcome / duplicate conflict;
      create no new Effect

    verify grant signature, exact binding, scope, expiry and eligible head

    if e < Fence[D,scope] or matching installed head revokes D@e:
      Decision[req.id] := REJECTED_STALE_AUTHORITY
      append rejection receipt
      create zero Effect
    else:
      mutate exact Target state once
      Occurrence[k] := COMMITTED(receipt_hash)
      Decision[req.id] := COMMITTED(receipt_hash)
      append commit receipt
```

`STATUS/READBACK` 是对同一 authoritative `Decision`、`Occurrence` 和 history coverage 的
线性化读。ACK 丢失后，它返回已经存在的 commit 或 rejection；它不重新执行 Effect。

这里有一个容易忽略但重要的顺序：已经提交的同一 request 在后来发生 revoke 后，status 仍应
返回历史 commit，而不是把过去真实发生的 Effect 改写成 revoked。fence 只阻止新的 mutation，
不重写历史。

## R 世界必须具备的 happens-before 链

合法 R 不能靠 wall clock 或 controller 的数组顺序构造。最小可复算因果链为：

```text
LP_A(REVOKE_RECORDED)
  -> Authority sends authenticated matching fence
  -> Target receives matching fence
  -> LP_T(FENCE_INSTALLED durable)
  -> Target emits ACK bound to the durable history head
  -> root/controller receives and verifies ACK
  -> executor execute invocation is enabled
  -> Target records exact ingress
  -> LP_T(EXECUTE / REJECTED_STALE_AUTHORITY)
```

`->` 在这里是消息、进程启动或同一 state machine 的 happens-before，不是比较两个不可信
wall clock 数字。只有完整链闭合，R 才能说 `fence-install < execute`。

若 execute ingress 与 fence propagation 并发，最终只看 Target 原生的两个 LP：

- execute LP 先发生：允许一次 Effect 是 target-consumed 语义下的合法结果；
- fence LP 先发生：旧 epoch 必须拒绝；
- 两个 receipt 无法闭合到同一 Target history：样本 `INVALID/UNKNOWN`。

### S 世界能证明什么

S 最多能从 Target state/history 证明：

```text
no matching superseding fence was installed before LP_T(EXECUTE)
```

它不能仅凭“Target 没看到 revoke”证明：

```text
Authority A had not already recorded a revoke elsewhere
```

若 S 必须支持后一个命题，就需要 Authority 与 Target 之间更强的 permit、lease 或事务关系，
而不是再增加一份由 controller 写的 `current=true` receipt。

## 两个最小 TOCTOU 反例

### 反例一：远端 online check 仍有窗口

```text
t0  Target/executor asks A: is D@e current?
t1  A returns CURRENT
t2  A linearizes revoke(D,e+1)
t3  revoke propagation is delayed
t4  Target commits Effect using cached CURRENT
```

若规格声称 A-global current at `t4`，则违规；若规格只声称 Target-consumed currentness，则在
fence 尚未安装时可能合法。多做一次 check 不能消灭 `t1..t4`，只能缩短窗口。

### 反例二：Target 内部 check 与 commit 分离

```text
t0  Target transaction/read #1 observes Fence=e and returns eligible
t1  Target installs Fence=e+1 durably
t2  Target transaction/write #2 commits Effect based on the cached result
```

这甚至违反较弱的 Target-consumed 语义。解决它不需要分布式事务，只需要让 fence check、
idempotency/occurrence check 和 Effect mutation属于同一个 Target-local serializable transition。

## 四种成熟解的真实保证与代价

| 成熟方案 | 真正的序列化点 | 能提供的精确保证 | 分区与并发 revoke | 对 Wave 024 的判断 |
|---|---|---|---|---|
| **Target-consumed monotonic fence** | Target 本地 fence/effect state machine | 已安装 matching fence 之后，旧 epoch 不能产生新的 Target Effect | fence 尚未到达时可继续接受旧 epoch；安装与 execute 并发时由 Target 本地顺序裁决 | **本轮首选，已经足够**；前提是 R 等待 durable ACK，所有 mutation endpoint 都受同一 gate 管辖 |
| **Online Authority reference monitor** | Authority 的 check/permit 日志；若只是 query，Target commit 仍是第二个点 | 普通 query 只证明 check 时 current；线性化 permit 可证明 Authority 在 permit LP 授权 exact operation | partition 时 fail-closed 会失去 Target availability；fail-open 会接受未看到的 revoke；query 后仍有 TOCTOU | 单纯 online check 不足；除非把返回改为有明确消耗语义的 permit/reservation |
| **Lease / bounded capability** | Authority 签发 lease 的 LP，加受约束时钟和 expiry | 在 lease 语义内可离线执行；revoke 最迟在 lease 到期后对未同步 Target 生效 | 以最大 lease 时长换取撤销暴露窗口；依赖时钟偏差界，短 lease 增加不可用与刷新成本 | 可做现实工程替代，但检验的是 bounded-staleness，不是即时 current-at-commit |
| **Reservation / irrevocable per-operation permit** | Authority 对 exact operation 保留一次额度/权利的 LP；Target 对 permit 的一次消费 LP | revoke 与新 reservation 串行；已发 permit 是否继续有效由规格明确。可避免“撤销追杀在途提交”的歧义 | partition后可消费已发 permit；revoke阻止新 permit，但无法瞬时取消已发 permit，除非再加 Target fence | 若业务允许 in-flight permit surviving revoke，这是比 2PC 更简单的成熟完整解；claim 应写 current-at-reservation |
| **2PC / shared serializable transaction / consensus state machine** | 共同事务的 durable commit decision 或同一共识日志位置 | revoke 与 Effect commit 作为冲突操作获得一个共同全序；可以真正定义跨域 commit-time currentness | 朴素 2PC 在 coordinator crash/partition 下阻塞；共识只给多数侧进展，孤立 Target 仍不可用；不可逆外部 Effect 必须可 prepare/stage | 只有坚持 A-global strict semantics 时才值得；对当前本地 twin 过重，不应默认引入 |

### 方案之间不是“强弱排名”，而是撤销语义不同

- Target fence 把 revocation completion 定义到具体 Target 的 durable consume；
- lease 接受一个有界陈旧窗口；
- reservation 把某次 operation 的授权时点前移，并保护在途许可；
- 2PC/共识让 revoke 与 effect 进入同一序列，但用可用性和集成成本交换；
- human approval 或 workflow lock 也可能实现 reservation 语义，只要 exact permit、scope、
  expiry、一次消费和撤销边界都可复核。

它们都可能是正向 Towow 方案。选择依据是原始任务需要哪种撤销完成语义，而不是哪种机制看起来
更“协议化”。

## 网络分区下的不可同时满足条件

假设：

1. A 与 T 是独立故障域；
2. 网络可以无限期延迟 A→T 的 revoke；
3. T 在分区期间仍必须处理请求；
4. owner 在 A 记录 revoke 后要求任何 T 都绝不再提交旧 epoch；
5. 没有预先冻结的 lease/permit 例外，也没有共同事务或同步时钟界。

考虑两个对 T 完全不可区分的世界：

```text
W0: A 没有 revoke，网络安静；旧请求到达 T
W1: A 已 revoke，但 revoke 消息被分区延迟；同一旧请求到达 T
```

在决策时 T 的本地状态与输入逐字节相同。若 T 为了 W0 的可用性提交，它也会在 W1 提交，
违反要求 4；若为了 W1 的安全性拒绝/阻塞，它也会在 W0 拒绝/阻塞，违反要求 3。没有算法能
仅凭相同本地信息作出两个不同决定。

因此至少要放弃或限定一个要求：

- **安全优先**：分区期间 fail closed，等待 Authority/fence/quorum；
- **可用优先**：允许未消费 revoke 的 Target 在 lease/旧 view 下继续执行；
- **有界陈旧**：以 lease expiry 与时钟假设界定窗口；
- **在途许可优先**：revoke 不取消已经线性化的 exact reservation；
- **共同序列优先**：将 A/T 放进共享事务或共识域，并接受少数分区不可用；
- **效果可补偿**：允许先发生再补偿，但这不能证明 R 的全时段零 Effect，尤其不能撤销物理
  瞬时 Effect。

这也是为什么 Saga/compensation 不能替代本轮 R 的零 Effect 证明：最终状态恢复为零，不等于
整个时间区间从未发生 Effect。

## 并发 revoke 时的可达权衡

### Target fence 语义

同一 Target 内，fence install 和 execute 必须串行：谁先到本地 LP 谁赢。优点是明确、恢复
简单、无需全局钟；代价是 A 已记录但尚未传播的 revoke 不能立刻阻止 T。

### Online check / lease

普通 check 只能把竞态窗口移动到 response 之后。lease 明确允许窗口存在；如果业务不能接受
窗口，就不能把 lease 包装成 strict currentness。

### Reservation

Authority 必须预先决定：revoke 是否等待已发 permit drain、是否可强制取消未消费 permit、
以及取消如何在 Target 生效。若规则不明确，`revoke before physical Effect` 仍不足以判断该
Effect 是否越权。

### 2PC / 共识事务

若 Effect prepare 先取得冲突锁，revoke 等待或排在其后；若 revoke 先准备/提交，Effect abort。
这能给出共同顺序，但会把跨 Principal/Target 的自治边界转变为共同事务参与义务。对于无法
prepare 的物理动作，事务只能覆盖“发出动作命令”的数字状态，不能自动覆盖外部世界。

## 本地 twin 实际能够证明的类别

如果实现满足红队预注册的原生域、happens-before、同形、故障与外部锚要求，本地 S/R twin
最多能支持：

1. **存在性**：成熟组件组合可以实现一个 Target-local fence/effect 原子状态机；
2. **指定轨迹的区分力**：同一请求在 `no superseding fence before LP` 与
   `matching fence installed before LP` 两个冻结世界得到一次 Effect与零 Effect；
3. **局部因果性**：在 same-shape 与唯一 hidden diff 成立时，Target-consumed fence 是该对
   Target decision 差异的原因；
4. **恢复闭包**：Target decision 先 durable、ACK 后丢失的指定故障轨迹下，authoritative
   readback 能避免 replay，并保留 commit/reject 的真实历史；
5. **现有技术正结果**：若无需新增机制即可通过，这一条件化组合就是本作用域的解决方案。

单个 twin 即使全绿，也不能证明：

- A-global currentness 或“owner revoke 后任何远端 Effect 都不再发生”；
- 分区期间同时安全且可用；
- 多 Target、多 Authority head、equivocation、successor grant 或 alias closure 的一般解；
- 任意并发 interleaving 下的线性化实现；一个脚本化顺序只证明该顺序；
- 物理 Effect、法律 Authority、生产可靠性或真实主体认领；
- Target fence 相对 permit、lease、2PC、强中心或人工制度的总体优胜或必要性。

若希望从“指定 twin 轨迹”提升为“该本地 state machine 对并发可线性化”，还应另行运行：

- `execute LP < fence LP` 与 `fence LP < execute LP` 两个竞争顺序；
- check/commit 被 fence 插入的 TOCTOU mutation；
- Target 在 fence durability 各边界 crash/reopen 后的单调性；
- 同一 semantic key 的并发 duplicate 与 ACK-lost retry；
- `A_REVOKED_BUT_T_NOT_ACKED` 分区样本，并确认 evaluator 返回 `UNORDERED` 而非预期 R；
- 可重算历史的 linearizability checker 或确定性调度枚举，而不只重复同一 happy-path。

这些属于后续证据加强，不应阻止当前 S/R discriminator 先检验它真实声明的窄问题。

## 对 QUESTION 四项 claim 的精确影响

### 1. `CL-024-AUTHORITY-CURRENTNESS`：需要改名和降级

建议替换为：

```text
CL-024-TARGET-CONSUMED-AUTHORITY-FENCE

For the exact Target and mutation boundary, authenticated matching fence
installation and new semantic-Effect execution are serialized by one durable
Target-native state machine. A D@e request creates no new Effect when a matching
fence f>e was durably installed before its execute linearization point; absent
such an installed fence, eligibility is evaluated against the Target-consumed
grant/head/scope view. This does not establish Authority-global currentness.
```

同时把更强命题单列为未检验：

```text
CL-024-GLOBAL-AUTHORITY-CURRENTNESS = NOT_TESTED

No Target commits after LP_A(revoke), including during propagation delay or
partition. This requires additional permit/lease/transaction semantics and is
not implied by the Wave 024 twin.
```

### 2. `CL-024-EXACTLY-ONCE-RECOVERY`：可保留，但限定到 Target ledger

它应表述为 exact Target、exact semantic occurrence key 和 frozen alias/mutation boundary 内的
恰好一次数字 Effect。不要从一次 Target-native occurrence 推出物理世界或未覆盖 endpoint 的
全局 exactly-once。

### 3. `CL-024-NATIVE-POSTCONDITIONS`：与 currentness 正交

原生 Effect/Acceptance/finality 可以独立成立或失败。S 的一次 Effect不自动产生双 Acceptance；
R 的安全拒绝也不产生 Effect Acceptance/finality。这个 claim 不需要因 currentness 降级而删除。

### 4. `CL-024-ISOMORPHIC-BLINDNESS`：与跨域线性化正交

同形只能证明候选没有按泄漏标签选择行为，不能为 Authority/Target 补出一个不存在的共同 LP。
最早差异来自 Target-native response 是必要实验条件，不是 global currentness 证据。

## 对 S/R 文案的最小修改建议

S 中：

```text
旧：exact delegation 在 Target commit gate 原子检查时仍为 current
新：在 Target execute linearization point 前，没有 matching superseding fence
    被该 Target 持久安装；Target 按其已消费的 grant/head/scope view 原子判定 eligible
```

R 中：

```text
保留并强化：Authority revoke -> Target durable matching fence ACK -> execute ingress
必须形成可复算 happens-before；只有随后发生的 Target stale-fence rejection 才可评分
```

另加第三种不计分世界：

```text
U: Authority 已记录 revoke，但 Target 尚未 durable ACK，execute 与传播无完整顺序
结果：CONCURRENT_OR_UNORDERED / NOT SCORED
```

U 不是新的主实验 arm；它是防止 evaluator 把未知传播状态强塞进 S/R 的必要负控。

## 当前行动判断

1. **本轮采用 Target durable fence 即可。** R 已经预设等待 Target ACK，因此没有必要为本轮
   引入 online Authority RPC、lease、2PC 或共识事务。
2. **实现必须让 fence install 与 Effect commit 共享 Target-local serialization root。** 仅把
   两条签名 receipt 拼接到 controller manifest 不足。
3. **Question 的 global-sounding claim 必须降级。** 否则一个正确的 Target fence 实现也会被
   用来支撑它没有提供的跨域即时撤销。
4. **保留成熟替代方案。** 若未来真实任务需要 owner-global strict currentness，再比较
   fail-closed online monitor、bounded lease、irrevocable reservation 与 2PC/consensus；不要
   从本 twin 直接推断必须创新。
5. **本地 twin 的建设性价值是确定最小充分组合与适用条件。** 它若成功，说明这个有界 residual
   已由成熟技术解决；它若在原子性 mutation 下失败，才说明实现或所选组合仍有具体缺口。

最终最高准确表述应是：

> 在冻结的本地合成数字 Target、预锚合成 Authority root 与合作式进程隔离下，Target-native
> durable monotonic fence 和 atomic operation ledger 可以对同一 exact request 实现
> target-consumed revocation ordering：fence LP 在先则零新 Effect，execute LP 在先则至多一次
> Effect；ACK 丢失后 authoritative readback 保留原决定且不 replay。该结果不建立
> Authority-global instantaneous revocation。
