# Cohort 003 G3 最终返回

日期：2026-07-30  
状态：`LOCAL SYNTHETIC COMPONENT MODEL COMPLETE / ROBUST UNKNOWN / REAL PRODUCTS NOT RUN / NO FORMAL STATUS CHANGE`

## 结论

本轮构建并实际运行了 CE-001 的单一 G3 formation/reachability module。它不是五臂比较，
没有 `_common_candidate` 或 `choose(packet)`，也没有把 operator proposal、semantic case
ID、expected label 或 private owner truth放进 public packet。

当前最窄可支持结果是：

```text
DIRECT / OLD FULL-POLICY / NEW TOKEN / MODEL-KERNEL / TASK CHANGE
  = LOCALLY DISTINGUISHED

E2 OWNER PROPOSAL + PURPOSE TOKEN + DELEGATION
  = POSITIVE LOCAL SYNTHETIC

E2 EXACT-S0 REMOVE / REVERSE
  = POSITIVE LOCAL SYNTHETIC

E4 POST-REVOKE REDISCOVERY + RECOVERY-TO-VALUE
  = POSITIVE LOCAL SYNTHETIC FOR FROZEN O_Q/O_V TASK

OPEN INVENTORY
  = UNKNOWN PRESERVED

EFFECT / SAFE / TERMINAL ROBUST
  = UNKNOWN — COMPLETE RESPONSE TREE NOT RUN
```

这不支持真实平台、成熟产品、真人 Principal、法律 Authority、现实供电 Effect、完整
CE-001 episode 或任何方法优越性结论。

## 实际结果

模块运行产生 11 个 receipt、16 条 raw run。十个 baseline/control 与一个 controller
task-substitution mutation 的主要向量如下：

| case | path class | `C / N / E / T / V` | actual | resolution | recovery |
|---|---|---|---|---:|---:|
| E0 | direct path | `SAT / NONE / SAME / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| E1 | old full-policy closure | `SAT / EXTANT_ACTIVATED / SAME / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| E2 | old-policy new token | `SAT / NEW_TOKEN / SAME / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| E3A | old full-policy closure | `SAT / NONE / SAME / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| E3B | old full-policy closure | `SAT / NONE / SAME / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| E4 | old-policy new token | `SAT / NEW_TOKEN / SAME / INVARIANT / VALID` | TRUE | TRUE | TRUE |
| E5 | bounded unreachable control | `UNSAT / NONE / SAME / INVARIANT / VALID` | FALSE | TRUE | FALSE |
| E6 | old full-policy closure | `SAT / NONE / SAME / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| open control | open-inventory Unknown | `UNKNOWN / UNKNOWN / SAME / INVARIANT / VALID` | FALSE | TRUE | FALSE |
| kernel control | model/kernel change | `UNSAT / NEW_TOKEN / CHANGED / INVARIANT / VALID` | TRUE | TRUE | FALSE |
| controller mutation | task change | `SAT / UNKNOWN / SAME / CONTROLLER_SUBSTITUTION / INVALID` | FALSE | FALSE | FALSE |

每个结果都返回：

```text
C / N / E / T / V
R_physical_exists
R_measurable_exists
R_actual
R_effect_robust
R_safe_robust
R_terminal_robust
```

三个 robust 坐标在 11/11 结果中均为 `UNKNOWN`。receipt 明确记录：

```text
robust_denominator.status =
  UNKNOWN_UNFROZEN_COMPLETE_RESPONSE_TREE
allowed_branch_population = null
counterfactuals_are_not_robust_denominator = true
```

因此本轮没有拿单条 actual trace 或 E2 intervention 冒充全分支 robust。

## E2：形成与 exact-S0 重放

E2 public packet 只给出 opaque handle、Q、接口和当时可见 context。executor 在运行中生成
exact proposal，绑定：

- task hash、Q version 与 resource；
- purpose 与完整 scope；
- expiry、recipient、cost 与 nonce。

`OwnerService` 接收 proposal，O_V receipt 绑定 proposal hash 与 current owner-policy head；
scorer 再核对 signer Authority、resource、Q、scope、expiry、head、receipt hash，以及
purpose token/delegation 的 exact binding。基线得到：

```text
C=SAT
N=NEW_TOKEN
E=SAME
T=INVARIANT
V=VALID
```

这保留了关键区分：具体 token/delegation 在 episode 内首次形成，但
`request → sign → reserve → execute` 已属于旧 full policy，所以旧 closure 仍是 SAT；
新 token 不等于新 kernel。

五个预注册 intervention 均从相同 frozen S0 credential 重放：

```text
REMOVE_FORMATION_OPERATOR
REVERSE_OWNER_DECISION@read
REVERSE_OWNER_DECISION@sign
REVERSE_OWNER_DECISION@reserve
REVERSE_OWNER_DECISION@execute
```

5/5 的 `exact_s0_replay=true`，5/5 未取得 exact value。S0 credential 同时绑定 owner
policy heads、scripted response snapshot、budget、horizon、clock seed 与 public bytes。
REMOVE 通过独立 intervention delta 真正从 executable kernel 删除
`REQUEST_PURPOSE_DELEGATION`，执行器没有再调用 sign；它不是改写 owner answer。

wrong scope、controller signer、stale head、receipt tamper、proposal tamper 与 owner-policy
transplant 均被 mutation tests 拒绝。

## E4：撤销后的 recovery-to-value

E4 的 initial read 只返回 primary resource。primary reservation 被 O_R 撤销后，executor
才发出独立 rediscovery query；alternative 仅在该 response 中出现，不是 public packet 或
pre-revoke 列表里的预选赢家。

随后实际 trace：

```text
primary revoke
→ post-revoke rediscovery
→ alternative-specific proposal
→ O_V purpose token/delegation
→ alternative reserve/execute
→ target-native readback
→ O_Q/O_V exact Acceptance
→ recovery-to-value
```

value checker 验证 Venue V / Circuit C7、Q version、`3kW ±5%`、不少于 45 分钟、
`T0+90min`、noise/safety/exact-target/no-other-circuit、resource/operation submit-readback
binding、readback hash，以及 O_Q/O_V 对 exact task/effect/operation 的 Acceptance。

deadline、wrong operation 与 Acceptance refusal mutation 均使
`exact_task_success=false / recovery_to_value=false`。因此当前 E4 的 TRUE 不再由
“曾经 revoke + 任意 Effect”触发。

## Open inventory 与 task change

open control 即使声明已耗尽 bounded frontier，仍返回：

```text
C=UNKNOWN
R_physical_exists=UNKNOWN
R_measurable_exists=UNKNOWN
R_effect_robust=UNKNOWN
R_safe_robust=UNKNOWN
R_terminal_robust=UNKNOWN
```

controller 把 C7 改成 C8 的 mutation 返回
`T=CONTROLLER_SUBSTITUTION / V=INVALID / exact_task_success=false`，没有把目标偷换包装成
formation success。

## 信息与实现边界

- public cases 使用 `H001`–`H010` opaque handles；semantic join 只在 private manifest；
- executor 不读取 scorer label、physical/measurable truth 或未来 owner decision；
- owner service 产生 proposal-bound receipt、撤销、readback 与 Acceptance；
- scorer 在 actual transcript 冻结后读取 private transition truth；
- raw producer event 使用中性的 `EFFECT_READBACK_OBSERVED`，exactness 只由 scorer 判定；
- 本轮只实现一个 line executor，未虚构 A0–A5 方法比较；
- `product_run_status=NOT_RUN`。

## 实际内部 Agent

### A `/root/g3_problem_reconstruction`

在未读取 B 实现的前提下独立重建 G3/CE-001 接口，产物为
`g3-formation/internal/A-problem-reconstruction.md`。它明确了 direct path 与 old closure
不可合并、`C=SAT + N=NEW_TOKEN + E=SAME` 可以同时成立、E2 两层 exact-S0 重放、E4
recovery-to-value 和 open-inventory Unknown。

### B `/root/g3_minimal_module`

实现 public/private fixture、owner/execution/scorer/runner、raw traces、outputs、tests、
README 与 failure history。B 的首轮绿灯经过根会话与 C 攻击后两次修订，没有把早期结果
覆盖掉。

### C `/root/g3_adversarial_audit`

先在不知道实现赢家的阶段形成 truth-copy、alias、task substitution、exact-S0、E4 与 robust
攻击清单；随后对实现做只读 mutation。第二轮在 14/14 绿灯后发现 10 个红信号、四个 P0；
B 修复后第三轮重跑 14 项 mutation，确认四个 P0 全部关闭。原始红灯与 post-fix recheck
共同保存在 `g3-formation/internal/C-adversarial-audit.md`。

A/B/C 均属于同一 Codex CLI、同一模型家族与同一仓库环境。职责分离增加了失败路径，不构成
外部实验室、真实主体或独立生产实现证据。

## 测试与 evidence hashes

主会话实际执行：

```text
PYTHONPYCACHEPREFIX=/tmp/ce001-g3-root-final-pycache \
  python3 -m py_compile run.py formation/*.py tests/*.py

PYTHONDONTWRITEBYTECODE=1 \
  python3 run.py > /tmp/ce001-g3-root-final-report.json

PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s tests -v

git diff --check -- .
```

结果：

```text
py_compile        PASS
unittest          18/18 PASS
JSON parse        3/3 files PASS
git diff --check  PASS
receipts          11
raw runs          16
```

Evidence:

```text
report body sha256
  5e11275aeda0d201c8a421bd83acefff97b58233971ffa5bdef5b3f7321d1232

traces.jsonl sha256
  07cf64631913297ec091ddeb041c4b0358831925480ad5478c4b8f63a86cdcb6

public_cases.json sha256
  7e2bf4a4a78254da2a7b1f65fc5fde3940e325265d16eb93f576a559d3b521a1

owner_truth.json sha256
  077bc21684914f19c4be44cad4f3ef2b2ba9b72a33f332cb75cd79ca5da522ee
```

## 红灯历史

保留的修订轨迹：

1. cohort 002 的五臂共享 `choose(packet)`，同分属于 alias-by-construction；
2. 第一版 `13/13` 将 robust 压成单值，并从 actual Effect 反推 measurable；
3. 第二版 `14/14` 输出复核发现 `R_physical_exists=null`；
4. C 在修复后的 `14/14` 再发现 E2 无 exact proposal、S0 未绑定 owner policy、E4
   recovery false positive、robust 无 denominator 四个 P0；
5. 最终版 `18/18` 与 C 的 14 项 post-fix mutation 关闭四个 P0。

测试绿灯只支持其覆盖范围；旧红灯没有因最终通过而删除。

## 能支持与不能支持

本轮支持：

- 当前本地合成 fixture 能区分 direct path、old full-policy closure、new token、
  model/kernel change 与 controller task substitution；
- E2 的 proposal-bound owner token/delegation 在 exact-S0 remove/reverse 下具有当前
  fixture 内的因果区分；
- E4 在当前 O_Q/O_V 冻结任务中完成 post-revoke rediscovery 与 recovery-to-value；
- open inventory 保持 Unknown；
- public packet 未预解 operator，单 line module 未共享多臂 decision root。

本轮不能支持：

- full response-family 的 effect/safe/terminal robust；三个坐标均为诚实 `UNKNOWN`；
- `R_physical_exists / R_measurable_exists` 是独立 oracle/model-check witness；当前仍是
  scorer-side local fixture truth/scan；
- 通用 task-defined Acceptance owner set；当前 CE-001 固定核对 O_Q/O_V；
- 真实产品、真人 owner、现实 Authority、现实供电、Acceptance、Settlement 或成本净值；
- A0–A5 方法比较、candidate-exclusive success、现有技术完整解或新机制必要性；
- 完整 G1–G7 CE-001 episode；
- 任何 Problem、LineContract、MechanismProfile 或正式 claim 状态变化。

## 下一接口

若继续 G3，下一项高价值工作不是扩大同源 case，而是：

1. 冻结完整 allowed response family 与 observation kernel，交由不同实现构造
   history-measurable policy/tree witness；只有遍历人口与 coverage proof 完整后，才把三个
   robust 从 `UNKNOWN` 升级；
2. 把 physical/measurable 从 fixture label/scan 改为可重放 sequence 与 contingent-policy
   witness，并由独立 checker 交叉复算；
3. 让 Acceptance owner set 直接由冻结 task 驱动，再做 owner-set mutation；
4. 把这个 line module 接入同一个 CE-001 root episode 的真实独立 A0–A5 executor，而不是
   在 G3 内重新制造共享 decision root。

本轮未修改 `research/NOW.md`、`PROGRAM.md`、CE-001 contract、Problem、LineContract 或任何
机制状态。
