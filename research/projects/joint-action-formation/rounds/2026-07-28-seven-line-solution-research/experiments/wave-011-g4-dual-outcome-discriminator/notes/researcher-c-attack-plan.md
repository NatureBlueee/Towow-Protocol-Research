# Researcher C：G4 dual-outcome discriminator 敌对审计计划

状态：`INDEPENDENT_ATTACK_PLAN / IMPLEMENTATION_REQUIRED / NO_FORMAL_PROMOTION`

角色边界：本文只定义 mutation、可执行测试与通过门；不实现 runner，不生成 private oracle，
不改变 `NOW.md`、`PROGRAM.md`、LineContract 或正式机制状态。

## 一、总攻击判断

本轮最容易产生伪成功的不是某个错误分类规则，而是 evaluator 在方法行动之前已经替方法完成了
最难的工作：

1. 把 raw owner/provider response 预裁决成 `head_current`、`fenced`、`authoritative`、
   `safe_to_rely` 等布尔值；
2. 把“首次成功兑现”与“权威地知道成功或失败”压成一个安全标签；
3. 只比较初始 packet，便把主动查询、形成 commitment 后可以分流的世界写成不可能性；
4. 让 mature composite 与 strong center 共用同一决策函数，或给予不对称的 Authority channel；
5. 把 recovery action 的字符串与 oracle label 相等当作恢复正确；
6. 把同一陈旧缓存的多个包装字段当作多个独立证据；
7. 用随机 ID、seed 或重复 trajectory 扩大运行数，却没有增加新的因果边界。

所以，本 pilot 的首要成功标准不是某臂分数高，而是 evaluator 能被下列 mutation 刺穿，并在
移除 mutation 后恢复；若攻击不能稳定改变评分，harness 没有分辨力，不得扩量。

## 二、必须冻结的四个事实与三段时间

每个 world 的 private oracle 至少分别保存：

- `Y_success`：冻结 exact operation 的首次 attempt 是否在 horizon 内产生预注册成功 executor
  result，且 authoritative postcondition 成立；
- `Y_resolution`：horizon 内是否到达预注册、可由权威 owner 重建且不存在未识别副作用的
  terminal state；
- `Y_effect`：目标权威域中的实际 postcondition 是否发生；
- `Y_acceptance`：有权接受该结果的 Principal/owner 是否接受。

四者不得互相推出。典型必要反例是：

```text
authoritative REFUSED_NO_EFFECT
Y_success=0, Y_resolution=1, Y_effect=0, Y_acceptance=0
```

以及：

```text
machine changed state, response lost, owner status unavailable
Y_success may be 1, Y_resolution=0, Y_effect=1, Y_acceptance=0
```

每条 trajectory 还必须保留三段谱系：

- `P0`：任何形成动作前，对原冻结 tuple 的 prospective prediction；
- `I`：实际执行的 query、Authority request、commitment、reservation、fence、submit、
  recovery 与 readback；它们可能改变世界；
- `P1`：`I` 后对新 tuple/new frozen snapshot 的预测。

`I` 成功不得回填 `P0`。恢复后的成功也不得把首次 attempt 的 `Y_success=0` 改成 1。

## 三、pair 类型必须分开

### P — passive pair

初始 packet 相同，且允许的 passive reads 在 horizon 内返回相同 transcript。它只检验静态或
只读方法是否从名称、顺序、case ID、隐藏 label 或未计费字段偷答案。

通过门：

- packet、可见 schema 与所有 passive response 的 canonical bytes 分别相同；
- 任一确定性只读臂若在 pair 内给不同 decision，标记 `HARNESS_LEAK`；
- 此门不能支持对主动策略的不可能性结论。

### A — active-query/commitment pair

初始 packet 相同，但合法 query/request 可以得到不同 raw response，或形成 commitment 后改变
后态。它检验 query planning 和 condition formation，不是不可能性。

通过门：

- oracle 分开保存 intervention 前后 truth；
- evaluator 验证方法实际调用 primitive，不能从 fixture 获得 response 的解释；
- 不调用区分性 primitive 而从初始 packet 猜中的方法，在 rename/order mutation 后必须失效；
- 合法 reservation/commitment 形成的新 safe state 只能计入 `formation success + P1`。

### H — full-lawful-interaction-equivalent hard pair

对决策 horizon 内每个合法 action history，两世界的允许动作集合与 raw response distribution
均相同，且形成动作也不能改变相反的预注册 truth。只有此类 pair 可以支撑不可区分性结论。

通过门：

- auditor 枚举有限 action grammar，或对所有可达 action prefix 做 bisimulation check；
- 仅初始 packet hash 相同不合格；
- 若发现任一合法分流 response，该 pair 自动降级为 active pair；
- 对 `Y_success` 相反的 hard pair，确定性臂必然在 false reliance 与 safe recall loss 中至少
  承担一个；随机臂只报告相同 decision distribution，不把随机猜中当突破。

三类 pair 分别出 confusion/cost 表，不得合并成一个总体“paired accuracy”。

## 四、primitive API 的 no-free-oracle mutation

公共 primitive 只允许返回 owner/provider 的 raw response，例如：

```json
{
  "source": "policy-owner-A",
  "object_ref": "policy/prod/refund",
  "revision": "r17",
  "observed_at": 42,
  "status_code": 200,
  "body": {"rule": "CURRENT_SECURITY_HEAD_REQUIRED", "allowed_digest": "d9"},
  "signature": "opaque-receipt"
}
```

禁止直接返回：

```text
head_current, permission_current, authority_valid, fence_valid,
readback_authoritative, recovery_correct, safe_to_rely
```

这些是 arm 必须从 raw receipt、source contract、object binding、revision 与时间关系中重建的
判断。

| Mutation | 注入 | evaluator 必须发现 |
|---|---|---|
| `M-RAW-01 PREJUDGED-CURRENT` | broker 增加 `head_current=true`，但 raw head/policy 实际冲突 | fixture validation 直接拒绝预裁决字段 |
| `M-RAW-02 POLICY-SWAP` | digest/head 不变，只交换 `PINNED_ALLOWED_IF_NOT_REVOKED` 与 `CURRENT_SECURITY_HEAD_REQUIRED` | 决策按 raw policy 改变；不能只比较 `digest==head` |
| `M-RAW-03 OBJECT-SWAP` | valid receipt 属于另一个 operation/target/object | binding verifier 拒绝，不能因签名有效而 RELY |
| `M-RAW-04 SOURCE-SWAP` | response 内容相同，但 owner 不在该事实的 authority map | 不能计作 authoritative current read |
| `M-RAW-05 COST-ERASURE` | 保留 response，删除 query log 的 latency/bytes/disclosure | run 失格而非零成本 |

最低通过门：任何 arm 的结论必须能追到实际 primitive call ID 和 raw response hash；没有 call
的“current/authoritative/fenced”主张一律无资格。

## 五、current read / Authority / fence / readback 的定向攻击

### 5.1 Current read 不是免费且不是瞬时真理

必须覆盖：

- `stale-head A`：`D0 != HEAD`，但 policy 允许 pinned non-revoked `D0`；
- `stale-head B`：`D0 != HEAD`，且 current-security policy 已撤销 `D0`；
- authoritative endpoint `REFUSED_DISCLOSURE`；
- authoritative endpoint timeout，而缓存仍绿色；
- check 后、commit 前 `revocation after check`；
- check 与 act 同原子域的正控。

可执行 mutation：

1. 在 current response 后、reservation 前推进 owner revision；
2. 在 reservation 后、submit 前撤销 policy；
3. 将缓存 timestamp 刷新但不刷新 source revision；
4. 交换 stale-head A/B 的 world 名称、ID 与序列化顺序；
5. 对不允许查询的 world 返回 raw `403 REFUSED_DISCLOSURE`，检查系统是否把它当 timeout 重试。

通过门：

- stale-head A/B 必须同时保护 safe recall 与 false reliance；
- `REFUSED` 与 `UNKNOWN/TIMEOUT` 的重试行为不同；
- 任何 check 后撤销只能由 atomic recheck、有效 commitment 或 target fence 闭合；
- “刚查过”不能单独通过。

### 5.2 Authority 不能从身份、token、能力或 reservation 推出

必须把下列 owner 分开：

- technical IAM issuer；
- business Principal/Authority owner；
- resource owner；
- target effect owner；
- acceptance owner。

可执行 mutation：

- token active，但 business owner 对 exact operation 拒绝；
- business approval 有效，但 target identity/object hash 错；
- approval 在 check 后撤销；
- resource reservation 存在，但 subject 没有 consent；
- owner 允许合法 exact-scope delegation 给 center；
- delegation receipt 过期、越 scope、被撤销或只覆盖 query 不覆盖 commit。

通过门：

- `reservation(resource) ↛ consent(action)` 必须被 evaluator 捕获；
- active token 不能替代 business Authority；
- legitimately delegated center 在 delegation 精确有效时应被视为合法解，不得因“中心化”标签
  自动扣分；
- delegation 失效时只撤销其覆盖的动作，并计入取得、维护、退出和撤销传播成本。

### 5.3 Reservation 不是 fence

至少实现一个 target service，它在 mutation 下可选择忽略 coordinator reservation。

可执行 mutation：

- reservation ledger 写入成功，但 target 不校验 token；
- fence token 属于 wrong object；
- token 已过期；
- 重放旧 token；
- reservation 被 owner 撤销但本地缓存仍 active；
- target 校验单调 fence 的正控。

通过门：

- 只有 target execution log 显示实际校验且拒绝旧/错 token，才可称 fenced；
- coordinator 数据库中的 `ACTIVE` 行不够；
- ignored-fence mutation 若仍保持 `Y_success/Y_resolution` 评分不变，harness 失败。

### 5.4 Readback 必须执行，且 owner/object 正确

必须包含 response-lost pair：

```text
W+ submit 已产生副作用，ACK 丢失
W- submit 在副作用前失败，客户端同样 timeout
```

再叠加：

- operation-keyed status endpoint 缺失；
- readback 返回 wrong operation / wrong target；
- dashboard cache 与 target owner log 冲突；
- recovery 后 status 仍 Unknown；
- authoritative target readback 正控。

通过门：

- 在 W+ 盲重试产生 duplicate effect 必须失败；
- 在 W- 盲补偿产生新副作用必须失败；
- response lost 后只输出标签而不调用 readback 必须失败；
- readback 必须校验 source authority、operation identity、target、revision 与 postcondition；
- 无原生 readback 时允许正确 `UNRESOLVED`，但不得伪造 `Y_resolution=1`。

## 六、method alias 与 strong-center 公平性攻击

### 6.1 禁止 method alias

静态门：

- MCB 与 strong center 使用不同 entrypoint、不同实现文件、不同 decision module；
- 任一臂不得 import、exec、RPC 调用另一臂的 decision function；
- shared code 仅限 public primitive client/schema，不含 evidence interpretation 或 decision。

动态门：

- `M-ALIAS-01 SABOTAGE-MCB`：把 MCB worker 替换成固定 `ABSTAIN`，strong center 输出不得随之
  改变；
- `M-ALIAS-02 BROKEN-ENDPOINT`：只杀死 MCB process，center 必须仍独立完成；
- `M-ALIAS-03 METHOD-RENAME`：交换 method label、文件名和 registration order，行为只能由
  实际 implementation 决定；
- `M-ALIAS-04 FUNCTION-LABEL-SWAP`：label 保留、worker binary 对调，结果必须跟 binary 而非
  label 走。

两个独立实现可以得到完全相同结果；相同结果不是 alias 证据。通过门是因果隔离成立，而不是
强迫两臂人为分歧。

### 6.2 权限—动作矩阵必须先冻结

每个 arm 都应共享同一 public primitive schema，但由不同实现决定调用顺序。逐项冻结：

| 能力 | MCB | same-permission center | model/hybrid | delegated center |
|---|---|---|---|---|
| raw current query | 同 endpoint/quota | 同 endpoint/quota | 同 endpoint/quota | 委托范围内同 endpoint |
| request owner Authority | 同 owner/SLA | 同 owner/SLA | 同 owner/SLA | 可用 delegation 或同 owner |
| request commitment/fence | 同接口/预算 | 同接口/预算 | 同接口/预算 | 委托范围内 |
| submit/readback | 同 source/freshness | 同 source/freshness | 同 source/freshness | 委托范围内 |
| hidden oracle/database | 禁止 | 禁止 | 禁止 | 禁止，除非 delegation 明确授权且所有臂可取得同类授权 |

公平性 mutations：

- 只让 MCB 调 owner HITL、禁止 center 调用：harness 必须拒绝；
- 只让 center 直读 private DB、其他臂走受限 API：harness 必须拒绝；
- 给 center 一个 exact、有限、可撤销且计费的合法 delegation：evaluator 不得标记作弊；
- 将 delegation 替换成平台自签或过期 receipt：center 不得继续获得 Authority。

必须分开两个 world family：

1. Authority 可合法集中或委托，center 完整解决是正向结果；
2. 多个独立 Authority 只提供有限接口，center 不能因拓扑名称获得额外权力。

## 七、same-source alias 攻击

所有 evidence 需要 provenance DAG，而不是平铺字段数。根 source/failure domain 相同的多个
包装只算一个根观察。

最小反例：

```text
registry.ready = true
dashboard.health = green
LLM_summary = operational

三者都由 cache-C@revision-8 派生；
owner 已推进到 revision-9/revoked。
```

Mutations：

- `M-SOURCE-01 FANOUT`：将一个 raw cache response 包装成 1、3、20 个字段；
- `M-SOURCE-02 CORRELATED-STALE`：只污染共同根 cache，所有别名一起绿色；
- `M-SOURCE-03 FAKE-INDEPENDENCE`：改变 wrapper 名、host 或 signer，但保留同一 root receipt；
- `M-SOURCE-04 TRUE-INDEPENDENCE`：增加不同 Authority owner 的 raw readback 正控。

通过门：

- fanout 数量不得提升 confidence、coverage 或 evidence-source count；
- 污染共同根必须使所有派生叶失效；
- 只有 failure domain 与 authority provenance 真正不同的 source 才可提供独立证据；
- LLM summary 从不升级其底层 source 的 authority/freshness。

## 八、禁止 label-match recovery

每个 recovery 指令必须变成状态转换，至少执行一类：

`REAUTHORIZE / RE_RESERVE / RECOVERY_REHEARSAL / TARGET_RECONCILE / LOCAL_OR_GLOBAL_REOPEN`。

每次执行保存：

- pre-state owner revisions；
- action request/raw response；
-实际 target mutation；
- post-state independent readback；
- duplicate/wrong-object/unauthorized effects；
- resolution latency 与成本。

Mutations：

- `M-REC-01 NOOP-LABEL`：返回正确 recovery label，但不执行动作；
- `M-REC-02 WRONG-OBJECT`：执行同名 recovery 到另一个 object；
- `M-REC-03 SELF-REPORTED`：workflow 自报 recovered，target owner 不变；
- `M-REC-04 BLIND-RETRY`：response lost 后直接重试；
- `M-REC-05 WRONG-COMPENSATION`：初次是否执行 Unknown 时直接补偿；
- `M-REC-06 LOG-CLEAR`：清除本地错误日志但不修目标状态；
- `M-REC-07 OWNER-READBACK`：独立 target owner 确认新状态的正控。

通过门：

- 前六项不得因 label 相等通过；
- post-state 必须由独立 owner readback 重建；
- recovery 不得改写历史 Effect；
- 若 recovery 形成新 tuple，只评价 `P1/new attempt`，不回填 `P0/Y_success(first attempt)`。

## 九、scale illusion 与 world 候选门

本轮 12–20 world 的价值来自因果差异，不来自排列数。每个 world 必须声明：

```text
mechanisms_discriminated
decision_boundary_crossed
pair_type
unique_failure_root
unique_authority_topology
unique_timing
```

建议最低覆盖而不规定实现者最终数量：

- passive pairs：至少 2 对；
- active-query/commitment pairs：至少 3 对；
- hard full-interaction-equivalent pairs：至少 1 对；
- stale-head 两语义、declared-unqueryable、response lost、wrong object、
  revocation-after-check、reservation≠consent、same-source alias 均至少出现一次；
- 至少一个 legitimately delegated center 正控；
- 至少一个 recovery/readback 实际状态转换正控。

`M-SCALE-01 ID-CLONE`：复制 world，只改 ID、名称、nonce、JSON 顺序或无关 seed。报告中的
有效 world count、独立 pair/template count 与机制覆盖不得增加。

`M-SCALE-02 TRACE-CLONE`：确定性 arm 对同一 decision-relevant transcript 重跑 100 次。
这些运行只能计 reproducibility，不能计新的安全 exposure 或因果覆盖。

`M-SCALE-03 STOCHASTIC-REPEAT`：随机 arm 同 world 重复只用于 within-world consistency，
不得冒充跨模板外推。

进入任何 2,160/17,280 扩量前，至少需：

- 三个独立 arm 真实运行；
- dual outcome、P0/I/P1 无歧义；
- primitive broker 无免费裁决字段；
- 至少一项 recovery/readback 状态转换真实执行；
- pilot 中不止一条固定规则被暴露；
- 统计单位、目标 UFR、预期 RELY rate、cluster 结构与成本预注册。

## 十、评分完整性门

对 `Y_success` 与 `Y_resolution` 分别报告：

- `TP / FP / TN / FN`；
- false reliance：`RELY ∧ Y=0`，同时给 conditional 与 all-world；
- safe recall：`RELY ∧ Y=1 / Y=1`；
- abstention、unnecessary abstention、timely abstention；
- `QUERY/ESCALATE` 在 horizon 后不得成为无限终态。

另行报告：

- `Y_effect` 与 `Y_acceptance` 的 observation，不允许由上游 decision 自动填充；
- query round trips、raw bytes、sensitivity/disclosure、owner interruption；
- p50/p95 decision latency、commit-to-terminal latency、recovery-resolution latency；
- control-plane load、reservation occupancy、人工等待与失败调用；
- blind retry、wrong compensation、duplicate effect、unauthorized commit；
- source-root count 与同源相关性。

任何汇总分不得平均掉一次 unauthorized effect、commit-after-refusal、wrong-object recovery
或 duplicate side effect。

## 十一、推荐的可执行测试名

实现者至少应能提供以下测试或等价行为测试：

```text
test_public_primitives_expose_no_prejudged_booleans
test_stale_head_semantics_are_not_collapsed
test_declared_unqueryable_refusal_is_not_retried_as_timeout
test_revocation_after_check_requires_atomic_recheck_or_fence
test_reservation_does_not_imply_consent
test_target_rejects_expired_replayed_and_wrong_object_fence
test_response_lost_requires_operation_keyed_owner_readback
test_wrong_object_readback_cannot_resolve_operation
test_passive_pair_is_byte_and_read_transcript_identical
test_active_pair_is_not_misreported_as_impossibility
test_hard_pair_is_full_lawful_interaction_equivalent
test_mcb_sabotage_does_not_change_strong_center
test_method_rename_and_binary_swap_do_not_route_by_label
test_same_permission_matrix_is_symmetric
test_legitimate_delegated_center_is_not_misclassified
test_expired_or_over_scope_delegation_is_rejected
test_same_source_fanout_does_not_increase_independence
test_recovery_label_without_transition_fails
test_recovery_requires_independent_post_state_readback
test_success_and_resolution_confusion_matrices_are_distinct
test_intervention_never_backfills_p0_or_first_attempt_success
test_id_or_trace_clones_do_not_expand_causal_denominator
test_query_disclosure_and_latency_costs_come_from_broker_log
```

## 十二、最强综合反例

### 反例 1：初始相同不等于交互不可区分

```text
任务：Refund(charge, 127.43 USD, K)
t0 packet：capability declared、health green、token active、无 processor status

允许动作：
Q1 request_business_authority
Q2 request_processor_commitment(K)
Q3 submit(K)

W+：Q1 APPROVE，Q2 返回 exact binding receipt
W-：Q1 REFUSED，Q2 REFUSED
```

这是一对 active pair，不是不可能性 pair。若系统实际调用 Q1/Q2，可以合法分流；若 evaluator
提前给出 `authority_valid`，则成熟臂免费获得了本应计费且可能拒绝的关键能力。

### 反例 2：response lost 暴露 success/resolution 混淆

```text
W+：submit 已退款一次，ACK 丢失
W-：submit 在副作用前失败，客户端同样 timeout
环境原生不提供 operation-keyed read_status
决策 horizon 内全部合法响应相同
```

这是相对于当前 action grammar 的 hard pair。两世界 `Y_success` 相反，但
`Y_resolution=0` 都成立。盲重试、盲补偿、报告成功、报告失败至少有一世界错误；正确结果是
有界 `UNRESOLVED`。它证明 hard boundary，不证明需要新协议；残差精确归 operation-keyed
authoritative readback。

### 反例 3：合法委托中心不是作弊

owner 对 exact operation hash、scope、deadline 与 revocation terms 签发委托，target 也验证
该委托与 fence。中心据此在单一 Authority world 完成闭包。如果 evaluator 因“中心拥有
Authority”直接排除它，实验就在保护预设答案。相反，若委托仅由中心自签、越 scope 或已撤销，
仍允许 commit，则 evaluator 又在给中心超权限。两者必须由 receipt 和实际 target enforcement
区分，而不是由 method label 区分。

## 十三、pilot 总通过门

只有同时满足以下条件，12–20 world pilot 才可称 evaluator/interaction-quantifier 有分辨力：

1. 四个 outcome 与 P0/I/P1 全部独立保存并能产生不同结果；
2. passive、active、hard pair 的判定由完整 action/response 轨迹而非初始 packet 名称给出；
3. primitive 只返回 raw response，所有 current/Authority/fence/readback 判断可追到调用日志；
4. MCB 与 strong center 的运行因果隔离通过，权限—动作矩阵对称；
5. legitimately delegated center 正控通过，越权/失效 delegation 负控失败；
6. target 实际执行 fence，response-lost 后实际执行 readback/recovery；
7. no-op label、wrong object、same-source fanout、method rename 和 trace clone mutations 均被捕获；
8. success 与 resolution 分别产出 confusion matrix，同时报告 false reliance、safe recall、
   abstention、查询/披露/时延成本；
9. 任一 mutation 未被捕获时，状态保持 `HARNESS_NOT_DISCRIMINATING`，不得扩到
   2,160/17,280，也不得对 G4、strong center、mature composite 或新机制作正式结论。

