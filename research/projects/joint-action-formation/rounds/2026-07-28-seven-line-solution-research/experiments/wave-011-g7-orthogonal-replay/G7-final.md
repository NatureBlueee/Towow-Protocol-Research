# 第二批 Codex CLI G7-final

日期：2026-07-29  
Cohort：`codex-cli-cohort-002`  
候选：`T6-G7-ORTHOGONAL-REPLAY-001`  
状态：`LOCAL_SYNTHETIC_CANDIDATE / NO FORMAL STATUS CHANGE`

## 最终判断

本 cohort 已经把 G7 从五态路由和动作标签推进为实际执行的 18-world 正交 replay，但结果
不支持 G7 已闭合。

```text
WORLD_COUNT = 18
METHOD_COUNT = 6
TRACE_COUNT = 108
EXACT_WORLD_PASS = 23 / 108
FACTUAL_UNSAFE_CONTINUATION = 5
UNJUSTIFIED_CONTINUATION = 17
HISTORY_REWRITE = 0
UNRECONCILED_EFFECT_WORLDS = 12
MISSED_REOPEN_NODES = 132
OVER_REOPEN_NODES = 85
TESTS = 24 / 24 PASS
```

五个 factual unsafe 都发生在 public-identical hidden pair 的 revoked world `w011`。B0、
B1、mature composite、equal-authority center 与 human rule 只能看到和 hidden-valid
`w010` 相同的 native transcript；它们继续时保留了 `w010` 的 liveness，却在 `w011`
实际提交。这个结果支持一个有界不可区分边界：没有新观察、lease/fence 或保守 policy 时，
同一 packet 不能同时保证零误继续和零不必要阻断。

这不支持“新协议必要”。可行下一步可能是 owner-native dependency query/probe、组织委托、
人工 discovery、全局阻断或显式接受 safety-liveness 损失。

## 原生 G7 是否被保留

保留了五个互不蕴含的分面：

1. reuse：稳定子图是否值得编译，重复运行是否真降本；
2. context：目标 runtime 能否只凭最小充分、带回源引用的 Context 重建判断；
3. legitimacy：commit point 的 current Authority、Effect 与 Acceptance 依据；
4. reopen：失效 justification 的 local/global closure 与历史保真；
5. migration：source/target 语义义务、old-runtime fence 与 reconciliation。

`CURRENT/REVOKED/UNKNOWN/REFUSED/STALE` 已降为 Authority observation 的兼容投影。
normative、epistemic、channel、freshness/provenance、fork、Effect、coordinator epoch、
migration 和 Acceptance applicability 分别保存。worker 只见 native response，private
oracle 才持有 normalized truth、hidden edge 和 expected closure。

## 六臂比较

| Arm | exact pass | factual unsafe | unjustified | 当前 T6 通过 |
|---|---:|---:|---:|---|
| B0 immutable + monitoring + human amendment | 3/18 | 1 | 5 | R2 |
| B1 durable workflow/history/migration + human amendment | 3/18 | 1 | 4 | 无 |
| mature composite | 11/18 | 1 | 0 | R2, R5, R7 |
| equal-authority center | 2/18 | 1 | 4 | R2 |
| delegated center | 1/1 applicable | 0 | 0 | `NOT_APPLICABLE` |
| human rule | 3/18 | 1 | 4 | R2 |

delegated center 只在 `w001` 明确冻结合法委托时适用；其他 17 个独立 Authority world 的
BLOCK 不能计算为一般 T6 成功。这个 strata 分离阻止“通过吞并 Authority 获得真值”与
equal-permission center 混在一起。

mature composite 是当前有限 world 中表现最强的候选，但仍失败于：

- R1：没有真实 cold-vs-repeat reformation cost；
- R3/R6：hidden revoked 无新 observation 时误继续；
- R4：仍有 unsafe 或未对账 Effect；
- R8：response-lost readback 未闭合，field-drop migration 按预期 fail closed。

它通过 R5/R7 说明 material goal/shared root 能被扩大重开；不能外推为完整 G7。

## 实际 runner

runner 实际执行：

- owner native query；
- source runtime intent persistence；
- commit-time authority/fence check；
- dispatch、timeout 与 response loss；
- effector authoritative readback；
- independent Acceptance readback；
- local/global reopen；
- planned drain 与 crash takeover；
- capsule export/import；
- old-runtime restart/fencing；
- target reconciliation。

`w017` 的旧 runtime restart 再次遭遇 timeout；caller 看不到最终结果，但 effector 的独立
ledger 记录第二次提交为 `FENCED_OR_DENIED`，Effect 总数保持 1。`w018` 的 source Effect
和 Acceptance 先实际进入 capsule，再删除 `compensation_obligations/acceptance_records`；
target 拒绝 import，mature arm 返回 `BOUNDED_UNKNOWN`。

## 实际多 Agent

本 CLI 实际创建了三名内部研究者，没有模拟：

| 内部研究者 | 实际会话 | 职责 | 交付 |
|---|---|---|---|
| A | `/root/g7_researcher_a` | 原生 reuse/context/legitimacy/reopen/migration 重建 | `researcher-A.md` |
| B | `/root/g7_researcher_b` | provider、runner、migration/reconciliation、六 workers | `provider_simulators.py`、`runner.py`、`workers/` |
| C | `/root/g7_researcher_c` | 五态/truth-copy/hidden-edge/alias/migration-oracle 攻击 | fixture、private oracle、grader、attack tests |

root 主研究会话完成输入冻结、接口整合、错误归因、结果重跑、集成测试与最终判断。三名
Agent 的一致意见没有被当作证据；最终分数来自实际 trace 和独立 grader。

并行过程还暴露并修复了三个真实缺陷：

1. 六 worker 一度把 native `{active:false}` 因字符串包含 `active` 误判为 CURRENT；
2. grader 一度把 HUMAN_AMEND/global block 等保守行为错误算成 factual unsafe；
3. capsule 攻击器一度把合法 native `channel_outcome` provenance 误报为 truth leak。

三项修复均进入测试，结果在修复后重新生成。

## 验证

执行：

```text
python3 runner.py --output run-traces.json
python3 private_oracle.py run-traces.json --output results.json
python3 -m unittest discover -s tests -v
python3 -m py_compile runner.py provider_simulators.py private_oracle.py workers/*.py tests/*.py
```

结果：

- 18 worlds × 6 methods = 108 actual traces；
- 24/24 unit/integration/attack tests PASS；
- Python compile PASS；
- public/private world IDs 一致；
- hidden pair method-visible packet 同构；
- runner 不 import/open private oracle；
- 六 worker source hashes 不同且不互相 import；
- history ledger hash-chain 与 prefix preservation 受 grader 检查；
- core artifact SHA-256 见 `manifest.json`。

## 成本边界

runner 保存 query、human minutes、calendar wait、handoff、runtime、central ops、assurance
和 governance 等原生成本。它们当前不是统一货币或统一生命周期函数，不能由字段求和宣布
winner。R1 因缺 cold-vs-repeat 对照保持 FAIL；这比把“记录了成本”写成复用增益更诚实。

## 不能支持与下一步

本 cohort 不能支持：

- mature composite、center 或 human baseline 已完整解决 G7；
- delegated center 可用于未委托 Authority；
- Context capsule 已证明跨真实 runtime 语义标准化；
- 真人授权、现实 Effect、生产恢复或长期净值；
- 新协议必要或 residual 已关闭；
- 任一正式 claim、LineContract、MechanismProfile、NOW 或 PROGRAM 状态变化。

下一条最高信息增益不是扩到 1500 个同源 world，而是：

1. 为 hidden pair 增加一条合法但有成本的 owner-native observation path，测量安全、
   liveness、披露和等待前沿；
2. 建立第二个独立 base family，并实际比较 cold reformation 与 repeat assurance；
3. 对 `w004` 运行可恢复的 delayed readback，区分安全阻断与可恢复继续；
4. 在另一套 source/target runtime adapter 上重做 capsule conformance，而不是复制当前
   Python state machine；
5. 只有跨 base family/runtime 重复出现相同语义损失时，才重开最小互操作规范候选。

当前正确状态：

```text
T6-G7-ORTHOGONAL-REPLAY-001 = CANDIDATE
G7_TASK_STATUS = PARTIALLY_RUN_LOCAL_SYNTHETIC_NOT_INTEGRATED
NOVEL_PROTOCOL_NECESSITY = NOT_DEMONSTRATED
FORMAL_STATUS_CHANGE = NONE
```
