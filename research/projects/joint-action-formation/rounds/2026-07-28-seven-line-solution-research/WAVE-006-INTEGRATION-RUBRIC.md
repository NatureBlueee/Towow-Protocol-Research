# Wave 006 integration rubric

Shared task SHA-256:
`0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`

三个实验进入跨线综合前必须同时满足：

1. manifest 绑定上述 shared task bytes；
2. 竞争策略面对相同事件序列与可见信息；
3. 评分同时包含 false positive、false negative、成本和恢复，不只奖励拒绝；
4. 现有/中心/简单方案胜出时直接记为正向结果；
5. 至少有一个最强反例能推翻漂亮但无 postcondition 的候选；
6. `UNKNOWN / REFUSE / ABSENT` 不合并；
7. 局部 PASS 只改变本研究线的 scoped claim；
8. 合成结果不冒充现实频率、真人接受或生产保证。

## G2 最小验收

- A/B/C 三组除 relation layer 外完全相同；
- 一次性任务不会被强制物化为持续关系；
- reuse success 与 stale/withdrawal misuse 都计入；
- 若双 ACK 已充分，RelationVersion 无增益应被明确保留为结果。

## G4 最小验收

- 四策略不能看到不同未来；
- probe success 后 revocation 必须构成辨别例；
- missed valid action 与 false reliance 同时计算；
- `operation success ≠ capability ≠ reliance ≠ business effect` 可由输出重建。

## G6/G7 最小验收

- effect ladder 每一级有独立 authority/postcondition；
- 上一级 self-claim 不能晋升下一级；
- replay、migration、re-authorization 使用同一 drift cases；
- exact replay 与 material semantic change 分开；
- anchor fork 和 beneficiary refusal 不被 schema alias 掩盖。

## 综合规则

不以三条线同时偏好某个对象作为结论。综合只回答：

- 哪种条件下最简单现有组合已经足够；
- 哪个 residual gap 仍能改变真实决策；
- 哪个机制只是在补 evaluator/表示契约；
- 下一实验应优先区分哪两个竞争解释。
