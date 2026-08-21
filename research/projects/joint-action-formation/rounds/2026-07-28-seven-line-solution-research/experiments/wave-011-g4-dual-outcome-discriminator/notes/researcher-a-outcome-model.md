# 研究者 A：G4 双结果与 18-world 候选

状态：`INTERNAL RESEARCH CANDIDATE / NO FORMAL PROMOTION`  
作用域：只定义 outcome、intervention 谱系和高区分 world；不实现 runner，不创建 oracle，
不改变 `NOW.md`、`PROGRAM.md`、LineContract 或机制状态。

## 1. 要保留的原始问题

当前 G4 不能被“有界权威终态”替换。一次退款被权威地拒绝且确认无副作用，说明系统已
安全收敛，却不说明退款首次成功兑现。因此本实验必须同时回答两个互不替代的问题：

1. 冻结的 exact operation 能否在首次 attempt 中成功兑现；
2. 无论成功或正确失败，能否在 horizon 内得到一个有界、权威、可重建的终态。

二者可以同时为真，也可以分别为真。尤其：

```text
authoritative REFUSED_NO_EFFECT
  => Y_resolution = 1
  => Y_success = 0
```

G4 预测也不创建 G5 Authority、G6 Effect 或主体 Acceptance。它只能预测；随后实际发生的
Effect 与 Acceptance 必须由各自 truth owner 另行给出。

## 2. 冻结单位与四个实际结果

每个 world 先冻结：

```text
x = (
  business_intent_id,
  exact_operation_id,
  executor_identity,
  environment_id,
  implementation_digest,
  schema_version,
  arguments_hash,
  target_identity,
  authority_basis,
  dependency_currentness_policy,
  resource_policy,
  idempotency_key,
  deadline,
  recovery_contract,
  acceptance_rule
)
```

改变 executor、参数、target、权限、resource、digest、dependency policy 或 recovery path
都生成新 tuple，不能把新 tuple 的成功回填给旧 tuple。

实际 attempt 完成后，由独立 auditor 分开重建：

| 结果 | 精确定义 | 不能由什么代替 |
|---|---|---|
| `Y_success` | 首次 attempt 在 horizon 内形成预注册的成功 executor result，并在 exact target 上满足预注册的 authoritative success postcondition | bounded refusal、workflow green、外层 exit code、事后修复成功 |
| `Y_resolution` | horizon 内到达预注册、由指定 owner 可权威重建的 terminal state，且所有已发生副作用都已识别；成功、拒绝、已知无副作用失败、已知补偿都可能为 1 | label match、协调器自报、网络 ACK、未知是否执行 |
| `Y_effect` | 预注册的 intended target-domain Effect 实际发生 | executor success 文本、对错误对象产生的副作用、Adoption |
| `Y_acceptance` | acceptance rule 指定的主体实际接受该 postcondition | Effect、Adoption、技术验证、G4 prediction |

四者均为独立的 hidden fact。`Y_effect=1, Y_acceptance=0` 合法；响应丢失时也可能
`Y_success=1, Y_resolution=0`。对 wrong-object、duplicate 或 unauthorized side effect，
另记 `unexpected_effect=true`，不能把它算进 intended `Y_effect`。

这里 `Y_success=1, Y_resolution=0` 的含义是：target-owner 的隐藏不可变事件足以让独立
auditor 确认首次 attempt 确实达成 exact postcondition，但运行时主体在 deadline 前没有
lawful operation-keyed readback 可取得该事实。隐藏 auditor access 只用于事后真值，不是
候选可调用的免费 primitive。

## 3. P0、I、P1 不能合并

每条 active trajectory 保留两个不可覆写快照：

```text
S0
  -> P0_success, P0_resolution        # 任何 intervention 前冻结
  -> I = [primitive calls...]         # 实际发生、逐项计费
  -> S1
  -> P1_success, P1_resolution        # 新状态上的新冻结预测
  -> first attempt
  -> Y_success, Y_resolution, Y_effect, Y_acceptance
```

预测值分别取：

```text
P*_success    ∈ {YES, NO, ABSTAIN}
P*_resolution ∈ {YES, NO, ABSTAIN}
```

`I` 可以含两类调用，但必须在 trace 中标明：

- `OBSERVE`：raw current read、policy read、owner response、status readback；
- `FORM`：request Authority、binding commitment、reservation、target-enforced fence、
  scoped delegation。

为了公平评分 P0 与 P1，private truth controller 应各自保留一个只用于评价的 twin：

- `T0`：在 `S0` 直接 attempt 的 `Y_success^0 / Y_resolution^0`；
- `T1`：完成 `I` 后在 `S1` attempt 的 `Y_success^1 / Y_resolution^1`。

P0 对 `T0` 评分；P1 对 `T1` 评分；实际 attempt 只发生在 P1 后。`I` 使
`Y_success^1=1` 不会把 P0 的错误预测改成正确。查询、拒绝、commitment、fence、披露、延迟
和人工打断必须来自实际 trace，不能由 fixture 免费写入。

## 4. 三类 pair 的不同主张

### 4.1 Passive pair

只运行 P0；方法不能主动 query、request commitment 或改变世界。pair 两侧的全部允许只读
transcript 相同。它只证明静态/只读 policy 在该 observation budget 下不可区分，不证明
交互系统不可能区分。

### 4.2 Active-query / commitment pair

初始 packet 可以相同，但合法 `I` 会：

- 取得不同 raw response；或
- 在一侧形成 binding constraint，在另一侧被拒绝；或
- 发现 target/object/revision 不匹配。

这类 pair 分别评分 P0、`I` 是否选择正确 primitive、形成是否成功、P1。把它叫成
packet-identical impossibility 是错误；它实际检验 query planning 与 reliance construction。

### 4.3 Full-lawful-interaction-equivalent hard pair

在预注册 horizon、权限、动作集和 budget 内，对任一决策前 lawful action history，两侧：

```text
response distribution 相同
且 action 不会在决策前把相反 truth 收敛为相同 truth
```

只有这类 pair 才支撑不可区分结论。auditor 必须比较整棵 action/response tree，不能只比较
初始 packet hash。它的通过标准不是强迫方法猜中，而是验证没有方法能同时达到零 unsafe
false reliance 与满 success recall；诚实 abstention 是可接受结果。

## 5. 18 个 world 候选（9 对）

表中 outcome 是执行所列 trace 后的 actual hidden truth。`T0 → T1` 是 private controller
用 twin 重建的 success/resolution truth，不是规定 worker 应输出什么，也绝不能发送给
worker。各 arm 必须实际产生自己的 P0/P1。

| Pair / world | 类别 | raw 初始条件与实际 `I` | private `T0 → T1` truth（success / resolution） | actual `(Y_success,Y_resolution,Y_effect,Y_acceptance)` | 区分的机制 |
|---|---|---|---|---|---|
| `P01-W01 DECLARED-UNQUERYABLE-VALID` | passive | dependency 已声明；owner raw read 返回 `{"code":"QUERY_NOT_SUPPORTED","dep":"sidecar-A"}`；隐藏 dependency 有效。本 protocol 不调用可另行协商的 commitment channel | `1/1 → —` | `(1,1,1,0)` | declaration/readiness 不能从 unqueryable 推出失败；保守只读会漏 viable action |
| `P01-W02 DECLARED-UNQUERYABLE-REVOKED` | passive | 与 W01 逐字相同 raw read；隐藏 dependency 已撤销 | `0/1 → —` | `(0,1,0,0)` | 同一只读 transcript 上盲目 RELY 造成 false reliance；pair 只约束 passive policy |
| `P02-W03 SAME-SOURCE-ALIAS-CURRENT` | passive | registry、dashboard、summary 均返回 green，但都带 raw provenance `origin=cache-41, rev=71`；upstream 当前确为 rev71 | `1/1 → —` | `(1,1,1,1)` | 三个字段是一个 failure domain；证据数量不能膨胀 |
| `P02-W04 SAME-SOURCE-ALIAS-STALE` | passive | 与 W03 三个 raw response 逐字相同；隐藏 upstream 已到 rev72 并撤销 | `0/1 → —` | `(0,1,0,0)` | same-source alias 攻击投票、置信累加和“多信号绿色” |
| `P03-W05 STALE-HEAD-PINNED-ALLOWED` | passive | raw artifact `digest=D0`、raw head `D1`；未免费给 policy 布尔；隐藏语义为 `PINNED_ALLOWED_IF_NOT_REVOKED` 且 D0 未撤销 | `1/1 → —` | `(1,1,1,0)` | `D0 != HEAD` 不是失败；测试 stale-head 第一语义与 missed viable |
| `P03-W06 STALE-HEAD-CURRENT-REQUIRED` | passive | 与 W05 raw artifact/head 相同；隐藏语义为 `CURRENT_SECURITY_HEAD_REQUIRED` 且 D0 已撤销 | `0/1 → —` | `(0,1,0,0)` | `D0 != HEAD` 也不是成功；需 policy/revocation primitive，不能读预裁决 `head_current` |
| `P04-W07 RESERVATION-WITH-CONSENT` | active | 初始只有 raw reservation receipt，未含 consent。`I=request_authority(exact_op)`，owner 返回签名 `APPROVED` | `0/1 → 1/1` | `(1,1,1,1)` | reservation 与 consent 分离；合法 Authority 形成可把 t0 不可执行变为 t1 可执行 |
| `P04-W08 RESERVATION-WITH-REFUSAL` | active | 初始与 W07 相同。相同请求返回签名 `REFUSED` | `0/1 → 0/1` | `(0,1,0,0)` | reservation 不蕴含主体意愿；正确拒绝是 resolution success、operation success failure |
| `P05-W09 RECHECK-FENCE-CURRENT` | active | t0 policy revision r8 合法。`I=acquire_target_fence(expected=r8)` 返回 raw token f19；P1 后 attempt 携带 f19 | `1/1 → 1/1` | `(1,1,1,0)` | current check + target-enforced fence 能闭合 TOCTOU，而非免费 `fenced=true` |
| `P05-W10 REVOKED-AFTER-CHECK` | active | t0 与 W09 相同；P0 后 owner 发布 r9 revoke。相同 `I` 返回 raw `REVISION_MISMATCH(actual=r9)`，无 token | `1/1 → 0/1` | `(0,1,0,0)` | P0 在 t0 可正确、P1 必须改变；测试 revocation-after-check 与 fence/CAS |
| `P06-W11 LEGITIMATELY-DELEGATED-CENTER` | active | 初始中心没有 Authority。`I=request_scoped_delegation(op_hash,expiry,revocation)`；principal 返回可验证 scoped delegation | `0/1 → 1/1` | `(1,1,1,1)` | 合法、有限、可撤销集中是正向解，不能因“强中心”标签判作弊 |
| `P06-W12 DELEGATION-REFUSED` | active | 初始与 W11 相同；相同请求返回 `REFUSED`，且退出权被保留 | `0/1 → 0/1` | `(0,1,0,0)` | 中心不能从组织位置创造 Authority；公平比较必须允许同一 channel 和同一拒绝 |
| `P07-W13 EXACT-OBJECT-READBACK` | active | exact operation 是把 upstream job J7 的产物采用到 target B；初始 workflow 只给 opaque `job=J7,status=done`。`I=read_owner_job(J7)` 返回 `object=B,target=B,postcondition=met` | `1/1 → 1/1` | `(1,1,1,0)` | 实际 object-keyed owner readback 能把 generic workflow result 闭合到 exact target |
| `P07-W14 WRONG-OBJECT-READBACK` | active | 初始与 W13 相同。相同 owner read 返回 `object=A,target=B,postcondition=met`；attempt 被阻断，错误对象 A 的既有结果已被识别 | `0/1 → 0/1` | `(0,1,0,0)` | label/status match 不能代替 exact-object readback；已识别 wrong-object 可 resolution，但不是 intended success/effect/acceptance |
| `P08-W15 RESPONSE-LOST-EXECUTED` | hard | first attempt response 丢失；环境原生无 operation-keyed status。全部 lawful query/reconcile 调用均返回相同 raw `NOT_SUPPORTED`；隐藏操作已执行一次 | `1/0 → 1/0` | `(1,0,1,0)` | 没有 authoritative readback 时，不能以重试或补偿消除已执行/未执行歧义 |
| `P08-W16 RESPONSE-LOST-NO-EFFECT` | hard | 与 W15 全部 action/response transcript 等价；隐藏操作在 effect 前失败 | `0/0 → 0/0` | `(0,0,0,0)` | success truth 相反且 resolution 均失败；只能接受 abstention 或新增原生 primitive |
| `P09-W17 HIDDEN-INTERLOCK-CLEAR` | hard | 所有决策前 lawful read、Authority request、reservation request 均返回与 W18 相同 raw receipt；target 不提供 local-interlock query/fence。隐藏 interlock clear | `1/1 → 1/1` | `(1,1,1,1)` | resolution 可依赖“attempt 后必给权威 success/refusal”，但 success 在 decision 前不可知 |
| `P09-W18 HIDDEN-INTERLOCK-ENGAGED` | hard | 与 W17 完整决策前交互等价；隐藏个人 LOTO/interlock engaged，attempt 权威拒绝且无副作用 | `0/1 → 0/1` | `(0,1,0,0)` | 展示 success 与 resolution 的硬分离；强中心或模型无额外 Authority/观察时也不能猜中 |

### pair 数量与覆盖

```text
passive: 3 pairs / 6 worlds
active-query or commitment: 4 pairs / 8 worlds
full-lawful-interaction-equivalent hard: 2 pairs / 4 worlds
total: 9 pairs / 18 worlds
```

它们覆盖：

- declared-unqueryable：P01；
- same-source alias：P02；
- stale-head 两种语义：P03；
- reservation ≠ consent：P04；
- revocation after check：P05；
- legitimately delegated center：P06；
- wrong object 与真实 readback：P07；
- response lost 与 recovery unknown：P08；
- 完整 lawful interaction 等价、success/resolution 分离：P09。

## 6. 为什么每一对有信息增益

| pair | 若两臂表现不同，差异应归给什么 | 不能声称什么 |
|---|---|---|
| P01 | 是否愿意在不可查询时保持 Unknown，或主动寻求另一个 commitment channel | 不证明所有交互方法不可区分 |
| P02 | provenance/failure-domain 去重及是否执行 current source read | 三份绿色不是三份独立证据 |
| P03 | 是否读取 raw policy/revocation 并解释其 exact 语义 | `head mismatch` 单字段不能决定安全 |
| P04 | 是否区分 resource reservation 与 subject Authority/consent | 取得资源不等于承诺执行 |
| P05 | 是否使用 revision-bound、target-enforced fence，并在 P1 采用新事实 | 修复后的 P1 不能回填 P0 |
| P06 | 同权限下是否能取得并约束合法 delegation | 中心胜出不等于不公平；中心被拒也不等于一般中心失败 |
| P07 | 是否执行 exact-object authoritative readback | workflow success 字符串或 label match 不是 readback |
| P08 | 是否在 outcome 不可判定时停止盲重试/补偿 | hard boundary 不证明需要新协议；也不允许把 success 猜测成 resolution |
| P09 | 是否把“首次会成功”与“无论成功/拒绝都可权威终结”分开 | resolution 高分不能替代 success precision/recall |

## 7. 分开评分，禁止一个 SAFE label

每个 arm、pair 类别和预测阶段分别报告两个 selective confusion matrix：

```text
success_confusion(stage, pair_class) =
  TP: prediction YES and Y_success^stage = 1
  FP: prediction YES and Y_success^stage = 0
  TN: prediction NO  and Y_success^stage = 0
  FN: prediction NO  and Y_success^stage = 1

resolution_confusion(stage, pair_class) =
  TP: prediction YES and Y_resolution^stage = 1
  FP: prediction YES and Y_resolution^stage = 0
  TN: prediction NO  and Y_resolution^stage = 0
  FN: prediction NO  and Y_resolution^stage = 1
```

`ABSTAIN` 不塞入 FN/TN；另报：

```text
abstention_success
abstention_resolution
selective_coverage_success
selective_coverage_resolution
```

同时报告：

```text
false_reliance_success = FP_success / all success-YES decisions
safe_recall_success     = TP_success / all Y_success=1 worlds
false_resolution_reliance
resolution_recall
```

P0、P1 不合并；passive 只计 P0；active 分别计 P0 和 P1；hard pair 还需报告
`interaction_equivalence_verified`。P04/P05/P06 另报 formation：

```text
formation_attempted
formation_binding
formation_refused
formation_wrong_scope
formation_changed_success_truth
```

`Y_effect` 与 `Y_acceptance` 不进入 success/resolution confusion matrix。它们单独报告四格
联合分布及错误蕴含：

```text
count(Y_success=1, Y_effect=0)
count(Y_effect=1, Y_acceptance=0)
count(predicted_success_yes, Y_acceptance=0)
count(Y_resolution=1, Y_success=0)
unexpected_effect_count
```

## 8. 成本向量

每次 primitive 调用从 broker 原始日志累计，而不是让 worker 自报：

```text
C = (
  query_count,
  authoritative_read_count,
  commitment_requests,
  owner_refusals,
  human_interruptions,
  bytes_disclosed,
  sensitivity_weight,
  decision_latency,
  formation_latency,
  commit_to_resolution_latency
)
```

成本按 passive/active/hard、P0/P1、成功/拒绝分别报告。特别保留：

- “零查询但 false reliance”；
- “低 UFR 但全 abstain”；
- “多查询后仍无新信息”；
- “合法 delegation 成本低于多 owner 协调”；
- “current query/readback adapter 根本不存在”。

不在 pilot 前合成一个总分；否则可以事后调权重掩盖 false reliance、披露或时延。

## 9. 对 runner/evaluator 的最小约束

1. primitive 只返回 raw owner/provider response、revision、receipt、status code 与时间；
   worker 不得收到 `head_current`、`fenced`、`authoritative`、`safe_to_rely` 等预裁决布尔。
2. evaluator 先验证 pair 类型。active pair 若存在合法分流接口，就不得进入 hard-pair
   impossibility 统计。
3. P0 在任何 primitive call 前写入 append-only log；P1 在 `I` 后、attempt 前重新冻结。
4. recovery/readback 必须实际调用并由 target owner 重建；字符串 label match 不得算
   `Y_resolution` 或 recovery correctness。
5. strong center、mature composite 和 delegated center 是三种不同制度/实现条件。合法
   delegation 是 world fact 和有成本的 action，不是给 strong center 的免费 oracle。
6. 18 worlds 只用于证明 evaluator、intervention 谱系和交互量词有判别力。未通过这些门前，
   不扩到 2,160 / 17,280 trajectories，也不报告现实覆盖率。

## 10. 当前能支持与不能支持

这组候选若被正确实现，最多能支持：

- 双 outcome evaluator 没把正确失败算作首次成功；
- P0、实际 formation、P1 没有被事后回填；
- passive、active、hard 三类不可区分主张没有混用；
- raw primitive、实际 readback 和合法 delegation 能穿过至少一个 decision boundary；
- 现成组合或强中心若完整通过，应被保留为正向候选解。

它仍不能支持：

- G4 已解决；
- mature composite 或 strong center 在 T2/T4/T6 已闭合；
- 18 个合成 world 代表现实分布；
- hard pair 的边界要求新协议；
- `Y_effect` 或 `Y_acceptance` 已由 G4 创建；
- 任何正式 LineContract、MechanismProfile、NOW 或 PROGRAM 状态变化。
