# Wave 020 E6 independent red-team

日期：2026-07-30  
状态：`ROOT RAW RE-AUDIT PASSED / SCOPED ACCEPTANCE GRANTED`

本审计只从 CE-001 exact task 与 `REMAINING-CASE-CONTRACTS.md` 的 E6 required
claims 出发。它不继承 builder 的预期结论，不把测试绿灯、controller 文本、schema
完整或未冻结运行当作证据。

## 冻结攻击矩阵

| ID | 必须区分的现实 | 可执行攻击 / 独立检查 | 接受条件 |
|---|---|---|---|
| RT-01 | crash vs 受控暂停/合作退出 | 检查 source 的退出路径、exit code、crash cut 后是否还能导出/签写/响应；攻击 cooperative export-after-cut | source 在 Effect/readback 后被外部非合作终止；cut 后 source 零写入、零 capsule 生成 |
| RT-02 | durable native fact vs controller 叙述 | 删除/篡改 controller summary，只从 SQLite native rows、process receipts 和 frozen bytes 重建 crash、epoch、Target、owner 状态 | 结论不依赖 controller 自述字段 |
| RT-03 | standalone freeze vs WAL 主文件 | 检查 SQLite header 18/19、`-wal/-shm/-journal`、physical hash、logical table snapshot；复制主文件单独复核 | 每个正式 DB 是 DELETE `01/01` 单文件，且物理/逻辑哈希均受绑定 |
| RT-04 | reconcile existing Effect vs migrated 第二次 EXECUTE | 搜索 migrated native requests/target mutations；主动提交 migrated EXECUTE/replay attack | migrated 只查询/导入/reconcile；Target occurrence、commit event、sample chain 均恰为一 |
| RT-05 | 真正 restart/reopen vs 新进程角色扮演 | 核对 old runtime restart schedule 的 run-before freeze、不同 PID、重新打开独立 durable source state、跨 controller instance 的 fence read | old restart 不是 controller 内存对象调用；在新 controller/connection 下由外部 durable fence 拒绝 |
| RT-06 | prefix extension vs 可重写 history | 重算 source prefix hash、逐项 prefix equality、target append；rewrite/fork/transplant/remove-entry attacks | migrated history 逐字以 source frozen prefix 开头，只追加 recovery events |
| RT-07 | crash cut 前零 Acceptance/finality | 直接查询 O_Q/O_V/O_P owner-native DB 与 source capsule/history；将 post-crash receipt 移入 prefix 攻击 | pre-crash 三者均不存在；Acceptance 只能由各 owner source 在 migrated readback 后生成；finality 后于两者 |
| RT-08 | Target evidence 必要性 | REMOVE_TARGET_EVIDENCE 只移除 durable ledger/readback，保持其他输入等价 | 必须降为 `BOUNDED_UNKNOWN/UNRECONCILED_EFFECT`，零 EXECUTE、零 Acceptance/finality |
| RT-09 | opaque startup vs scenario 泄漏 | 扫描 source/migrated/old 的 startup、argv、cwd、env、process name、public transcript | 无 E6/case/outcome/crash cut/restart schedule/private paths/owner answer |
| RT-10 | exact CE-001 vs 粗粒度 energized=true | 独立验证 occurrence/readback 的 46 offsets 0..45、absolute minute、45-minute duration、3kW±5%、safety/noise、other circuits、deadline | 每个 sample 全坐标成立，不能靠顶层布尔值通过 |
| RT-11 | owner-current revalidation vs 旧 receipt 搬运 | 篡改 owner head、key、principal、receipt order；检查 migrated fresh query 是否来自 owner source | exact O_Q/O_V/O_P current heads 与 capsule lineage 一致；漂移时不得全局静默接受 |
| RT-12 | exactly-once finality vs controller 拼接 | 交换 Acceptance、删除一个、重复 finality、wrong readback/operation | O_P 原生 finality 只在两份 exact Acceptance 后出现且只出现一次 |
| RT-13 | frozen run vs live mutable directory | 重算 artifact、DB、capsule、source/migrated state 的哈希；检查 manifest 是否遗漏文件 | acceptance 只针对不可歧义的完整 frozen package；任何未绑定 mutable truth 都拒绝 |

## 暂不接受

在实际代码检查、攻击执行、冻结 artifact 重放以及 REMOVE_TARGET_EVIDENCE 反事实完成前：

```text
E6_ACCEPTED = false
RECOVERED_AFTER_MIGRATION = NOT INDEPENDENTLY ESTABLISHED
```

## 第一轮代码与现有 artifact 审计

当前仍为 `REOPENED / BLOCKED`，不能接受。

### B-00：当前实现不能完成一轮 baseline

在 `/tmp` 独立目录直接调用当前 `make_frozen_configuration()` +
`run_case(..., DURABLE_FULL)`，source termination 与 controller reopen 之后，migrated child
立即失败：

```text
TypeError: migrated_runtime_worker() got an unexpected keyword argument
'capsule_file'
```

当前 worker 签名要求 `source_capsule_file` 与 `migration_view_file`，但 `run_case()` 仍传
`capsule_file`，parent 最终在 `migrated_results.get(timeout=20)` 得到 `_queue.Empty`。
因此 builder 当前显然仍在重构中；下面其余发现是代码审计输入，不是对完成 artifact 的最终
裁决。

### B-01：现有 latest artifact 不是当前 evaluator 可接受的冻结包

`artifacts/latest-suite.txt` 当前指向
`suite-ca9328a414a34b6ea9aac56499e5dbe0`。其 `artifact.json` 没有当前 evaluator
要求的 `formal_database_paths`，目录中也没有 `formal/` snapshots。直接运行当前
`independent_evaluator.py artifacts/actual-e6-migration-replay.json` 得到
`KeyError: formal_database_paths`，exit status 1。

同时，两个 case 的 runtime SQLite files 虽然 header 为 DELETE `01/01`，但每个主文件
旁都存在 `-shm`。它们不能作为 standalone formal truth。

因此现有 `ROOT-ACCEPTANCE.json` 无论写了什么 decision，都不是当前实现/当前 evaluator
下可重放的 acceptance。

### B-02：冻结 exact task 的 `object_id` 错了

CE-001 的 object 是 `VenueV:CircuitC7`，operation 是一次独立 operation。当前 runtime 与
evaluator 的 `exact_task()` 都写成：

```text
object_id = CE001:VenueV:CircuitC7:3kW:45m
target_id = VenueV:CircuitC7
operation_id = CE001:VenueV:CircuitC7:3kW:45m
```

这让 `object_id == operation_id`，与 CE-001 正典 `object_id=VenueV:CircuitC7` 不同。
runtime 与 evaluator 复制同一个错误常量只会共同假绿。必须修正后重新生成全部 frozen
input、capsule、Target receipt/readback 和 artifacts。

### B-03：formal DB evaluator 仍可能把 WAL header 读成 DELETE

`verify_formal_database()`、`read_durable()`、`verify_target_db()`、owner/state DB
verification 都通过 `mode=ro&immutable=1` 执行 `PRAGMA journal_mode`。SQLite 对没有
companions 的 WAL-header 主文件可在 immutable view 中报告 `delete`；Wave018 已实际复现
此行为。

当前 evaluator 没有直接验证 SQLite header bytes 18/19。攻击者可以把正式 DB 改成 WAL
header、移除 sidecars、重算 artifact/summary 内部 hashes，而 evaluator 的 mode check 仍
可能通过。必须要求 header 精确 `01/01`，并把 journal mode 纳入独立 logical snapshot。

### B-04：old restart 没有证明是旧 runtime durable identity 的 reopen

第二代 controller 确实是另一 spawn process，也确实 spawn 另一 worker；但
`old_runtime_restart_worker`：

- 不打开 `source-state.sqlite3`；
- 不持有/验证 source runtime key；
- 不恢复 source durable state；
- 只拿一个 `runtime_handle`，由共享 durable DB 查出 epoch 1 后提交 `EXECUTE`。

所以当前事实只证明“一个新 generic process 使用 source handle 被 fence 拒绝”，还不能
区分“旧 runtime 真正 restart”与“controller 新建进程角色扮演旧 runtime”。至少需要新
进程实际 reopen source state identity、以冻结 credential 证明身份，并由外部 fence
记录该 credential/state binding。

### B-05：restart schedule 没有 run-before frozen evidence

E6 要求 old-runtime restart schedule 在 run 前冻结且对 arm 不可见。当前
`make_frozen_configuration()` 与 case config 没有 schedule、trigger 或其 hash；第二代
controller 只是无条件 hard-code spawn restart。代码存在不等于本次 run 的 schedule
preimage 已在运行前冻结。需要 private frozen schedule receipt/hash，并在 controller
reopen 后以同一 preimage 触发。

### B-06：pre-crash Acceptance/finality 的时间不存在不可混淆证据

`SOURCE_DURABILITY_MARKER_V1` 中的
`precrash_acceptance_count=0/precrash_finality_count=0` 是 source 写入的数字。正式 frozen
owner DB 是最终快照：baseline 里已经含 post-crash Acceptance；它本身没有插入序号、前驱
head、cut binding 或 pre-crash snapshot。最终 artifact 无法区分：

1. Acceptance 确实在 migration 后写入；
2. 同一 signed Acceptance 更早已存在，只在后面补写 history event。

代码顺序支持情形 1，但独立 frozen artifact 没有 native temporal witness。应在 crash
marker 同一 durable cut 绑定 O_Q/O_V/O_P owner-store logical heads/counts，并让后续
Acceptance/finality 成为这些 heads 的 append-only extension。

### B-07：新的 removal projection 没有真正从 migrated runtime 移除 Target evidence

正在重构的版本新增 `migration-input-view.json`，在 removal world 将 visible capsule 的
`target_evidence` 设为 null。但 `migrated_runtime_worker` 在读取 projection 之前，仍直接：

1. 接收 `source_capsule_file` path；
2. 从该文件读取包含完整 receipt/readback 的 source capsule；
3. 通过同一个 `durable_path` 读取 `capsules.capsule_json` 的完整副本；
4. 把完整 `source_capsule` 传给 projection verifier。

所以 Target evidence 并未从 migrated process 可访问世界移除，只是当前 cooperative code
随后选择使用 `visible_capsule` 变量。一个同权限 migrated implementation 可以直接读取
刚刚得到的 `source_capsule["target_evidence"]`。

这不能作为 `REMOVE_TARGET_LEDGER_READBACK` 的证据必要性反事实。必须让 migrated process
只能访问 projection 与必要的 history/fence API，不能访问 controller-private full capsule
file/row；或使用真实权限域/独立 store 隔离。projection 文本
`WITHHOLD_TARGET_LEDGER_READBACK_AFTER_CUT` 本身也不应成为 evaluator case oracle。

### 已看到但尚未升格为 blocker

- source 在 marker 后进入无限等待，再由 parent `terminate()` signal 杀死；这是真实外部
  signal termination，不是 source 自行 return。但它仍是预设、受控 cut，不证明不可预告
  physical hard crash。最终 claim 必须持续保留这一限制。
- migrated code path没有调用 Target `apply()`，fence actions 也禁止 migrated `EXECUTE`；
  这一点需由新冻结 artifact 再验证。
- Target exact state包含 46 个 samples、offset/absolute minute、3kW tolerance、
  safety/noise 和 other-circuit 坐标；但正式接受仍要从新 formal Target DB 独立重算。

## 最终 root 独立复验

第一轮审计中的 suite、实现和 `ROOT-ACCEPTANCE.json` 均未被沿用。最终接受对象是 root
使用修正后的当前实现从零重新运行得到的：

```text
suite = suite-688917cb80094ed49d5f8e4195a811a8
summary internal SHA-256 =
  f73b9963feea432845907e40a5e42521a341895622834166fbc99529d3b9bb88
baseline disposition = RECOVERED_AFTER_MIGRATION
baseline postcondition count = 3
removal disposition = BOUNDED_UNKNOWN/UNRECONCILED_EFFECT
removal postcondition count = 0
```

### 阻断项关闭记录

| 原阻断 | 最终关闭证据 |
|---|---|
| B-00 worker 调用漂移 | `run_case` 使用当前 worker 参数；child 退出会被主动轮询并 fail fast，不再用 queue timeout 掩盖真实异常。 |
| B-01 stale/WAL artifact | 最终 suite 有 15 个独立 formal SQLite snapshots；root 逐文件读取 header bytes 18/19，全部为 `01/01`，formal 目录无 `-wal/-shm/-journal`。 |
| B-02 object 错绑 operation | frozen task、capsule 与 evaluator 均绑定 `object_id=VenueV:CircuitC7`，operation 保持独立 CE-001 identity。 |
| B-03 immutable PRAGMA 假绿 | runtime 与 evaluator 都直接读取 SQLite header；攻击测试把 header 改成 WAL 后，即使重算外层 hash 也会 fail closed。 |
| B-04 generic old-worker 角色扮演 | restart process 实际 reopen `source-state.sqlite3`，核对 runtime id、state identity 与 epoch，并用 source Ed25519 key 对预冻结 challenge 签名；外部 durable fence 仍拒绝 epoch 1 `EXECUTE`。 |
| B-05 restart 未预冻结 | restart schedule 与 challenge 在 run 前生成，hash 进入 frozen input、source capsule 和 controller generation-two 输入；reopen 后按同一 preimage 触发。 |
| B-06 pre-crash absence 自报 | cut 在 owner-native DB 上绑定 O_Q/O_V/O_P 的 logical head、entry count 和 hash；后续两份 Acceptance 与 finality 必须成为这些 heads 的签名 append-only extension。 |
| B-07 removal 仍可偷看 full capsule | full source capsule、source-cut DB 与 restart schedule 在 migration 期间位于 controller-private 外部目录；migrated-facing durable DB 在 spawn 前删除 full capsule row，worker 只收到 signed migration view。终局才把 private evidence 移回 artifact。注入 full capsule row 到 migrated-facing DB 的攻击即使重算 formal/artifact hashes仍被 evaluator 拒绝。 |
| B-08 source 两臂路径分叉 | 两个 source 都使用同形 opaque Target path、执行同一 full commit/readback/capsule prefix；retain/remove 只发生在 cut 后。pair evaluator 重算 source startup、history 和 capsule semantic projection 完全等价。 |

### root fresh-run 暴露并关闭的额外假失败

root 第一次从零运行得到 `suite-2463a4b89fb046749f0e4c08700171b3`，两个世界都被
`runtime_startups_blind_and_actual` 拒绝。根因不是 scenario leak，而是旧 evaluator 对完整
serialized visibility 做短字符串 `e6` 扫描；随机 opaque hex token 自然可能包含 `e6`，所以
旧 suite 的通过带有偶然性。

最终实现改为：

- argv、process name、environment 和 input fields 按语义字段检查；
- runtime handle 与 cwd 按严格 opaque hex 结构检查；
- 不对 opaque 随机标识做两字符 substring 推断；
- opaque token 恰含 `e6` 必须通过；
- argv/env/input field 中的真实 E6 或 case label 必须拒绝。

修正后 root 生成中间 suite
`suite-6bd6857604a344c794245cead4146a5a` 并重新独立评估通过。但继续比较两臂输入后，
又发现 migrated-facing view 与 controller event 暴露了 `projection`、`REMOVE` 和
`target_store_removed` 等反事实标签；即使 evaluator 没直接读取 arm id，这些字段仍可成为
实现或评估器的隐式 oracle。当前实现删除这些语义标签，使两臂的 migrated-facing schema
相同，只在 Target evidence/store 的真实可用性上不同，并新增相应攻击测试。

最终从 workspace root 运行攻击套件为 `25 passed`；冻结实现后，root 再从零生成
`suite-688917cb80094ed49d5f8e4195a811a8` 并独立评估通过。此前
`suite-df89501b4fb747f99938b93999be3f93` 是同一修正后的 fresh re-audit target，不作为最终
root fresh-run 凭据。

### 最终接受尺度

root 对最终 suite 重新确认：

- summary internal hash、两个 artifact internal hash 与 frozen input binding 全部可重算；
- baseline 与 removal 使用同一 frozen input；
- source startup、history prefix 和 capsule semantic projection 等价；
- baseline 只有 source epoch 1 的一个 accepted `EXECUTE`，migrated epoch 2 只执行
  `IMPORT_CAPSULE / VERIFY_TARGET / POSTCONDITIONS_ONLY`；
- old restarted epoch 1 `EXECUTE` 被 persistent fence 拒绝；
- Target ledger 中 occurrence、commit、receipt 与 readback 均为一个；
- 46 个样本逐项绑定 C7、空其他线路、功率容差、安全、噪声、时长与 deadline；
- baseline 的 O_Q/O_V Acceptance 和 O_P finality 都发生在 migration verification 后；
- removal 世界即使 source 在 cut 前完成同一 occurrence，也因 migrated 看不到 durable
  Target receipt/readback 而保持 bounded unknown，零 replay、零 Acceptance、零 finality；
- 15 个 formal DB 全部是 standalone DELETE `01/01`；
- root acceptance 的全部 bound files 无 hash drift。

因此本审计接受的只是：

```text
LOCAL_SYNTHETIC_E6_EXISTING_DURABLE_WORKFLOW_LEDGER_FENCE_SCOPED_SOLUTION
```

它证明成熟的 durable history、signed recovery capsule、Target receipt/readback、
persistent epoch fence、owner-head revalidation 与 post-crash Acceptance/finality 组合，
能够解决本地合成的受控 process-termination E6。

它不证明不可预告物理硬崩溃、物理供电、法律 Authority、OS 级 noninterference、恶意同目录
writer resistance、真实跨机 transport、生产长期可靠性、跨域普遍性或 V1/V2 整体解决。
