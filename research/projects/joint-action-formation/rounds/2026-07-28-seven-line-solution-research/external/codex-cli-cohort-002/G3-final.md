# 第二批 Codex CLI G3 最终返回

日期：2026-07-29  
状态：`LOCAL SYNTHETIC QUANTIFIER DISCRIMINATOR COMPLETE / NO FORMAL STATUS CHANGE`

## 结论

本轮没有得到“需要新造 formation-specific planner”的证据。

6-world 鉴别器实际运行了 5 个 arm：

- equal-envelope center；
- legitimately-centralized environment envelope；
- mature planner/workflow rule；
- bounded human institutional rule；
- formation candidate。

共生成 `6 × 5 = 30` 个结果。五个 arm 在每个 public world 上选择的动作序列完全相同，
candidate 独有成功为 `0`。在这个有限合成分母内，成熟 planning/workflow、center 和有界
人工制度规则已经与 candidate 等效；这是“不需要为当前分母增加新 planner”的正向结果。

这个结果不证明真实成熟产品、真人制度或跨组织 full-stack 已经解决 G3。当前 baseline 是同一
可执行合成规则的不同 envelope，不是四个独立生产系统；legal-control 是条件化构造反例，
human 是规则模拟，不是真人实验。

## 最重要的量词修订

G3 不能只问“`S0` 有没有立即执行路径”。必须至少分开：

```text
C  old full-policy closure: SAT / UNSAT / UNKNOWN
N  operative condition: NONE / EXTANT_ACTIVATED / NEW_TOKEN / UNKNOWN
E  executable model/kernel: SAME / CHANGED / UNKNOWN
T  task: INVARIANT / OWNER_AUTHORIZED_NEW_EPISODE /
   CONTROLLER_SUBSTITUTION / UNKNOWN
V  trace/Authority/counterfactual validity
```

并同时返回：

```text
R_physical_exists
R_measurable_exists
R_actual
R_effect_robust
R_safe_robust
R_terminal_robust
```

本轮最承重的反例是：

```text
C=SAT, N=NEW_TOKEN, E=SAME, T=INVARIANT, V=VALID
```

旧 model 已经包含 `request → holder_sign → execute`，所以 full-policy closure 从 `S0`
就是 SAT；具体 purpose token 在 episode 内才由 holder 新签发，所以同时
`N=NEW_TOKEN`。现实 token 的首次形成不能倒推出旧规划闭包 UNSAT，更不能倒推出需要新
planner。

只有当 old action/meta-action、response、observation、transition inventory 全部 complete，
bound/horizon 冻结，old closure 穷举为 UNSAT，且精确、获授权的 executable model diff 后
同一任务变 SAT，才能登记有界 `UNSAT→SAT`。

## 六个 world 的实际结果

| world | 五个 arm 的共同类别 | `C/N/E/T/V` |
|---|---|---|
| `E01` | `PREEXISTING_QUALIFIED_PATH` | `SAT / NONE / SAME / INVARIANT / VALID` |
| `E02` | `QUALIFIED_CONDITION_FORMATION` | `UNSAT / NEW_TOKEN / CHANGED / INVARIANT / VALID` |
| `E03` | `PREFIX_SAT_NEW_TOKEN` | `SAT / NEW_TOKEN / SAME / INVARIANT / VALID` |
| `E04` | `ACTUAL_POLICY_MISS` | `SAT / NONE / SAME / INVARIANT / INVALID` |
| `E05` | `UNKNOWN` | `UNKNOWN / NONE / SAME / INVARIANT / VALID` |
| `E06` | `AUTHORIZED_NEW_EPISODE` | `UNSAT / NONE / SAME / OWNER_AUTHORIZED_NEW_EPISODE / VALID` |

具体区分：

1. E01 在 `S0` 已有 direct qualified path，不是 formation。
2. E02 保存 old closure `UNSAT` 和 authorized extension 后 `SAT` 两个独立结果；remove、
   reverse、block 均从 frozen `S0` 重放为 `UNSAT`。
3. E03 的旧 policy 已经含 request/sign；新 token 与 prefix closure SAT 同时成立。
4. E04 的 independent measurable worker 找到 SAT path，但 actual policy 信任 stale cache
   并直接执行，故是 actual-policy miss，不是 bounded unreachable。
5. E05 的 tool、partner、task-representation inventory 未封闭；即使 declared frontier
   exhausted，closure 仍只能 UNKNOWN。测试另构 complete/frozen 正控，才允许
   `BOUNDED_UNREACHABLE`。
6. E06 主运行由 owner 批准 exact `Q/V0` diff，故生成新 Episode，不是原 G3 success。
   独立 mutation 让 controller 应用同一 diff 时，分类为 `INVALID_SUBSTITUTION`；owner
   拒绝且 controller 未改写时保持原任务不变，不能误报 substitution。

## 实现与信息边界

实现位于：

`research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/`
`experiments/wave-011-g3-quantifier-discriminator/`

交付包括：

- public fixture；
- private oracle；
- blind actual-policy worker；
- closure、measurable、robust、counterfactual 四个 scorer-side worker；
- runner；
- 16 个 conformance/mutation tests；
- README；
- 30 个 per-world/arm run bundles 与汇总 report；
- A/C 两份内部独立研究返回。

actual-policy worker 只接收 public world packet 和 arm envelope。它在 scorer 运行前冻结：

- 动作序列；
- Authority endpoint 使用；
- public-only formation-witness proposal；
- task-change proposal。

它不接收 private oracle、expected category、`C/N/E/T/V` 或 scorer verdict。runner 随后以
独立 subprocess 分别计算 closure、measurable、robust 与 counterfactual。

counterfactual 使用 private oracle 中运行前登记的 intervention IDs，不从成功结果事后挑
operator。它从 exact private `S0` 重放相同 frozen trace，阻断 operator，并核对冻结 trace
后缀的 derived-effect graph。缺少 descendant effect 会使 counterfactual 为 UNKNOWN、
`V=INVALID`，不能继续取得 formation verdict。

每个 run 的 `evidence_binding` 同时绑定：

- G3 receipt body；
- actual-policy transcript；
- closure/measurable/robust/counterfactual receipts；
- exact task diff。

本地 G3 body 保留 X1 v1 要求的字段形状；整个输出不是 X1 finalized outcome，也没有改变
X1 的 `CANDIDATE_NOT_RUN` 状态。

## 实际多 Agent 使用

本 CLI 成功并行启动了三名内部研究者，未模拟：

### A `/root/g3_quantifier_semantics`

职责：量词、Episode/full-policy closure、W1–W6 真值、category precedence 和 causal reset
语义。

实际产物：

`experiments/wave-011-g3-quantifier-discriminator/internal/A-quantifier-semantics.md`

关键影响：

- 明确 W2 必须双绑定 old `UNSAT` 与 after-extension `SAT`；
- 明确 W3 必须允许 `C=SAT + N=NEW_TOKEN + E=SAME`；
- 把 W6 拆为 owner fork / controller substitution paired semantics；
- 要求 causal removal 从 exact S0 重跑，而不是填写 expected label。

### B `/root/g3_minimal_simulator`

职责：最小 simulator/evaluator、public/private 分离、workers 和 runner。

实际产物：fixture、private oracle、5 个 scorer/actual worker、runner 和首轮 30 个输出。

B 的首版受到 C 的真实攻击后修订了：

- 公开语义 world ID 和 `policy_hint` 泄漏；
- 按 arm 名故意制造 miss/substitution；
- closure/measurable 只看 realized branch；
- invalid trace 被算 terminal；
- open inventory 仍可得到 UNSAT；
- counterfactual 不消费 derived-effect reset；
- legal center 按 arm 名偷加 Authority。

### C `/root/g3_adversarial_attack`

职责：攻击 post-treatment oracle、inventory completeness、actual miss/bounded unreachable
混淆和 baseline 偷权。

实际产物：

`experiments/wave-011-g3-quantifier-discriminator/internal/C-adversarial-audit.md`

C 在 B 落盘过程中发现 7 个直接缺陷。主会话没有把首轮 smoke 当验收，而是把这些缺陷路由
回 B，并在 B 结束后继续补：

- public-only method witness；
- derived-effect graph completeness gate；
- owner refusal 与 controller substitution 分离；
- actual transcript/oracle/task diff 的联合 evidence binding；
- legal-control comparison scope；
- 16 个主会话独立测试。

A/B/C 均来自同一 CLI 研究环境。它们提供职责分离和不同失败路径，不构成外部模型、独立
机构或真实主体证据。

## 测试

实际通过：

```text
Wave 011 py_compile                         PASS
Wave 011 unittest                          16/16 PASS
X1 outcome-contract v1 conformance          6/6 PASS
X1 v1 candidate validator                  PASS
所有 Wave 011 JSON parse                    PASS
git diff --check                            PASS
```

16 个 Wave 011 测试覆盖：

- 6 个 opaque public IDs、无 expected category/policy hint；
- 5 个 arm、30 个实际 run 和 worker 分权；
- `C/N/E/T/V`、六个 R、inventory、counterfactual、task diff；
- G3 body、actual transcript、oracle receipts、task diff 联合哈希绑定；
- W1 direct path；
- W2 old UNSAT / extended SAT；
- W3 prefix SAT / new token / same kernel；
- W4 actual-policy miss；
- W5 open-inventory Unknown；
- complete/frozen bounded-unreachable 正控；
- W6 owner fork；
- controller substitution；
- owner refusal不是 substitution；
- invalid trace 不是 safe/terminal；
- derived-effect graph 残留 fail closed；
- method witness 不读 oracle；
- 五个 arm 的动作不按 arm 名变化；
- legal-control 与 equal-envelope comparison scope 分开。

## 当前没有证明什么

本轮只支持：

> 这六类本地合成 world 的主要量词和误分类已经可以由一个可复算 evaluator 区分；当前五个
> arm 在相同 public packet 上没有行为差异，因此没有 formation-specific candidate 增量。

仍然不能支持：

- 真实成熟 full-stack、中心、planner/workflow/IAM 产品已经端到端解决 G3；
- 真人 Principal、真实 Authority 签名、真实 Effect/Acceptance 或商业净值；
- 多领域、fresh holdout、三域 216 episodes 或跨组织一般化；
- worker 是独立实现：scorer workers 虽分进程，仍共享本地 `_engine.py`；
- 恶意 worker 的 OS 权限隔离：当前是输入/代码路径隔离，不是 filesystem sandbox；
- inventory completeness 已由外部 truth owner 独立重建；它仍是合成 fixture 的冻结事实；
- human baseline 是真人、legal-control 是独立生产环境；
- W3/W4 已覆盖 approve/refuse/defer/stale 的完整 contingent response tree；当前 token worlds
  仍是最小 approve branch，W6 才有 approve/refuse；
- synthetic owner receipt 等于现实 Authority service 的签名证据；
- PFE/A2A、NAC 或任何正式机制状态发生改变。

## 下一步门

不要扩到 216 episodes。下一步若继续，应先补两个更承重的局部试验：

1. 同一 method-visible packet、冻结 `APPROVE/REFUSE/DEFER/STALE` response family 的
   contingent-policy pair；actual worker 在合法 response 到达前必须保持不可区分，robust
   worker 不能事后 shrink 分支。
2. 独立 Authority service 对 exact task/model diff 真实签名，并由不同实现的 closure worker
   交叉复算；若两 worker 分歧，必须输出 `UNKNOWN/CONFLICT`。

只有 equal-envelope center、真实 mature composition 和 bounded human baseline 在不同实现、
相同权限与成本下持续失败于同一个 residual，candidate 才有新增机制理由。若成熟组合继续
完整通过，应该接受“现有组合在该边界内解决 G3”，而不是制造新 planner。

本轮未修改 `research/NOW.md`、`PROGRAM.md`、G3 LineContract 或任何正式状态。
