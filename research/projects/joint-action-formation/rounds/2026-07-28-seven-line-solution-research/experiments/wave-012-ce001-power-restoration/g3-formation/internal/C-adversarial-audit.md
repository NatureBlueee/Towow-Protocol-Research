# G3 internal C adversarial audit

日期：2026-07-30  
内部 Agent identity：`/root/g3_adversarial_audit`  
处置：`BLOCKED / REVISION REQUIRED / PRESERVE CURRENT RUNS`

## 结论

当前实现的 14 个既有测试全部通过，open inventory、单模块而非共享
`choose(packet)`、任务 hash substitution 和六轴结果 shape 等局部门已生效。但第二轮只读
攻击得到 10 个红信号，其中四组会阻断当前最承重的 G3 结论：

1. E2 没有 proposal；owner 只收到 `phase + resource_id` 就返回预编译签名。错误 scope
   甚至 `owner_id=CONTROLLER` 仍被判为 `V=VALID / N=NEW_TOKEN / exact_task_success=true`。
2. `exact_s0_replay` 只比较一个未绑定 owner policy/response family 的 S0 hash；
   `REMOVE_FORMATION_OPERATOR` 也没有移除 kernel action，而是改写了 sign response。
3. E4 的 `recovery_to_value` 只要求 trace 曾出现 revoke 且随后有五字段 Effect；没有
   deadline、Acceptance、完整约束或 operation binding，也没有 revoke 后 rediscovery。
4. 三个 robust 结果没有冻结或穷举 allowed response family；同一 E0 run 是否
   effect-robust，仅由 caller 有没有临时传入 reverse branch 决定。

因此当前运行不能支持：

```text
E2_CAUSAL_FORMATION = ESTABLISHED
E2_EXACT_S0_REMOVE_REVERSE = ESTABLISHED
E4_RECOVERY_TO_VALUE = ESTABLISHED
R_EFFECT_SAFE_TERMINAL_ROBUST = ESTABLISHED
```

可保留的最窄状态是：

```text
LOCAL_TRACE_SHAPE_AND_SELECTED_FIXTURE_CONFORMANCE = POSITIVE_SCOPED
OPEN_INVENTORY_CLOSURE = UNKNOWN_PRESERVED
CURRENT_EXECUTOR_CASE_ID_BRANCHING = NOT_OBSERVED
G3_FORMATION_AND_ROBUST_REACHABILITY = BLOCKED
```

本审计没有读取 `internal/A-problem-reconstruction.md`，没有编辑实现、fixture、private
truth、tests 或 outputs。

## P0 blockers

### C-P0-01：E2 是无 proposal 的 scripted sign，Authority/scope 未被验证

`FormationExecutionService` 发现 token 缺失后直接调用
`owner_event("sign", resource_id)`；没有构造、发送或 hash-bind proposal、task bytes、
purpose、scope、recipient、expiry 或 cost（`formation/execution_service.py:72-113`）。
`OwnerService.owner_event` 的接口也只有 `phase` 与 `resource_id`
（`formation/owner_service.py:27-38`）。所以当前 trace 证明的是：

```text
resource requires token
→ fixture lookup returns SIGNED
→ token/delegation copied into state
```

它不证明 owner 对 exact proposal 理解、决定并签发。测试只检查 sign event 在 formed event
之前，并未检查 proposal 存在或 owner 看到了什么（`tests/test_module.py:82-109`）。

更严重的是，`_trace_valid` 只核对 token/delegation 的 `q_version`
（`formation/scorer.py:283-298`），不核对 signer Authority、purpose、target、scope、
expiry/current head、resource binding 或 owner receipt。定向 mutation 实测：

```text
purpose = temporary-power-C8
delegation.scope = Venue-V/C8/3kW/45min
=> V=VALID, exact_task_success=True

sign.owner_id = CONTROLLER
=> V=VALID, N=NEW_TOKEN, exact_task_success=True
```

这会让 controller/self-report 或 wrong-scope delegation 冒充 owner-owned formation。

最小修复：

- execution service 先生成独立 `Proposal`，绑定 exact task bytes/hash、resource、purpose、
  scope、expiry、recipient、cost 与 nonce；
- owner endpoint 接收 proposal bytes，并返回绑定 proposal hash 与 owner policy head 的
  signed/refused receipt；
- scorer 校验 signer 属于该 exact Authority locus、receipt current、token/delegation
  scope 完整覆盖 Q 且没有扩大；
- 加入 wrong signer、wrong scope、expired、stale head、proposal mutation 和 receipt
  tampering 的红灯测试。

### C-P0-02：exact S0 没有绑定 owner policy；remove 不是 remove

`FrozenState` 只含 case/episode/task/inventory、world state 与 kernel action list
（`formation/models.py:9-16`）；owner policy、owner event snapshot、response family、
policy head、clock/seed/budget 都不在 S0。scorer 又只用
`counterfactual.frozen_s0_sha256 == baseline.frozen_s0_sha256` 宣称 exact replay
（`formation/scorer.py:67-77`）。

攻击时把 E2 private truth 的 sign decision 从 `SIGNED` 改成 `REFUSED`，两个运行仍得到完全
相同的 S0 hash：

```text
6b494502d5faf569d50a080a0f2350bb6180aede8c6e29833cd930faddf205a4
```

scorer 仍返回 `exact_s0_replay=true`。这证明当前 exact-S0 receipt 无法发现 owner
policy/response-family transplant。

另外，E2 baseline 与 `REMOVE_FORMATION_OPERATOR` 的 `kernel_actions` 完全相同，且都包含
`REQUEST_PURPOSE_DELEGATION`。所谓 remove 实际在 `OwnerService` 的 sign phase 删除返回
字段并把 decision 改成 `FORMATION_OPERATOR_REMOVED`
（`formation/owner_service.py:56-61`）。它改变的是 owner response，不是移除 formation
operator。因此 `formation_operator_removal_blocks_value=true`
（`formation/scorer.py:123-127`）目前没有所声称的因果含义。

现有 trace 的一个窄正面是：每次 `execute_one` 都新建 OwnerService，world state 又 deep
copy；本轮 fixture 没观察到 baseline token/delegation 被带入 remove/reverse 的 frozen
world state。但这不能补上未绑定 owner policy 的缺口。

最小修复：

- S0 credential 绑定 owner policy/version heads、完整 frozen response family、inventory
  closure、budgets/horizon、clock/seed，以及实际传输 bytes；
- intervention 作为 S0 之外的单独 delta；runner 在运行前验证 S0 credential 与所有 owner
  heads；
- 真正从 executable kernel/action registry 移除 operator，让 execution service 因 action
  不可用而无法调用，而不是让 owner 改答复；
- scorer 核对 deep snapshot/heads、intervention delta 和 derived-descendant closure，
  不能只比较 S0 hash。

### C-P0-03：E4 recovery-to-value 是 false positive

执行器把 `recovery_to_value` 定义为“当前 Effect 前的 trace 中曾有任意
`RESERVATION_REVOKED`”（`formation/execution_service.py:175-181`）；scorer 只再要求
`effect_exact`（`formation/scorer.py:120-122`）。而 `_effect_matches_task` 只检查 venue、
circuit、Q version、精确 3.0kW 和 duration（`formation/scorer.py:300-313`），没有检查：

- `T0+90min` deadline 或任何时间；
- `3kW ± 5%` 的容差语义（当前反而只接受精确 3.0）；
- noise、安全、no-other-circuit；
- execute operation 与 readback operation 的 binding；
- requester `O_Q` 与 venue `O_V` Acceptance；
- Acceptance 前后的 exact Effect/Q lineage。

把 task 改为已经不可能满足的 `deadline=T0-1min`，再增加第三个 Acceptance owner `O_P`，
trace 中仍没有任何 Acceptance event，但结果仍为：

```text
exact_task_success=True
recovery_to_value=True
```

把 E4 submit operation 保持 `OP-E4-ALT-C7`、readback operation 改成 `WRONG-OP`，结果仍是
`exact_task_success=True`。

此外，alternative 在第一次 read 时已经与 revoked primary 一起按顺序返回
（`private/owner_truth.json:335-349`）。执行器只是继续迭代预给列表；没有 revoke 后的
rediscovery query、alternative qualification 或重新规划。当前可保留的是“primary reserve
返回 REVOKED 后，fixture 中第二项形成 token/delegation 并出现 C7 Effect”；不能称为
contract 要求的 recovery、rediscovery、reconstitution 与 recovery-to-value。

最小修复：

- revoke 后触发独立 rediscovery，不能把 alternative 作为初始有序 next winner；
- target/readback 绑定 operation、resource、deadline/timestamp、完整安全与目标约束；
- 实际运行 O_Q/O_V Acceptance endpoint，并把 Acceptance exact-bind 到 Q version、Effect、
  operation；
- `recovery_to_value` 由完整 Q predicate + Acceptance lineage 重算；只有安全停止时保持
  correct resolution，但 recovery-to-value 必须为 false。

### C-P0-04：robust 没有全分支量词

private fixture 没有冻结 allowed response family，runner 也没有 robust-tree traversal。
`_effect_robust_result` 的逻辑是：

- caller 传了 counterfactuals，就只看 caller 传入的这些 runs；
- 没传时，单次 Effect 就等于 effect robust；
- E4 只看 `recovery_to_value` boolean。

见 `formation/scorer.py:214-243`。safe robust 只检查这些 runs 中是否有 wrong-object Effect，
不检查越权、非法披露、stale Authority 等；terminal robust 只检查是否出现名为
`EXACT_TASK_EFFECT_OBSERVED` 或 `BOUNDED_STOP` 的 event，没有 horizon/time 语义
（`formation/scorer.py:245-281`）。

定向 mutation 对同一 E0 baseline：

```text
score(baseline, counterfactuals=[])             => R_effect_robust=TRUE
score(baseline, [REVERSE_OWNER_DECISION@read]) => R_effect_robust=FALSE
```

结果取决于 caller 有没有传 branch，而不是 run 前冻结的 response family。E2 的五个
intervention 也不是 owner 合法 response family 的穷举，不能替代 robust tree。

最小修复：

- 每 case run 前冻结合法 response family 与 observation kernel；
- 枚举或 model-check history-measurable policy 对全部 allowed branches；
- effect/safe/terminal 分别检查完整 Q、Authority/privacy safety 和 horizon termination；
- receipt 保存 branch population/hash、每支 trace 与覆盖证明；缺 population 时 robust
  必须为 `UNKNOWN`。

## P1 defects

### C-P1-01：physical 是 private boolean copy，measurable 是 realized truth scan

`R_physical_exists` 直接复制 `physical_solution_exists`
（`formation/scorer.py:180-183`）。把这个 label 改为 false、保持实际 E0 target Effect
不变，结果成为：

```text
R_physical_exists=FALSE
R_actual=TRUE
```

这不是 physical oracle witness。`R_measurable_exists` 则扫描同一份 realized
read/sign/reserve/execute truth（`formation/scorer.py:185-212`），没有 observation
histories、branch-contingent policy 或 policy witness。它虽然不再由 actual Effect 直接
反推，但仍不能支持“存在 history-measurable policy”的量词主张。

最小修复是让 physical oracle 返回可重放 sequence witness，让 measurable oracle 返回对
observation histories 的 policy/tree witness；二者都要有独立 checker，而不是 truth
boolean 或最终 owner events。

### C-P1-02：public case_id 直接泄漏语义标签

public packet 包含：

```text
E2-CONDITION-FORMATION
E4-REVOKE-WITH-ALTERNATIVE
G3-OPEN-INVENTORY-CONTROL
G3-MODEL-KERNEL-CHANGE-CONTROL
```

测试只查 `expected_label`、`operator_proposal` 等禁词，没有查 case ID
（`tests/test_module.py:49-61`）。这使 method-visible packet 直接暴露预期分类。runner
还按 exact case ID 决定哪些 counterfactual 被运行（`formation/runner.py:51-60`）。

把 E2 的 case/episode ID 换成 opaque 值后，当前 executor 的事件类型序列保持不变，说明
当前这份执行器没有实际靠 ID 选动作；这是一个已关闭的窄项。但 public packet 仍不满足盲
worker 边界，换成模型或另一实现时可直接作弊。

最小修复是 public packet 只使用 opaque handle；语义 case 名和 private truth join 保存在
scorer/controller 无法传给 actual worker 的 manifest。

### C-P1-03：trace 中的 “EXACT” event 是 producer self-report

执行器只要 readback 的 `effect_occurred` 为真就追加
`EXACT_TASK_EFFECT_OBSERVED`（`formation/execution_service.py:173-188`），没有在这里检查
target、task invariance 或 Authority。controller task-change run 中，result target 已改为
C8，readback 仍是 C7，raw trace 仍出现该 “EXACT” event；只是 scorer 后来把最终 V 判为
invalid。

最终 task substitution gate 在当前 scorer 中确实关闭，但 raw event 名不能作为 exact
evidence。应改成中性 `EFFECT_READBACK_OBSERVED`，exactness 只能由独立 verifier receipt
给出。

## 已关闭或可保留的 checklist 项

| 检查项 | 当前结果 | 边界 |
|---|---|---|
| 共享 `choose(packet)` / 五臂 alias | `CLOSED` | 当前是单 line executor，未实现 arm comparison；不得外推为方法比较 |
| explicit public `operator_proposal` | `ABSENT` | packet 没有 proposal；但 E2 实际上也完全没有 proposal，见 P0-01 |
| direct / old closure / new token / kernel / task change 字段区分 | `PRESENT` | shape 与选定 fixture 分类可复算；formation validity 被 P0 阻断 |
| open inventory → UNSAT | `CLOSED` | `C/physical/measurable/effect robust=UNKNOWN`；不能把 safe/terminal TRUE 外推为真 robust |
| controller task hash substitution | `CLOSED_SCORER_SIDE` | T/V/success 能拒绝当前 C8 改写；raw trace 的 “EXACT” 命名仍有 P1-03 |
| wrong venue/circuit readback | `CLOSED_NARROW` | 当前 scorer 拒绝 C8；operation/deadline/Acceptance/constraints 仍未绑定 |
| current fixture descendant carry-over | `NOT_OBSERVED` | fresh service/deepcopy 有效；owner policy 不在 S0 credential，exact replay 仍失败 |
| raw outputs | `PRESENT` | 11 receipts、16 raw runs有 body hash；缺完整 state/owner heads/time/cost/Acceptance |
| product/production claim | `CLOSED_BY_LABEL` | README/report 明示 local synthetic 与 `NOT_RUN` |

## 运行与红灯证据

在 `g3-formation/` 目录执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s tests -v
```

结果：

```text
Ran 14 tests in 0.075s
OK
```

随后使用不落盘的 `python3 - <<'PY' ... PY` mutation batch，分别调用
`execute_one` 与 `FormationScorer.score`，改变 proposal/scope/signer、owner policy、
deadline/Acceptance、operation binding、robust branch、physical label 与 case ID。关键原始
输出：

```text
RED E2_NO_PROPOSAL: proposal_events=0,
  owner_event_signature=(self, phase, resource_id=None)
RED E2_SCOPE_NOT_VALIDATED: V=VALID success=True
  scope=Venue-V/C8/3kW/45min
RED E2_SIGNER_NOT_VALIDATED: owner_id=CONTROLLER V=VALID
  exact_task_success=True N=NEW_TOKEN
RED REMOVE_IS_OWNER_RESPONSE_MUTATION:
  kernel_equal=True decisions=['DISCLOSED', 'FORMATION_OPERATOR_REMOVED']
RED EXACT_S0_OMITS_OWNER_POLICY:
  exact_s0_replay=True changed_sign_decision=REFUSED
RED E4_RECOVERY_IGNORES_DEADLINE_ACCEPTANCE:
  deadline=T0-1min acceptance_events=0 success=True recovery=True
RED E4_OPERATION_BINDING_IGNORED:
  submit=OP-E4-ALT-C7 readback=WRONG-OP success=True
RED ROBUST_NOT_FROZEN_FULL_BRANCH:
  without_branch=TRUE with_same_valid_reverse_branch=FALSE
RED PHYSICAL_LABEL_NOT_WITNESS:
  physical=FALSE actual=TRUE
RED PUBLIC_CASE_ID_SEMANTIC_LEAK:
  current_executor_shape_invariant=True
CLOSED OPEN_INVENTORY_UNKNOWN:
  C=UNKNOWN, physical=UNKNOWN, measurable=UNKNOWN, effect_robust=UNKNOWN
```

mutation 全部使用内存 deep copy；没有改写 fixture/private truth 或 outputs。

## 下一接口与解除 blocker 的顺序

1. 先建立 proposal/owner-receipt/Authority verifier，否则 E2 的 token 和 delegation 不是
   可接受的 formation evidence。
2. 把 owner policy/response family 纳入 frozen S0 credential，并实现真正 kernel
   operator removal；否则 remove/reverse 因果证据无效。
3. 重做 E4 exact-Q predicate、Acceptance lineage 与 revoke 后 rediscovery；否则
   recovery-to-value 仍是 false positive。
4. 冻结并穷举 response family，生成 physical/measurable/robust witnesses；缺少时将相关
   R 坐标降为 `UNKNOWN`。
5. 最后 opaque 化 public case handle，补充 mutation tests，再复跑 C 审计。

在这四个 P0 blocker 关闭前，`G3-final.md` 应明确写
`G3_FORMATION_REACHABILITY = BLOCKED`，而不是用 14/14 既有绿灯宣称 E2、E4 或 robust
已经成立。

---

## POST-FIX RECHECK — 2026-07-30

复核 identity：`/root/g3_adversarial_audit`  
处置：`FOUR P0 BLOCKERS CLOSED / TWO P1 LIMITS REMAIN`

本节保留上面的原始红灯，不改写历史。B 修复后，C 重新读取最终代码、fixtures、private
truth、tests 与 outputs，并重跑原攻击。没有编辑实现文件。

### 实际运行

命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s tests -v
```

结果：

```text
Ran 18 tests in 1.581s
OK
```

随后运行一个不落盘的 inline Python mutation batch：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
# load PUBLIC_CASES / PRIVATE_TRUTH
# execute_one + FormationScorer.score
# mutate proposal evidence, signer/head/receipt, owner policy,
# removal kernel, E4 deadline/operation/acceptance,
# robust denominator, public handles and raw event
...
PY
```

批次数字：

- 14 项原 P0/packet/raw-event mutation 全部关闭；
- 11/11 report results 的 effect/safe/terminal robust 全为 `UNKNOWN`，且各自绑定同一
  scripted response-family hash、`allowed_branch_population=None`；
- 10/10 public cases 仅使用 `H001`–`H010` opaque handles；
- 1 项既有 P1 physical-witness 攻击仍为红；
- 另加 1 项超出冻结 CE-001 owner set 的 task-mutation，暴露 Acceptance owner list
  hardcode，记为 P1 scoped-generalization limit。

### 四组 P0 复核

#### 1. E2 proposal、Authority、scope 与 receipt：`CLOSED`

baseline E2 现在先产生一个 `FORMATION_PROPOSAL_CREATED`，proposal 绑定 task hash、Q
version、resource、purpose、完整 scope、expiry、recipient、cost 与 nonce；owner sign
接口实际接收 proposal。mutation 结果：

```text
CLOSED E2_PROPOSAL:
  count=1, owner_event(..., proposal=None)
CLOSED E2_WRONG_SCOPE:
  V=INVALID, success=False
CLOSED E2_WRONG_SIGNER:
  V=INVALID, N=NEW_TOKEN, success=False
CLOSED E2_STALE_HEAD:
  V=INVALID
CLOSED E2_RECEIPT_TAMPER:
  V=INVALID
```

wrong-scope 攻击直接改写 formed delegation；wrong signer 使用
`owner_id=CONTROLLER`；stale/tamper 分别重签错误 owner-policy head 和破坏 proposal
binding。scorer 都拒绝 value。`N=NEW_TOKEN` 仍可作为“trace 中出现候选 token”的分类，
但 `V=INVALID / success=false` 不会让错误 Authority 算成功。

#### 2. owner-policy transplant 与真实 REMOVE：`CLOSED`

把 E2 sign decision 从 `SIGNED` transplant 为 `REFUSED` 后：

```text
CLOSED S0_OWNER_POLICY_TRANSPLANT:
  baseline S0=359a007f6443...
  transplant S0=a1146a9a0ad0...
  exact_s0_replay=False
```

S0 现在绑定 owner policy heads、scripted response-family hash/status、budget、horizon、
clock seed 与 public packet hash。baseline 与合法 intervention 仍从相同 credential
重放；改变 owner policy 则不再冒充 exact S0。

`REMOVE_FORMATION_OPERATOR` 现在通过独立 intervention delta 从 executable kernel 删除
`REQUEST_PURPOSE_DELEGATION`。复核结果：

```text
CLOSED REMOVE_TRUE_KERNEL_DELTA:
  removed=True
  sign_events=0
```

原 frozen kernel 仍保留，用于证明从哪个 S0 施加 delta；final executable kernel 已不含
该 action，且执行器没有调用 sign。这关闭了“改 owner answer 冒充 remove”的原红灯。

#### 3. E4 deadline、operation、Acceptance 与 post-revoke rediscovery：`CLOSED_SCOPED`

E4 initial read 现在只返回 revoked primary；alternative 只在 revoke 后的独立 rediscovery
response 中出现：

```text
CLOSED E4_POST_REVOKE_REDISCOVERY:
  initial=['BAT-R1-REVOKED']
  rediscover=True
```

value checker 现在验证 deadline、power tolerance、约束、resource/operation submit-readback
binding、readback hash，以及 O_Q/O_V 两份 exact task/effect/operation Acceptance。原攻击
结果：

```text
CLOSED E4_DEADLINE:
  success=False, recovery=False
CLOSED E4_OPERATION_BINDING:
  success=False, recovery=False
CLOSED E4_ACCEPTANCE:
  acceptance_events=2, refusal => success=False, recovery=False
```

因此当前冻结 CE-001（Acceptance owners 固定为 O_Q/O_V）内，E4
`recovery_to_value=true` 已不再由“曾 revoke + 任意 Effect”触发，且 alternative 不是
pre-revoke 有序第二项。

#### 4. robust denominator：`CLOSED_BY_HONEST_UNKNOWN`

实现没有用 E2 interventions 或单条 actual trace 冒充 robust denominator。全部 11 个
结果返回：

```text
R_effect_robust=UNKNOWN
R_safe_robust=UNKNOWN
R_terminal_robust=UNKNOWN
robust_denominator.status=UNKNOWN_UNFROZEN_COMPLETE_RESPONSE_TREE
allowed_branch_population=None
counterfactuals_are_not_robust_denominator=True
```

每个 receipt 的 `scripted_response_family_sha256` 与 S0/bindings 一致。当前没有宣称 full
branch robust；这是正确关闭，不是 robust 已被证明为 true。

### packet 与 raw trace：`CLOSED`

public packet 已移除语义 case IDs，只含 `H001`–`H010` 与 `P001`–`P010`；语义 join 在
private manifest。execution service 只看到 opaque handle。

raw trace 现在使用中性：

```text
EFFECT_READBACK_OBSERVED
```

不再由 producer 写 `EXACT_TASK_EFFECT_OBSERVED`。exactness 只由 scorer 的完整 value
predicate 给出。

### 仍未关闭的 P1

#### P1-A：physical/measurable 仍不是独立 witness

原 physical mutation 仍得到：

```text
RED P1_PHYSICAL_WITNESS:
  R_physical_exists=FALSE
  R_actual=TRUE
```

因为 physical 仍复制 private boolean；measurable 仍扫描 scripted realized truth，而非
返回 observation-history policy witness。这不再污染 robust（robust 已降 Unknown），但
`R_physical_exists / R_measurable_exists` 只能解释为当前 local fixture labels，不能写成
独立 oracle/model-check 证明。

#### P1-B：Acceptance owner set 对 CE-001 是正确的，但仍为 hardcode

scorer 与 executor 固定要求 `{"O_Q","O_V"}`，没有读取 task 的
`acceptance_required_from`。把冻结输入扩成 `["O_Q","O_V","O_P"]` 时，实际只有 O_Q/O_V
两份 Acceptance，仍返回：

```text
exact_task_success=True
recovery_to_value=True
```

这不反驳当前 CE-001 contract，因为该 contract 固定只要求 requester O_Q 与 venue O_V；
但它限制模块迁移到 task-defined owner set，也意味着不能宣称通用 exact-task checker。
最小修复是由 task 字段驱动 acceptance requests 与 required-owner equality，而不是硬编码。

### post-fix 当前最窄状态

```text
E2_OWNER_PROPOSAL_RECEIPT_VALIDATION = POSITIVE_LOCAL_SYNTHETIC
E2_EXACT_S0_REMOVE_REVERSE = POSITIVE_LOCAL_SYNTHETIC
E4_RECOVERY_TO_VALUE_FOR_FROZEN_OQ_OV_TASK = POSITIVE_LOCAL_SYNTHETIC
OPEN_INVENTORY_UNKNOWN = PRESERVED
ROBUST_TREE = NOT_RUN / HONEST_UNKNOWN
PUBLIC_PACKET_SEMANTIC_LABEL_LEAK = CLOSED
RAW_PRODUCER_EXACT_CLAIM = CLOSED
PHYSICAL_MEASURABLE_WITNESS = NOT_ESTABLISHED
GENERAL_TASK_DEFINED_ACCEPTANCE_SET = NOT_ESTABLISHED
REAL_PRODUCTS_OWNERS_POWER_EFFECT = NOT_RUN
```

第三轮没有剩余 P0 blocker。`G3-final.md` 可以撤销先前的
`G3_FORMATION_REACHABILITY = BLOCKED`，但必须保留以上 scoped/Unknown 边界：本轮支持
冻结 CE-001 local component model 的 E2 因果反事实与 E4 recovery trace，不支持 robust
tree、独立 physical/measurable witness、通用 task owner set、真实产品或现实供电结果。
