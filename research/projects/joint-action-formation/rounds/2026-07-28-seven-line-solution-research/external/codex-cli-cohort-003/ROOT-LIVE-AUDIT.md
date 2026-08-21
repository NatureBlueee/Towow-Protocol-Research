# Cohort 003 根会话滚动审计

日期：2026-07-30  
状态：`RUNNING / PARTIAL / ROOT INTERPRETATION OVERRIDES CLI FINAL`

## G4

### 根复跑

- `python3 -m unittest discover -s tests -v`：`11/11 PASS`
- `python3 runner.py --self-test`：`SELF_TEST_PASS`
- private holdout hash 前后相同；
- E3A/E3B 的 ACK-loss、wrong-object readback、exact reconciliation 与当前 idempotent
  retry 路径可复现。

### 新红灯：Acceptance closure 可伪造

`OwnerTargetService._deliver_once()` 在产生 Effect 的同一个本地 service 内，直接为
`episode["acceptance_owners"]` 生成两个 `ACCEPT` record；没有 O_Q/O_V 的独立请求、
owner act、拒绝、版本变化或 readback。

根会话把 `acceptance_owners` 从 `["O_Q", "O_V"]` 改为 `["O_Q", "O_Q"]`，不改 worker，
实际返回：

```json
{"Y_acceptance": true, "acceptance_owners": ["O_Q", "O_Q"]}
```

原因是 `Y_acceptance = len(acceptance_records) == 2`，没有检查 exact required owner set、
唯一 issuer、Q/effect binding 或 owner provenance。

因此：

```text
G4_TIME_AND_RECONCILIATION_COMPONENT = POSITIVE_SCOPED
G4_INDEPENDENT_ACCEPTANCE = FAIL
CE001_ACCEPTANCE_CLOSURE = NOT_ESTABLISHED
```

### 新红灯：P1 resolution calibration 是 one-class

四个 private case 的 `p1_truth()["Y_resolution"]` 全部为 `True`，worker 也只对
`Y_resolution` 一律预测 `YES`。根会话实际读回：

```text
P1_resolution_truths = [True, True, True, True]
unique = [True]
```

所以 `TP=4` 只证明当前手写 family 没有 unresolved/incorrect-resolution 负例，不能支持
calibration、区分力或一般 false-reliance 判断。

### 边界：matched twin

`matched_no_interaction_effects` 的 twin 直接在没有 reservation/commit 的状态调用
`submit_operation`，由 `_valid_attempt()` 必然拒绝。`interaction_effect_delta=+3` 可以保留为
“当前 simulator 中合法前置步骤是 Effect 的必要条件”，不能保留为 competing method 的
因果优势或完整 interaction 价值。

### 下一门

- Acceptance 必须由独立 O_Q/O_V owner service 分别行动并验 exact owner set；
- 加入 effect happened 但 owner 拒绝、重复同一 owner、wrong episode/Q/effect、
  stale acceptance 和一个真正 unresolved resolution 负例；
- 只有修复后，G4 输出才可进入 CE-001 的 Acceptance 与 calibration 聚合。

## 跨线 integration preflight

入口：
[`../../experiments/wave-012-ce001-power-restoration/integration-preflight/README.md`](../../experiments/wave-012-ce001-power-restoration/integration-preflight/README.md)

### 根复跑

- `unittest discover`：`12/12 PASS`；
- `qualified-e1.json`：返回 `QUALIFIED_COMPONENT_OUTPUTS`；
- `negative-duplicate-acceptance.json`：退出码 `2`，同时返回
  `DUPLICATE_ACCEPTANCE_OWNER` 与 `ACCEPTANCE_OWNER_SET_MISMATCH`；
- 正例与负例均保持 `CONTRACT_SCORE_NOT_COMPUTED`，没有生成
  `ExactTaskSuccess / CorrectResolution / RecoveryToValue`。

### 当前能阻断什么

- G1–G7 组件以同名合同字段直接宣称 episode 成功；
- `SIMULATED_MULTI_OWNER` 冒充独立 owner；
- 重复 O_Q 或 O_V 冒充双 owner Acceptance；
- G5 Authority receipt 只被记录、没有由 G6 target 明确消费；
- Effect 未绑定 frozen `Q@v1 / CircuitC7 / operation / target`；
- O_P finality 复用其他 owner source，或由 Acceptance object 派生；
- E6 source/target runtime、process 或 state boundary 未分离，旧 epoch 没有实际重启后
  被 fence，或 lineage/recovery 缺项。

### 仍然不能证明什么

预检只检查 envelope 中声明的标识、绑定和结构。不同的 `state_source_id`、
`act_source_id`、`process_id` 或 receipt hash 仍可能由同一 fixture、controller 或进程伪造；
`consumed_by_target=true` 也仍需要 target-native 原始事件和独立 readback 才能变成事实证据。
因此它只是 fail-closed admission gate，不是独立来源证明、真实产品运行或 CE-001
合同 evaluator。

```text
INTEGRATION_PREFLIGHT = POSITIVE_SCOPED
CONTRACT_FIELD_PASSTHROUGH = BLOCKED_BY_CURRENT_FIXTURES
STRUCTURAL_OWNER_SEPARATION = CHECKED
ACTUAL_OWNER_INDEPENDENCE = NOT_ESTABLISHED
CE001_CONTRACT_SCORE = NOT_COMPUTED
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## G1 第三轮最终返回与根复跑

G1 writer 已写出 `G1-fix2-final.md`。根会话在最终 source 上重新运行并核对冻结文件：

```text
unittest = 35/35 PASS
frozen bytes = 1,449,446
frozen sha256 = a3f908e7199d0475d09bd00268bd6074a0cdc31d994eb2c7772cfee17aa8081f
manifest = valid / mismatches=[]
```

当前实际建立的是 actual `Popen.pid`、controller-assigned owner source/state/process
instance、worker instance 与 exact raw relay 的 current-run binding；四类来源错配在转发
或评价前 fail closed，G1 line envelope 只保留
`CANDIDATE_NOT_COMMITMENT` 等 G1-local 语义。

owner records/operators 仍由 controller 通过 `OWNER_INIT` 写入 child，因此 separate process
不等于 independent fact authority。`RED_NOT_ISOLATED` 也仍保留。

```text
G1_CONTROLLER_OBSERVED_CHILD_PID_BINDING = POSITIVE_SCOPED
G1_CONTROLLER_ASSIGNED_LAUNCH_INSTANCE_BINDING = POSITIVE_SCOPED
G1_EXACT_RAW_BYTE_RELAY = POSITIVE_SCOPED
G1_LINE_LOCAL_CANDIDATE_ENVELOPE = POSITIVE_SCOPED
G1_INDEPENDENT_OWNER_TRUTH = NOT_ESTABLISHED
G1_REAL_DISCOVERY = NOT_ESTABLISHED
G1_HOSTILE_OS_ISOLATION = RED_NOT_ISOLATED
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## G1 第二轮返回：process/API 正向，owner origin 仍是 synthetic self-report

根会话复跑：

```text
unittest = 30/30 PASS
frozen manifest = valid / mismatches=[]
```

可保留的是 cooperative worker 的实际入站边界：独立 worker 默认只收到冻结 interface 与
owner response raw bytes；private canary、L/D、expected 和 evaluator 输入没有进入传输。
handoff 也仍明确是 `CANDIDATE_NOT_COMMITMENT`。

新边界：

- owner records/operators 由 controller 从同一个 synthetic World 注入 owner child；
- owner READY 与 event origin 主要用 child self-report PID，尚未全部与实际 `Popen.pid`
  绑定；
- worker PID attestation 同样需要 actual child identity 绑定；
- same-user 绝对路径可读已经诚实返回 `RED_NOT_ISOLATED`。

```text
G1_LOCAL_COOPERATIVE_PROCESS_API_BOUNDARY = POSITIVE_SCOPED
G1_RAW_BYTE_RELAY = POSITIVE_SCOPED
G1_INDEPENDENT_OWNER_TRUTH = NOT_ESTABLISHED
G1_OWNER_ORIGIN_PROOF = NOT_ESTABLISHED
G1_HOSTILE_OS_ISOLATION = FAIL
```

第三轮 `towow-w12-g1-fix2` 已启动，要求实际 PID binding 与 synthetic owner 明示。

## G2 第二轮返回：exact raw signature 成立，request/constitution/trust 仍有缺口

根会话复跑：

```text
unittest = 46/46 PASS
```

Ed25519 对 exact raw bytes、hash、manifest、owner、Q/object/revision/version/scope 的验证
可以保留；五 child 的实际 PID/public-key uniqueness gate 也确实执行。

新红灯：

1. child 自生成 key，endpoint/profile 来自 local test config；这只证明本地来源对 bytes
   签过名，不证明现实 owner/platform identity 或 Authority；
2. request verifier 没完整绑定 request `kind`、canonical request payload/hash、
   operation IDs、schema/freshness/ordinal；
3. 五 owner 全部 Unknown 时仍生成
   `DERIVED_SNAPSHOT_OF_VERIFIED_EXACT_BOUND_OWNER_EVIDENCE` RelationVersion；
4. T5 proof/readback 由同一个 self-configured platform process/profile 生成，
   `platform_native_scope_verified` 不能被解释为真实平台 applicability。

```text
G2_LOCAL_EPHEMERAL_KEY_EXACT_RAW_SIGNATURE = POSITIVE_SCOPED
G2_ACTUAL_CHILD_IDENTITY_UNIQUENESS = POSITIVE_SCOPED
G2_REQUEST_RESPONSE_EXACT_BINDING = INCOMPLETE
G2_ALL_UNKNOWN_RELATION_VERSION = OVERCLAIM
G2_REAL_OWNER_IDENTITY = NOT_ESTABLISHED
G2_REAL_PLATFORM_APPLICABILITY = NOT_ESTABLISHED
```

第三轮 `towow-w12-g2-fix2` 已启动。

## G4 第二轮返回：time/reconciliation 保留，Acceptance 仍不能进入集成

根会话复跑：

```text
unittest = 19/19 PASS
self-test = PASS
```

新的根级反例：

- O_Q/O_V 仍是同一 `OwnerTargetService` 内两个 Python 对象；相同 service id 也能闭合；
- provenance 只是公开可重算 hash；不调用 owner `issue_act` 也能构造两条 record 并使
  `Y_acceptance=true`；
- `PENDING / 0kW / wrong circuit / exact_reconciliation=false` 仍能使
  `Y_acceptance=true`；
- G4 object id 与 canonical integration object id 字面值不一致。

```text
G4_TIME_AND_RECONCILIATION_COMPONENT = POSITIVE_SCOPED
G4_EXPIRY_GATING = POSITIVE_SCOPED
G4_RESOLUTION_NEGATIVE_CASE = POSITIVE_SCOPED
G4_RESOLUTION_DISCRIMINATION = NOT_ESTABLISHED
G4_OWNER_SOURCE_INDEPENDENCE = FAIL_SIMULATED_MULTI_OWNER
G4_PROVENANCE_AUTHENTICITY = FAIL
G4_EXACT_Q_ACCEPTANCE = NOT_ESTABLISHED
G4_CONTRACT_OUTPUT_QUALIFICATION = REJECT
```

根会话还复现并修复了 integration preflight 的两处 fail-open：

- `Y_effect / Y_acceptance` 现在属于合同字段，不能由 G4 透传；
- 任意 `contract_*` 字段现在 fail closed，包括
  `contract_exact_task_success`。

preflight 当前为 `14/14 PASS`，合格 fixture 仍只返回
`CONTRACT_SCORE_NOT_COMPUTED`。第三轮 `towow-w12-g4-fix2` 已启动。

## G5 第二轮返回：local target gate 通过，独立边界复核运行中

根会话复跑：

```text
unittest = 13/13 PASS
runner --check = COMPLETE_LOCAL_COMPONENT_MODEL
race = 12/12
target-native negative gates = 14/14
```

当前可保留为可信 bootstrap、可靠 owner-event ingest、cooperative subprocess 和 shared
durable store 下的 target-native component。真实 Authority、bootstrap 合法性、
revoke withholding、跨故障域 migration 和 named product 仍未建立。独立第三轮
`towow-w12-g5-audit2` 正在复核 channel/target 同源、key rotation、withholding、
concurrent takeover 与 shared-store migration。

## G6 第二轮返回：五进程接口正向，line-local closure 被新反例击穿

根会话复跑：

```text
unittest = 54/54 PASS
runner = 8 cases / 8 correct-resolution labels / 6 local closure
```

五 owner process/state shard 与 current honest RPC bytes 是实际存在的局部能力；但独立复核
实际复现：

1. native O_E 没有 occurrence/target state，仅提供格式正确 response bytes 也能
   `EXACT_EFFECT_ACCEPTED_SETTLED`；
2. O_Q/O_V Acceptance response 跨 session 重放，新 owner ledger 为空仍可 closure；
3. recovery/target-state 两份同源 response 一起失真时，actual C8 仍 `POWERED@v1` 也能
   报 recovered；
4. O_P native obligation/phase ledger 为空时，两份同源 finality response 仍可 settle；
5. grader 明文位于同一目录/parent process，不构成 hostile blind evaluator；
6. raw G6 evaluation 仍含 `contract_*` 与 Acceptance/Settlement 字段，不能作为 qualified
   line envelope。

```text
G6_FIVE_PROCESS_INTERFACE_ISOLATION = POSITIVE_SCOPED
G6_HONEST_DIRECT_PATH_REGRESSION = 54/54 PASS
G6_EFFECT_NATIVE_STATE_BINDING = FAIL
G6_ACCEPTANCE_CURRENT_PROVENANCE = FAIL
G6_O_P_NATIVE_FINALITY_BINDING = FAIL
G6_RECOVERY_INDEPENDENT_READBACK = FAIL
G6_GRADER_BLINDNESS = NOT_ESTABLISHED
G6_LINE_LOCAL_CLOSURE = UNSAFE_FALSE_POSITIVE
G6_CONTRACT_ADMISSIBILITY = UNQUALIFIED
```

第三轮 `towow-w12-g6-fix2` 已启动。G6 artifacts 在复跑时会含本次 PID/hash 并被重新生成；
它们当前只作运行副产物，不是 immutable candidate evidence。

## 2026-07-30 03:07 现场校正：窗口退出不等于 writer 完成

根会话只读检查系统进程后确认，G1/G2/G4/G6 的 tmux 窗口虽然已经消失，四个底层
`codex exec` 仍在运行并写入实验目录。G3/G5/G7 已返回。此时任何 final 文档、测试数或
artifact hash 只要早于当前 source mtime，就不能作为最新封口证据。

当前复核快照：

- G1 在修复 owner/worker 实际 PID 与 controller-assigned instance binding 后，独立复核
  取得 `35/35 PASS`；但 owner facts 仍明确来自
  `CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE`，且旧 `G1-fix-final.md` 已滞后；
- G2 已加入 requested kind、完整 raw request/payload、operation IDs、endpoint、ordinal、
  nonce、30 秒 freshness 与 in-run replay binding；全 Unknown 现在返回
  `DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION` 且不打开 downstream gate。独立复跑当前
  为 `44/46 PASS`，两项失败来自旧 artifacts/source hashes 和旧
  `evidence_boundaries` 期待未同步，因此 package 仍不具备集成资格。ephemeral self-key 与
  controller-visible profiles 仍只支持 local synthetic transport，不支持现实 owner identity；
- G3 当前源为 `26/26 PASS`，worker、owner endpoint、grader 的 cooperative process
  boundary、scripted exact-S0、Unknown 与 E2/E4 隔离可保留；单一 owner endpoint/fixture/
  signing seed 不支持 per-owner source independence，`G3-final.md` 的 `18/18` 已滞后；
- G4 第三轮 writer 仍在改动。旧 `19/19` 不关闭 provenance、exact-Q Acceptance 和 source
  independence 缺口；integration preflight 当前独立复跑为 `14/14 PASS`，并实际拒绝
  `Y_effect/Y_acceptance` 透传；
- G5 当前源 `13/13 PASS`，可保留 target-native signed receipt gate、12/12 本地 race、
  14/14 target gate 与 same-shared-store restart；bootstrap、reliable ingest、lawful
  Authority、stale separate store 和 cross-domain migration 未建立。runner 会覆盖
  artifacts，旧 final hash 已失去跨运行冻结意义；
- G6 第三轮新增 current request、native ledger 与 frozen evidence closure 测试后，根会话
  在当前中间态实跑 `72 tests`，结果为 `21 failures + 1 error`。旧 `54/54` 已被推翻；
  当前状态是 `REOPENED / NOT_INTEGRATION_QUALIFIED`，等待 writer 收敛后按新 hash 重跑；
- G7 当前源独立复跑 `58/58 PASS`。可保留 local receipt consumption、dependency/capsule
  checks 与外部 durable fence 的局部实现证据；`hidden_pair=NOT_CONSTRUCTED`、
  `safety_liveness_frontier=NOT_RUN`、现实产品与跨产品 portability 仍未建立。

这次现场校正再次确认：会话窗口、final 文档、旧测试总数和生成 artifact 都不是稳定事实源；
最新 source hash、实际仍存活的 writer、稳定后根复跑和独立边界样例共同决定当前状态。

## G4 第三轮最终返回与根复跑

G4 writer 已于 03:20 写出 `G4-fix2-final.md`。根会话在最终 source 上重新运行：

```text
unittest = 35/35 PASS
runner --self-test = SELF_TEST_PASS
integration preflight = 14/14 PASS
```

当前可保留的增量是：O_E/O_Q/O_V 三个实际 child process 分别生成进程内 Ed25519 key，
actual `Popen.pid`、process/service/state/act source 与 exact bytes 被 current-run pin；
owner request 前后都检查 `SUCCEEDED`、C7、3kW 容差、45 分钟、deadline、exact
reconciliation 与 O_E provenance；G4 compact output 不再含 `Y_*` 或合同级字段，并通过
当前结构预检。

边界仍然不变：三个 child 的初始 synthetic state 仍由同一研究 harness/world author
配置；这不证明现实 owner identity、法律 Authority、真实 Effect 或真人 Acceptance。
P1 当前只有 `TP=9/FP=1/TN=0/FN=0`，因此一般 reliance calibration 仍未建立。

```text
G4_LOCAL_PROCESS_SIGNED_OWNER_ACT_GATE = POSITIVE_SCOPED
G4_EXACT_TARGET_RECONCILIATION_PRE_ACT_GATE = POSITIVE_SCOPED
G4_LINE_LOCAL_PREFLIGHT_QUALIFICATION = POSITIVE_SCOPED
G4_REAL_OWNER_ACT = NOT_RUN
G4_REAL_EFFECT = NOT_ESTABLISHED
G4_REAL_ACCEPTANCE = NOT_ESTABLISHED
G4_GENERAL_CALIBRATION = NOT_ESTABLISHED
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## G2 第三轮最终返回与根复跑

G2 writer 已于 03:28 写出 `G2-fix2-final.md`。根会话在最终 source 上串行复跑：

```text
unittest = 67/67 PASS
two full reruns = semantic projection equal
signed receipts = 256
actual child process/key instances = 62/62 unique
```

当前可保留的是 exact requested kind、canonical request payload/hash、endpoint、
operation IDs、schema、ordinal、nonce、30 秒 freshness、current process/key/source
manifest 与 raw Ed25519 response 的同次运行绑定。全 Unknown 与 constitution 未闭合时，
输出保持 `DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION`，不打开
AUTHORIZE/ACTIVATE 或 Relation gate。

这仍是 controller 配置 profile、child 自生成临时 key 的本地合成传输。T5 只是
self-configured platform fixture 的同源断言，不能证明现实 PKI、owner/platform identity、
法律 Authority、真实 Effect、Acceptance 或 Settlement。

```text
G2_EXACT_CURRENT_REQUEST_RESPONSE_BINDING = POSITIVE_SCOPED
G2_UNKNOWN_AND_CONSTITUTION_GATE = POSITIVE_SCOPED
G2_SYNTHETIC_RELATION_SNAPSHOT = QUALIFIED_LINE_LOCAL_ONLY
G2_REAL_OWNER_IDENTITY = NOT_ESTABLISHED
G2_REAL_PLATFORM_APPLICABILITY = NOT_ESTABLISHED
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## G6 第三轮最终返回、根复跑与跨线导出反例

G6 writer 已于 03:28 写出 `G6-fix2-final.md`。根会话在稳定 source 上复跑 writer 最终版
得到 `78/78 PASS`；随后新增五项跨线导出测试，全量为：

```text
unittest = 83/83 PASS
runner = 8/8 local resolution labels
G6 line-local closure = 6/8
integration export tests = 5/5 PASS
```

current request/session/native ledger/TraceClosure 的修复确实阻断了已测跨运行旧状态、无 native
occurrence 的格式正确 response、Acceptance/O_P finality 脱离当前 owner ledger、
recovery/readback 与 actual target state 脱离，以及 plan/result/trace closure 替换。
这是 G6 的正向局部能力。

但根审计还发现 writer final 的“只输出 G6-local 字段”描述与实际 artifact 不一致：
`artifacts/e2e-results.json` 仍有 18 个
`contract_exact_task_success` / `correct_resolution` 顶层或逐 record 字段。即使字段值为
`NOT_COMPUTED_BY_G6`，字段身份仍越过 line boundary，raw report 不能进入 integration
preflight。

根会话因此没有删除内部 diagnostic，而是增加严格的现有接口 adapter：

```text
adapter = g6-effect/integration_export.py
artifact = g6-effect/artifacts/integration-fragment.json
artifact sha256 = f8277c8f863a2e0a3a925a941403a0e6e932b22f291e047d2ad3e7defb85787e
records = 8
line-local closed = 6
contract-field passthrough = 0
```

adapter 只导出 source report digest、每 case 的 G6-local gate、plan/result/trace digest、
current session/process 与 native ledger heads/lengths，并显式保留真实产品、生产 target、
真人 owner act、付款 finality、hostile grader blindness 与跨线 score 未建立。

新的负结果不能抹掉：

- 把该 fragment 作为附加的 G6 line-local evidence 放入完整合成 envelope，preflight 通过且
  仍返回 `CONTRACT_SCORE_NOT_COMPUTED`；
- 用 fragment 直接替代 CE-001 G6 integration object，则按预期因缺少逐 episode
  Authority consumption、exact Effect binding、Acceptance closure 与 O_P finality
  integration binding 被拒绝；
- 因而 adapter 已解决“内部 diagnostic 越权污染跨线判断”，但没有解决“完整集成对象构造”。
  不能为了得到绿灯把旧 synthetic integration 字段伪装成实际 G6 输出。

```text
G6_CURRENT_NATIVE_SOURCE_STATE_BINDING = POSITIVE_SCOPED
G6_FROZEN_TRACE_CLOSURE = POSITIVE_SCOPED
G6_RAW_REPORT_INTEGRATION_ADMISSIBILITY = REJECT_CONTRACT_FIELD_PASSTHROUGH
G6_CLEAN_LINE_LOCAL_ADAPTER = POSITIVE_SCOPED
G6_DIRECT_CE001_INTEGRATION_REPLACEMENT = REJECT_INCOMPLETE_BINDING
G6_REAL_EFFECT_ACCEPTANCE_SETTLEMENT = NOT_RUN
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## Cohort 003 稳定准入矩阵

截至本节写入时，七个主 writer 均已实际退出并返回；窗口消失与底层进程退出已经分开核对。
当前准入不是“七线完整解”，而是七个作用域各异的可组合输入：

| 线 | 稳定复跑 | 可保留能力 | 不能外推 |
|---|---:|---|---|
| G1 | 35/35 | actual child PID/source/state/instance + exact raw relay；synthetic `CANDIDATE_NOT_COMMITMENT` | independent owner truth、real discovery |
| G2 | 67/67 | exact current request/response + unresolved constitution gate | real identity、Authority、platform applicability |
| G3 | 26/26 | cooperative process boundary、exact S0/Unknown、E2–E4 isolation | per-owner source independence、完整 response family |
| G4 | 35/35 | process-signed owner-act + exact target reconciliation pre-act gate | real owner act、Effect、Acceptance、general calibration |
| G5 | 13/13 | target-native receipt gate、local race/saga/shared-store restart | lawful bootstrap/Authority、reliable ingest、cross-domain migration |
| G6 | 83/83 | current native source/state/trace closure；clean line-local adapter | raw report admission、complete episode binding、real Effect/Acceptance/Settlement |
| G7 | 58/58 | local receipt dependency/capsule/durable fence | hidden safety-liveness pair、production portability |

因此第三批的建设性结果不是“没有方案”，而是：多个成熟 primitive、确定性 controller、
进程接口、签名/哈希 binding、event/ledger、reconciliation、workflow recovery 与窄 adapter
已经解决七个清楚边界内的问题。剩余承重缺口是把这些异质输入绑定到同一个冻结 episode，
由独立 evaluator 重算完整任务，而不是让各线自报合同答案。

```text
SEVEN_LINE_WRITERS_RETURNED = TRUE
SEVEN_LINE_LOCAL_INPUTS = QUALIFIED_WITH_EXPLICIT_SCOPE
FULL_G1_TO_G7_ARM_RUNNER = NOT_IMPLEMENTED
INDEPENDENT_CE001_CONTRACT_EVALUATOR = NOT_RUN
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
NEW_MECHANISM_NECESSITY = NOT_ESTABLISHED
```

## Actual artifact binding audit：七个局部输入不是一次共同运行

在七线稳定准入后，根会话没有继续把 hash 拼接成一个 synthetic envelope，而是增加了直接
读取当前实际 artifact 的 binding audit：

```text
path = experiments/wave-012-ce001-power-restoration/integration-binding-audit/
tests = 4/4 PASS
result = NOT_JOINABLE_CURRENT_ARTIFACTS
contract score = NOT_COMPUTED
report sha256 = 81e8f85cc198a1e7f574d4653e554e7ab8455d0d3f72ed61df515471cfc39f6b
```

检查器要求 G1–G7 对同一个 selected case 共同绑定：

```text
episode manifest / run root / Q version / canonical object / operation
owner registry / target registry / source artifact digest
G5 → G6 actual source link / G6 → G7 actual source link
```

当前实际失败不是抽象猜测：

- G4 只把 envelope 打到 runner stdout，没有可由另一个进程按 digest 消费的持久产物；
- 七线没有共同 `episode_manifest_sha256`、run root、selected case、owner registry 或
  target registry；
- C7 至少出现 `Venue-V:Circuit-C7`、`Venue-V/Circuit-C7`、
  `VenueV:CircuitC7`、`Circuit-C7` 四种本地坐标；显式 object adapter 可以解决 lexical
  差异，但不能证明背后 target state 相同；
- operation IDs 来自各线自己的 world/allocator；G6 一线就有
  `op-platform/op-extant/op-formed/...`，不能事后把不同 operation 强制别名为同一动作；
- G6 clean fragment 没有引用 G5 actual source artifact；
- G7 当前 E6 的一条 Effect、两条 Acceptance 与 finality hash 共四项，在 G6 actual report
  中全部不存在。

三项异质独立复核还实跑了当时 preflight 的假绿反例：

1. G1/G2/G4 可以来自三个不同 episode，当前 preflight 仍通过；
2. 六个 owner 的字符串 source id 不同，但 actual process/state boundary 相同，仍通过；
3. G5 receipt owner 集合错误、已过期或已撤销，只要自报 `current=true` 仍可能通过；
4. 同一 operation 有两次 occurrence、只提交其中一次，仍可能通过；
5. E6 foreign lineage 只替换表面 hash/self-report boolean，仍可能通过；
6. 把合格成功 envelope 的 case id 改成 `E5-IMPOSSIBLE-REFUSAL`，错误的
   Effect/Acceptance/finality 路径仍通过；真正正确的 zero-Effect bounded refusal 反而会被
   success-only schema 拒绝。

根会话随即把最确定、无需共同 world 才能判断的两类错误 fail closed：G1–G7 每个 component
现在都必须逐字段绑定顶层 selected episode；case id 必须属于八个冻结 case。当前只实现
E1 success closure 与 E6 migration-success structure，E0/E2/E3A/E3B/E4/E5 在对应
`SUCCESS / REFUSAL / UNKNOWN_OR_REOPEN` admission branch 完成前一律返回
`CASE_ADMISSION_NOT_IMPLEMENTED`，不能再用 E1 成功形状冒充 E5。

```text
integration preflight = 17/17 PASS
cross-episode component transplant = REJECTED
unknown case = REJECTED
E5 success-shaped envelope = FAIL_CLOSED_NOT_IMPLEMENTED
```

owner source receipt、Authority expiry/revocation、完整 occurrence range 与 E6 bytes/hash
重算仍必须由共同 world/runtime 和下一版 case-aware admission 关闭，不能靠给 fixture
增加更多自报字段解决。

因此当前 preflight 的准确身份进一步缩窄为：

```text
NAMESPACE_AND_SUCCESS_CLOSURE_STRUCTURAL_SUBGATE
NOT_SAME_EPISODE_PROOF
NOT_CASE_AWARE_ADMISSION
NOT_CONTRACT_EVALUATOR
```

这不要求创造新协议。下一步应优先把现有能力放进同一个冻结 world：

1. 由独立 world author 冻结 `EpisodeManifest`、case private/public bundle、clock、
   interventions、owner registry、target registry 与 operation allocator；
2. 每个 episode 只启动一组 O_Q/O_V/O_R/O_S/O_P/O_E 和唯一 target/O_E ledger；
3. G1–G4 改为读取共同 owner/target service 并输出 manifest-bound fragment；
4. 先闭合 G5 actual Authority receipts → G6 target consumption/native occurrence/
   O_Q+O_V Acceptance/O_P finality；
5. G7 只能迁移 G6 本次实际产生的 Effect/Acceptance/finality；
6. admission 按 `SUCCESS / REFUSAL / UNKNOWN_OR_REOPEN` 分支，E5 不再被 success-only
   schema 误判；
7. 先实现最接近当前成熟 primitive 的 A4 deterministic composition，再由不 import
   arm/line evaluator 的独立程序从 owner/target 原生日志重算八 case。

```text
CURRENT_COMPONENT_CONFORMANCE_EVIDENCE = POSITIVE_SCOPED
CURRENT_COMPOSED_ARM_EVIDENCE = NONE
ADAPTER_ONLY_POSTHOC_JOIN = REJECT
COMMON_WORLD_RUNTIME = NOT_IMPLEMENTED
CASE_AWARE_ADMISSION = NOT_IMPLEMENTED
INDEPENDENT_CONTRACT_EVALUATOR = NOT_IMPLEMENTED
```

## Wave 013：A4 共同世界 E1/E5 纵切

上一节的 `COMMON_WORLD_RUNTIME / INDEPENDENT_CONTRACT_EVALUATOR =
NOT_IMPLEMENTED` 是当时真实状态，现由 Wave 013 的有界结果更新，但只更新 E1/E5 与 A4。

当前实现将六个 process-private owner、唯一 Target 与独立 A4 放入同一
EpisodeManifest/world/run。实际运行：

```text
E1 run = ce001-run-98769954828719289991
E1 = SUCCEEDED / ExactTaskSuccess=true / CorrectResolution=true

E5 run = ce001-run-17131469301657144993
E5 = BOUNDED_REFUSAL / ExactTaskSuccess=false / CorrectResolution=true
```

这不是从 unit fixture 直接得到。实际碰撞依次经历：

- `INVALID_RUN`：service/manifest/freeze/seal 与 Target request 证据没有真正闭合；
- E1=`UNSAFE_EFFECT`、E5=`INVALID_REFUSAL`：Authority decision、consumed receipt 和
  non-delegable terminal 语义错误；
- 首次转绿后仍被独立攻击构造出 Target EXECUTE request 缺失、`execute_at=999` 和
  E5 truth 内有替代方案三个假阳性。
- 首批绿灯把 semantic case label 与 case-derived identifiers 直接交给 A4，只能证明
  label-visible branch closure；
- 第一轮去标签又保留了 full-manifest hash，E1/E5 两候选字典可恢复 case；spawn 还继承
  parent `--case` argv。这两批运行都保留为 development evidence，不是 blind evidence。

当前版本增加了
`Authority → EXECUTE request → occurrence/sensors → signed READBACK →
O_E/O_Q/O_V → O_P` 的内容父引用，Authority/deadline 使用 `execute_at_minute`，E5 使用
唯一 `alternative_oracle` 并逐项核对冻结 owner shard；重复 EXECUTE 为幂等。产物改为
`artifacts/<run_id>/`，evaluation 显式绑定 run/manifest/bundle/seal，旧 run 不再被覆盖。
当前 blind boundary 使用 evaluator-private full manifest 与独立随机
`arm_binding_token` 双视图；arm-facing IPC 不出现 case label 或 full manifest hash，
child argv 在 spawn 前被清理并由 visibility observation 回读。两个当前 run 的
two-candidate visible hash 命中均为 0。

```text
evaluator unit = 28/28 PASS
runtime + root actual acceptance = 13/13 PASS
COMMON_WORLD_RUNTIME_E1_E5_A4 = POSITIVE_SCOPED
INDEPENDENT_CONTRACT_EVALUATOR_E1_E5 = POSITIVE_SCOPED
LABEL_VISIBLE_AND_HASH_OR_ARGV_RECOVERABLE_GREENS = DEVELOPMENT_EVIDENCE_ONLY
CAUSAL_TWIN_A4_CAUSED_EFFECT = NOT_RUN
OTHER_SIX_CASES = NOT_RUN
OTHER_ARMS_AND_FAIR_BASELINES = NOT_RUN
REAL_AUTHORITY_EFFECT_ACCEPTANCE = NOT_RUN
SAME_USER_WHOLE_RUN_REWRITE_RESISTANCE = NOT_COVERED
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

完整 root acceptance 与证据边界见
`experiments/wave-013-ce001-common-world-a4/ROOT-ACCEPTANCE.md`。
