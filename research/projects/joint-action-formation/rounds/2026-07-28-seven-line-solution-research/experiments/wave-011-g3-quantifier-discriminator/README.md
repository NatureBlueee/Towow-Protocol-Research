# Wave 011 G3 six-world quantifier discriminator

状态：`LOCAL_SYNTHETIC / QUANTIFIER DISCRIMINATOR / NOT X1 RUN`

本实验先检验 G3 的量词和分类能否被一个小型可执行系统稳定区分，不扩展到三域
216 episodes，也不主张新的 formation-specific planner 必要。

## 这次实际区分了什么

同一张输出同时保留：

- `C`：冻结 old full-policy closure 的 `SAT / UNSAT / UNKNOWN`；
- `N`：现实 operative condition 是 `NONE / EXTANT_ACTIVATED / NEW_TOKEN`；
- `E`：action/kernel 是否 `SAME / CHANGED`；
- `T`：原任务保持、owner-authorized fork 或 controller substitution；
- `V`：trace、Authority、counterfactual evidence 是否有效；
- 六个 `R`：physical、measurable、actual、effect robust、safe robust、terminal robust；
- inventory completeness、actual-policy transcript、frozen-trace counterfactual 和 exact task
  diff。

`C` 不是“当前没有立即执行路径”。W3 明确允许旧 policy 已经包含
`request → sign → execute`，因此 `C=SAT`；episode 中具体 purpose token 首次生成，故同时
`N=NEW_TOKEN, E=SAME`。W2 则保存两个 executable model：old closure 是 `UNSAT`，经过
预先声明且获授权的 `install_adapter` extension 后为 `SAT`。

## 六个 worlds

| public id | 区分 | 主要结果 |
|---|---|---|
| `E01` | direct qualified path 已存在 | `PREEXISTING_QUALIFIED_PATH`, `C=SAT` |
| `E02` | complete/frozen old inventory 无解，合法新 operator 后可解 | `QUALIFIED_CONDITION_FORMATION`, old `UNSAT` → extended `SAT` |
| `E03` | 旧 policy 已含 request/sign，token 在 episode 内新生成 | `PREFIX_SAT_NEW_TOKEN`, `C=SAT, N=NEW_TOKEN, E=SAME` |
| `E04` | measurable path 存在，actual policy 信任 stale cache 并失败 | `ACTUAL_POLICY_MISS`，不能归为 bounded unreachable |
| `E05` | tool/partner/representation inventory 开放 | `UNKNOWN`；有限 frontier exhausted 也不能写 `UNSAT` |
| `E06` | material `Q/V0` 变化 | 主运行是 `AUTHORIZED_NEW_EPISODE`；测试另行注入 controller rewrite 并要求 `INVALID_SUBSTITUTION` |

W6 的 owner refusal 也有独立测试：owner 没有批准且 controller 没有改写时，结果保持原任务
不变，不能凭“未获批准”伪造 controller substitution。

## 进程与信息隔离

`actual_policy_worker.py` 只接收 public world packet 和 arm envelope。它先输出冻结动作
transcript 和一个只由公开 packet/所选动作生成的 formation-witness proposal，不接收
`private/oracles.json`、expected category 或 scorer verdict。

runner 随后分别启动：

1. `closure_oracle_worker.py`；
2. `measurable_oracle_worker.py`；
3. `robust_worker.py`；
4. `counterfactual_worker.py`。

closure 和 measurable worker 穷举冻结 response family；inventory 任一承重项不是
`COMPLETE` 就 fail closed 为 `UNKNOWN`。counterfactual worker 只使用运行前冻结的
intervention IDs，从 exact private `S0` 重放同一 actual trace，阻断 operator，并核对
derived-effect reset graph。缺失派生效应会使 counterfactual 和 `V` 失效，不能继续获得
formation verdict。

每个 run 的 `evidence_binding` 同时绑定 G3 body、actual transcript、oracle receipts 和
exact task diff。它是本地 receipt bundle，不是正式 X1 finalize。

## 公平 baseline

每个 world 运行五个 arm：

- `B-CENTER-EQUAL-ENVELOPE`；
- `B-CENTER-LEGAL-CONTROL`；
- `B-MATURE-PLANNER-WORKFLOW`；
- `B-HUMAN-RULE`；
- `C-FORMATION`。

五个 arm 在当前 public packet 上产生相同动作序列，candidate 独有成功为 `0`。这说明当前
六个合成 world 没有显示新 planner 增量；成熟 planning/workflow、equal-envelope center 和
有界制度规则已覆盖同一分母。

`B-CENTER-LEGAL-CONTROL` 标为
`DIFFERENT_ENVIRONMENT_CONSTRUCTIVE_COUNTEREXAMPLE`。它表达“合法集中控制条件下成熟中心
可以解决”的正例，不参与同 Authority topology 下的算法优越比较，也不能凭 arm 名代替
Principal 决定。`B-HUMAN-RULE` 是可执行、有限预算的制度规则，不是真人实验。

## 文件

```text
fixtures/public-worlds.json        method-visible episode 与 baseline envelope
private/oracles.json               scorer-only transition/response/reset truth
g3disc/                            canonical JSON/hash helper
workers/actual_policy_worker.py    blind actual policy + method witness proposal
workers/closure_oracle_worker.py   old/extended full-policy closure
workers/measurable_oracle_worker.py
workers/robust_worker.py
workers/counterfactual_worker.py
runner.py                          subprocess orchestration + receipts
tests/test_discriminator.py        16 个 conformance/mutation tests
outputs/report.json                最近一次 6×5 本地运行
outputs/runs/                      30 个逐 world/arm receipt bundle
internal/                          A/C 独立研究返回
```

## 运行

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-011-g3-quantifier-discriminator

PYTHONPYCACHEPREFIX=/tmp/wave011-pycache \
  python3 -m py_compile runner.py g3disc/*.py workers/*.py tests/*.py

PYTHONDONTWRITEBYTECODE=1 python3 runner.py

PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s tests -v
```

当前复核结果：`6 worlds × 5 arms = 30 results`，16 项测试通过。

测试包括：opaque public IDs、无 expected label、worker 分权、receipt/evidence binding、
W1–W6 分类、open inventory fail-closed、actual miss 不得归入 bounded unreachable、
complete inventory 的 bounded-unreachable 正控、owner/controller/refusal 三分、invalid
不得计作 safe/terminal、derived-effect residue、method witness 不读 oracle、arm-invariant
动作以及 legal-center comparison scope。

## 证据边界

本实验支持的是：这六类合成 world 的量词和主要误分类可以由一个可复算 evaluator 区分；
当前现成组合与 candidate 在同一公开信息上行为相同。

它不支持：

- 真实 full-stack 产品或独立成熟实现已经完成端到端 G3；
- 真人制度、真实 Principal/Authority、商业净值或跨域一般化；
- 三域 216 episodes 的 coverage；
- 新 planner、协议或 PFE/A2A 独特性；
- X1 已运行、正式状态已改变或 X2 已获授权。

当前实现仍是同一研究工作流内的本地合成 fixture。内部 A/C 返回提高了反例覆盖，但不构成
外部独立证据。
