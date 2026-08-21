# G4 第二次根红灯修复

读取 `COMMON.md`、`G4-PROMPT.md`、`G4-FIX-PROMPT.md`、`G4-fix-final.md`、
`ROOT-LIVE-AUDIT.md` 与 integration preflight。你是 G4 独立 CLI 主线的第三轮。

实际建立 A/B/C：A 重建 G4 真正有权输出的 reliance/reconciliation 范围；B 实现；C 独立
复核公开 provenance 可重算、service id 重复、未经过 owner process、PENDING/0kW/wrong-circuit/
unreconciled Acceptance 和合同字段直通。只可修改 `g4-reliance/` 和本目录
`G4-fix2-final.md`。

根审计实际击穿：

- O_Q/O_V 仍是同一 `OwnerTargetService` 的两个 Python 对象，同 service id 也可闭合；
- provenance 只是公开 SHA-256，完全不调用 `issue_act` 也能由 controller 构造两条 act 并
  `Y_acceptance=true`；
- `PENDING + 0kW + 其他线路有 Effect + exact_reconciliation=false` 仍能
  `Y_acceptance=true`；
- G4 输出 `Y_effect/Y_acceptance`，旧 preflight 曾 fail-open（根已先修 preflight）；
- G4 object id 与集成 canonical object id 不同。

必须：

- O_Q/O_V 使用不同 process/state/act source；controller 只能消费 transmitted bytes；
- owner act 需有 pinned local trust binding（签名或等价不可由 controller公开重算的来源），
  PID/source/process instance 与实际 child identity 绑定；
- Acceptance request 前必须验证 exact target-native Effect、SUCCEEDED、C7、3kW±5%、
  45min、no-other-circuit、deadline、O_E provenance 与 exact reconciliation；
- G4 最终只输出 P0/I/P1、attempt、readback、reconciliation、reliance calibration 等
  line-local 证据；禁止 `Y_effect/Y_acceptance/ExactTaskSuccess` 等合同级字段；
- 使用显式 adapter 对齐 `VenueV:CircuitC7`，不能悄悄字符串替换；
- 保留 ACK pair、expiry gating、revoke、wrong-object、resolution negative case 与
  当前 19 项风险覆盖；新增上述 root mutations；
- matched twin 继续只标 `LOCAL_STATE_MACHINE_NECESSARY_CONDITION_ONLY`。

真实 owner act、现实 Effect/Acceptance、一般 calibration、完整 CE-001 仍为
`NOT_RUN/NOT_ESTABLISHED`。
