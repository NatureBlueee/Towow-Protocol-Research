# G3 第二轮内部 A：证据权威与 line-local 输出边界

日期：2026-07-30  
canonical identity：`/root/g3_round2_a_authority`  
角色：`A / EVIDENCE-AUTHORITY RECONSTRUCTION`  
处置：`ROOT RED LIGHTS CONFIRMED / IMPLEMENTATION BOUNDARY REBUILT / NO CODE CHANGED`

## 独立性声明

本文件是在实现 Agent B 作出本轮选择、攻击 Agent C 返回本轮结论之前形成的 A 侧规范。
我没有读取或依赖本轮 B/C 新增文件，也没有编辑实现、测试、fixture、private truth、outputs
或旧审计。本文只重建本轮 G3 的证据权威、进程间传输和输出边界；它不是对修复已经完成的
验收，也不以 Agent 数量作为证据。

## 已完整读取的输入

- 仓库根 `AGENTS.md`（用户消息亦提供了完整项目宪章）；
- `external/codex-cli-cohort-003/COMMON.md`；
- `external/codex-cli-cohort-003/G3-PROMPT.md`；
- `external/codex-cli-cohort-003/ROOT-LIVE-AUDIT.md`；
- `external/codex-cli-cohort-003/G3-final.md`；
- `experiments/wave-012-ce001-power-restoration/CE-001-CONTRACT.md`；
- cohort 002 的 `ROOT-ADVERSARIAL-AUDIT.md` 与 `SYNTHESIS.md`；
- `g3-formation/README.md`；
- 旧 `g3-formation/internal/C-adversarial-audit.md`，包括原始红灯与 post-fix recheck；
- `integration-preflight/README.md`，并核对了其 `preflight.py` 的字段扫描规则和
  `qualified-e1.json` 中 G3 的最小 envelope；
- 本轮开始时的 `models.py`、`owner_service.py`、`execution_service.py`、`scorer.py`、
  `runner.py` 接口，以及与这些接口直接相关的测试断言。

接口读取时的 SHA-256 快照为：

```text
execution_service.py e31f3202a994d6ac1b0540ffa4d9f209214615bb756deee9ff2a5b2ccce61b27
owner_service.py     da7b8b4932cb7e6baf1a83c65b7959189a2a16e1a4d3b38b07c7db8a306d13fc
scorer.py            d94c857b1b47ddf698ef5c85bf69318f6bc91943d02edc77c819434bc93782d7
runner.py            9acdb94c418af13fe902178cd638b84a5fdc29ff1023bda8df2dfad5fdd93638
models.py            68d2554bba5293fbe0d78dc48ee084ffa386cc5c319437771500ce72712f252c
```

这些 hash 只定位 A 实际观察的旧接口，不代表修复后代码或正确性。

## 直接观察

以下是对上述快照的直接观察，不是推断：

1. `runner.py` 同一 Python 进程同时读取 `fixtures/public_cases.json` 和
   `private/owner_truth.json`，随后直接构造 `OwnerService`、`FormationExecutionService`
   和 `FormationScorer`。
2. `FormationExecutionService` import 并持有一个 `OwnerService` 实例。冻结 S0 时直接从
   该实例取得 initial state、initial kernel、owner policy heads 和 scripted response
   family hash；运行时又直接调用同一实例的 read/sign/reserve/rediscover/execute、
   target readback 和两个 owner postcondition 方法。
3. `FormationScorer` 也 import 并自行构造 `OwnerService` 来获得 current anchors，同时
   持有 `case_truth`。所以“worker 实例与 scorer 实例不同”并没有建立可信传输边界；二者
   都可由同一 private fixture 和同一 owner 类重建事实。
4. scorer 直接输出 `exact_task_success`、`correct_resolution` 和
   `recovery_to_value`。它的 `_correct_resolution` 还直接读取 private
   `resolution_requirement`。这些是未来 CE-001 evaluator 的合同结论，不是 G3
   line-local 事实。
5. 当前 owner sign receipt 直接绑定 signer、proposal hash 和 policy head；proposal
   内间接含 task/Q/resource/scope。但 receipt 本身没有完整绑定 episode、Q、object、
   operation、request hash 和签发时刻。其他 owner response 也没有统一的可验证
   response envelope。
6. 当前 target readback 和两个 owner postcondition response 仍由 worker 持有的同一个
   `OwnerService` 产生；worker 没有只能看“线上实际返回 bytes”的可检查限制。
7. 当前 old closure、direct、physical、measurable 和完整 value 判断都由 scorer 扫描或
   复制 private truth。尤其 physical 是 private boolean，measurable 是 scripted truth
   scan；它们不是独立 sequence/policy witness。
8. integration preflight 会递归扫描组件内所有 key，去下划线并转小写后拒绝合同字段。
   当前扫描集合包括 exact-task success、correct resolution、recovery-to-value 以及
   Authority、Effect、Acceptance、Settlement 等合同级 key；G3 还单独禁止
   `contract_recovery`。
9. qualified fixture 给 G3 的最小形态只有 namespaced component、`C/N/E/T/V`
   coordinates 与 `bounded_reachability_witness`，没有任何合同评分。

## 推断

由以上观察可推出：

- 当前“private truth 没在 public packet 中”不足以证明 worker 没消费 private truth。
  当 worker 与 owner object 同进程、能直接调用 owner 方法并在 freeze 时读取 owner
  initial state/kernel/anchors 时，private truth 仍以 object capability 形式跨过边界。
- “owner service 与 scorer 是不同实例”同样不足以证明 owner truth 与 scorer truth
  分离；同一个类和同一份 private fixture可让两者 closure/reflection 到相同预期结构。
- owner response 的 Python dict、重新序列化后的对象或 controller 构造的等价 dict，
  都不能证明 worker 消费了 owner 实际传输 bytes。证据必须绑定传输前后的原始字节与
  request/response transcript。
- 一条 E4 trace满足 deadline、operation、安全约束并收到了 O_Q/O_V 响应，最多证明当前
  冻结局部环境中存在一条 post-revoke 可达路径；是否完成 CE-001 任务仍必须由未来独立
  evaluator 从七线证据重算。

## 本轮必须建立的证据权威

### 1. 三个运行域

至少形成以下三个可检查运行域；subprocess 是当前最清晰实现：

```text
owner process
  private world/state/policy
  request verifier + transition function
  emits exact response bytes

public worker process
  worker code + public packet bytes
  receives only owner endpoint response bytes
  emits request bytes + raw line-local transcript

grader process (worker transcript frozen后才启动)
  independent grader input + frozen transcript bytes
  emits only G3 line-local evidence
```

必要的不只是 PID 不同。worker import graph、argv、stdin、environment 和打开文件清单必须
能够检查：不得 import owner/scorer module，不得读取 `private/`、expected label、
expected path 或 resolution。owner/scorer 也不得以共享内存对象注入 worker。

controller 可以负责建管道、保存 bytes、等待退出和在 transcript 冻结后启动 grader；
controller 不能把 private fixture 派生值放进 worker argv、environment、public packet
或控制消息。

### 2. public worker 唯一可见输入

worker 可见输入闭包只能是：

1. 精确的 public packet bytes；
2. owner endpoint 对 worker 已发送 request bytes 返回的精确 response bytes；
3. worker 自身已发布的 executable registry/code 与确定性本地时钟接口，且其 hash 在
   本轮 S0 中冻结。

若 executable registry、预算、horizon 或 clock seed 会改变行为，它们必须属于 public
packet 或已发布 worker artifact/config；不能由 private owner object 的 accessor 注入。
worker 不应看到 semantic case ID、private manifest join、expected path、expected
resolution、grader input 或 scorer labels。

证据 transcript 必须逐消息保留：

```text
seq
sender_process_id / receiver_process_id
request_bytes_base64 or lossless byte reference
request_sha256
response_bytes_base64 or lossless byte reference
response_sha256
worker_consumed_response_sha256
parse_result or rejection
monotonic send/receive ordering
```

`worker_consumed_response_sha256` 必须等于 endpoint 实际写出的
`response_sha256`。重新构造“语义相同”的 dict 不算传输证明。

### 3. owner response 的最小绑定

每一次 owner response，无论 decision 是批准、拒绝、撤销、Unknown 或延迟，都必须以
canonical bytes 绑定：

```text
issuer_owner_id
owner_endpoint_id
owner_state_version
owner_policy_version
episode_id
q_version
object_id
operation
request_sha256
proposal_sha256  # 无 proposal 的请求显式为 null
decision
issued_at
request_nonce
response_nonce
response_body_sha256 / signature-or-local-authenticator
```

这里的签名或本地 authenticator 只证明当前合成 owner process 对 exact bytes 的签发；
不升级为法律权力、现实主体理解或合同结果。

验证顺序必须 fail closed：

- issuer/endpoint 与本请求所需 owner 不同：拒绝；
- episode、Q、object 或 operation 任一不同：wrong-target/transplant，拒绝；
- request/proposal hash 与实际发送 bytes 不同：tamper，拒绝；
- owner state/policy version 不是冻结请求时允许的 current version：stale，拒绝；
- `issued_at` 超出 deadline、expiry 或早于请求：拒绝；
- canonical body/hash/authenticator 不一致：tamper，拒绝；
- nonce 已使用或属于另一请求：replay/transplant，拒绝。

测试必须包含跨 case、跨 episode、跨 Q、跨 object、跨 operation、旧 policy、旧 state、
改 body 不改 hash、改 hash 不重签和 wrong issuer。只测试 proposal field mutation不够。

### 4. transcript 冻结后的 grader

worker 退出或到达有界终止点后，controller 先对完整 transcript 计算 hash并封存；此后
owner 和 worker 都不能再接收 grader 输出。grader 才可读取：

- frozen public packet bytes/hash；
- frozen worker artifact/config hash；
- frozen raw request/response/transcript bytes/hash；
- 独立 grader input（只供 grader，不经 owner/worker通道）；
- owner response 的公开验证材料和本轮冻结版本。

grader 不得构造 `OwnerService`、调用 owner transition function或读取 owner 的
`expected_path` / `resolution_requirement` 来决定答案。private fixture 可以驱动 owner
process 的隐藏世界，也可以为 grader提供独立核验材料，但不能把 expected path/resolution
当作方法、owner response 或比较 label。closure 应从冻结 S0、公开 operator semantics 和
观察 transcript 计算；局部路径判断应返回 witness 或 Unknown，而不是“等于 expected”。

任何从 grader 回到 worker/owner 的 pipe、文件、环境变量、共享 tmp path 或 callback 都是
反向泄露，应由测试拒绝。

## G3 唯一可输出的 line-local 事实

G3 可进入 integration 的输出只描述 formation/reachability，不描述 CE-001 合同是否完成。
推荐 envelope：

```json
{
  "namespace": "G3",
  "qualification": "QUALIFIED_COMPONENT_OUTPUT",
  "evidence": {
    "coordinates": {
      "C": "SAT|UNSAT|UNKNOWN",
      "N": "NONE|EXTANT_ACTIVATED|NEW_TOKEN|UNKNOWN",
      "E": "SAME|CHANGED|UNKNOWN",
      "T": "INVARIANT|CONTROLLER_SUBSTITUTION|UNKNOWN",
      "V": "VALID|INVALID|UNKNOWN"
    },
    "path_relation": "DIRECT_PATH|OLD_FULL_POLICY_CLOSURE|OLD_FULL_POLICY_NEW_TOKEN|MODEL_KERNEL_CHANGE|TASK_CHANGE|OPEN_INVENTORY_UNKNOWN|BOUNDED_UNREACHABLE",
    "new_token_witness": {
      "status": "OBSERVED|NOT_OBSERVED|UNKNOWN",
      "request_sha256": "sha256:...",
      "owner_response_sha256": "sha256:...",
      "trace_sha256": "sha256:..."
    },
    "bounded_reachability_witness": {
      "status": "WITNESSED|NOT_WITNESSED|UNKNOWN",
      "operation_observation_sha256": "sha256:...",
      "target_observation_sha256": "sha256:...",
      "owner_postcondition_response_hashes": ["sha256:..."],
      "deadline_observation": "WITHIN_BOUND|OUTSIDE_BOUND|UNKNOWN",
      "safety_observation": "WITHIN_BOUND|OUTSIDE_BOUND|UNKNOWN"
    },
    "intervention_trace": {
      "frozen_s0_sha256": "sha256:...",
      "delta_sha256": "sha256:...",
      "removed_operator_ids": [],
      "owner_endpoint_call_hashes": [],
      "trace_sha256": "sha256:..."
    },
    "uncertainty": {
      "open_inventory": false,
      "complete_response_tree_frozen": false,
      "branch_robustness": "UNKNOWN",
      "independent_physical_witness": "NOT_ESTABLISHED",
      "independent_history_policy_witness": "NOT_ESTABLISHED"
    }
  }
}
```

上例中的 hash 必须能回读到保存的 raw bytes；仅填任意字符串不构成证据。若 preflight
未来收紧 schema，以其实际允许的严格子集为准。

### 禁止输出或透传

G3 component 内任何深度都不得出现下列合同字段、大小写/下划线变体或同义结论：

- `ExactTaskSuccess`、`CorrectResolution`、`RecoveryToValue`；
- `Authority`、`Effect`、`Acceptance`、`Settlement`；
- achievable/all-case coverage、unsafe/duplicate/wrong-object/unreconciled outcome、
  candidate-exclusive success、contract score/success、complete solution；
- `contract_recovery`、`task_completed`、`goal_satisfied`、`value_recovered`、
  `final_accepted`、`authorized` 等把 raw observation重新包装成同义合同判断的字段。

raw owner response、target observation和 operation observation可以按原始 bytes/hash提交，
但 G3 不能把它们命名或归纳为上述合同对象成立。未来 evaluator从 G1–G7 精确绑定的原始
证据重新计算合同结果。

## E2 remove/reverse 的可证要求

E2 baseline 与 intervention 必须从同一 frozen S0 credential重放。S0 至少绑定：

- public packet bytes/hash；
- worker artifact、executable operator registry 与 public config hash；
- owner endpoint identity及冻结 state/policy version；
- owner响应生成规则或本轮允许 response snapshot/family 的 hash；
- budget、horizon、clock/seed；
- case/episode/Q/object 坐标。

intervention 是 S0 之外的单独 delta，不能回写 S0 或换 owner fixture。

`REMOVE_FORMATION_OPERATOR` 只有同时满足以下条件才可形成局部移除证据：

1. 从 worker 实际 executable registry 删除 operator ID 与 executable callable；
2. 删除后 registry hash 与 baseline 不同，且 delta 精确绑定被删 bytes/hash；
3. worker 不能 import、反射、closure-capture 或通过 alias registry重新取得该 callable；
4. 所有 public action入口的 bounded call graph/registry enumeration 中，不存在执行同一
   owner request的替代 alias；
5. raw endpoint log 证明没有发送该 formation request，也没有调用等价 operation；
6. exact S0 的其他字段不变，失败不能由改 owner答复、换 policy、换 task或删资源造成。

第 4 项只能在冻结 worker artifact 与封闭 executable registry 内证明。若 action inventory
开放、动态 import/插件未被封死，结论必须降为 `UNKNOWN`，不能声称全局不存在另一路径。

四个 reverse intervention 也必须只改变 exact owner response，在相同 request 和 S0 上
重放；reverse bytes需满足统一 binding并由 transcript显示 worker确实消费。remove 与
reverse 是两种不同因果干预，不能用“都没走到结果”合并。

## E4 可达性证据范围

E4 必须保留以下按时间排序的原始观察：

1. primary 在 initial read中出现；
2. primary reservation response发生撤销；
3. 撤销后才发出新的 rediscovery request；
4. alternative 首次在该 post-revoke response中出现；
5. alternative-specific proposal/request及其 owner transmitted bytes；
6. exact resource/operation submit与 target readback bytes；
7. operation ID、resource/object、Q、deadline、功率/时长、安全/no-other-target等逐项
   observation；
8. O_Q 与 O_V 两个独立 owner endpoint 对 exact episode/Q/object/operation/target
   observation hash返回的原始 postcondition response bytes。

G3 可把这条序列报告为 `bounded_reachability_witness=WITNESSED` 和
`post_revoke_path_relation=REDISCOVERED`，并提交各段 hash。它不能报告“恢复到价值”、
“任务成功”或“合同已被接受”。独立 evaluator还必须结合其他六线重算，且可能因为
commit-time owner状态、target provenance、最终性或别线失败而拒绝。

deadline、operation、safety、wrong target或任一 owner response mutation必须使该局部
witness变为 `NOT_WITNESSED`/`INVALID`，而不是产生合同级 false值。

## 必须保留的区分与 Unknown

- `DIRECT_PATH`：S0 已有立即 executable path；不得强造 relation或 new token。
- `OLD_FULL_POLICY_CLOSURE`：准备与执行动作都在冻结旧 policy/kernel中。
- `OLD_FULL_POLICY_NEW_TOKEN`：旧 closure可为 `SAT`，但具体 token/delegation在 episode
  中首次形成；new token不自动等于 kernel change。
- `MODEL_KERNEL_CHANGE`：旧 closure为 `UNSAT`，随后安装新 executable operator。
- `TASK_CHANGE`：运行目标 hash偏离 frozen Q；只能报告 substitution/invalid，不能用新目标
  形成局部正例。
- `OPEN_INVENTORY_UNKNOWN`：有限 frontier耗尽不等于封闭全集 UNSAT；closure、
  physical/measurable存在性保持 `UNKNOWN`。
- 完整 allowed response tree 未冻结且没有 branch population/coverage proof时，所有分支
  robustness必须为 `UNKNOWN`。E2 五个 intervention不是 robustness denominator。
- physical存在性没有独立可重放 sequence witness时为 `NOT_ESTABLISHED/UNKNOWN`；
  measurable存在性没有 observation-history policy/tree witness时同样为
  `NOT_ESTABLISHED/UNKNOWN`，不能复制 private boolean或扫描预期 path升为 TRUE。

## 最小攻击/验收矩阵

| 风险 | 必须实际实施的攻击 | G3 局部预期 |
|---|---|---|
| reflection/closure | worker尝试 import owner/scorer、读 private path、inspect closure或继承 fd | 启动/访问失败，transcript记录拒绝 |
| owner response transplant | 把另一 episode/Q/object/operation的真实 owner bytes移植 | binding verifier拒绝 |
| stale | 重放旧 owner state/policy version或过期 issued_at | verifier拒绝 |
| tamper | 改 response body/hash/authenticator任一项 | verifier拒绝 |
| wrong target | request或 response中替换 object/operation/target | witness invalid |
| expected-path leak | private expected path/resolution放入 public packet、owner response、argv/env | test fail |
| grader backflow | grader输出经 pipe/file/env再次进入 worker/owner | test fail |
| pseudo remove | 只改 owner response、不删 executable operator | remove test fail |
| alias remove | 主 operator删掉但 alias/captured callable仍发同一请求 | remove test fail |
| pseudo E4 | alternative预置于 initial response或撤销前可见 | rediscovery witness invalid |
| contract passthrough | 扫描完整 G3 envelope的禁词/归一化变体 | preflight返回合格且无 passthrough拒绝 |
| incomplete tree | 单 trace或五个 intervention被当作全分支 robust | 必须保持 Unknown |

这些攻击需要保存原始输入、原始输出、退出码、PID/进程边界和未修改的 negative fixtures。
18/18 旧测试必须作为风险回归保留，但不是第二轮完成条件。

## 原始结论

```text
CURRENT_OWNER_WORKER_SCORER_TRANSPORT_BOUNDARY = FAIL
CURRENT_G3_CONTRACT_FIELD_BOUNDARY = FAIL
CURRENT_OWNER_RESPONSE_FULL_BINDING = FAIL
CURRENT_EXPECTED_RESOLUTION_ISOLATION = FAIL

REQUIRED_G3_OUTPUT =
  LINE_LOCAL FORMATION / REACHABILITY WITNESSES ONLY

E2_REMOVE_CLAIM =
  SUPPORTABLE ONLY INSIDE A FROZEN CLOSED EXECUTABLE REGISTRY

E4_POST_REVOKE_PATH =
  POTENTIALLY SUPPORTABLE AS BOUNDED REACHABILITY EVIDENCE
  NOT AS A CONTRACT OUTCOME

OPEN_INVENTORY =
  UNKNOWN

FULL RESPONSE-FAMILY ROBUSTNESS =
  NOT RUN / UNKNOWN

REAL PRODUCTS / REAL PRINCIPALS / LEGAL POWER /
PHYSICAL-WORLD OUTCOME / CONTRACT POSTCONDITION / FINALITY =
  NOT RUN OR NOT ESTABLISHED
```

## 本文件不能支持

本文件不能支持修复已实现、subprocess隔离已生效、owner bytes确实被消费、E2 remove已通过、
E4局部 witness已成立、integration preflight已通过或 CE-001任何结果。那些都需要 B 的
实现、C 的独立攻击及主会话对 raw transcript、tests和 preflight 的实际复跑。

它也不能支持真实产品、真人 Principal、法律 Authority、物理 Effect、完整 response-family
robustness、Acceptance、Settlement或 CE-001合同解；这些状态继续为
`NOT_RUN / NOT_ESTABLISHED`。
