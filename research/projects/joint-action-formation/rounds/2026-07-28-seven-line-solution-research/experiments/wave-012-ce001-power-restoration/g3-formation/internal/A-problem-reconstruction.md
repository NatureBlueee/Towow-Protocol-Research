# G3 / CE-001 formation-reachability 原始问题重建

日期：2026-07-30  
角色：内部 Agent A `/root/g3_problem_reconstruction`  
状态：`PROBLEM / INTERFACE PROPOSAL ONLY — NO IMPLEMENTATION — NO RUN`

## 0. 证据边界

本重建先完整读取：

- 仓库根 `AGENTS.md`；
- cohort 003 `COMMON.md`；
- `CE-001-CONTRACT.md`；
- cohort 002 `ROOT-ADVERSARIAL-AUDIT.md`；
- cohort 002 `SYNTHESIS.md`。

为恢复 `C/N/E/T/V` 的既有展开，又只读参考了 cohort 001、002 的历史
`G3-final.md` 与 cohort 002 `G3-PROMPT.md`。没有读取或依赖 cohort 003 内部 Agent B
的实现或预期结果。

来源中存在一条必须显式保留的边界：CE-001 contract 要求形成与恢复，但没有在合同正文里
展开 `C/N/E/T/V`；其展开来自历史 G3 候选接口。因此下文把该向量作为本轮建议冻结的
line-interface，而不是声称 CE-001 contract 已经逐字段定义了它。

## 1. 原始问题

G3 不是问“有没有一串动作看起来能完成供电”，也不是问“这次是否出现了一份新 token”。
它要在冻结 episode 及合法信息边界后，分别回答：

1. `S0` 是否已经存在无需形成动作的 exact-Q direct path；
2. 冻结的旧 full policy（包括合法 search/query/request/sign/reserve 等 meta-action）
   是否能从 `S0` 闭合任务；
3. 运行中是否由相应 owner 新形成了 operative condition，例如 exact purpose token、
   短期 delegation、commitment 或 reservation；
4. 可执行 action/model/policy kernel 是否真的改变，而非只生成一个新实例 token，或只把
   同一过程换一种表示；
5. `Q@v1`、Circuit C7、必要 Principals、Authority、不可替代约束和 Acceptance 标准是否
   保持，还是形成了 owner-authorized new episode / controller substitution；
6. 全知物理可达、合法可测 policy 可达、某个实际 arm 的执行结果和跨冻结 response/failure
   family 的稳健性分别是什么；
7. 在 E2 删除形成 operator 或反转 owner decision 后，从同一个 exact `S0` 重放会发生什么；
8. E4 的首选资源撤销后，是否真的恢复到原任务价值，而不只是安全停止、找到候选或重新预订；
9. 当 action/meta-action/tool/partner/response/transition inventory 没有封闭时，能否诚实
   保持 `UNKNOWN`。

形式化地，先冻结：

```text
F = (
  episode_id,
  S0,
  Q@v1,
  exact target = Venue V / Circuit C7,
  necessary Principals and owner heads,
  Authority topology and stratum,
  action + meta-action model,
  observation model and owner API schemas,
  response/failure family,
  policy/model/kernel versions,
  budget, deadline, horizon,
  target/readback semantics,
  settlement and acceptance obligations
)
```

然后只允许实际 executor 使用合法 public observation history `h_t` 选择动作：

```text
a_t = pi_arm(h_t)
```

owner decision、Authority receipt、resource Effect、target readback 和 Acceptance 必须由
各自 owner/service 产生。executor 不能把 scorer truth、自拟签名或未来 receipt 当作输入。

## 2. 五种不能混淆的变化

### 2.1 Direct path

`direct_path=TRUE` 只表示在 `S0` 已有一条 qualified execution path：

- 所需资源、人员、Authority、token 和 target capability 已存在且 current；
- 不需要 search/query/request/sign/形成新 condition 或改 model/kernel；
- 路径完成的是 exact `Q@v1`，不是近似目标。

E0 应优先允许 platform-direct 成为这种正解。对 direct path 再强造 relation、第二事实源或
额外审批，不是 formation 增益。

建议把 direct path 作为独立三值字段返回：

```text
direct_path: TRUE | FALSE | UNKNOWN
```

不能用 `C=SAT` 代替它，因为 full-policy closure 可以通过后续 owner interaction 成功。

### 2.2 Old full-policy closure

`C` 检验的是冻结旧 executable model 下的完整 contingent policy closure，不只是 `S0`
立即可执行的动作，也不只是事后 realized branch。旧 policy 可以包含：

```text
search → query → proposal → owner counter/refuse/approve
       → exact token/delegation → reserve → execute → readback
```

因此以下结果完全一致：

```text
direct_path = FALSE
C = SAT
N = NEW_TOKEN
E = SAME
T = INVARIANT
V = VALID
```

这正是 E2 最重要的反例之一：purpose token 和 delegation 在 episode 内首次形成，但
`request/sign` 已经属于旧 policy；新 token 不能倒推出旧 closure `UNSAT`，也不能倒推出
需要新 planner。

### 2.3 New operative token

token 是 episode state 中的 exact owner act，不自动是 executable model 变化。它至少应绑定：

```text
token_id / token_type / issuer_owner_id / subject
Q_version / object_id / operation scope / constraints
issue event / owner head / expiry / revocation head
receipt hash / predecessor evidence
```

E2 至少要求实际形成：

- exact purpose token；
- 对 exact object/version/scope/expiry 的短期 delegation；
- 若资源执行需要，owner-specific commitment / reservation condition。

签名字节只证明 owner 对 exact bytes 有 act，不自动证明理解、current、Effect、Acceptance
或法律充分性。

### 2.4 Model/kernel change

只有冻结 executable semantics 真正发生获授权、可执行且可复算的 diff，才可记
`E=CHANGED`。以下都不足：

- 产生某个 token instance；
- 激活旧对象；
- 把 `request → sign` 重写成 `install(spec)` 或 `register_new_operator`；
- controller 在运行后把 observed transition 填回 model；
- 只有 proposal，没有 deployment Authority / executable install / version receipt。

建议除 `E` 外保留：

```text
executable_diff:
  kind: NONE | ACTION_MODEL | POLICY_KERNEL | INSTITUTION | ADAPTER | UNKNOWN
  old_hash
  new_hash
  authority_receipt
  installed_at
  executable_readback
```

只有在 complete/frozen old inventory 下 `C_old=UNSAT`，获授权 diff 后同一任务
`C_extended=SAT`，并且 `T=INVARIANT, V=VALID`，才能登记 bounded model reach gain。

### 2.5 Task change

task continuity 不能靠 `Q_version` 字符串相同判断。至少逐项比较：

- `3kW ± 5%`；
- 连续不少于 45 分钟；
- `T0 + 90min` deadline；
- Venue V / Circuit C7 exact target；
- 噪声、安全、不得给其他线路送电；
- necessary Principals、Authority envelope；
- requester 与 venue 对 exact Q 和实际 Effect 的 Acceptance；
- Settlement obligation。

owner 对 material diff 的正式授权形成新 episode，不是旧任务的 G3 success。controller
降低功率/时长、改送别的线路、删除 Acceptance 主体或扩大 Authority，是 substitution。

## 3. 建议冻结的 `C/N/E/T/V`

不得先压成一个 formation 标签或分数。建议返回结构化值与证据：

| 坐标 | 值 | 不可混淆语义 |
|---|---|---|
| `C` | `SAT / UNSAT / UNKNOWN` | 冻结旧 full-policy closure；`UNSAT` 只允许 complete/frozen/bounded inventory 的穷举证据 |
| `N` | `NONE / EXTANT_ACTIVATED / NEW_TOKEN / UNKNOWN` | operative condition；新 token 是 owner act，不是 model change |
| `E` | `SAME / CHANGED / UNKNOWN` | executable model/kernel/institution/adapter semantics 是否改变 |
| `T` | `INVARIANT / OWNER_AUTHORIZED_NEW_EPISODE / CONTROLLER_SUBSTITUTION / UNKNOWN` | exact task 及必要主体是否保持 |
| `V` | `VALID / INVALID / UNKNOWN` | trace、Authority、信息边界、counterfactual、exact-object/version 与 evidence binding 是否有效 |

E2 同时形成多个 token 时，`N=NEW_TOKEN` 只是摘要；必须另返
`operative_conditions[]`，不能丢掉 purpose、delegation、commitment 的不同 owner、scope
和 revoke head。

`V=VALID` 至少要求：

- actual executor 只消费当时合法可得的 public evidence；
- owner decision 与 receipt 来自对应 owner service；
- receipt 在使用点 current，且绑定 exact object/version/operation；
- task diff 与 executable diff 都有独立 hash 和 Authority；
- counterfactual 从 exact `S0` 重放，派生 Effect graph 被正确重置；
- target truth、Effect、Acceptance 不由 G3/controller 自填；
- 没有用最终 receipt、expected label 或 alternative identity 回灌 P0/P1。

`R_actual=FALSE` 不必导致 `V=INVALID`：合法 refusal、defer 或 bounded Unknown 可以是有效
trace。反之，偶然完成任务但使用 stale Authority、wrong object 或 oracle leakage，
`R_actual` 不能记作合格 success，且 `V=INVALID`。

## 4. physical / measurable / actual / robust

这些结果应使用 `TRUE / FALSE / UNKNOWN`，并附 witness/receipt，不用 Python truthiness
折叠 `UNKNOWN`。

```text
R_physical_exists
R_measurable_exists
R_actual
R_effect_robust
R_safe_robust
R_terminal_robust
```

### `R_physical_exists`

在允许全知 world truth 的诊断 oracle 下，是否存在物理上能完成 exact Q 的序列。它不受
executor 可见性限制，只用于区分“世界里没有路径”和“路径存在但系统无法合法知道/利用”。
它不能作为 actual executor 的输入。

### `R_measurable_exists`

是否存在一个只依赖合法 observation history、遵守同一 Authority/action/query/budget
envelope 的 policy。它必须面对冻结的 response family，不能只看 realized branch，也不能
把 ask-human 当零成本必答 oracle。

`R_physical_exists=TRUE` 与 `R_measurable_exists=FALSE/UNKNOWN` 可以同时成立。

### `R_actual`

实际 arm 的独立 executor 是否在本次 trace 中：

- 完成 exact Q；或
- 对 E5 等不可达 case 给出合同规定的 correct bounded resolution。

建议拆返 `actual_exact_task_success` 与 `actual_correct_resolution`，避免把安全拒绝算任务
success。若 measurable path 存在而实际 policy 漏掉，应分类 `ACTUAL_POLICY_MISS`，不是
`BOUNDED_UNREACHABLE`。

### 三种 robust

- `R_effect_robust`：在冻结的 admissible owner response / failure / revoke family 中，
  对所有仍可达分支，policy 是否恢复并取得 exact Effect；E5 合法拒绝时可以为 `FALSE`。
- `R_safe_robust`：所有分支是否都避免 unauthorized、wrong-object、duplicate、over-scope
  Effect；合法拒绝可以为 `TRUE`。
- `R_terminal_robust`：所有分支是否在 budget/horizon 内到达 exact success 或正确的
  bounded refusal/defer/Unknown，而不是死循环或悬空 Effect。

robust 分母必须在运行前冻结。运行后把 response family 缩成实际发生的 approve/revoke
分支，只能得到 realized-trace 结果，不能得到 robust 结论。

## 5. Inventory 完备性与 Unknown

建议逐维返回：

```text
inventory:
  action: CLOSED_FROZEN | OPEN | CONFLICT | UNKNOWN
  meta_action: ...
  observation: ...
  response_family: ...
  transition: ...
  tools_partners_institutions: ...
  authority_paths: ...
  bound_horizon: ...
  freeze_hashes: [...]
```

只有所有承重维度均 `CLOSED_FROZEN`、hash/version 绑定、bound/horizon 有限且 closure worker
穷举后，`C=UNSAT` 才可成立。只要任一维度 open/incomplete/conflict：

```text
C = UNKNOWN
```

“已搜索公开目录”“declared frontier exhausted”“actual arm 没找到”“owner 暂未回答”
都不构成 inventory complete。open inventory 下 actual arm 可以成功；但 actual 未成功时
不得据此宣称 bounded unreachable。物理或 measurable 的不存在也应保持 `UNKNOWN`，除非有
独立、更强的闭合证据。

## 6. E2：形成、remove/reverse 与 exact-S0 重放

### 6.1 E2 的初态与正向 trace

E2 的 `S0` 应明确：

- capability 存在；
- exact purpose token、短期 delegation 和所需合作条件尚不存在；
- owner 保留独立 approve/counter/refuse/defer/revoke；
- public packet 只给出合法 API/schema、Q 和当时可见 evidence；
- packet 不提供 expected operator、owner 的未来决定、预选 alternative 或 expected
  `C/N/E/T/V`。

一个合格正向 witness 形如：

```text
arm proposal/query
→ O_Q/O_V/O_R/O_S owner interaction
→ exact purpose token
→ exact short delegation
→ resource commitment/reservation
→ commit-time current check
→ target operation + O_E readback
→ requester/venue Acceptance
```

其中真正形成 token 的是 owner act，不是 arm 的 proposal 文本。

### 6.2 exact `S0`

每次 counterfactual 必须绑定同一个：

```text
S0_hash
Q_hash / Q_version
owner heads and policy versions
resource and target pre-state
old model/kernel hashes
inventory hashes
response/failure family
budget/horizon
exogenous schedule / deterministic seed
```

不得从成功后的 state 删除 token 再继续，也不得编辑 completed receipt、沿用已派生
reservation/Effect 或把 scorer 期待答案写进 replay。

### 6.3 两层重放

为了避免“删掉一步当然破坏固定 trace”的空洞因果证据，建议同时运行：

1. **frozen-trace ablation**：对同一冻结 action/receipt lineage 施加 intervention，从 exact
   `S0` 重放；检查被删除/反转 owner act 的所有 descendants 是否消失或失效。
2. **same-policy replay**：同一个 arm executable/policy 从 exact `S0` 重新运行，可以依
   新 observation 合法改道，但不得更换 task、权限、model 或预算；检查它是否存在替代闭合。

预注册干预至少覆盖：

```text
REMOVE_FORMATION_OPERATOR
REVERSE_OWNER_DECISION@read
REVERSE_OWNER_DECISION@sign
REVERSE_OWNER_DECISION@reserve
REVERSE_OWNER_DECISION@execute
```

每个 intervention 返回：

```text
intervention_id / target owner event hash
replay S0 hash / policy hash / task hash
trace-ablation result
same-policy replay result
descendant reset receipt
exact success / correct resolution / Unknown
```

E2 的 condition-formation 证据要求正向 token 真实形成，remove/reverse 后在原 Q、原 envelope
下实际 arm 失败或保持 Unknown；若 same-policy replay 找到另一条 exact-Q path，则只能说该
token 是原 trace 的 causal condition，不能说它对任务全局必要。若 intervention 后仍沿用
旧 reservation/Effect，就是 history rewrite / invalid replay。

## 7. E4：撤销后的 recovery-to-value

E4 不是“发现撤销并安全停止”。完整路径至少要求：

```text
primary reserve
→ O_R current revoke
→ invalidate affected reachability/commitment descendants
→ reopen discovery/formation nodes
→ legally discover an alternative
→ obtain alternative-specific purpose/delegation/commitment
→ re-reserve and commit-time Authority check
→ execute only on Circuit C7
→ O_E exact readback
→ requester + venue Acceptance
→ correct Settlement lineage
```

alternative 的身份、排序和完成动作不能作为解答预写入 public packet。public packet 可以
公开目录/query/action API 的语义与成本；各 executor 必须用自己的 state、queries 和
decision logic 发现并取得 alternative。

建议返回：

```text
recovery_to_value:
  status: TRUE | FALSE | UNKNOWN
  revoke_receipt
  affected_nodes_reopened
  missed_reopen_nodes
  over_reopen_nodes
  alternative_discovery_trace
  new_condition_receipts
  exact_task_success
  correct_resolution
  elapsed_from_revoke
  deadline_margin
  effect_readback
  acceptance_refs
  settlement_ref
  duplicate_or_wrong_effect
```

只有 exact `Q@v1` 在 deadline、duration、power、safety 和 target 约束下完成，并取得相应
readback/Acceptance，`RecoveryToValue=TRUE`。以下都必须为 `FALSE` 或在缺证时
`UNKNOWN`：

- 安全停止；
- “已找到备选”；
- 重新 reservation 但未 Effect；
- 给错误 circuit 供电；
- 降低功率/时长或删除 Acceptance；
- Effect 已发生但无法对账；
- 恢复超时而任务价值已经丢失。

G3 可以产生/检验 reachability 与 formation trace，但不能代替 `O_E`、requester、
venue 或 settlement owner 宣布最终真实结果。

## 8. 最小模块接口

### 8.1 Executor 可见输入

```text
PublicEpisodePacket:
  episode_id / case_id
  Q ref + exact bytes hash + Q_version
  public S0 observations
  Authority stratum
  owner/query/action API schemas
  target/readback API schema
  current public receipts
  budget/deadline/horizon
  arm_id and arm-specific envelope
```

明确禁止：

```text
expected category / expected C/N/E/T/V
private owner decisions or future heads
private inventory-completeness label
physical/measurable oracle witness
pre-solved operator proposal or action sequence
pre-ranked E4 alternative
intervention expected result
grader/private oracle truth
```

API schema 可以说明“可向 owner 提交 exact purpose proposal”；不能把“向哪个 owner、提交
什么 exact proposal、owner 会批准、下一步选谁”预解进 packet。

### 8.2 Arm 输出

每个 arm-specific executor 独立维护：

```text
policy/executor hash
private arm state
queries and action proposals
observations actually received
owner/target receipt refs
terminal claim and claimed witness
cost/disclosure/wait/human/tool trace
```

不得让五臂或 CE-001 全局 arms 调用同一个 `choose(packet)`、共享 `_common_candidate` 或
decision root 后仅换 arm 名。line module 不需要虚构一个五臂赢家比较；应暴露统一 I/O
contract，让 root episode 把独立 A0–A5 executor 接入。A6 只有在合同 residual gate 成立后
才可实例化。

共享 evaluator、owner API 和 target simulator 是允许的，但 evaluator 只能在 arm transcript
冻结后消费 private truth，owner/target 不得返回 expected label。

### 8.3 Evaluator 输出

```text
G3Result:
  episode_id / case_id / arm_id
  direct_path
  C / N / E / T / V
  operative_conditions[]
  executable_diff
  exact_task_diff
  inventory
  R_physical_exists
  R_measurable_exists
  R_actual
  R_effect_robust
  R_safe_robust
  R_terminal_robust
  actual_exact_task_success
  actual_correct_resolution
  formation_counterfactuals[]
  recovery_to_value
  failure_codes[]
  evidence_bindings
  evidence_scope
```

`evidence_bindings` 至少联合绑定 public packet、exact S0、actual transcript、owner receipts、
closure/measurable/robust workers、counterfactual replay、task/model diff 与 target readback。

## 9. 必须保留的反例与攻击

1. E0 direct path 已在 `S0`，executor 却强造 token/relation 并称 formation。
2. 旧 policy 已有 request/sign，故 `C=SAT`；token 新形成，故 `N=NEW_TOKEN`；把它误报
   `C=UNSAT` 或 `E=CHANGED`。
3. 同一物质过程改名为 `install(spec)` 后凭表示变化宣称新 kernel。
4. inventory open，却因搜索穷尽 declared frontier 输出 `UNSAT`。
5. `R_physical_exists=TRUE` 被偷当作 measurable/actual path。
6. measurable path 存在而 actual executor miss，被误报 bounded unreachable。
7. robust worker运行后缩掉 refuse/defer/stale/revoke 分支。
8. controller 自签 purpose token、delegation、PolicyVersion 或 owner Acceptance。
9. 把 Circuit C7 换成其他线路，或降低功率/时长/Acceptance 后继续沿用旧 success。
10. owner 正式批准 material task diff，却被错误算作原任务 G3 success。
11. remove/reverse 直接篡改成功后 state，没有从 exact `S0` 重放，也未清除 descendants。
12. frozen trace 删除一步失败，就未经 same-policy replay 宣称该 operator 全局必要。
13. E4 只安全停止、找到 alternative 或重新预订，就记 recovery-to-value。
14. E4 alternative / operator proposal 已在 public packet 中预选，实际 executor 只照抄。
15. 五臂共享 `choose(packet)`，再用同分/candidate-exclusive zero 宣称方法等价。
16. owner truth、expected vector 或 scorer receipt 被复制进 public method witness。
17. signature bytes 被当成 understanding、current Authority、Effect 和 Acceptance 的合并证明。
18. wrong-object 或 duplicate Effect 最终被正确终态覆盖，仍记作无损恢复。

## 10. 结果分类建议

向量优先于单类；若需要人类可读摘要，可从证据派生：

| 摘要 | 必要条件 |
|---|---|
| `PREEXISTING_DIRECT_PATH` | `direct_path=TRUE, C=SAT, N=NONE, E=SAME, T=INVARIANT, V=VALID` |
| `OLD_POLICY_DISCOVERY_OR_ACTIVATION` | `direct_path=FALSE, C=SAT, N=NONE/EXTANT_ACTIVATED, E=SAME` |
| `OLD_POLICY_CONDITION_FORMATION` | `C=SAT, N=NEW_TOKEN, E=SAME, T=INVARIANT, V=VALID` |
| `AUTHORIZED_MODEL_REACH_GAIN` | `C_old=UNSAT, C_extended=SAT, E=CHANGED, T=INVARIANT, V=VALID` |
| `ACTUAL_POLICY_MISS` | `R_measurable_exists=TRUE` 且实际 executor 未给出合格 success/resolution |
| `BOUNDED_UNREACHABLE` | complete/frozen inventory 下 `C=UNSAT`，无 task substitution |
| `UNKNOWN_OPEN_INVENTORY` | 任一承重 inventory 维度 open/conflict/unknown，`C=UNKNOWN` |
| `AUTHORIZED_NEW_EPISODE` | material task diff 由对应 owner 授权；不计原 Q success |
| `INVALID_SUBSTITUTION` | controller/无权主体改变 material task 或 Authority |
| `INVALID_TRACE` | oracle leak、stale Authority、wrong object、history rewrite 或 evidence binding 失败 |

这些摘要不得用 precedence 丢掉原向量。例如 `AUTHORIZED_NEW_EPISODE` 仍应保留其物理/可测
结果，但它对旧 `Q@v1` 的 `ExactTaskSuccess` 必须为 false。

## 11. 本文不能支持的结论

本文没有实现或运行模块，因此不能支持：

- 任一平台、强中心、成熟组合、通用模型、人工制度或 candidate 已解决 CE-001；
- E2 token/delegation 已实际形成；
- E4 已实际 recovery-to-value；
- 任一 arm 的 success、coverage、成本或 robust 数字；
- 真实成熟产品、真人 owner、现实 Authority、现实供电 Effect、Acceptance 或 Settlement；
- 五臂/七臂经验等价或某一臂获胜；
- open inventory 在现实中必定不可达；
- 新机制必要或不必要；
- full G1–G7 episode 已运行；
- 任何 Problem、LineContract、MechanismProfile 或正式 claim 状态改变。

当前能支持的最窄结论是：上述接口能把 CE-001 G3 最容易混淆的 direct path、old closure、
new token、model/kernel change、task change，以及 physical/measurable/actual/robust、
exact-S0 counterfactual 和 recovery-to-value 分开；它为 B 的实现和 C 的攻击提供了可检查
边界，但不是运行结果。
