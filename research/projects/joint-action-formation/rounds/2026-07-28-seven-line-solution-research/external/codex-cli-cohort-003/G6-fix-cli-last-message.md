已完成 G6 CE-001 根红灯修复。

- O_S/O_E/O_Q/O_V/O_P 已拆为五个独立 `spawn` 进程和 state shard。
- method 只消费 canonical response bytes，不再持有 world/callable closure。
- O_Q/O_V 使用独立 exact Acceptance act；O_P 独立产生 obligation/finality。
- recovery 绑定 damaged occurrence，并验证真实 versioned target mutation/readback。
- C 新增 13 项攻击，发现并修复了 Acceptance payload PID 未绑定 transport PID 的真实红灯。
- 合同级 `ExactTaskSuccess` 改为 `NOT_COMPUTED_BY_G6`；本线只报告 `g6_line_local_closure`。

验证结果：

```text
新增根红灯攻击       13/13 PASS
完整回归             54/54 PASS
原有回归             41/41 保留
CorrectResolution       8/8
G6 line-local closure   6/8
Semantic                6/6
Failure injection       4/4
```

交付：

- [G6-fix-final.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/external/codex-cli-cohort-003/G6-fix-final.md:1>)
- [g6-effect/README.md](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g6-effect/README.md:1>)
- [新增根红灯测试](</Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g6-effect/tests/test_root_redlights.py:1>)

真实产品、生产 Effect、真人 Acceptance、付款 finality 均保持 `NOT_RUN`。未修改授权范围外文件。