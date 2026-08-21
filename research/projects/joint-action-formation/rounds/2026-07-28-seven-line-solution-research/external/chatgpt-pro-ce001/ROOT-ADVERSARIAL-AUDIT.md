# ChatGPT Pro CE-001 harness 根级对抗审计

日期：2026-07-30  
状态：`ROOT REPRODUCED / P0 FALSE POSITIVES FOUND / PRO INTERPRETATION OVERRIDDEN`

对象：

- `generated/ce001_independent_harness/run_harness.py`
- 原 zip SHA-256：
  `8f5963b8486a0315947f2753e34911600ef992b6ba1326621b5e324a81b0d5b8`

根会话实际复跑默认 harness，得到与 Pro 报告一致的摘要。这只能建立复现起点，不能证明
evaluator 正确。

## P0-1：错误 Acceptance 与伪 Settlement 仍被判完整成功

源码：

- `OwnerService.accept_effect()`（242–247）对调用者指定的 owner 和任意
  `effect_digest` 自动签发 Acceptance；
- `OpaqueWorld.accept()/settle()`（529–533）把该接口直接给 executor；
- `SettlementService.settle()`（418–427）只检查 owner/kind/status 集合，不核验签名、
  expiry、effect digest、vendor、amount 或 payment cap；
- evaluator（1022–1037）只看 Acceptance owner 名集合和是否存在任一 `SETTLED`。

根会话对一个真实 E1 Effect 清空原 Acceptance/Settlement，再写入：

```text
O_Q acceptance effect_digest = WRONG-DIGEST-A
O_V acceptance effect_digest = WRONG-DIGEST-B
settlement vendor             = NOT-EXECUTED-VENDOR
settlement amount             = 999999
```

实际返回：

```text
settlement_complete = true
acceptance_complete = true
exact_task_success  = true
correct_resolution  = true
```

把 payment 与两份 Acceptance 的 signature 全部改为 `FORGED`，同样得到 `SETTLED`。

```text
INDEPENDENT_ACCEPTANCE = FAIL
SETTLEMENT_BINDING = FAIL
```

## P0-2：E4 撤销资源没有进入 Effect/evaluator 真值链

源码：

- reservation 可以返回 `REVOKED`（286–298）；
- target submit 没有 vendor/reservation 输入（333–345）；
- target Authority 检查不验证 current reservation，也不把 safety permit 与 actual vendor
  绑定（323–331）；
- evaluator 只看 Effect，不检查 current resource commitment（1004–1042）。

根会话实际取得 `VENDOR-A / REVOKED` reservation，仍直接向 target submit 并 Settlement。

实际返回：

```text
target            = APPLIED
settlement        = SETTLED
exact_task_success = true
correct_resolution = true
recovery_to_value  = true
```

现有 portfolio 的正常源码会发现 A 撤销并选择 B，这个控制流可保留；但当前 target/evaluator
无法拒绝坏实现继续使用 A，不能支持 E4 完整闭环。

```text
RESOURCE_REVOCATION_CLOSURE = FAIL
```

## P0-3：duplicate oracle 漏掉同 operation ID 的第二次物理 Effect

evaluator 使用：

```python
duplicate = len({e.operation_id for e in effects}) > 1
```

根会话向一个正确 E1 run 追加第二个、同 operation ID 的 Effect：

```text
effect_count       = 2
duplicate_effect   = false
exact_task_success = true
correct_resolution = true
```

物理重复应按 Effect occurrence 与 semantic operation/object 计数，不能只数不同 ID。

```text
DUPLICATE_EFFECT_ORACLE = FAIL
```

## P0-4：E3 不是 hostile blind pair

被测 arm 能够访问：

- `scenario_id = E3A_ACK_LOST_EFFECT / E3B_ACK_LOST_NO_EFFECT`（471–473）；
- `w._w._private.submit_mode`（459–473）；
- 两种 AckLost 异常文本分别写明 effect 前或后丢 ACK（366–381）。

当前三个主要 executor 没有依据 case ID 分支，但 harness 没有阻止被测实现作弊，不能用它
证明区分只来自 exact-object readback。

```text
E3_EXACT_READBACK_LOCAL_CAUSALITY = POSITIVE_SCOPED
E3_BLIND_PAIR = FAIL
HOSTILE_ORACLE_ISOLATION = FAIL
```

## P0-5：E6 没有实际 runtime migration

portfolio 在同一个 `run()` 调用栈中 catch crash，继续持有 operation ID、vendor、decisions
和对象图，再由同一 executor 模拟 old replay（691–708）；human arm 同样如此（835–851）。
没有销毁 source process，也没有让 target process 只从预先持久化 capsule 恢复。

target fence 持久/丢失的反事实有区分力，可以保留；process migration、lineage recovery
和 split-brain closure 不能保留。

```text
E6_TARGET_FENCE_PERSISTENCE_COUNTEREXAMPLE = POSITIVE_SCOPED
E6_PROCESS_MIGRATION = NOT_RUN
E6_COMPLETE_LINEAGE_RECOVERY = NOT_ESTABLISHED
```

## P1：四臂与 50-seed 的安全边界

- 四个 executor 的 source-level 控制循环不同，且没有共同 `choose()`；
- 它们仍共享一个 `WorldAPI`、private dict、Owner、ResourceMarket、Target、Settlement
  与 evaluator；源码 hash 不证明 truth source 或实现独立；
- seed 唯一改变 vendor list 顺序；availability、owner truth、fault timing、TTL、cost、
  latency 与 target behavior 不变；
- batch 只有聚合结果，没有逐 seed 的冻结输入、运行和 raw trace。

```text
FOUR_DISTINCT_CONTROL_LOOP_BODIES = POSITIVE_SCOPED
SOURCE_LEVEL_NO_SHARED_CHOOSE = POSITIVE_SCOPED
INDEPENDENT_DECISION_ROOT = NOT_ESTABLISHED
INDEPENDENT_OWNER_TRUTH = NOT_ESTABLISHED
FIXTURE_ORDER_INVARIANCE = POSITIVE_SCOPED
SEMANTIC_MULTI_SEED_ROBUSTNESS = NOT_RUN
BLIND_HOLDOUT = NOT_RUN
```

## 可保留的局部成果

```text
E3_EXACT_READBACK_LOCAL_CAUSALITY = POSITIVE_SCOPED
E2_FORMATION_ABLATION = POSITIVE_SCOPED
E5_OWNER_RESPONSE_SENSITIVITY = POSITIVE_SCOPED
E6_TARGET_FENCE_PERSISTENCE_COUNTEREXAMPLE = POSITIVE_SCOPED
FIXTURE_ORDER_INVARIANCE = POSITIVE_SCOPED
```

## 当前总状态

```text
PRO_REFERENCE_SIMULATION = ROOT_REPRODUCED
PRO_ACCEPTANCE_SETTLEMENT = FALSE_POSITIVE_ORACLE
PRO_RESOURCE_REVOCATION = FALSE_POSITIVE_ORACLE
PRO_DUPLICATE_EFFECT = FALSE_NEGATIVE_ORACLE
REAL_PRODUCT_EXECUTION = NOT_RUN
EXISTING_COMPOSITION_FULL_CE001_SOLUTION = NOT_ESTABLISHED
NOVEL_MECHANISM_NECESSITY = NOT_DEMONSTRATED
```

这不是否定现有组合。它仍然是当前最有希望的 bounded CE 解；当前失败说明最关键的
Acceptance、Settlement、resource commitment 和 migration 仍被同源模拟提前闭合，下一步
应修 evaluator 和 owner/target source，而不是改回“需要原创协议”的价值导向。
