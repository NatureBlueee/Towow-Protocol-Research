# Wave010 X1 outcome-contract v1 candidate

状态：`CANDIDATE_NOT_RUN / CONFORMANCE ONLY / NO X1 RUN`

本目录只修复 v0 中三个已确认的机器契约缺口：

1. measurable policy 存在而 actual arm 失败时，输出
   `ACTUAL_POLICY_MISS`，不能伪装成 `BOUNDED_UNREACHABLE`；
2. Principal/owner 正式批准的 material goal change 输出
   `AUTHORIZED_NEW_EPISODE`，controller 代签或偷换输出
   `INVALID_SUBSTITUTION`；
3. G3 receipt 必须内嵌并哈希绑定 `C/N/E/T/V`、六个 R 坐标、inventory
   completeness、counterfactual 与 task diff。

`task_diff` 不只保留 before/after task hashes 和字段名，还内嵌有序的
`path/before_value/after_value` 变化；owner authorization 或 controller claim 只能解释这份
明确 diff，不能以一张通用 receipt 替代 diff 本身。

`validator.py --write-contract` 从未修改的 v0 机械生成相邻的 v1 文件，并重新计算 schema
与 reason-registry preimage hashes。测试使用的 run/world/arm 全是 conformance fixture，
不是 X1 实验运行，也不形成任何 coverage、score 或证据晋升。

兼容边界：

- v0 文件保持不变；
- 不涉及三个缺口的 v0 outcome，补齐 G3 embedded body 后可以按 v1 重新 finalize；
- 使用 `BOUNDED_UNREACHABLE/G3_NO_ACTUAL_POLICY_PATH` 或
  `INVALID/G3_INVALID_SUBSTITUTION` 的 v0 outcome 必须重新分类，不能原样进入 v1；
- v1 仍为 `CANDIDATE_NOT_RUN`，不得据此激活 runner、X2 或正式机制状态。
