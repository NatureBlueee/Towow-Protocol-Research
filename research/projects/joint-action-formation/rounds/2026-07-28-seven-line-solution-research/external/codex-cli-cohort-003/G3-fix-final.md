# Cohort 003 G3 根红灯修复返回

日期：2026-07-30  
状态：`LOCAL SYNTHETIC LINE ENVELOPE QUALIFIED / CONTRACT SCORE NOT COMPUTED /
REAL-WORLD CLAIMS NOT ESTABLISHED`

## 结论

本轮没有沿用旧 `18/18` 的完成口径。旧实现的 owner、worker、scorer truth surface
确实没有可信传输边界，且 G3 越权输出了合同结论。修复后，当前最窄可支持状态为：

```text
OWNER / PUBLIC WORKER / GRADER PROCESS BOUNDARY
  = ACTUALLY OBSERVED

OWNER RAW JSONL → BROKER → WORKER
  = BYTE-EXACT FORWARDED AND HASHED

OWNER RESPONSE BINDING
  = FAIL-CLOSED FOR 14 SINGLE-DIMENSION FAULTS

G3 OUTPUT
  = LINE-LOCAL FORMATION / REACHABILITY EVIDENCE ONLY

INTEGRATION PREFLIGHT
  = QUALIFIED_COMPONENT_OUTPUTS
  = CONTRACT_SCORE_NOT_COMPUTED
  = REJECTIONS []

FULL RESPONSE-FAMILY ROBUSTNESS
  = NOT RUN / UNKNOWN

REAL PRODUCTS / REAL PRINCIPAL / LEGAL POWER /
PHYSICAL-WORLD RESULT / CONTRACT POSTCONDITION / CE-001 SOLUTION
  = NOT RUN OR NOT ESTABLISHED
```

`QUALIFIED_COMPONENT_OUTPUTS` 只说明当前 G3 局部 envelope 可以进入未来独立 evaluator，
不说明 CE-001 成功。

## A / B / C

### A：`/root/g3_round2_a_authority`

A 在不读取本轮 B/C 新文件的前提下重建 evidence authority，原始返回保存在
`g3-formation/internal/A2-evidence-authority.md`。A 直接确认旧接口的四个根失败：

1. runner 同进程读取 public/private 并构造 owner、worker 与 scorer；
2. worker 与 scorer 都能通过 `OwnerService` 回到同一 private truth；
3. owner response 没有统一绑定 identity、state/policy version、episode/Q/object/
   operation、request/proposal、nonce 与 issued-at；
4. scorer 输出合同 success/resolution/recovery 字段并读取 private resolution。

A 冻结了三运行域、actual transmitted bytes、transcript-frozen grader、E2 closed
executable registry、E4 bounded witness 与 line-local envelope 的验收边界。

### B：`/root/g3_round2_b_impl`

B 的实现与原始结论保存在
`g3-formation/internal/B2-implementation-return.md`。B 实际建立：

- 独立 owner endpoint subprocess；
- public worker subprocess 与 workspace file allowlist capsule；
- worker/owner 退出、transcript 冻结后才启动的 grader subprocess；
- Ed25519 owner response authenticator；
- raw JSONL 逐字节 broker；
- closed formation dispatch registry；
- 只返回 line-local evidence 的 grader envelope。

### C：blind preregistration + post-fix recheck

C 的盲攻击矩阵由 `/root/g3_round2_c_attacks` 在不知道 B 选择时先冻结；post-fix 复核
identity 为 `/root/g3_round2_c_recheck`。完整原始结论保存在
`g3-formation/internal/C2-adversarial-audit.md`。

C 没有用人数或绿灯代替证据。首个 B 快照已有 `25/25 PASS` 且 preflight 为绿，但 C 与
根会话分别发现：

```text
runner parse owner stdout
→ canonical object hash
→ re-serialize to worker
```

因此当时的 equality 不是 owner stdout raw bytes equality。这个
`C2-P0-02 / PRE-WIRE-FIX` 红灯被保留；B 改成 raw JSONL 原样转发后，C 才追加
post-wire recheck。

A/B/C 都属于同一 Codex CLI、同一模型家族与同一工作区。职责隔离增加了失败路径，
不构成外部实验室或现实主体证据。

## 承重红灯与实际修复

### 1. owner / worker / scorer 同 truth surface

旧状态：

- `FormationExecutionService` import 并持有 `OwnerService`；
- runner 同进程直接构造 `OwnerService`、`FormationScorer`；
- scorer 可重建 owner truth，worker 可反射 private/scorer/runner。

修复：

```text
owner endpoint PID
  ↕ raw JSONL
runner byte broker PID
  ↕ exact forwarded JSONL
public worker PID

worker + owner exit
→ transcript hash frozen
→ grader PID starts
```

worker cwd 为 `/private/tmp`，环境是最小白名单。Python audit-hook allowlist 只允许
capsule 及 `worker_process / execution_service / protocol / models / canonical /
__init__` 源码与对应 pyc；private、owner、scorer、runner、tests、internal、outputs 和
cohort final 均拒绝。

这是当前固定 Python worker 的可检查本地隔离，不是抵抗任意 native syscall 或恶意本机
进程的 OS/硬件安全边界。

### 2. parsed object equality 冒充 actual transmitted bytes

首个 `25/25` 快照仍先 parse/re-serialize，C 将其判为 P0。

最终实现用 `read_raw_message()` 捕获 owner stdout 原始 JSONL line，并用
`write_raw_message()` 原样写入 worker stdin。每条 raw line 分别保留：

- owner-emitted SHA-256 list；
- broker-forwarded SHA-256 list；
- worker-consumed SHA-256 list；
- 三方 stream hash。

`WIRE_VARIANT` 刻意改变 whitespace 与 key order，最终仍逐字节一致，排除了
canonical encoding 偶然相等。

当前 16/16 raw runs：

```text
owner_emitted_equals_forwarded = true
transmitted_equals_consumed    = true
worker_pid != owner_pid        = true
```

### 3. owner response 绑定不足

最终 response 使用 public packet 固定的 Ed25519 verification key，绑定：

- owner identity；
- owner state version、policy version 与 policy head；
- episode、Q、object/target 与 operation；
- request hash、request nonce、proposal hash 与 response nonce；
- issued-at、request sent-at 与 response deadline；
- payload、response hash 与 owner authenticator。

这只证明本地 fixture owner endpoint 对 exact bytes 的 act，不证明现实 identity、
理解、法律 Authority 或合同充分性。

### 4. scorer 越过 G3 line-local 权限

旧 scorer 输出：

```text
exact_task_success
correct_resolution
recovery_to_value
```

最终 G3 component 不再输出这些字段，也不输出或透传
`Authority / Effect / Acceptance / Settlement` 及预注册同义 verdict。private fixture
中的 `resolution_requirement` 已删除。

真实 integration preflight 会递归扫描最终 G3 body；当前返回：

```json
{
  "preflight_status": "QUALIFIED_COMPONENT_OUTPUTS",
  "contract_score_status": "CONTRACT_SCORE_NOT_COMPUTED",
  "rejections": []
}
```

另有 canonical + synonym key/value-label scan，当前零命中。

### 5. E2 伪 remove 与旁路

E2 baseline 与 remove/reverse 使用相同 frozen S0。S0 绑定：

- public bytes；
- executable kernel 与 closed operator registry；
- owner routing、state/policy versions/heads；
- scripted response snapshot；
- budget、horizon 与 clock seed。

`REMOVE_FORMATION_OPERATOR` 是 S0 外 intervention delta。最终 remove run：

```text
matching executable registry ids = []
proposal count                    = 0
owner sign request count          = 0
token/delegation formed count     = 0
target submit count               = 0
target readback count             = 0
terminal                          = NO_EXECUTABLE_RESOURCE
```

源码只保留一个 formation owner-request dispatch site；当前 closed registry 内未观察到
alias、fallback、direct-call 或 descendant-token 旁路。这个结论只适用于冻结的封闭
worker artifact；开放插件/动态 action inventory 不在证明范围内。

### 6. E4 伪 recovery

E4 initial read 只返回随后被 revoke 的 primary。alternative 只在 revoke 后的独立
rediscovery response 中出现。G3 保留：

- revocation 与 rediscovery 顺序；
- alternative-specific proposal；
- resource/operation submit-readback binding；
- deadline、功率/时长、安全与 no-other-target observation；
- O_Q/O_V owner-outcome response observation。

以下六个单点变体均不能形成 bounded witness：

1. 没有 rediscovery response；
2. wrong submit/readback operation；
3. deadline miss；
4. unsafe readback；
5. O_Q refusal；
6. wrong target readback。

G3 只报告 post-revoke bounded reachability，不报告 recovery-to-value、正确解决或合同
成功。

## 实际对抗结果

### owner response：14/14 fail closed

| fault | rejection |
|---|---|
| transplanted episode | `OWNER_EPISODE_TRANSPLANT` |
| stale issued-at | `OWNER_RESPONSE_STALE` |
| wrong owner | `OWNER_IDENTITY_MISMATCH` |
| stale state version | `OWNER_STATE_VERSION_STALE` |
| stale policy version | `OWNER_POLICY_VERSION_STALE` |
| stale policy head | `OWNER_POLICY_HEAD_STALE` |
| wrong Q | `OWNER_Q_TRANSPLANT` |
| wrong target | `OWNER_WRONG_TARGET` |
| wrong operation | `OWNER_OPERATION_TRANSPLANT` |
| wrong request hash | `OWNER_REQUEST_TRANSPLANT` |
| wrong request nonce | `OWNER_REQUEST_NONCE_TRANSPLANT` |
| wrong proposal hash | `OWNER_PROPOSAL_TRANSPLANT` |
| payload tamper | `OWNER_RESPONSE_AUTHENTICATOR_INVALID` |
| tamper + recompute bare hash | `OWNER_RESPONSE_AUTHENTICATOR_INVALID` |

14/14 都在 token formation、target submit 与 target readback 前停止。

### reflection / closure

实际 probes 拒绝读取或导入：

- `private/owner_truth.json`；
- owner/scorer/runner source；
- runner pyc；
- outputs/report；
- tests/internal；
- cohort `G3-final.md`。

公开 packet 中加入 private path、expected path、grader/scorer 等诱饵后，worker core
projection 不变。相反 grader input 只改变 grader 输出，不改变已经冻结的 worker/owner
transcript。

### task、remove、E4 与 Unknown

- controller C7→C8：`TASK_CHANGE / CONTROLLER_SUBSTITUTION / INVALID`；
- wrong target：bounded witness false；
- remove：同 exact S0，formation/submit 全零；
- E4 六个 false-recovery 变体：6/6 bounded witness false；
- open inventory：closure、physical、measurable 保持 `UNKNOWN`；
- 11/11 line evidence 的 branch/safety/terminal robustness 都为 `UNKNOWN`；
- E2 interventions 不计入 robust denominator。

## 验证数字

根会话在正确 cwd 实际运行：

```text
py_compile run.py worker_capsule.py formation/*.py tests/*.py
  PASS

python3 run.py
  PASS
  stdout JSON parse PASS
  outputs/report.json parse PASS

python3 -W error::ResourceWarning -m unittest discover -s tests -v
  26/26 PASS

integration-preflight unittest
  14/14 PASS at root final readback

qualified-e1 with components.G3 = final report body
  QUALIFIED_COMPONENT_OUTPUTS
  CONTRACT_SCORE_NOT_COMPUTED
  rejections=[]

git diff --check -- g3-formation
  PASS
```

C 的冻结快照曾记录 preflight `13/13`；根最终 readback 时该共享 preflight suite 为
`14/14`。本任务没有修改 integration-preflight。

产物：

```text
line evidence receipts = 11
raw runs              = 16
report body sha256    = 445b016aac078be71458b71e6749387697c3203e958433cc7184f925735dfabf
report file sha256    = 957074a35a5547601e3495edd70a861b69cbbde777b15d27bb057f496d649c77
traces file sha256    = 1eafe1f2332f4f4d0726f73ec348015f88e69c48a48515112a8d7b9f8b3df7c8
```

## 可进入 integration 的精确 envelope

进入 integration 的对象是 `outputs/report.json.body`，不是 raw trace、private grader
input 或任何合同评分。顶层严格为：

```text
schema_version = ce001-g3-line-envelope-v2
namespace = G3
qualification = QUALIFIED_COMPONENT_OUTPUT
evidence_level = LOCAL_SYNTHETIC_COMPONENT_MODEL
product_run_status = NOT_RUN
public_packet_sha256
private_grader_input_sha256
case_result_count = 11
raw_run_count = 16
line_evidence[]
separation
```

每个 `line_evidence[].body` 只含：

```text
C / N / E / T / V
opaque case_handle / episode_handle
path_class

reachability:
  physical / measurable / actual / robust

R:
  R_physical_exists
  R_measurable_exists
  R_actual
  R_branch_robust
  R_safety_robust
  R_terminal_robust

bounded_reachability_witness
post_revoke_observation
intervention_trace
robust_denominator
bindings
```

每个 receipt 另带 `body_sha256` 和 frozen-handoff `process_boundary`。允许的 path class 为：

```text
DIRECT_PATH
OLD_FULL_POLICY_CLOSURE
OLD_FULL_POLICY_NEW_TOKEN
MODEL_KERNEL_CHANGE
TASK_CHANGE
OPEN_INVENTORY_UNKNOWN
BOUNDED_UNREACHABLE
```

不在 integration envelope 中的内容：

```text
ExactTaskSuccess / CorrectResolution / RecoveryToValue
Authority / Effect / Acceptance / Settlement
上述字段的大小写、snake/camel 或同义 verdict
raw owner/target trace
private expected path/resolution
CE-001 contract score
```

future evaluator 必须从 G1–G7 精确绑定的 evidence 重新计算合同结果。

## 残余边界

当前仍不能支持：

1. physical/measurable 是独立现实 oracle 或 observation-history policy witness；当前仍是
   grader-side local scan；
2. 完整 response-family robustness；branch population 与 coverage proof 未冻结；
3. Python capsule 抵抗任意 native-code 恶意进程；
4. 本地 Ed25519 fixture key 等于现实 owner identity、理解或法律 Authority；
5. 真实成熟产品、真人 Principal、现实供电与物理 Effect；
6. 合同 Acceptance、Settlement、完整 response-family robustness；
7. G1–G7 完整 CE-001 episode、任一 arm 的完整解或候选独占必要性；
8. Problem、LineContract、MechanismProfile 或正式 claim 状态变化。

因此本轮最终状态是：

```text
G3_LOCAL_LINE_ENVELOPE = QUALIFIED_FOR_INTEGRATION_PREFLIGHT
G3_CONTRACT_VERDICT = NOT AUTHORIZED / NOT COMPUTED
CE001_CONTRACT_SOLUTION = NOT_ESTABLISHED
```

本轮未修改 `research/NOW.md`、`PROGRAM.md`、CE-001 contract、Problem、LineContract、
MechanismProfile 或 integration-preflight。
