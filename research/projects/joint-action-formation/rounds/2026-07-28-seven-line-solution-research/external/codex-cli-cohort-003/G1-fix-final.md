# Cohort 003 G1 根红灯修复最终返回

日期：2026-07-30  
状态：`ROOT RED REPAIRED IN COOPERATIVE PROCESS/API SCOPE / SAME-USER OS RED /
LOCAL SYNTHETIC ONLY / NO FORMAL PROMOTION`

## 最窄结论

本轮建立了一个可复跑的窄边界：

> 在当前 8-case CE-001 本地合成 G1 fixture 中，默认 method 运行于独立 worker
> subprocess。worker 的实际入站 bytes 只有冻结
> `IntentAtCoordinationInterface` 与独立 owner-service process 返回的允许原始
> response；本轮受控 reflection/closure/frame/gc/import/env/argv/cwd 扫描没有取得
> private `expected/L_benchmark/D_actual/oracle/final proposal`，controller 对 owner
> response 做逐字节转发，G1 输出只是一份可复算的
> `CANDIDATE_NOT_COMMITMENT` handoff。

这不是 hostile OS isolation。相同 OS 用户若预先知道仓库绝对路径，仍可确认 private fixture
源码可读；实际 probe 返回 `RED_NOT_ISOLATED`。因此本轮只建立“默认 worker 的进程/API
非传输边界”，不建立同 UID 恶意进程的机密性。

## 首轮根红灯如何被复现

Agent A 的只读重建与根会话源码复核确认：

- `DiscoverySession` 把完整 `World` 保存在 `self._world`；
- method 与 controller 同 PID，能经 `_world`、bound method `__self__`、传递 import 与
  reflection 取得 `expected/L/D`；
- `DiscoverySession._issue()` 由 controller/session 本身生成 owner event；
- `method_visible_input_receipt` 只是对内存 interface 重算 hash，实际 IPC frame 数为 0；
- population receipt 没有同时冻结 source、实际 input bytes、transport、raw trace 和
  result。

因此上一轮 `26/26 OK` 只能保留为诚实 method 的 local semantic regression，不能支持
oracle、owner 或 process isolation。

## 修复后的进程与数据边界

默认运行每个 episode 建立三个不同 PID：

```text
controller + local evaluator PID
  ├─ private evaluator bytes:
  │    expected / L / D / oracle roots / private canary
  ├─ exact-byte relay
  │
  ├── owner-service PID
  │     持有 owner records/operator state
  │     生成 event hash、service PID、state version、request hash
  │
  └── standalone worker PID
        python -I -S
        sanitized temporary cwd
        stdlib-only single-file program
        stdin: WORKER_INIT + raw DISCOVERY_RESPONSE frames
```

worker 启动前，controller/evaluator 确实构造了包含
`expected/L/D/oracle roots/private canary` 的 private bytes，并记录 byte length 与 hash。
这些 private bytes 不发送给 worker。

worker 每次只发通用 `DISCOVER(kind, predicates)`。controller 把 worker query 的原始 JSONL
bytes 原样送给 owner service，再把 owner stdout 的原始 response bytes 原样送回 worker；
转发路径不从解析后的 dict 重新序列化 response。每个 credited evidence 暴露
`owner_service_pid / owner_state_version / owner_request_hash`。

controller 仍是受信任 fixture builder、router 与 evaluator；本轮没有把 evaluator 与
controller 再分成两个 PID。每个 episode 也只运行一个合成 owner-service process，它承载
本 case 的 scoped owner records；这不是现实中 O_R/O_V 的权限域独立部署证明。

## 实际传输 bytes 与冻结输出

冻结运行保存在：

`experiments/wave-012-ce001-power-restoration/g1-provenance/frozen-output.json`

文件：

```text
bytes  = 1,123,818
sha256 = e333359dedbfc538558b6839d040f58ca928007559e60869fb438674567aadec
```

它包含 16 个实际 process runs：

- 8 baseline；
- 3 个 E2 actual/remove/reverse；
- 5 个 failure injection。

这些运行共记录：

```text
process receipts                 = 16/16 distinct controller/owner/worker PID
worker inbound frames            = 64
worker inbound bytes             = 52,176
worker↔owner exact relay checks  = 96
all exact-byte relay checks      = 96/96
private canary present privately = 16/16
private canary absent inbound    = 16/16
```

worker 自报 stdin frame length/hash 与 controller 记录逐项相等。worker source 与实际入站
bytes 均没有 private marker；受控 runtime scan 的 marker/module hit 都为空。

内嵌 `ce001-g1-frozen-manifest-v2` 绑定：

- Python source tree；
- public interface 与 private evaluator input receipts；
- 每个 raw process-boundary trace；
- evaluator raw result trace；
- manifest 之外的完整 result bytes。

冻结 manifest：

```text
manifest_sha256 = bf68ee628346cd2aed76043300de47a0f0ed83e4857a83fad3b3acd9a5b3ea29
verify          = valid / mismatches=[]
```

mutation verifier 分别改 source receipt、private input receipt、transport frame、raw trace 和
result，均使相应 binding 失效。该 manifest 是本地冻结与普通误改检测，不是外部
append-only seal 或签名证明。

## clarification、E2 与 failure injection 保留情况

clarification 链仍是：

```text
vague request
→ questions/context
→ IntentCandidate
→ O_Q explain-back
→ O_Q claim
→ IntentAtCoordinationInterface
```

prelude 原文、questions、draft、explain-back 和 claim 不进入 worker input；worker 只收到
接口及 prelude receipt。完整 `Q@v1` 继续保留 requester/venue 对 exact Q 与实际 Effect
作出 Acceptance、之后才可 Settlement 的要求，但 G1 不把它们写成已实现结果。

E2：

```text
actual  = QUALIFIED_CANDIDATE
remove  = UNKNOWN
reverse = INVALID / REVOKED_EVIDENCE
```

operator 改变 owner-service state；worker 不收到 answer-shaped operator menu。

五类 failure injection：

```text
WRONG_AUTHORITY   = INVALID
SOURCE_ALIAS      = INVALID
TAMPER_PAYLOAD    = INVALID
TRUTH_TRANSPLANT  = INVALID
POST_TREATMENT_T0 = INVALID
```

全部在 positive interpretation 前 hard fail。

## handoff 语义边界

qualified handoff 的 status 仍是：

```text
CANDIDATE_NOT_COMMITMENT
```

并精确列出以下 non-claims：

```text
RELATION
COMMITMENT
AUTHORITY
EFFECT
ACCEPTANCE
SETTLEMENT
```

candidate/resource/partner、owner response 与 provenance 可以由后续组合 runner 消费；它们
不能推出 Relation 已形成、主体已 Commitment、已有 Authority、Effect 已发生或已被
Acceptance。

## A / B / C 实际建立情况

1. `/root/g1_a_reconstruct`
   - 只读完整重建首轮 oracle/owner/process 红灯；
   - 实际确认同 PID、`session._world`、bound `__self__` 与 0 IPC frames；
   - 未编辑文件。
2. `/root/g1_b_implement`
   - 只修改 `g1-provenance/`；
   - 实现 standalone worker、owner service、exact-byte relay、runtime scan、manifest 与
     tests；
   - 未写本 final。
3. 首个 `/root/g1_c_attack`
   - 在 B 修复前重建结构攻击；
   - 一次用于排除 `fixtures.py` 的 glob 未生效，意外显示部分 L/D 赋值行；
   - 其结果因此只保留为结构审计，不冒充未见分母的独立攻击证据。
4. 替代盲态 `/root/g1_c_blind`
   - 使用 `fork_turns=none`，只读 `worker_process.py`、`owner_process.py` 与
     `process_boundary.py`，未读 fixtures/evaluator/tests/final/prompt；
   - 独立确认 worker 只经 JSONL bytes 收入 interface/owner response、无 controller Python
     object/closure 传入、owner event 在 owner process 生成、controller 是 raw-byte relay；
   - 只输出布尔/状态元数据的实际 QA run 为：

```text
distinct=True
markers=[]
private_absent=True
worker_match=True
exact=True
origin=True
runtime_marker_hits=[]
runtime_module_hits=[]
exit=0
```

Agent 数量不构成独立证据；结论来自实际 bytes、进程边界、可执行 red、冻结 output 与根会话
复跑。

## 红灯历史与最终验证

修复过程中保留了两项新的真实失败：

1. 首版恶意 runtime graph 递归扫描在 worker READY 前运行超过 60 秒；已收窄为有界
   targeted scan。
2. 首版 protocol timeout 对带 read-ahead 的 `Popen.stdout` 使用 `select()`。读取
   `WORKER_READY` 时可能已把下一帧读入 Python 用户态 buffer，OS fd 随后不 readable，
   造成 false timeout。根会话串行 30-test run 实际出现两个 error 后中止。

第二项通过给 subprocess pipe 设置 `bufsize=0` 修复；随后根会话运行 40 个连续 process
episode，没有 timeout。

最终串行验证：

```text
python3 -m unittest discover -s tests -v
Ran 30 tests in 17.097s
OK

40 consecutive process episodes
40/40 QUALIFIED_CANDIDATE

python3 runner.py --output frozen-output.json
exit 0

verify_frozen_manifest(frozen-output.json)
valid=true / mismatches=[]

compileall with isolated /tmp pycache
PASS
```

实际 G1 分母与结果：

```text
baseline cases                        = 8
|L_benchmark|                         = 9
|D_actual|                            = 6
D_actual discovered                   = 6/6
L_benchmark discovered                = 6/9
baseline qualified                    = 6
refused/unknown outside D_actual      = 2
baseline invalid                      = 0
E2 actual/remove/reverse              = QUALIFIED / UNKNOWN / INVALID
failure injections                    = 5/5 INVALID
process-boundary tests                = 4/4
all tests                             = 30/30
```

`6/6 D_actual` 只是当前 hand-authored local fixture 的 actual-policy denominator，不是一般
discovery 能力、现实频率、方法胜者或完整任务成功率。

## 仍未建立的边界

- same-user hostile OS、绝对路径读取、debugger、进程内存读取或同 UID 文件访问下的机密性；
- evaluator 与 controller 的独立 PID/权限域；
- O_R 与 O_V 各自独立部署、独立凭据与真实拒绝权；
- 外部 append-only seal、签名系统或抗恶意 controller 的 origin proof；
- 真实产品、真实 owner act、真人理解、认领或 Acceptance；
- 现实临时供电、Effect、Settlement、恢复或迁移；
- 一般 discovery/formation 能力、方法比较或 winner；
- G2–G7、完整 CE-001、V1/V2 或跨七线组合闭合；
- 新机制必要性、Problem/LineContract/MechanismProfile 或任何正式状态变化。

本轮未修改 contract、NOW、PROGRAM、Problem、LineContract、机制状态或其他六线目录。
