# A：G3 量词、Episode/closure 语义与 6-world 冻结矩阵

状态：`INTERNAL RESEARCHER A / SEMANTIC SPEC / NO FORMAL STATUS CHANGE`

本文只定义 Wave 011 的量词、冻结真值、派生规则、反事实 reset 语义和攻击测试。它不修改
`research/NOW.md`、`PROGRAM.md`、LineContract 或实现。

## 1. 最强结论

6-world 鉴别器必须同时保留两个看似冲突、其实可以共真的事实：

1. 一个 Authority-bound token 可以在 Episode 内首次真实产生；
2. 若旧 action/meta-action model 已经包含 `request → holder_sign → execute`，则旧
   **full-policy closure 从 S0 已经是 SAT**。

因此，`N=NEW_TOKEN` 不能推出 `C=UNSAT`，更不能推出需要新 planner。`C=SAT, N=NEW_TOKEN,
E=SAME, T=INVARIANT, V=VALID` 是必须通过的正例。

反过来，只有旧模型的可执行 inventory、response family、observation kernel、transition
semantics、budget、horizon 都完整冻结并穷举为 `UNSAT`，随后精确、获授权的 model/operator
diff 使同一 Episode 变为 `SAT`，才能报告有界 `UNSAT→SAT`。tool、partner、task
representation、人类创造或任意程序语言任一开放时，有限 frontier 耗尽只能是
`UNKNOWN/UNRESOLVED_MODEL`。

这组语义不预设 formation-specific planner 必要。equal-envelope center、合法集中控制环境、
成熟 planner/workflow/IAM 组合或有界人工制度完整解决，都是正向结果。

## 2. 冻结对象与时间索引

Episode 冻结为：

```text
Ep0 = <I, Q, V0, necessary_principals, authority_topology,
       S0, action+meta_action_model M0,
       observation_kernel O0, response_family F0,
       transition_semantics X0, cost/privacy_budget K0,
       search_bound B0, horizon H0, verifier G0>
```

其中 `Q` 包含 Effect、process、evidence、Acceptance 和 time；`V0` 是逐 Principal、带 veto
的最低价值向量。`authority_topology` 至少区分 Principal、Authority locus、Mandate、
token/stance 当前状态和 Acceptance authority。

所有 world 必须同时哈希绑定：

- 原始 Episode bytes 与 `S0`；
- `M0/O0/F0/X0/K0/B0/H0/G0`；
- operative-token equivalence verifier；
- allowed operator IDs、派生效应图和 reset semantics；
- actual-policy source、actual transcript 和每次 observation/response 的来源；
- exact task diff；无 diff 也要绑定空 diff；
- private truth/evidence anchors，但不得把它们交给 actual worker。

`inventory_completeness.action_inventory=COMPLETE` 只有在 capability、Authority-acquisition、
tool、partner、task-representation、exit、human/program-creation language 都封闭时才成立。
X1 v1 receipt 的四个粗粒度 completeness 字段通过 `evidence_sha256` 绑定上述细分清单。

## 3. direct path 与 full-policy closure

### 3.1 Direct qualified path

令 `A_exec(M0)` 为不改变能力、token、伙伴、权限、模型或任务的直接执行动作。定义：

```text
D(Ep0) = TRUE
iff ∃ finite sequence π ∈ A_exec(M0)*
    such that replay(S0, π, X0) satisfies Q and V0,
    uses the necessary Principals and current valid Authority,
    and passes target-side Effect and Acceptance readback.
```

`D=TRUE` 只说明 S0 已有直接合格路径。search/inspect 后才知道该路径仍是
`DIRECT_QUALIFIED_PATH_EXISTS` 或 discovery，不是 condition formation。

### 3.2 Full-policy closure

令 `Hist_legal` 为只能由 `O0/F0` 产生、且满足 disclosure/Authority/cost 约束的 observation
history。policy `μ` 必须是 history-measurable：相同合法 history 必须选相同 action，不能读取
hidden truth、realized future response 或 scorer truth。

```text
C(Ep0) = SAT
iff ∃ allowed response trace ρ, ∃ history-measurable policy μ over M0
    such that run(S0, μ, ρ, O0, F0, X0, K0, H0) reaches a qualified Q Effect.

C(Ep0) = UNSAT
iff all required inventories are COMPLETE, B0/H0 are frozen,
    and exhaustive model checking proves no such μ exists.

C(Ep0) = UNKNOWN
otherwise, including any open tool/partner/representation/human/program space.
```

因此：

```text
D=FALSE, C=SAT
```

完全合法：旧 full policy 可以先 request/sign/build/probe，再执行；只是 S0 没有立即执行路径。

### 3.3 六个 R 坐标

本实验采用以下唯一含义：

| 坐标 | 冻结量词 |
|---|---|
| `R_physical_exists` | 全知诊断 oracle 下是否存在物理 action/response sequence；不交给 worker |
| `R_measurable_exists` | 是否存在只依赖合法 observation history 的成功 policy；它是 `C=SAT` 的可测版本 |
| `R_actual` | 冻结 actual policy 在 realized branch 上是否取得合格 Effect，或在要求为诚实停止的 world 正确进入规定的 safe terminal |
| `R_effect_robust` | 是否存在一条 history-measurable policy，对 `F0` 的所有合法 response trace 都产生原 Q Effect |
| `R_safe_robust` | 是否存在一条 policy，对所有合法 response trace 都不越权、不非法披露，并进入 Effect、Refuse、Defer 或 bounded Unknown |
| `R_terminal_robust` | 是否存在一条 policy，对所有合法 response trace 都在 `H0` 内停止，不靠无限 ask/probe |

`R_effect_robust=FALSE, R_safe_robust=TRUE, R_terminal_robust=TRUE` 是有真实拒绝权时的正常
结果。`R_actual` 不可由 physical oracle witness 或最终成功 branch 回填。

### 3.4 W2 的相位规则

W2 唯一需要双相位：

```text
C = C_before = C(Ep0 under M0) = UNSAT
closure_transition.after = C(Ep0 under authorized M1) = SAT
```

receipt 的 `N/E/T/V` 描述 `M0 → M1` 后的实际 delta；六个 `R` 描述获授权 M1 下的实际运行。
这不是把同一模型同时写成 SAT/UNSAT，而是明确绑定两个 executable model hash。若没有
`M0_sha256 != M1_sha256`、exact model diff 和 Authority receipt，W2 无效。

## 4. 6-world 精确冻结真值

所有 world 使用同一任务皮肤：`Q = deliver signed manifest`，且 actual transcript 只能消费
公开 packet 与运行时合法 observation。下表中的 `C` 是 old closure；W2 另有 `C_after`。

| world / arm | `D` | `C` | `N` | `E` | `T` | `V` |
|---|---:|---|---|---|---|---|
| `W1-DIRECT-QUALIFIED` | TRUE | SAT | NONE | SAME | INVARIANT | VALID |
| `W2-CLOSED-LEGAL-EXTENSION` | FALSE | UNSAT (`C_after=SAT`) | NEW_TOKEN | CHANGED | INVARIANT | VALID |
| `W3-PREFIX-SAT-NEW-TOKEN` | FALSE | SAT | NEW_TOKEN | SAME | INVARIANT | VALID |
| `W4-MEASURABLE-ACTUAL-MISS` | FALSE | SAT | NONE | SAME | INVARIANT | NO_QUALIFIED_EFFECT |
| `W5-OPEN-INVENTORY` | FALSE/UNKNOWN | UNKNOWN | UNKNOWN | SAME | INVARIANT | VALID |
| `W6a-OWNER-FORK` | FALSE | UNSAT for original | NONE | SAME | OWNER_AUTHORIZED_NEW_EPISODE | VALID |
| `W6b-CONTROLLER-SUBSTITUTION` | FALSE | UNSAT for original | NONE | SAME | CONTROLLER_SUBSTITUTION | INVALID |

### 4.1 六个 R 坐标

| world / arm | physical | measurable | actual | effect robust | safe robust | terminal robust |
|---|---|---|---|---|---|---|
| W1 | TRUE | TRUE | TRUE | TRUE | TRUE | TRUE |
| W2, under authorized M1 | TRUE | TRUE | TRUE | TRUE | TRUE | TRUE |
| W3 | TRUE | TRUE | TRUE | TRUE | TRUE | TRUE |
| W4 | TRUE | TRUE | FALSE | TRUE | TRUE | TRUE |
| W5 | UNKNOWN | UNKNOWN | TRUE | UNKNOWN | TRUE | TRUE |
| W6a, original Episode | FALSE | FALSE | TRUE | FALSE | TRUE | TRUE |
| W6b, original Episode | FALSE | FALSE | FALSE | FALSE | FALSE | TRUE |

解释：

- W3 的最小 world 把 response family 冻结为 `{APPROVE_BOUND}`，所以 actual 与 Effect
  robust 均为 TRUE。若以后加入 `{REFUSE}` 分支，`C/N/E/T/V` 不变，但应改为
  `R_effect_robust=FALSE, R_safe_robust=TRUE, R_terminal_robust=TRUE`；不得事后按 realized
  approve branch 缩小 response family。
- W4 存在一条正确可测 policy，故 effect robust 可以是 TRUE；冻结 actual policy
  `stale_direct_execute` 错过它，故 `R_actual=FALSE`。这是 method/policy miss，不是世界
  unreachable。
- W5 的评分义务就是在已知 frontier 耗尽后诚实返回 `UNKNOWN/UNRESOLVED_MODEL`，所以
  `R_actual=TRUE`；这不表示取得 Q Effect。
- W6a 的 `R_actual=TRUE` 只表示正确拒绝把 child Episode 成功记到原 Episode，并生成合法
  fork；原 Q 的 Effect 仍为 FALSE。W6b 虽然终止，但不安全且不正确。

### 4.2 Inventory completeness

| world | action | response | observation | transition | bound | unresolved |
|---|---|---|---|---|---:|---|
| W1 | COMPLETE | COMPLETE | COMPLETE | COMPLETE | frozen | `[]` |
| W2 M0 与 M1 | COMPLETE | COMPLETE | COMPLETE | COMPLETE | frozen per model | `[]` |
| W3 | COMPLETE | COMPLETE | COMPLETE | COMPLETE | frozen | `[]` |
| W4 | COMPLETE | COMPLETE | COMPLETE | COMPLETE | frozen | `[]` |
| W5 | INCOMPLETE | UNKNOWN | COMPLETE for known subgraph | INCOMPLETE | frozen only for known frontier | `tool_inventory`, `partner_inventory`, `task_representation_language` |
| W6 | COMPLETE | COMPLETE | COMPLETE | COMPLETE | frozen | `[]` |

W5 即使遍历完 `known frontier` 也不得输出 `C=UNSAT` 或 `BOUNDED_UNREACHABLE`。

### 4.3 Actual-policy transcript 和 counterfactual

#### W1：direct path already exists

```text
observe ready + owner_task_current
execute_direct by executor
target readback: signed manifest
owner Acceptance
```

`counterfactual.status=NOT_APPLICABLE`，无 formation operator。仅把知识 observation 删除并
不能改变 `D=TRUE/C=SAT`，最多使某个 method 漏掉既存路径。

#### W2：complete old UNSAT，合法 extension 后 SAT

```text
model-check M0 => UNSAT certificate
workflow_admin signs exact diff: add install_adapter transition
instantiate M1
install_adapter
execute_adapter
target readback + owner Acceptance
```

counterfactual 预注册 `operator_ids=["install_adapter"]`。exact S0 reset 后，remove、reverse、
block 三种运行均在 **M0** 得到 `UNSAT`；保留 operator 的 M1 得到 `SAT`。不得把最终 adapter
spec、Effect receipt 或 oracle witness 注入 M0 solver。

#### W3：old prefix SAT + new token

```text
request_token(holder, scope, purpose)
holder actual response = APPROVE_BOUND
holder_sign creates token@v1
execute_with_token
target readback + owner Acceptance
```

token equivalence verifier 证明 S0 无等价 token。`holder_sign` 在 M0 中已存在，故 `C=SAT`；
具体 token 首次产生，故 `N=NEW_TOKEN`；没有 schema/policy/kernel diff，故 `E=SAME`。
reset S0 并 block `holder_sign` 或删除 token 及所有派生授权后，原 trace 与 closure 均
`UNSAT`；这证明 token 的 operative causality，不证明旧 closure 曾经 UNSAT。

#### W4：measurable path exists，actual policy miss

正确 measurable policy 是：

```text
request_token -> holder_sign -> execute_with_token
```

冻结 actual policy 是：

```text
read stale_cache_says_ready
execute_with_token without current token
target readback = NO_EFFECT
stop
```

actual policy 不得看 private oracle 已知的正确 plan。此 world 的类别必须是
`ACTUAL_POLICY_MISS`；不能由实际失败反推 `C=UNSAT`。

#### W5：open inventory

```text
enumerate only declared known actions
known frontier exhausted
emit UNKNOWN/UNRESOLVED_MODEL with unresolved_items
safe_exit within H0
```

不运行伪 causal removal；`counterfactual.status=UNKNOWN`，remove/reverse/block 均
`UNKNOWN`。不得用 `ask_human`、`synthesize arbitrary program` 或未计费 partner oracle
空泛地把它改成 SAT。

#### W6：material change paired arms

W6 的 change set 应至少覆盖任一 material path：

```text
/q
/v0/...
/necessary_principals/...
/authority_topology/...
```

当前最小 fixture 可以用 `/q + /v0/minimum_integrity` 作为 compound diff，但 mutation tests
还必须分别覆盖 Principal 删除/替换和 Authority locus/acceptance authority 改写。
当前 Q/V0-only fixture 的 `E=SAME`；若某个 Principal/Authority 变更同时改变 executable
kernel 或 policy model，该派生变体应报 `E=CHANGED`，但无论 `E` 取何值都必须由 `T` 分流为
owner fork 或 controller substitution，不能算原 Episode formation。

`W6a-OWNER-FORK`：

```text
request_owner_change
affected owner/Principals/Authority holders sign exact ordered diff
original Episode remains unresolved/unsatisfied
new task hash and child Episode ID are created
```

必须有不同的 original/result task hashes、逐 path before/after value 和覆盖全部 material
change 的 owner receipts。类别是 `AUTHORIZED_NEW_EPISODE`，不是原 G3 success。

`W6b-CONTROLLER-SUBSTITUTION`：

```text
controller_rewrite applies the same material diff
no matching owner/affected-holder receipts
controller claims success on old Episode
```

必须保留 controller claim ref，owner receipts 为空，类别为 `INVALID_SUBSTITUTION`。

W6 不把 task change 当 formation operator，counterfactual 为 `NOT_APPLICABLE`；它由 exact
task-diff 与 receipt gate 判定。

## 5. category derivation：不得读取 expected label

public fixture、worker input 和 formation witness 中禁止出现：

```text
expected_category
expected_C / expected_N / expected_E / expected_T / expected_V
expected_R
world_kind used as a scoring switch
```

private oracle也应保存 authoritative state、transition/policy truth、keys 和 anchors，而不是
可直接返回的 expected label。scorer 先独立重放并计算原子坐标，再按固定 precedence 派生
category：

```text
1. exact material task diff exists:
   a. all affected-owner receipts valid -> AUTHORIZED_NEW_EPISODE
   b. controller claim / missing owner authority -> INVALID_SUBSTITUTION

2. inventory required for UNSAT is not COMPLETE:
   -> UNKNOWN/UNRESOLVED_MODEL

3. C=SAT and R_measurable_exists=TRUE and R_actual=FALSE:
   -> ACTUAL_POLICY_MISS

4. D=TRUE:
   -> DIRECT_QUALIFIED_PATH_EXISTS

5. C_before=UNSAT and authorized exact M0→M1 diff and C_after=SAT
   and T=INVARIANT and V=VALID:
   -> BOUNDED_MODEL_EXTENSION

6. C=SAT and N=NEW_TOKEN and E=SAME and T=INVARIANT and V=VALID:
   -> PREFIX_SAT_NEW_TOKEN

7. complete closed C=UNSAT with physical=FALSE and measurable=FALSE:
   -> BOUNDED_UNREACHABLE

8. otherwise:
   -> INVALID or UNKNOWN, with explicit failed gate
```

优先级不可由 arm 名、world ID 或 worker 的自报 category 改变。worker 可以提交 category
proposal，但 scorer 必须从原子 receipts 重算并保存 disagreement。

formation witness 只能读取：public episode、自己的 legal observations/actions、holder
返回、target readback 和自己的 receipt chain。它不能读取 private oracle、closure witness、
其他 worker transcript、expected outcome 或 scorer-derived coordinates。

## 6. Causal removal：frozen trace + reset semantics

causal removal 不是把 expected label 改成 `UNSAT`，也不是在成功 state 上删一个布尔值。
必须实际执行以下两类 replay：

### 6.1 Trace-dependence replay

1. 在 actual run 前预注册 eligible operator set、subset enumeration bound 和
   remove/reverse/block 规则。
2. 保存 successful actual transcript 的 raw bytes、每步 pre/post state hash、observation、
   response、receipt 和 target readback。
3. 从 exact `S0` clone 重启；冻结相同 exogenous response tape、policy versions、budgets、
   horizon 和 verifier。
4. 禁用指定 operator，并按预冻结 derived-effect graph 删除它产生的 token、permission、
   reservation、knowledge obligation 和 target-side descendant；独立外生事实保持不变。
5. 用同一个 actual policy 重新运行；不得把原成功 branch 或未来 observation注入。

这回答“该 actual trace 是否依赖 operator”。

### 6.2 Closure-dependence replay

在同一个 reset world 上，由独立 measurable-policy oracle 对移除后的 executable model
重新 model-check；oracle 可读 private transition truth，但结果不能回流 actual worker。
这回答“删掉 operator 后是否仍存在另一条合法 policy”。

冗余原因必须枚举预注册边界内的 minimal sufficient sets，不能要求每个步骤单独必要，也不能
在看到成功后挑 treatment。`remove/reverse/block` 至少返回：

```text
actual_policy_result
closure_result
changed_state_paths
cleared_derived_effects
preserved_exogenous_hash
reset_S0_hash
transcript_hash
```

若 reset hash、exogenous hash 或 response-family hash 变化，counterfactual 无效而非
`UNSAT`。

## 7. 击穿 post-treatment oracle 的测试

以下测试是进入评分前的硬门：

1. **Expected-label flip**：只篡改测试辅助文件中的 expected category，scorer 输出必须不变；
   最好生产 scorer 根本不加载该字段。
2. **World-ID/arm-name permutation**：互换 world ID、arm label 和文件顺序，原子坐标与类别
   不变。
3. **Same transcript, different hidden truth**：在合法 query 前，两个公开 packet 和 transcript
   相同而 hidden willingness 不同；actual worker 输出必须相同。只有收到合法 holder response
   后才允许分叉。
4. **Realized-branch preinjection**：把最终 holder response 放入 initial observation，runner
   必须拒绝或标记 leakage。
5. **After-the-fact response shrink**：实际运行后把 `F0` 缩为 realized branch，hash gate
   必须失败；robust 坐标不得提高。
6. **Hindsight plan injection**：把 physical/measurable oracle witness 交给 actual worker，
   isolation test 必须发现；W4 不得因此变成成功。
7. **Post-hoc operator selection**：witness 提交未预注册 operator ID 或成功后扩展 token
   equivalence class，counterfactual 必须无效。
8. **Delete-token-keep-descendants**：删除 token 但保留由它产生的 permission/reservation/
   learned obligation/target state，必须被 derived-effect consistency gate 击穿。
9. **Over-delete exogenous state**：remove 时连独立外生可用性或 owner policy 一并清除，
   `preserved_exogenous_hash` 必须失败。
10. **Knowledge residue**：reset 后保留只由已删除 operator 获得的 hidden fact，但删除其
    provenance、purpose、retention 或 cost，必须 invalid。
11. **No actual replay**：若 counterfactual 只有枚举值或 expected label，没有第二份真实
    transcript、pre/post hashes 与 model-check receipt，测试必须失败。
12. **C/N collapse mutation**：把 W3 的 `C` 从 SAT 改为 UNSAT 或把 `N` 改为 NONE，分类器
    必须拒绝不一致 receipt。
13. **Actual-miss laundering**：W4 的 `R_measurable_exists=TRUE/R_actual=FALSE` 若被标
    bounded unreachable，必须失败。
14. **Open-inventory laundering**：W5 已知 frontier 穷尽但任一 required inventory
    incomplete 时，任何 UNSAT certificate 必须失败。
15. **Task-diff laundering**：通用 owner receipt 没有逐字段绑定，或只改 hash 不保存
    ordered before/after diff，W6a 必须失败；controller receipt 不得替代 owner receipt。
16. **Always-Unknown policy**：W1/W2/W3 的 liveness-positive worlds 必须击穿永远 abstain 的
    worker；正确 Unknown 只在 W5 得分。

## 8. Baseline 公平性与停止判断

至少运行：

- equal-envelope center：同 observation API、独立 holders、response family、budget、
  horizon、human service 和 verifier；中心不能代替 Principal；
- legitimately-centralized environment：另一个 Authority/状态确实合法集中的环境，作为
  成熟方案足够的构造反例，不与 distributed world 混算算法优势；
- mature planner/workflow/IAM composition；
- bounded human rule baseline；
- candidate。

所有 baseline 必须提交同一 receipt body，不能只把组件能力相加。额外 connector、实时政策
访问、人工自由度、询问、披露、等待和治理负担全部入账。

若 center、成熟组合或人工规则在同一 envelope 下通过 6-world 全部门，candidate 没有独有
成功或只增加成本，应停止 formation-specific planner 创新，并登记“当前有界问题由现有组合
解决”。只有同一个 residual 在 equal-envelope baseline、两个异质任务族和 fresh holdout 中
稳定复现，才值得提出新机制。

## 9. 与当前合同的关系与证据边界

- 本文保留 X1 v1 的 `C/N/E/T/V`、六个 `R`、inventory、counterfactual、exact task diff；
- `W4` 必须走 `ACTUAL_POLICY_MISS`，不能走 `BOUNDED_UNREACHABLE`；
- `W6a/W6b` 分别走 `AUTHORIZED_NEW_EPISODE` 与 `INVALID_SUBSTITUTION`；
- `W3` 是对“NEW_TOKEN 必然代表旧 closure UNSAT”的最小反例；
- 6-world 通过只证明本地有限合成判别器能稳定区分这些量词，不证明真人、生产、跨域一般性、
  PFE/A2A 独特性或新协议必要性；
- 当前 LineContract 中“`S0` 无合格路径”必须解释为冻结 **full-policy closure** 无解时才支持
  bounded model-reach formation；若只是 `D=FALSE/C=SAT`，最多支持现实 token 新产生，
  不能支持旧 closure 从不可达变可达。
