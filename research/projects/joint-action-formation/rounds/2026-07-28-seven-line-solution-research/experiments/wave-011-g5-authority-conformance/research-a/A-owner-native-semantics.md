# 研究者 A：owner / Authority / native outcome 语义设计

日期：2026-07-29  
角色：第二批 G5 内部研究者 A  
状态：`DESIGN INPUT / NOT A RUN / NO FORMAL PROMOTION`

本文件只为 `MCB-G5-v2` 小型 discriminator 提供可实现的 owner、Authority 和 native
semantics 设计。它不是 canonical IR，不修改 `NOW.md`、`PROGRAM.md`、LineContract、
MechanismProfile、X1/M01 状态或任何正式主张。

## 0. 结论

最小 discriminator 不应问“哪一个系统能返回统一四值”，而应问三个更窄的问题：

1. 当技术权限完全相同时，方法能否区分“一个 Principal 真正拥有全部 required Authority”
   与“一个不可转委托的外部权利仍由其他 owner 保有”？
2. 方法能否先保存 provider 的原生 outcome/error/version/freshness，再依据任务特定、
   owner-approved mapping 派生业务四值，而不是从 evaluator 或 fixture 预读
   `ALLOW/REJECT/UNKNOWN/DEFER`？
3. 四个 owner 在独立 store/key/process 下发生 reject、revoke、outage 或 fork 时，方法能否
   保留事实所有权、原生负事实、未知和 provenance，并避免把串行重读误称为跨 Authority
   原子快照？

若真实统一 Authority 的强中心获胜、成熟组合获胜、CLM/HITL 或纯人类规则获胜，都是完整
正结果。只有它们在相同信息、权限、预算和 owner 接口下共同留下同一个稳定断点，才存在
进一步机制研究的理由。

## 1. 证据分类

### 1.1 直接本地观察

`[OBS-01]` 当前 G5 LineContract 要求公平提供 RBAC、ABAC、ReBAC、scoped delegation、
approval、contract/version、reservation 和 audit 的完整成熟组合；还要求 policy decision、
实际 operation 与 postcondition 分开 readback。它明确不允许把机器 policy fixture 提升为
现实授权、Commitment、Effect 或 Acceptance。

来源：

- `research/projects/joint-action-formation/lines/05-authority-adapter-v2.json:8-30`
- `research/projects/joint-action-formation/lines/05-authority-adapter-v2.json:60-87`

`[OBS-02]` Wave009 的 B0/B5 `24/24` 是有价值的局部正结果，但运行条件是冻结合成 world、
受信 parent、单进程原子 ledger 和同一 authoring stream。B3A/B3B 是产品“形状”，B5 也不是
实际 OPA/Cedar/OpenFGA/CLM/数据库集成。

来源：

- `experiments/wave-009-g2-g5-crossed-square/README.md:6-21`
- `experiments/wave-009-g2-g5-crossed-square/README.md:55-73`
- `experiments/wave-009-g2-g5-crossed-square/README.md:199-252`
- `external/chatgpt-pro-cohort-001/G5-AUDIT.md:45-82`

`[OBS-03]` X1/M01 目前只被接受为 scoreable-pair freeze candidate。它没有 scoreable
episode、method、runner 或 run，也没有产生真实 owner signature。下一道门是 owner
commitment 与 process allowlist。

来源：

- `experiments/wave-010-x1-m01-freeze-bundle-v0/AUDIT-002.md:1-13`
- `experiments/wave-010-x1-m01-freeze-bundle-v0/AUDIT-002.md:67-74`

`[OBS-04]` Pro 审计已经把三类过强推断拆开：

- typed evidence 与 exact digest 不等于现实 material closure；
- serial read set 不等于跨 Authority simultaneous snapshot；
- 相同管理员/API/数据库权限不等于统一 Authority；
- OPA、Cedar、OpenFGA、XACML 的 native outcome 不能无损、通用地直接映射为业务四值。

来源：

- `external/chatgpt-pro-cohort-001/G5-AUDIT.md:21-43`
- `external/chatgpt-pro-cohort-001/G5-AUDIT.md:105-126`
- `external/chatgpt-pro-cohort-001/G5-AUDIT.md:148-195`
- `external/chatgpt-pro-cohort-001/G5-AUDIT.md:223-256`
- `external/chatgpt-pro-cohort-001/G5-AUDIT.md:330-355`

### 1.2 由观察推出的判断

`[INF-01]` “owner 独立”不能由四个文件名、四个 key ID 字符串或四段签名 JSON 证明。最低
可运行判据必须包含相互独立的 writer capability、private key custody、process lifetime、
head history 和拒绝接口。

`[INF-02]` task-level 四值可以保留，因为它们能区分权威拒绝、证据不可得和有界等待；但它们
只能是带 mapping 证据的派生视图。provider-native record 才是迁移、重放和争议时不可丢失的
一手记录。

`[INF-03]` “完全相同技术权限”的 crossed pair 不能靠移除 P 世界的 API 权限来制造答案。
两边中心必须有相同 CRUD、查询、workflow 和 signer-session 发起能力；唯一差异是某一
规范权利是否可由中心 Principal 合法行使。中心在 P 世界即使能写 `approved=true`，该写入也
不能替代外部 owner 的 non-delegable act。

`[INF-04]` 一个进程挂掉、一个 store 不可读或一个 native engine 报错，均不等于 owner
`REJECT`。这些先保留为 native outage/error；只有 owner-approved task mapping 能判定它是
`UNKNOWN`、`DEFER`、硬阻断，还是某个可继续分支。

### 1.3 本文件的设计提案

下面所有 `[PROP-*]` 都是待实现、待测试提案，不是运行结果。

## 2. E1：Unified Authority / Same-Permission crossed pair

### 2.1 冻结共同部分

`[PROP-E1-01]` U/P 两个 world 必须在以下技术维度 byte-for-byte 相同：

- operation candidate 和 material closure；
- center 的账号、role、CRUD/API/database 权限；
- 可查询 owner endpoint、请求预算、超时和重试预算；
- policy、relation、CLM、reservation 和 target adapter 版本；
- center 可创建 approval/e-sign session，但不能因此被视为 signer；
- 网络故障计划、clock、日志、成本和人类 reviewer availability；
- 被测方法可见的 public packet。

不得在 public input 中出现 `unified_authority=true`、`external_owner=true`、
`expected_outcome` 或业务四值标签。

### 2.2 唯一承重差异

`[PROP-E1-02]`

| World | Authority truth | 中心可做什么 | 中心不可凭技术权限推出什么 |
|---|---|---|---|
| U | 中心 Principal 真实拥有或已获得可转委托的全部 required Authority；不存在仍相关的外部 non-delegable right、acceptance 或 Standing | 可按自身 owner policy/record 直接决定、签署、预留；若所有状态也在单一 consistency domain，可事务闭合 | 仍不能把 execution receipt 当 Effect/Acceptance |
| P | 技术拓扑和中心权限与 U 完全相同，但 `site-data-use-consent` 由外部 owner 保有且 `nonDelegable=true` | 可读写平台记录、创建签署会话、请求外部 owner、协调等待 | 不得自产外部 owner stance、签名或 consent；平台 `approved=true`、workflow green、controller key 均不能替代 |

唯一 primitive delta 存在于 evaluator 私有的 normative owner record 及 owner 自己的签发
行为中，不存在于方法可预读的标签中。

### 2.3 如何让方法合法发现差异

`[PROP-E1-03]` 方法不得猜 oracle，但可通过相同的 lawful discovery API 请求 operation 所需
Authority closure：

```text
GET /authority-requirements?operation_ref=...
→ owner-signed native requirement record
```

U 返回由 center Principal 控制、可转委托的 requirement record；P 返回外部 owner 签发的
`nonDelegable` requirement record。两者都按相同延迟、字节预算和 freshness 规则计费。
这不是给 P 额外 oracle：它就是待比较方法都必须调用的权威来源。若某方法不调用而只凭平台
权限前进，P 中应被 owner oracle 判为 false allow。

### 2.4 三种 strong-center stratum

`[PROP-E1-04]` 为避免把不同强度的中心混成一个 baseline，至少分三层报告：

1. `SC-U1 / UNIFIED-IN-DOMAIN`  
   一个 Principal 拥有全部 required Authority，且权威记录、reservation 和被测 side effect
   都在中心可原子控制的 consistency domain。允许 ACID/CAS 直接闭合。若其成本最低且安全、
   可前进，应判完整胜出。
2. `SC-U2 / UNIFIED-CROSS-SYSTEM`  
   Authority 仍统一，但 CLM、target 或资源系统在事务域外。中心可作全部规范决定，却仍需
   outbox/idempotency/fence/target readback；本地 ACID 只能原子提交 intent。它也可以完整
   胜出，但不能宣称外部 Effect 与本地 commit 原子。
3. `SC-P / SAME-PERMISSION-PLURAL-AUTHORITY`  
   中心拥有与 U 相同的技术权限，但外部 owner 保有 non-delegable right。正确中心退化为
   coordinator：查询、等待、拒绝代签、保存 owner-native evidence。若它通过这种方式完整
   闭合，仍是 strong-center 正结果；若直接自产批准，则失败。

不得加入一个可读 evaluator 私有 truth 的“omniscient center”作为可评分方案；它最多是
无效上界诊断。

### 2.5 E1 最小判定

```text
U:
  center-owned native approval + all other gates valid
  → task mapping may derive ALLOW for the tested stage

P:
  same center-owned approval, no external owner act
  → must not derive ALLOW

P:
  external owner native reject/forbid
  → task mapping should derive REJECT

P:
  external owner service unreachable, no negative owner fact
  → preserve OUTAGE; derived result cannot be REJECT merely for safety

P:
  external owner workflow has a known reviewer/event and deadline
  → mapping may derive DEFER

P:
  external owner native approval on exact material closure, all other gates valid
  → may derive ALLOW
```

安全与 liveness 都必须计分。一个总是停止的中心不能因 P 世界零 false allow 而胜出。

## 3. 四个 owner：独立 truth / key / process 的最低判据

### 3.1 四个 owner 及其唯一事实

`[PROP-OWN-01]`

| Owner process | 唯一事实所有权 | 不拥有 |
|---|---|---|
| `program-coordinator-owner` | program Mandate、program stance、program Commitment、对应 head | calibration resource、validation independence、site-data consent |
| `delta-calibration-owner` | calibration Mandate/stance/Commitment、field-service reservation、fence epoch | program budget、validation verdict、site-data consent |
| `independent-validation-owner` | validator Mandate/stance/Commitment、independence condition | calibration resource、program commitment、site data |
| `site-data-steward-owner` | data-use purpose、scope、retention、nonDelegable consent/forbid、challenge head | program 或 calibration commitment |

assembler、controller、runner、evaluator 均为消费者，不是第五个可覆盖四域的 truth owner。

### 3.2 独立性的可运行判据

`[PROP-OWN-02]` 只有同时满足以下条件，README 才能写“四个独立 owner services”：

1. 四个不同 OS process，分别有 PID/lifecycle/exit record；
2. 四个不同 store root；每个 store 只有相应 owner writer 可写，其他 owner/controller
   只通过接口读；
3. 四把分别生成、分别保管的私钥；controller 与 assembler 不读取 private key；
4. 每个 receipt 绑定 owner ID、key ID、operation closure hash、native state、head、
   issued/effective/observed/expires time 和 previous-head hash；
5. 每个 owner 自己验证本域 CAS/monotonic head；assembler 只验证与组合；
6. 可独立 kill/restart/outage，且单域故障不会改写其他三域 store/head；
7. 每个 owner 至少实际执行一次 `REJECT` 或 `REVOKE`；
8. 可定向产生 fork/equivocation，且 verifier 能把“两份都签名有效”报告为 fork，而不是
   静默选择较大 head；
9. controller 直接改 store、复用他域 key、伪造 owner response 都必须失败；
10. process allowlist 和实际 executable hash/argv 被记录。

在共享同一 UID、同一可写仓库的本地实验中，上述条件只能证明 cooperative process
separation 和普通越界写检测；不能声称抵抗拥有同一目录写权限的恶意本机进程。

### 3.3 owner-native head record

`[PROP-OWN-03]` owner store 的权威记录不保存业务四值，只保存本域原生事件：

```json
{
  "owner_id": "site-data-steward-owner",
  "head": 18,
  "previous_head_hash": "...",
  "operation_closure_hash": "...",
  "native_fact": {
    "kind": "DATA_USE_STANCE",
    "outcome": "OBJECT",
    "reason": "purpose_not_accepted",
    "non_delegable": true
  },
  "issued_at": "...",
  "effective_at": "...",
  "observed_at": "...",
  "expires_at": null,
  "key_id": "...",
  "signature": "..."
}
```

`OBJECT` 是该 owner 的 native stance；只有 mapping 才能把它派生为本 task/stage 的
`REJECT`。

### 3.4 race/fork/outage 的语义

`[PROP-OWN-04]`

- `REVOKE`：新的 authoritative negative/superseding fact；若其 material scope 命中当前
  operation，mapping 可派生 `REJECT` 或 stage-specific block。
- `OUTAGE`：没有得到新 owner fact；保留 transport status、last observed head 和 freshness。
  默认安全执行策略可以停，但评测类别不是 owner Reject。
- `FORK`：同一 owner/epoch 或不可排序 lineage 下存在两个有效签名的冲突 head。保留两份
  native records 和 fork proof；派生层至少不得 `ALLOW`，通常为 `UNKNOWN` 或 human
  adjudication `DEFER`。
- `DELAYED_PUBLICATION`：区分 `effective_at`、`published_at`、`observed_at`；不允许用收到
  时间覆盖规范生效时间。
- `KEY_COMPROMISE`：保存 compromise interval 与领域 adjudication rule；不能把“当前 key
  inactive”映射为所有历史签名自动无效。

## 4. Native outcome preservation：先保存，再映射

### 4.1 统一的是 envelope，不是语义

`[PROP-NAT-01]` 可以统一 transport envelope，但不得把 provider outcome 先压成四值：

```json
{
  "engine": "opa|cedar|openfga|xacml|owner_service|clm|human_rule",
  "engine_version": "...",
  "policy_or_model_version": "...",
  "request_raw_sha256": "...",
  "response_raw_sha256": "...",
  "native_outcome": {},
  "native_error": {},
  "input_completeness": {},
  "source_freshness": {},
  "negative_authority_facts": [],
  "observed_at": "...",
  "provenance": {},
  "mapping": null
}
```

`native_outcome` 和 `native_error` 必须保留 engine-native 字段与 raw bytes hash。禁止 worker
接收 `expected_business_outcome`、oracle 四值、映射后的 fixture 或从文件名/ID 泄漏答案。

### 4.2 owner-approved task mapping

`[PROP-NAT-02]` 四值只由以下独立对象派生：

```json
{
  "mapping_id": "joint-bid.execute.site-data.v1",
  "task_id": "mcb-g5-v2-e1",
  "stage": "EXECUTE",
  "authority_owner": "site-data-steward-owner",
  "mapping_version": 1,
  "accepted_native_patterns": [],
  "forbid_precedence": [],
  "missing_or_error_rules": [],
  "freshness_requirement": {},
  "resolver_events": [],
  "owner_approval_signature": "...",
  "mapping_source_sha256": "..."
}
```

派生器输出：

```text
business_outcome =
  ALLOW | REJECT | UNKNOWN | DEFER | UNMAPPED_NATIVE_OUTCOME
```

`UNMAPPED_NATIVE_OUTCOME` 是 conformance 结果，不是新的 owner stance。运行策略可 fail
closed，但评测不得把它计作正确 Reject。

### 4.3 四个 policy family 的 native 边界

本研究者 A 没有在本轮启动任何真实引擎。以下是基于已审计本地材料形成的 corpus 合同，不是
产品运行结果。

| Provider | 必须保存的 native surface | 禁止的直接映射 | 本研究者 A 的运行状态 |
|---|---|---|---|
| OPA | 完整 structured decision 或 undefined、evaluation error、bundle/policy metadata、输入与 external-data freshness | `undefined/error → REJECT`；自定义 `allow=true` 也不自动证明 owner Authority | `NOT_RUN` |
| Cedar | Allow/Deny、determining policies、errors/diagnostics、forbid/permit provenance、schema/entity version | `Deny → owner REJECT`；忽略 skip-on-error 或独立 permit | `NOT_RUN` |
| OpenFGA | `allowed=true/false`、HTTP/status/error、authorization model ID、consistency mode、tuple/source freshness | `false/400/outage → REJECT`；`HIGHER_CONSISTENCY` 等于跨系统 current truth | `NOT_RUN` |
| XACML | Permit/Deny/NotApplicable/Indeterminate subtype、Status、obligations/advice、combining algorithm、policy set version | `NotApplicable → UNKNOWN`、`Indeterminate → DEFER`、`obligation → Commitment` | `NOT_RUN` |

Wave009 中的 `OPENFGA/CEDAR`、`OPENFGA/OPA` 只是本地 Python shape，不能改写上表为真实运行。
主实现若只接入一个真实本地引擎，应对该引擎写 `RUN` 与版本/命令/原始输出；其他三项继续
明确 `NOT_RUN`，不得从 adapter corpus 生成产品胜负。

### 4.4 无预读 oracle 的运行顺序

`[PROP-NAT-03]`

```text
1. runner 冻结 raw provider request；
2. worker 只收到 request + provider endpoint + budget；
3. provider 返回 native bytes/status；
4. recorder 先不可变保存 raw/native/version/freshness；
5. mapping worker 读取 owner-approved mapping，派生业务结果；
6. evaluator 最后读取私有 truth，分别评分：
   a. native preservation
   b. mapping correctness
   c. stage decision
7. evaluator truth 不回流到 1-5。
```

必须加入 response transplant、mapping-version transplant、stale bundle/model、missing
attribute、transport outage、unregistered native outcome 和 negative/forbid precedence
攻击。

## 5. Material operation closure，而不是单一 digest

`[PROP-OBJ-01]` exact object 扩为 owner-approved material operation closure：

```json
{
  "closure_version": 1,
  "primary_object": {
    "raw_sha256": "...",
    "canonical_sha256": "...",
    "canonicalization_id": "..."
  },
  "canonicalization": {
    "algorithm": "...",
    "version": "...",
    "owner_approvals": []
  },
  "sidecars": [
    {
      "role": "data-use-terms",
      "required": true,
      "raw_sha256": "...",
      "owner": "site-data-steward-owner"
    }
  ],
  "external_dependencies": [
    {
      "dependency_id": "facility-safety-rule",
      "authority_owner": "...",
      "head": 7,
      "fresh_until": "...",
      "materiality": "BLOCK_ON_CHANGE"
    }
  ],
  "materiality_rule": {
    "version": 1,
    "material_paths": [],
    "allowed_variations": [],
    "reapproval_triggers": [],
    "owner_approval_signatures": []
  }
}
```

最少两个 paired controls：

- primary digest 相同、material external dependency 不同：必须暴露 false allow；
- raw bytes 不同、按 owner-approved canonicalization 等价：仅按 raw hash 的方法会产生
  false deny。

一个“完整 JSON schema”仍可能漏 sidecar；因此 closure completeness 是 owner-approved
任务假设，不宣称全世界因果闭包。

## 6. Standing lifecycle 与 late challenge

`[PROP-STAND-01]` 不把 Standing 压成 bool。最小 lifecycle：

```text
UNSEEN_AFFECTED_PARTY
→ CANDIDATE_AFFECTED_PARTY
→ ASSERTED_STANDING
→ PROVISIONAL_STANDING
→ ADJUDICATED_STANDING
→ CHALLENGE_{PENDING|UPHELD|REJECTED|WITHDRAWN}
→ APPEAL_{NONE|PENDING|DECIDED}
```

每一状态绑定：

- stakeholder/representative；
- discovery provenance；
- jurisdiction 和 rule version；
- exact material closure；
- challenge 对 `reserve/commit/execute/settle/accept` 各阶段的 effect；
- adjudicator owner；
- deadline/liveness budget；
- late discovery 时的 reopen、compensation 或 irreversible-loss record。

必须运行：

1. 未预登记 stakeholder 在 execute 前出现；
2. stakeholder 在 Effect 后才被 adjudicator 认定具有 Standing；
3. 合同规则 non-suspensive、监管规则 suspensive；
4. 恶意阻塞 challenge；
5. 被驳回 challenge 后合法路径能够恢复。

安全通过但永久停机不算完整解。CLM/case management/HITL 或纯人类制度只要同时满足合法
challenge coverage 和 liveness floor，可以完整胜出。

## 7. Migration：只声明 witnessed equivalence

### 7.1 不允许的声明

以下结论在本 discriminator 中一律禁止：

- `OPA/Cedar/OpenFGA/XACML are semantically equivalent`；
- `migration is lossless`；
- `canonical IR preserves all policy meaning`；
- `round-trip parse success proves preservation`。

### 7.2 可允许的最强声明

`[PROP-MIG-01]`

> 对已冻结 corpus `C`、source/target engine version、mapping version 与明确列出的 native
> dimensions，迁移前后 observed decisions 一致；该结论是
> `WITNESSED_EQUIVALENCE(C)`，corpus 外保持 Unknown。

receipt 至少包含：

- source raw bytes、provenance、engine/version；
- target raw bytes、provenance、engine/version；
- source 和 target native outcome/error；
- absence semantics；
- negative fact 和 forbid precedence；
- combining、obligation、time、delegation；
- owner/source Authority；
- mapping source/hash/version 和 owner approval；
- corpus、metamorphic、holdout 和 failure case hashes；
- 未映射字段、非单射映射、round-trip loss；
- 一旦发现新差异，旧 receipt 自动降级的 rule。

### 7.3 必须保留的三个差异

`[PROP-MIG-02]`

1. `native Unknown`：例如 unavailable status source、缺失 attribute 或未映射 error，迁移后
   不能为了二值引擎而伪装为 owner Deny/Reject。
2. `forbid/negative fact`：显式 forbid、negative stance、objection 不得退化为“没有 permit”
   或 tuple absence。
3. `provenance`：issuer、owner、source Authority、policy/model version、raw bytes 和
   observed freshness 不得只留下一个目标系统 bool。

任何一项不能重建，migration 仍可作为有损 adapter 使用，但必须出具 loss manifest，并阻止
依赖该丢失字段的自动 `ALLOW`。

## 8. baseline 公平性与胜出条件

`[PROP-BASE-01]` 至少并列比较：

| Baseline | 允许的完整胜出方式 | 不得偷取的能力 |
|---|---|---|
| `SC-U1/SC-U2/SC-P` | 按各自 Authority stratum 正确前进/等待/拒绝，并满足成本和恢复 | evaluator truth、外部 owner key、虚构统一 Authority |
| `MATURE-COMPOSITION` | IAM/PDP/ReBAC/transactional reservation/CLM/case management/target fence 的实际组合闭合 | 把 product shape 当真实产品；给额外 oracle |
| `CLM-HITL` | exact closure、签署身份链、Mandate、challenge、revoke 和人工 liveness 闭合 | e-sign session 创建者冒充 non-delegable signer |
| `HUMAN-RULES` | 人类 owner/审查制度以更低总成本安全闭合低频高后果任务 | 不计人工等待/错误/恢复；把口头同意伪造为签名 |
| `POLICY-ONLY` | 只在其声明的 policy slice 获胜 | 把 Allow 当 Commitment/Reservation/Effect |

成熟组合、CLM/HITL、人类制度是候选完整解，不是弱基线。若其中任一在相同分母完整通过，
应报告 residual 为零或收窄，不得为保留 MCB/通爻增量而提高它的负担。

`[PROP-BASE-02]` 共同指标：

- false allow / false hard reject；
- native outcome preservation 和 mapping confusion matrix；
- `UNKNOWN`、`DEFER`、`UNMAPPED_NATIVE_OUTCOME` 的正确性与可恢复性；
- revoke/fork/outage 后 unsafe continuation；
- liveness、等待、人工分钟、abort/retry、hold time；
- disclosure bytes、owner API calls；
- duplicate reservation 与 stale target Effect；
- Standing coverage 和 late challenge recovery；
- migration field/constraint/behavior/provenance loss；
- 实际维护、restore/export/import 成本。

## 9. 主实现可直接采用的 fixture 草案

```json
{
  "fixture_schema": "mcb-g5-v2-owner-native-discriminator-draft",
  "status": "DESIGN_NOT_RUN",
  "world_pair": {
    "same_public_input_sha256": "REQUIRED",
    "same_center_permissions_sha256": "REQUIRED",
    "only_normative_delta": "site-data-use-consent owner and delegability"
  },
  "owners": [
    {
      "owner_id": "program-coordinator-owner",
      "process_required": true,
      "private_store_required": true,
      "private_key_required": true,
      "faults": ["REJECT", "REVOKE", "OUTAGE", "FORK"]
    },
    {
      "owner_id": "delta-calibration-owner",
      "process_required": true,
      "private_store_required": true,
      "private_key_required": true,
      "faults": ["REJECT", "REVOKE", "OUTAGE", "FORK"]
    },
    {
      "owner_id": "independent-validation-owner",
      "process_required": true,
      "private_store_required": true,
      "private_key_required": true,
      "faults": ["REJECT", "REVOKE", "OUTAGE", "FORK"]
    },
    {
      "owner_id": "site-data-steward-owner",
      "process_required": true,
      "private_store_required": true,
      "private_key_required": true,
      "faults": ["REJECT", "REVOKE", "OUTAGE", "FORK"]
    }
  ],
  "native_provider_runs": {
    "opa": "NOT_RUN_UNTIL_RAW_RECEIPT_EXISTS",
    "cedar": "NOT_RUN_UNTIL_RAW_RECEIPT_EXISTS",
    "openfga": "NOT_RUN_UNTIL_RAW_RECEIPT_EXISTS",
    "xacml": "NOT_RUN_UNTIL_RAW_RECEIPT_EXISTS"
  },
  "forbidden_worker_inputs": [
    "expected_business_outcome",
    "oracle_four_value",
    "authority_valid",
    "unified_authority_boolean",
    "answer_bearing_fixture_id"
  ],
  "required_outputs": [
    "owner_process_receipts",
    "native_provider_receipts",
    "owner_approved_mapping_receipts",
    "material_operation_closure",
    "standing_lifecycle_trace",
    "migration_witnessed_equivalence_or_loss",
    "stage_decision",
    "target_readback"
  ]
}
```

## 10. 接受门与不能支持的结论

### 可接受的最小实现

- E1 U/P pair 只有 Authority ownership/delegability 不同，中心技术权限完全相同；
- 四个 owner 的 process/store/key/receipt/lifecycle 可独立检查；
- worker 从未收到业务四值或 oracle truth；
- 至少一个真实本地 policy engine 保存 native receipt；未接入产品明确 `NOT_RUN`；
- task mapping 有 owner approval、version 和 source hash；
- material closure 含 canonicalization、sidecar、external dependency 和 materiality rule；
- outage/fork/revoke/late challenge/native error/migration loss 都能保留而不被抹成 bool；
- strong center、成熟组合、CLM/HITL、人类规则都拥有公平胜出路径。

### 本设计不能支持

- 四个本地进程等于四个现实 Principal 或法律独立主体；
- owner 签名等于真人理解、自由认领或现实可执行责任；
- serial re-read、lease 或 receipt aggregation 提供跨 Authority ACID；
- fencing token 在未覆盖 target enforcement 时阻止现实 Effect；
- 一个真实引擎通过就代表 OPA/Cedar/OpenFGA/XACML 产品比较完成；
- `WITNESSED_EQUIVALENCE(C)` 等于全语义无损迁移；
- 需要新的通用 Authority 协议、canonical IR 或稳定 G5 residual；
- G5 `ALLOW` 自动推出 G2 Relation、Execution、Effect、Adoption、Acceptance 或 Settlement。

## 11. 给主线程的五个关键判别器

1. **Normative delta discriminator**：相同权限下，U 可由中心闭合，P 必须等待/读取外部
   non-delegable owner；相同判断即失败。
2. **Native-before-mapping discriminator**：没有 raw native receipt 与 owner-approved
   mapping 的业务四值无效；outage/error/absence 不得伪装成 Reject。
3. **Owner independence discriminator**：任一 domain 可单独 reject/revoke/outage/fork，
   controller 无法写其 store 或使用其 key；四文件/四 key ID 不够。
4. **Material closure discriminator**：同 primary digest + 不同 external dependency 与
   不同 raw bytes + canonical equivalent 两组 crossed controls 分别测 false allow/deny。
5. **Witnessed migration discriminator**：保留 native Unknown、forbid/negative fact 和
   provenance；corpus 外保持 Unknown，禁止宣称 canonical/lossless。

