# Hidden World Foundation Contract

状态：`RUNNER FOUNDATION / SCENARIOS NOT RUN`

## 目的

本文件约束 `OwnerTopologyBroker` 与 `HiddenScenarioController` 的最小隔离能力。它只回答：

1. evaluator-private owner topology 能否与固定 arm-facing Broker surface 分离；
2. E3 两个 private outcome 能否共享同一 pre-readback arm view；
3. E4 alternative 是否只在 primary revoke 后经实际查询返回 opaque handle；
4. E6 crash schedule 是否能在 arm 不知情时按 native-event hash 与逻辑时间触发；
5. private receipt 的 payload、episode、controller 与 public view 绑定能否被核验。

它不证明 E3、E4 或 E6 的任务结果，也不构成剩余案例的总验收。

## Arm 公共表面

Hidden controller 不再实现第二套公开投影。它只接受
`visibility.ArmViewFactory` 已经按精确 schema 生成并经 `validate_arm_view` 验证的
arm view；固定 Broker surface 已在这同一个 schema 内。未知 arm 字段或未知 Broker
surface 字段一律 fail closed。

唯一 arm view 只允许：

```text
CE001_ARM_VIEW_V1
broker_surface = fixed endpoint/capability/version schema
```

`broker_surface` 只有固定的 opaque endpoint handle、能力字母表和 surface version。
新增 private manifest 字段不会自动进入 arm view。

以下内容不得进入 arm：

```text
semantic case/scenario label
expected disposition
candidate or topology hash
owner registry, owner count, principal relation
alternative identity, order, endpoint or role
commit/no-commit fork truth
crash cut, migration epoch, restart time or fault schedule
private receipt or private payload hash
```

## OwnerTopologyBroker

Broker evaluator-private registry 保存 owner instance、role、Principal、authority locus、
resource kind、discoverability condition、current head 与 epoch。Arm 只收到一个固定 endpoint。

E4 中：

- 初始查询只能返回 primary 的 opaque owner/resource handle；
- primary revoke 是 controller-private native event；
- alternative 只在 revoke 后的新 `DISCOVER` 中返回；
- opaque handle 到真实 owner 的映射只允许 evaluator-private resolve；
- topology receipt 必须先与精确 Broker instance、episode 和 arm view 绑定。

本实现不启动真实 owner process，也不证明 offer、授权、reservation 或执行成立。

## HiddenScenarioController

### E3 paired fork

两个 fork 复制同一份可直接交给 `BlindProcessLauncher` 的 startup arm view 和同一
submit-failure prefix。Prefix 作为后续公共 transcript 单独保存，不被塞回 startup schema。
private truth 分别记录
commit-before-readback 与 no-commit-before-readback。首次允许的语义差异是 exact Target
readback。

当前证据同时记录 raw equality 与 alpha-equivalence。这里没有模拟 Target readback，也没有
证明恢复策略正确。

### E6 schedule

Schedule 在 private packet 中冻结，至少绑定：

```text
trigger native-event sha256
trigger logical minute
crash cut
target epoch
old-runtime restart minute
```

只有 event hash 与逻辑时间同时匹配才生成一次 private trigger receipt。Arm view 中不出现
schedule、migration 或 restart 字段。

本实现没有真正杀死、迁移或重启 process；这些是 runner/BlindProcessLauncher 的后续职责。

## Private receipt

每个 receipt 使用 controller 进程内 Ed25519 key 签名，并绑定：

```text
receipt kind
controller instance and public key
episode binding
public view sha256
private payload sha256
```

Verifier 必须持有预期 controller、kind、episode 与 public view。以下攻击应失败：

- 修改 private payload 后保留旧 receipt；
- 把 receipt 移植到另一个 episode；
- 把 receipt 移植到另一个 controller；
- 改写 public view 后复用旧 receipt；
- 把 topology receipt 绑定到另一 Broker instance。

## 精确非目标

- 不启动 Agent、owner、Target、source/migrated/restarted runtime。
- 不实现 Target operation ledger、readback、Effect 或 Acceptance/finality。
- 不实现真实 crash、migration capsule、epoch fence 或 process recovery。
- 不证明 timing side-channel、FD inventory 或 OS process topology 已隐藏。
- 不证明 opaque handle 无法被跨运行流量分析。
- 不把本文件或测试通过解释为 E3/E4/E6 已运行、已成功或 Wave 015 总验收通过。
