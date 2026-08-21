# Wave 010 X2 输入合同候选：PROSPECTIVE-EPISODE-CLOSURE

日期：2026-07-29  
状态：`CANDIDATE INPUT CONTRACT / NOT RUN / NO SCORED RUNNER`  
对象：`X2 — PROSPECTIVE-EPISODE-CLOSURE`

## 0. 状态与作用域

本文只设计 X2 的输入、truth-owner 边界、公平比较条件与反作弊门，不创建 world、不实现
runner、不产生 coverage，也不改变 `research/NOW.md`、Problem、LineContract、
MechanismProfile 或任何正式研究状态。

本文吸收但不晋升以下输入：

- [`problem/v1-candidate.md`](../../problem/v1-candidate.md) 与
  [`problem/v2.md`](../../problem/v2.md) 的 RelationEpisode、权威不可代行、前态/资格
  谓词冻结、Effect ladder、漂移与净价值边界；
- [`TASK-TRUTH-CORRECTION-001.md`](./TASK-TRUTH-CORRECTION-001.md) 的 E4–E7
  evaluator 约束；
- [`TASK-TRUTH-CORRECTION-002.md`](./TASK-TRUTH-CORRECTION-002.md) 对
  `V0 / BE0 / Q_episode / A_Gi`、V2 Intent 边界、X1→X2 全 population 交接与数量非分母
  的当前正典校正；
- [`WAVE-010-X1-OUTCOME-CONTRACT-v0.json`](./WAVE-010-X1-OUTCOME-CONTRACT-v0.json)
  的 canonical category、lossless reason registry、raw receipt refs 与 fail-closed ingress
  规则；
- [`WAVE-009-G3-DESIGN.md`](./WAVE-009-G3-DESIGN.md) 的 actual-policy、safe-robust、
  Principal policy 与 purpose-limited disclosure 设计；
- [`WAVE-009-G4-G6-G7-DESIGN.md`](./WAVE-009-G4-G6-G7-DESIGN.md) 的 prospective
  prediction、分域 readback、hidden dependency 与 affected closure 设计；
- [`WAVE-009-G2-G5-DESIGN.md`](./WAVE-009-G2-G5-DESIGN.md) 已支持的
  relation/authority 非蕴含边界；
- [Pro 独立返回摘要](./external/pro-wave009-independent-001/RESPONSE-SUMMARY.md)中的
  X1→X2 顺序、未审计运行预算草案和成熟组合公平基线。

外部 Pro 材料是结构化观察摘要，不是 raw response，也不是实验事实。X1 与 X2 目前均未按
该顺序实际运行。X1 outcome contract 本身的状态也是 `CANDIDATE_NOT_RUN`；引用它只冻结
交接 schema，不创建 X1 result。

### Correction 002 修订说明

本版按 Correction 002 与随后的独立审计收窄：

- `V0` 恢复为原始价值与不可接受底线，公平 baseline envelope 只写 `BE0`；
- 全文只使用唯一 `Q_episode`，线路局部条件写成 `A_Gi`；
- Pro 的 64+8/72 明确为 `REJECT_AS_DENOMINATOR`；
- X1 从协调接口内 Intent 开始，不继承 pre-Intent generation；
- X2 population 由每个 arm 自己的 finalized X1 actual outputs 机械形成；
- valid 与所有 typed non-success 一并进入 ingress，执行子集与 blocked branches 分报。
- X1 outcome 逐项采用 v0 canonical category/reason/raw refs；未知 reason fail closed 为
  `UNRESOLVED_SCHEMA`。

## 1. X2 要检验什么

X2 的主问题不是“系统最后有没有显示成功”，而是：

> 对 X1 实际产生的全部 finalized outputs，valid branch 能否在不可预知的能力、权限、
> 资源、执行、接受与依赖变化下，先作出 attempt 前可追责的 reliance prediction，在
> attempt 时重新通过 Authority gate，再由相应 Authority domain 分别重建 Attempt、
> Effect、Adoption、Acceptance 与 Settlement，并对后续 defeater 计算安全的 affected
> closure；Reject、Defer、Unknown、invalid、revoked、expired、Bounded Unreachable 与
> Safe Exit branch 能否不被伪晋升，并诚实进入 BLOCK、等待、恢复、再授权、
> HUMAN_AMEND 或更广范围的 reopen；schema unresolved 能否 fail closed 而不冒充业务结果。

X2 主要区分五种常被压成一个绿色状态的现实：

1. X1 结束时有资格，不等于未来 attempt 时仍有权执行；
2. attempt 前值得依赖，不等于已获授权；
3. workflow/outbox 完成，不等于目标世界发生 Effect；
4. Effect 不等于 Adoption、Acceptance 或 Settlement；
5. 历史路径有效，不等于依赖变化后仍可安全复用或只需局部重开。

## 2. 承重非蕴含

X2 的任何实现都必须保留：

```text
X1 AUTHORITY_VALID_FRONT_HALF_CANDIDATE
  ⇏ G4 RELY
  ⇏ G5 PERMIT
  ⇏ Attempt
  ⇏ Effect
  ⇏ Adoption
  ⇏ Acceptance
  ⇏ Settlement
  ⇏ drift 后 CONTINUE
```

反向也不成立：

- 后来出现 Effect 不能回填 X1 Authority 合法；
- successful readback 不能回填 G4 prediction 正确；
- Acceptance 不能证明 Effect；
- safe reopen 不能修正旧 prediction；
- G7 recovery 不能把一次越权 attempt 变成合法。

只有在同一平台同时拥有所有相关状态、原子更新、closed/version-pinned action grammar，
不存在独立 affected Principal、外部 Adoption/Acceptance、延迟撤销或外部 Settlement，
且平台本身就是 execution/outcome Authority 时，某些层才可在 T5 control 中显式合并。
这种合并必须由 control truth 证明，不能靠产品名或路由标签推断。

## 3. X2 的唯一 population 来源：实际 X1 finalized outputs

### 3.1 禁止手写“成功 relation”

X2 ingress population 不得由 X2 fixture、runner、candidate 或文档作者手写成：

```json
{
  "relation": "FORMED",
  "authority": "VALID",
  "execution_ready": true
}
```

这类对象即使 schema 合法，也不构成 X1 output。X2 主评分只接受
`X1FinalizedOutputEnvelope`，它必须能逐字追到一次实际完成的 X1 run 及其独立 evaluator
receipts。outcome contract v0 的全部 canonical categories——valid、Reject、Defer、
Unknown、invalid、revoked、expired、Bounded Unreachable、Safe Exit 与
Unresolved Schema——都进入 ingress population，不能先筛出成功对象再构造 X2。若 X1
没有运行，X2
可以开发 schema、truth broker 与 mutation fixtures，但状态保持 `NOT RUN`，不得启用主
评分。

允许手写的只有：

- schema conformance test doubles；
- 明确标为 `INGRESS_NEGATIVE_CONTROL` 的伪造、缺失、过期或篡改包；
- T5 direct negative controls。

这些对象都不得进入 scoreable population，也不得被转写成成功 base。

### 3.2 `X1FinalizedOutputEnvelope`

每个 envelope 至少绑定：

```text
x1_program_version
x1_run_id
x1_arm_id
x1_world_id
x1_outcome_contract_id = WAVE-010-X1-OUTCOME-CONTRACT
x1_outcome_contract_version = 0
x1_outcome_contract_raw_bytes_sha256
x1_outcome.schema_version + schema_sha256
x1_outcome.reason_registry_version + reason_registry_sha256
x1_outcome.category
x1_outcome.reason_code
x1_outcome.raw_method_return_bytes_sha256
x1_outcome.line_receipt_refs.G1/G2/G3/G5
x1_outcome.transition_receipt_refs.T_G1_TO_G2/T_G2_TO_G3/T_G3_TO_G5/T_G5_TO_X2
x1_run_manifest_bytes_sha256
x1_frozen_input_bytes_sha256
x1_intent_at_coordination_interface_bytes_sha256
x1_S0_root
x1_V0_bytes_sha256
x1_BE0_bytes_sha256
x1_Q_episode_bytes_sha256
x1_transition_model/action_grammar/envelope/bound hashes
x1_private_oracle manifest refs/hashes
x1_method_id + executable identity
x1_completion/finalization receipt
x1_truth-broker/evaluator versions and public-key identities
Principal/Authority owner receipt roots
raw event-log root
operation/receipt byte roots
X1 source world opaque id
base-family id (oracle-only classification by default)
```

所有引用必须解析为同一 finalized run；只给 score JSON、结论摘要、复制后的 relation
object、同名 run id、文件路径或 controller 自签声明均无效。envelope 还必须冻结实际传输
bytes，而不只冻结解析后的等价 JSON。

X2 的 ingress validator 逐字加载并重新计算 outcome contract v0 的 schema 与 reason
registry hashes，只做完整性、current-head 与跨 receipt 一致性校验。`X1IngressReceipt`
保留以下 canonical categories：

```text
AUTHORITY_VALID_FRONT_HALF_CANDIDATE
REJECT
DEFER
UNKNOWN
INVALID
REVOKED
EXPIRED
BOUNDED_UNREACHABLE
SAFE_EXIT
UNRESOLVED_SCHEMA
```

`reason_code` 必须在 `x1-reason-registry-v0` 中注册于该精确 category，且必须无损保留 raw
receipt 证明的具体原因。不得把 `REQUIRE_APPROVAL / STALE_VERSION /
RESERVATION_REQUIRED / RESERVATION_CONFLICT / REVOKED / EXPIRED` 压成 generic
`G5_DENY/G5_BLOCKED`。

`AUTHORITY_VALID_FRONT_HALF_CANDIDATE` 只接受
`ALL_LINE_OUTPUTS_ACCEPTED_AND_TRANSITIONS_CURRENT`；`BOUNDED_UNREACHABLE` 与
`SAFE_EXIT` 必须保留各自注册 reason，不能合并进 `UNKNOWN/REJECT/INVALID`。

未知 category、reason、category/reason pair、schema version/hash、reason-registry hash 或
缺失 mandatory receipt 一律 fail closed 为：

```text
UNRESOLVED_SCHEMA/UNKNOWN_SCHEMA_VERSION
UNRESOLVED_SCHEMA/SCHEMA_HASH_MISMATCH
UNRESOLVED_SCHEMA/REASON_REGISTRY_HASH_MISMATCH
UNRESOLVED_SCHEMA/UNREGISTERED_CATEGORY
UNRESOLVED_SCHEMA/UNREGISTERED_REASON_CODE
UNRESOLVED_SCHEMA/UNREGISTERED_CATEGORY_REASON_PAIR
UNRESOLVED_SCHEMA/MISSING_REQUIRED_RECEIPT
```

尤其未知 reason 必须是 `UNRESOLVED_SCHEMA/UNREGISTERED_REASON_CODE`（或在 category 已知但
pair 非法时 `UNRESOLVED_SCHEMA/UNREGISTERED_CATEGORY_REASON_PAIR`），不得 normalize 为
`UNKNOWN` 或 `INVALID`。unresolved wrapper 必须保留 attempted raw bytes SHA-256。

所有 G1/G2/G3/G5 line refs 与四个 transition refs 都必须存在；未到达的线也必须给
owner-signed typed `NOT_REACHED` receipt，不能用 null。每个 ref 必须含
`ref/raw_bytes_sha256/owner_key_id/receipt_version/status`，并解析到同一
`run/world/arm/episode anchor/finalized output`。

ingress validator 不能重算或代替 X1 四个 truth owner，也不能把任何 non-success 提升成
valid。X2 method 只得到配置允许的 envelope projection 与 ingress status，不得到 X1
oracle。`AUTHORITY_VALID_FRONT_HALF_CANDIDATE` 也只表示 front-half handoff，不蕴含
execution permission、Effect、Adoption、Acceptance、Settlement 或 `Q_episode`。

### 3.3 ingress population 与两个后续子集

scoreable ingress population 不是预写 world list，而是 X1 结束后机械冻结：

```text
P_X2_INGRESS =
  every finalized (x1_run_id, x1_world_id, x1_arm_id, x1_output_hash)
```

每个 X2 arm 只继承同一 arm 自己的 X1 output。不得把某个 strong center、existing
composition 或 candidate 的成功 relation 复制给其他 arm，也不得删除某 arm 的
Reject、Defer、Unknown、invalid、revoked、expired、Bounded Unreachable、Safe Exit 或
Unresolved Schema 结果来“对齐”成功样本。

冻结后只为报告和执行路由划分：

```text
P_EXECUTION_ELIGIBLE
  = mechanically valid, current AUTHORITY_VALID_FRONT_HALF_CANDIDATE

P_BLOCKED_OR_NON_SUCCESS
  = REJECT | DEFER | UNKNOWN | INVALID | REVOKED | EXPIRED |
    BOUNDED_UNREACHABLE | SAFE_EXIT

P_SCHEMA_UNRESOLVED
  = UNRESOLVED_SCHEMA
```

`P_EXECUTION_ELIGIBLE` 可以进入 G4 prediction 与 G5 gate；`P_BLOCKED_OR_NON_SUCCESS`
仍属于 X2 scoreable population，评价是否保持 non-attempt、是否正确恢复/再授权/等待或安全
终止。不能只报告 `P_EXECUTION_ELIGIBLE`。`P_SCHEMA_UNRESOLVED` 仍保留在 ingress
population，但单独报告为 schema/provenance failure，不能被任何 arm 计作安全业务判断。

### 3.4 G1 条件

每个 X1 envelope 必须从 V2 协调接口内的 `INTENT_AT_COORDINATION_INTERFACE` 开始，并
绑定其原始 bytes/hash。Intent 字段可以是 Unknown，而且以下角色不得预设重合：

- generator；
- represented Principal；
- beneficiary；
- affected party；
- decision Authority。

G1 receipt 还必须保存：

- Intent 的 lawful projection、clarification、qualification、partner-discovery 与 relation
  handoff transcript；
- query/constraint 的 origin、purpose、direction、版本和 provenance（若实际形成）；
- Principal clarification、拒绝、披露与 acceptance 的 owner receipts；
- 任何 purpose-limited disclosure 的 recipient、purpose、projection、retention、
  onward-use、revocation、expiry 与成本。

controller 生成的“Principal 已接受”标签、免费注入的敏感事实或删除义务后保留的 learned
fact 均使相应输出 invalid。Wave 009 的 `vague value seed → query` 只保留为
`G1_EXTENDED_BOUNDARY_LOCAL_SYNTHETIC`；除非独立证明 seed 已满足 V2 Intent 接口，否则
不能作为 X1/X2 的 V1/V2 ingress 证据。T5 direct control 不要求伪造 G1 relation，而走
独立 control contract。

### 3.5 G2 条件

每个 branch 都必须保存 G2 evaluator 的 typed output，而不是 controller 的 `FORMED`
字段。`P_EXECUTION_ELIGIBLE` 中的 RelationVersion 至少绑定：

- horizon：`ONE_SHOT_EPISODE / BOUNDED_RELATION / DURABLE_RELATION`；
- exact version/hash、role、action、purpose、evidence、exit 与 evaluation schema；
- 必要 Principal 对该精确版本的 stance；
- proposal、counter、explain-back、commit 的原始次序与来源；
- contribution provenance、局部 opposition、unresolved challenge；
- material-change、semantic-loss、stale-stance 检查；
- X2 入口时的 current head。

G2 `FORMED` 不替代 G5。durable relation 也不产生 future blanket authority。

### 3.6 G3/QHM-2 条件

每个 branch 的 G3 receipt 必须来自 actual-policy run，而非逐 truth world 的 omniscient
existential path。它至少保存：

- frozen `S0 / V0 / BE0 / Q_episode / A_G3`；
- transition model、action grammar、Authority envelope 与 search/horizon bound；
- operator 分类：
  `EPISTEMIC_DISCOVERY / ACTIVATE_OR_RESTORE / CREATE_CONDITION /
  MUTATE_PROBLEM / INVALID_SUBSTITUTION`；
- 实际 observation→action trace；
- Principal-owned policy version/transitions；
- `R_exists / R_actual / R_effect_robust / R_safe_robust /
  R_terminal_robust` 的分别结果；
- 若声称 condition creation，则保存 unchanged `Q_episode` 下关键 operator 的
  remove/reverse/block 消融。

进入 `P_EXECUTION_ELIGIBLE` 的 branch 还必须满足：

- 实际 trace 已到达一个合格的 exact-operation candidate；
- `R_safe_robust=true` 且 `R_terminal_robust=true`；
- `R_actual` 不是 hindsight path；
- 没有 `MUTATE_PROBLEM` 或 `INVALID_SUBSTITUTION` 冒充原 `Q_episode` formation；
- Principal refusal/defer 分支仍作为合法分支保留。

`R_effect_robust=false` 本身不使整个方法失败：有合法拒绝权时它可以与 safe robust 同时
成立。实际 `REJECT`、`DEFER`、`UNKNOWN`、`INVALID`、`REVOKED`、`EXPIRED`、
`BOUNDED_UNREACHABLE`、`SAFE_EXIT` branch 不进入 attempt，但仍在
`P_BLOCKED_OR_NON_SUCCESS` 中接受 X2 的 non-promotion、恢复或安全停止评价。
`UNRESOLVED_SCHEMA` 单独 fail closed。

### 3.7 G5 条件与时间边界

X1 只能交付“X1 close 时的 authority basis”，不得替 X2 预签 execution-time permit：

- exact action/RelationVersion scoped Mandate；
- Principal、actor entity、controller、Authority Locus 映射；
- Commitment 条件；
- Reservation resource、owner、unique key、lease、expiry 与 current head；
- budget/data/signature/Acceptance authority；
- affected party Standing/challenge/recourse；
- X1 close 时的 revoke head 与验证时间。

这些字段必须来自 X1 G5 truth owner 的原始 receipts。X1 的
`EXECUTION_READY/PERMIT` 只表示 X1 close 那一时点；进入 X2 后它是可失效的历史输入。

## 4. 两个 episode-genesis family

两个 family 用于防止 X2 只适配一种 episode genesis。它们不是两个方法 arm，也不能只靠
identifier permutation 制造。

### BF-A `DISCOVERED_OR_RESTORED_PATH`

- 满足 `Q_episode` 的语义等价路径在 S0 已存在；
- X1 通过合法 discovery、clarification、activation 或 restoration 使其可行动；
- 没有把 world-changing `CREATE_CONDITION` 计作形成；
- relation 与 authority receipts 仍完整存在。

### BF-B `AUTHORITY_VALID_CONDITION_CREATED`

- 在冻结 transition model、action grammar 与 bound 内，S0 不存在满足原
  `Q_episode` 的路径；
- X1 的一个或多个 authority-valid `CREATE_CONDITION` operator 后首次出现合格路径；
- `Q_episode` 与 `V0` 未被降低或改写；
- remove/reverse/block 关键 operator 后路径消失；
- operator 的 Principal/Authority、版本和披露义务可追溯。

`MUTATE_PROBLEM`、controller substitution 和“发现已有路径”不能进入 BF-B。

### 4.1 family 独立性

如果 finalized X1 actual outputs 中实际出现 BF-A 与 BF-B，它们必须分别具有：

- 不同 S0、`Q_episode`、RelationVersion namespace 与 opaque world ids；
- 不同 Authority roots、reservation resources 和 target-domain state；
- 独立 X1 run/envelope/finalization receipt；
- 独立 private truth、dependency graph 与 event schedule；
- 各自的 success、refusal、stale 和 tamper ingress tests。

可共用 schema、evaluator code 与成本口径，不能共用一行隐藏 truth 再只改 family 标签。
任何 family 的 PASS/FAIL 不可用于填充另一 family。某 family 没有从 X1 实际产生时，结果
是该 family 当前 `NO_FINALIZED_OUTPUT`，不得手写补齐，也不得从另一 arm transplant。

Reject、Defer、Unknown、invalid、revoked、expired、Bounded Unreachable 与 Safe Exit
output 可以保留可判断的 genesis family；无法合法分类时记为 `GENESIS_UNRESOLVED`，仍不
从 ingress population 删除。`UNRESOLVED_SCHEMA` 不做 semantic family 推断。

## 5. X2 world 的冻结输入

本文只保留 V1 的单一 episode qualification predicate：

```text
V0 = original desired value + unacceptable floor
BE0 = fair baseline observation/action/authority/cost envelope
Q_episode = V1 episode-level qualification predicate Q
A_G1 ... A_G7 = line-local acceptance predicates
T_Gi→Gj = typed transition contracts
```

`BE0` 是实验变量，不是 V1 的 `V0`。任何 arm 都不能靠降低 `V0`、扩大自己的 `BE0` 或
缩小对手的 `BE0` 获胜。`A_Gi` 只判断该线输出是否满足有界交接条件，不创建新的
`Q_episode`，也不蕴含 `Q_episode`。

从每个 finalized X1 output 派生的 scoreable X2 continuation instance，在 method 运行前
冻结：

```text
world_id (opaque)
base_family (oracle-only by default)
X1 envelope + X1IngressReceipt
X2 S0 and world-entry event index
V0
BE0
Q_episode
A_G1 / A_G2 / A_G3 / A_G4 / A_G5 / A_G6 / A_G7
T_G1→G2 / T_G2→G3 / T_G3→G5 / T_X1→G4 / T_G4→G5 /
T_G5→G6 / T_G6→G7
exact operation bytes/hash
actor / controller / counterparty / beneficiaries / affected Principals
Authority Loci and current-head query endpoints
prediction horizon and episode horizon
declared evidence/probe/approval/readback APIs
declared response families
privacy, reservation, query, human, time and cost budgets
idempotency and causal-identity scope
public dependency graph/version
method-visible packet bytes/hash
private oracle packet bytes/hash
event/defeater schedule commitment
truth-broker/evaluator identities and versions
```

open action world 中的“不存在路径”只相对于冻结
model/grammar/Authority-envelope/search-bound 成立；边界外保持 Unknown。

parent broker 只负责逻辑时钟、事件顺序、attempt admission 与 transport routing/recording。
它不得拥有 target-domain store 的写权限、不得生成 target readback，也不得持有任何
readback signer key。target write 只能由相应 domain owner 接收合法 transport 后执行；
readback 只能由该 domain owner 从自己的 authoritative state 签发。method 不得直接读
private oracle、改时钟、预看未来 drift 或自行写成功 receipt。

### 5.1 标签默认不可见

`base_family`、motif id、paired A/B label、realized branch、oracle expectation 与
applicability truth 默认只存在于相应 private package。method-visible packet 不得包含这些
字段，也不得通过 world id、文件名、ordering、固定数量、错误文本或预算差异旁路泄漏。

只有在某个字段本身就是现实中合法可见的 observation 时，owner 才能通过正式 API 返回其
语义内容；返回内容仍不能携带 fixture label。deterministic permutation 必须攻击这些标签
通道。

## 6. G4：attempt 前冻结 prediction

`A_G4` 只判断 prospective reliance output 是否满足本线交接条件，不创建 permission 或
`Q_episode`。

每个可能进入执行的 operation 都必须先产生不可回填的 `PredictionReceipt`：

```text
prediction_id
created_event_index
exact operation hash
RelationVersion/hash
evidence-head snapshot
authority-head snapshot
reservation snapshot
decision = RELY | BLOCK | ABSTAIN
confidence
expiry
prediction_horizon
selective-coverage class
evidence producer set + correlation groups
probe coverage
assumptions and bounded Unknown
cost/disclosure/human usage to date
receipt bytes/hash/signature
```

冻结顺序为：

```text
prediction receipt committed
→ hidden holdout/drift schedule may advance
→ G5 execution-time gate
→ optional execution attempt
```

任何在 attempt、target readback、Acceptance 或 failure 后生成、重签、改 confidence、缩
response family 或替换 evidence snapshot 的 prediction 都是 `POST_HOC_INVALID`。失败后的
repair 可以成为下一 attempt 的新 prediction，但不能改写前一次。

G4 评价 false reliance、missed viable action、calibration、coverage、abstention、
首次成功/恢复时延与真实 evidence cost。`ABSTAIN` 是合法状态，但 all-ABSTAIN/all-UNKNOWN
必须受预先冻结的 selective-coverage 与 liveness floor 约束。对于决策前合法 observation
完全相同的 paired worlds，不要求方法预知 hidden truth；应评价跨 pair 的 calibrated
safe policy，而不是给 hindsight 分支标签。

## 7. G5：execution-time Authority gate

`A_G5` 只判断当前 exact attempt 的 Authority gate，不创建 Effect 或修正 `A_G4`。

`RELY` 不是授权。每次 attempt 紧前必须由 G5 truth owner 对当前状态原子评价：

- exact operation bytes/hash、purpose、counterparty 与 RelationVersion；
- actor/controller 与 Principal/Authority Locus；
- Mandate scope、signature、expiry 与 current revoke head；
- Commitment 条件是否仍成立；
- Reservation 是否 required、owner-valid、unique、current、未消费且未过期；
- budget/data/account/credential/current identity；
- affected party Standing、challenge、pause 与 recourse；
- idempotency key 与同 causal identity 的既有 attempt；
- human approval 是否来自真正 owner，且绑定当前版本。

输出只能是：

```text
PERMIT
DENY
REQUIRE_APPROVAL
STALE_VERSION
REVOKED
RESERVATION_REQUIRED
RESERVATION_CONFLICT
UNKNOWN
DEDUPLICATED_REPLAY
```

`PERMIT` 必须与 attempt binding、reservation consumption/lease transition 和
idempotency registry 原子提交。gate 未通过时不能创建 execution attempt。policy engine
的 `Allow`、认证账户、旧 X1 receipt、workflow green、G4 confidence 或 controller 摘要都
不能替代该门。

G4 和 G5 采用不同 truth owner。G5 不评分 prediction，G4 不创建 permission。

## 8. G6：五层 authoritative readback

`A_G6` 只判断五层 postcondition readback 是否按各自 truth owner 成立，不反推前序授权。

G6 evaluator 只接收并验证五个相应 domain owner 实际签发的 receipts，不生成 receipt、不
写 target state、不代签任何 owner，也不允许 parent/controller 代签。五个 domain owner
分别拥有自己的 authoritative store、写入规则、signer key 与 readback source。

G6 据此分别重建五层，不允许用一个 `SUCCESS` 字段：

| 层 | 最低 truth owner | 必须证明 | 不自动证明 |
|---|---|---|---|
| Attempt | execution/command authority | exact operation 被合法提交或开始 | Effect |
| Effect | target-domain authority | 目标域指定 postcondition 实际成立 | Adoption |
| Adoption | operational/adopting authority | output 被实际接入、使用或采纳 | Acceptance |
| Acceptance | 有权接受的 Principal/beneficiary | 精确 output/goal/RelationVersion 被接受 | Settlement |
| Settlement | settlement/accounting authority | 约定结算、责任或关闭条件成立 | 长期价值 |

每层 receipt 至少绑定：

```text
layer
authority domain and signer
subject/beneficiary
exact operation + causal id
RelationVersion
acceptance_object_version where applicable
target pre/postcondition or explicit refusal/unknown
event index / observed time / head
source bytes/hash/signature
retract/dispute/supersedes relation
```

workflow、outbox、CDC、CloudEvents 和 event sourcing 是 execution substrate，不是外部
truth owner。G6 必须统一 transaction、workflow retry、message retry、consumer 和 target
write 的 causal identity，区分：

- timeout before target commit；
- Effect 已发生但 ACK/readback 延迟；
- duplicate delivery；
- partial Adoption；
- Acceptance refusal；
- Settlement pending/disputed/retracted；
- Saga compensation 后仍存在的 residual。

没有 authoritative readback 时保持 `NOT_OBSERVED/UNKNOWN/REFUSED`，不能从 timeout 或
workflow status 推断不存在或成功。后到 readback 可以更新 G6 当前事实，但不能回填 G4
prediction 或 G5 gate。

如果某个 T5 control 声称多个层由同一 Authority 合并，仍必须由该 control 的
closed/version-pinned truth 证明 owner 确实同一；不能因为同一进程、同一数据库、同一
workflow 或同一 signer implementation 就自动合并规范层。

## 9. G7：hidden dependency 与 affected closure

`A_G7` 只判断当前 defeater 下的 affected closure 与 safe action，不回填前序
`A_G4/A_G5/A_G6`。

G7 private oracle 独立持有：

- versioned full dependency graph；
- public、queryable 与 hidden edges；
- cycles、shared roots 与 optional leaves；
- affected Principals、Authority heads 与 acceptance dependencies；
- in-flight irreversible actions；
- recovery、compensation 与 migration constraints；
- cross-runtime context portability truth。

candidate 只见 public graph 和配置允许的 evidence/query/probe。依赖变化后，method 输出：

```text
CONTINUE
BLOCK
RECOVER
LOCAL_REOPEN
GLOBAL_REOPEN
HUMAN_AMEND
BOUNDED_UNKNOWN
```

oracle 根据变更时的真实 dependency graph 计算 ground-truth affected closure；candidate
提交的 graph 或 closure 不能成为 scorer truth。`LOCAL_REOPEN` 只有在 dependency coverage
足以证明未包含节点仍安全时才成立；coverage 不足必须 broad block、global reopen、创造
新观察或 human discovery。

hidden-dependency paired worlds 的决策前 public transcript 必须相同：唯一差异是一条未表达
sidecar/account/third-party edge 在 A 有效、B 已撤销。此 pair 的作用不是要求模型猜中 A/B，
而是证明只读公开 evidence 下不存在同时避免 unsafe continue 与 missed reuse 的策略。正确
结果可以是：

- 新增合法 dependency query/probe 后分流；
- `BOUNDED_UNKNOWN` + broad block/global reopen；
- `HUMAN_AMEND`/discovery。

若 fixture 把 hidden edge 泄漏到 method packet，或按 world 分别给 hindsight action，便失去
信息论负控作用。

G7 评价 unsafe continuation、missed/over reopen、recovery latency、in-flight loss、
Acceptance preservation、human load、portability loss、assurance tax 与 reuse surplus。
global-stop/never-compile 受 liveness 和 lifecycle-cost floor 约束。

## 10. Pro 的 16 个 paired motifs：mutation inventory，不是 population

下表只保留为待审计的 prospective mutation inventory，不是已经冻结的 worlds，也不能要求
X1 预先产出正好能填满每一格的成功 relation：

| ID | 主要线 | A / B 的唯一承重差异 | 必须区分或诚实保持的结果 |
|---|---|---|---|
| M01 | G4 | exact-operation probe current pass / held-out regression | calibrated RELY vs BLOCK/ABSTAIN |
| M02 | G4/G5 | permission current head ACTIVE / REVOKED | rely 不能越过 execution-time revoke |
| M03 | G4 | 多独立 producer / 同源相关 receipts | independence rank 与 confidence 不得按数量膨胀 |
| M04 | G4/G5/G7 | same identity recover / owner-key changed | resume vs reauthorize/reopen identity dependency |
| M05 | G5/G7 | schema alias / material goal-Acceptance change | adapter vs Principal amendment |
| M06 | G4/G5 | unique current reservation / expired-or-double reservation | PERMIT vs block/conflict |
| M07 | G4 | current regime / regime shift | history usable vs current evidence/abstention |
| M08 | G4/G5 | attestation current+authorized / attestation valid but permission revoked | revocation dominates |
| M09 | G5 | no change / revoke-or-scope change immediately before gate | TOCTOU recheck blocks stale attempt |
| M10 | G6 | timeout before target commit / timeout after Effect | retry vs readback then no duplicate |
| M11 | G6 | one end-to-end causal id / split retry ids | one Effect vs duplicate/false exactly-once |
| M12 | G6 | Effect only / Effect followed by Adoption | preserve ladder |
| M13 | G6 | Acceptance binds exact output / Acceptance binds stale or different version | accept vs wrong-object rejection |
| M14 | G6 | Settlement complete / pending-disputed-retracted | preserve settlement truth |
| M15 | G7 | hidden dependency valid / revoked, public transcript identical | new observation or conservative Unknown |
| M16 | G7 | optional leaf / shared root with irreversible in-flight action | local vs broad/global reopen |

X1 finalized 后，四个 truth owner 在读取任何 X2 method output 前，分别只依据自己的
private package 对每个 actual ingress output 签发：

```text
C_G4(output) = signed prospective-applicability commitments
C_G5(output) = signed execution-authority-applicability commitments
C_G6(output) = signed postcondition-applicability commitments
C_G7(output) = signed dependency-reopen-applicability commitments

C(output) =
  NeutralApplicabilityComposer(
    public output anchor,
    C_G4(output),
    C_G5(output),
    C_G6(output),
    C_G7(output),
    frozen typed composition rules
  )
```

每份 owner commitment 绑定 owner package/hash、key id、ledger position、source identity、
适用/不适用/Unknown、registered reason 与 raw refs。owner 不得读取其他 owner 的 private
truth。neutral composer 只核验签名、共同 output anchor、版本与公开 typed composition
rules；它没有 private oracle、不能调用 truth helper、不能推断缺失 owner 的结果，也不能
改写任何 applicability commitment。

owner commitments、composer 的 motif mapping 与 composed `C(output)` metadata 默认不向
method 暴露；method 只接收相应 continuation 的合法 public API 与事件。不得以“当前适用
M15-B”之类标签替代真实 observation。

`C(output)` 至少保留原 typed status 的 identity/no-promotion continuation；只有
`P_EXECUTION_ELIGIBLE` output 才可加入需要 attempt 的 prospective motifs。Reject、Defer、
Unknown、invalid、revoked、expired、Bounded Unreachable 与 Safe Exit output 仍有
non-attempt、恢复、再授权、等待或安全终止 continuation；`UNRESOLVED_SCHEMA` 只有
fail-closed schema continuation。

motif 的适用性、A/B truth、holdout、Effect、Acceptance 与 dependency oracle 必须在 X2
method output 前冻结。一个 actual output 可以适用零个、一个或多个 motif；不能为了达到
预设数量改写 X1 output，也不能从其他 arm 借用成功 envelope。最终 scoreable population
数量由实际 finalized X1 outputs、四方 applicability commitments 与 neutral composition
决定，事前不写 64。禁止用全局真值 mega-oracle、共享 `world_factory` 或 combined private
truth object 直接生成 `C(output)`。

M01、M07 和 M15 尤其不能按 world 泄漏 realized answer。部分 pair 检验可观察分流，部分
检验不可区分性与 calibrated policy；evaluator 必须在 manifest 中逐项声明。

## 11. T5 collapse gate 的八项预算草案

T5 不进入 BF-A/B，不要求先伪造 X1 relation。Pro 的八项预算草案可分别检验：

1. 单 Authority、closed grammar、原子 target state 的 direct success；
2. direct authoritative no-match/refusal；
3. 同 causal id 的 exact replay 不产生第二 Effect；
4. 已有平台只缺格式/身份转换，`LIGHTWEIGHT_ADAPTER` 足够；
5. platform 不是 target Effect Authority；
6. 存在独立 beneficiary Acceptance；
7. 存在 delayed external revocation；
8. Settlement/affected Principal 位于平台外。

前三类应允许 `DIRECT_PLATFORM` 胜出；第四类允许 adapter；后四类必须保留必要的
cross-domain chain。比较的是
`DIRECT_PLATFORM / LIGHTWEIGHT_ADAPTER / FULL_RELATION_FORMATION`，不是对象数量。

实际采用的 controls 必须在运行前实例化并冻结；“八个”不是 release requirement。T5 作为
collapse gate 单独报告，不进入正任务平均分或 numerator。

## 12. `64 + 8 = 72`：`REJECT_AS_DENOMINATOR`

Pro 的：

```text
Pro draft: 16 motifs × 2 paired cells × 2 proposed families = 64
           + 8 proposed T5 controls = 72 cells
```

当前正典状态是：

```text
PRO_X2_72 = UNAUDITED_RUN_BUDGET_DRAFT
DENOMINATOR_STATUS = REJECT_AS_DENOMINATOR
RELEASE_REQUIREMENT = false
```

不能再称其为“条件性必要”“候选分母”或“最终可调 denominator”。原因是：

- motifs 尚未全部以实际 `S0/V0/BE0/Q_episode/input/oracle` 实例化；
- BF-A/B 是否以及各有多少实际 output，只能由 finalized X1 runs 给出；
- 每个 arm 必须继承自己的 valid/non-success outputs，不能共享 canonical success；
- identifier/order permutation 是 metamorphic replay，不是新增 truth world；
- T5 是单独 collapse gate，不进入正任务平均分；
- Reject、Defer、Unknown、invalid、revoked、expired、Bounded Unreachable、Safe Exit
  与 Unresolved Schema 不能被 positive-only sampling 删除。

即使未来恰好运行 72 个 cells，world 数量也不能替代：

- X1 真实 output ingress 与答案隔离；
- truth owners、bytes/hash、事件顺序与 executable identity；
- hidden indistinguishability 没有泄漏；
- family 不是标签复制；
- attempt 前 prediction；
- execution-time Authority gate；
- target-domain 五层 readback；
- affected-closure private oracle；
- mutation attacks、成本/liveness floor 与公平 baseline；
- 新任务、跨域迁移、真人 Authority 或生产观察。

实现前必须做 motif orthogonality audit。若两个 motif 在相同前提下没有不同判别力，可以
合并；若一个 motif 混入两个无法归因的变量，必须拆分。但 population 不是由审计后另选一个
固定数字，而是由 finalized X1 actual outputs、四域 owner applicability commitments 与
neutral composition 机械构成。

另做一次 deterministic identifier/event-order permutation 作为 reproducibility replay，
不增加 truth denominator。ingress tamper、post-hoc prediction、receipt promotion 等攻击是
mandatory gates，也不进入正任务平均分。

## 13. baseline arms 与 parity

候选 arms：

1. `A0 DECLARATION_ONLY`；
2. `A1 PROBE_CI_ATTESTATION`；
3. `A2 LAWFUL_OPTIMIZED_STRONG_CENTER`；
4. `A3 DURABLE_EXISTING_COMPOSITION`：
   Temporal 或等价 durable workflow + policy engine + transactional reservation +
   outbox/CDC + target readback + HITL；
5. `A4 GENERAL_MODEL_POLICY_CONTROLLER`；
6. `A5 HUMAN_OPERATIONS`；
7. `A6 CANDIDATE_METHOD`。

T5 controls 另允许 direct platform 与 lightweight adapter。

### 13.1 相同能力边界

A2、A3、A4、A6 必须获得相同的：

- 同一 X1 task/world 的输入、`V0/BE0/Q_episode` 与 truth boundary，但各自只继承本 arm
  的 X1 envelope 和 typed outcome；
- 对各自 outcome 采用相同 X2 projection schema 与 precommitted `C(output)` 适用规则；
- current-head、evidence、probe、readback 与 approval APIs；
- Principal/HITL response family；
- exact operation/action grammar；
- privacy、query、reservation、human、time 与成本预算；
- attempt、retry、recovery 与 migration 权限；
- model/tool/account 类别上限；
- event ordering 与 horizon。

任何 arm 都不能读 private oracle、制造 consent、改变 Principal policy、直接写 target truth
或在 attempt 后重写 prediction。

parity 不意味着给所有 arm 同一成功 relation。若某 arm 在 X1 返回 Reject/Defer/Unknown/
invalid/revoked/expired/Bounded Unreachable/Safe Exit，它在 X2 必须沿自己的 branch 接受
non-promotion、恢复或安全停止评价；Unresolved Schema fail closed。端到端报告分别公开
X1 attrition、execution-eligible subset、blocked branches 与 schema-unresolved branch。

### 13.2 强中心不能被故意削弱

lawful optimized strong center 可以集中计算、使用多个 current general models、solver、
local tools/oracles、privacy query、policy、reservation、durable workflow、target readback
和 HITL。它与 A3 的区别是控制与集成策略，不是少给成熟组件。若 A2 与 A3 因果等价，应报告
等价；不为 candidate 制造独占优势。

### 13.3 existing composition 不能靠产品名通过

Temporal、OPA/Cedar/OpenFGA、outbox/CDC、CloudEvents 或 HITL 的存在不自动形成 truth。
A3 必须通过同一接口实际产生：

- attempt 前 prediction；
- attempt 时 current Authority decision 与 atomic reservation；
- end-to-end causal identity；
- 五层 owner receipts；
- dependency-aware reopen。

允许使用等价成熟产品或本地最小 reimplementation；品牌不进入 evaluator truth。

### 13.4 HITL parity

所有可调用 human/Principal 的 arms 使用相同：

- 可见信息；
- Authority scope；
- response policy/family；
- availability、latency、次数与费用；
- refusal、defer 与 amendment 权。

HITL 不是总会给答案的 oracle，也不能由 controller 代签。human operations arm 同样受
privacy、Authority、时间和不可见 truth 边界。

## 14. truth-owner 与 evaluator 隔离

X2 至少需要四个独立 truth owner：

| evaluator | 私有真值 | 公开输出 |
|---|---|---|
| `ProspectiveRelianceEvaluator` | hidden holdout、operation distribution、prediction order | RELY/BLOCK/ABSTAIN 质量与成本 |
| `ExecutionAuthorityEvaluator` | current Principal/locus/mandate/commitment/reservation/standing state | execution-time gate truth |
| `AuthoritativePostconditionEvaluator` | 五个 owner receipt 的 expected binding、domain/key registry 与验证规则；不持有/写入 owner store | Attempt/Effect/Adoption/Acceptance/Settlement 的 receipt-validation result |
| `DependencyReopenEvaluator` | full graph、hidden edges、in-flight irreversibility | affected closure 与 safe action |

另有非评分的 `X1IngressValidator`。镜像 X1 的 cross-authority 隔离要求，四个 evaluator
必须各自拥有：

- 独立 private package 及 package manifest/hash；
- 独立 signing keyspace；
- 独立 append-only ledger；
- 独立 evaluator source、executable identity 与 source hash；
- 只属于本 domain 的 raw refs、owner registry 与 expected bindings。

四者可以读取同一个 parent event index 与公开 episode anchor，但不得 import、调用或读取
彼此 private truth。尤其禁止：

- 共享 `world_factory`；
- 共享 private-truth dataclass/object；
- 共享 `expected_outcome` row/table；
- 共享返回 truth label 的 helper；
- 一个 package 同时生成四条线的 expected result；
- 用同一个 key、ledger writer 或 source module 伪装为四个 owner。

共享层只允许 schema、canonicalization utility、opaque public coordinates 和 transport
types；这些 utility 不能包含 world mode、expected status、motif、A/B 或 hidden branch。
四个 evaluator 只交换带版本的公开 receipts。

integration/compositor 只能：

- 检查 operation、RelationVersion、causal id 与 event-order 一致；
- 报告跨线矛盾；
- 检查各 `A_Gi` 与 typed transition contracts，并判定 end-to-end episode 是否满足唯一
  预先冻结的 `Q_episode`。

它不能让一个 evaluator 的 PASS 创建另一个事实。

## 15. mandatory invalidation gates

主评分启用前，至少要证明以下攻击会失败或产生预定的诚实状态：

### X1 ingress

- 手写 `FORMED/AUTHORITY_VALID`；
- 只有 score/summary，没有 raw run/finalization；
- X1 `NOT_RUN` 被冒充 finalized output；
- X1 canonical category 被删除、改名或相互提升，尤其漏掉 Bounded Unreachable、Safe Exit
  或 Unresolved Schema；
- 未注册 reason 被 normalize 成 Unknown/Invalid，而不是
  `UNRESOLVED_SCHEMA/UNREGISTERED_REASON_CODE`；
- `BOUNDED_UNREACHABLE` 或 `SAFE_EXIT` 被删除、合并为 generic failure 或提升为 valid；
- 任一 line/transition raw ref 缺失，或 `NOT_REACHED` 使用 null 而非 owner-signed receipt；
- envelope 与 receipt 来自不同 run/world；
- 把一个 arm 的成功 envelope transplant 给另一个 arm；
- method return、event log 或 exact RelationVersion transplant；
- stale X1 head 被写成 current；
- BF-A/B 只换标签或复用同一 private truth。

### G4/G5

- attempt 后生成或修改 prediction；
- 结果揭晓后缩 response family；
- G4 `RELY` 直接创建 G5 `PERMIT`；
- policy `Allow`、旧 token、账户或 workflow completion 替代 Mandate；
- reservation 非原子、重复、过期或被另一 attempt 消费；
- revoke 与 attempt 次序翻转；
- all-ABSTAIN/all-UNKNOWN 绕过 liveness floor。

### G6

- workflow complete/self-report 冒充 Effect；
- performer receipt 冒充 target Authority；
- G6 evaluator 或 parent 生成、代签 owner receipt；
- parent 直接写 target store 或持有 readback signer key；
- Effect 冒充 Adoption/Acceptance/Settlement；
- stale-version Acceptance；
- outbox、CDC、event-sourcing 三份事件被计为三个独立 Effect；
- timeout retry 产生 duplicate Effect；
- Saga compensation 被宣称恢复原 world；
- readback 后回填旧 prediction/gate。

### G7

- candidate public graph 被当作 full oracle；
- hidden edge 删除后仍宣称 local closure 已证明；
- unchanged public transcript 却给方法泄漏 world-specific action；
- shared root 被错作 optional leaf；
- irreversible in-flight action 被无损回滚；
- global stop/never compile 以零风险获胜；
- migration 丢失 Authority、Acceptance 或 dependency context 仍称 safe resume。

### truth ownership 与隐藏标签

- 四 evaluator 共享 `world_factory`、private truth dataclass、`expected_outcome` 或 truth
  helper；
- 四个 private packages 实际共用 keyspace、ledger writer 或 evaluator source；
- 全局 mega-oracle 直接生成四域 `C(output)`；
- neutral composer 读取 private truth、补造缺失 commitment 或重写 owner result；
- `base_family`、motif、A/B、realized branch 或 expected result 出现在 method-visible
  packet、id、ordering、错误文本或预算差异中。

### T5 与路由

- 仅凭 world 名称路由；
- 对 platform-direct case 强制创建 full relation；
- 对 split Authority case 把平台 success 扩大为跨域 Acceptance/Settlement。

## 16. 报告结构与成功判据

结果必须逐层报告，不使用单一 accuracy 或 success rate：

### G4

- false reliance、missed viable action；
- calibration、selective coverage、abstention；
- first-success/recovery latency；
- evidence correlation、probe/disclosure/human cost。

### G5

- false allow/deny、stale execution；
- controller substitution、standing violation；
- duplicate reservation、TOCTOU 与 idempotency。

### G6

- 五层各自的 false promotion/miss；
- wrong Authority、wrong object/version；
- duplicate Effect、readback latency；
- compensation residual、dispute/retraction。

### G7

- unsafe continuation；
- missed/over reopen；
- affected-closure precision/recall；
- recovery/amendment latency；
- context portability、Acceptance preservation；
- assurance tax 与 reuse surplus。

end-to-end `CLOSED` 只能表示该 continuation 的唯一冻结 `Q_episode` 在当前 horizon 内
满足；它不晋升真人、生产、长期有效或一般机制主张。合法的
`BLOCK/REFUSE/UNKNOWN/HUMAN_AMEND/GLOBAL_REOPEN` 不能被平均 accuracy 自动写成失败。

比较必须给 Pareto frontier 与 distribution sensitivity，不宣布普遍 winner。existing stack
完整通过是 V1/V2 的有界正解，并关闭在该作用域重复创造新机制的必要；只有在相同 lawful
输入、Authority、预算和成本条件下出现稳定、因果承重的 residual，才有资格提出新构造。

## 17. 实现前的冻结顺序

建议但尚未执行的顺序：

1. X1 完成实际 blind runs，冻结每个 `run/world/arm/output` 的全部 finalized envelopes，
   不筛 valid 或要求 BF-A/B 数量；
2. 独立 ingress implementer 只按本合同验证 X1 包并冻结完整 `P_X2_INGRESS`；
3. 四个 truth owners 对每个 actual output 分别冻结并签发本域 applicability commitments，
   neutral composer 只按公开 typed rules 形成 `C(output)`；16 motifs 与 T5 条目仅作为待审计
   budget inventory；
4. 做 motif orthogonality、信息泄漏、arm-output provenance 和可观察到的 base-family
   independence 审计；
5. 在读取任何 X2 method output 前，冻结 holdout、Effect、Acceptance、dependency truth、
   method-visible packets、private oracles、bytes/hash、事件 schedule 与 evaluator
   executable identity；
6. baseline implementers 只读取公开合同与方法输入；
7. 先跑 mandatory invalidation gates，再启用 scored runner；
8. deterministic permutation replay 后由独立审查者检查非蕴含与 claim boundary。

在第 1 步前，任何 X2 “成功 relation base”都只能是 conformance test double。本文完成不等于
X2 启动、scoreable population 冻结、runner 存在或任何方案已有覆盖率。

## 18. 当前真实阻塞与开放决定

1. X1 正式 input/output contract 与 actual finalized outputs 尚不存在；本文中的 envelope
   字段需与 X1 最终合同逐项对齐，不能反向要求 X1 伪造已有结果。
2. BF-A/B 是本地综合提出的 semantic family 候选，不是 Pro summary 明示的 family 名称；
   它们只能用于 actual-output 分层，不能成为预填 population。
3. 16 motifs 中 M02/M08/M09、M12/M13/M14 可能存在条件相关；需要 orthogonality audit，
   不因“凑够 16”保留重复项。
4. Pro 的 72 只保留为 `UNAUDITED_RUN_BUDGET_DRAFT`，其 denominator 状态固定为
   `REJECT_AS_DENOMINATOR`；实际 population 只能由 finalized X1 outputs 与
   四域 commitments 经 neutral composition 形成。
5. 真实 Principal、Authority、target domain、长期漂移与生产恢复均未运行。

当前结论保持：

```text
X2_INPUT_CONTRACT=CANDIDATE
X2_WORLDS=NOT_FROZEN
X2_RUNNER=NOT_IMPLEMENTED
X2_RESULT=NOT_RUN
```
