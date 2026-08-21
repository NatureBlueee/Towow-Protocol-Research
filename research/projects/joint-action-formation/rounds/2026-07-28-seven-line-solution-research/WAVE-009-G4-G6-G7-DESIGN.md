# Wave 009 Unit D — G4 reliance, G6 effect, G7 reopen

日期：2026-07-29  
状态：`INDEPENDENT DESIGN COMPLETE / T6 MUTATION REPLAY SPEC / NOT RUN`

## 三个独立 truth owner

- G4 在执行前判断一个 exact operation 是否值得依赖；
- G6 从目标 Authority domain 重建 Effect、Adoption、Acceptance 和 Settlement；
- G7 根据依赖与漂移决定 continue、block、recover 或 reopen。

任何一条线通过，都不能自动创建另一条线的事实。

## 新变量

### G4

- `prediction_horizon`；
- evidence 绑定 head/epoch 与 current head 的 `authority_head_gap`；
- 按独立 producer 而非 receipt 数量计算的 `evidence_independence_rank`；
- `probe_coverage` 与 actual operation distribution；
- `reservation_lease_risk`；
- history 是否仍属于当前分布的 `regime_shift`；
- `selective_coverage`，并用 liveness floor 阻止 all-UNKNOWN。

### G6

- 跨 transaction、workflow retry、outbox、consumer 的 `causal_identity_scope`；
- Effect、Adoption、Acceptance、Settlement 的 `authority_lag_vector`；
- Saga 后仍存在的 `compensation_residual`；
- `acceptance_object_version`：精确 output、goal 和 RelationVersion。

### G7

- `dependency_coverage`；
- 耦合度 \(\kappa=\) 受影响闭包价值权重 / 全部活跃未来动作价值；
- `inflight_irreversibility`；
- 跨 runtime 的 `context_portability_loss`；
- 获得 Principal/Authority 决定的 `amendment_latency`。

跨线报告：

- `assurance_tax`：probe、验证、披露、监控、人工和恢复成本；
- `reuse_surplus = 首次形成成本节省 - assurance_tax - 漂移损失`；
- `evidence_correlation`：不同证据是否来自同一 producer。

## 当前最强现成组合

强中心负责计算和编排，但不成为跨域事实 owner：

1. current authority head + exact-operation probe + IAM/permission + exclusive reservation +
   provenance attestation + recent history，由校准模型输出 `RELY/BLOCK/ABSTAIN`；
2. local transaction + outbox + durable workflow + event sourcing/CDC/CloudEvents + 统一
   idempotency/causal ID + bounded Saga + target-domain readback；
3. Effect、Adoption、human Acceptance、Settlement 分域 receipt；
4. immutable contract/workflow version + telemetry + dependency/defeater contract +
   workflow migration + Principal-owned amendment；
5. 依赖不完整时退化为 broad block、global reopen 或 human discovery。

在依赖完整、current head 可查、target readback 可用、外部 Effect 幂等或可靠补偿的环境中，
这个成熟组合若完整通过，就是通爻正向解决，不需要新协议。

## 精确残余

- 未进入 evidence API、workflow history 或 dependency graph 的隐藏依赖，使任何系统都无法
  保证最小局部重开；
- telemetry 不能决定 goal change 是否 material，必须由相应 Principal amendment；
- outbox 只保证本地 command/event 原子化，不保证外部 world exactly-once；
- workflow history 不会自动说明一个事件是 Effect、Adoption 还是 Acceptance；
- event export 不等于 authority/dependency/acceptance 语义可移植；
- history、attestation 和 declaration 不能消灭新 model/environment distribution 的前瞻
  不可识别性，只能 probe、abstain 或创造新观察。

这些残余目前更像 authority-specific readback、dependency contract 与 migration conformance
layer 的实现责任，尚未证明需要新协议。

## Paired worlds

| Pair | World A / B | 预期 |
|---|---|---|
| Model | exact probe pass / held-out regression | continue / block capability path |
| Permission | current head ACTIVE / REVOKED | continue / block future dependent actions |
| Evidence | 同 Authority 续签 / 来源被反证 | recover / Unknown + defeater |
| Account | 同身份恢复 / owner-key 改变 | resume / reauthorize and reopen identity dependency |
| Goal | schema alias / Acceptance material change | adapter / Principal amendment |
| Reservation | valid-exclusive / expired or double | rely / block |
| History | current regime / regime shift | history usable / current evidence dominates |
| Attestation | valid+current / valid but permission revoked | rely / revocation dominates |
| Hidden dependency | unexpressed dependency active / revoked | 决策前不可区分，诚实 Unknown |
| Coupling | optional leaf / shared root | local / global reopen |
| Effect timeout | before target commit / after Effect | retry / readback then no duplicate |
| Effect ladder | Effect not Adoption / Adoption but Acceptance refuse | 保持分层 |
| T5 control | 单 Authority direct / 独立 beneficiary Acceptance | platform direct / cross-domain chain |

## 三个 evaluator

`ProspectiveRelianceEvaluator` 只接受 attempt 前冻结的 prediction，输出
`RELY/BLOCK/ABSTAIN`、confidence、expiry、horizon 和 exact operation binding；评价 false
reliance、missed viable action、calibration、coverage、abstention、首次成功、恢复时延和
真实证据成本。事后修复不能回填为原 prediction 正确。

`AuthoritativeEffectEvaluator` 从不同 Authority domain 的 event store、target readback 和
Principal receipt 重建 `Attempt / Effect / Adoption / Acceptance / Settlement`，不读取
workflow 自报终态；评价 false promotion、duplicate、wrong authority、timeout retry、
readback latency、compensation residual 和 causal identity。

`DependencyReopenEvaluator` 私有持有包含 cycle、hidden edge、in-flight irreversible action
的 oracle dependency graph；candidate 只见 public graph 和允许的 evidence。输出
`CONTINUE / BLOCK / RECOVER / LOCAL_REOPEN / GLOBAL_REOPEN / HUMAN_AMEND`，评价 unsafe
continuation、missed/over reopen、recovery、Context sufficiency、Acceptance preservation、
human load、portability 和 reuse surplus。

三个 evaluator 只交换带版本的公开结果。compositor 只能检查矛盾，不能让 G4 PASS 创建
Effect，也不能让 G7 修复回填 G4 的原预测。

## 成本与负组合效应

必须直接计量 evidence API、bytes、current-head 查询、probe 风险、reservation 稀缺占用、
workflow/outbox/CDC/retry、target readback、Acceptance latency、披露目的和保留期、human
amendment、reopen/compensation/migration/Context，以及 false/missed action。

重点攻击：

- declaration、probe、history、attestation 同源却被重复计作独立证据；
- probe 消耗 reservation 并改变被预测对象；
- reservation + 长 workflow 制造 stale lock；
- workflow retry 与 message retry 因 ID 不统一而 duplicate Effect；
- outbox、CDC、event sourcing 同时制造多个“权威事件”表面；
- attestation 被错误当作 liveness/capacity/authorization；
- Saga compensation 被错误宣称为回到原 world；
- dependency graph 成本吞噬局部 reopen 收益；
- center cache 被下游误作第二 truth source；
- human amendment 退化为 rubber stamp；
- deterministic replay 与模型临时改写计划冲突。

必须报告 Pareto frontier 和 distribution sensitivity，不宣布普遍 winner。

## 最强反例

构造两个决策前 transcript 完全相同的 world：declaration、exact probe、reservation、history、
attestation、permission head、workflow health、telemetry 和 public dependency graph 全部
一致；唯一差异是一条未表达的第三方 sidecar/account 依赖，A 有效、B 已撤销。

任何只读公开 evidence 的策略：

- RELY 会在 B 中 unsafe continue；
- BLOCK/ABSTAIN 会在 A 中漏掉合法复用；
- 强中心也不能改善。

执行后 target readback 才能区分 timeout-before-effect 和 Effect 已发生但后续
Adoption/Acceptance 失败。由于 G7 graph 没有该 edge，“最小 local reopen”也不可证明。

解决条件只有三类：把依赖和 Authority head 变成可查询 evidence；运行有界 probe 创造观察；
或保持 Unknown 并 broad block/global reopen/human discovery。

## 下一实现及前置阻塞

下一实现为 `T6-D-READONLY-PILOT-REPLAY-001`：

1. 独立 truth owner 从 T2 构造一条新、完整、synthetic 的成功 base trace；
2. 冻结 13 组 paired worlds、opaque IDs、method-visible packet 和三个私有 oracle；
3. capability holdout、effect/adoption/acceptance stores、full dependency graph 分域；
4. parent broker 记录 evidence、execution、readback、retry 和 human request；
5. 八种策略/组合在统一预算下运行；
6. 重放 rename、truth flip、stale head、evidence 删除/重复、correlated receipt、log clear、
   self-report、timeout before/after effect、hidden edge delete、always-stop/continue 和
   T5 name routing；
7. 第一版只在 T2 synthetic replay 上判断机制，再迁移到新 T4 qualified base。

当前 T6 只有 `MUTATION_REPLAY_SPEC`，没有独立合格 base-run 和 oracle dependency graph，
因此本文件不报告覆盖率。
