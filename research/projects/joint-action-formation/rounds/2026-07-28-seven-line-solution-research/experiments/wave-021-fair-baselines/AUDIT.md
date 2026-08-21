# Wave 021：CE-001 A1–A5 公平基线审计

日期：2026-07-30  
状态：`FAIRNESS PREREGISTERED / COMPARATIVE RUNS = 0 / WINNER = NONE`

## 结论

CE-001 现在有了可执行的公平比较准入，而不是新的胜负结果。

冻结合同是 `BASELINE-CONTRACT.json`，内容哈希：

`8fe94be48d8d2bc506af292ac6b0015160d8d2eaab059c619e930ce0f77f8362`

它不把 Towow/A4 设为期待答案，也不把强中心、通用模型、人工或现有组合设为陪跑。任何
现有 arm 或合法 portfolio 完整解决，都是正向结果。

## 读取与继承

本审计逐字读取并绑定：

- `PROGRAM.md`；
- Wave 012 `CE-001-CONTRACT.md`；
- Wave 013 `REMAINING-CASE-CONTRACTS.md` 与原 `FAIR-BASELINE-CONTRACT.md`；
- Wave 017 E0、Wave 019 E2、Wave 016 E3A/E3B、Wave 018 E4 的
  `ROOT-ACCEPTANCE.md`。

E0/E2/E3/E4 的已接受结果只证明现有技术组合在对应
local-synthetic/local-digital 有界问题上可行。它们不构成 A1–A5 横向比较，也不能被回填
为某个 arm 的胜场。

## 公平性如何定义

公平不是让所有方法内部相同。若把模型、确定性 workflow、强中心和真人都削成同一个
decision root，比较会失去对象。

本合同冻结的是同一个外生包络：

- 同一 `Q@v1`、Target、deadline、功率、时长、安全、噪声、Acceptance 与 finality 要求；
- 同一语义任务投影；仅随机 binding、opaque run/operation 等允许 α-renaming；
- 同一显式 allowlist public view 与固定 broker endpoint surface；
- 同一 owner/Target API、合法 action grammar、交互预算和披露政策；
- 同一 evaluator-private、运行前冻结、native-event-triggered failure plan；
- 同一零后验条件：零 grader feedback、零 private truth、零跨臂 transcript、零 evaluated
  episode rerun、零 budget override。

模型调用、确定性规则、中心事务和真人判断属于 treatment 本身，不能被抹掉；它们的真实
调用、人力、等待、维护与退出成本进入预注册成本向量。

语义 `arm_id` 不进入 arm-visible 初始视图。harness/evaluator 私下知道哪一个 executable
对应 A1–A5；arm 只收到 opaque `arm_binding_token`。否则 A3/A5 会在启动时知道自己处在
哪个研究假说或 treatment 中，形成额外先验。

故障注入的“相同”也不按第 N 个事件、相同 trace 长度、相同 wall time 或相同 raw event
hash 判断。不同 arm 合法地产生不同长度的 trace。克隆间的触发点必须同时绑定：

- 等价 native event class；
- current owner head set；
- Target prefix semantic digest；
- exact Q/Target/operation scope。

每个 clone 的实际 event hash可以保存为 provenance，但 clone-specific trigger 不得进入
arm view。

## A1 与 A2 不能混为一谈

`A1-LAWFUL-CENTER` 只在 `U / LAWFULLY_UNIFIED` 或 `D / EXACT_DELEGATION` 适用。它在
合法范围内完整解决就是正解，但在 `P / PLURAL_INDEPENDENT` 必须
`NOT_APPLICABLE`，不能代 owner 签名，也不能把不适用记作中心计算失败。

`A2-EQUAL-INFORMATION-CENTER` 保持集中计算，但只能通过与 A3/A4/A5 相同的 owner 和
Target API 行动。这样才能区分：

- 中心是否有足够计算/规划能力；
- 世界是否根本没有可合法集中的 Authority。

跨 Authority stratum 选一个“总冠军”被合同禁止。

## 每个 arm 的执行边界

| Arm | Native treatment | 不得获得的额外优势 |
|---|---|---|
| A1 | 合法强中心、中心 policy/transaction/workflow | P 中 owner substitution、private case store、额外初始信息 |
| A2 | 等信息中心协调器 | owner 代签、额外 API、额外重试 |
| A3 | 冻结通用模型 + 成熟 policy/workflow/readback | 隐藏检索、grader 反馈、把模型输出当 Authority/Effect |
| A4 | 规则/workflow/IAM/outbox/fence/readback/HITL | case 分支、future decision、额外重试、事后修复 |
| A5 | 真人 coordinator + 不推荐路线的最小 console | 把模型模拟人记作 A5、把 coordinator 当 Principal |

所有 arm 引用同一 view、预算、披露和 failure-plan profile。一个 profile 发生变化就必须形成
新合同版本，不能只给某一 arm 增补。

当前数值预算是 pre-blind 工程上限，不宣称已经证明对五种 native treatment 都充分。若
任一合法 arm 在 preflight 中证明完整候选无法装入该 envelope，必须在盲测前创建新合同
版本、对全部 arm 同时提高上限；不能在失败后单独给它或 A4 加预算。

## Exact Effect 证据门

`ExactTargetOccurrenceCount=1` 只是必要条件，不再足以通过。每个可达 case 还必须由独立
evaluator 重算：

- occurrence exact 绑定 Q、object、Target C7、operation、readback 与 Acceptance；
- 46 个连续、唯一 offset `0..45`；
- 每个 sample 自身绑定 `target_id=VenueV:CircuitC7`；
- 每个 sample 自身绑定 `other_circuits_energized=[]`；
- 每点 `2.85..3.15kW`、`safety_ok=true`、`noise_ok=true`；
- duration=45 且 `effect_start+45<=deadline`；
- occurrence 顶层其他线路同样为空。

这条门专门阻断早期 E2/E4 曾出现的“有一个 occurrence 数字就算 exact task”的假绿。

## 现有技术直接与组合 arm

直接 arm 为 A1–A5。合同还预注册三个未运行的现有组合：

1. `C1-PUBLIC-AUTHORITY-ROUTER-A1-A4`：只根据 common broker 返回的 current 签名
   Authority/delegation 路由，不能看 case label 或 private stratum；
2. `C2-MODEL-PLAN-DETERMINISTIC-GATES`：通用模型提议，独立确定性 gate 与 owner API
   授权；
3. `C3-DETERMINISTIC-HUMAN-ESCALATION`：按运行前冻结的 uncertainty/policy signal
   进入真人协调。

若组合与某直接 arm 的行为和 decision provenance 完全相同，它只能作为同一实现，不能
重复计票。

## 预注册结果向量

不使用单一总分。每次实际 run 必须返回：

- 任务：`ExactTaskSuccess / CorrectResolution / RecoveryToValue`；
- 唯一 Effect：exact occurrence 数、`UniqueEffect / DuplicateEffect /
  UnreconciledEffect`；
- Acceptance：O_Q、O_V、双 Acceptance 后 O_P finality，以及 readback 前错误 Acceptance；
- 错误行动：unsafe、wrong-object、Authority violation、owner substitution、无谓 formation、
  unsafe continuation、missed/over reopen、oracle access、budget violation；
- 披露成本：初始/动态 bytes、敏感度、接收者、保存成本和被拒披露；
- 协调成本：owner query、round trip、协商轮、等待、真人分钟、模型/工具调用；
- 恢复成本：status/readback、retry、recovery、reopen、恢复时间与 compensation。

安全门先于成本排序；`UNKNOWN`、refusal、`NOT_APPLICABLE` 与 failure 分开报告。

## 已保存的不公平攻击

`fixtures/UNFAIR-TOWOW-EXTRA-ORACLE.json` 故意只给 A4：

- 语义 `arm_id`、`semantic_case_id` 与 `expected_disposition`；
- failure/effect oracle；
- private truth 与 grader feedback；
- 一次 evaluated-episode rerun；
- 第三次 Target execute 的额外预算；
- 只检查 occurrence count 的粗粒度 Effect scorer。

validator 会分别识别这些不公平来源。这个攻击说明：即使 A4 最终成功，只要多看一个答案
字段、多试一次或在评分后重跑，比较就无效。

`fixtures/UNFAIR-RAW-ORDINAL-FAILURE-TRIGGER.json` 则把故障固定在 trace ordinal 7，并把
clone-specific trigger 暴露给 arm。它会被拒绝，因为 trace ordinal 并不代表跨异质 arm 的
等价 native boundary。

## 尚缺输入

这些缺口不阻止冻结公平合同，但阻止实际胜负结论：

- E6 尚无完整 accepted case；
- A1/A2/A3/A5 尚未在共同 blind world 中实际运行；
- A3 尚缺冻结模型版本、完整 prompt、工具 allowlist 与稳定调用预算；
- A5 尚缺真人 coordinator、同信息 console 与真实人力记录；
- A1 的 `D / EXACT_DELEGATION` 共同世界尚未实例化；
- 交互预算已有共同 pre-blind 上限，但尚需五臂 preflight 证明充分性；model/human/
  maintenance/exit 成本也尚无经验证的统一货币换算；
- 尚无跨 arm 独立 world clone、运行次序随机化、实际可见性 receipt 与结果置信区间；
- 本地合成 Authority/Effect 仍不是现实法律 Authority 或物理送电。

因此本轮只能接受：

```text
FAIRNESS_CONTRACT = FROZEN_AND_MACHINE_CHECKED
COMPARATIVE_RESULTS = NONE
FINAL_WINNER = NONE
EXISTING_TECH_FULL_SOLUTION = STILL_POSITIVE_AND_OPEN
```
