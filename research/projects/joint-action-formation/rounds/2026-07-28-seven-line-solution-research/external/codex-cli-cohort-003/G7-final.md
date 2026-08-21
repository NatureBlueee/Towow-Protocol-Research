# Codex CLI cohort 003：G7 final

日期：2026-07-30  
模块：`CE-001 / G7 reuse-reopen-migration`  
状态：`LOCAL_SYNTHETIC COMPONENT MODULE / E4+E6 RUN / NO FORMAL STATUS CHANGE`

## 最终判断

本 cohort 为 CE-001 建立了一个可运行的 G7 局部模块，并实际执行了 E4 与 E6：

```text
E4/E6 cases                         2
ExactTaskSuccess                    2/2
CorrectResolution                   2/2
RecoveryToValue                     2/2
UnsafeEffect                        0
DuplicateEffect                     0
WrongObjectReliance                 0
UnreconciledEffect                  0
HistoryRewrite                      0
runner audit                        PASS
```

这个 `2/2` 只表示当前两个本地合成 case 在已实现 owner/target component model 中通过。
它不是 CE-001 八 case、跨七线完整 episode、真实产品、真人 Authority/Acceptance、物理供电、
付款或生产迁移的结果。

当前最窄结论是：

```text
E4_ALTERNATIVE_RECOVERY_TO_VALUE = POSITIVE_SCOPED_LOCAL_SYNTHETIC
E6_EFFECT_ACCEPTANCE_GAP_RECOVERY = POSITIVE_SCOPED_LOCAL_SYNTHETIC
APPEND_ONLY_AND_EFFECT_RECONCILIATION = POSITIVE_FOR_TESTED_TRACES
KNOWN_C_AGENT_MUTATIONS = 17/17 CLOSED_OR_HONESTLY_BOUNDED
HIDDEN_PAIR = NOT_CONSTRUCTED
SAFETY_LIVENESS_FRONTIER = NOT_RUN
ADAPTER_SEMANTIC_INDEPENDENCE = NOT_ESTABLISHED
COLD_REPEAT_FULL_LIFECYCLE = NOT_MEASURED
FULL_CE001_AND_REAL_PRODUCT = NOT_RUN
```

## 实际内部 Agent

| 角色 | 实际 identity | 职责 | 交付 |
|---|---|---|---|
| A | `/root/g7_agent_a` / `G7 INTERNAL AGENT A` | 独立重建 G7 原始问题、CE-001 E4/E6 接口与正确 hidden-pair oracle | `g7-evolution/A-reconstruction.md` |
| B | `/root/g7_agent_b` / `G7_INTERNAL_AGENT_B` | 实现 owner adapters、Context、runtime、history、Effect、migration、runner 与 tests | `g7-evolution/g7evo/`、fixture、runner、raw traces、results |
| C | `/root/g7_agent_c` / `G7 INTERNAL AGENT C` | 不预设赢家，攻击 truth-copy、alias、目标偷换、伪恢复、history rewrite、fence、capsule 与成本口径 | `g7-evolution/C-adversarial-audit.md`、`tests/test_adversarial.py` |

三者共享模型家族、仓库与研究传统，不构成外部独立实验室复现。Agent 数量和一致意见未被当作
结果证据；最终数字来自实际 trace、mutation tests 与根会话复跑。

## E4：撤销后恢复到原任务价值

E4 的 runner 不把安全停止算作成功。执行链为：

```text
O_R_PRIMARY exact reservation revocation
→ append Defeater，不删除旧 reservation/history
→ 从 resource-primary 计算 local causal closure
→ O_R_ALTERNATIVE 对 Q@v1 / Circuit-C7 / operation 作 exact-scope commitment
→ O_S exact-operation safety permit
→ alternative-bound target Effect
→ O_E exact-object readback
→ O_Q requester Acceptance
→ O_V venue Acceptance
→ O_P 在两份 Acceptance 后 Settlement
```

局部重开 closure 为旧 resource 分支及其事实下游，不包含 alternative 或未被击败的
`safety-root`。另一个 `safety-root` intervention 计算出全图 global closure，防止把共享根
变化伪装成局部重开。

关键防伪：

- alternative lease 的 `ACTIVE` 标签不足以执行，必须额外形成 exact
  `Q_version/object/operation/expiry` commitment；
- target Effect 必须绑定 alternative resource/reservation；
- target 若已有 primary 的同 semantic-key Effect，`DEDUPLICATED` 只算旧 Effect 对账，
  不算 alternative recovery-to-value；
- alternative 不可用时返回 `BLOCK / RecoveryToValue=false`。

## E6：Effect 后、Acceptance 前 crash 与 takeover

source coordinator 在 epoch 1 提交 Effect、丢失 response、Acceptance 尚未发生时崩溃。
target coordinator：

```text
验证 capsule hash、schema、required fields 与 obligation 语义
→ 验证并导入 source append-only history prefix
→ 在独立 DurableFenceAuthority 中安装 epoch-2 fence
→ O_E exact semantic-key readback
→ 确认 Effect count=1，禁止 replay
→ 分别恢复 O_Q/O_V Acceptance
→ O_P 在两份 Acceptance 后 Settlement
→ old runtime epoch-1 restart 被 target-side fence 拒绝
```

`TARGET_RESTART_LOSES_EPOCH` 与“新建 target runtime instance”两个攻击都共享同一外部 fence
authority 复跑；old runtime 仍返回 `FENCED_OR_DENIED`。这支持当前本地 component model
中的跨实例 fence，不支持现实权限域、分布式持久化或生产 split-brain 已经解决。

## History、Effect reconciliation 与 Context

history 使用 hash-linked append-only records。E4/E6 都从 emitted records 重新验证 chain；
E6 target history 保留 source prefix 后只追加 takeover、reconciliation、Acceptance、
Settlement 与旧 runtime 拒绝。修改历史 payload 会使验证失败，不能由常量
`history_prefix_preserved=true` 遮蔽。

Effect reconciliation 保持：

```text
episode / Q_version / object / operation / semantic_effect_key
```

E6 capsule 中一个 unresolved Effect key 经 O_E readback 后降为零，Effect count 保持 1。
workflow activity、response loss 或 imported completed flag 不代替 Effect readback。

Context 对以下字段做存在性、非空、binding hash、current packet 和 evidence binding 检查：

```text
episode_id / Q_version / object_id / operation_id / semantic_effect_key
dependency_graph_version / Authority evidence hashes / history root
runtime epoch / pending Acceptance / context binding hash
```

wrong Q/object、wrong operation/effect key、空 evidence/history 以及不可验证 transplant 均
fail closed。字段删除测试支持“这些字段对当前实现是 required”；不支持它们是所有现实
runtime 的全局最小闭包。

## Cold / repeat 与第二 adapter

cold/repeat 保存 owner query、disclosure、wait、human、compute/tool、formation/setup、
assurance、recovery/migration、governance 与 opportunity-loss 原生轴。当前 fixture 中 repeat
的 query 与 disclosure 较少，但这些数字仍是合成常数，没有独立 lane、长期故障分布或统一
价值函数，因此结果显式标记：

```text
cost_comparison_status = NOT_MEASURED_FULL_LIFECYCLE
```

模块实现了不同 native call/data shapes：

- resource lease/commitment adapter；
- safety policy adapter；
- source nested capsule exporter；
- target detached-metadata capsule importer。

unknown schema、空 Acceptance/Settlement obligation、空 owner evidence 和 required field
loss 都被拒绝。签名与局部行为不同不等于第二个真实 runtime 已独立复现，因此结果显式标记：

```text
semantic_independence = NOT_ESTABLISHED
```

## Capsule field loss

删除 `recovery.pending_acceptance` 后，即使攻击者重算合法 capsule hash：

```text
imported=false
dispatch_after_import=false
final_action=BOUNDED_UNKNOWN
SafetyGatePassed=true
CorrectResolution=false
```

这只表示 field-loss 攻击安全失败；它不是 migration portability 成功。

## Hidden pair 与 w010/w011 纠错

本模块没有构造 hidden pair，因此明确写：

```text
HIDDEN_PAIR = NOT_CONSTRUCTED
SAFETY_LIVENESS_FRONTIER = NOT_RUN
```

没有报告 frontier pass，也没有重复 w010/w011 两侧允许同一保守动作却宣称不可兼得的错误。
Agent A 已冻结未来 pair 的正确接口：

- valid 分支最终必须 `CONTINUE`，否则计 `liveness_loss`；
- revoked 分支禁止 `CONTINUE`；
- revoked 分支只安全阻断但未走 alternative recovery 时，
  `RecoveryToValue=false`；
- grader 分别报告 safety loss、liveness loss、closure 与 missed value。

## 红灯历史

首批实现的原 13 项测试全绿后，根会话首先复现：

```text
wrong prior Context Q/object → repeat still CONTINUE
```

Agent C 随后冻结 14 项合同攻击，首跑为：

```text
12 RED / 2 PASS / 0 ERROR
```

红灯包括 wrong Q/object/operation/effect identity、不可验证 history/evidence、只验字段
presence、成本缺轴、primary Effect 冒充 alternative recovery、E4 history 假绿、E6
同源目标偷换、volatile fence、空 obligations、field-loss 口径混淆和 hidden-pair 未声明。

第一轮修复后 14/14 通过，但 C 没有停止，又新增三个红灯：

1. fence 仍随单个 `EffectTarget` instance 消失；
2. adapter 只有签名差异却没有诚实限制 semantic independence；
3. 固定成本列被误读为 full-lifecycle measurement。

它们分别通过外部共享 fence authority及两个明确的 `NOT_ESTABLISHED/NOT_MEASURED` 边界关闭。
集成中还真实出现过一次测试读取旧 commitment schema 的 `KeyError`，修正消费者后才进入最终
绿灯。完整记录保存在 `g7-evolution/raw/red-history.json`；最终绿灯没有删除这些失败。

## 最终验证

在 `g7-evolution/` 中实际执行：

```bash
python3 runner.py --output raw/run-traces.json
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/g7-root-pycache \
  python3 -m py_compile runner.py g7evo/*.py tests/*.py
PYTHONPYCACHEPREFIX=/tmp/g7-root-pycache \
  python3 tests/negative_controls.py
```

结果：

```text
runner                         E4/E6 2/2, audit PASS
Agent C adversarial tests      17/17 PASS
full suite                     33/33 PASS
py_compile                     PASS
negative control               RED_DETECTED, exit 1 as expected
```

negative control 把 old runtime restart 改成 `COMMITTED`；auditor 返回非零并指出
`E6 old runtime restart was not fenced`。它证明 auditor 能拒绝这个特定 mutant，不证明
所有 false-green 都已被穷尽。

## 能支持、不能支持与下一接口

能支持：

- 当前两个本地合成 case 中，E4 alternative recovery-to-value 与 E6
  Effect/Acceptance gap recovery 可运行；
- tested traces 中 Effect 对账、零重复、双 Acceptance、Settlement、append-only prefix 与
  old-runtime fence 闭合；
- 17 个已知敌对 mutation 被关闭或被诚实降级；
- field-loss fail closed 与 portability success 已分开。

不能支持：

- CE-001 八 case、G1–G7 完整 episode或任一比较 arm 已解决；
- 第二 adapter 已获得独立语义复现；
- Context 已证明全局最小充分；
- repeat 的全生命周期净值为正；
- hidden-pair safety-liveness frontier；
- 真实产品、真人 owner、物理 Effect、生产恢复、现实付款或长期价值；
- 新机制必要或不必要；
- Problem、LineContract、MechanismProfile、NOW、PROGRAM 或正式 claim 的任何状态变化。

下一条高价值接口不是增加同源 world 数量，而是：

1. 在真正不同的 target-native obligation/runtime model 上重做 capsule import、resume 与
   owner readback；
2. 用独立 cold/repeat lanes 和相同 prospective failure schedule 测全生命周期成本与价值；
3. 把 E4/E6 module 接回同一个 CE-001 G1–G7 episode，由独立 owner/target services 产生
   Authority、Effect、Acceptance 与 Settlement；
4. 若以后构造 hidden pair，严格使用相反 final requirement，并分别计 safety/liveness。

