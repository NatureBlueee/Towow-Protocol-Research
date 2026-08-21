# Wave 013 扩六案前的 runner 抽象

日期：2026-07-30  
状态：`IMPLEMENTATION GATE / E1+E5 UNAFFECTED / REMAINING CASES NOT RUN`

## 结论

当前 dual-view `arm_binding_token` 与 child argv 清理是真实修复。它们关闭了当前 E1/E5
运行中的三类直接答案通道：

```text
CURRENT_E1_E5_EXPLICIT_LABEL_LEAK = CLOSED
CURRENT_E1_E5_PRIVATE_MANIFEST_HASH_DICTIONARY = CLOSED
CURRENT_E1_E5_PARENT_CASE_ARGV_LEAK = CLOSED
```

这不否定 `ROOT-ACCEPTANCE.md` 对 E1/E5 的 scoped local synthetic 结果，也不要求回滚现有
实现。

但当前 runner 仍是面向固定 E1/E5 topology、单一 A4 child 和 success/refusal 两分支的纵切。
如果直接增加六个 `case_id` 分支、owner process 或 fault flag，极易得到“arm 从 runner
形状读出答案”的假成功。因此以下抽象是扩展 E0/E2/E3A/E3B/E4/E6 前的实现门槛，不是对
当前 E1/E5 的追溯降级。

## 一、当前风险

### 1. blacklist projection 不能承担未来 arm view

当前 arm manifest 是从 evaluator-private manifest 中删除 `case_id` 与
`manifest_sha256` 后得到。这是 blacklist projection；新增 private 字段时默认会流入 arm。

目前 arm 仍可见：

- `world_root`，其来源含 private case receipt；
- `authority_stratum`；
- `owner_registry_sha256`；
- `target_registry_sha256`；
- runner-level `runtime_policy` 与实验开关。

这些值在 E1/E5 中没有形成当前已知答案通道，但扩案后可能直接区分：

- E0 的 `U / LAWFULLY_UNIFIED`；
- E4 的多 resource-owner topology；
- E3B 的 decoy target；
- E6 的 source/target runtime 或 migration shape。

因此后续必须使用 public allowlist 构造 arm view，不能继续依赖“完整 manifest 减少数
字段”。

`arm_binding_token` 本身可以保留：它是独立随机值，不由 case 或 private manifest 派生。
但它只能做公开 IPC binding，不能作为 arm 可查询的 token-to-private-case lookup key。

### 2. owner topology 与 endpoint count 可能成为答案

当前 arm 启动时收到显式 owner 名列表和每个 owner 的独立 queue endpoint；inherited FD
inventory 也反映 endpoint 数量。

这在固定 E1/E5 topology 下没有区分力，但不能扩展为：

- 用六个假独立 owner 表示 E0，破坏 lawful unity；
- 增加 `O_R:alternative` endpoint 表示 E4，在 discovery 前暴露 alternative；
- 增加 decoy Target 或 migration runtime endpoint，并让 E3B/E6 从进程数获得答案。

owner/Target 的真实 topology 应保存在 evaluator-private registry。arm 只接触固定 broker
surface，并通过实际 discovery、owner response 与 Target readback逐步获得合法信息。

### 3. E3A/E3B 的 pre-readback 同构尚未建立

每次 run 都重新随机生成 run/token/PID/key/state head/request nonce/signature。即使两个
world 的可见语义完全相同，raw bytes 与 prefix hash 仍必然不同。

“两个启动 payload 长度相同”不能替代 E3 pair 的 indistinguishability。扩案前必须明确采用
以下一种证据：

1. **paired fork**：从同一个冻结可见 S0/prefix 分叉两个 evaluator-private Target outcome，
   向两个 arm 重放同一份 signed public prefix；或
2. **α-equivalence**：预注册允许重命名的 opaque run/token/PID/key/nonce/signature，再证明
   schema、action sequence、合法可见语义、response family、timing bucket 与 endpoint
   surface 完全同构。

E3A/E3B 只允许在 exact Target status/readback response 处首次出现可观察差异。

### 4. E4 alternative 不能由 topology 预告

E4 的 alternative 身份、owner 数、排序、endpoint、expected action 与成功结论都不能进入
arm 初始输入。

特别需要阻止：

- 启动时出现 `O_R:alternative`；
- owner registry digest 成为稳定的 topology 标签；
- revoke 前 DISCOVER 已返回完整 alternative set；
- process name、FD 数或 endpoint map 暴露额外 owner；
- controller 在 public packet 中预选 alternative。

alternative 必须由 primary revoke 之后的实际查询返回 opaque owner/resource handle；其真实
Principal、key、state 与可行性仍由 evaluator-private registry 和原生日志验证。

### 5. E6 crash schedule 不能成为 runtime policy

当前 runner 已把 `duplicate_execute_probe` 作为 arm-visible runtime policy 字段。这在当前
窄测试中不是 case label，但不能沿用为 E6 的故障注入方式。

source runtime 初始 payload 不得包含：

- 将要 crash；
- crash cut；
- 是否会迁移；
- target epoch；
- old runtime 是否 restart；
- 预期 fence result。

这些事件必须由 evaluator-controlled controller 在对应 native event hash 出现后触发。迁移
runtime 只在 crash 后获得真实 recovery capsule；old runtime 只在实际 restart 时观察
durable fence 的返回。

当前 child argv 修复也不能只包住第一只 A4 process。E6 的 source、migrated 与 restarted
runtime 都必须走同一 blind launcher。并行运行时不能依赖临时改写全局 parent `sys.argv`，
否则另一个同时 spawn 的 process 可能继承错误 argv。

## 二、扩案前必须形成的五个接口

### 1. `ArmViewFactory`

职责：从 public task contract 明确构造 arm-visible context，而不是裁剪 private manifest。

建议输出只包含：

```text
public schema
opaque episode/run binding
arm_binding_token
arm id
Q version and exact task constraints
object/target/operation public coordinates
deadline and cost/action envelope
fixed broker capabilities
```

明确排除：

```text
semantic case id
expected disposition
private-derived world root
authority-stratum conclusion
owner/target registry digest
alternative oracle
future owner decision
fault/crash schedule
evaluator manifest hash
```

接口还应生成逐字段 disclosure receipt，并对所有未列入 allowlist 的新增字段 fail closed。

### 2. `BlindProcessLauncher`

职责：为所有 method/solver/coordinator child 创建统一可见性边界。

必须提供：

- 固定 bootstrap argv，不从 parent CLI 继承 semantic `--case`；
- 显式最小 env；
- opaque process name 与 cwd；
- 受控 FD/IPC inventory；
- 固定 broker endpoint surface；
- start-payload bytes/hash 与可见性扫描；
- 并发安全，不依赖无锁修改全局 `sys.argv`。

它必须覆盖：

- 当前 A4；
- E6 source runtime；
- E6 migrated runtime；
- E6 old-runtime restart；
- 后续 A1/A3/A5 比较 arm。

owner/Target 事实源可以接收 evaluator-private binding，但不得把它通过 response、
process name、错误信息或 latency class反射回 arm。

### 3. `OwnerTopologyBroker`

职责：把真实 owner topology 与 arm-facing request surface 分开。

evaluator-private registry 至少保存：

```text
owner_instance_id / owner_role / principal_id / authority_locus
process/key/state/backend identity
current head and epoch
discoverability condition
```

arm-facing surface 保持固定数量的 broker endpoint。合法 DISCOVER 返回 opaque owner handle，
后续 request 经 broker 路由到实际 owner process。

它必须能够同时表达：

- E0：一个 lawful Principal 承担多个 owner role；
- E2：多个 owner 形成 exact token/delegation/commitment；
- E4：`O_R:primary` 与 `O_R:alternative` 是两个真实 owner instance；
- refusal、defer、Unknown、revoke 与 current-head change。

不能用 dummy owner 数量对齐掩盖真实 Principal 关系，也不能把真实 endpoint count直接给 arm。

### 4. `TargetOperationLedger`

职责：提供 operation-bound 的唯一 Effect truth 与可恢复 readback。

最小 API：

```text
EXECUTE
STATUS
READBACK
```

它必须原生支持：

- current Authority set consumption；
- exactly-one occurrence/idempotent retry；
- signed positive readback；
- current-head signed negative readback；
- exact object/target/operation binding；
- negative query 的 ledger coverage；
- `effect_start_minute + offset 0..45 <= 90` 的相对样本；
- wrong-object/history decoy 排除；
- E6 跨 runtime 的 durable operation state。

“没有 Target 日志”“本地没找到”“arm 自报未发生”均不能替代 signed negative readback。

### 5. `HiddenScenarioController`

职责：冻结并注入 arm 不应提前知道的 exogenous event 与 lifecycle transition。

覆盖：

- E2 owner-decision reverse 与 formation-operator removal；
- E3A/E3B submit ACK drop、commit/no-commit private fork；
- E4 primary revoke 与 revoke 后 alternative discoverability；
- E6 crash cut、capsule交接、target runtime start、old-runtime restart；
- paired fork 或 α-equivalence evidence。

事件应由 native request/event hash、current logical time和冻结 schedule 触发，并产生
controller-private receipt。它不能把 `drop_ack=true`、`effect_occurred=true`、
`will_migrate=true` 等 flag 放入 arm payload。

对于 E3 pair，controller 还必须证明在 readback 前：

```text
same public action alphabet
same endpoint surface
same response semantics
same observable timing class
same failure returned to submit
no label/topology/schedule leak
```

## 三、扩案准入

在五个接口建立前，以下状态保持：

```text
E1_E5_CURRENT_SCOPED_RESULT = RETAINED
REMAINING_SIX_CASE_CONTRACTS = SPECIFIED / NOT RUN
FUTURE_CASE_ARM_VIEW_NONINTERFERENCE = NOT ESTABLISHED
E3_PAIR_PRE_READBACK_EQUIVALENCE = NOT ESTABLISHED
E4_ALTERNATIVE_TOPOLOGY_HIDDEN = NOT ESTABLISHED
E6_CRASH_SCHEDULE_HIDDEN = NOT ESTABLISHED
```

扩案准入不是“接口文件存在”，而是至少实际证明：

1. 一个 private manifest 新增字段不会自动进入 arm view；
2. E0/E4 不因 owner count、endpoint map、registry digest 或 FD inventory 泄漏 topology；
3. E3A/E3B 在 readback 前满足预注册的 paired-fork 或 α-equivalence；
4. E4 alternative 只能在 revoke 后经实际 query 出现；
5. E6 source/new/old runtime 都由 `BlindProcessLauncher` 启动，fault schedule 只在
   `HiddenScenarioController`；
6. 独立 evaluator 仍只从原生 owner/Target/runtime logs 重算结果。

这些门槛防止把 E1 success shape 或 E5 refusal shape 改名复制成六案，不预设现成组合会
失败，也不制造新机制必要性。
