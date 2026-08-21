# W023 Pro 独立返回凭据与结构化捕获

状态：`EXTERNAL CANDIDATE / NOT LOCAL EVIDENCE / NOT A3 TREATMENT`

## Provenance

```text
task_id = W023-PRO-INDEPENDENT-FAIRNESS-RECONSTRUCTION
task_packet_sha256 = bf7f2167a05e8d2faed17d119be186839335219b1c5b65f3b6b48377ea12fd04
conversation_url = https://chatgpt.com/c/6a6d7419-8564-83ea-8748-f89073e99952
visible_account = ChatGPT Pro
visible_reasoning_setting = 极高
page_reported_thinking_time = 3m 58s
captured_response_characters = 34472
captured_response_sha256 = 9b433a3a7c634c26cffa56d69b25f66b34177aa21122e2b5c86c55ef16e1fbda
```

没有可回读的精确 model deployment、weights、provider request ID、sampling 参数、token usage
或 API receipt。因此此返回是独立外部研究候选，不是 Wave 021/023 的正式 A3 treatment，也不
是公平性或机制有效性证据。完整原始返回保留在上面的会话 URL；本文件是结构化捕获，不冒充
逐字 raw transcript。

## 独立重建的核心结论

Pro 没有看到本地 Wave 021 validator、五个本地攻击或 Wave 023 gate 设计。它从五种
treatment 与任务描述独立得出：比较对象不是“谁能给出看似合理的计划”，而是谁能在自己的
合法适用域内，以原生证据完成或正确拒绝共同任务。一次完成必须分别建立：

```text
Current Authority
AND Exact Target Effect Count = 1
AND Authoritative Readback
AND O_Q Acceptance
AND O_V Acceptance
AND Finality
```

任何 controller statement、model output、workflow green、local row 或 success message 都
不能替代这些原生事实。

### 它独立指出的主要假绿

- field-name/profile-ID 验证不能区分 cached authority 与 commit-time current authority；
- private manifest hash 即使不可逆，也可能被有限候选字典枚举成 case oracle；
- case/Target/owner/delegation/path/seed/argv/env/port/log destination 都可能编码答案；
- “相同 endpoint 数量”不能保证 API 语义相同，例如某 arm 获得 current version，另一 arm
  只得到 Boolean；
- A5 console 可以通过排序、颜色、默认展开、过滤或预选而隐性推荐；
- evaluator 若只接受一条 golden trace，会把自身 workflow 偏好误写成 treatment 能力；
- wall-clock fault 会在快慢 arm 上落到不同 causal boundary；
- model context、human feedback、provider cache、shared Target/log 都会污染跨 arm 独立性；
- synthetic acceptance、workflow green 和 pending retry 下的 finality 都是假结果；
- A1 在 P 中获得中心 credential 是不公平，A1 合法不适用被记作普通失败同样不公平。

这些判断与本地 red-team 独立收敛，但模型共识不升格为证据；它们进入本地 validator 的原因是
存在可执行 counterexample，而不是因为两个模型同意。

## Preflight 与 scored batch 的区分

Pro 建议 development preflight 公开、可修复、不可计分，至少检查：

1. arm-view 与 private manifest 分离；
2. Authority/owner/Target/readback/Acceptance/finality 接口能被所有适用 arm 调用；
3. lost ACK、process restart、duplicate-safe readback/recovery 的 plumbing；
4. revoked-before-commit 与 authoritative impossibility 的不同终态；
5. scorer 能区分 semantic task result、treatment availability 和 harness invalidity。

通过 preflight 不能证明 blind、无隐藏 shortcut、接口语义等价、console 无推荐、fault 等价、
模型/真人会在 blind case 中保持行为，也不能选出赢家。

它提出的最小 diagnostic scored batch 是 5 arms × 7 case types = 35 episodes：U success、
D lost-ACK/crash recovery、P success、commit 前 revoke、authoritative impossibility、required
owner refusal、healthy-interface observable unknown。它自己明确说明这不是统计充分 benchmark；
replicate、counterbalanced twin 与独立实例仍是后续强主张所需。

## 两轴及多层状态

Pro 同样拒绝把所有未完成压成 failure。它区分：

- task semantics：`COMPLETE / REVOKED / IMPOSSIBLE / OWNER_REFUSED /
  DEFER_UNKNOWN / INAPPLICABLE`；
- treatment availability：`PROVIDER_REFUSAL / HUMAN_COORDINATOR_WITHDRAWAL /
  BUDGET_EXHAUSTED / ARM_RUNTIME_FAILURE`；
- harness invalidity：`INFRASTRUCTURE_INVALID / FAULT_INJECTION_INVALID /
  BLINDING_BREACH / WORLD_CONTAMINATION`；
- unsafe outcome：unauthorized/duplicate Effect、false readback/Acceptance/finality、错误不完成原因。

evaluator 私有知道 impossible，而合法 API 只返回 Unknown 时，正确可评分终态是
`DEFER_UNKNOWN`，不能要求 arm 猜出 private truth。

## 没有共同经济换算时仍可比较什么

可以报告：

- 每个 case 的 semantic correctness 与正确 abstention；
- unauthorized/duplicate/stale-authority/false-finality 等安全事件；
- 在合法适用域内的 conditional completion；
- Authority topology coverage；
- recovery/readback/duplicate avoidance；
- wall time、API/owner/model/human/retry/write/provider dependency 等原始资源向量；
- 在未加权向量上的 Pareto dominance。

不能报告：overall winner、ROI、human-minute 与 token 等价、把安全/速度/覆盖/成本加权成一分，
或 provider refusal 比 human withdrawal 更昂贵。

## 最高信息量的下一本地实验候选

Pro 提出：

```text
W023-BLIND-TWIN-AUTHORITY-EPOCH-001
```

两个 arm-visible schema 同形、opaque identifier 独立随机的 twin：

- **Twin S**：exact delegation 当前有效；Target 唯一 commit；ACK 丢失；treatment crash；恢复后
  必须 readback、避免 duplicate、取得双 Acceptance 和 finality。
- **Twin R**：静态 profile 与 S 同形，但 current Authority source 在 commit 前进入 revoke
  epoch；Target 应拒绝 stale fence；正确结果为 0 Effect + `REVOKED`。

唯一决定性差异只能通过合法 current-Authority API 与 commit-time fence 发现，不能出现在
ID、hash、filename、argv、field presence、console ordering 或 response formatting 中。

本地采用方式：先让 Wave 023 sealed admission 能冻结和验证这类 twin；不在 admission 未完成
前运行或计分。之后它是比“先扩到更多同质 cases”信息增益更高的首个共同世界实验候选。

## 本地接受边界

```text
external_problem_reconstruction = USEFUL_CANDIDATE
independent_convergence = OBSERVED_NOT_EVIDENCE
new_high_value_test_candidate = W023-BLIND-TWIN-AUTHORITY-EPOCH-001
local_validator_or_runtime_changed_by_model_output = NO_AT_CAPTURE_TIME
formal_A3_treatment = NOT_RUN
comparative_result = NONE
winner = NONE
```

