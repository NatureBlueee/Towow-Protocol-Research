# Wave 010 G6/G7 独立攻击审计

日期：2026-07-29  
状态：`REVISE / DEVELOPMENT EVIDENCE ONLY / NO FORMAL STATUS CHANGE`

## 审计结论

当前 `7/7` 只能保留为可复现的本地开发回归，不能作为成熟组合已经解决 G6/G7、lawful
strong center 与成熟组合因果等价，或当前不存在新机制残余的证据。

原
[`WAVE-010-G6-G7-SYNTHESIS.md`](./WAVE-010-G6-G7-SYNTHESIS.md)、
[`WAVE-010-G6-G7-FIXTURE.json`](./WAVE-010-G6-G7-FIXTURE.json)、
[`WAVE-010-G6-G7-SIMULATOR.py`](./WAVE-010-G6-G7-SIMULATOR.py) 与
[`WAVE-010-G6-G7-RESULTS.json`](./WAVE-010-G6-G7-RESULTS.json)
保持不变，作为 `PSEUDO-PERFECT-SCORE HISTORICAL EVIDENCE`：它们准确记录了一个怎样由
perfect readback、共享实现、硬编码 closure 和有限 fixture 得到满分的历史开发状态，但不得
被反向解释为 blind、held-out、独立实现、现实恢复或正式机制证据。

## `7/7` 的实际来源

1. **Truth direct-copy。** `broker_method_view()` 在
   `SIMULATOR.py:100-109` 直接把 `world["truth"]["layers"]` 复制为五层 owner readback，
   又在 `:113-118` 把 `truth["dependency_query_response"]` 复制为 dependency owner
   response。当前分数检验的是 perfect、及时、如实且对象正确的 oracle readback 假设，不是
   query/adapter 能否在现实中满足这些条件。
2. **共享实现。** mature composition 与 strong center 的对应 profile 在
   `SIMULATOR.py:25-79` 除名称外相同，九个方法臂都调用同一个 `method_decision()`（`:123-177`）。
   `:350-353` 再直接断言两份聚合结果相同。因此这里是 profile alias 的输出恒等，不是独立
   架构的因果等价。
3. **Fixture-aligned closure。** `REVOKED` 分支在 `SIMULATOR.py:164-166` 硬编码
   `container-v2 / sidecar-account / buyer-sandbox`，逐字等于唯一 revoked world 的
   `FIXTURE.json:242-248`。fixture 没有 `STALE / UNKNOWN / REFUSED / timeout` query world。
4. **Gate 覆盖不足。** `bounded_recovery` 只检查 `failed_recoveries == 0`
   （`SIMULATOR.py:281-293`），没有 step 上限；`recovery_steps` 是分支常数，不是实际恢复。
   `exact_reopen` 的 per-world 结果同时比较 action 和 closure（`:223-231`），但聚合 gate
   只检查漏/误节点（`:290-292`），会漏掉 action 错误。除 Effect 外也没有其他四层
   true-claim recall gate。

## 三个已执行反例

以下反例于 2026-07-29 直接调用原 simulator 函数执行，没有修改 fixture、simulator 或
results。

| 反例 | 唯一注入 | 实际结果 | 证明边界 |
|---|---|---|---|
| stale owner head | private truth 为 `REVOKED`，method-visible dependency response 为 stale `CURRENT` | 输出 `CONTINUE`；`missed_reopen_nodes=3`、`unsafe_continuations=1`、`recovery_succeeded=false` | 原 `7/7` 依赖 query response 与 private truth 恒等 |
| wrong-object Acceptance | T3 truth 对象为 `prototype-correct`，同 owner 的 readback 对象为 `prototype-wrong`、state 仍为 `TRUE` | 方法丢弃 object id；evaluator 仍给 `false_promotions=0`、`ladder_collapse_errors=0` | 当前 gate 没有验证 exact-object Acceptance |
| wrong reopen action | CURRENT world 保持正确空 closure，只把 action 从 `CONTINUE` 改为 `BOUNDED_UNKNOWN` | per-world `reopen_exact=false`，aggregate `exact_reopen=true` | 聚合 gate 会把 action 错误计为通过 |

最小复现入口：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research
python3 - <<'PY'
import copy
import runpy

n = runpy.run_path("WAVE-010-G6-G7-SIMULATOR.py")
fixture = n["load_fixture"]()
profile = n["PROFILES"]["MATURE_COMPOSITION_WITH_OWNER_DEP_QUERY"]

revoked = next(
    w for w in fixture["worlds"]
    if w.get("truth", {}).get("hidden_dependency_state") == "REVOKED"
)
view, costs = n["broker_method_view"](revoked, profile)
view["dependency_query"]["state"] = "CURRENT"
decision = n["method_decision"](view, profile)
print("STALE_HEAD", n["evaluate_world"](revoked, decision, profile, costs))

t3 = copy.deepcopy(next(w for w in fixture["worlds"] if w["task"] == "T3"))
t3["truth"]["layers"]["Acceptance"]["object_id"] = "prototype-correct"
view, costs = n["broker_method_view"](t3, profile)
view["readbacks"]["Acceptance"]["object_id"] = "prototype-wrong"
decision = n["method_decision"](view, profile)
print("WRONG_OBJECT", n["evaluate_world"](t3, decision, profile, costs))

current = next(
    w for w in fixture["worlds"]
    if w.get("truth", {}).get("hidden_dependency_state") == "CURRENT"
)
view, costs = n["broker_method_view"](current, profile)
decision = n["method_decision"](view, profile)
decision["reopen_action"] = "BOUNDED_UNKNOWN"
row = n["evaluate_world"](current, decision, profile, costs)
print("WRONG_ACTION", row["reopen_exact"], n["aggregate"]("ATTACK", [row])["gates"]["exact_reopen"])
PY
```

## 可保留的主张

- fixture、hash、results 和六项原 self-test 可复现；重新运行结果与保存的 RESULTS
  byte-for-byte 一致。
- T6 paired worlds 的 no-query public transcript 相同，因此任何只读取该 transcript 的
  确定性方法不能精确区分两者。
- workflow/outbox/event delivered 不逻辑蕴含外部 Effect、Adoption、Acceptance 或
  Settlement；当前 T2 可作为这个非蕴含关系的构造反例，但不能估计现实频率。
- 在“owner response 完美、新鲜、如实且绑定正确对象”的冻结假设下，dependency observation
  可以在当前一个 `CURRENT/REVOKED` pair 上消除 local-vs-global reopen 的信息歧义。

## 必须降级的主张

- `7/7` 降级为：`4 个共同设计 worlds + oracle-fed perfect readbacks + fixture-aligned
  closure 下的 developer regression pass`。
- “strong center 与成熟组合因果等价”降级为：同 profile、同一决策函数的输出恒等。
- “两个 branch 在有界步骤内恢复”降级为：两个手写 recovery predicate 与固定 step label
  通过；没有实际恢复、权威 postcondition readback 或 step bound。
- “五层零误晋升、Effect 零漏报”降级为：直接复制 truth readback 后的 evaluator 计数。
- “没有新协议残余”“当前无资格 INVENT”降级为：当前 fixture 没有生成残余；不得据此改变
  MechanismProfile、研究线地位或 `ADOPT / COMPOSE / WRAP / INVENT` 决策。

## Held-out 入口

下一次能够改变上述判断的最小入口是新鲜 `T3-HW-A` 或安全 surrogate：

1. truth owner 在任何方法输出前冻结 resource、slot、object/version、causal identity、五层
   postcondition 与 dependency graph；oracle 单独保存并绑定 hash。
2. owner API 与 grader 分域。API receipt 至少绑定 owner、object/version、head、
   `observed_at`、expiry 与签名，并真实允许 `CURRENT / REVOKED / UNKNOWN / REFUSED / STALE`、
   timeout、response loss、wrong owner 和 wrong object；不得由 grader truth 直接复制返回值。
3. mature composition、strong center 与 human institution 使用独立实现和进程，只共享同一
   packet/API、预算、HITL 与时限，不共享 `method_decision()`。
4. 运行前隐藏并冻结 stale `CURRENT`、response loss、changed causal id、wrong-object
   Acceptance、hidden edge、connector migration 丢 head/version 与多故障组合，随机化顺序后
   一次评分。
5. grader 从 authoritative target/owner ledger 检查五层 precision 与 recall、真实重复 Effect、
   action **和** closure exactness、恢复后 postcondition、elapsed time、query/HITL/disclosure
   成本；标签字符串或固定 step 常数不能替代恢复。

在这个入口完成以前，现有 `7/7` 不进入 X2、不晋升正式证据，也不改变任何机制或研究线状态。
