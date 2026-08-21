# Wave 023：sealed-run admission 前置敌对审计

日期：2026-08-01  
状态：`WAVE021 STATIC PREREGISTRATION PRESERVED / SCORED RUN ADMISSION REJECTED`

## 结论

Wave 021 的价值取向和静态比较边界仍然成立，但它的机器 validator 不能准入任何可计分运行。
它验证的是字段名、profile ID 和若干自报布尔值，没有绑定实际传输字节、启动面、candidate、
world、Authority witness、预算账本或 failure trigger receipt。

因此：

```text
UNSCORED HARNESS DEVELOPMENT PREFLIGHT = ALLOWED
SCORED OR FAIRNESS-EVIDENCE PREFLIGHT = REJECTED
WAVE021 STATIC PREREGISTRATION = PRESERVED
WAVE023 SEALED RUN ADMISSION = REQUIRED BEFORE COMPARISON
```

## root 复现的五个假绿

root 在当前 checkout 中从 `FAIR-BATCH-TEMPLATE.json` 和
`FAIR-FAILURE-TRIGGER.json` 分别构造下列变体，原 Wave 021 validator 全部返回接受：

| 变体 | 注入内容 | 原 validator 返回 |
|---|---|---|
| unknown payload oracle | 只在 A4 的未知字段加入 `runtime_env`、case、expected result、private truth | `FAIR_BATCH_PLAN_ACCEPTED_NOT_EXECUTED` |
| declared U / actual P | plan 声明 `U`，另加实际 world=`P`，A1 仍保持 `PLANNED` | `FAIR_BATCH_PLAN_ACCEPTED_NOT_EXECUTED` |
| unmetered A3 | A3 加 10,000 次模型调用、隐藏检索和巨量 token，自报 `budget_overrides={}` | `FAIR_BATCH_PLAN_ACCEPTED_NOT_EXECUTED` |
| posthoc per-arm trigger | trigger 加各 arm 不同的 success/grader 后验条件，并把 Q/Target/operation binding 标为 false | `SEMANTIC_FAILURE_TRIGGER_ACCEPTED_NOT_EXECUTED` |
| unfrozen executable/world | 每个 arm 加不同但未冻结的 executable 与 world root | `FAIR_BATCH_PLAN_ACCEPTED_NOT_EXECUTED` |

这五项不是 Wave 021 合同“结论错误”的证据；它们证明静态合同尚未连接到真实运行 preimage，
所以 `13/13` 只能证明原测试覆盖的静态准入性质。

## 任何计分运行前必须关闭的门

### 1. 封闭实际启动面

- plan、arm run、world、trigger 和 receipt 使用封闭 schema，拒绝未知字段；
- 绑定实际 initial payload bytes 与 hash，而不只比较 field names；
- 绑定 argv、env、cwd、process name、fd、network 与 endpoint surface receipt；
- 绑定 candidate executable/container；A3 还绑定 provider/model/prompt/tools/parameters，A5
  绑定 console bundle/renderer/真人 receipt；
- `a*64` 等占位 hash、缺 preimage hash 和运行后才补的 manifest 一律拒绝。

### 2. 完整任务与 world preimage

- 冻结完整 canonical Q bytes，而不是只写 `Q@v1`；
- Q 必须包含 object、Target、每点 safety/noise/other-circuit、duration/deadline、readback、
  O_Q/O_V Acceptance 与 O_P finality；
- world blueprint、case×intervention truth、owner/Target roots 和 initial state 全部进入 seal；
- opaque handle/token/operation 由 evaluator RNG 生成，并检查 case×arm 独立性和值级泄漏；
- initial view 的 value、顺序、错误形状和延迟也不能编码 case 或预期结果。

### 3. Authority 不能由 plan 自报

- U/D/P 由 owner/Principal 签名 topology 独立重算；
- D 必须绑定 exact delegation scope、expiry、head 和 revocation status；
- A1 在 P 的 `NOT_APPLICABLE` 来自作用域和 witness，不是私有 case label；
- C1 只能从 common broker 返回的公开 signed Authority/delegation 路由，并记录误路由和成本。

### 4. Failure trigger 必须有原生 receipt

每个 intervention 冻结并返回：

- canonical native event class；
- Q、Target、operation、current owner heads 与 Target-prefix digest；
- 在该 treatment 中是否 reachable；
- 实际 fired/not-fired；
- pre/post state 与 causal order；
- clone-specific trigger 不进入 arm view。

不同 treatment 没有等价 native boundary 时应报告 `NOT_APPLICABLE_TO_TREATMENT`，不能改成
第 N 个事件、wall time，或在看到成功/评分后触发。

### 5. 单一候选和共同结果 evaluator

- 每个 arm 在整个 blind batch 中只有一个冻结 candidate；
- 不能由 evaluator-private case router 在 E0/E2/E3/E4/E6 bespoke runner 之间切换后称为 A4；
- case×intervention 的 expected disposition/Effect/Unknown matrix 在运行前冻结；
- independent evaluator 从 owner-native、Target-native 和 causal receipts 重算 task、Effect、
  Acceptance、finality、refusal、Unknown 和重复执行；
- E5、removal、readback 缺失与 provider refusal 不能套同一个 occurrence=1 scorer。

### 6. Treatment 身份、资源与组合臂

- A3 冻结真实 model identity、prompt、tools、generation、cache/retry/token/model-call 上限；
- A5 只有真实 human+非推荐 console 才是 treatment；模型 fixture 不得计分；
- A4 的 bounded HITL 必须有上限，防止静默退化成 A5；
- C1–C3 是单一全局预算下的组合 executor，必须冻结 router/escalation executable、union
  resource budget 和 alias/ablation 规则；
- behavior 与 provenance 相同的 arm 只能算 alias，不能重复计票。

### 7. 重复、成本和生命周期

- 预注册 case×stratum×intervention 的 N、seed、blocked randomization、timeout/missingness、
  estimand、CI 和 stop rule；
- keys、DB、path、process、provider cache 和真人 carryover 隔离；
- 当前公共 interaction budget 不等于共同 economic budget；没有货币、ratecard、人力补偿、
  cold/maintenance/exit 摊销前，只能报告原始成本向量；
- 宣称“完整解决/优胜”前还需恢复 `C_cold/C_maint/C_exit` 以及 `PROVIDER_STOP / FORMAT_EXIT /
  PROVIDER_SWAP / SECURITY_AND_DRIFT`。

## Wave 023 的正确最小产物

Wave 023 当前只建立 sealed-run admission 与开发性 smoke 准入，不选赢家：

1. seal Wave 021 来源、完整 Q、world/candidate/launch/trigger/预算 preimage；
2. 机器拒绝上述五个假绿；
3. 接受一个具有真实 preimage 与 receipts、但明确 `UNSCORED` 的开发 batch；
4. A3/A5 treatment 不具备真实 receipt 时保持 `NOT_READY/NOT_RUN`；
5. 下一阶段才运行共同 world，且比较证据必须由新的 sealed batch 产生。

这一步不是为了让 schema 变漂亮，而是为了保证后续数字确实来自不同 treatment 面对同一问题，
而不是来自五套各自知道答案的 runner。

