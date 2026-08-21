# G6 CE-001 根红灯修复任务

你是 G6 独立 Codex CLI 主会话的第二轮。完整读取 `COMMON.md`、`G6-PROMPT.md`、
`ROOT-LIVE-AUDIT.md`、`G6-final.md`、`g6-effect/README.md` 和 `ATTACK.md`。

实际建立 A/B/C：A 重建 Effect/Acceptance/Settlement truth domains，B 实现，C 在不知道
期待答案的条件下尝试 owner-response transplant、closure/reflection oracle 读取、重复
Acceptance owner、伪 O_P finality 和 bogus recovery。

只可修改 `g6-effect/` 和本目录 `G6-fix-final.md`；不得修改其他路径。

必须：

- O_S、O_E、O_Q、O_V、O_P 使用独立 process/state，不得闭包到同一 `PrivateWorld`；
- method 只消费各 owner 的 transmitted response bytes，不能通过 closure/reflection 取 world；
- O_Q/O_V Acceptance 必须是两个唯一 owner 的 exact act，O_P 独立产生 obligation/finality；
- evaluator 不得与 owner simulator共享 `EXPECTED_RESOLUTION`；由独立冻结 grader 输入评分；
- recovery 必须绑定 damaged occurrence，并由 target-native state change + readback 证明；
- 合同级 `ExactTaskSuccess` 必须保留 deadline、operation、Authority、安全约束、Acceptance、
  Settlement；若本线无法独立证明，就改成 line-local 名称，留给集成 evaluator重算；
- 保留 wrong-target harm、response transplant 与当前 41 项回归。

真实产品、生产 Effect、真人 Acceptance 与付款 finality仍为 `NOT_RUN`。
