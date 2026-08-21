# G1 第二次根红灯修复

读取 `COMMON.md`、`G1-PROMPT.md`、`G1-FIX-PROMPT.md`、`G1-fix-final.md` 与
`ROOT-LIVE-AUDIT.md`。这是 G1 独立 CLI 主线的第三轮。

实际建立 A/B/C：A 重建 owner-origin 与 process identity 的证据边界；B 实现；C 不读 B
期待答案，主动测试 PID、origin、raw relay 与 worker attestation 的来源错配。只可修改
`g1-provenance/` 和本目录 `G1-fix2-final.md`。

根审计已经确认：

- 当前 owner records/operators 仍由 controller 从同一个 synthetic World 注入 owner child；
- owner READY、event origin 与 worker PID 主要是 child self-report；
- controller 没有把 owner/worker attested PID 与实际 `Popen.pid` 全部绑定；
- same-user hostile OS 仍是 RED，这是诚实边界，不要求伪装解决。

必须：

- controller 对 owner READY、每条 event origin、worker READY/attestation 的 PID 与实际
  `Popen.pid` 强制相等；伪报 `424242` 必须 fail closed；
- source/state/process instance 不能只靠两份可同时失真的自报字段；
- 明确把 owner source 标为 `CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE`，不得输出
  independent owner truth/origin；G1 handoff 仍只为 `CANDIDATE_NOT_COMMITMENT`；
- 保留 exact raw-byte relay、private canary 不入站、worker无 closure/import oracle、
  L/D 分母、E2 remove/reverse 和原 30 项风险覆盖；
- 输出 G1 namespaced line-local envelope，不含任何合同成功、Relation、Authority、
  Effect、Acceptance、Settlement；
- 新增 owner PID 错配、worker PID 错配、origin self-report 不一致、wrong source instance
  失效注入；
- 同 UID 绝对路径可读继续标 `RED_NOT_ISOLATED`，不得用绿灯覆盖。

真实 owner、hostile OS isolation、现实 discovery、完整 CE-001 仍为 `NOT_ESTABLISHED`。
