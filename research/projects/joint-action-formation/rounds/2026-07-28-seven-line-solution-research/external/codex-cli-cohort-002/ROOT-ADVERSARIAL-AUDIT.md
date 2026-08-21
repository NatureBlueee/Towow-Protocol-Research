# Cohort 002 根会话敌对审计

日期：2026-07-29  
处置：`REVISE INTERPRETATION / PRESERVE RUNS / NO FORMAL PROMOTION`

## 为什么需要这份覆盖审计

七条 CLI 主会话都产出了可运行文件，根会话也复跑了测试。但测试通过只说明实现满足当前
合同；不保证合同能区分竞争方法，也不保证 final 对数字的解释成立。

根会话在完成七线复跑后，另设三路只读复核：过度结论攻击、数字/边界核验和下一实验设计。
前两路共同发现以下问题。原 final 保留为生成时的研究记录；当前解释以本审计和
`SYNTHESIS.md` 为准。

## P0：G7 safety-liveness 结论未被编码

`w010` 与 `w011` 的 method-visible transcript 相同，private Authority truth 不同。但
`private_oracle.json` 给两者完全相同的 `expected_actions`：

```text
BOUNDED_UNKNOWN / GLOBAL_REOPEN / HUMAN_AMEND / BLOCK
```

两者都不要求 `CONTINUE`。因此同一保守 `BLOCK` 可以同时满足两个 world；当前实验没有建立
“零误继续与零不必要阻断不能兼得”的被测对立。

可保留：

- `w011` 中实际继续会形成 unsafe；
- hidden dependency、恢复、迁移和 capsule 已形成可运行 harness；
- 18 worlds × 6 methods = 108 method-world traces；
- 23 个 exact-pass cells、5 个 unsafe cells、17 个 unjustified cells、12 个
  unreconciled cells、0 history rewrite。

不能保留：

- 当前 hidden pair 已证明 safety-liveness 不可能性；
- `w010` 的继续是被 oracle 要求的 liveness 正解。

修复条件：让 valid 分支明确要求 `CONTINUE` 或单独计量 conservative block 的 liveness
loss，让 revoked 分支禁止 `CONTINUE`，再在同一 interaction envelope 下运行。

## P1：多条“方法比较”由共享决策结构预定

### G1

`t0_paths` 已预枚举 allowed、cost 和 evidence IDs，方法主要选择已有 path；`D_actual=2`。
它支持 provenance evaluator、invalidity gate、双分母和 mutation harness，不支持一般
discovery/formation 能力或方法胜者。

### G2

四臂都调用 `_common_candidate`，消费相同 owner events；五轴 evaluator 又主要从这些共享
events 重建。`240/240` 和四臂同分是 owner-event semantic conformance，不能证明 human、
center、mature composition、replicated state 四种独立方法等效解决，也不能证明
replication semantic gain 为零。

### G3

五臂直接调用同一个 `choose(packet)`。动作完全相同和 candidate-exclusive success 为零是
alias-by-construction。可保留的是六类 `C/N/E/T/V` 量词分类器和反例，不是成熟 workflow、
center、human 与 candidate 的经验等价。

### G5

Authority stratum、materiality、Standing、race 和 fence 是可运行回归例，但部分结果由
controller 读取 fixture truth 后直接填 route/correctness。`TRUE_UNIFIED_CENTER` 的部分
race 路径没有实际经过 owner/target worker。Saga 当前只记录 compensation intent 并设置
`compensated=true`，没有执行 target reversal/readback。

因此：

- U/P/X 区分保留为理论/设计候选；
- no-common-transaction 的 4 次 transient stale Effect、bounded confirm 的当前分母
  结果、2PC-like hold 的阻塞成本、target fence failure 均可保留为回归观察；
- “统一中心已实际闭合”“Saga 10/10 safe final”“成熟组合闭合 P/X”不能作为端到端结果；
- OPA/Cedar/OpenFGA/XACML 均为 `NOT_RUN`。

### G6

三个 worker 有不同源码 hash，但共享 fixtures、owner services、evaluator，且语义逻辑高度
同构。108/108 表示在完整 owner observation packet 已给定时，三份投影保存了 12 对语义
差异；它不是 transaction/outbox/workflow、人类制度或中心实际取得事实、形成 Authority、
执行 Effect/Acceptance 的端到端证明。

## P2：最可保留的局部成果与口径修订

G4 是当前最有区分力的局部 harness：

- `Y_success/Y_resolution` 分离；
- `P0/I/P1` 分离；
- passive/active/hard pair 量词分离；
- readback/recovery 真实执行；
- mature 与 center 源码不同，sabotage mutation 不互相改变。

但 P1 truth 发生在各臂各自 interaction 后，同时混合干预能力和预测校准；hard universal
只枚举 action depth ≤2；blind holdout 未运行。因此只支持 harness 有判别力，四臂均未解决，
不支持纯预测优越性。

其他记录修订：

- G7 的 `23/108` 是 method-world cells，不是 23/108 个独立 worlds；
- G7 的 12 个 unreconciled cells 只来自 `w004/w014` 两个 unique worlds；
- G6 的 108/108 包含正确阻断和 Unknown，不是 108 个 episode 成功；
- G2 与 G6 并行复跑出现 timeout；串行分别 119.03 秒与 49.38 秒通过；
- G2 的 `ACTUAL_MATURE_COMPOSITION` 应解释为
  `LOCAL_SYNTHETIC_COMPONENT_MODEL`，避免与 G5 的真实产品 `NOT_RUN` 冲突。

## 当前可保留的总状态

```text
LOCAL_FIXTURE_CONFORMANCE = POSITIVE_SCOPED
G1_DISCOVERY_METHOD_COMPARISON = NOT_ESTABLISHED
G2_METHOD_COMPARISON = ALIASED_BY_SHARED_EVENT_DERIVATION
G3_METHOD_COMPARISON = ALIASED_BY_CONSTRUCTION
G4_DISCRIMINATOR = POSITIVE_SCOPED / NO ARM SOLUTION
G5_REAL_PRODUCT_COMPARISON = NOT_RUN
G6_SEMANTIC_CONFORMANCE = POSITIVE_SCOPED
G6_IMPLEMENTATION_INDEPENDENCE = NOT_ESTABLISHED
G7_SAFETY_LIVENESS_FRONTIER = NOT_TESTED_BY_CURRENT_ORACLE
REAL_EXISTING_TECH_FULL_SOLUTION = NOT_RUN
NOVEL_PROTOCOL_NECESSITY = NOT_DEMONSTRATED
FULL_V1_V2_EPISODE = NOT_RUN
```

这不降低强中心、成熟组合、通用模型、人工制度或平台直达的价值。它们仍是完整正向候选；
只是当前 cohort 尚未对这些候选进行有区分力的端到端运行。下一轮若其中任何一种真正闭合
原问题，就应直接登记为通爻解决方案。
