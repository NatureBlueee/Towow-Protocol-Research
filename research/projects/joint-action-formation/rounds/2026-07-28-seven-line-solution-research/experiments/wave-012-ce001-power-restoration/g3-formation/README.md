# CE-001 G3 formation/reachability module

状态：`LOCAL_SYNTHETIC LINE MODULE / CONTRACT EVALUATOR NOT RUN / REAL PRODUCTS NOT RUN`

本目录只产生 G3 line-local evidence。它区分 direct、old full-policy closure、
episode 内 new token、model/kernel change、task substitution 与 open-inventory Unknown，
但不计算或透传 CE-001 合同结论。

## 运行与进程边界

每个 run 使用三个先后隔离的来源：

1. runner 启动独立 owner endpoint 与 public worker；
2. worker 的初始输入是公开 packet/control bytes，运行中只消费经 broker 原样传输的
   owner response bytes；
3. worker 与 owner 都终止、transcript 冻结后，runner 才启动独立 grader process。

worker 由 `worker_capsule.py` 启动，cwd 在 `/private/tmp`，环境变量使用最小白名单。
不可移除的 Python audit hook 对整个研究 workspace 使用 file allowlist：只允许 capsule、
`worker_process / execution_service / protocol / models / canonical / __init__` 及对应 pyc；
private truth、owner/scorer/runner、tests、internal、outputs 与 cohort final 均拒绝读取。
这是当前可检查的本地隔离，不是抵抗任意 native-code 恶意进程的 OS/硬件边界。

owner endpoint response 使用 public packet 固定的 Ed25519 verification key 验证，并绑定：

- owner identity、state version、policy version/head；
- episode、Q、object/target、operation；
- request hash/nonce、proposal hash、response nonce；
- issued-at 与 request response deadline；
- payload、response hash 与 owner authenticator。

transplant、stale time/state/policy、wrong owner/Q/target/operation/request/request nonce/proposal
与 tamper（包括重算裸 hash）都由传输边界测试拒绝。broker 从 owner stdout 读取完整 raw
JSONL line，并把同一字符串逐字节转发给 worker；owner-emitted、broker-forwarded 与
worker-consumed 的逐行 raw-byte hash/list 必须相等。测试另用不同 whitespace/key-order
的合法 owner wire 验证不会被 parse/re-serialize 偷换。

## G3 envelope

`outputs/report.json` 的 component body 只含：

- `C/N/E/T/V`；
- path class 与 opaque case/episode handle；
- physical/measurable/actual bounded reachability coordinates；
- branch/safety/terminal robustness（完整 response tree 未冻结，因此全为 `UNKNOWN`）；
- bounded reachability witness、intervention trace、post-revoke operation/deadline/safety/
  owner-outcome observation 与 uncertainty；
- transcript/process separation bindings。

它不含合同级字段或同义 verdict。测试把此 G3 body 实际替换进
`integration-preflight/fixtures/qualified-e1.json` 后调用真实 preflight；当前返回
`QUALIFIED_COMPONENT_OUTPUTS / CONTRACT_SCORE_NOT_COMPUTED`，没有 rejection。

## E2 与 E4 的局部事实

E2 proposal 在 public worker 内生成，owner endpoint 返回 proposal-bound response。
`REMOVE_FORMATION_OPERATOR` 从实际 closed dispatch registry 删除唯一
`FORM_PURPOSE_TOKEN_AND_DELEGATION` operator。remove run 同时证明：

- runtime matching operator inventory 为空；
- proposal/sign-request/token-formed/target-submit count 全部为 0；
- frozen/executable registry 与 intervention delta 均有 hash；
- 源码只有一个 formation owner-request dispatch site。

四个 owner-response reverse intervention 与 remove 都从相同 frozen S0 重放。S0 绑定公开
bytes、owner routing/state/policy heads、scripted response snapshot、budget、horizon、
clock seed 与 executable registry。

E4 initial read 只含随后被 revoke 的 primary。revoke 后发生独立 rediscovery，才观察到
alternative；raw trace 保留 resource/operation/readback、deadline、safety constraints 与
O_Q/O_V outcome response。G3 envelope 只报告这些可达性观察，未来独立 evaluator 必须从
冻结 episode 重算合同结果。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/ce001-g3-pycache \
  python3 -m py_compile run.py worker_capsule.py formation/*.py tests/*.py

PYTHONDONTWRITEBYTECODE=1 python3 run.py

PYTHONDONTWRITEBYTECODE=1 \
  python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

生成：

- `outputs/report.json`：integration-facing G3 line envelope；
- `outputs/traces.jsonl`：baseline、E2 exact-S0 interventions 与 task-substitution raw runs。

## 边界

当前 26 项测试只支持本地合成 fixture 的传输、拒绝、闭包分类、counterfactual 与 envelope
admission 行为。physical/measurable 仍是 local grader scan，不是独立现实 oracle；
完整 response-family robustness 未运行。真实产品、真人 Principal、法律 Authority、
物理 Effect、合同 Acceptance/Settlement、完整 CE-001 合同解均为
`NOT_RUN / NOT_ESTABLISHED`。
