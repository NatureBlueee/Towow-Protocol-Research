G4 根红灯已在本地组件模型范围内关闭，最终记录见 [G4-fix-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G4-fix-final.md)。

关键结果：

- A/B/C 三个内部 Agent 均已实际运行。
- Effect 与 O_Q/O_V Acceptance act 已分离。
- Closure 验证唯一 owner、完整 tuple、effect occurrence、current revision、expiry、provenance 和完整 act payload。
- 拒绝、wrong episode/Q/effect、stale、duplicated owner 均不能闭包。
- 新增真正的 nonterminal readback：P1 resolution 为 `9 true / 1 false`，固定 worker 得到 `TP=9, FP=1`。
- E3A/E3B、wrong-object、double-submit、revoke 全部保留。
- matched no-interaction 仅标记本地必要条件，不再宣称方法优势。

C 的首次盲审另外发现了 provenance 可篡改和过期 commit 仍可执行两个红灯；修复后用原攻击复核通过。

最终验证：

- `19/19 PASS`，串行耗时 10.454 秒。
- `SELF_TEST_PASS`
- `runner.py --full`、`py_compile`、两份 JSON 校验通过。
- holdout 前后 SHA-256 均为 `d9bf6f2346f6bb5cfaba741071fae760e19df41c112ef9986665d6849a249536`。
- 10 cases：Effect `9/10`、Resolution `9/10`、Acceptance `2/10`；duplicate/unsafe/wrong-object reliance 均为 0，unreconciled 为 1。

完整失败历史保存在 [FAILURE_HISTORY.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g4-reliance/FAILURE_HISTORY.md)。本轮只写入允许的 G4 目录及最终记录，未修改 NOW、合同、机制、Scenario 或 `ROOT-LIVE-AUDIT.md`。

最重要的限制仍然成立：`Y_success` 只是首次 attempt Effect，不是 CE-001 `ExactTaskSuccess`；真实产品、真实供电、真人 Authority 与 Acceptance 全部仍是 `NOT_RUN`。