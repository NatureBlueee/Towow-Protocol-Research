# G6 第二次根红灯修复

读取 `COMMON.md`、`G6-PROMPT.md`、`G6-FIX-PROMPT.md`、`G6-fix-final.md` 与
`ROOT-LIVE-AUDIT.md`。这是 G6 独立 CLI 主线的第三轮。

实际建立 A/B/C：A 重建 owner response currentness 与 evaluator 证据链；B 实现；C 不读
B 期待答案，测试跨 session response replay、来源错配、无 native state 的 response bytes、
O_P obligation 错配和 recovery readback 同源失真。只可修改 `g6-effect/` 和本目录
`G6-fix2-final.md`。

根独立复核已发现：

- 仅构造格式正确的 O_E effect response bytes，即使 native O_E 没有 occurrence/target
  state，也可能得到 line-local closure；
- O_Q/O_V response 可跨 session 重放，新 session owner ledger 为空仍可能闭合；
- recovery_state 与 target_state 同时由无 native mutation 的来源提供时，实际 C8 仍
  `POWERED@v1` 也可能被解释为 recovered；
- O_P obligation/finality response 若不绑定 current request hash、current process 与 native
  ledger，可能闭合错误 scheme；
- 当前 verifier 需要进一步绑定 actual request、transport envelope、current OwnerClient
  PID/session、native ledger head 与 evaluator trace。

必须：

- 每条 response 绑定 canonical current request bytes/hash、owner endpoint、session id、
  actual process PID、state/ledger head、nonce/ordinal，并由 current client 验证；
- 跨 session、跨 owner、跨 endpoint、跨 request 的 bytes 全部 fail closed；
- O_E effect/recovery 必须能回到 current native ledger/state transition/readback，
  evaluator 不能只验证 response payload；
- O_Q/O_V Acceptance 必须与各自 current native act ledger 对账；
- O_P obligation/finality 必须与 current O_P native ledger、exact Acceptance set、effect、
  scheme/phase 和 request 对账；
- evaluator 只消费冻结 trace/receipt closure，不接受 detached response payload；
- 保留五 process/state shard、raw bytes transport、wrong-target damage、原 54 项风险覆盖；
- 继续只输出 G6 line-local closure，合同 `ExactTaskSuccess` 为
  `NOT_COMPUTED_BY_G6`。

真实产品、生产 Effect、真人 Acceptance/付款、完整 CE-001 仍为
`NOT_RUN/NOT_ESTABLISHED`。
