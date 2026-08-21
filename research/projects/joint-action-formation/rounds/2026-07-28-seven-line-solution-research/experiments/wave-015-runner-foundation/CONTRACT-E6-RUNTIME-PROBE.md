# E6 Runtime Probe Contract

状态：`RUNTIME FOUNDATION PROBE / FULL E6 NOT RUN`

## 本 probe 要关闭的窄问题

本 probe 检查以下运行时基础是否能够在真实本地进程中同时成立：

1. source、migrated、old-runtime-restart 是三个不同的实际 `spawn` process；
2. 三者由同一个 `E6BlindProcessLauncher` 实例启动，使用同一 generic worker、同一
   `ARM_VIEW_SCHEMA` 和逐字相同的 arm view；
3. crash schedule 只存在于 `HiddenScenarioController` 的 private packet；
4. controller 只在 exact native-event hash 与 logical minute 同时匹配时触发；
5. source 在触发后导出与 source identity、episode、operation、view 和 event 绑定的 capsule，
   随后被 controller 外部终止；
6. migrated runtime 只能凭 current epoch fence receipt继续 postconditions；
7. old runtime restart 的 stale epoch replay 被同一 controller 生命周期内的 epoch
   fence 拒绝。

这是一项 runner foundation probe，不是 E6 成功实验。

## Blind launcher 的局部扩展

Foundation `BlindProcessLauncher.launch()` 是同步接口：child 返回一次结果后立即退出，无法在
native event 后由 controller 外部终止。

`e6_runtime_probe.py` 因此只在本文件作用域内定义
`E6BlindProcessLauncher(BlindProcessLauncher)`：

- 复用 `validate_arm_view`、固定 argv、最小环境、空 cwd、opaque process name 和 spawn lock；
- 把 child 保持为异步 command/event loop；
- 返回可终止的 process handle；
- source、migrated、old restart 均走这一个扩展类和同一个 generic child entry。

它没有修改 foundation launcher，也不声称该异步扩展已经成为稳定公共接口。

## 可见性

三种 runtime 的初始 arm view 必须逐字相同，并符合唯一
`CE001_ARM_VIEW_V1` schema。以下内容不得出现在 arm view 或 launch visible surface：

```text
E6 semantic label
crash cut
trigger event hash
target epoch
old restart minute
expected fence result
```

Runtime 在生命周期推进后可以收到当前 capsule、epoch 请求或 fence decision；这不等于允许
它在初始输入中预知未来 crash schedule。

## Native event 与 capsule

Schedule 冻结 exact native-event body hash 和 logical minute。Source 实际进程签出该 event；
controller 用 `HiddenScenarioController.maybe_fire_e6()` 生成 trigger receipt。

Capsule 由 source 进程内 Ed25519 key 签名，并绑定：

```text
source runtime instance / PID / public key
episode instance
operation
public arm-view hash
source epoch
native-event hash
history head
pending obligations
```

跨 episode、operation、view 或 source key 的 transplant，以及 capsule 字段 rewrite，必须失败。

## Controller epoch fence（内存态）

Fence 是 controller-side 的最小内存态 register，登记 launcher 返回的 runtime identity。
每个 runtime 用自己的进程内 key 签出 fence request。Fence receipt 绑定 request hash、
episode、operation、requested/current epoch 与 action。

- migrated runtime 请求 epoch 2 的 `RECOVER_POSTCONDITIONS_NO_EXECUTE`，应被接受；
- old restart 请求 epoch 1 的 `REPLAY_EXECUTE`，应得到 `REJECTED_STALE_EPOCH`；
- runtime 自报 `executed=true` 不能覆盖 fence receipt；
- receipt 移植到另一 request 必须失败。

这里的 “accepted” 只表示 fence 在当前 controller 生命周期内允许继续 postconditions，
不表示发生了真实 Effect，也不表示 durable recovery 已建立。

## 仍未闭合

- 没有真实 Target process、Target operation ledger、46 个样本或 signed readback。
- Capsule export 发生在 controller 外部终止 source 之前，是受控 handoff，不是不可预告的
  硬崩溃恢复。
- Fence 当前是本次 probe controller 内存对象，未跨 controller crash 持久化。
- 未实现真实 migration transport、owner-head revalidation、Acceptance 或 finality。
- 未证明 migrated history 是完整 source prefix extension。
- 未证明 old OS process 使用其原 crash 前内存；old restart 是新进程携带 stale epoch 请求。
- 未覆盖 hostile same-user process、时间侧信道、FD 数量同构或并发 spawn 干扰。
- 不得把测试通过表述为 E6 已恢复成功、完整扩案准入闭合或 Wave 015 总验收通过。
