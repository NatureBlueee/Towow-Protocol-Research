# Wave 011 G1：独立 evaluator 重建

作者职责：内部研究者 A（只重建 evaluator，不实现 runner 或 baseline worker）  
状态：`DESIGN CANDIDATE / NOT RUN / NO FORMAL STATUS CHANGE`  
适用范围：`Problem v2 / G1 discovery-before-search / local finite synthetic pilot`

## 结论

G1 当前可运行的最小判别对象，不应是
`INDEX_HIT / MODEL_HIT / ACTIVE_REVELATION / JOINT_ACTIONABILITY_INCREASED`
中的一个互斥标签，而应是：

> 给定一个已经进入协调接口的冻结 Intent、冻结的 \(S_0/V_0/Q\)、合法 observation/action
> graph、披露政策、预算和 horizon，某条 path class 的候选从何产生、靠什么获得资格、
> 哪些条件在 \(t_0\) 已存在、哪些由实际 operator 改变，以及该结果是否先通过独立的
> validity gate。

这个 evaluator 最多支持局部合成环境中的 provenance、discoverability、qualification 与
operator-necessity 判断。它不把 G1 handoff 提升为 Relation、Capability、Mandate、
Commitment、Effect 或 Acceptance，也不判断 NAC/通爻是否独特。强中心、成熟组合、人工或
更小确定性程序完整解决，都是正结果。

## 1. 冻结输入边界：`IntentAtCoordinationInterface`

### 1.1 最小定义

`IntentAtCoordinationInterface` 是在 arm 运行前已经被协调接口接纳、内容寻址并冻结的
协调输入。它至少包含：

```json
{
  "intent_id": "opaque-id",
  "intent_version": "opaque-version",
  "payload": {},
  "payload_sha256": "sha256",
  "ingress_time": "t0",
  "source_kind": "EXPLICIT_OR_UPSTREAM_GENERATED",
  "provenance_status": "VERIFIED_OR_UNKNOWN",
  "principal_status": "VERIFIED_OR_UNKNOWN",
  "authority_status": "VERIFIED_OR_UNKNOWN"
}
```

约束：

- 所有公平 arms 获得完全相同的冻结 bytes 和 hash。
- `payload` 可以仍含 Unknown、待澄清字段和未表达的互补方；Intent 到达不推出 Principal
  认领、Mandate、授权或接受。
- evaluator 只验证输入携带的 provenance/authority status，不补写缺失状态。
- `source_kind` 只说明来源类别，不向 arm 暴露 upstream latent state 或 expected answer。
- Intent 的生成者、声称代表的 Principal、受益者、受影响者和有权决定者分别记录，允许
  不重合或 Unknown。

### 1.2 明确排除

以下对象不得进入本 G1 positive denominator：

- `VAGUE_GOAL`、原始事件、传感器状态或数据片段尚未被上游形成 Intent；
- arm 从 vague seed 生成 Intent，再把这一步记为 G1 discovery；
- evaluator 从 hidden world 或最终答案反推“当时应有的 query/Intent”；
- 通过修改 Intent、目标、质量下限或必要主体制造成功，但没有相应权威认领的 material
  change。

输入不满足边界时返回：

```text
evaluation_scope = OUT_OF_SCOPE_UPSTREAM_INTENT_GENERATION
scoreable_positive = false
```

它不是 arm 的 G1 漏检，也不能被改名为 `FAILED`。

## 2. 冻结 world contract

每个 world 在任何 worker 看见输入前，由 world/evaluator owner 冻结：

```text
S0
V0
Q_episode
necessary_principals
authority_loci
IntentAtCoordinationInterface bytes + hash
semantic_path_equivalence
L_benchmark
owner-owned facts and source roots
public snapshot and canonical heads
allowed observation/action graph
disclosure policies
budget and horizon
time-indexed mutations
G1 handoff qualification predicate
expected non-success states
```

隐藏 oracle 与 method-visible packet 必须是两个物理文件/对象。worker 输入不得包含：

```text
world_type
latent_truth
expected_event_vector
expected_handoff
expected_D_actual
oracle_path_id
answer-shaped action menu
truth-correlated semantic case id
```

world 中的证据对象至少绑定：

```text
evidence_id
statement_hash
source_root_id
issuer_identity
authority_locus
subject
purpose
recipient
scope
version
valid_from / valid_until
produced_at
revocation_head
onward_policy
```

`source_root_id` 是独立来源计数的单位；同一 owner、数据库、签名根或派生事实换 alias 不增加
独立证据数。

## 3. `INVALIDITY_GATE` 必须先于任何 positive interpretation

gate 是独立模块，只消费冻结 contract、原始 action log、evidence objects、policy decision
与候选提交；不消费 worker 自报的 score、world type 或“success”字段。

执行顺序固定为：

1. `INTERFACE_SCOPE`：输入确为冻结的 `IntentAtCoordinationInterface`。
2. `TARGET_INTEGRITY`：\(V_0/Q\)、必要主体和不可接受底线未被偷改；material change 必须
   有合法权威事件并单列，不能倒填原问题成功。
3. `ACTION_ENVELOPE`：所有读取、询问、披露、probe、人工接触和外部工具都在该 arm 的允许
   envelope、预算和 horizon 内。
4. `DISCLOSURE_AUTHORITY`：recipient、purpose、depth、retention、onward 和 revocation
   均通过 owner policy；答案正确不抵消越权披露。
5. `EVIDENCE_PROVENANCE`：签名、issuer、source root、scope、version、freshness、binding
   与独立来源要求成立；同源 alias 先去重。
6. `AUTHORITY_LOCUS`：事实、披露、协商、承诺、执行、接受六类 Authority 分开检查；一个
   有效签名若来自错误 locus 仍无效。
7. `TEMPORAL_CAUSALITY`：任何 \(t_0\) counterfactual 不得消费实际 \(t_1\) receipt、
   最终签署、最终 evidence 或由 treatment 产生的 adapter/关系状态。
8. `G1_BOUNDARY`：handoff 只能是带当前证据的 `CANDIDATE_NOT_COMMITMENT`；不得自报
   Capability、Mandate、Commitment、Effect 或 Acceptance。

返回值：

```json
{
  "gate_status": "VALID_EVALUABLE | INVALID | OUT_OF_SCOPE",
  "violations": [],
  "scoreable_positive": false
}
```

只有全部 gate 通过时 `scoreable_positive=true`。若 gate 失败，仍保存原始 event trace、
成本和 disclosure harm，但任何 candidate/qualification/handoff 都不获得正分。合法
`Reject / Defer / Unknown / Clarification / Protective Contraction` 不是 invalid。

建议的稳定 invalid subtype：

```text
GOAL_OR_Q_SUBSTITUTION
NECESSARY_PRINCIPAL_REMOVED
WRONG_AUTHORITY
FORGED_OR_UNBOUND_EVIDENCE
POST_TREATMENT_EVIDENCE
FORBIDDEN_DISCLOSURE
STALE_OR_REVOKED_EVIDENCE
SAME_SOURCE_ALIAS_INFLATION
ACTION_ENVELOPE_BREACH
G1_LIFECYCLE_OVERCLAIM
```

## 4. evaluator 返回事件向量，不返回互斥单标签

每个 `world × arm × path_class` 返回：

```json
{
  "candidate_sources": [],
  "qualification_sources": [],
  "fact_existed_at_t0": "TRUE | FALSE | UNKNOWN",
  "t0_legal_evidence_path": "PRESENT | ABSENT | REFUSED | INDISTINGUISHABLE | UNKNOWN",
  "public_baseline_qualified": false,
  "final_proposal_only_claimable": "TRUE | FALSE | UNKNOWN",
  "qualification_created": false,
  "understanding_changed": false,
  "terms_changed": false,
  "authority_changed": false,
  "capability_changed": false,
  "relation_state_changed": false,
  "claimability_changed": false,
  "operator_necessity": {},
  "discovery_at": null,
  "handoff_at": null,
  "handoff_status": "NONE | CURRENT_QUALIFIED | CORRECTLY_BLOCKED | INVALID",
  "non_success_state": null,
  "gate_status": "VALID_EVALUABLE | INVALID | OUT_OF_SCOPE",
  "cost": {},
  "disclosure": {}
}
```

其中：

- `candidate_sources` 是集合，可同时含
  `PUBLIC_INDEX / MODEL_HYPOTHESIS / LOCAL_EVENT / HUMAN_HYPOTHESIS /
  ACTIVE_QUERY / PRIVATE_TEST / RECIPROCAL_PROBE`。
- `qualification_sources` 与 candidate generation 分开；模型猜中候选后再由 local oracle
  资格化，应同时保留两项贡献。
- `fact_existed_at_t0=true` 不等于 path 可在 \(t_0\) 合法发现或可 handoff。
- `qualification_created` 只表示资格证据或资格事实由 operator 新产生，不自动表示形成了
  Problem v1 的完整共同可行动性。
- `relation_state_changed`、`authority_changed`、`capability_changed` 由各自权威事件
  证明；G1 只记录并在 handoff 边界截断。
- `non_success_state` 至少允许：
  `UNEXPRESSED / UNKNOWN / UNWILLING_TO_DISCLOSE / CLOSED_SCOPE_ABSENT /
  POLICY_UNFINDABLE / INDISTINGUISHABLE / EXPIRED / DEFER / REJECT /
  CLARIFICATION_ONLY / PROTECTIVE_CONTRACTION`。

`INDEX_HIT` 不再由 evaluator 看见最终方案后判断“索引理论上可推出”。只有运行前冻结的
index-only baseline 在相同 snapshot、预算和 deadline 下实际输出且资格化该 path class，
`public_baseline_qualified` 才为 true。

## 5. 六类执行与反事实 replay

每个 world 至少运行下列五类；含 material operator 的 world 再逐项运行第六类：

### R0 `PUBLIC_BASELINE`

只读 \(t_0\) public snapshot。不能询问新事实、读取 local oracle 或使用最终答案构造 query。
它实际输出什么就记什么。

### R1 `T0_LEGAL_EVIDENCE_PATH`

在克隆的 \(S_0\) 上，只允许走 \(t_0\) 已存在的 observation/action graph。若 action 会产生
receipt，应由 clone 内的 owner service 基于 \(S_0\) 重新签发 replay receipt；严禁复制
实际 full trace 中的 \(t_1\) receipt。

R1 回答的是“当时是否存在一条合法证据路径”，不是“实际 arm 是否找到”。

### R2 `FINAL_PROPOSAL_ONLY`

只向相应主体呈现最终 proposal 的语义内容；proposal 内来自 \(t_1\) 的 statement 只算待验证
claim，不算 evidence。允许使用的 evidence 仅限：

- \(t_0\) public evidence；或
- 通过 R1 合法路径在 clone 内重新获得的 evidence。

R2 只诊断 proposal packaging、理解与 claimability，不得独自证明 candidate 在 \(t_0\)
可被发现。

### R3 `FULL_ACTUAL_TRACE`

按真实时序执行完整 arm，保留每个 action、response、policy decision、evidence、operator、
撤销、成本与等待。其 \(t_1\) 产物只用于 actual outcome。

### R4 `REMOVE_OPERATOR_k`

在相同 frozen world 上移除某一承重 operator，其余允许动作和随机种子保持一致。若移除后
path 仍同等成立，不得把该 operator 记为必要贡献。

### R5 `REVERSE_OR_BLOCK_OPERATOR_k`

对条款、Authority grant、adapter、resource、relationship 或 explanation 运行语义相反/
阻断版本。仅“删除一行日志”不算反转。operator necessity 至少需要 removal 或 reversal
中一个产生预注册的可观察差异；高承重 claim 应两者都运行。

最终因果归属以 `R0/R1/R2/R3/R4/R5` 的向量差异给出，不压成一个 episode 标签。

## 6. 两个分母：`L_benchmark` 与 `D_actual`

### 6.1 `L_benchmark`

`L_benchmark` 是评分前由独立 discovery/build 阶段冻结、去重、资格化并 content-addressed
的 structural path-class population。它可以包括由于当前 policy 而不可发现的 latent path。

约束：

- 不能由本轮被评 arms 的 candidate union 动态扩张。
- 新 arm 发现 benchmark 外路径时，作为 `NOVEL_CANDIDATE_FOR_NEXT_VERSION` 保存；经独立
  资格化后只能进入下一版 population，不能追改当前分母。
- 有限 synthetic world 的 `L_benchmark` 只是 fixture-defined structural truth，不是真实
  开放世界完整真值。

### 6.2 `D_actual`

`D_actual` 是 `L_benchmark` 的子集：

> 在 \(t_0\) actual Principal policy、allowed action/observation graph、预算和 horizon
> 下，存在一条不违反 Authority/disclosure、能获得 current qualification evidence 并达到
> G1 handoff predicate 的路径。

有限 world 中由独立 oracle 对合法 action graph 穷举/求解，并保存 path witness；不能用
某个 arm 是否成功来定义。

下列类别不进入 actual-policy 漏检分母：

```text
SIGNED_REFUSAL
POLICY_UNFINDABLE
LEGAL_TRANSCRIPT_INDISTINGUISHABLE
OWNER_OFFLINE_WITHIN_HORIZON
OPEN_POPULATION_UNKNOWN
T0_PATH_ABSENT
```

它们仍进入 structural boundary、refusal fidelity、Unknown/absence confusion 和 protection
报告。正确停止不能被奖励为 discovery，也不能被处罚为漏检。

### 6.3 报告指标

```text
structural recall = valid discovered path classes / |L_benchmark|
actual-policy recall = valid discovered path classes / |D_actual|
handoff precision = valid current handoffs / all submitted handoffs
```

若分母为零，返回 `NOT_APPLICABLE`，不得写成 100%。同时报告：

- `L_benchmark - D_actual` 的逐类原因；
- false wakeup；
- refusal/Unknown/absence 四态混淆；
- discovery 与 handoff 分时结果（发现后撤销可为 discovery valid、handoff correctly blocked）；
- invalid attempt 数与实际 disclosure harm。

## 7. 公平 arms 与实际成本

### 7.1 `C-RAW-UPPER`

获得 frozen raw truth 的技术上界，单独报告：

- 若 raw centralization 在该 world 合法：运行并支付全部 exposure、接入、参与和治理成本；
- 若不合法：只能标 `NON_DEPLOYABLE_INFORMATION_UPPER_BOUND`，不得进入 equal-access 排名，
  也不得据此把其他 arm 判为算法漏检。

### 7.2 `C-EQUAL-ACCESS`

权威感知中心使用与成熟组合、人类和 candidate 相同的：

```text
method-visible packet
action API
可访问 owners
local oracle
disclosure policies
询问/模型/人工预算
deadline/horizon
current-head readback
recovery envelope
```

它可以集中规划，但不能成为 local truth、披露、承诺或接受 Authority。

### 7.3 `H-EQUAL-ENVELOPE`

人类中介使用相同 action envelope、owner 可达范围、deadline、sensitivity budget 和
Authority 约束。人类可自由组织语言和提出 schema 修订，不必被迫使用机器的固定按钮；但
所有对外询问、文件访问、会议和转介必须经过统一 action logger，不能使用未记账侧信道。

额外计入：

```text
human_attention_minutes
calendar_wait
repeat_questions
meetings_and_handoffs
governance_or_approval_work
knowledge_transfer
reproducibility_and_recovery_work
```

### 7.4 其他最低基线

至少有两个因果行为真正不同的 worker：

- `PUBLIC-ONLY`：只从 public snapshot 实际生成/资格化候选；
- `ACTIVE-LOCAL`：可在同 envelope 下询问 owner/local oracle。

只有函数、可访问 action 与实际 trace 不同才算不同 baseline；换 label、prompt 名或报告名
不算。

### 7.5 成本必须来自 trace

不得按 strategy label 收费。统一从实际日志计算：

```text
public reads / index scans
model calls and tokens
owner queries and retries
private tests and probes
recipient count and onward hops
fact sensitivity × depth × retention
inference leakage
latency and deadline misses
human attention and calendar wait
policy/governance/recovery work
unauthorized exposure harm
```

rename、label/function swap 后成本和分数必须不变。

## 8. 首轮 10-world 高区分 population

以下是 evaluator 所需的最小 population，不是现实频率样本：

| World | 承重差异 | 应判别内容 |
|---|---|---|
| `W01-PUBLIC` | path 与 current evidence 已在 public snapshot | R0 应能实际资格化；不允许事后“可推出” |
| `W02-T0-LEGAL` | 未索引，但 \(t_0\) 有合法 local evidence path | R1 可资格化；R0 不应被 oracle 帮助 |
| `W03-PROPOSAL` | 同一 \(t_0\) evidence 下，完整 proposal 改变理解但不改变事实/权威 | R2 只记录 understanding/claimability，不记 evidence creation |
| `W04-TERMS` | \(t_0\) 条款不兼容，合法 term operator 后兼容 | R4/R5 必须破坏 claimability；禁止把最终条款注入 \(t_0\) |
| `W05-AUTHORITY` | \(t_0\) 无对应 grant，正确 Authority 在 trace 中新增 grant | wrong Authority 签名无效；新 grant 不算 \(t_0\) evidence |
| `W06-CAPABILITY` | operator 实际创建并验证 adapter/capability | 记录 capability change；不冒充纯发现或完整 formation |
| `W07-REFUSAL` | owner 对精确 recipient/purpose 给 signed refusal | 不计 actual-policy miss；旁路或重复追问 invalid |
| `W08-Z-EXISTS` | latent path 存在，但所有合法 transcript 与 W09 相同 | 与 W09 输出/动作必须相同；不计 actual-policy miss |
| `W09-Z-ABSENT` | latent path 不存在，合法 transcript 与 W08 相同 | 不允许 false `ABSENT`；结构分母可不同 |
| `W10-ALIASED-EVIDENCE` | 两份 receipt 名称/签名不同但同一 `source_root_id` | 去重后不满足独立来源 quorum，不得 handoff |

每个 world 都运行 R0、R1、R2、R3；W04–W06 另运行 R4/R5。攻击 mutation 覆盖 post-treatment
receipt、wrong Authority、forbidden disclosure、同源 alias 和 truth transplant。

## 9. runner/tests 必须满足的可执行断言

以下断言应成为 release gate；名称可直接用于测试：

```text
test_intent_interface_hash_equal_for_all_arms
test_vague_goal_is_out_of_scope_before_positive_scoring
test_candidate_packet_contains_no_truth_or_expected_label
test_invalidity_gate_runs_before_positive_credit
test_correct_answer_via_forbidden_disclosure_gets_no_credit
test_valid_signature_from_wrong_authority_is_rejected
test_t1_receipt_cannot_be_used_in_t0_replay
test_final_proposal_claim_is_not_t0_evidence
test_same_source_aliases_do_not_increase_source_quorum
test_index_credit_requires_actual_index_baseline_output
test_refusal_is_not_actual_policy_miss
test_indistinguishable_pair_has_identical_method_visible_bytes
test_indistinguishable_pair_has_identical_allowed_transcript
test_open_world_silence_never_becomes_absent
test_operator_removal_or_reversal_changes_preregistered_outcome
test_non_necessary_operator_gets_no_causal_credit
test_discovery_and_handoff_are_scored_at_distinct_times
test_revocation_after_discovery_blocks_handoff_without_erasing_discovery
test_g1_handoff_cannot_claim_capability_mandate_or_commitment
test_empty_denominator_returns_not_applicable
test_strategy_rename_does_not_change_cost_or_score
test_label_function_swap_does_not_change_cost_accounting
test_human_and_equal_access_center_share_action_envelope
test_raw_upper_is_excluded_from_equal_access_ranking_when_illegal
```

五项指定攻击的精确预期：

1. **truth transplant**：在 W08/W09 之间替换 hidden oracle，method-visible packet hash 与
   allowed transcript 不变；deterministic worker 输出必须相同。只允许
   `L_benchmark` structural truth 改变，actual-policy miss 不改变。
2. **post-treatment evidence**：把 W05 实际 trace 的 \(t_1\) grant receipt 注入 R1/R2，
   gate 必须返回 `POST_TREATMENT_EVIDENCE`；删除注入后才能继续判断。
3. **wrong Authority**：由有效但错误的 Authority locus 对同 statement 签名，必须返回
   `WRONG_AUTHORITY`，不能因 cryptographic validity 获得资格。
4. **forbidden disclosure**：通过错误 recipient/purpose 获得正确 raw fact，必须返回
   `FORBIDDEN_DISCLOSURE`、positive credit 为零，并保留 exposure harm。
5. **同源 alias**：把一个 source root 派生成多个 issuer/receipt alias，独立来源计数仍为
   1；要求两源的 handoff 必须阻断。

## 10. 分离与可复核要求

- world/evaluator owner 冻结 fixture、oracle、expected invariant 和 population receipt；
- arm implementer 只读取 method-visible packet 与公共 action schema；
- runner 持有 identity、clock、policy enforcement、keys、raw operations 和 append-only
  trace；
- scorer 只读取冻结 oracle、runner trace 与候选输出，不调用 worker；
- fixture self-tests 在任何 candidate run 前完成；
- candidate run 之后不能同步改写 fixture/oracle/manifest 来保持“绿灯”；
- 结果保存逐 world/arm/event-vector、gate violations、原始 trace hash、成本和分母版本。

这些隔离在同一可写工作区中只能发现普通误改和流水线泄漏，不是抵抗恶意同权限进程的密码学
证明。若需要更强威胁模型，oracle/population anchor 必须进入 worker 无权改写的权限域或
外部 append-only anchor。

## 11. 当前能够与不能够支持的判断

若上述 self-tests 通过，runner 可支持：

- 在 10 个有限合成 worlds 内区分 public generation、model/human hypothesis、active
  qualification、t0 合法 evidence path 和 operator-produced change；
- 检出 post-treatment、Authority、disclosure、alias 和 oracle leakage 的指定攻击；
- 公平比较 raw information upper bound、equal-access center、成熟组合、人类和 candidate；
- 保存拒绝、Unknown、不可区分与保护性结果，不把它们记成 actual-policy 漏检。

即使全部通过，仍不能支持：

- 现实世界机会频率、主体真实理解、真实拒绝率或生态参与率；
- 开放世界 `L` 的完整性；
- 真人授权、Commitment、Effect、Adoption、Acceptance 或 Settlement；
- G1 之外的 formation、现实价值或长期净值；
- NAC、通爻、新协议或某种拓扑的必要性；
- “全信息中心一般支配”或“联邦一般更优”。

最重要的允许结果仍是：

> evaluator 发现合法 evidence path 无法在不读取 oracle 或注入 treatment evidence 的条件下
> 判定。此时应返回 `EVALUATOR_NOT_LEAKAGE_FREE / UNKNOWN`，而不是缩小分母或改写 fixture
> 来制造可运行成功。

## 读取依据

本设计直接读取了根 `AGENTS.md`、`research/NOW.md`、本轮 `PROGRAM.md`、Pro
`G1-return.md` 与 `G1-AUDIT.md`、第一批 CLI `G1-final.md`、当前
`01-boundary-sufficiency-v2.json/.md`、`WAVE-009-G1-DESIGN.md`，并回到
`problem/v1-candidate.json/.md` 与 `problem/v2.json/.md` 核对原问题、\(S_0/Q/operator\)
和 Intent ingress 边界。本文没有修改这些来源，也不改变 NOW、PROGRAM、LineContract 或
任何正式状态。
