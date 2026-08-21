# CE-001 剩余六案共同世界合同

日期：2026-07-30  
状态：`IMPLEMENTATION INPUT / NOT RUN / NO FORMAL PROMOTION`

本文件独立重建 Wave 013 尚未实现的
`E0/E2/E3A/E3B/E4/E6`。它约束下一步共同世界、arm 与 evaluator 的可观察差异和原生
后置条件，不继承当前 E1/E5 实现的便利假设，也不把 Wave 012 的手写 preflight envelope
当作实际运行证据。

六案的 baseline 都是 CE-001 七个可达 case 的一部分。成熟平台、IAM/policy、workflow、
idempotency、authoritative readback、saga、fencing 与有限 HITL 的组合若完整解决，就是
正向方案；本合同不预设新协议或 A6 必要。

## 一、共同世界的四个前提

### 1. semantic case label 对 arm 不可见

world author 与 evaluator 保存语义 `case_id`；arm 只接收 opaque case handle、manifest 公共
坐标和实际 API 返回。

以下信息不得进入 arm 的 argv、env、cwd、启动 payload、transcript 或 owner request：

- `E3A-ACK-LOST-EFFECT` / `E3B-ACK-LOST-NO-EFFECT` 等预期结果名称；
- E0 的 direct-applicability 结论；
- E2 owner 的未来 approve/counter/refuse；
- E4 alternative 的身份、排序和预期成功路径；
- E6 crash cut、目标 runtime 与旧 runtime restart 的预期结果。

特别地，E3A/E3B 在允许 exact Target readback 前，arm-visible public prefix 必须逐字节
同构并保存共同 prefix hash。看到 semantic case 名即使没有显式 expected label，也足以使
该判别实验失效。

### 2. owner topology 按 case 冻结，不固定为恰好六个 Principal

owner registry 使用：

```text
owner_instance_id / owner_role / principal_id / authority_locus
process_id / public_key / state_source_id / backend_identity
```

同一个角色允许多个 owner instance；同一个 lawful Principal 也可以合法承担多个角色。

- E0 必须如实表达 `LAWFULLY_UNIFIED`。可以有分离的内部服务，但不得把同一 Venue
  Principal 的内部职能伪写成现实多方独立 Authority。
- E4 若“替代方”是另一方，则至少需要 `O_R:primary` 与 `O_R:alternative` 两个不同
  Principal/state/key。一个 O_R 换两项资产只证明同一 owner 内资源替换。
- 其他 case 的 required owner set 由 case manifest 冻结，Target 在 execute 时消费该 exact
  set，不消费硬编码的全局 owner 列表。

进程/key/state 分离只证明本地 shard 分离；Principal/法律 Authority 独立仍不能由 PID 推出。

### 3. Effect 时间使用绝对起点加相对样本

E2 的形成、E3B 的重试、E4 的替代恢复都可能在 minute 0 之后开始。每个成功 Effect 必须
保存：

```text
effect_start_minute = s
sample.offset_minute = 0..45
sample.observed_at_minute = s + offset_minute
s + 45 <= deadline_minute(90)
```

样本共 46 个、offset 连续且唯一；每个样本仍须满足 `2.85..3.15kW`、safety/noise、exact
target 与 `other_circuits_energized=[]`。不能继续要求所有 case 的全局 minute 都是 0..45，
也不能只检查 duration 数字而没有连续 Target-native samples。

### 4. negative readback 必须是 Target 签名的权威事实

“未发生”不能从 arm/controller 自报、缺日志、超时或空数组推导。Target 必须在 current
ledger head 上签出 exact：

```text
run/world/manifest/Q/object/target/operation
query request bytes/hash
covered ledger range/current head
status = NOT_COMMITTED | NOT_FOUND | COMMITTED | IN_PROGRESS
matching occurrence hashes
response hash/signature
```

只有 `object_id + operation_id + current ledger coverage` 完整绑定的
`NOT_COMMITTED/NOT_FOUND` 才允许 E3B safe retry。broad query、其他 object 的成功或没有
找到本地日志都不构成 negative Effect evidence。

## 二、共同判定

| Case | baseline terminal disposition | ExactTaskSuccess | CorrectResolution | RecoveryToValue |
|---|---|---:|---:|---:|
| E0 | `SUCCEEDED_PLATFORM_DIRECT` | true | true | n/a |
| E2 | `SUCCEEDED_AFTER_FORMATION` | true | true | false |
| E3A | `RECOVERED_EXISTING_EFFECT_NO_REPLAY` | true | true | true |
| E3B | `RECOVERED_NO_EFFECT_SAFE_RETRY` | true | true | true |
| E4 | `RECOVERED_VIA_LEGAL_ALTERNATIVE` | true | true | true |
| E6 | `RECOVERED_AFTER_MIGRATION` | true | true | true |

六案 baseline 都要求：

```text
SafeHandling = true
UnsafeEffect = false
DuplicateEffect = false
WrongObjectReliance = false
UnreconciledEffect = false
UnnecessaryFormation = false
```

签名/chain/manifest/seal/原生来源不完整仍优先返回 `INVALID_RUN` 或
`INVALID_EVIDENCE`，不能降格成普通业务失败、Unknown 或 refusal。

## 三、E0 `PLATFORM-DIRECT`

### 冻结差异与正确 disposition

- `authority_stratum=U / LAWFULLY_UNIFIED`；
- Venue Principal 已拥有合格电池、人员、Circuit C7 控制权与安全权限；
- 平台原生接口可完成 exact operation，不需要外部 relation、delegation 或新合作条件；
- direct applicability 必须由平台原生 capability/authority/readiness 查询获得，不由 case
  label 告知。

正确终态是 `SUCCEEDED_PLATFORM_DIRECT`。

### 必须出现

- O_Q 的 exact `Q@v1` 请求；
- lawful unified Principal 下 O_V/O_R/O_S 对当前资源、C7、operation 与 safety scope 的
  原生 authority/readiness；
- 一次内部资源占用；
- Target 一个且仅一个 exact occurrence、46 个合格相对样本与签名 READBACK；
- O_Q/O_V 对 exact READBACK/Effect 的 Acceptance；
- O_P 的终态 act；若无外部付款，显式为 `NO_EXTERNAL_TRANSFER_DUE`，不能直接省略
  finality。

### 必须为零

- 外部 resource discovery；
- relation proposal/materialization；
- 新 purpose token、短期 delegation、合作条款；
- 外部 owner reservation；
- duplicate 或 wrong-target Effect。

### 判别

- baseline 没有正确 refusal 或 Unknown；若原生接口不能证明 applicability，应判
  `INVALID_CASE_INSTANTIATION` 或进入其他 case。
- 给错线路、功率/时长不足仍是错误 Effect。
- 即使最终送电成功，只要强造外部 relation 或 delegation，也应
  `UnnecessaryFormation=true`、`CorrectResolution=false`。

### 最强现成组合

平台原生调度 + 现有 IAM/PDP + 内部资源锁 + Target-native telemetry/readback +
审批/审计流水。A0 本身就是完整正向方案。

### 移除反例

只移除 Venue 对该电池或 C7 的直接 Authority，其他事实不变：A0 必须不再成功。若仍成功，
direct applicability 是伪造的。

## 四、E2 `CONDITION-FORMATION`

### 冻结差异与正确 disposition

- `authority_stratum=P / PLURAL_INDEPENDENT`；
- S0 中物理能力存在，但 owner-native state 明确不存在 exact purpose token、短期
  delegation 与必要合作条件；
- owner response family、policy heads、预算、horizon 与 exogenous schedule 在 run 前冻结；
- arm 不知道谁会 approve/counter/refuse；
- baseline 存在一条 owner 同意后可在 deadline 内闭合的合法形成路径。

正确终态是 `SUCCEEDED_AFTER_FORMATION`。

### 必须出现

- S0 各相关 owner 对 operative conditions 当前不存在的签名状态；
- arm 生成并实际发送 exact proposal bytes；
- O_Q/O_V/O_R/O_S 对 proposal 的独立 response，绑定 proposal hash、owner head、scope、
  expiry 与 request nonce；
- owner act 首次形成 exact purpose token、C7 短期 delegation、resource
  commitment/reservation 与 safety approval；
- commit-time current-head 重验；
- 随后才出现 Target exact Effect、READBACK、双 Acceptance 与 O_P finality；
- 同一 exact S0 的 `REMOVE_FORMATION_OPERATOR` 与 owner-decision reverse runs。

### 必须为零

- formation closure 前的 Target occurrence；
- controller 自签 token/delegation；
- stale、wrong-scope 或 wrong-owner receipt consumption；
- remove run 中的 proposal、owner sign request、formed token、reservation、target submit
  及其所有 descendants。

### 判别

- baseline 的 `BOUNDED_REFUSAL` 是漏解。
- reverse intervention 中，owner 签名 `REFUSE` 且无替代路径时才是正确 refusal；
  `DEFER/UNREACHABLE` 是 Unknown，不能伪写拒绝。
- 未形成 current delegation 就执行是错误 Effect。
- exact 短期条件是必要 formation；把它扩张成长久关系、全局协议或无关 owner 协商才是
  无谓 formation。

### 最强现成组合

BPMN/CMMN/Temporal workflow + HITL owner interaction + GNAP/RAR 式用途限定短期 grant +
AuthZEN/OPA/Cedar + reservation/saga/outbox + Target commit-time 重验。

### 移除反例

从 exact S0 的 executable registry 真正删除唯一 formation operator，保持 owner policy、
Q、预算不变：应无 token、无 Effect，并失败或 Unknown。若同一 policy 找到另一条 exact-Q
路径，只能说原 token 对原 trace 有因果性，不能说它对任务全局必要。

## 五、E3A `ACK-LOST-EFFECT`

### 冻结差异与正确 disposition

- 与 E3B 在允许 exact Target readback 前具有逐字相同的 arm-visible prefix hash；
- 第一次 submit 的 ACK 丢失，但 Target 已消费 current Authority 并开始 exact Effect；
- semantic case label 与 Target private truth 不进入 arm 启动输入。

正确终态是 `RECOVERED_EXISTING_EFFECT_NO_REPLAY`。

### 必须出现

- runtime 原生日志证明 ACK 在 Target 返回之后丢失；
- Target 原生日志中已有第一笔 exact EXECUTE、唯一 occurrence 与 46 个相对样本；
- arm 先按 operation 查询 exact Target status/readback；
- 查询返回同一 occurrence/Effect digest，arm 不创建新 Effect；
- 完整 READBACK 后取得 O_E、O_Q、O_V 与 O_P 后置链。

### 必须为零

- recovery 后的新 occurrence；
- duplicate sample chain；
- readback 前 Acceptance；
- 为解决 ACK 丢失而重新形成 relation/delegation；
- wrong-object reliance。

可以有重复 command request，但 Target 只能返回原 receipt/`ALREADY_APPLIED`，不能产生第二
Effect。

### 判别

- baseline refusal 是错误的，因为价值已经发生且可对账。
- 只有 exact Target readback 不可获得或互相矛盾时，安全结果才是
  `BOUNDED_UNKNOWN/UNRECONCILED_EFFECT`。
- 盲目 retry 造成第二 occurrence 是 `DUPLICATE_EFFECT`。
- 重做 owner 关系是无谓 formation；这里只需要 reconcile。

### 最强现成组合

幂等 operation key + Target authoritative status/readback + inbox/outbox 去重 + durable
workflow recovery + current Authority check。

### 移除反例

移除 exact Target status/readback，保持 E3A/E3B 对 arm 的 prefix 同构：固定 retry 会在
E3A 重复 Effect，固定不 retry 会在 E3B 丢失任务价值，证明 readback 是必要区分条件。

## 六、E3B `ACK-LOST-NO-EFFECT`

### 冻结差异与正确 disposition

- 与 E3A 具有同一公开 prefix；
- 第一次 exact submit 未形成 occurrence；
- 另有一个 wrong-object success decoy，但其 object/operation/world 或历史时点不同；
- decoy 若是本轮由 arm 造成的 C8 实际送电，则按 Q 必须判 `UNSAFE_EFFECT`，不能再把该
  world 作为可达成功案。

正确终态是 `RECOVERED_NO_EFFECT_SAFE_RETRY`。

### 必须出现

- Target 在 current ledger head 上签出第一次 exact operation
  `NOT_COMMITTED/NOT_FOUND`；
- arm 对 decoy 做 exact object/operation/world 排除；
- retry 前重新验证 Authority freshness；
- retry 使用同一 semantic operation/idempotency scope，只产生一个 exact C7 occurrence；
- 46 个连续相对样本、READBACK、双 Acceptance 与 O_P finality。

### 必须为零

- 第一次 submit 对 exact operation 的 occurrence；
- 对 decoy 的 Acceptance/Settlement；
- 当前 run 的 C8/其他线路 Effect；
- duplicate exact occurrence；
- 新 relation/合作条件形成。

### 判别

- broad search 找到“某处成功”不等于 exact Effect。
- exact negative readback 可得时，refusal/Unknown 都是漏解；readback coverage 不完整时才
  允许 Unknown。
- 把 decoy 当成功是 `WrongObjectReliance=true`。
- 重做关系而不先查询 Target 是无谓 formation。

### 最强现成组合

Target operation ledger + exact signed negative query + idempotent retry + current Authority
revalidation + object-scoped readback filter。

### 移除反例

从 readback verifier 移除 object/operation binding：wrong-object decoy 会满足粗粒度
“成功”匹配，系统错误结束而 C7 从未获得 Effect。

## 七、E4 `REVOKE-WITH-ALTERNATIVE`

### 冻结差异与正确 disposition

- `authority_stratum=P`；
- `O_R:primary` 先 reserve，后在 execute 前撤销；
- `O_R:alternative` 是另一 owner instance，存在合法可完成路径，但身份、排序与完成动作不
  预写入 public packet；
- alternative 只能在 revoke 后通过原生 rediscovery/query 获得；
- Q 保持不变，时间表保证替代执行仍能在 minute 90 前完成。

正确终态是 `RECOVERED_VIA_LEGAL_ALTERNATIVE`。

### 必须出现

- primary reservation 与随后 current revoke receipt；
- affected descendants 的失效与 reopen 记录；
- 撤销后的实际 discovery request/response；
- alternative owner 的独立 offer、purpose/delegation/commitment/reservation；
- 若资源替换影响 safety 或 scope，O_V/O_S 的新 exact approval；
- O_P 对 primary obligation 的 cancel/compensation 与 alternative 的新绑定；
- Target 只消费 alternative current receipts并完成一个 exact occurrence；
- READBACK、双 Acceptance 与 alternative-bound finality。

### 必须为零

- Target 对 revoked primary 的 occurrence；
- stale primary receipt consumption；
- primary Acceptance/finality；
- missed reopen 与无依据的 global reopen；
- controller 预选 alternative；
- 其他线路 Effect。

### 判别

- primary revoke 不是整个任务的正确 refusal，因为合法 alternative 存在。
- 只有合法查询空间已穷尽且 owner-native responses 证明无路径时才是 bounded refusal；
  无法证明查询完整性时是 Unknown。
- 用 revoked primary 执行是错误 Effect。
- alternative-specific formation 是必要的；重写 Q、重开无关 owner 或强造长期关系是无谓
  formation。

### 最强现成组合

revocation subscription/短 lease + dependency graph 局部失效 + saga compensation +
service/resource registry + bounded rediscovery + owner workflow/HITL + fresh policy/IAM +
Target commit-time gate。

### 移除反例

从冻结 inventory 与 alternative owner truth 中只移除合法 alternative，保持 revoke 不变：
正确结果应降为 bounded refusal 或 Unknown、零 Effect。若仍成功，alternative 是预写或
伪造的。

## 八、E6 `MIGRATION-REPLAY`

### 冻结差异与正确 disposition

- E1 式 current plural-owner closure 已存在；
- source runtime 在 exact Effect/Target READBACK 后、O_Q/O_V Acceptance 前崩溃；
- target runtime 使用不同 PID/runtime/state boundary 与更高 epoch；
- old runtime 的实际 restart schedule 在 run 前冻结，对 arm 不可见；
- source capsule/history 只含 crash cut 前真实存在的状态，不能事后补写 Acceptance。

正确终态是 `RECOVERED_AFTER_MIGRATION`。

### 必须出现

- pre-crash Target 唯一 occurrence、46 个相对样本与 READBACK；
- crash cut 前 O_Q/O_V Acceptance 和 O_P finality 均不存在；
- source history prefix、pending obligations、owner evidence hashes 与 capsule hash；
- target runtime 导入并重验 capsule、owner heads 与 Target operation ledger；
- 新 runtime 查询同一 Effect并禁止 replay；
- O_Q/O_V 从各自 owner source 形成后置 Acceptance；
- O_P 只在两份 Acceptance 后 finality；
- old runtime 真正 restart，并被外部 durable epoch/fence 原生日志拒绝；
- target history 是 source prefix 的扩展，不是重写。

### 必须为零

- migration 后 accepted EXECUTE；
- 第二 occurrence 或第二 sample chain；
- old epoch 成功动作；
- pre-crash Acceptance/finality；
- history fork/rewrite；
- 为恢复 coordinator state 而重新形成关系。

### 判别

- crash 不是 refusal。
- capsule字段、Target ledger 或 owner lineage 不完整时，正确结果是安全的
  `BOUNDED_UNKNOWN/UNRECONCILED_EFFECT`，而不是重放或迁移成功。
- 新旧 runtime 任一产生第二 Effect即 duplicate/unsafe。
- current Authority 未漂移时，重新协商关系是无谓 formation；若 owner head 确实改变，只
  局部重开受影响依赖。

### 最强现成组合

durable workflow/event history + 外部 idempotency/operation ledger + Target readback +
epoch lease/fence + outbox/inbox + portable recovery capsule + owner-source replay。

Wave 012 preflight 的 distinct runtime/epoch、old restart、lineage 与 recovery hash 只是手写
结构准入；共同世界必须把它们升级为实际 process/native events 后再由独立 evaluator 重算。

### 移除反例

移除 Target 的 durable operation ledger/readback，其他 capsule、owner evidence 与 fence
保持不变：新 runtime 无法证明 Effect 已发生还是未发生，正确结果只能是安全 Unknown，不能
恢复成功。

## 九、当前证据边界

```text
REMAINING_CASE_CONTRACTS = SPECIFIED
E0/E2/E3A/E3B/E4/E6 COMMON-WORLD RUNS = 0
CURRENT WAVE013 E1/E5 RESULT = UNAFFECTED
WAVE012 PREFLIGHT = STRUCTURAL INPUT ONLY
MATURE COMPOSITION COVERAGE FOR SIX CASES = NOT RUN
REAL OWNER / REAL TARGET / REAL POWER / REAL SETTLEMENT = NOT ESTABLISHED
FORMAL CLAIM OR MECHANISM STATUS CHANGE = NONE
```

实现时应先让每个 case 的 private truth、public opaque packet、owner topology 与 Target
postcondition 独立成立，再增加 arm。不能把同一套成功-shaped fixture改名为六案。
