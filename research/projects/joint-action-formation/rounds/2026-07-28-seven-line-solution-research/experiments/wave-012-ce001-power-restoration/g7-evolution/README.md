# CE-001 G7 evolution

## 第二轮当前实现

当前公开实现是 process/state/byte-separated 的 G7 line-local evidence runner。权威说明见
[`B-implementation-v2.md`](B-implementation-v2.md)，实际原始证据见
[`raw/run-traces.json`](raw/run-traces.json)，窄摘要与精确 G7 envelope 见
[`results.json`](results.json)。

当前验证：

```text
原首轮风险测试              33/33 PASS
第二轮冻结根红灯            19/19 PASS
新增 process-boundary tests  6/6 PASS
全套                         58/58 PASS
negative control             RED_DETECTED
integration preflight        QUALIFIED_COMPONENT_OUTPUTS
```

`EvolutionModule.run_all()` 只输出 G7 line-local evidence 和 namespaced integration
fragment；下文是首轮实现与风险历史，只对应 internal regression surface，不再描述当前
runner 的公开输出。

---

# 首轮历史：Agent B 最小可运行模块

实现身份：`G7_INTERNAL_AGENT_B`  
证据状态：`LOCAL_SYNTHETIC_COMPONENT_MODEL / NO FORMAL STATUS CHANGE`  
覆盖范围：CE-001 的 `E4-REVOKE-WITH-ALTERNATIVE`、`E6-MIGRATION-REPLAY` 与指定
failure injections；不是八 case 完整 episode。

## 结果

当前 runner 在两个冻结局部 case 上得到：

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
result audit                        PASS (0 violations)
```

这两个正例依赖本地 owner/target 模拟器，不是现实供电、真人 Acceptance、法律 Authority、
真实付款、生产迁移或跨域复现。

## 实际实现

### E4：撤销后恢复到任务价值

resource owner 的 native lease adapter 先返回 primary reservation 已撤销，再给出合法
alternative。模块执行：

```text
append revocation Defeater
→ 从 resource-primary 计算 downstream causal closure
→ LOCAL_REOPEN
→ 查询 alternative lease 与独立 safety permit
→ 形成 alternative-bound commitment
→ Circuit-C7 target Effect
→ exact-object readback
→ Acceptance
→ Settlement
```

alternative lease 不是一个裸 `ACTIVE` 标签：O_R native scope 必须逐项绑定
`Q@v1 / Circuit-C7 / power-C7-45m-v1 / expiry`，并返回
`COMMITTED_EXACT_SCOPE` receipt；任一 scope 被移植时 E4 阻断。

primary 旧 Effect 即使以同一 semantic key 被 target `DEDUPLICATED`，也不能算 alternative
recovery；正例要求新 dispatch 为 `COMMITTED`，且 target Effect 同时绑定
`battery-alternative / lease-alternative / O_R commitment evidence hash`。安全根变化的
intervention 从 `safety-root`
计算全图 `GLOBAL_REOPEN`，不把局部和全局重开混成标签选择。

### E6：Effect 后、Acceptance 前 crash

旧 coordinator 在 epoch 1 提交一次 Effect 后丢失 response 并崩溃。source capsule 带入
exact Q/object/operation/effect key、append-only history、未对账 Effect、待完成
Acceptance/Settlement obligation 与 owner evidence hashes。target runtime：

```text
验证 capsule hash、schema、字段与 obligation 语义
→ 导入并重验 source history chain
→ 在 target owner 域安装 durable epoch-2 fence
→ O_E exact-key readback
→ 发现 Effect 已发生，禁止 replay
→ 分别取得 O_Q requester Acceptance 与 O_V venue Acceptance
→ O_P 仅绑定两份 exact receipt 后 Settlement
→ 拒绝 epoch-1 old runtime restart
```

nominal 结果为 target Effect count `1`、replay suppressed、old runtime
`FENCED_OR_DENIED`、source history prefix preserved、unresolved Effect 从一个降为零。
fence 由独立 `DurableFenceAuthority` 持有；old runtime 使用新建的 `EffectTarget` 实例、
只共享该外部 fence owner，仍被拒绝。`TARGET_RESTART_LOSES_EPOCH` mutation 因而不依赖
coordinator 或原 target 对象的 volatile epoch。

### Context 与 adapter

Context cold/repeat 都逐项绑定：

```text
episode_id / Q_version / object_id / operation_id / semantic_effect_key
dependency_graph_version / Authority evidence hashes / history root
runtime epoch / pending Acceptance / local binding hash
```

repeat 会重查 resource owner，并验证 prior Context 与当前 packet 的 exact bindings、
safety evidence 的 operation binding 和 Context binding hash。wrong Q/object/operation/
effect key/history/evidence transplant 均 fail closed。

cold/repeat 保留十个生命周期成本轴，而不是只报 query 数：

| 轴 | cold | repeat |
|---|---:|---:|
| owner queries | 2 | 1 |
| disclosure bytes | 855 | 491 |
| calendar wait | 0 | 0 |
| human minutes | 0 | 0 |
| compute/tool | 3 | 2 |
| formation/adapter setup | 2 | 0 |
| assurance | 2 | 1 |
| recovery/migration | 0 | 0 |
| governance | 1 | 0 |
| opportunity loss | 0 | 0 |

这些是同一合成 fixture 的原生常数，结果显式标记
`NOT_MEASURED_FULL_LIFECYCLE`；未换算成统一价值函数，不能据此宣称长期净值、全生命周期
比较或普遍“repeat 更便宜”。

模块实际使用不同 native call/data shapes：

- `LeaseRegistryAdapter.fetch_lease(reservation_ref, if_revision=...)`；
- `SafetyPermitAdapter.verify(operation, policy_revision, at_epoch=...)`；
- source `CapsuleV1Exporter.export(...)`；
- target `CapsuleV2Importer.ingest(metadata, content, target_runtime_id=...)`。

unknown schema、空 Acceptance/Settlement obligation、空 owner evidence 或 required
field loss 均被 target importer 拒绝。函数签名和这些 mutation 只支持当前两个 adapter
合同有行为差异；结果显式标记 `semantic_independence=NOT_ESTABLISHED`，不支持真实产品或
跨组织语义独立性。

## Capsule field-loss 边界

`DROP_MIGRATION_CAPSULE_FIELD` 删除 `recovery.pending_acceptance` 后，即使攻击者重新计算
合法 capsule hash，importer 仍返回：

```text
imported=false
final_action=BOUNDED_UNKNOWN
dispatch_after_import=false
SafetyGatePassed=true
CorrectResolution=false
```

fail closed 是安全攻击通过，不是 migration portability 成功。

## Hidden pair

```text
HIDDEN_PAIR = NOT_CONSTRUCTED
SAFETY_LIVENESS_FRONTIER = NOT_RUN
```

本模块没有用一对 hidden worlds 支持 safety-liveness 结论，因此不强造 pair，也不报告
frontier pass。若后续实例化，valid 分支必须要求 `CONTINUE` 或计 liveness loss，revoked
分支禁止直接 `CONTINUE`。

## 红灯历史

红灯保留在 [`raw/red-history.json`](raw/red-history.json)：

- root 与 Agent B 复现：wrong Q/object prior Context 仍 `CONTINUE`；
- Agent C 冻结攻击集：首轮 `14 tests / 12 RED / 2 PASS / 0 ERROR`；
- expected negative control：old runtime 能提交时 auditor 非零退出；
- 修复后 validator 变强，旧单值 test assertion 暂时红灯，随后只修测试合同。
- alternative commitment event schema 改动后，全套一度
  `33 tests / 1 ERROR`；修复 evidence 接口兼容后才恢复全绿。

修复没有删除这些失败；首轮 Agent C 攻击集修复后为 `14/14 PASS`。Agent C 随后新增三个
二阶攻击，三项先实际变红；进一步修复后，扩展集合为 `17/17 PASS`。这只关闭列出的
mutants。

## 文件与复现

- `g7evo/model.py`：append-only history、causal closure、Effect/Acceptance owners；
- `g7evo/adapters.py`：两个 owner-native adapter 与两个 capsule interface；
- `g7evo/runtime.py`：E4/E6、Context、migration/reconciliation；
- `g7evo/audit.py`：从结果记录复核关键合同；
- `fixtures/ce001-g7.json`：无 private expected label 的合成输入；
- `raw/run-traces.json`：完整原始运行记录；
- `results.json`：窄摘要；
- `tests/test_g7_evolution.py`：实现与 failure-injection tests；
- `tests/test_adversarial.py`：Agent C 冻结攻击集；
- `tests/negative_controls.py`：预期非零的 split-brain mutant。

在本目录运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7b-pycache python3 runner.py
PYTHONPYCACHEPREFIX=/tmp/g7b-pycache python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/g7b-pycache \
  python3 -m py_compile runner.py g7evo/*.py tests/*.py
```

当前第二轮复核：runner audit `PASS`；原首轮风险测试 `33/33 PASS`；Agent C
冻结根红灯 `19/19 PASS`；新增 process-boundary tests `6/6 PASS`；全套
`58/58 PASS`；compile `PASS`。

预期红灯：

```bash
PYTHONPYCACHEPREFIX=/tmp/g7b-pycache python3 tests/negative_controls.py
```

它应以 exit `1` 返回 `RED_DETECTED`；若变成 exit `0`，说明 auditor 对 split-brain mutant
出现 false green。

## 不能支持

- CE-001 八 case 或 G1–G7 完整 episode 已解决；
- 两个 adapter 已在真实产品/权限域间实现通用 portability；
- Context 已证明全局最小或长期净值为正；
- hidden-pair safety-liveness frontier；
- 任一比较 arm 胜出；
- novel mechanism 必要或不必要；
- Problem、LineContract、MechanismProfile、NOW、PROGRAM 或正式 claim 的任何变化。
