# Wave 020 — E6 Migration-Replay 可执行合同

状态：`EXECUTABLE LOCAL SYNTHETIC / ROOT REQUIRED`

## 问题

检验成熟组合：

```text
durable workflow/history
+ Wave015 TargetOperationLedger/readback
+ portable signed recovery capsule
+ owner-source replay
+ persistent SQLite epoch/fence
```

能否在 source 已唯一完成 exact local-digital occurrence、但尚未形成 O_Q/O_V Acceptance 和
O_P finality 时发生 runtime crash，随后由不同 runtime 在不重放 Effect 的条件下恢复这些
后置条件。

完整解决应登记为现有技术正向方案，不要求额外协议创新。

## 冻结 exact task

- `Q@v1`，`object_id=target_id=VenueV:CircuitC7`；
- `operation_id=CE001:VenueV:CircuitC7:3kW:45m`，不得把 object 与 operation 混同；
- `effect_start_minute=0`、deadline 90；
- 46 个 `offset_minute=0..45` 连续 Target-native samples；
- `observed_at_minute = effect_start_minute + offset_minute`；
- 每个样本 `2.85..3.15kW`，safety/noise 均 true；
- `other_circuits_energized=[]`；
- source 必须获得唯一 `COMMITTED` receipt 和 attached authenticated readback。

任一坐标缺失不得成功。

## Crash 与 durable cut

source 是真实 `spawn` process。它先写 Target occurrence/readback，再将 Ed25519-signed
source history prefix 和 recovery capsule：

1. 以文件 `fsync` 写入外部 store；
2. 以 `synchronous=FULL` SQLite transaction 写入外部 durable DB；
3. 写入 `CAPSULE_DURABLE` marker；
4. 等待，但不得写 Acceptance 或 finality。

controller 只轮询外部 SQLite marker，不创建 source result queue；观察 marker 后先从
O_Q/O_V/O_P native owner stores 冻结 cut-time head、event head 与零 Acceptance/finality，
再调用 process termination。后续 owner 结果必须是该 cut head 的 append-only extension。
Crash event 必须晚于 marker，source exitcode 必须为 signal termination。
这证明受控的 process termination cut，不证明不可预告的物理掉电。

## Migration

- migrated runtime 使用不同 PID、runtime id、Ed25519 key、state DB 和更高 epoch；
- source full capsule 与 source-cut DB 留在 controller/evaluator-private store，不进入
  migrated runtime-facing 目录或 shared durable capsule table；
- cut 后 controller 以独立 Ed25519 key 签 migration input view。baseline view 披露完整
  source capsule；removal view 不披露 Target ledger/readback；
- migrated runtime 只能读取 signed view、shared continuation history/fence、owner current
  heads 和（baseline 才存在的）retained Target DB；
- migrated runtime 必须主动查询 runtime-facing capsule table并原生记录结果为零；不得仅靠
  代码选择“不读”来声称隔离；
- 它只允许 `IMPORT_CAPSULE / VERIFY_TARGET / POSTCONDITIONS_ONLY`；
- migrated runtime 的 accepted `EXECUTE` 必须为零；
- history 必须从 capsule 的 source head 逐项 append，不得 rewrite/fork；
- O_Q、O_V 由各自 owner process 在 migration verification 后签 Acceptance；
- O_P process 只在两份 Acceptance 存在后签 `RECOVERED_AFTER_MIGRATION` finality。

## Persistent epoch/fence

source epoch 为 1，migrated epoch 为 2。第一代 controller 在外部 SQLite 将 current epoch
持久化为 2 后以非零 exit 模拟 controller crash；第二代 controller 从同一 DB reopen，再
真实 spawn old runtime restart。Restart schedule preimage 必须在 source 启动前冻结，只把
commitment 带入 source capsule。重启进程必须实际 reopen 独立 source-state DB，以 source
private key 对 schedule challenge、runtime identity、state identity 与 epoch 签名认证，再从
durable registry 恢复 epoch 1 credential；其 `EXECUTE` 必须获得
`REJECTED / STALE_EPOCH`。仅内存 fence、
reopen 后丢失或 old epoch accepted 都使 run 无效。

## Blind startup

runtime argv/process name、空 temp cwd、最小固定 env 和 input-field schema 必须可重建。启动
面不得出现 E6、migration-replay、Wave020、crash cut、target epoch、restart schedule、
expected outcome、removal 或 recovered result label。Source 与 migrated runtime 可以读取
真实 API/DB 返回，但不能收到 evaluator oracle。

## Removal counterexample

`REMOVE_TARGET_LEDGER_READBACK` 与 baseline 共享 frozen task、runtime/owner keys、epochs、
owner heads 与 restart schedule。两臂 source 都只看到同形 opaque temp Target handle，
执行相同 synthetic occurrence，并生成结构和语义相同的 full source capsule/prefix。
只有 cut 后 controller 才在 baseline retain Target DB，在 removal 删除它并签署不披露
Target ledger/readback 的 migration view。独立 evaluator 必须比较两臂的规范化 source
prefix、source/old-restart startups 与 capsule 语义 hash，阻止 source 自选实验臂。

正确结果只能是：

```text
BOUNDED_UNKNOWN/UNRECONCILED_EFFECT
replay count = 0
O_Q/O_V Acceptance count = 0
O_P finality count = 0
```

不能依据 source history 中不可展开的 hash 假定 Effect 已发生，也不能执行第二次 Effect。

## 独立接受

`independent_evaluator.py` 不 import runtime 或 runtime summaries。它直接验证：

- controller-private source capsule/source-cut DB/signature/store binding；
- migrated runtime-facing shared DB 中 full capsule 行恰为零，以及 signed view 的披露边界；
- source prefix 与完整 signed append-only history；
- Target DB HMAC、receipt/readback、commit actor、唯一 occurrence 和 46 samples；
- owner DB current heads、Acceptance/finality signatures 与时序；
- source/migrated/old-restart startup visibility 与真实不同 PID；
- controller crash/reopen rows、persistent fence 和 stale rejection；
- formal SQLite backup 的 physical/logical hash、header bytes 18/19=`01/01`、integrity、
  `journal_mode=DELETE` 与无 `-wal/-shm/-journal`。

攻击测试必须覆盖：pre-crash Acceptance、migration EXECUTE、duplicate occurrence、capsule
rewrite/transplant、history rewrite/fork、owner-head stale、fence 只在内存或 reopen 丢失、
old epoch accepted、no-ledger 仍成功。

只有 `ROOT-ACCEPTANCE.json` 对当前 summary、capsule、全部 DB、实现、evaluator 和本合同的
字节 hash 全部绑定且 decision=`ACCEPTED_SCOPED` 时，才登记：

```text
E6_EXISTING_DURABLE_WORKFLOW_LEDGER_FENCE = POSITIVE_SCOPED_SOLUTION
```

不证明：不可预告物理硬崩溃、物理 Effect、法律 Authority、OS 级 noninterference、恶意
同权限本机进程枚举/读取 controller-private 临时目录、恶意同目录 writer resistance或
跨实现普遍性。
