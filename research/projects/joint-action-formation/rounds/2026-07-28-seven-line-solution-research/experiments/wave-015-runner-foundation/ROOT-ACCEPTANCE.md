# Wave 015 root acceptance

状态：
`COMPONENT_FOUNDATION_ACCEPTED / FULL_REMAINING_CASE_ADMISSION_PARTIAL`

这轮不是 E0/E2/E3/E4/E6 任务成功，也不是完整 runner。它回答的是：

> 扩展剩余案例前，arm 公共面、真实 child 启动、owner topology、Target mutation truth 和
> 隐藏场景控制，能否先形成一组彼此可组合、可攻击、可落盘复核的基础接口？

## 正式实际运行

- run：`foundation-2cceea49ee07d0790e48`
- bundle：
  `artifacts/foundation-2cceea49ee07d0790e48/foundation-bundle.json`
- bundle file SHA-256：
  `97f2551c7ac511848065f5bf8198e3cdaa6ac8f48e70c747a573d8726df5a178`
- internal bundle SHA-256：
  `8f4ff7825120518d38d23408bf65c5290ab716f605507ec8b2740d6496f54c0b`
- SQLite truth store：
  `artifacts/foundation-2cceea49ee07d0790e48/target-ledger.sqlite3`
- SQLite SHA-256：
  `9b2f160d15078e04b6503b14382be087f6077301569f6835044dd3997aaffc69`

冻结 artifact 的独立 root acceptance 会重算文件、bundle、SQLite 哈希，从冻结 controller
identity/public key 验证全部 Ed25519 private receipts，并从 SQLite 原始 stored identity
重新验证 HMAC receipt/readback。

## 实际结果

### 唯一 arm view 与真实 child

- `ArmViewFactory` 只接受精确 public task schema；
- Broker endpoint/capability/version 已进入同一唯一 `CE001_ARM_VIEW_V1`，不存在第二套
  Hidden-controller view；
- 未知字段、嵌套 private 字段、semantic label、private scalar、candidate hash、padding
  和 Broker surface 扩字段均 fail closed；
- `BlindProcessLauncher` 实际启动 `spawn` child；
- child 实际看到的 view 与 E4 controller 冻结 view 完全相同；
- parent 的 argv/cwd/name/env 被清理后，child 回传实际可见面；
- E3/E4/E6 标签、alternative Principal 与 private topology 不在该可见面。

### Hidden controller 与 Broker

- E3A/E3B 使用同一个 launcher-compatible startup view 和同一个 pre-readback public
  prefix；raw equality 与 alpha-equivalence 均为 true；
- E4 初始查询只返回 primary opaque handle；private revoke 后重新查询才返回另一个
  alternative opaque handle；
- E6 schedule 只在 exact native-event hash 与 logical minute 同时匹配时触发一次；
- topology、schedule、fork truth、route、revoke、trigger 都由 controller-private
  Ed25519 receipt 绑定 episode、public view 与 private payload；
- receipt 可由持有冻结 controller identity/public key 的独立 verifier 重算，不依赖原
  controller 内存对象。

### TargetOperationLedger

这是本轮最强建设性结果。成熟 SQLite `BEGIN IMMEDIATE` + CAS + one-shot capability +
stored authenticated receipt/readback 在本地数字 Target 边界实际得到：

- H 先提交相同终态：`H=COMMITTED`；
- A4 随后提交：`ALREADY_SATISFIED`；
- A4 `mutation_applied=false`；
- A4 receipt/readback 指向真实 `commit_actor_id=H`；
- 两个独立 SQLite connection 从同一 expected version 并发竞争，结果恰为一个
  `COMMITTED`、一个 `CONFLICT`；
- exact replay、capability replay、request rebind、actor relabel、receipt transplant 和
  readback detach 攻击均被拒绝。

因此可以登记：

```text
EXISTING_MATURE_TARGET_LEDGER = POSITIVE_SCOPED_SOLUTION
DIRECT_COMMIT_ATTRIBUTION_WITHIN_LOCAL_DIGITAL_TARGET_BOUNDARY = CLOSED
NOVEL_TARGET_MUTATION_MECHANISM_NECESSITY_FOR_THIS_RESIDUAL = CLOSED
```

这正是通爻的正向成果，不因 SQLite、CAS、HMAC 和 capability 都是现成技术而降级。

### E6 actual runtime foundation probe

冻结 bundle 现在包含一个独立的、作用域受限的 E6 runtime probe：

- source、migrated、old-runtime-restart 是三个不同 PID、不同进程内 Ed25519 key 的真实
  `spawn` process；
- 三者由同一个 `E6BlindProcessLauncher` 实例和同一个 generic worker 启动，launcher
  instance、worker-code hash、arm-view schema 与逐字 view hash 一致；
- crash schedule 只存在于独立 `HiddenScenarioController` private packet，不出现在三个
  runtime 的 arm view、argv、cwd、process name 或 environment；
- source 实际签出与冻结 schedule 完全匹配的 native-event hash 和 logical minute；
- controller 生成 exact trigger receipt 后，source 先受控签出并交接 capsule，随后由
  controller 外部终止，冻结 exit code 为 `-15`；
- fence 从 epoch 1 推进到 epoch 2；migrated runtime 的
  `RECOVER_POSTCONDITIONS_NO_EXECUTE` 请求得到 `ACCEPTED`；
- old-runtime-restart 是另一只实际 spawn process，其 epoch 1 `REPLAY_EXECUTE` 请求得到
  `REJECTED_STALE_EPOCH`；
- capsule 绑定 source identity、episode、operation、public-view hash、source epoch、
  native event 与 history head；跨 episode transplant 和字段 rewrite 被拒绝；
- runtime 自报执行或 fence receipt 移植不能覆盖 signed fence decision。

这只关闭了“统一 blind launch + exact hidden trigger + capsule/fence 的本地进程闭环”这一部分
准入，不是 E6 任务成功。

## root 攻击改变了什么

三条独立实现最初分别 12/12、8/8、11/11 通过，但不能直接合并为成功。

1. Hidden controller 自己维护了第二套 allowlist，对未知字段静默丢弃；这会绕开
   `ArmViewFactory` 的 fail-closed 合同。
2. Hidden controller 产出的复合 view 无法交给 `BlindProcessLauncher`；组件各绿但系统
   不可运行。
3. E3 public prefix 被塞回 startup view，破坏唯一 launcher schema。
4. private scanner 只看整包与整包哈希，可能漏掉嵌套 Principal/resource scalar。
5. private receipt 只能由原 controller 对象方法验证，持久化后缺少独立验证入口。

当前实现将这些冲突收敛为一个 arm schema、一个 Broker surface，并新增 nested scalar/hash
攻击、跨组件真实 spawn、Broker transplant 和 persisted independent verifier。

当前验证：46/46 component/cross-component/attack，加 1/1 frozen actual artifact root
acceptance，共 47/47；语法编译检查通过。root acceptance 独立重验 E6 process identity、
schedule trigger、capsule、fence advance、migrated/old decisions 与 visible-surface
非泄漏。

## 仍未通过完整扩案准入

以下不能从 foundation 推出：

- E3A/E3B 尚未实际启动两个 Agent/Target world，也没有实际 signed negative readback、
  retry、reconcile、duplicate-effect 后置条件；
- E4 没有真实 owner process、offer、Authority、reservation、Target execution、
  Acceptance 或 finality；
- E6 probe 没有 Target process、Target operation ledger 或 signed positive/negative
  readback；foundation 中另一个数字 Target ledger 不能冒充 E6 runtime 的 Target；
- source 是在 exact trigger 后先受控导出 capsule、再被 controller 终止，不是无预告 hard
  crash，也没有证明 crash cut 前后的真实 durable history；
- E6 fence 只在本次 controller 内存中维持 current epoch，尚未跨 controller crash 或机器
  重启持久化；
- migrated runtime 没有真实 migration transport、owner-head revalidation、Acceptance 或
  finality，也没有证明其 history 是完整 source prefix extension；
- old-runtime-restart 是一只新进程携带 stale epoch 请求，不是原 OS process 恢复 crash 前
  内存；
- E6 的异步 `E6BlindProcessLauncher` 是 probe-local 的最小扩展，尚未并入稳定 foundation
  launcher 公共接口；
- inherited FD inventory 只记录，尚未证明固定或不可形成 topology side channel；
- timing、traffic volume 与 hostile same-user 不可区分未建立；
- Target ledger 的 HMAC key 与数据库在同一权限域，恶意 DBA/同用户协调改写不在威胁模型；
- capability issuer 的法律 Authority、物理 Effect、Acceptance、Settlement 与 V1/V2
  整体问题仍开放。

因此只能登记“接口基础接受”，不能把
`FULL_REMAINING_CASE_ADMISSION`、`E3/E4/E6_SUCCEEDED` 或 `CE001_COMPLETE` 写成 true。

## 下一条高价值行动

优先用这套基础实际运行 E3A/E3B paired world。它比先做显而易见的 E0 更有区分力：同一
ACK-lost prefix 下，只有 Target signed positive/negative readback 能决定 reconcile 还是
safe retry。运行必须实际产生：

- E3A：已有 commit，只 reconcile，零第二 mutation；
- E3B：current-head exact negative readback 后 safe retry，最终只有一个 mutation；
- wrong-object decoy 不能满足 exact query；
- 两个 arm 在 readback 前共享同一可见 prefix；
- A0/A1/A3/A4 等公平臂使用同一个 Target ledger primitive。

E0 platform-direct 与公平强中心可以并行实现；若成熟平台在 U/D 条件完整解决，直接登记
正向方案。
