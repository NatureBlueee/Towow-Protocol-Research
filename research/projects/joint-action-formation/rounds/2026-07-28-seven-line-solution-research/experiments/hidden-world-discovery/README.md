# T1 Hidden-world discovery evaluator

这是 G1/T1 的一个高保真合成评测夹具。它只回答一个有界问题：

> 在方法不能读取完整世界、不能预设一张完整 Agent 目录、且披露受 authority 和
> policy 约束时，它能否发现当前可发现的互补机会，同时诚实地区分
> `UNKNOWN`、`REFUSE`、`ABSENT`、陈旧信息和“存在但在当前 policy 下不可发现”？

它不是候选解决方案，不实现发现算法，也不证明任何协议已经解决 V1/V2。它提供的是一个
与候选技术分离的 latent world、一个只供 controller/scorer 使用的 oracle，以及一个
确定性 evaluator。`fixtures/scorer_conformance_receipt.json` 仅证明评分器能识别一份人工
构造的合规回执；不得把它当成任何候选方法的实验结果。

## 文件边界

- `controller_input.json`：包含 public view 与全部 local view 的 controller-only 源文件，
  永远不能直接交给候选方法。
- `packet_builder.py`：确定性路由器。它把 controller source 物理拆成一个 coordinator
  packet 与每个 holder 各自的 local packet；不读取 oracle，也不生成发现结果。
- `submission_schema.json`：唯一 method-visible 的提交契约。候选方法使用自己的
  `detection_id`，并提交可观察的主体、方向、证据或 `claim_key`。
- `oracle_truth.json`：隐藏世界、冻结条件、预期状态、authority、policy 与 witness。
  只允许 controller/evaluator 读取。
- `evaluator.py`：确定性评分器。正式盲跑时应与 oracle 一起留在 scorer 权限域。
- `fixtures/scorer_conformance_receipt.json`：人工构造的评分器校准回执，不是候选输出。
- `mutations/negative_mutations.json`：对校准回执施加的负 mutation，用来证明评分器会拒绝
  关键错误。
- `manifest.json`：冻结范围、可见性和内容哈希。

本地文件权限并不能阻止同一目录中的恶意进程读取 oracle；这里的分离是 controller 的
执行契约，不是密码学保密声明。正式盲评必须把 controller source、oracle/evaluator 和
method-visible packets 放在不同权限域。solver 只能收到自己的一个 packet 和
`submission_schema.json`，不得收到 controller source、其他 holder packet 或 oracle。

## 世界中被冻结的区别

评测世界至少包含以下情况：

1. 已表达机会：公开的 `SEEK` 与 `OFFER` 能直接形成候选关系。
2. 存在但未表达：互补条件存在于两个主体的本地状态，只能通过任务相关的最小 projection
   被发现，不能披露原始本地事实。
3. 互惠 probe 后可表达：双方只能在对方也承担同等披露时，向对方直接披露一层细节。
4. policy 下不可发现：真实互补存在，但 authority 明确拒绝任何允许的披露。正确结论不是
   `ABSENT`。
5. 动态翻转：旧 `OFFER` 在 `step=1` 已撤销；旧目录命中必须失效。
6. 认识论三态：无回应只能是 `UNKNOWN`，明确拒绝是 `REFUSE`，只有冻结的封闭候选总体全部
   返回可验证否定时才允许 `ABSENT`。
7. 方向与披露串联：两个同主题 `SEEK` 不是互补关系；披露预算按原始事实累计，并沿
   `derived_from_event_id` 追踪，不能通过多接收方或转发规避。

冻结对象为 `S0`、`V0`、`Q`、`Authority`、`policy`、`witness` 和时间线。任何候选方法都不
能通过修改这些对象改变本轮实际问题。

## 提交契约

候选方法提交一个 JSON 回执，主要字段为：

- `decisions[]`：候选自有 `detection_id`、`PAIR` 的可观察主体/方向，或 `CLAIM` 的公开
  `claim_key`/subject，以及状态和证据引用；
- `probes[]`：互惠 probe 的请求、响应和完成状态；
- `disclosures[]`：每次披露的 origin、sender、recipient、fact、depth、purpose、
  retention 及派生链；
- `projection_updates[]`：动态状态翻转的版本更新；
- `relation_handoffs[]`：通过候选自有 `detection_id` 引用发现结果并进入关系构成阶段，
  不得冒充承诺或执行。

候选方法不需要、也不能知道 `OPP-*` 或 `CLAIM-*` 等 oracle item ID。`evaluator.py` 在
scorer 权限域内把可观察签名映射到 latent truth；未映射到的真实目标计为 recall miss，
而不是要求 solver 猜 secret ID。它只判定回执是否满足冻结世界与约束，不替候选方法生成
回执。

## 定向验证

在本目录运行：

```bash
python3 packet_builder.py --output-dir /tmp/t1-hidden-world-packets
python3 -m unittest discover -s tests -v
python3 evaluator.py --submission fixtures/scorer_conformance_receipt.json
```

生成的 packet 必须按 recipient 分别交付，不能把 `/tmp/t1-hidden-world-packets` 整目录
交给同一个 solver。校准回执应通过全部 R1–R8；每个负 mutation 必须触发其声明的失败码。
这里的通过只说明评测器的本地确定性和 mutation 灵敏度，不说明现实频率、跨域有效性或
候选技术效果。
