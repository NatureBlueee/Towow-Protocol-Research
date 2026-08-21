# Cohort 003 G1 第二次根红灯修复最终返回

日期：2026-07-30  
状态：`PROCESS IDENTITY RED REPAIRED IN CONTROLLER-HOSTED SYNTHETIC FIXTURE SCOPE /
SAME-USER OS RED / LOCAL SYNTHETIC ONLY / NO FORMAL PROMOTION`

## 最窄结论

本轮建立的是一个 controller-hosted synthetic fixture 的进程与来源错配拒绝边界：

> controller 不再用 child 的两份自报互相证明进程身份。owner READY、每条 owner
> response/event、worker READY/attestation、worker query 与 worker result，都必须同时
> 匹配 controller 持有的实际 `Popen.pid` 和 controller 为本次 launch 分配的
> source/state/process instance；任一错配都在 owner raw response 转发或正向评价之前
> fail closed。合法 owner response 仍按收到的 exact raw bytes 原样转发。

owner source 被逐字标为：

```text
CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE
```

这不是 independent owner truth/origin。owner records、operators 与 evaluator truth 仍由
controller 从同一个 synthetic `World` 构造；PID 与 launch-instance 绑定只能证明当前
cooperative controller/child channel 没有发生这些来源错配，不能把 fixture 变成现实 owner。

same-UID 绝对路径探针继续实际返回：

```text
RED_NOT_ISOLATED
```

因此真实 owner、hostile OS isolation、现实 discovery 与完整 CE-001 均保持
`NOT_ESTABLISHED`。

## A：根红灯重建

`/root/g1_fix2_a_boundary` 只读重建了修复前证据链，未编辑文件。它确认：

- controller 确实持有 owner/worker 的 `Popen` handle，但正常证据链没有使用
  `Popen.pid`；
- owner READY 只校验 message type，随后把 child 自报 PID 当作 owner PID；
- event origin 只与同一个 child 的 READY 自报比较，而且结果只写入 receipt，不阻断
  raw response 转发或 evaluator；
- worker receipt 的 PID 与 `distinct_processes` 也来自 worker attestation 自报；
- 因此 owner READY + event origin 可同时伪报 `424242`，worker attestation 也可伪报；
- records、expected、source aliases 与 authority aliases 来自同一个 synthetic
  `World`，修 PID 后也不能支持 independent owner truth。

Agent A 给出的修复判据是：以 controller-side `Popen.pid` 和 pipe 为 runtime anchor，
在 raw owner response 转发前验证 actual PID、controller-held launch instance、request
raw hash 与 state/process binding；失败帧绝不进入 worker。

## B：实现

`/root/g1_fix2_b_implement` 只修改 `g1-provenance/`，未写本 final。

每个正常 episode 的边界现在是：

```text
controller + local evaluator
  ├─ synthetic World:
  │    owner records/operators + private expected/L/D/oracle
  ├─ controller-observed Popen.pid
  ├─ controller-assigned owner source/state/process instance
  ├─ controller-assigned worker process instance
  │
  ├── controller-hosted synthetic owner fixture child
  │     READY/response/event 必须匹配 actual Popen.pid + launch binding
  │
  └── standalone worker child
        READY/query/result 必须匹配 actual Popen.pid + process instance
        inbound 只有 interface 与通过 gate 的 exact owner raw response
```

controller 验证通过后转发同一份 `owner_wire`，不从 parsed dict 重序列化。身份错配抛出
`ProcessBoundaryViolation`；receipt 保存 actual worker/owner `Popen.pid`、controller
assignment、拒绝码和截至拒绝点的 raw frames。异常发生在 `run_process_episode()` 内，
`evaluate_trace()` 不会获得 candidate。

source/state/process instance 是 controller 每次 launch 分配并在 controller 内保存的值，
不是由 READY 与 event 两份 child 字段自行定义。child 的字段只是与 controller assignment
和实际 `Popen.pid` 比对的 claim。它仍不是签名、外部 ledger 或恶意同 UID 进程隔离。

## 四个必需来源错配注入

四项均运行真实 owner/worker subprocess：

| injection | 实际拒绝 | raw frames | 正向评价 |
|---|---|---:|---|
| `OWNER_PID_MISMATCH` | `OWNER_READY_PID_MISMATCH` | 2 | 0 |
| `WORKER_PID_MISMATCH` | `WORKER_READY_PID_MISMATCH` | 4 | 0 |
| `ORIGIN_SELF_REPORT_INCONSISTENCY` | `OWNER_EVENT_ORIGIN_PID_MISMATCH` | 7 | 0 |
| `WRONG_SOURCE_INSTANCE` | `OWNER_EVENT_SOURCE_INSTANCE_MISMATCH` | 7 | 0 |

前两项实际伪报 `424242`。后两项的无效 owner response 已进入
owner→controller forensic trace，但没有对应 controller→worker frame，故不是“先转发、
最后记一个 false bool”。

## C：不读 B 期待答案的攻击

`/root/g1_fix2_c_blind_attack` 使用隔离上下文，不读 `tests/`、README、`C-ATTACK.md`、
任何 final 或 B 的返回；它只读 FIX2 prompt 与必要运行源码，用临时内存探针攻击实际 child，
未编辑文件。

C 独立复现：

- owner READY `424242`、worker READY/attestation `424242` 均在正向动作前拒绝；
- origin self-report 与 wrong source instance 的无效 response SHA 没有进入 worker
  inbound；
- 额外把 worker query/result 的 PID 或 process instance 改错，也分别触发
  `WORKER_DISCOVER_*_MISMATCH` 或 `WORKER_RESULT_*_MISMATCH`，evaluator 调用为 0；
- E1 正例 owner/worker/controller PID 不同，3 次 query 与 3 次 response 的双向 relay
  都保持 exact bytes；
- 8 个 baseline 的 canary/forbidden marker 均不在 worker inbound；
- same-UID path probe 仍是 `RED_NOT_ISOLATED`。

C 还找到一项新的真实红灯：B 首版 composition envelope 把内部 `authority_id` 改名为
`g1_claim_root_id`，词法 validator 因而假绿；value validator 也会放过
`RELATION_ESTABLISHED` 这类组合值。

根会话据此完成两项修复：

1. 删除 `g1_claim_root_id`，Authority-root 数据只留在内部 G1 invalidity evaluator，不以
   改名方式进入 composition envelope；
2. 对所有 envelope 字符串做 token-level 禁止检查。E3 exact episode ID 含后线词，故
   envelope 只输出其可复算 SHA-256 reference，exact ID 留在 envelope 外的 forensic
   result。

根会话另发现五个原语义 injection 名称被一并写入 `WORKER_INIT`。这虽不是 L/D/canary，
却会让恶意 worker 按攻击类型特判。最终版本只在
`WORKER_PID_MISMATCH` 时把 worker 自身 attestation injection 送入 worker；原五个
owner/evaluator 语义 injection 名称均不进入 method-visible bytes。

## G1 line-local composition envelope

composition-facing schema 为：

```text
towow-g1-provenance-line-envelope-v2
```

字段使用 G1 namespace；它只携带 local candidate/source/process provenance、invalidity
摘要、raw trace hash 与 output hash。输出状态仍只能是：

```text
CANDIDATE_NOT_COMMITMENT
```

或相应的 G1 local `UNKNOWN / INVALID / REFUSED_OR_UNAVAILABLE /
NOVEL_CANDIDATE_FOR_NEXT_VERSION`。

envelope 不携带合同成功，也不携带 Relation、Authority、Effect、Acceptance 或 Settlement
字段/值。8 个 baseline envelope 的递归 violations 均为空，raw exact episode ID 也没有
进入 envelope。

旧 `g1_handoff` 与 forensic result 只为保留原 30 项回归和内部 invalidity 诊断，不是合格的
跨线 composition envelope；后续 runner 应只消费 `g1_line_envelope`。

## 原有能力与红灯保留

clarification 仍明确分界：

```text
vague request
→ questions/context
→ IntentCandidate
→ O_Q explain-back
→ O_Q claim
→ IntentAtCoordinationInterface
```

prelude 不进入 worker input，只由 receipt hash 连接。完整 Q 文本仍保留后续 owner 对 exact
Q 与实际结果作出接受、之后才能进入结算的要求，但 G1 envelope 不输出这些后线状态。

E2：

```text
actual  = QUALIFIED_CANDIDATE / handoff CANDIDATE_NOT_COMMITMENT
remove  = UNKNOWN
reverse = INVALID / REVOKED_EVIDENCE
```

原五个 invalidity-first failure injection 全部保留：

```text
WRONG_AUTHORITY   = INVALID
SOURCE_ALIAS      = INVALID
TAMPER_PAYLOAD    = INVALID
TRUTH_TRANSPLANT  = INVALID
POST_TREATMENT_T0 = INVALID
```

它们的标签均未进入 worker input。

## 最终数字与冻结凭据

最终根会话验证：

```text
python3 -m unittest discover -s tests -v
Ran 35 tests in 17.148s
OK

40 consecutive normal process episodes
40/40 QUALIFIED_CANDIDATE

python3 runner.py --output frozen-output.json
exit 0

verify_frozen_manifest(frozen-output.json)
valid=true / mismatches=[]

PYTHONPYCACHEPREFIX=<temporary dir> python3 -m compileall -q g1prov tests runner.py
PASS
```

测试构成：

```text
原风险覆盖                    = 30/30
新增 identity/envelope tests = 5/5
总测试                        = 35/35
```

运行分母与结果：

```text
baseline cases                         = 8
|L_benchmark|                          = 9
L_benchmark discovered                 = 6/9
|D_actual|                             = 6
D_actual discovered                    = 6/6
baseline qualified                     = 6
refused/unknown outside D_actual       = 2
baseline invalid                       = 0
E2 actual/remove/reverse               = QUALIFIED / UNKNOWN / INVALID
semantic failure injections            = 5/5 INVALID
process identity injections            = 4/4 FAIL_CLOSED
exact raw relay checks                  = 96/96
private canary absent from inbound      = 16/16
semantic injection labels in worker     = 0/5
line envelope violations               = 0/8
raw episode IDs in line envelope        = 0/8
same UID absolute-path isolation        = RED_NOT_ISOLATED
```

冻结文件：

```text
path            = experiments/wave-012-ce001-power-restoration/
                  g1-provenance/frozen-output.json
bytes           = 1,449,446
sha256          = a3f908e7199d0475d09bd00268bd6074a0cdc31d994eb2c7772cfee17aa8081f
manifest_sha256 = 0a6282a0b679d7d58fc9cc256b6b4370110e466ef6350f763a34e8a557de83c0
verify          = valid / mismatches=[]
```

manifest 继续绑定 source tree、public/private input receipts、16 个正常/语义注入 run 的 raw
boundary/result traces、4 个 identity fail-closed raw traces 与完整 result bytes。它是普通
误改检测，不是外部 append-only seal、签名或 hostile controller 证明。

`6/6 D_actual` 只表示当前 hand-authored local synthetic policy denominator；它不表示现实
discovery 的频率、一般能力、方法胜者或完整任务成功率。

## 能支持与不能支持

当前可以支持：

```text
G1_CONTROLLER_OBSERVED_CHILD_PID_BINDING = POSITIVE_SCOPED
G1_CONTROLLER_ASSIGNED_LAUNCH_INSTANCE_BINDING = POSITIVE_SCOPED
G1_SOURCE_MISMATCH_FAIL_CLOSED = POSITIVE_SCOPED
G1_EXACT_RAW_BYTE_RELAY = POSITIVE_SCOPED
G1_COOPERATIVE_WORKER_PRIVATE_INPUT_NON_RECEIPT = POSITIVE_SCOPED
G1_LINE_LOCAL_CANDIDATE_ENVELOPE = POSITIVE_SCOPED
G1_OWNER_SOURCE = CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE
```

仍不能支持：

```text
G1_INDEPENDENT_OWNER_TRUTH = NOT_ESTABLISHED
G1_INDEPENDENT_OWNER_ORIGIN = NOT_ESTABLISHED
G1_REAL_OWNER_IDENTITY_OR_ACT = NOT_ESTABLISHED
G1_HOSTILE_OS_ISOLATION = RED_NOT_ISOLATED
G1_REAL_DISCOVERY = NOT_ESTABLISHED
G1_GENERAL_DISCOVERY_CAPABILITY = NOT_ESTABLISHED
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

此外仍未建立 evaluator/controller 独立权限域、O_R/O_V 独立部署与真实拒绝权、外部
append-only seal、签名 origin、真人理解/认领、现实供电、恢复、后线状态、G2–G7 或任何
Problem/LineContract/MechanismProfile 正式状态变化。

## 下一接口

后续 composition runner 只能把 `g1_line_envelope` 当作 G1 local candidate provenance。
它必须自行取得其他线的 owner act、target-native state、现实读回与各自 acceptance gate；
不得从 synthetic fixture PID/instance binding 或 `CANDIDATE_NOT_COMMITMENT` 推出完整
episode 已成立。

本轮未修改 contract、NOW、PROGRAM、Problem、LineContract、机制状态或其他六线目录。
