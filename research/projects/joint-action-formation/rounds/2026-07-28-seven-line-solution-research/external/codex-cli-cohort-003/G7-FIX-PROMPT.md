# G7 CE-001 根红灯修复任务

你是 G7 独立 Codex CLI 主会话的第二轮。完整读取 `COMMON.md`、`G7-PROMPT.md`、
`ROOT-LIVE-AUDIT.md`、`G7-final.md`、`g7-evolution/README.md`、
`g7-evolution/C-adversarial-audit.md` 以及
`../../experiments/wave-012-ce001-power-restoration/integration-preflight/README.md`。

先实际建立 A/B/C：A 独立重建 owner/runtime/lineage 权威边界；B 实现；C 在不知道 B 方案
的前提下攻击合并 owner、controller 注入 Authority、同进程假迁移、volatile fence、
capsule fixture hash、旧 runtime 假重启、history rewrite 与合同字段直通。必须保留三者
身份和原始红灯，不能用多 Agent 共识作证。

只可修改 `g7-evolution/` 和本目录 `G7-fix-final.md`；不得修改其他路径。

当前 33/33 不是本轮完成条件。根审计已确认：

1. 当前 runtime 仍直接传入 `authority_allowed=True`，target 没有消费 G5 风格的 current
   Authority receipt set；
2. O_Q/O_V/O_P 是同一进程内对象，标识分离不等于独立 owner source；
3. E6 source/target coordinator 与 Effect target/fence 多为同一 Python 对象图中的
   simulator，尚不能称真实 process/state boundary；
4. 输出仍直接生成 `ExactTaskSuccess / CorrectResolution / RecoveryToValue` 等合同级
   结论，会被 integration preflight 拒绝；
5. hidden safety-liveness pair 已诚实为 `NOT_CONSTRUCTED/NOT_RUN`，必须继续保持，除非
   真正构造相反 final requirement 的 pair。

必须：

- O_Q、O_V、O_P 使用独立 process/state/act source，通过实际 transmitted bytes 返回
  exact Acceptance 与 post-Acceptance finality；重复 owner、response transplant、
  stale/wrong episode/Q/effect 必须失败；
- target dispatch 不再接受 controller boolean。它必须读取并验证 current Authority
  receipt set，记录 target-native consumption event/hash；wrong/stale/tampered receipt
  fail closed；
- E6 source runtime 与 target runtime 至少是不同 process、不同 durable state path、
  不同 runtime identity；实际终止 source，启动 target，再实际重启 old source，用外部
  fence owner 的新 epoch 拒绝旧提交；
- capsule、source/target state、history prefix、owner evidence 与 effect occurrence 都从
  实际传输/落盘 bytes 计算 hash，不得用 fixture 常量代表已验证；
- G7 只输出 line-local evolution/reopen/migration/lineage evidence；不得输出或透传
  `ExactTaskSuccess / CorrectResolution / RecoveryToValue / Authority / Effect /
  Acceptance / Settlement` 或同义合同结论。未来独立 evaluator 才计算合同成功；
- 产出可进入 integration preflight 的 G7 namespaced envelope，且 E6 migration 必须包含
  distinct source/target runtime/process/state boundary、actual restart、old-epoch fence、
  lineage 与 owner-source recovery 证据；
- 保留 E4 alternative recovery、E6 effect/acceptance gap、append-only、exact effect
  reconciliation、field-loss fail closed、冷/复用成本未测和 semantic independence 未建立；
- 原 33 项测试的风险覆盖不得删除或改弱；新增 owner/source transplant、process identity、
  receipt consumption 与合同字段扫描攻击。

真实产品、真人 owner、法律 Authority、物理 Effect、生产 split-brain、跨产品 portability、
full-lifecycle net value 与完整 CE-001 解仍为 `NOT_RUN/NOT_ESTABLISHED`。完成后写
`G7-fix-final.md`，报告实际进程、状态路径、攻击、测试、残余边界和精确 integration
envelope。
