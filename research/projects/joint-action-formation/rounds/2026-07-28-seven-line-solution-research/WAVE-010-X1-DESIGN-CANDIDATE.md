# Wave 010 X1 设计候选：BLIND-JOINT-BID-CROSSOVER

日期：2026-07-29  
状态：`DESIGN_CANDIDATE / NOT RUN / NO RUNNER / NO FORMAL STATUS CHANGE`

## 结论先行

X1 应建立一组**全新、答案隔离、方法中立**的 T4 joint-bid episodes，在同一 episode 上
分别评价 G1、G2、G3、G5，并允许强中心、成熟组件组合、人工 broker 或其他方法完整获胜。

Pro 提出的 `10 paired motifs × 2 × 3 + 6 T5` 只保留为
`DESIGN/RUN BUDGET CANDIDATE`。根据 Correction 002 和独立审计，本设计明确
`REJECT 66 AS DENOMINATOR`：

1. `10 × 2 = 20` 只是尚待实例化和独立冻结的 semantic-world budget candidate，不是真值
   分母；
2. `×3` identifier/ordering permutations 是 metamorphic replay budget，不是新增 world 或
   truth；
3. 六个 T5 cases 是单列的 negative-control/collapse-gate budget，只比较
   `DIRECT_PLATFORM / LIGHTWEIGHT_ADAPTER / FULL_RELATION_FORMATION`，不进入正任务平均分。

因此 `60+6` 不是理论最小、coverage denominator、release requirement 或充分性门。truth
fragments 尚未真正独立冻结前，连 scoreable population 都没有成立。

本文件只冻结设计候选。它没有实现或运行 runner，没有产生 coverage，没有激活 Problem、
Scenario 或 MechanismProfile，也不改变 Wave 009 的正式证据状态。

## 一、来源与证据边界

本设计直接核对：

- [Problem v1](../../problem/v1-candidate.md)：`S0 / V0 / Q`、必要 Principal、formation
  反事实、强中心/制度/人工基线和全生命周期成本；
- [Problem v2](../../problem/v2.md)：V1 加法继承、协调接口外的上游 Intent generation、
  开放 role/action space、平台/中心/制度正基线和三个分析尺度；
- [PROGRAM](./PROGRAM.md) 与
  [TASK-TRUTH-CORRECTION-001](./TASK-TRUTH-CORRECTION-001.md)：T4/T5 当前只是合成规格，
  任务真值、方法输入和 evaluator 必须隔离；
- [TASK-TRUTH-CORRECTION-002](./TASK-TRUTH-CORRECTION-002.md)：保留 V1 单一 `V0` 和
  `Q_episode`，另设实验变量 `BE0`；X1 从 V2 协调接口内 Intent 开始；66 只可作为运行预算
  草案；
- [Wave 009 G1 design](./WAVE-009-G1-DESIGN.md) 及其
  [local synthetic run](./experiments/wave-009-g1-query-genesis/README.md)；
- [Wave 009 G2/G5 design](./WAVE-009-G2-G5-DESIGN.md) 及其
  [second-repair local synthetic run](./experiments/wave-009-g2-g5-crossed-square/README.md)；
- [Wave 009 second return](./WAVE-009-SECOND-RETURN.md)；
- [Pro X1 structured observation](./external/pro-wave009-independent-001/RESPONSE-SUMMARY.md)；
- 当前状态为 `CANDIDATE_NOT_RUN` 的机器输出契约
  [WAVE-010-X1-OUTCOME-CONTRACT-v0.json](./WAVE-010-X1-OUTCOME-CONTRACT-v0.json)；
- 历史 [Wave 003-C joint-bid blind task](./wave-003-c-joint-bid/README.md)。

这些材料支持设计变量与失败假说，不支持 X1 已运行。Pro 返回是本地保存的结构化观察摘要，
不是 raw response；Wave 009 是同一 authoring stream 的局部合成结果；Wave 003-C 的具体
任务、角色和答案已在仓库中可读，不能继续进入 X1 的新冷启动 scoreable population。

## 二、X1 实际检验的有界主张

### 2.1 主张

在一个冻结、有限、有 truth owner 的 joint-bid transition model 中，如果所有方法拥有相同
的 lawful observation/action boundary、Authority envelope、预算与恢复能力，那么：

> 某方法能否从一个已经进入 V2 协调接口的 current tender Intent 出发，发现合格的可替换
> role fillers，形成精确版本的关系，区分既存路径、条件创造和问题改写，并在当前
> Principal/Authority/Commitment/Reservation/Standing 真值下得到
> `AUTHORITY_VALID_FRONT_HALF_CANDIDATE` 或诚实的 refusal/Unknown/safe exit。

X1 输入明确冻结为：

```text
INTENT_AT_COORDINATION_INTERFACE
fields may be Unknown
generator / represented Principal / beneficiary / affected party /
decision Authority may be non-coincident
```

它采用 `PROJECTION_ONLY` 的 G1 边界，不把此前的上游隐式 Intent 感知或生成纳入 coverage。
方法可以从 current tender Intent 进行 projection、clarification、qualification、partner
discovery 和 relation handoff，但不能把这称为 V2 接口外的 upstream Intent generation。

### 2.2 不检验

X1 不检验：

- 现实采购、真人授权、法律充分性、真实提交、Effect、Adoption、Acceptance 或 Settlement；
- G4 前瞻 capability、G6 目标域后置状态或 G7 漂移重开；
- 开放世界中“绝对不存在任何等价路径”；
- 跨故障域 reservation 的线性一致性；
- 自然语言、行业和亿级网络的一般化；
- 通爻、中心、联邦或任何专有对象的先验必要性；
- Wave 009 的 B0/B5 局部正结果能否直接迁移为 X1 正结果。

reachability 结论只能相对于冻结的 transition model、action grammar、Authority envelope、
search bound 和 horizon 成立。

## 三、保留 V1 的单一 `V0 / Q_episode`，另设实验变量 `BE0`

每个未来可能进入 scoreable population 的 episode candidate，都必须在任何 baseline 实现
和运行前冻结：

```text
Episode0 = {
  S0,
  V0,
  BE0,
  Q_episode,
  P_fixed,
  RoleConstraints0,
  PrincipalClosureRule0,
  TransitionModel0,
  ActionGrammar0,
  Horizon0,
  Budget0,
  A_G1, A_G2, A_G3, A_G5,
  T_G1→G2, T_G2→G3, T_G3→G5, T_G5→X2,
  BearingDeltaCertificateRef
}
```

完整冻结内容与实际传输字节分别 hash。solver 只获得 `PublicProjection(S0)`、公开合同和经
`BE0` 允许取得的响应；`S0` 的私有 truth slices 不因此公开。

### 3.1 `S0`

`S0` 是干预前的完整前态 composite，不是公开 brief，也不是一个 synthetic mega-owner
可以代签的权威对象；其规范事实必须来自后文独立 truth fragments：

- current tender/constraint/version head；
- 固定权利主体、受影响主体和 Authority Loci；
- 候选 population 中各实体的局部能力、容量、价格、风险、披露策略和真实控制关系；
- 已存在的语义等价路径、既有关系、工具、adapter、可激活资源和阻断；
- Mandate、Commitment、Reservation、Standing、revocation head；
- 允许的 observation/action graph 和真实资源占用；
- 运行前已经存在但 solver 尚未观察到的事实。

任何 operator 后才创建的事实不得回写 `S0`。任何从 S0 已存在、只是后来被看见的路径只能记
为 discovery 或 activation/restoration，不能记为 formation。

### 3.2 `V0`

`V0` 完整保留 V1 的定义：`original desired value + unacceptable floor`。它是多
Principal 的不可补偿底线集合，不是一个可被总效用抵消的分数：

- tender outcome 和 deadline 的最低要求；
- privacy、目的、保存期、独立性与安全底线；
- 每个 affected Principal 的不可代行权利、拒绝和不可接受损失；
- 不得省略的 evidence/exit/recourse；
- 最大协调、披露、等待、治理与恢复成本边界。

如果方法只有降低 `V0`、删除必要主体或改变验收语义才可行，它没有解决本次
`Q_episode`。有权主体明确接受 material goal change 时，应生成新 episode/new `V0`，而
不是追改本次任务。

### 3.3 `BE0`

`BE0` 是本实验新增的 fair baseline observation/action/authority/cost envelope，不是 V1
概念，也不能改名回 `V0`。它只描述每个 arm 在 S0 中**同等可见和可做的能力边界**，不
描述答案或既存路径。至少冻结：

- 相同 public bytes、current-head/readback endpoints 和目录 snapshot；
- 相同 local projection、purpose-bound local oracle、reciprocal probe 和人类/Principal
  decision interfaces；
- 相同 general models、constraint/planning solvers、workflow/policy/reservation tools；
- 相同 query、model、human、latency、retry、recovery 和 calendar horizon；
- 相同 disclosure vector：origin fact、recipient、purpose、sensitivity、retention、
  onward hops、depth 和 cryptographic leakage；
- 相同 action grammar：ask、search、probe、nominate、counter、activate/restore、
  create-condition、amend、seek mandate、commit、reserve、revoke-check、safe exit；
- 相同 idempotency、freshness、failure injection 和 authoritative response semantics；
- 相同禁区：hidden oracle、truth labels、冒充 Principal、修改 private policy 或绕过 owner。

每个 arm 从独立但字节一致的 S0 clone 开始。除非另立 RelationEcology 复用实验，arm 之间
不得共享前一 arm 已发现的答案。

### 3.4 `Q_episode`

`Q_episode` 是 V1 唯一的 episode-level qualification predicate `Q`，不是某条线的局部
交接条件。例如：

- current tender version 与 `V0` 保持不变；
- deadline/budget/operation/evidence/exit 及后续 Effect/Acceptance witness 资格保持冻结；
- role constraints 被满足，而不是命中一个预写 consortium；
- 精确 operation、前置依赖、待由 X2/G4 前瞻资格化的范围和完整路径资格都属于同一
  episode；
- 必要资源不重复占用；
- 目标域 witness、必要 Principal、Authority 与不允许的 goal substitution 保持不变。

`Q_episode` 可由多个语义等价 path 满足。oracle 必须保存 equivalence class，而不是只
保存一条 reference witness。X1 只建立通向该同一 `Q_episode` 的 front-half candidate；
不能因四条局部 assessment 通过就声称 `Q_episode` 已满足，也不把它缩成 X1-only readiness
predicate。

## 四、冻结 Principals，开放 role fillers

旧 joint-bid 任务把 `PRIME/FIELD/ASSURE` 三个身份直接写进 blind input，这会把 partner
discovery 与 role formation 部分预编译。X1 改为：

```text
P_required(path)
  = P_fixed
  ∪ P_affected(path)
  ∪ P_resource_owner(path)
  ∪ P_liability_and_acceptance(path)
```

- `P_fixed`：任何合格路径都不可替换的 tender owner、既有 rights holders、受影响
  Principals 与既定 target/acceptance Authority；
- `RoleConstraints0`：待填角色的能力、独立性、分离义务、接口、责任、容量、证据与
  incompatibility constraints；
- optional role-filler identity 不作为公开必选项冻结；hidden S0 只冻结实际 population
  和每个候选背后的 Principal/Authority mapping；
- 当方法选择一个 filler 并使用其私有事实、资源或责任时，相应
  `P_affected/P_resource_owner/P_liability` 才进入该 path 的 Principal closure；
- role 可替换不等于 Principal 可替换。role occupant、controller、Agent Entity 和
  Principal 是不同事实；占据某 role 不产生 Mandate；
- 若存在多组满足同一约束的 fillers，任一合格组合都可通过；不得只按 reference identity
  评分。

这既避免把所有 optional identities 预冻结成答案，也防止方法通过更换 controller、删除
受影响主体或把技术角色当权利主体来制造成功。

## 五、四条 line-local acceptance predicates 与 transition contracts

`A_G1/A_G2/A_G3/A_G5` 只是 line-local acceptance predicates。它们不创建四个缩小版
Problem，也不与 `Q_episode` 竞争；任一 `A_Gi=PASS` 都不能单独或合取推出
`Q_episode`。

### 5.1 `A_G1` — lawful discovery handoff

G1 truth owner 冻结 latent complement、expression state、actual disclosure policy、
lawful observation/action graph、current heads 和 horizon。line-local target set 是：

```text
D_actual(S0, BE0, policy, budget, horizon)
```

而不是全部 latent opportunity。

G1 的合格输出只能是：

- current、purpose-bound、来源可追溯的 `CANDIDATE_NOT_COMMITMENT`；
- `UNEXPRESSED / UNKNOWN / UNWILLING_TO_DISCLOSE /
  POLICY_UNDISCOVERABLE / BOUNDED_ABSENT` 等有证据边界；
- 不得偷渡 capability、relation formation、Mandate 或 Commitment。

开放 population 中沉默不能写成 `ABSENT`。合法 transcript 完全相同的 paired worlds 必须
输出相同的 calibrated `Unknown/Reject/Defer`；只有独立 oracle 证明冻结范围内全部合法
observation/probe paths 被 policy 阻断时，才可写 `POLICY_UNDISCOVERABLE`。

### 5.2 `A_G2` — relation semantics

G2 truth owner 独立冻结：

- role/action/purpose/evidence/exit/evaluation constraints；
- one-shot/bounded/durable horizon；
- semantic equivalence classes 与 material-change oracle；
- proposal、ack、explain-back、counter、opposition 和 exact-version stance；
- contribution provenance 与编译损失。

G2 合格输出是精确 `RelationVersion` 或 typed pending/reject，不是 workflow green。ACK、
explain-back、stance、Commitment 和 acceptance 互不蕴含。

### 5.3 `A_G3` — causal reachability and operator class

G3 truth owner 独立冻结 transition system、action grammar、search bound、hidden operators、
S0 中的 `Q_episode`-path 集合和 remove/reverse/block counterfactual。输出至少区分：

- `EPISTEMIC_DISCOVERY`；
- `ACTIVATE_OR_RESTORE`；
- `CREATE_CONDITION`；
- `MUTATE_PROBLEM`；
- `INVALID_SUBSTITUTION`；
- `BOUNDED_UNREACHABLE / UNKNOWN`。

只有在相同 `V0/Q_episode` 下，S0 不存在语义等价合格路径，authority-valid operator 后
首次出现路径，且移除、反转或阻断该 operator 后路径消失，才能标为 formation。存在性、
actual-policy reachability 与 robust reachability 分别报告；X1 不把其中一个替代其他两个。

### 5.4 `A_G5` — current authority gate

G5 truth owner 独立冻结并评价：

- Principal、Agent Entity、controller、delegation 与 Authority Locus；
- action/purpose/resource/time/counterparty/RelationVersion scoped Mandate；
- versioned stance、Commitment；
- owner-issued、unique、current、leased、可撤销的 Reservation；
- affected Principal Standing、challenge 与 recourse；
- X1 handoff-gate 时刻的 current revoke head。

输出可以是 `X2_HANDOFF_ELIGIBLE / DENY / REQUIRE_APPROVAL / STALE_VERSION / REVOKED /
RESERVATION_REQUIRED / CONFLICT / UNKNOWN`。policy `Allow`、身份认证、relation formed 或
workflow complete 都不得推出 `X2_HANDOFF_ELIGIBLE`。这个命名只表示 G5 的 X1 内部
handoff gate 通过，不是任何 attempt-time 或执行授权；X2 必须在真实 attempt 前再次运行
G5 execution-time gate。

### 5.5 Line transition contracts

四条线共享 exact episode anchor，但不共享 PASS：

1. `T_G1→G2`：G1 handoff 只携带候选与当前 evidence；G2 必须独立解释关系语义；
2. `T_G2→G3`：G2 版本绑定实际采用的 G1 evidence，但不能从 handoff 推断路径可达；
3. `T_G3→G5`：G3 path 绑定 exact RelationVersion 并列出所需 authority obligations，不能自行
   满足这些 obligations；
4. `T_G5→X2`：G5 在 X1 handoff gate 时重新读 current head，不继承早期 authorization；X2
   仍须在 attempt 前再次检查；
5. 任何 line receipt 的 world、version、principal closure、source bytes 或 head 不一致，
   integration fail closed。

`T_G5→X2` 还必须为每个 arm 的 valid、Reject、Defer、Unknown、invalid、revoked 与 expired
分支保存 finalized 原始 bytes，绑定 `run/world/arm/output` hash 以及该次
`S0/V0/BE0/Q_episode/input/model/oracle/evaluator/owner receipts`。X2 只能继承本 arm 的
实际输出，不能共享 canonical successful relation、手写等价对象或旧 head；X2 的 holdout、
Effect、Acceptance 与 dependency truth 必须在读取 X1 方法输出前独立冻结。

### 5.6 Integration decision，不新增第二个 Q

integration evaluator 不新增另一个 episode-level qualification predicate。它只能根据四条
local assessments 与 typed transition contracts 作 X1 交接决定：

```text
AUTHORITY_VALID_FRONT_HALF_CANDIDATE, only if:
  V0 unchanged
  candidate still targets the same Q_episode
  A_G1, A_G2, A_G3, A_G5 each accept its bounded output
  all typed transition contracts are valid

otherwise preserve one exact typed outcome:
  REJECT / DEFER / UNKNOWN / INVALID / REVOKED / EXPIRED /
  BOUNDED_UNREACHABLE / SAFE_EXIT / UNRESOLVED_SCHEMA
```

即使返回 `AUTHORITY_VALID_FRONT_HALF_CANDIDATE`，也只说明 X1 front half 有资格交给 X2；
它不说明 `Q_episode` 已满足，更不是 submission、Effect 或 Acceptance。integration 不能把
任何 line PASS 反向晋升为另一个 line truth。

完整输出字段、枚举、receipt bindings 与 lossless serialization 以
[WAVE-010-X1-OUTCOME-CONTRACT-v0.json](./WAVE-010-X1-OUTCOME-CONTRACT-v0.json) 为机器契约。
它当前仍是 `CANDIDATE_NOT_RUN`，引用不构成运行结果。报告可以聚合统计，但传输值不得用
generic non-success 覆盖 `BOUNDED_UNREACHABLE`、`SAFE_EXIT`、`REJECT`、`DEFER`、
`UNKNOWN`、`INVALID`、`REVOKED`、`EXPIRED` 或 `UNRESOLVED_SCHEMA`；X1→X2 必须逐字节
无损传递具体 category、reason code 和原始 method return hash。

四条 line receipts 和四条 transition receipts 始终必填；未到达的线也必须提供 owner-signed
typed `NOT_REACHED` receipt，不能写 null。未注册 category/reason pair、schema hash 或 reason
registry hash 不匹配时必须 fail closed 为 `UNRESOLVED_SCHEMA`，不能归一化成
`UNKNOWN/INVALID`。正向 category 只允许精确 reason
`ALL_LINE_OUTPUTS_ACCEPTED_AND_TRANSITIONS_CURRENT`。

## 六、四个独立 truth owner/evaluator

最低结构是四个 truth-owner/evaluator pair，而不是一个 world factory 生成四列答案：

| Domain | Truth owner 私有持有 | Evaluator 只判断 | 明确不得读取 |
|---|---|---|---|
| G1 | local facts、表达、policy、observation graph、`D_actual` | discovery/handoff 与披露边界 | G2/G3/G5 truth |
| G2 | role constraints、semantic equivalence、version/horizon、stances | relation stage/materiality/provenance | reachability/authority verdict |
| G3 | transition model、S0 path、operators、counterfactual | causal class 与 bounded reachability | G2/G5 PASS |
| G5 | Principal/locus、delegation、Mandate、Commitment、Reservation、Standing、revoke | current authority outcome | relation/formation verdict |

实现时必须满足：

- 四个 private truth package、四个 keyspace、四个 ledger 和四个 evaluator source 独立；
- evaluator 只能读取本线 oracle、public episode anchor 和冻结后的 method transcript slice；
- 不存在可被四线 import 的 `expected_outcome`、`world_mode` 或共享 truth dataclass；
- neutral episode assembler 只校验 exact bytes、shared coordinates 和 hash，不计算任何 line
  verdict；
- 第五个 integration evaluator 没有 hidden truth，只消费四个签名 line returns 与
  transition-contract bindings，不能修复或反向晋升任何 line；
- evaluator 在评分时只看到 opaque arm id；成本账本在 correctness 冻结后合并；
- pair scoring 只能读取各 owner 已签名的 `BearingDeltaCertificate`；neutral assembler
  不能自行宣布某 truth fragment non-bearing；
- truth/evaluator 作者不得实现被评分方法。若现实资源只能做到同一 authoring stream，结果
  必须如实标成 `STRUCTURALLY_SEPARATED_SAME_AUTHORING_STREAM`，不能宣称独立 evidence。

四线需要共享同一个 `episode_anchor_hash`，但 sharing coordinate 不等于 sharing truth。

## 七、20 个 semantic-world design/run budget candidates

下列十组是待实例化 motif candidates，不是已经冻结的 truth population，也不是公开 world
labels。实际运行若获准，solver 只见 opaque episode id 和方法中立接口。

### 7.1 `BearingDeltaCertificate`

cross-authority 审计否定了“一个字段变化，所以其他 line truth 相同”的推断。每个 pair 在
进入 scoreable population 前必须有一份由相关 truth owners 分域签名的
`BearingDeltaCertificate`：

```text
BearingDeltaCertificate = {
  certificate_id,
  motif_id,
  left_episode_anchor,
  right_episode_anchor,

  changed_fragments: [{
    truth_owner_domain,
    owner_receipt,
    canonical_path,
    left_bytes_ref,  left_sha256,
    right_bytes_ref, right_sha256,
    first_effective_event_index,
    owner_local_event_index,
    effective_time_or_head
  }],

  method_visible_equality_policy: {
    compared_surfaces,
    comparison_interval,
    exact_bytes | canonical_semantic_equivalence | allowed_divergence,
    left_transcript_hash,
    right_transcript_hash,
    policy_owner_receipts
  },

  initially_affected_line_set,
  downstream_propagation: [{
    from_fragment,
    through_transition_contract,
    to_line_or_outcome,
    causal_reason,
    first_affected_event_index
  }],

  scoring_mask: {
    A_G1, A_G2, A_G3, A_G5, integration
  },

  non_bearing_fragment_equality_proofs: [{
    truth_owner_domain,
    canonical_path,
    left_sha256,
    right_sha256,
    owner_signature
  }]
}
```

规则：

- `changed_fragments` 必须指向 changed owner、canonical path 和实际 content-addressed bytes，
  不能只写人工标签；
- event index 同时绑定 parent global order 与 owner-local order；“上游已经完成”必须由
  assessment seal 的 index 早于 delta 生效 index 证明；
- `method_visible_equality_policy` 按 surface 和时间区间声明相等或允许分流，不能笼统写
  “public input 相同”；
- `initially_affected_line_set` 必须沿 `T_Gi→Gj` 和 outcome contract 做因果闭包。无法证明
  不传播时，保守加入 affected set 或 mask，不能默认为 unaffected；
- `scoring_mask` 每线只可为 `SCORE_DELTA / SCORE_PROPAGATED / SCORE_INVARIANCE /
  MASK_NOT_COMPARABLE / SPLIT_REQUIRED`；
- `SCORE_INVARIANCE` 同时需要 method-visible equality 和本线 owner 签名的 non-bearing
  fragment equality proof；changed owner 或 neutral assembler 不能替其他 owner 证明相等；
- `MASK_NOT_COMPARABLE` 表示不得用 pair 差分评价该线；单个 episode 只有在自己的 truth
  已独立冻结时才可另行评分；
- `SPLIT_REQUIRED` 表示两侧必须改成独立 episodes，不能保留 pair claim；
- certificate、owner receipts、event indexes、scoring mask 和实际评分输入一起进入 completed
  run seal。缺 certificate 的 motif 只能是设计候选。

### 7.2 十个 motif 的审计后处置

| Motif | 审计状态 | bearing delta 与必然传播 | 允许的 scoring mask / 拆分条件 |
|---|---|---|---|
| M01 indexed / local-unexpressed | `CONDITIONALLY_ACCEPTED` | G1 index/expression owner 的 projection path/bytes 在其 event index 改变；G1 handoff evidence bytes 可能沿 `T_G1→G2` 传播 | `A_G1=SCORE_DELTA`。只有 G2/G3/G5 各自证明 semantic candidate、path、Principal/authority fragments 等价，且声明允许不同 handoff evidence provenance 时，才可 `SCORE_INVARIANCE`；否则逐线 `SCORE_PROPAGATED`、mask 或 split |
| M02 zero-disclosure exists / absent | `REPAIR_REQUIRED` | G1 latent-fact owner 改变存在性；method-visible lawful transcript 必须全程相等，但 latent path 可能直接改变 G3 reachability，且没有 handoff 时 G2/G5 不可比 | `A_G1=SCORE_INVARIANCE`，正确输出相同 calibrated `Unknown/Reject/Defer`；`A_G3` 必须显式 `SCORE_PROPAGATED` 或 split；G2/G5 默认 `MASK_NOT_COMPARABLE`。只有独立闭包证明后才可输出 `POLICY_UNDISCOVERABLE` |
| M03 reciprocal complement / direction decoy | `REPAIR_REQUIRED` | G1 direction/complement truth 改变 candidate handoff，并自然传播到 G2 relation eligibility、G3 reachability 和 path-specific Principal closure/G5 | 默认 affected set 为 `{G1,G2,G3,G5,integration}`。若只想检验 G1，必须在 terminal G1 outcome 截断并 mask G2/G3/G5；不得声称后续 truth 相同 |
| M04 semantic no-op / material delta | `REPAIR_REQUIRED` | G2 semantic owner 改变 materiality/RelationVersion；version、purpose、evidence、exit 或 independence 会传播到 G3 path 和 G5 scoped authority | `A_G2=SCORE_DELTA`，G3/G5 为 `SCORE_PROPAGATED` 或 split。G1 只有在 delta 生效晚于 sealed G1 handoff 且 G1 owner/visible transcript 均等时才可 `SCORE_INVARIANCE`，否则 mask。若 V0 或 Q_episode bytes 改变，pair 必须 split |
| M05 mutual exact stance / ACK mimic | `CONDITIONALLY_ACCEPTED` | G2 stance owner 的 explain-back/stance bytes 在 relation event index 改变；没有 formed relation 时不存在可直接比较的 downstream handoff | `A_G2=SCORE_DELTA`。G1 仅在其 assessment seal 早于 delta 且 G1 fragments/visible transcript 等价时 `SCORE_INVARIANCE`；G3/G5/integration 默认 mask。若要评价 downstream，拆成各自拥有完整 truth 的 episodes |
| M06 pre-existing hidden path / condition-created | `REPAIR_REQUIRED` | G3 owner 改变 S0 path/operator truth；它可能同时改变 G1 可发现对象、G2 所需关系和 G5 对 operator 的 Authority obligations | 默认只 `A_G3=SCORE_DELTA`，G1/G2/G5 mask；若任一 upstream/downstream line 进入评分，必须由该 owner 证明 non-bearing equality 或将 motif split。不能再声称“两者其他 line 相同” |
| M07 condition-created / V0 mutation | `REPAIR_REQUIRED` | G3 operator classification 与 V0/Q adjudicator 共同承重；非法 goal substitution 还会改变 G2 materiality 与 G5 的 Principal recognition/authority | 若两侧 V0 或 Q_episode bytes 不同，立即 `SPLIT_REQUIRED`；若 V0/Q_episode 相同而一侧 operator 试图越界改写，`A_G3=SCORE_DELTA`，G2/G5 按实际传播评分或 mask，G1 默认 mask |
| M08 admissible filler / controller substitution | `REPAIR_REQUIRED` | G5 Principal/delegation owner 改变 controller authority；同一差异也可能改变 G2 provenance/Principal closure 和 G3 operator authority-validity | affected set 至少 `{G2,G3,G5,integration}`；G1 默认 mask，只有 G1 owner 证明 candidate evidence 不依赖 controller/Principal fragment 才可 invariant。G2/G3 不得因 role label 相同而写相同 truth |
| M09 unique / duplicate reservation | `REPAIR_REQUIRED` | G5 resource owner/ledger 改变 reservation bytes；资源冲突会改变 G3 actual reachability 和最终 handoff，未自动保证 G2 不受影响 | `A_G5=SCORE_DELTA`、`A_G3=SCORE_PROPAGATED`；G1/G2 默认 mask，只有各 owner 给出 non-bearing equality proof 才可 invariant。若 duplicate 改变 relation commitments 或 participant stance，必须 split |
| M10 active / revoked-at-gate | `CONDITIONALLY_ACCEPTED` | G5 revocation owner 在明确 event index 改变 current head，直接传播到 `T_G5→X2` 与 outcome | `A_G5=SCORE_DELTA`、integration=`SCORE_PROPAGATED`。G1/G2/G3 只有各自 assessment seal 早于 revocation、method-visible inputs 在其区间相等、对应 owner fragments 相等时才可 invariant；否则 mask/split。不得无证据宣称历史 relation/path 相同 |

若一个所谓 permutation 改变了非交换事件的因果顺序，它不再是 replay，必须登记为新的
semantic-world candidate 或 failure mutation。

这 20 个候选被设计为攻击关键非蕴含，但在每个 motif 尚未用
`S0/V0/BE0/Q_episode/input/oracle/BearingDeltaCertificate` 实例化、四线 truth fragments
尚未独立冻结和审核前，
不能说它们“覆盖”了这些非蕴含。即使未来全部运行，也不证明跨行业迁移、开放 population
完备性、所有 Standing 拓扑或分布式 reservation。

## 八、`×3` 只是 metamorphic replay budget

若一个 semantic-world candidate 最终被独立冻结，可为它预算最多三次等义 replay：

- `P0`：随机 opaque IDs 与一种合法的独立事件顺序；
- `P1`：对 entity/run/receipt IDs 作新的双射重命名，并置换 candidate 列表；
- `P2`：再次重命名，并只交换因果上可交换的 disclosure、probe 或 receipt 到达顺序。

这些 replay 的设计要求：

- 三次必须绑定同一 finalized semantic truth hash，但使用不同 public presentation hash；
- world id、长度、字段出现、错误码、签名者顺序、成本和时延不得编码 A/B branch；
- permutation mapping 只由 neutral presentation owner 持有，四个 evaluator 不靠 motif 名称
  评分；
- 三次结果语义必须一致；任一不一致记 `PERMUTATION_FRAGILITY`；
- P1/P2 不进入 truth population，只进入 metamorphic replay consistency。

未来只有在 scoreable population 实际 finalized 后，才可按实际数量报告：

```text
line_assessment_exactness:        line × finalized scoreable episodes
front_half_integration_exactness: finalized scoreable episodes
metamorphic_replay_consistency:   registered replay families
t5_collapse_gate:                 separately finalized controls
```

`20 × 3 = 60` 只是最大运行预算候选，不得写成 60 个 worlds、60 份 truth 或 coverage
denominator。

## 九、六个 T5 negative-control budget candidates

下列六项只是待实例化的 T5 run-budget candidates。T5 使用另一套 parent-owned
authoritative platform truth，不经过四线 oracle：

| Control | authoritative state | 正确 route |
|---|---|---|
| T5-01 | exact standard request、current SKU、buyer authority active | `DIRECT_PLATFORM` |
| T5-02 | current platform authoritative `NO_MATCH` | direct readback 后 safe terminal |
| T5-03 | native schema 差一个可逆格式映射，平台仍拥有全部 truth | `LIGHTWEIGHT_ADAPTER` |
| T5-04 | buyer authority missing/revoked | platform deny，不构造 relation 补权 |
| T5-05 | same idempotency key + same exact bytes | idempotent replay，无重复 effect |
| T5-06 | same idempotency key + changed bytes | conflict，不能覆盖旧 request |

若这些 controls 被独立冻结，所有通用方法都必须先执行 route test。强制
`FULL_RELATION_FORMATION` 可作为诊断 arm 运行，但在 T5 上创建第二 truth source、额外
relation/authority objects、额外披露或审批即失败；它不能靠输出更多对象获胜。

T5 correctness 优先于成本；在都正确时再比较新增等待、认知、披露、治理和恢复负担。T5
必须单列，不进入正任务平均分。即使六项未来全部运行，也只能支持对应冻结平台模型的旁路，
不支持真实 SaaS/支付平台的一般结论。

## 十、公平 baseline arms

所有 arms 使用完全相同的 `BE0`：

1. `B-DIRECTORY`：directory/catalog only，作为局部诊断，不冒充强基线；
2. `B-CENTER`：authority-aware strong center，可使用 current general models、全部合法
   local oracles、planner/solver、workflow、policy、transactional reservation 和 HITL；
3. `B-COMPOSE`：local projection/privacy matching + directory + CMMN/CLM/BPMN +
   planner/adapter + OPA/Cedar/OpenFGA 类 policy + scoped delegation + Commitment +
   transactional Reservation + HITL；
4. `B-LOCAL-PRIVACY`：local projection、privacy match 与 reciprocal probe 的专门组合；
5. `B-HUMAN`：expert human broker，保留其隐性知识与社会合法性，同时计时、等待和错误；
6. `B-CANDIDATE`：不预设实现；可以等同或退化为以上任一成熟组合；
7. T5 另有 `B-PLATFORM-DIRECT` 权威路径。

parity gate：

- 强中心和成熟组合都能使用全部合法工具，不给 candidate 独占 local oracle、模型或 solver；
- privacy、Authority、预算、deadline、query/response、recovery 和 readback 完全相同；
- 同一 method-neutral output schema、同一 correctness evaluator、同一 failure injection；
- baseline 不因“成熟”获加分，candidate 不因“新”获加分；
- 规则建模、adapter、人工审批、会议、等待、治理、恢复和机会成本进入同一 ledger；
- 只有 correctness/critical bottomlines 相同后才比较成本；
- B-CENTER 或 B-COMPOSE 完整获胜、并列或更便宜，都是通爻的正结果；
- 只有两者在公平 access 下出现同一、稳定、可复现 residual，才允许设计新机制候选。

目录单项、弱 workflow 或缺 reservation 的 policy arm 可以暴露局部合同，但不能用于证明
成熟技术失败。

## 十一、blind/oracle 隔离

### 11.1 冻结顺序

1. 冻结本设计与 method-neutral schemas；
2. 四个 truth owners 分别生成并 seal private truth packages；
3. 各相关 owner 为 pair 分域签发 `BearingDeltaCertificate` fragments；neutral assembler
   只验证签名并冻结 episode anchors、public projections 与 replay maps；
4. 建立只含 transport 的 disjoint dev fixtures；未来 scoreable truth 不进入开发包；
5. 冻结 baseline/candidate source、模型版本、工具与 `BE0`；
6. 在新的 run identity/keyspace 下运行方法；
7. 先 seal exact method return 和 transcript，再开放 oracle 给对应 evaluator；
8. line returns seal 后，integration evaluator 才运行；
9. correctness 冻结后合并 arm identity 与 cost ledger。

### 11.2 solver 权限域

solver 只可读取：

- public episode packet；
- method-neutral schemas；
- `BE0` 中声明的 endpoint；
- 自己产生的 transcript 与 receipts。

它不可读取：

- scoreable episode construction source；
- private truth packages、motif/branch/permutation maps；
- evaluator source、expected labels、failure-mutation list 的实例参数；
- 其他 arm 的输出；
- parent broker object、private key、ledger 或内存。

实际运行必须使用进程/文件白名单或更强隔离。Python 同进程 public API 不是 hostile
isolation；若仍同进程，只能声明 cooperative/non-reflective contract，不能把 blind 当安全
事实。

### 11.3 反答案塑形

- scoreable episode 不复用 Wave 003-C 的 PRIME/FIELD/ASSURE、城市站点、价格、request types 或
  reference witness；
- opaque IDs 使用每次 run 的 fresh secret mapping，不含 `valid/stale/revoked/material`
  等坐标；
- public schema 不出现 `authority_valid`、`formation_mode`、`expected_outcome` 等 truth
  字段；
- A/B 分支保持相同字段形状、长度类、非语义时延和错误外壳；
- truth response 只经 lawful owner interface 返回；合法 query 获得的信息不算 leakage，
  bypass policy 或从 metadata 猜中才算；
- evaluator 和 method 不共享 helper，其公共依赖只限 canonical bytes、hash、signature
  verification 和 transport primitives；
- baseline authors、truth authors、evaluator authors与最终综合者的重叠必须报告。

## 十二、failure mutations

mutation 不创建 truth population；它们攻击 harness 或方法的失败闭合。至少覆盖：

| 类别 | 注入 | 必须结果 |
|---|---|---|
| input binding | S0/V0/BE0/Q_episode bytes 或 episode id transplant | `HARNESS_INVALID` |
| oracle isolation | solver import evaluator/truth，或 same-process reflection 触及 parent | run invalid，不评分 |
| identifier leakage | branch 与 ID/长度/顺序相关，重命名后答案变化 | permutation gate fail |
| baseline parity | 只给 candidate oracle/tool，或缩短 center budget | 整个比较 invalid |
| bearing delta | changed owner/path/bytes 或 effective event index 与 certificate 不符 | pair `HARNESS_INVALID` |
| propagation mask | 删除 affected line、伪造 non-bearing equality、给 masked line 计分 | pair score invalid |
| G1 query injection | parent 注入 oracle-derived query/candidate | G1 run invalid |
| G1 indistinguishability | M02 两侧相同 transcript 却输出不同 | leakage/false inference |
| G1 freshness/privacy | stale index、越权 disclosure、open-world `ABSENT` | method fail |
| G2 sequence/cardinality | missing/duplicate/reordered proposal、ack、explain-back、stance | fail closed |
| G2 semantics | material/no-op truth、version、opposition 或 contribution transplant | fail closed/new version |
| G3 counterfactual | remove/reverse claimed operator 后 `Q_episode` path 仍存在 | formation claim fail |
| G3 goal substitution | 修改 V0、Q_episode、必要 Principal 或 search bound 后沿用旧 verdict | method/harness fail |
| role/Principal | controller 代签、role occupant 冒充 Principal、遗漏 affected Standing | G5 deny/challenge |
| G5 non-implication | policy Allow 当 Commitment/Reservation，或 relation formed 当 `X2_HANDOFF_ELIGIBLE` | method fail |
| G5 TOCTOU | early valid receipt 后 revoke head 前移 | X1 handoff gate revoked；X2 仍须重检 |
| reservation | sequential duplicate、真实并发竞争、lease expiry | 唯一成功或 bounded conflict |
| cross-line | 强制上游 PASS、交换 line receipt、version/head/world 不同仍 ready | integration fail closed |
| completed run | 改 stdin/stdout、operation log、任一 owner ledger、exit 或 output | seal invalid |
| T5 | 删除 authoritative state、重复 effect、same-key changed bytes 覆盖 | bypass fail closed |

mutation 结果必须区分：

- `HARNESS_INVALID`：隔离、绑定、parity 或 oracle 失效；
- `METHOD_FAILURE`：方法在有效 harness 中违反 gate；
- `EXPECTED_SAFE_BOUNDARY`：正确拒绝、Unknown、冲突或 safe exit。

不得把 harness 失败记为 baseline 失败，也不得把总是停止当安全成功。未来 scoreable
population 与 T5 collapse gate 都必须包含需要前进的正例，形成 liveness floor。

## 十三、Wave 009 可以复用什么

复用仅限不承载答案的 infrastructure pattern：

| Wave 009 资产 | X1 可复用 | 禁止直接继承 |
|---|---|---|
| G2/G5 `common.py` 的 canonical bytes、SHA-256、签名 envelope 验证 | 作为独立审查后的中性 primitive | 固定 namespace、固定 key、带 hidden coordinate 的 `opaque_id` |
| subprocess worker 的 exact stdin/stdout capture | transport pattern | 现有 runner、arm registry、world packet |
| section/event context binding | exact world/version/head/source bytes 绑定思路 | 现有 relation/authority event 及其 expected sequence 作为 X1 答案 |
| completed-run evidence anchor/seal | exact input/output/ledger/exit seal 思路 | parent 内存 key 被描述成恶意本机不可篡改证明 |
| 独立 broker keyspace/ledger | 四线隔离模板 | 现有两个 broker 类、private world dataclass 和同一 world factory |
| reservation race probe | failure mutation 结构 | 单进程结果外推为分布式保证 |
| G1 disclosure vector/Pareto accounting | 成本和披露字段 | G1 worlds、strategy、evaluator、`D_actual/H` 标签 |
| G1 authority-evidence scope binding | purpose/version/current-head 绑定思路 | static fixture keys、query-genesis truth、同进程 gateway |
| T5 authoritative state/readback/idempotency | internal negative-control prototype | 把该本地类称为真实平台，或让它携带 T5 expected answer |
| residual matrix fail-closed decision | harness validity gate 形式 | 复用 Wave 009 的 11 行结果、固定数量 release gate 或把 `no residual` 当 X1 先验 |

必须新建而不能复用：

- scoreable episodes、角色/主体、domain skin、truth labels 和 replay maps；
- 四个 line truth packages 与四个 evaluators；
- `S0 / V0 / BE0 / Q_episode / A_G1 / A_G2 / A_G3 / A_G5 /
  T_G1→G2 / T_G2→G3 / T_G3→G5 / T_G5→X2`；
- `BearingDeltaCertificate`、owner-specific equality proofs、causal propagation 和 scoring
  masks；
- strong-center、mature-composition 和 candidate 的 X1 实现；
- blind run secrets、trusted anchors 与 failure-mutation instances。

尤其禁止直接复用：

- G2/G5 `world_factory.py`、`baselines.py`、现有 evaluators；
- G1 `worlds.py`、`strategies.py`、`evaluator.py`；
- Wave 003-C `blind/input.json`、oracle、controller responses、角色名与 reference witness。

复用前要重新审查公共 helper 是否携带固定 salt、world mode、error text、truth-shaped schema 或
import alias。复用代码的 hash 进入 manifest，但 checksum 只证明 bytes，不证明隔离或设计
正确。

## 十四、评分与结果语义

当前没有 scoreable population，因此下列只是未来运行的评分顺序，不带固定数量：

1. 四 evaluator 分别只对 `BearingDeltaCertificate.scoring_mask` 允许计分的 finalized
   episodes 给出 `A_G1/A_G2/A_G3/A_G5` 的 typed exactness、false closure、false refusal、
   Unknown calibration 和 line-specific metrics；masked lines 不进入 pair 差分；
2. integration 对同一 finalized episodes 只判断
   `AUTHORITY_VALID_FRONT_HALF_CANDIDATE` 或 outcome contract 中一个具体、无损的 typed
   non-success code；
3. 已注册的 identifier/ordering permutations 只判断 metamorphic replay consistency；
4. 实际 finalized 的 T5 controls 单列 route、correctness、额外
   objects/disclosure/steps/cost，不进入正任务平均分；
5. 只有 critical truth 全对后才比较 disclosure、human judgment、latency、governance、
   recovery 与 lifecycle cost。

任何下列情况都使相应运行不能支持有效 X1 front-half 结果：

- oracle leakage、baseline access 不公平或 completed-run seal 无效；
- `BearingDeltaCertificate` 缺失、changed bytes/event index 不匹配、affected-line closure
  不完整或 masked line 被计分；
- 任一 unauthorized disclosure/controller substitution/false authority；
- material goal substitution 被记为 formation；
- duplicate reservation 或 revoked gate 被放行；
- G1/G2/G3 任一局部成功被 integration 静默提升；
- T5 direct/adapter 可解却被强制 full relation；
- liveness floor 上通过全部 Unknown/global stop 获得“安全”。

允许且必须保存：

- strong center 完整获胜；
- mature composition 完整获胜；
- 两者并列；
- directory/单项组件只覆盖局部合同；
- candidate 没有新增价值；
- policy 下信息论不可发现；
- bounded unreachable、Unknown、refusal、safe exit；
- lifecycle cost 使正确但更重的方法失去净值。

只有在 B-CENTER 与 B-COMPOSE 获得完全相同 access，且失败稳定定位到同一个非蕴含跨越，
failure mutations 能复现，人工/平台也未无损覆盖时，才登记
`NEW_BOUNDED_MECHANISM_CANDIDATE`。X1 本身不能自动晋升机制。

## 十五、`REJECT 66 AS DENOMINATOR`

### 唯一允许的数量表述

```text
20 semantic-world candidates
× up to 3 metamorphic replays
+ 6 separately reported T5 collapse-gate candidates
= DESIGN/RUN BUDGET CANDIDATE ONLY
```

不能由此推出 theoretical minimum、coverage denominator、release requirement、
statistical confidence 或 sufficiency。

原因：

- motifs 尚未全部以
  `S0/V0/BE0/Q_episode/input/oracle/BearingDeltaCertificate` 实例化；
- 四条线的 truth fragments 和 evaluators 尚未真正独立冻结；
- permutation 是 replay，不是新增 truth；
- T5 是单列 collapse gate，不进入正任务平均分；
- 20 个 motifs 即使实例化，也不能代表开放行动世界、真实行业、所有 Standing 拓扑、跨域
  迁移和长期漂移；
- 同一 authoring stream 即使全绿也不是独立产品 evidence；
- 本地 owner/broker 不是真人 Principal、真实平台或外部 Authority；
- G4/G6/G7 未进入 X1，不能声称 episode closure；
- 未覆盖的多元交互可能产生新 residual。

未来只有在 truth fragments、episodes、input/oracle、owners 与 evaluators 实际冻结后，才可
根据实际 finalized population 报告“运行了 N 个 scoreable episodes”；N 不需要等于 20，
replay 与 T5 仍须单列。baseline parity、failure mutations、exact-byte seals 和范围诚实是
运行有效性条件，但它们不会把 66 变成 release denominator。

当前状态保持 `DESIGN/RUN BUDGET CANDIDATE / NOT RUN`。

## 十六、实现前 handoff

下一步若获准实现，不应直接从 runner 开始。顺序应是：

1. 由不同 owner 分别写四份 method-neutral truth/evaluator contract；
2. 独立 truth-fragment/scoreable-population reviewer 检查每个实际 episode 是否只改变一个
   可归因 bearing fragment，复核因果传播和 scoring mask，并决定哪些 episode/line 有资格
   进入分数；
3. 冻结 fresh task skin、`P_fixed`、role constraints、V0、BE0、Q_episode 和 T5 platform；
4. 由各 truth owners 分域签发 `BearingDeltaCertificate` 与 non-bearing equality proofs；
5. 冻结 baseline parity 与 blind filesystem/process boundary；
6. 先完成 oracle-leakage、certificate/mask transplant 和 unequal-access attack；
7. 再分别实现 strong center、mature composition、人工基线接口和 candidate；
8. 最后实现 runner 与 integration，不能让 runner/world factory 同时生成答案。

当前没有执行上述步骤：

```text
X1_DESIGN = CANDIDATE
RUN_BUDGET = DESIGN_CANDIDATE_ONLY
SCOREABLE_POPULATION = NOT_FINALIZED
SEMANTIC_EPISODES = NOT_CREATED
BEARING_DELTA_CERTIFICATES = NOT_CREATED
TRUTH_OWNERS = NOT_CREATED
EVALUATORS = NOT_CREATED
OUTCOME_CONTRACT = CANDIDATE_NOT_RUN / REFERENCED
BASELINES = NOT_IMPLEMENTED
RUNNER = NOT_IMPLEMENTED
X1_RUN = NOT_RUN
COVERAGE = NOT_AVAILABLE
FORMAL_PROMOTION = NONE
```
