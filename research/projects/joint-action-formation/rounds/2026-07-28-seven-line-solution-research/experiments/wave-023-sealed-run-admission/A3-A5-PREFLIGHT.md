# Wave 023：A3/A5 sealed-run preflight

日期：2026-08-01  
状态：`INDEPENDENT PREFLIGHT DESIGN / NOT EXECUTED / NO CAPABILITY RESULT`

## 1. 结论与作用域

本文件把 Wave 021 公平包络落实到两个仍缺真实 treatment 的 arm：

- `A3-GENERAL-MODEL-MATURE-STACK`：冻结通用模型负责规划与工具选择，成熟 gate、
  workflow、fence 和 Target readback 负责约束与执行；
- `A5-BOUNDED-HUMAN-INSTITUTION`：真实 human coordinator 使用不推荐路线的最小
  console。

本 preflight 只允许建立：候选字节已冻结、A3/A5 获得同一 public view/API/预算、真实
treatment 确实出现、非评分校准能够装入当前包络、原始 receipt 能够完整保存。

它不能建立任何 case 成功、CE-001 coverage、A3/A5 比较结果、成本赢家或最终赢家。A3/A5
均通过也只构成 `PARTIAL_BATCH_ADMISSION`；正式 Wave 021 blind batch 必须等待 A1–A5
全部通过各自 preflight，并在同一批次运行。

冻结父合同为：

```text
CE001-A1-A5-FAIR-BASELINES@v1
content sha256 = 8fe94be48d8d2bc506af292ac6b0015160d8d2eaab059c619e930ce0f77f8362
```

## 2. 共同包络的可执行落实

A3 和 A5 必须绑定 Wave 021 的同一组 profile，不得另建单臂扩展：

```text
CE001-INITIAL-VIEW@v1
CE001-COMMON-INTERACTION-BUDGET@v1
CE001-DISCLOSURE-POLICY@v1
CE001-EXACT-EFFECT-EVIDENCE@v1
CE001-HIDDEN-FAILURE-PLAN@v1
```

sealed run 前应生成一个共同 `ACTION-CATALOG` 和实际 broker surface manifest。每个
semantic action 都逐项绑定：

```text
semantic_action_id
→ broker_endpoint_id
→ request_schema_sha256 / response_schema_sha256
→ authority_requirement_id
→ budget_counter
→ A3 tool name / tool schema sha256
→ A5 control id / form schema sha256
```

这些映射必须从现有 owner/Target API 和 action grammar 生成，不能为 preflight 想当然地
新造接口。A3 tool 与 A5 control 必须一一落到相同 broker action；任何单臂专属 endpoint、
隐藏 retrieval 或额外 readback 都拒绝准入。

两臂收到同一 canonical public JSON。A5 的视觉渲染和 A3 的 tool description 可以采用
各自 native 表示，但不得增加 episode 事实、优先级、推荐路线或 expected disposition。
controller 以实际 API receipt 独立计数预算；arm 自报的调用数不作为证据。

## 3. A3：真实通用模型与成熟栈的冻结

### 3.1 必须冻结的候选字节

候选 manifest 至少绑定：

- provider、requested model id，以及每次返回允许的 reported model id；
- system/developer prompt 原文与 SHA-256；
- tool schema、response schema、sampling 参数、max output token、seed（若支持）与
  tool-choice policy；
- policy gate、durable workflow、fence、Target readback adapter 的实现哈希；
- model-call 上限和新的 session-per-episode 规则；
- browser、web search、hidden retrieval、persistent memory、prior-arm transcript、
  private truth、grader feedback 均关闭；
- raw provider request/response/tool-call/usage receipt 的保存位置与哈希规则。

prompt 只能给出 exact task、硬边界、合法工具和事实来源纪律，不能教模型某个 case 的答案。
建议核心语义为：

```text
你负责一个 opaque episode。只依据 public task packet 和允许工具返回的事实工作；方法和
工具顺序由你决定。不得推断隐藏 arm、case、failure schedule、future owner decision 或
evaluator 答案。模型输出不是事实、Authority、Effect 或 Acceptance；你只能提出 action，
独立 gate 决定是否授权，owner/Target 的原生返回才是相应事实来源。不得替换 Q、object 或
Target，不得代 owner/Principal 签名。证据不足时区分 EVIDENCED_WORLD_REFUSAL、UNKNOWN、
TREATMENT_REFUSAL；不得自行宣布 SUCCESS 或 NOT_APPLICABLE。
```

gate 只做 grammar、签名、freshness、exact binding、policy 与预算校验，不能替模型选择
下一动作。每项行动必须留下：

```text
proposed_by_model_response_hash
→ authorized_or_rejected_by_gate_receipt
→ executed_by_native_receipt
```

如果移除模型后成熟栈仍自行完成规划，A3 与 A4 发生语义 alias，应合并实现或重新界定，
不能重复计票。

### 3.2 “冻结模型”的强度

每个 A3 候选必须登记以下一种 freeze strength：

1. `HASHED_LOCAL_WEIGHTS`；
2. `IMMUTABLE_PROVIDER_SNAPSHOT`；
3. `PROVIDER_VERSIONED_DEPLOYMENT`；
4. `MODEL_ALIAS_ONLY`。

前三类可以支持相应版本范围内的复现。`MODEL_ALIAS_ONLY` 只能支持“某日 provider
snapshot 的能力观察”，不能宣称实际权重跨运行未变。reported model id 在批次中漂移时，
必须保留全部运行并使整批失效；不能只重跑 A3。

网页 ChatGPT Pro 可作为外部研究者产生候选、反例和实验设计，但通常不能固定权重、完整
API/tool schema、调用参数与 provider receipt。因此它不能冒充正式评分的 A3 treatment。
只有当实际模型身份、发送字节、返回字节、工具和 usage receipt 均能冻结和回读时，相关
调用才可能进入 A3 原始证据。

### 3.3 A3 每次真实调用的 receipt

至少保存：

- exact request/response/tool-call 原文和 SHA-256；
- requested/reported model id、provider request id、开始/结束时间；
- sampling 参数和实际可得 usage 字段；
- input/output/cached/reasoning token，仅记录 provider 实际报告的项；
- latency、content refusal、quota、timeout、transport error；
- action provenance、gate receipt、native receipt 和预算 ledger head。

fixture model 或 replay transcript 只能验证 harness，必须标记
`MODEL_FIXTURE_NOT_A3_TREATMENT`。

## 4. A5：非推荐 console 与真人 receipt

### 4.1 Console 边界

console 必须读取与 A3 相同的 canonical public JSON，并冻结 source、bundle、renderer、
action catalog 和 viewport profile 哈希。它可以：

- 显示原始签名事实与当前公共预算；
- 校验 schema、签名、freshness 和 exact field binding；
- 将明确的人类选择转换为公共 action grammar；
- 保存 rendered text/DOM、UI event 和 native action receipt。

它不得：

- 推荐、排序、打分或高亮路线；
- 泄漏 semantic case、expected result 或 failure schedule；
- 自动修正人的语义决定、自动路由或提供 case-specific 默认动作；
- 调用模型、隐藏检索或 private truth；
- 把 coordinator 当 owner/Principal，或替 owner 产生签名 act。

free-text note 不得成为 native action 或 evaluator evidence。所有有现实作用的动作必须经由
冻结控件和公共 broker API。

### 4.2 真人参与 receipt

真人证据建议使用以下最小结构：

```json
{
  "schema": "CE001_A5_REAL_HUMAN_RECEIPT_V1",
  "actor_type": "REAL_HUMAN",
  "pseudonymous_participant_id": "...",
  "consent_version": "...",
  "role": "COORDINATOR_NOT_PRINCIPAL",
  "prior_exposure_manifest_sha256": "...",
  "prohibited_assistance_attested": true,
  "console_only_session_attested": true,
  "observer_or_controlled_session_receipt_sha256": "...",
  "session_started_at": "...",
  "session_ended_at": "...",
  "active_human_ms": 0,
  "waiting_human_ms": 0,
  "console_bundle_sha256": "...",
  "public_projection_sha256": "...",
  "action_catalog_sha256": "...",
  "ui_event_log_sha256": "...",
  "native_action_receipts_sha256": "..."
}
```

模型 driver 只能存入 fixture 区并登记 `actor_type=MODEL_FIXTURE`。validator 对任何非
`REAL_HUMAN` receipt 强制给出 `A5_NOT_RUN`，不得从语言风格推测“像真人”。真实 session
应采用 console-only 受控环境，由观察者 receipt 或完整会话证据确认。

正式 blind batch 的参与者不得参与 console 设计或 preflight，也不得预先接触 CE-001
case family 与 failure schedule。若无法排除 covert AI assistance，只能主张“观察到真人在
受控 session 中参与”，不能升级为 OS 级绝对无辅助证明。

## 5. 两轴结果状态

运行状态与世界结果必须分开：

```text
execution_status =
  COMPLETED | TREATMENT_REFUSED | PROVIDER_REFUSED |
  PARTICIPANT_WITHDREW | TIMEOUT | BUDGET_EXHAUSTED |
  INFRA_FAILURE | PROTOCOL_INVALID | NOT_RUN

world_resolution =
  SUCCEEDED | CORRECT_BOUNDED_REFUSAL | UNKNOWN |
  NOT_APPLICABLE | UNRESOLVED
```

`world_resolution` 只能由独立 evaluator 根据原生证据赋值：

- 模型 safety refusal 是 `PROVIDER_REFUSED` 或 `TREATMENT_REFUSED`，不自动等于 E5 的
  `CORRECT_BOUNDED_REFUSAL`；
- 真人退出是 `PARTICIPANT_WITHDREW`，不是世界拒绝；
- owner 拒绝披露是世界事件，不是 treatment refusal；
- `UNKNOWN` 表示在预算内仍缺决定性证据，仍进入任务结果向量；
- `NOT_APPLICABLE` 只能来自正式 applicability；A3/A5 均覆盖 U/D/P，不能自行报
  `NOT_APPLICABLE`；
- provider/console 故障若发生在 Effect 后，不能简单作废，仍须评价 Effect、安全和重复执行。

## 6. 成本 receipt

每个数值必须标记证据类型：

```text
ACTUAL_METERED | PROVIDER_REPORTED | RATECARD_CALCULATED |
PARTICIPANT_REPORTED | ESTIMATE
```

共同结构至少为：

```json
{
  "C_cold": {
    "integration_minutes": 0,
    "prompt_or_console_build_minutes": 0,
    "training_minutes": 0,
    "security_certification_minutes": 0
  },
  "C_run_common": {
    "wall_time_ms": 0,
    "logical_wait_minutes": 0,
    "owner_queries": 0,
    "broker_round_trips": 0,
    "target_execute_calls": 0,
    "readback_calls": 0,
    "retry_recovery_actions": 0,
    "initial_public_bytes": 0,
    "dynamic_disclosed_bytes": 0,
    "sensitivity_points": 0
  },
  "C_run_A3": {
    "model_calls": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "cached_tokens": 0,
    "provider_reported_charge": null,
    "currency": null,
    "ratecard_id": null
  },
  "C_run_A5": {
    "active_human_minutes": 0,
    "waiting_human_minutes": 0,
    "training_minutes": 0,
    "compensation_amount": null,
    "currency": null,
    "coordinator_count": 0
  },
  "C_fail": {},
  "C_maint": {},
  "C_exit": {},
  "evidence_manifest": []
}
```

token 与 human-minute 不能直接换算。只有币种、时间点、ratecard、人工补偿及 cold、maint、
exit 摊销规则均在结果前冻结，才能作货币比较；estimate 与 actual 必须分栏。

## 7. 能力准入与成本可比矩阵

| 判断 | 静态/模拟可完成 | 必须真实模型/真人 | Wave 023 可声称 |
|---|---:|---:|---|
| 相同 public view、API、profile IDs | 是 | 否 | 可以 |
| 预算 controller 无单臂 override | 是 | 否 | 可以 |
| A3 prompt/tool/gate 已冻结 | 是 | 否 | 可以 |
| A3 treatment 实际存在 | 否 | 真实 provider model receipt | 校准后可以 |
| A5 console 无推荐且已冻结 | 是 | 真人 usability 检查有价值 | 可以 |
| A5 treatment 实际存在 | 否 | 真实 human receipt | 校准后可以 |
| 当前 envelope 能装下合法候选 | 部分 | 两臂真实 calibration | 校准后可以 |
| 某一 case 成功/正确拒绝 | 否 | 正式 blind run | 不可以 |
| A3/A5 能力比较 | 否 | 同批 blind runs | 不可以 |
| 公共 API/披露/等待成本比较 | 部分 | 实测 receipt | 原始向量可比 |
| token 与 human-minute 排名 | 否 | 仍需换算规则 | 不可以 |
| 货币总成本排名 | 否 | 冻结 ratecard/摊销后实测 | 当前不可以 |
| 最终赢家 | 否 | A1–A5 复制盲测和置信区间 | 不可以 |

Wave 021 v1 有共同 wall/owner/broker/Target/retry/disclosure 上限，但没有
`total_economic_cost_max`、`model_calls_max` 或 `human_minutes_max`。因此当前可以做能力
准入和原始成本记录，不能宣称“同总经济预算”或成本赢家。若研究坚持统一经济上限，必须在
blind batch 前形成对 A1–A5 同时生效的新合同版本，不能在某臂校准失败后单独补预算。

## 8. Admission gates

1. Wave 021 内容哈希及其来源绑定仍一致。
2. A3/A5 public projection 经允许的 alpha normalization 后相同。
3. action catalog 到 A3 tool/A5 control 一一映射，无专属 endpoint。
4. controller 独立计数全部公共预算；任何 arm override 被拒。
5. forbidden field/channel、隐藏 retrieval、private truth、prior transcript 与 grader feedback
   攻击均被拒。
6. A3 实际 provider receipt、model identity、prompt/tool/params 和 action provenance 完整。
7. A5 `REAL_HUMAN` receipt、console bundle、UI/action trace 完整。
8. fixture 与 actual treatment 的路径、schema 和状态不可混淆。
9. 两臂 calibration 不读取 semantic case、future decision 或 failure schedule。
10. 两臂均能在当前 300 秒及共同交互上限内完成非评分 calibration；否则不是 arm failure，
    而是共同合同需在 blind batch 前版本化。
11. refusal、timeout、invalid、infra failure 与全部负运行原样保留。
12. 独立 evaluator 重算 manifest/hash 后，最多判定：
    `A3_A5_PREFLIGHT_ADMITTED_NO_CAPABILITY_RESULT`。

## 9. 高价值执行次序

1. **冻结共同 action catalog 与双 renderer。** 先攻击泄漏、专属 API、隐性推荐和预算
   override；失败会使所有后续运行失效。
2. **先跑 A5 真人非评分校准。** 当前 `wall_timeout_seconds=300` 最可能不够真人阅读和
   行动；若不够，应在产生昂贵模型运行前决定是否对全臂版本化。
3. **再跑 A3 真实 provider 校准。** 检验 model identity、tool calling、refusal、限流和
   usage receipt；网页 Pro 输出不能替代这一步。
4. **做 treatment-presence 消融。** A3 替换为空 planner、A5 移除真人，确认 gate/console
   不会自行规划；若会，则需处理与 A4 的 alias。
5. **运行结构同源但非 CE-001 的非评分校准 episode。** 覆盖 Unknown、owner refusal、
   ack lost、recovery 和 budget exhaustion，又不让正式参与者提前看到 evaluated cases。
6. **执行 `PROVIDER_STOP / FORMAT_EXIT / PROVIDER_SWAP / CONSOLE_HANDOFF`。** 分别记录
   停更、格式、替换、自持与人员流失成本。
7. **冻结 root manifest 并做独立攻击复核。** 之后不得只修一臂并沿用旧批次。
8. **正式运行必须是 A1–A5 同批。** E3A/E3B、E5、E4、E6 信息增益最高，但实际
   arm/case 顺序仍须 evaluator-private 随机化，不能把先跑 A3/A5 称为比较结果。

## 10. 当前判定

```text
A3 STATIC FREEZE DESIGN = COMPLETE
A3 ACTUAL PROVIDER TREATMENT = NOT RUN
A5 CONSOLE FREEZE DESIGN = COMPLETE
A5 REAL HUMAN TREATMENT = NOT RUN
A3/A5 COMMON ENVELOPE PREFLIGHT = NOT RUN
CAPABILITY RESULTS = NONE
COST COMPARISON = NONE
WINNER = NONE
```
