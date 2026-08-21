# Wave 009 Unit C — QHM-2 principal policy and privacy design

日期：2026-07-29  
状态：`ROOT INDEPENDENT DESIGN / NOT IMPLEMENTED`

## 新变量

QHM-1 的逐 world existential sequence 不能回答四件事：

1. 同一初始 observation 下，策略是否会根据后续 observation 正确分支；
2. Principal 的 response 是固定但未知、被 probe 发现，还是互动后才由 Principal 形成；
3. 有合法拒绝权时，“无法保证所有分支都产生 Effect”是否被错误写成方法失败；
4. 敏感信息只有在 purpose-limited commitment 后才能披露时，系统如何避免把信息免费注入
   planner，或陷入“先披露才愿承诺、先承诺才可披露”的循环。

QHM-2 不再用一个 `reachable=true/false`。每个 scenario 同时输出：

| 坐标 | 量词 | 含义 |
|---|---|---|
| `R_exists` | \(\exists\) allowed response trace, \(\exists\) policy | 是否至少存在一个合法成功分支 |
| `R_actual` | frozen policy 在实际 realization 上 | 不看答案的 planner 是否完成或正确停止 |
| `R_effect_robust` | \(\exists\) policy, \(\forall\) allowed response trace | 是否所有合法 response 都产生原 Q Effect |
| `R_safe_robust` | \(\exists\) policy, \(\forall\) allowed response trace | 是否所有分支都无越权、无非法披露，并进入 Q、Refuse、Defer 或 bounded Unknown |
| `R_terminal_robust` | 同上 | 是否所有分支在 horizon 内停止，不靠无限追问 |

`R_effect_robust=false` 与 `R_safe_robust=true` 可以同时成立。Principal 有合法拒绝权时，这往往
是正确结果，不是协议失败。

这些量词与 QHM-1 的 `C/N/E/T/V` 并列，不互相替代。

## Principal-owned policy state

Principal service 持有版本化状态，controller 只能 request：

- `FIXED_HIDDEN`：response policy 在 S0 已存在，只是 controller 不知道；probe 后变化属于
  discovery，不是 preference formation；
- `DECLARED_CONDITIONAL`：threshold/countercondition 已声明；执行承诺前缀属于旧 policy；
- `UNFORMED_DELIBERATIVE`：S0 没有本次 stance，Principal 在看到合法 proposal/counter 后
  自己签发 `PolicyVersion@v1 = ACCEPT_BOUND / REFUSE / DEFER`；
- `REVISED`：Principal 明确把旧 policy version 改为新 version，并给出 supersedes、
  provenance 和适用范围。

只有 Principal service 能生成 policy-version receipt。Controller 观察到 response 改变，
不能据此自称“形成了人的偏好”。合成实验最多支持 synthetic Principal-policy transition。

## Purpose-limited disclosure state

敏感 observation 必须引用：

- data Principal；
- recipient；
- purpose；
- data projection；
- retention；
- onward-use；
- revocation；
- expiry；
- privacy cost 与 disclosure receipt。

Commitment type 在 action model 中存在，不等于某次 purpose token 已存在。可允许的现有组合
包括 consent/contract workflow、最小 public metadata、PSI/ZK predicate、TEE/code-to-data、
neutral human/broker 和 ordinary signed approval。它们完整解决时就是正向答案。

## Paired worlds

### A. Observation-contingent policy

两个 worlds 的初始 observation 完全相同：

- `OBS-A`：probe 后发现 alternate route，可直接 L0 execution；
- `OBS-B`：probe 后发现 schema blocked，需 known adapter；
- `OBS-C`：probe 被 Principal 合法拒绝，应安全停止；
- `OBS-D`：probe 返回 stale version，必须重查而不能沿旧 route。

固定 action sequence 至少在一个分支失败；同一 history→action policy 必须在四分支分别
discover、prepare、refuse 和 refresh。Runner 不得为每个 truth world 单独调用 omniscient BFS。

### B. Principal policy

- `PP-FIXED-HIDDEN`：S0 已有固定拒绝条件，probe 只发现它；
- `PP-DECLARED`：公开 countercondition 满足后自动签发；
- `PP-DELIBERATE-ACCEPT`：S0 stance 未形成，proposal 后 Principal 签发 bounded acceptance；
- `PP-DELIBERATE-REFUSE`：同前态与同合法 proposal，Principal 有权签发 refusal；
- `PP-REVISE`：已有 stance 被 Principal 自己版本化修改；
- `PP-CONTROLLER-SUBSTITUTE`：controller 回填一个“Principal 已同意”的 label，必须失败。

`PP-DELIBERATE-ACCEPT/REFUSE` 共享 S0、公开 observation 与 response family；不能把 realized
answer 事后写回 planner 输入。

### C. Privacy bootstrap

- `PB-TOKEN-EXISTS`：purpose token 已存在，披露是 ordinary old-model action；
- `PB-PUBLIC-BOOTSTRAP`：只用非敏感 metadata 可请求并形成 token，随后 scoped disclosure；
- `PB-CIRCULAR-UNSAT`：接收方必须先看敏感事实才肯承诺，数据方无 token 就拒绝披露；在冻结
  action set 内 bounded UNSAT；
- `PB-PRIVATE-PREDICATE`：PSI/ZK/TEE 只返回必要 predicate，现有组合打破循环；
- `PB-VALID-REFUSAL`：数据 Principal 拒绝任何披露，安全停止；
- `PB-FREE-INJECTION`：planner 获得敏感 fact，但没有 recipient/purpose/cost/obligation，
  必须 invalid。

## 公平基线

所有方法使用同一 observation API、response family、Authority endpoint、privacy budget、
human service、L2 channel、horizon 和 evaluator：

1. strong center + distributed Principal holders + HITL；
2. deterministic workflow + consent/contract steps；
3. POMDP/contingent-policy planner；
4. privacy composition：minimization + purpose token + PSI/ZK/TEE/code-to-data；
5. formation candidate。

不得给 candidate 更多 response branches、更多 private facts或更宽 human creativity。强中心
若完整覆盖，结果为正向解决；candidate 独有成功为 0 时不制造创新需求。

## 可执行 evaluator

冻结包必须绑定：

- `S0/Q/V0`、observation kernel、response family、policy-version transition；
- action/meta-action、privacy and human budgets；
- executable transition、qualified predicate、refusal terminal、checker version；
- parent-owned observation、policy decision、effect、cost 与 target anchors。

Runner 分三次运行：

1. `EXISTENTIAL ORACLE`：只作 declared finite model 的可解性参照；
2. `ACTUAL POLICY`：planner 不知道 realized branch，只通过 observation 行动；
3. `ROBUST TREE CHECK`：穷举所有 declared response branches，分别计算 effect/safe/terminal。

成功与正确停止都必须重放：

- after-the-fact response-family shrink；
- response label flip；
- policy-version controller substitution；
- disclosure receipt deletion；
- purpose/recipient/retention mutation；
- privacy cost deletion；
- learned fact 保留但合法来源/义务删除；
- valid refusal 被错误记为 solver failure；
- infinite clarification loop；
- exact S0 reset 后删除新 policy/token 并重新规划。

## 最强反例

1. 若把 realized Principal answer 写入 world truth，再逐 world 求路径，`R_actual` 只是 hindsight。
2. 若 robust 只承认 Effect，任何有拒绝权的 Principal 都让系统看似失败；必须另报 safe robust。
3. 若把 `ask_human` 当成总会给出可用答案的旧 action，existential closure 会空泛化。
4. 若 response family 在运行后缩到实际分支，任何策略都可伪造 robust。
5. 若披露内容可免费保留而 provenance/义务被删除，privacy bootstrap 的因果判断无效。
6. 若 controller 能签 PolicyVersion，互动形成与冒权无法区分。

## 当前最佳组合与残余

当前最强候选不是新协议，而是：

> strong center 或 contingent planner + distributed Principal policy holders +
> purpose-limited consent/contract workflow + minimization/PSI/ZK/TEE/code-to-data +
> parent-anchored verifier。

它很可能覆盖 QHM-2 的大部分 closed worlds。真正仍需检验的残余只有：

- 同 observation 下的多分支策略能否在相同成本内安全收敛；
- Principal policy version 是被发现还是在 episode 中由 Principal 形成；
- privacy circularity 在什么条件下由成熟组合打破，什么条件下应保持 bounded UNSAT；
- safe robust 是否能避免把合法拒绝误写成系统失败。

下一步应由另一 Agent 按本设计实现 QHM-2，再由第三个 Agent只拿冻结 spec 做独立策略或攻击。
