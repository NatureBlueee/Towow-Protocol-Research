# T2 盲化任务：被拒绝的企业 AI 试点

状态：`TASK_TRUTH_V1`

用途：为 G2–G7 提供同一任务分母下的盲化输入、独立 oracle 真值和评价契约。它是从历史
设计案例与虚构 `sample_case` 派生出的研究仪器，不是真实企业事件或真实 Principal 证据。

## 物理隔离

- `blind/input.json`：唯一初始事实输入。它没有 reference countercondition、probe 结果、
  v2 方案或最终状态。
- `schemas/query-batch.schema.json`、`schemas/final-submission.schema.json`：方法可见的交互和
  最终返回形状；只规定字段，不包含 reference 答案。
- `oracle/truth.json`：只允许任务 controller 和独立 evaluator 读取。它保存各 Authority
  的局部真值、允许披露、reference path、后置状态与伪成功 mutation。
- `evaluator/spec.json`：评价要求、候选返回契约和逐项判据。求解方法可以知道评价维度，但
  不能读取 oracle 期望值。
- `controller.py`：controller-only 的确定性披露状态机。它只按
  `authority_id + request_type` allowlist 返回最小响应，并记录 receipt、轮次哈希和重放。
- `manifest.json`：controller 使用的字节哈希闭包；不要随 blind payload 发送。

物理分目录本身不是安全隔离。实际运行必须给 solver 建立只允许读取
`manifest.json:solver_payload_allowlist` 所列四个文件的文件白名单；`controller.py`、controller
state、manifest、oracle、测试和档案来源均不得进入 solver 权限域。同一工作区内拥有任意读取
权限的 solver 可以绕开盲化。

## 运行协议

1. controller 只发送 manifest 中四个 method-visible 文件；
2. solver 按 query schema 提交一轮查询；每条 query 只能含
   `authority_id / request_type / purpose / relation_version_ref / retention_scope`；
   `retention_scope` 只允许 `EPHEMERAL` 或 `RUN_ONLY`；
3. controller 按冻结的 `disclosure_transitions` 返回最小响应；未知 Authority、未知 request、
   错配 Authority 和格式越界都拒绝并留下 receipt，不提示正确答案；
4. 相同 run 的重复 query 返回 `REPLAY` 且不二次披露；相同 round 重放返回完全相同结果；
5. 下一轮必须携带上一轮 `round_hash`；controller state 和 receipt 不交给其他方法复用；
6. solver 的最终返回按 final-submission schema 组织，并绑定最后一个
   `controller_history_hash`；
7. 独立 evaluator 才读取 oracle，逐项给出 `PASS / PARTIAL / FAIL / UNKNOWN / NOT_RUN`；
8. 覆盖率不能覆盖任何 critical requirement 的失败。

不同 method/run 对相同合法查询获得相同 `decision / response_type / disclosed_fields /
response_hash`。Receipt ID 会绑定 method、run、round 和 query index，所以不是跨方法相同值。

Controller 示例：

```bash
python3 controller.py \
  --input /path/to/method-query-batch.json \
  --state /controller-only/path/t2-state.json \
  --output /path/to/method-response.json
```

`--state` 必须位于 solver 无权读取的 controller 权限域。不要把完整工作目录挂载给 solver。

## 证据边界

该任务可以检验：

- 冷启动关系构成与 material change；
- condition creation、discovery 和目标改写的区分；
- prospective capability qualification；
- Authority、Mandate、Stance、Commitment 与 Reservation 的非蕴含；
- Attempt、Effect、Adoption 与 Acceptance 的分离；
- 第二次运行、撤销、证据失效与 scoped reopen。

该任务不能证明真实企业采用、真人理解、法律充分性、商业频率或长期净价值。Reference v2
只是一个已知 witness，不是唯一合法解；能满足同一冻结 Q、V0、Authority 和证据要求的
不同方案可以通过。

## 定向校验

```bash
python3 validate_task.py
python3 -m unittest discover -s tests -v
```

校验只检查 JSON、哈希、必要字段、明显答案泄漏和 controller 的确定性行为，不实现候选解、
语义评分，也不代替独立评价。
