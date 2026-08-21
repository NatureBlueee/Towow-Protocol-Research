# T6-G7-ORTHOGONAL-REPLAY-001：研究者 A 的原生 G7 重建

日期：2026-07-29  
角色：内部研究者 A（问题重建与实验合同建议，不实现 runner）  
状态：`CANDIDATE DESIGN INPUT / NOT RUN / NO FORMAL STATUS CHANGE`

## 1. 结论

G7 不是一个 `CURRENT / REVOKED / UNKNOWN / REFUSED / STALE` 路由器，也不只是 durable
workflow 的故障恢复。它要同时回答五个互不自动成立的问题：

1. **reuse**：首次形成后的哪一部分已经稳定到值得编译和复用，第二次运行是否真的降本且
   不增错；
2. **context**：目标执行者得到的是否是带回源引用的最小充分 Context，而不是全量历史或
   无法核验的摘要；
3. **legitimacy**：在 exact operation 的不可逆提交点，当前 Authority、Evidence、Effect
   与 Acceptance 依据是否仍适用；
4. **reopen**：漂移击败了哪些 justification，应该继续、阻断、恢复、局部重开、全局重开
   还是交给 Principal/Authority amendment；
5. **migration**：source runtime 的未结义务能否经中立 capsule 在 target runtime
   重建，并通过 old-runtime fencing 和 reconciliation 避免双执行、丢 Effect 或改写历史。

这五个分面可以由成熟组件、强中心或人工制度完整解决；它们不是必须保留的产品模块，也不
预设新协议。当前可检验的残差只是：在 owner 不被吞并、native response 不免费揭示依赖身份
与隐藏真值时，哪种组合能够以可接受的 assurance tax 实现安全复用和演化。

五态只允许作为一次 **Authority observation 的粗分类**。它不能决定控制动作，因为完全
相同的 `UNKNOWN` 可以分别对应“尚未 dispatch”与“旧 runtime 可能已经造成不可逆 Effect”；
二者的合法下一步不同。

## 2. 实际读取与证据边界

本重建直接核对了：

- 仓库根 `AGENTS.md` 与 `research/NOW.md`；
- 本轮 `PROGRAM.md`，尤其 T6 R1–R8 与 G7 定义；
- `external/chatgpt-pro-cohort-001/G7-return.md`；
- `external/chatgpt-pro-cohort-001/G7-AUDIT.md`；
- `external/codex-cli-cohort-001/G7-final.md`；
- `WAVE-010-G6-G7-AUDIT.md`；
- `WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md`；
- `lines/07-scoped-reopen-v2.{md,json}`；
- 原生档案 `a2a-reconstruction/04_audit/native_lines/07_runtime_and_evolution.md`。

直接观察到的当前边界是：

- Wave 010 的 `7/7` 来自 truth direct-copy、共享 decision implementation 与 fixture-aligned
  closure，只能作为伪满分的历史开发证据；
- T6 当前仍是 `UNKNOWN_NOT_RUN`；没有 cold-vs-repeat、跨 runtime migration、真实 recovery
  或完整 R1–R8 结果；
- X2 合同仍是候选，world 未冻结、runner 未实现；
- 原生 G7 还包含 Context Compiler、稳定子图编译和 Evidence Closure，不能被 Authority
  safety 一面替代；
- 本轮只能产生 local synthetic candidate；不能声称真人授权、现实 Effect、生产恢复、
  长期净价值、正式 LineContract 或 MechanismProfile 状态变化。

## 3. 五个原生分面

### 3.1 Reuse：稳定子图编译，而非 replay 本身

编译资格必须绑定一个不可原地改写的 `RelationVersion`，并逐节点保存：

- exact operation、输入/输出语义与目标版本；
- Principal、Authority Locus、Mandate/Commitment/Reservation 当前依据；
- dependency justification 与 defeater channel；
- Effect intent、semantic effect key、readback 与补偿边界；
- Acceptance owner、对象、标准、goal/effect/version binding；
- source adapter/runtime 版本与可替代路径；
- provenance、freshness budget 和未解 Unknown。

`workflow replay succeeded`、日志存在、版本递增、进程存活或 capsule 可解析都不是复用
成立。必须以同一 goal/quality floor 比较：

```text
reuse_surplus =
  cold reformation cost
  - repeat run cost
  - assurance tax
  - expected drift/error harm
  - opportunity loss
  - migration and governance cost
```

零 unsafe 但每次全局停机，只能是 `SAFE_BY_BLOCKING`，不能算低成本复用。

### 3.2 Context：最小充分、可回源、缺失时诚实失败

Context 是派生视图，不是 truth owner。每个承重字段必须携带：

```text
value or typed absence
source owner / object / version / head
scope and purpose
observed_at / valid_until / freshness kind
evidence or receipt reference
supersedes / conflict / refusal lineage
```

最小性和充分性必须分别检验：

- 删除非承重字段不改变合法动作，支持“最小”；
- 删除任一承重 binding 后，target 必须 fail closed、查询新证据或升级人工，而不是继续；
- target 不能依赖 source runtime 私有数据库、grader truth 或未声明共享内存；
- capsule 字段存在不等于语义保真；只有 target 的真实动作、owner readback 和历史重建能评分。

### 3.3 Legitimacy：提交点的正当性，不是历史 token

至少分离：

- Authority/Principal 的 normative stance；
- 观察者知道什么；
- 查询/披露/行动 channel 实际发生什么；
- evidence freshness、scope、issuer 与 fork；
- Effect 是否未发出、在途、不确定、已确认或需补偿；
- Acceptance 对 exact goal/effect/version 是否仍适用。

一次 fresh read 只证明 query 时刻。只有 effector 在 commit point 验证条件写、lease、epoch
或 fence，才可能关闭该 effector 范围内的 TOCTOU。没有这种能力时，合法结果可以是
`BOUNDED_UNKNOWN`、人工 gate 或退出，不能由 controller 猜测补齐。

### 3.4 Reopen：重开 justification，不删除现实

候选动作空间固定为：

```text
CONTINUE | BLOCK | RECOVER | LOCAL_REOPEN |
GLOBAL_REOPEN | HUMAN_AMEND | BOUNDED_UNKNOWN | SAFE_EXIT
```

局部重开只在以下条件同时成立时可声称：

- public/queryable dependency coverage 足以证明未纳入节点仍安全；
- hidden-edge discovery 的剩余 Unknown 在冻结容忍范围内；
- in-flight Effect 已对账，或被显式纳入 affected closure；
- Acceptance applicability 按 exact object/version 重判；
- 没有未结 compensation/settlement obligation；
- goal、necessary Principals、Authority topology 与核心 identity mapping 未发生物质变化。

否则必须扩大阻断、全局重开或人工 amendment。重开只改变 future applicability；历史
Attempt、Effect、Acceptance、拒绝、Unknown、失败和旧版本必须 append-only 保留。

### 3.5 Migration：迁移语义义务，不复制平台私有历史

中立 capsule 至少保存：

- case/goal/relation/task-graph version；
- active/completed/control node state；
- Authority observation 的完整正交坐标与 raw reference；
- Effect intents、semantic keys、idempotency namespace/horizon、readback witnesses；
- uncertain Effect、timer/deadline、compensation/settlement obligation；
- Acceptance receipt、owner、criteria、object/version 与 supersession；
- refusal/human hold、policy/code/schema/connector version；
- source coordinator epoch、target epoch、fence 和 old-runtime liveness；
- unresolved Unknown、fork、field-loss 与 reconciliation plan。

计划迁移必须先 drain/fence，再 export/import；崩溃接管必须把所有可能已 dispatch 的节点记为
uncertain，并先 fence + readback + reconcile。目标 runtime 不能把“未完成”直接等同于
“未发生”。旧 runtime restart、split-brain、字段 drop/rename 和 entity remap 都必须作为
硬攻击。

## 4. 正交控制模型

### 4.1 Authority observation 只是一面

保留兼容投影：

```text
authority_observation_class =
  CURRENT | REVOKED | UNKNOWN | REFUSED | STALE
```

该值只能由下面坐标派生，不能反向填充它们，更不能直接生成 expected action：

| 坐标 | 最低建议值 | 解决的混淆 |
|---|---|---|
| `normative_stance` | `CURRENT / REVOKED / EXPIRED / SUPERSEDED / NOT_ASSERTED` | Authority 规范断言 |
| `epistemic_state` | `KNOWN / UNKNOWN / AMBIGUOUS / CONFLICTED` | 真值与知识缺失 |
| `choice_or_consent` | `ALLOWED / REFUSED_DISCLOSURE / REFUSED_ACTION / DEFERRED` | 主体拒绝权 |
| `channel_outcome` | `RESPONSE / TIMEOUT / RESPONSE_LOST / UNREACHABLE / RATE_LIMITED / UNAUTHORIZED` | 传输结果不冒充 stance |
| `freshness_provenance` | owner、object、version、head、scope、issuer、observed_at、valid_until、lease-kind | 缓存 TTL 不冒充 lease |
| `authority_consistency` | `LINEAR / FORKED / EQUIVOCATED / UNANCHORED` | 一个“新 head”不代表单一历史 |
| `effect_phase` | `NONE / INTENT_PERSISTED / DISPATCHED / COMMIT_UNKNOWN / CONFIRMED / COMPENSATING / SETTLED` | no-dispatch 与 uncertain Effect |
| `coordinator_state` | epoch、fence status、old-runtime liveness、split-brain risk | 旧执行者是否仍能造成 Effect |
| `migration_phase` | `NONE / PLANNED_DRAIN / CRASH_TAKEOVER / RECONCILING / IMPORTED / REJECTED` | capsule 生命周期 |
| `acceptance_applicability` | owner/standing、goal、effect、object/version、criteria、decision、supersession | wrong-object 与旧接受 |

此外每个 dependency edge 都要保存 `edge provenance / visibility / hardness / coupling /
optional-or-shared-root / affected principal / defeater channel`。这些字段不能由 public API
免费给出；public side 先只见 provider-native response 与 public graph，adapter/方法必须
为其归一化结果和 edge hypothesis 付出查询、披露、等待、人工和维护成本。

### 4.2 动作不是字段查表

动作由至少四个独立谓词共同约束：

```text
admissible(action) =
  legitimacy_at_commit
  ∧ reconciled_effect_obligations
  ∧ acceptance_applicability_or_explicit_nonrequirement
  ∧ closure_safety_under_known_coverage
```

`authority_observation_class=CURRENT` 既不蕴含 Effect 尚未发生，也不蕴含 Acceptance 有效；
`UNKNOWN` 也不蕴含 global reopen。runner 必须执行 query、intent persistence、
dispatch/fence、response loss、readback、closure、reopen、capsule export/import、旧 runtime
restart/fencing 与 reconciliation，grader 再从独立 owner stores 评分。

## 5. T6 R1–R8 的可判定合同

每项返回 `PASS / PARTIAL / FAIL / UNKNOWN / NOT_RUN`；`UNKNOWN` 不得得分，`PARTIAL`
必须列未覆盖闭包。安全硬失败不能被其他普通 world 的成本收益平均抵消。

| 要求 | PASS 的最低运行判据 | 典型失败 |
|---|---|---|
| R1 重复降本不增错 | 对同一可比 goal/quality floor 实跑 cold 与 repeat；repeat 总成本下降，unsafe、duplicate Effect、wrong Acceptance、历史改写均不增加 | 靠 all-stop 降错；只报缓存命中或固定 step |
| R2 offline 不等于规范失效 | 同 native timeout/offline 下，依据 effect/coordinator/migration 等正交坐标选择等待、对账或阻断；不把 unavailable 自动写成 revoked | `UNKNOWN→REVOKED`，或恢复连接就自动 CURRENT |
| R3 撤销及时且保留无关动作 | 撤销在 commit cutoff 前阻断全部真实 affected closure，零 missed reopen；低耦合 world 的无关节点继续，且 over-reopen/成本受控 | stale CURRENT 继续；或任何撤销全局停机仍称 scoped |
| R4 证据失效传播且不改历史 | 未来依赖全部重判；旧 Effect/Acceptance/失败仍可按原 version 重建，future applicability 以追加记录改变 | 覆写旧 head、删除旧 Acceptance、让新证据回填旧 prediction |
| R5 material goal change 回到构成 | goal、criteria、necessary Principal 或 core identity 变化触发 GLOBAL_REOPEN/HUMAN_AMEND；旧 Effect 被当作资产/负债带入 | adapter 把 goal change 当 schema alias；工程目标反向替代原值 |
| R6 hidden dependency | public-identical pair 上不猜标签；通过合法 query/probe 得新观察，或 BOUNDED_UNKNOWN + broad block/human discovery | fixture 泄漏 dependency identity；hidden edge 删除后仍声称局部闭包 |
| R7 高耦合允许全局重开 | shared root、不可逆在途或 provenance 不完整时诚实扩大闭包；与低耦合 world 区分 | 为 reopen precision 强行局部；或所有 world 一律全局停机 |
| R8 Context/history 可移植 | source export、target import、旧 runtime restart、field-drop 攻击后，目标端以 capsule+合法 owner API 重建相同安全行为，且未丢义务 | schema parse 通过即计 portability；迁移 oracle 完美补字段 |

每个方法还必须逐 world 返回：

- unsafe 与 unjustified continuation；
- historical rewrite；
- unresolved/unreconciled Effect 与 compensation/settlement obligation；
- duplicate Effect、in-flight loss；
- missed/over reopen 与 action/closure correctness；
- wrong-object/stale Acceptance preservation error；
- query、disclosure、calendar wait、active human、model/tool、storage、migration、assurance tax
  和 opportunity cost；
- `SAFE_BY_BLOCKING / SAFE_RECOVERABLE / LOW_COST_SCOPED_REOPEN` 结果等级。

## 6. 六个公平基线

六臂共享同一 provider-native API families、任务可见包、时钟、查询/披露/HITL/时间预算和
owner 能力上限，但必须有独立 method executable、独立状态目录和独立 closure implementation。
不得共享 `method_decision()`、expected action、closure helper、truth-derived profile 或
grader object。

| 臂 | 原生能力与允许优势 | 不得免费获得 |
|---|---|---|
| `B0 IMMUTABLE-MONITOR-HUMAN-AMEND` | 不可变合同、原生监控、完整 human amendment；高后果或不确定时可广域阻断/人工重审 | 自动 dependency closure、免费 owner truth、零成本人工 |
| `B1 DURABLE-WORKFLOW-MIGRATION` | durable history/replay、version/migration、outbox/idempotency、telemetry 与 human amendment；Unknown 时 broad block/global reopen | perfect dependency closure、迁移补字段、免费 owner readback |
| `MATURE_COMPOSITE` | durable workflow + policy/versioning + outbox/inbox + conditional fence + owner readback + Saga + explicit Acceptance + dependency planner | 未表达 hidden edge、跨 owner truth、无限 freshness、无成本人工 |
| `EQUAL_AUTHORITY_CENTER` | 集中图、统一计算/运维和 coordinator epoch；与 mature arm 相同 owner API、权限和预算 | 未委托私有真值、额外 standing、grader truth |
| `DELEGATED_CENTER` | 仅在 fixture 明确证明所有承重决定、状态与 Effect control 可合法委托的子域内，使用统一事务与制度能力 | 把不可代行 Principal/Acceptance/外部 effector 自动纳入委托 |
| `HUMAN_RULE` | 冻结 runbook、Standing、升级链、合法线下 Authority channel 和自由语言判断 | grader oracle、无限追问、零等待/零认知成本、rubber stamp |

`DELEGATED_CENTER` 是条件不同但合法的竞争解，应单独分层报告；在不能集中委托的 world
返回 `NOT_APPLICABLE`，不能据此奖惩。若成熟组合、中心或人工制度完整通过且成本更低，应
关闭专用 planner/新协议候选；这是正结果。

`always-continue`、`global-stop`、`workflow/event-green` 另作为 mandatory invalidation
controls，不占六个公平解法臂。前者必须暴露 unsafe，后两者分别暴露 liveness/over-reopen
代价与 Control→Effect/Acceptance 的错误晋升。

## 7. 建议冻结的 20 个高区分 world

首轮应固定在 12–20 个 world；以下 20 个覆盖完整要求，先验证 evaluator 和方法独立性，
不扩到 1500。每个 world 只冻结一个主要判别点；伴随后果可以不同，但 grader 要标出因果主轴。

| ID | 主要判别点 | 方法可见 native 现象 | 私有评分事实与必要区别 |
|---|---|---|---|
| W01 | 低漂移复用控制 | 所有 owner native response 正常、同版本 | stable subgraph 可重复；比较 cold/repeat 成本与零新增错误 |
| W02 | 暂时 offline | Authority query timeout，last-known current | 无撤销、无 dispatch；等待/刷新可行，不能当 revoked |
| W03 | 低耦合 leaf revoke | leaf provider 原生返回 revoked | 只重开 leaf causal cone；全局停机安全但 over-reopen 昂贵 |
| W04 | stale by head | replica 返回旧 head 的 allow/current | canonical owner 已 supersede；必须识别 provenance/freshness |
| W05 | fork/equivocation | 两个都可验签但冲突的 native heads | 不得按“最大版本”选真；进入 conflict、阻断或人工 |
| W06 | refused disclosure | owner 明确拒绝回答，但不撤销动作 | 可探索不依赖披露的路径；不得重复轰炸或映射为 revoke |
| W07 | refused action | owner 明确拒绝 exact operation | affected action 必须停止；不能把 refusal 当 transient 5xx |
| W08 | response loss before dispatch | query/dispatch channel timeout | 没有 intent、没有 dispatch；可安全按 policy 重试查询 |
| W09 | response loss after dispatch | 与 W08 相同的顶层 UNKNOWN/timeout | intent 已持久化且可能 commit；必须 fence/readback/reconcile 后再动 |
| W10 | wrong-object Acceptance | 同一 owner 返回 native accepted receipt | receipt 绑定旧/错误 object version；不得晋升当前 Acceptance |
| W11 | hidden edge valid | public transcript 与 W12 相同 | 未公开 sidecar edge current；保守停机损失复用价值 |
| W12 | hidden edge revoked | public transcript 与 W11 相同 | sidecar edge revoked；无新观察时 continue 为 unsafe |
| W13 | high coupling/shared root | shared-root provider 出现 drift | 不可证明最小闭包，GLOBAL_REOPEN/HUMAN_AMEND 合法 |
| W14 | evidence invalidation | evidence source 过期/被反证 | future applicability 全传播，但旧 Effect/receipt 不可覆写 |
| W15 | material goal/criteria change | native schema 可兼容、字段名近似 | Principal 接受目标从 v1 改 v2；必须回关系构成而非 alias |
| W16 | planned drain migration | source 正常、drain 开始 | old runtime 停新 Effect、epoch/fence、capsule export/import 后接管 |
| W17 | crash takeover | source 无响应、若干 activity incomplete | 部分 Effect commit unknown；target 必须先对账，不能直接 replay |
| W18 | split-brain restart | target 已接管后 source 恢复 | old epoch 必须被 effector fence；否则双执行为硬失败 |
| W19 | capsule field drop | import 成功但 Authority/Acceptance/obligation 字段缺失 | target 必须 reject/import-bounded-unknown；不得由 grader 补齐 |
| W20 | low-risk delegated control | exact delegation、single controlled effector/Acceptance owner | delegated center 可完整获胜；复杂跨域机制的额外成本应受罚 |

覆盖关系：

- no-dispatch vs uncertain Effect：W08/W09；
- stale/fork/refusal：W04–W07；
- wrong-object Acceptance：W10；
- hidden edge：W11/W12；
- low/high coupling：W03/W13；
- planned drain/crash takeover/split-brain：W16–W18；
- migration field drop：W19；
- low-drift control：W01；
- R4/R5：W14/W15；
- 合法中心化正控：W20。

除了 world 主运行，还要做不计入分母的 deterministic metamorphic attacks：

1. world/method/field 名称与顺序 permutation；
2. 五态 label 替换但 native bytes 不变；
3. method alias 检查：两个臂 executable/source/state identity 相同即拒绝架构比较；
4. truth-to-API copy 检查：API 若从 grader row 直接生成，整轮 invalid；
5. hidden-edge delete/shared-root↔optional-leaf swap；
6. source capsule field rename/drop/duplicate 与 target 默认值注入；
7. migration oracle 检查：exporter 读取 grader/source 私有 truth 或 importer 获得 expected
   reconciliation 即 invalid；
8. old-runtime fence bypass、response-order reversal、query-to-commit revoke。

## 8. 分域与信息流

至少使用以下相互隔离的权限域：

```text
owner services
  ├─ Authority/Principal owner stores and native APIs
  ├─ Evidence owner
  └─ Acceptance owner

source runtime
  └─ source coordinator + exporter + source-local history

target runtime
  └─ target coordinator + importer + target-local history

effectors
  ├─ intent/admission endpoint
  ├─ commit-point fence/idempotency registry
  └─ authoritative target readback

grader
  ├─ full dependency/hidden-edge oracle
  ├─ event/defeater schedule
  └─ post-run evaluators
```

owner service 与 grader 分域还不够；native API 必须通过独立状态机实际产生 stale replica、
timeout、response loss、wrong object、fork、refusal、old-head replay 和 query-to-commit
drift，不能从 grader 的 truth row 复制一个标签。Acceptance owner 不得默认等同于 effector、
controller 或 Relation owner。

public side只见：

- public RelationVersion/graph projection；
- provider-native response bytes、status/headers/payload；
- 合法 query、readback、approval 和 human channel；
- 自己持久化的 intent/history/capsule。

public side不能免费见：

- dependency identity 或 hidden edge；
- `CURRENT/REVOKED/...` grader label；
- realized motif/world branch；
- expected closure/action；
- full graph、effect truth 或 Acceptance applicability；
- source runtime 未导出的私有状态。

## 9. 仍不可由本轮区分的边界

即使上述 20-world runner 全部正确，也只支持所冻结本地状态机和 provider simulator 的有界
结论，不能区分：

- 真实组织是否愿意表达 dependency、授予 standing 或接受中心委托；
- 现实 Authority API 的长期可用性、法律效力和维护成本；
- 物理不可逆 Effect 的真实频率和伤害；
- 跨 Temporal/Step Functions/Camunda 的完整活实例语义，而非本地模拟的子集；
- human-rule 在真人团队中的认知负担、冲突与 rubber stamp 分布；
- 20 个 world 之外的 failure correlation、长尾时延和长期净价值；
- 一个中立 capsule 是否应成为新规范、现成 adapter、组织合同还是保持 provider-specific。

对不可查询的私有 revocation paired world，任何同信息方法都不能同时得到零 unsafe 与零
不必要停机。该负结果应保留为信息边界：新增合法观察、commit fence、真实委托、人工裁决、
保险/补偿或退出，都是建设性解；更复杂的 planner 不是免费的真值来源。

## 10. 本角色不支持的状态变化

本文件不支持：

- 把五态晋升为完整控制态；
- 把成熟组合写成已端到端覆盖；
- 从 20-world 合成结果外推真实长期连续性；
- 登记新 protocol/mechanism 或改动现有 LineContract/claim；
- 改写 `NOW.md`、`PROGRAM.md`、历史 Acceptance 或正式状态；
- 将强中心、人工制度或成熟组合胜出描述为通爻失败。

只有真实 runner 通过上述隔离、攻击和逐项 R1–R8 评分后，才能形成
`T6-G7-ORTHOGONAL-REPLAY-001` 的本地候选证据；在此之前状态仍是 `NOT_RUN`。
