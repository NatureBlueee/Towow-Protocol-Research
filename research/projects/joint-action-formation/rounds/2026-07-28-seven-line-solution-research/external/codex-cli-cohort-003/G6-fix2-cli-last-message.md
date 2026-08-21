已完成 G6 第三轮修复，写入范围仅为 `g6-effect/` 与本轮 final。

核心结果：

- response 绑定 current request/session、owner instance、实际 owner/client PID、nonce/ordinal、native state/ledger heads。
- O_E、O_Q/O_V、O_P 均对账当前 native records；跨 session replay、伪 Effect、伪 recovery、错误 Acceptance set/finality 全部 fail closed。
- evaluator 强制验证冻结 `TraceClosure`、actual plan/result hash；detached payload 不再可用。
- 仅输出 `g6_line_local_closure` / `g6_line_local_components`；`ExactTaskSuccess = NOT_COMPUTED_BY_G6`。

根会话最终验证：

```text
C 独立红灯       12/12 PASS
原回归           54/54 PASS
实现侧测试       12/12 PASS
全量             78/78 PASS
CorrectResolution  8/8
G6 closure         6/8
Semantic            6/6
Failure injection   4/4
```

完整交付记录：[G6-fix2-final.md](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G6-fix2-final.md)

真实产品、生产 Effect、真人 Acceptance、付款 finality 仍为 `NOT_RUN`；完整 CE-001 与 grader hostile blindness 仍为 `NOT_ESTABLISHED`。