# G3 round-2 internal C2 adversarial audit

日期：2026-07-30  
canonical identity：`/root/g3_round2_c_attacks`  
角色：第二轮内部 Agent C；独立攻击者，不实现 B2，不选择实现方案  
状态：`PRE-REGISTERED / IMPLEMENTATION UNREAD / ATTACK EXECUTION PENDING`

## 0. 独立性与输入封印

本节在读取本轮 B2 新增文件、A/B 本轮 return 文档或任何 B2 实现选择之前写成。预注册阶段
只完整读取了用户指定的七份既有材料：

| 输入 | SHA-256 |
|---|---|
| `external/codex-cli-cohort-003/COMMON.md` | `94ef0dcd806972be72e5575836a66c8fd91be43ee8e76d2a5892ade4f6bddef7` |
| `external/codex-cli-cohort-003/G3-PROMPT.md` | `c83447a5be79e9de34dfa910652f745277db2af6f4831e52546f4e58c1d59f86` |
| `external/codex-cli-cohort-003/ROOT-LIVE-AUDIT.md` | `780b9cefda4a04074d496071dfa5fb3e2d6eebc285a73ac53e8b4de25f51f5a6` |
| `external/codex-cli-cohort-003/G3-final.md` | `6096fb6e6d473e0f484a3965f8c9a2b31581d1310bb1383ea04d4a9765ee2bee` |
| `g3-formation/README.md` | `49810ca4c3025751c09f36b62e21a060941b20fdc432443f4d0f5fe53b701111` |
| `g3-formation/internal/C-adversarial-audit.md` | `008a2c866a3ac235837237e3b8ce5de109e5b5bbe15f072626087ca8893729f5` |
| `integration-preflight/README.md` | `37da7e4162713ccd064caae93f51c7e67b72843ef47321a8cd9bcc0ba554c44c` |

封印时刻：`2026-07-29T16:19:02Z`。

禁止作为 C2 方法输入：

- 本轮 A2/B2 的文件、消息、return 文档和实现说明；
- `private/owner_truth.json` 中的 expected path、expected resolution 或预选答案；
- B2 选择的进程协议、类名、字段名或测试结构；
- scorer 的私有 grader input 或集成 evaluator 的期待结果。

C2 可以在本节封印后读取当时仓库实现并做只读攻击，但不会根据 B2 的选择回改以下攻击目标、
成功预言机和严重度。若具体接口不同，只做机械 adapter；不改变攻击语义。

## 1. 冻结问题与判定边界

本轮不是证明 G3 正确，而是尝试证伪以下最小传输主张：

> public worker 的实际因果输入只有公开 packet 与 owner endpoint 实际传输的 response
> bytes；owner、worker 与 scorer/grader 之间存在可检查的进程和信息边界；G3 输出只包含
> line-local formation/reachability 证据，不能替未来 CE-001 evaluator 宣布合同成功。

攻击通过不能由测试人数、已有 18/18、类名、注释、PID 字符串或序列化字段数量推出。每项
必须由实际 mutation 的失败、进程/字节证据或 transcript 不变量支持。

预注册严重度：

- `P0`：成功攻击会让 worker 读取未传输 truth、接受错误 owner act、伪造 remove/recovery、
  或输出合同结论，阻断 integration；
- `P1`：不一定让当前 frozen case 直接变真，但破坏独立 grader、可审计边界或证据解释；
- `P2`：可观察性不足，暂不能区分“真实边界”与“同进程约定”。

## 2. 预注册攻击矩阵

### C2-P0-01：private truth reflection / closure 回读

攻击：

1. 递归检查 worker 入口的 import、closure/global、默认参数、对象属性、环境变量、cwd、
   argv 与启动 payload，搜索 private truth、scorer、runner、expected path/resolution 的
   可达引用；
2. 向公开 packet 注入 `private_path`、`owner_truth`、`expected_path`、`resolution`、
   `grader_input`、`scorer` 等诱饵，检查 worker 是否反射读取、动态 import 或透传；
3. 在只提供 public packet 与录制 owner response bytes 的隔离调用中重放；私有 fixture
   缺席或不可寻址时，worker 行为必须仍只由这两类 bytes 决定；
4. 对同一公开输入与同一 owner bytes 改写 private truth/grader input，worker transcript
   必须 bitwise invariant。

失败预言机：worker 进程读取/导入 private、scorer 或 runner；输出随未传输 private/grader
变化；packet 中的路径或对象诱饵能触发回读；owner response 不是唯一 owner 信息来源。

### C2-P0-02：实际 transmitted-bytes 边界

攻击：

1. 捕获 worker 启动请求、owner endpoint 原始 response bytes、解析后对象和 transcript
   hash，核对 worker 消费的恰是被记录 bytes，而不是共享 Python object/service；
2. 对 JSON key order/whitespace 做等义重编码，确认签名/response hash 的规范明确；对一个
   payload byte 做非等义 tamper，必须 fail closed；
3. 给共享对象在 owner 返回后、worker 消费前做内存 mutation 的等价攻击；若存在对象直传，
   视为没有 bytes boundary。

失败预言机：owner 与 worker 共享 service/object；记录 bytes 与实际消费内容不一致；tamper
仍可形成 token/operator/value trace；无法给出请求与 response 的原始 bytes/hash。

### C2-P0-03：owner-response transplant

以一份真实 owner response 为 donor，分别 transplant 到：

- 不同 owner identity；
- 不同 owner state version 或 policy version；
- 不同 episode；
- 不同 Q/version；
- 不同 object/resource；
- 不同 operation；
- 不同 request hash；
- 不同 proposal hash；
- 过期或早于有效窗口的 `issued_at`；
- 同 episode 的另一请求 nonce。

每个维度单独变异，避免一次多错无法定位。响应必须由 worker-side verifier 在消费前拒绝，
且拒绝发生后不得出现派生 token、delegation、operator、execute 或 reachability witness。

失败预言机：任一 transplant 被接受；仅 scorer 事后降分而 worker 已执行；重新计算本地 hash
即可把 donor 洗成合法 response。

### C2-P0-04：错误 target / object / operation

保持 owner identity 与签名形式不变，只把 target 从 frozen `Venue-V/Circuit-C7` 改为
相邻 target，或在 request、proposal、owner response、execute、readback 中制造
object/operation 的单点错配。

失败预言机：worker 执行错误 target；line-local envelope 仍给出 bounded reachability；
scorer 通过 task substitution 后的目标；producer 自报的 “exact/correct” 被当成证据。

### C2-P0-05：伪 remove 与同动作旁路

攻击不满足于 registry 中少一个名字：

1. 删除 formation operator 后，枚举 executable registry、alias、fallback、generic
   dispatch、直接 owner call 与 prebuilt-token 路径；
2. 以不同 opcode/name 调用同一语义动作；
3. 检查删除前后 owner request 数、response 数、派生 token/operator 事件以及 target act；
4. 检查旧 closure 或 descendant state 是否携带已形成 token 绕过 remove。

失败预言机：被删 operator 的语义动作仍可通过 alias/fallback/direct call 执行；remove
只改 owner 答案、scorer 标签或事件名；同一动作发生而测试只检查原 opcode 不出现。

### C2-P0-06：伪 recovery / 预埋 alternative

针对 E4 分别注入：

- alternative 在 revoke 前已经进入 packet、worker memory、ordered candidates 或 closure；
- revoke 后不发生独立 rediscovery request/response；
- rediscovery response transplant 自别的 episode/request；
- wrong operation 或 submit/readback mismatch；
- deadline 超时；
- safety/no-other-circuit/功率/时长 observation 缺失或错误；
- acceptance observation 缺失、重复 owner、wrong target 或 refusal。

失败预言机：上述任一情况仍产生名为 recovery、recovery-to-value、correct resolution 或同义
结论；“曾 revoke + 后来任意 effect”被当成恢复；G3 自己计算合同成功。

通过边界：E4 最多可输出 post-revoke rediscovery、完整 observation 与 bounded
reachability/intervention trace；合同成功留给未来独立 evaluator。

### C2-P0-07：合同字段直接透传

递归扫描 G3 envelope 的 key、value-label 与 metadata。以下字段无论大小写、snake/camel、
前后缀或 namespace 都不得由 G3 输出：

`ExactTaskSuccess`、`CorrectResolution`、`RecoveryToValue`、`Authority`、`Effect`、
`Acceptance`、`Settlement`。

同时把 G3 envelope 送入 integration preflight；若返回
`CONTRACT_FIELD_PASSTHROUGH`，即为本项失败。不得通过把禁词藏入 `details`、raw
classification 或兼容字段规避。

### C2-P0-08：合同结论同义词直通

预注册 normalization：key/value label 转小写，移除 `_-. /`，并匹配以下语义族：

- exact task success：`task_succeeded`、`goal_achieved`、`value_delivered`、
  `exact_value_obtained`；
- correct resolution：`resolved_correctly`、`valid_resolution`、`resolution_ok`；
- recovery to value：`recovered_value`、`recovery_success`、`restored_to_value`；
- Authority：`authorized`、`permission_valid`、`delegation_authority`；
- Effect：`effect_occurred`、`physical_effect`、`effect_exact`；
- Acceptance：`accepted`、`owner_accepted`、`acceptance_valid`；
- Settlement：`settled`、`finality_complete`、`settlement_valid`。

诱饵 owner response 会携带这些字段。worker 可以保留原始 opaque response bytes/hash，但
不得选择性复制、改名、聚合成 G3 结论。

失败预言机：禁用 canonical 字段后，以任一同义字段恢复相同合同含义；raw owner assertion
未经 provenance 标注和局部化即进入 envelope。

### C2-P0-09：scorer → worker/owner 反向泄漏

1. 冻结公开 packet 与 owner scripts，分别使用两份相反 grader input/scorer truth；
2. 比较 worker request bytes、owner response bytes、owner call sequence 与 frozen
   transcript hash；
3. 让 scorer 缺席、延迟启动或故意失败，worker/owner trace 必须先独立完成并冻结；
4. 搜索 worker/owner argv、env、stdin、import graph、IPC 与共享文件，确认没有 grader
   label、expected path 或评分坐标。

失败预言机：改变 grader input 会改变 worker/owner 行为；scorer 在 transcript freeze 前
运行；worker/owner import 或直接构造 scorer；scorer 结果写回 owner decision。

### C2-P1-10：worker / owner / scorer 进程边界真实性

记录实际 PID、parent PID、启动命令、stdin/stdout 协议、退出码与 transcript freeze
顺序。至少 worker 与 owner/scorer 不得处于同一 Python 对象图；scorer 只能在冻结后读取
独立 grader input。

失败预言机：仅用类名 “Service” 冒充边界；runner 同进程直接构造 OwnerService 或
FormationScorer；PID 字段由 fixture 自报而无实际进程。

### C2-P1-11：line-local envelope 正白名单

允许的结论语义只限：

- closure；
- new-token / operator formation observation；
- kernel/task coordinates；
- bounded reachability witness；
- intervention trace；
- uncertainty / Unknown；
- 原始、带来源的 operation/deadline/safety/owner-response observation。

要求仍能区分 direct、old closure、new token、model/kernel change、task substitution、
open inventory Unknown，以及完整 response tree 未冻结时 robust Unknown。白名单之外的
派生 episode 结论按 P0-07/P0-08 处理。

### C2-P1-12：private expected-path 方法污染

静态与动态检查 runner/worker/owner：private fixture 的 expected path/resolution 不能被用作
method、owner response、candidate order、fallback 或测试 oracle 输入。把 expected 字段删掉
或颠倒时，在相同 public/owner bytes 下 worker transcript 必须不变。

失败预言机：worker 依 expected path 选 operator/target；owner endpoint从 expected answer
合成响应；expected 字段只是改名后进入 public packet。

## 3. 预注册执行顺序

1. 先做静态边界图：进程、文件、IPC、public packet、owner bytes、grader input；
2. 再运行已有测试并保存原始命令、退出码和数字，但不以绿灯替代攻击；
3. 优先执行 C2-P0-01/02/03/09，确认 truth 与传输边界；
4. 执行 target、remove、recovery mutations；
5. 生成真实 G3 envelope，做 canonical + synonym scan，并实际调用 integration preflight；
6. 保留所有红灯，不因后续修复覆盖；post-fix 只追加复核。

所有 mutation 应在内存或 `/tmp` 隔离副本中完成。C2 不修改实现、tests、fixtures、
private truth 或 outputs；本轮唯一落盘文件是本审计。

## 4. 预注册原始结论

在实现未知阶段，历史 18/18 不能解除根审计红灯。进入 integration 的必要条件至少是：

```text
WORKER_OWNER_SCORER_PROCESS_BOUNDARY = ACTUALLY OBSERVED
WORKER_INPUT = PUBLIC_PACKET_BYTES + OWNER_RESPONSE_BYTES ONLY
OWNER_RESPONSE_TRANSPLANT = FAIL_CLOSED
WRONG_TARGET = FAIL_CLOSED
REMOVE_SEMANTIC_BYPASS = NOT_OBSERVED
E4 = LINE_LOCAL_REACHABILITY_EVIDENCE_ONLY
CONTRACT_FIELD_AND_SYNONYM_PASSTHROUGH = ABSENT
SCORER_REVERSE_LEAK = NOT_OBSERVED
ROBUST_COMPLETE_RESPONSE_TREE = NOT_RUN / UNKNOWN
REAL_PRODUCTS_PRINCIPAL_AUTHORITY_EFFECT = NOT_RUN / NOT_ESTABLISHED
CE001_CONTRACT_SOLUTION = NOT_ESTABLISHED
```

---

## 6. PRE-WIRE-FIX ROOT RED LIGHT

canonical identity：`/root/g3_round2_c_recheck`

本轮攻击矩阵由 `/root/g3_round2_c_attacks` 在不知道 B 的实现选择时预注册；post-fix
复核没有倒推修改攻击语义、失败预言机或严重度。

C 首个实现快照的 aggregate SHA-256 为：

```text
662b9cc5952929bf6599932bd34c9b0a62b19e0b5d16f76673eac66a1d97132c
```

该快照当时已有 `25/25 PASS`，integration preflight 也为绿，但这两项绿灯不能支持
raw-bytes 主张。runner 已经 parse owner stdout，再 re-serialize；比较的是 canonical
object hash，而不是 owner stdout 实际 JSONL raw bytes。因此：

```text
OWNER STDOUT RAW BYTES == WORKER CONSUMED BYTES = NOT ESTABLISHED
C2-P0-02 ACTUAL WIRE-BYTES BOUNDARY             = RED
ROOT INTEGRATION DECISION                        = BLOCK
```

这个 P0 不是 C 的单方措辞判断，而是 C 与 root 独立确认的根红灯。25/25、preflight
绿灯以及解析后对象相等，都不能排除中间层对 whitespace、key order 或其他 wire
表示的改写。

## 7. POST-WIRE-FIX INDEPENDENT RECHECK

canonical identity：`/root/g3_round2_c_recheck`

root/B 在 C 的首个快照后修复 wire path；最终实现对 owner stdout raw JSONL
逐字节转发。复核逐行比较三方记录，owner-emitted、broker-forwarded 与
worker-consumed 的 raw line、SHA-256 list 均一致；`WIRE_VARIANT` 明确覆盖了
非 canonical whitespace 与 key order，而不是依赖 canonical encoder 偶然产生相同
bytes。private truth 中的 expected resolution 已删除。

最终独立复核结果：

```text
G3 TESTS = 26/26 PASS
OWNER RAW JSONL = BYTE-EXACT FORWARDED
OWNER / BROKER / WORKER LINE HASH LISTS = IDENTICAL
WIRE_VARIANT WHITESPACE + KEY ORDER = COVERED
```

owner response 的 14 个错误维度全部在派生 token、target submit 与 target readback
之前 fail closed。worker workspace allowlist 拒绝读取或导入
`private`、`scorer`、`runner`、`tests`、`internal`、`outputs`、cohort final 以及这些
受限来源对应的 `.pyc`。

E2 remove 后，registry match、proposal、owner sign、token formation、target submit 与
target readback 均为 `0`，没有 alias、fallback、旧 token 或 direct-call 旁路证据。

E4 的 alternative 只在 revoke 后的独立 rediscovery 中出现；envelope 保留有来源的
operation、deadline、safety 与 owner-outcome observations。它只形成当前 frozen
coordinates 下的 post-revoke bounded reachability evidence，不形成恢复成功、正确解决
或价值兑现的合同结论。

最终 G3 envelope 的 canonical contract-field scan 与 synonym scan 都无命中。真实
integration preflight 返回：

```text
preflight_status=QUALIFIED_COMPONENT_OUTPUTS
contract_score_status=CONTRACT_SCORE_NOT_COMPUTED
rejection_codes=[]
canonical_or_synonym_hits=[]
```

这些结果关闭当前 local G3 envelope 的已预注册 C2 P0，但不扩大现实主张。以下边界保持：

```text
ROBUST_COMPLETE_RESPONSE_TREE = NOT_RUN / UNKNOWN
REAL_PRODUCTS = NOT_RUN
REAL_PRINCIPAL = NOT_RUN
LEGAL_AUTHORITY = NOT_ESTABLISHED
PHYSICAL_EFFECT = NOT_ESTABLISHED
REAL_CONTRACT_POSTCONDITION = NOT_ESTABLISHED
CE001_CONTRACT_SOLUTION = NOT_ESTABLISHED
```

由于 root/B 在 C 首个快照后修复了 wire 源码，最终源码 hash 与首个 aggregate hash
不同。最终复核应以最终交付文件中的逐文件 hash 表为准；本节不伪造或补写一个没有实际
计算的最终 aggregate hash。

预注册处置：`BLOCK UNTIL ACTUAL ATTACKS RUN`。

---

## 5. POST-FIX 独立复核

复核日期：2026-07-30  
canonical identity：`/root/g3_round2_c_recheck`  
角色：C2 post-fix 独立复核；未读取 A2/B2 return 文档  
修改边界：未修改实现、tests 或 fixture；只追加本 C2 文档  
最终处置：`LOCAL QUALITY GATES PASSED / INTEGRATION ENVELOPE QUALIFIED / REAL-WORLD AND ROBUST CLAIMS REMAIN UNKNOWN`

本节不覆盖第 0–4 节的预注册身份、攻击目标和原始结论。复核先遇到一个真实
pre-wire 红灯，B 修复后重新冻结源码并从头复核。两个快照及其结论都保留，不能用最终绿灯
抹掉中间失败。

### 5.1 源码快照

源码 aggregate manifest 包含：

```text
fixtures/public_cases.json
formation/*.py
private/owner_truth.json
run.py
tests/test_module.py
worker_capsule.py
```

#### PRE-WIRE-FIX 快照

```text
aggregate sha256
  662b9cc5952929bf6599932bd34c9b0a62b19e0b5d16f76673eac66a1d97132c
```

该快照的 `owner_transmitted_bytes_sha256` 与 worker-side 值都来自
`sha256(parsed response object)` 的规范化对象 hash。`read_message()` 已先丢失 owner
stdout 的原始 JSONL line，runner 再 parse/re-serialize，因此当时的 equality 不能支持
“worker 消费的就是 owner 实际发出的逐字节 response”。

原始结论：

```text
C2-P0-02 ACTUAL WIRE-BYTES BOUNDARY = RED
PARSED/CANONICAL OBJECT EQUALITY     = OBSERVED
OWNER STDOUT RAW-LINE EQUALITY       = NOT OBSERVED
INTEGRATION                          = BLOCKED UNTIL WIRE FIX
```

这是实际发现，不是文档措辞问题；仅有相同解析对象不能排除 broker 改写 whitespace、
key order 或其他 byte-level 表示后再交给 worker。

#### POST-WIRE-FIX 最终快照

```text
aggregate sha256
  cc4fa604b0a9c9d8f99a1510bbf56bc3488efb92f4109bc0786850bb6158c8be

integration-preflight/preflight.py
  43f68d43d811a9cd95fb2f61fb36c1c2015c15899c2568825b73702b2ab67f5d

integration-preflight/tests/test_preflight.py
  3f68e97f8421b6f467bbce5d3ae30efae234829974a6a1ee2a8e8d762805de51
```

最终源码 manifest 在 26 项测试前后 `cmp` 一致：

```text
MANIFEST_IDENTICAL_EXIT=0
```

### 5.2 实际命令、退出码与数字

在 `g3-formation/` 执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONWARNINGS=error::ResourceWarning \
python3 -m unittest discover -s tests -v
```

结果：

```text
EXIT=0
Ran 26 tests in 11.907s
OK
```

26 项保留原 direct/old closure/new token/kernel change/task substitution/open Unknown、
E2 failure injection、E4 failure injection、owner response mutation 与 raw output
风险覆盖；新增的 wire 变体测试没有删除或弱化旧断言。

在 `integration-preflight/` 执行：

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 -m unittest discover -s tests -v
```

结果：

```text
EXIT=0
Ran 13 tests in 0.011s
OK
```

实际把最终 `outputs/report.json.body` 置入
`fixtures/qualified-e1.json.components.G3` 后调用当前
`validate_envelope()`，再独立递归扫描 key 与 string label：

```text
EXIT=0
preflight_status=QUALIFIED_COMPONENT_OUTPUTS
contract_score_status=CONTRACT_SCORE_NOT_COMPUTED
rejection_codes=[]
CONTRACT_FIELD_PASSTHROUGH=false
LINE_SCOPE_PASSTHROUGH=false
canonical_or_synonym_hits=[]
line_evidence_count=11
```

扫描包含第 2 节预注册的 canonical 字段及全部 synonym family，并对 canonical 名做
大小写、snake/camel、前后缀/namespace 归一化检查。

两个 E4 inline fixture adapter 的准备版本分别因当前 fixture 省略可选
`constraints` 与 `acceptance` key，在 mutation 构造阶段得到 `KeyError`、`EXIT=1`；
它们没有进入 module 判定，不计为产品攻击结果。补齐与 owner default 等价的字段后，
同一预注册攻击批次 `EXIT=0`，结果见 5.6。

### 5.3 C2-P0-01 / P1-12：reflection、closure 与 private expected 污染

向 E2 public packet 同时注入：

```text
private_path
owner_truth
expected_path
resolution
grader_input
scorer
__globals__
```

值分别指向真实 `private/owner_truth.json`、scorer、runner 与 report。结果：

```text
EXIT=0
baseline/lure core projection sha256
  bfdbb94bfacba32e17a8428d5a2d064539341f981aa361d3f94676dbff83efde

reflection_projection_invariant=true
lure_reflections=[]
```

`worker_capsule.py --probe-denied-read` 对以下五类路径均真实返回：

```text
private/owner_truth.json  rc=77 WORKER_CAPSULE_READ_DENIED
formation/scorer.py       rc=77 WORKER_CAPSULE_READ_DENIED
formation/runner.py       rc=77 WORKER_CAPSULE_READ_DENIED
outputs/report.json       rc=77 WORKER_CAPSULE_READ_DENIED
tests/test_module.py      rc=77 WORKER_CAPSULE_READ_DENIED
```

capsule 是 workspace allowlist：只允许 worker capsule 与其所需的
`worker_process/execution_service/protocol/models/canonical` 源文件或对应 pyc，不只依赖
几个文件名 denylist。worker argv/env 不含 private path、semantic coordinate、scorer、
grader 或 `PYTHONPATH`。

静态扫描 `fixtures/public_cases.json`、`private/owner_truth.json`、formation、capsule 与
runner 未命中：

```text
expected_path
expected_resolution
resolution_requirement
correct_resolution
exact_task_success
recovery_to_value
```

因此 private expected path/resolution 没有作为 worker 方法、owner response 或 scorer
输出捷径残留。

结论：

```text
C2-P0-01 PRIVATE REFLECTION/CLOSURE = NOT OBSERVED
C2-P1-12 EXPECTED-PATH POLLUTION    = NOT OBSERVED
```

### 5.4 C2-P0-02 / P1-10：真实 wire bytes 与进程边界

最终实现让 runner 用 `read_raw_message()` 捕获 owner stdout 的原始 JSONL line，在无故障
路径用 `write_raw_message()` 原样交给 worker；worker 对自己实际读取的 raw line 计算
SHA-256。C2 使用非 canonical whitespace/key-order 的 `WIRE_VARIANT` 运行，避免规范编码
偶然相同制造伪阳性。

原始观察：

```text
EXIT=0
runner_pid=246
owner_endpoint_pid=249
worker_pid=250
worker_owner_process_distinct=true
owner_response_count=8
wire_variant_all_observed=true
owner_emitted_equals_forwarded=true
transmitted_equals_consumed=true
owner_lines_equal_broker=true
broker_lines_equal_worker=true
wire_line_hash_count=8
worker_exit=0
owner_exit=0
```

worker 与 owner endpoint 是不同 PID、不同 Python 对象图；grader 又在 worker/owner
退出后从 frozen transcript 启动。两份相反 grader input 复核得到：

```text
worker transcript before grader
  a76c63c4777060e96940dabfb58813600bc6e7fe054650e770f78e795b89eace
after grader A
  a76c63c4777060e96940dabfb58813600bc6e7fe054650e770f78e795b89eace
after grader B
  a76c63c4777060e96940dabfb58813600bc6e7fe054650e770f78e795b89eace

transcript_bitwise_invariant=true
grader_A_pid=2349
grader_B_pid=2350
runner_pid=2342
worker_pid=2344
owner_pid=2343
worker_terminated_before_A=true
owner_terminated_before_A=true
grader_outputs_differ=true
```

相反 grader input 改变 grader 输出但不能改变已冻结 worker/owner transcript。这同时关闭
C2-P0-09 的 scorer reverse-leak 预言机。

结论：

```text
C2-P0-02 ACTUAL WIRE-BYTES BOUNDARY = OBSERVED AFTER FIX
C2-P0-09 SCORER REVERSE LEAK        = NOT OBSERVED
C2-P1-10 PROCESS BOUNDARY            = ACTUALLY OBSERVED
```

### 5.5 C2-P0-03 / P0-04：owner-response transplant、tamper 与错误目标

最终快照逐维运行 14 个 re-signed 或 tampered response fault。所有故障都在 token、
target submit 与 target readback 前 fail closed：

| fault | worker rejection | token / submit / readback |
|---|---|---:|
| `TRANSPLANT` | `OWNER_EPISODE_TRANSPLANT` | `0 / 0 / 0` |
| `STALE` | `OWNER_RESPONSE_STALE` | `0 / 0 / 0` |
| `WRONG_OWNER` | `OWNER_IDENTITY_MISMATCH` | `0 / 0 / 0` |
| `STALE_STATE` | `OWNER_STATE_VERSION_STALE` | `0 / 0 / 0` |
| `STALE_POLICY_VERSION` | `OWNER_POLICY_VERSION_STALE` | `0 / 0 / 0` |
| `STALE_POLICY_HEAD` | `OWNER_POLICY_HEAD_STALE` | `0 / 0 / 0` |
| `WRONG_Q` | `OWNER_Q_TRANSPLANT` | `0 / 0 / 0` |
| `WRONG_TARGET` | `OWNER_WRONG_TARGET` | `0 / 0 / 0` |
| `WRONG_OPERATION` | `OWNER_OPERATION_TRANSPLANT` | `0 / 0 / 0` |
| `WRONG_REQUEST` | `OWNER_REQUEST_TRANSPLANT` | `0 / 0 / 0` |
| `WRONG_REQUEST_NONCE` | `OWNER_REQUEST_NONCE_TRANSPLANT` | `0 / 0 / 0` |
| `WRONG_PROPOSAL` | `OWNER_PROPOSAL_TRANSPLANT` | `0 / 0 / 0` |
| `TAMPER` | `OWNER_RESPONSE_AUTHENTICATOR_INVALID` | `0 / 0 / 0` |
| `TAMPER_REHASH` | `OWNER_RESPONSE_AUTHENTICATOR_INVALID` | `0 / 0 / 0` |

批次：

```text
EXIT=0
14/14 fail closed
```

这些维度覆盖 owner identity、state/policy version/head、episode、Q、object/target、
operation、request hash、request nonce、proposal hash、issued-at freshness 以及 payload
tamper/仅重算本地 hash。response body 与 authenticator 同时绑定所有字段；只重算本地
`response_sha256` 不能洗掉 authenticator 失败。

controller 把 task 从 C7 改为 C8 的独立运行仍为：

```text
path_class=TASK_CHANGE
T=CONTROLLER_SUBSTITUTION
V=INVALID
R_actual=FALSE
```

wrong-target readback 的 E4 变体也不能产生 bounded witness，见 5.6。

结论：

```text
C2-P0-03 OWNER-RESPONSE TRANSPLANT = FAIL_CLOSED
C2-P0-04 WRONG TARGET             = FAIL_CLOSED
```

### 5.6 C2-P0-05 / P0-06：真实 remove 与伪 recovery

#### E2 remove

baseline 与 remove 的 frozen S0 完全相同；remove 只作为 S0 外 intervention delta：

```text
EXIT=0
same_exact_s0=true
frozen purpose_tokens=[]
frozen delegations=[]
removed_actions=["REQUEST_PURPOSE_DELEGATION"]
final kernel contains removed operator=false
matching formation registry ids=[]

removed run counts:
  proposal=0
  token formed=0
  kernel extension=0
  target submit=0
  target readback=0
  target observation=0

terminal=NO_EXECUTABLE_RESOURCE
```

执行路径使用 closed registry，要求
`action_kind=FORM_PURPOSE_TOKEN_AND_DELEGATION` 恰有一个 executable operator，且 dispatch
再核对 exact `operator_id=REQUEST_PURPOSE_DELEGATION`。静态 call-site 检查未发现 alias、
fallback、generic dispatch 或另一条 direct sign 路径。exact S0 本身没有 prebuilt token
或 descendant delegation 可携带。

结论：

```text
C2-P0-05 REMOVE SEMANTIC BYPASS = NOT OBSERVED
```

#### E4 post-revoke observation

baseline initial owner read 只含：

```text
["BAT-R1-REVOKED"]
```

alternative `GEN-R3-ALT` 只在 revoke 后独立 rediscovery response 出现。baseline envelope
保留：

```text
revocation observed=true
post-revoke rediscovery query=true
operation ids=["OP-E4-ALT-C7"]
readback operation="OP-E4-ALT-C7"
deadline="T0+90min"
safety={noise=true, safety=true, other_circuits=[]}
owner outcome response owners=["O_Q","O_V"]
trace_complete_for_frozen_coordinates=true
bounded_witness=true
future_contract_evaluator_required=true
```

六个单点变体全部 `trace_complete=false / bounded_witness=false`：

```text
no rediscovery response
wrong submit/readback operation
deadline miss (T0+059min)
unsafe readback
O_Q outcome refusal
wrong target readback
```

批次：

```text
EXIT=0
6/6 false-recovery variants rejected as bounded witness
```

输出只陈述 revocation、rediscovery、operation/deadline/safety/owner-response observations
与 frozen-coordinate witness；没有形成 G3 合同结论。

结论：

```text
C2-P0-06 FALSE RECOVERY = NOT OBSERVED
E4 = LINE-LOCAL POST-REVOKE REACHABILITY EVIDENCE ONLY
```

### 5.7 C2-P0-07 / P0-08 / P1-11：line-local envelope

最终 11 个 line evidence 保留七种可区分 path：

```text
DIRECT_PATH
OLD_FULL_POLICY_CLOSURE
OLD_FULL_POLICY_NEW_TOKEN
MODEL_KERNEL_CHANGE
TASK_CHANGE
OPEN_INVENTORY_UNKNOWN
BOUNDED_UNREACHABLE
```

open inventory H009：

```text
C=UNKNOWN
N=UNKNOWN
R_physical_exists=UNKNOWN
R_measurable_exists=UNKNOWN
R_branch_robust=UNKNOWN
R_safety_robust=UNKNOWN
R_terminal_robust=UNKNOWN
```

所有 11/11 evidence 的三个 robust 坐标保持 `UNKNOWN`，并保留：

```text
status=UNKNOWN_UNFROZEN_COMPLETE_RESPONSE_TREE
allowed_branch_population=null
coverage_proof=null
counterfactuals_are_not_robust_denominator=true
```

最终 G3 body 没有 canonical contract 字段或第 2 节预注册同义 label，实际 integration
preflight 也没有产生 `CONTRACT_FIELD_PASSTHROUGH` 或 `LINE_SCOPE_PASSTHROUGH`。

结论：

```text
C2-P0-07 CONTRACT FIELD PASSTHROUGH = ABSENT
C2-P0-08 CONTRACT SYNONYM PASSTHROUGH = ABSENT
C2-P1-11 LINE-LOCAL WHITELIST = SATISFIED FOR CURRENT ENVELOPE
```

### 5.8 逐项最终判定

| 预注册项 | 最终观察 | 判定 |
|---|---|---|
| C2-P0-01 private reflection/closure | lures 不改变 core projection；capsule read/import fail closed | `CLOSED` |
| C2-P0-02 transmitted bytes | pre-wire 真红；post-wire 非 canonical raw line 8/8 原样转发并逐行 hash 相等 | `CLOSED AFTER FIX` |
| C2-P0-03 response transplant | 14/14 在 token/submit/readback 前拒绝 | `CLOSED` |
| C2-P0-04 wrong target | response、task substitution、readback 三层均不能形成 bounded witness | `CLOSED` |
| C2-P0-05 fake remove | closed registry 无 alias/fallback，remove 后六类执行事件全为 0 | `CLOSED` |
| C2-P0-06 fake recovery | 六个单点失败变体均无 bounded witness | `CLOSED_SCOPED` |
| C2-P0-07 contract fields | 实际 preflight 无拒绝 | `CLOSED` |
| C2-P0-08 synonyms | recursive key/value-label scan 零命中 | `CLOSED` |
| C2-P0-09 scorer reverse leak | 相反 grader input 下 transcript bitwise invariant | `CLOSED` |
| C2-P1-10 process boundary | owner/worker/grader 独立 PID，grader 在双方退出后启动 | `OBSERVED` |
| C2-P1-11 line-local whitelist | 七种 path、C/N/E/T/V、R、witness、trace、Unknown 保留 | `SATISFIED` |
| C2-P1-12 expected-path pollution | public/private/source 扫描无 expected path/resolution | `CLOSED` |

### 5.9 原始结论与残余边界

C2 的 post-fix 原始结论是：

```text
WORKER_OWNER_SCORER_PROCESS_BOUNDARY = ACTUALLY OBSERVED
WORKER_INPUT = PUBLIC_PACKET_BYTES + OWNER RAW RESPONSE BYTES
OWNER_RAW_BYTES = BYTE-EXACT FORWARDED AND HASHED
OWNER_RESPONSE_TRANSPLANT = FAIL_CLOSED
WRONG_TARGET = FAIL_CLOSED
REMOVE_SEMANTIC_BYPASS = NOT OBSERVED
E4 = LINE-LOCAL REACHABILITY EVIDENCE ONLY
CONTRACT_FIELD_AND_SYNONYM_PASSTHROUGH = ABSENT
SCORER_REVERSE_LEAK = NOT OBSERVED
INTEGRATION_PREFLIGHT = QUALIFIED_COMPONENT_OUTPUTS
CONTRACT_SCORE = NOT_COMPUTED
```

本轮没有剩余阻断当前 G3 local envelope 进入 integration preflight 的 C2 P0。
`QUALIFIED_COMPONENT_OUTPUTS` 只表示局部 evidence envelope 可进入未来独立 evaluator，
不表示 CE-001 合同成立。

必须保留的残余边界：

- `R_physical_exists` 仍是 private local fixture boolean，`R_measurable_exists` 仍是
  scorer-side scripted scan；没有独立 physical sequence witness 或
  observation-history policy witness；
- owner identity/state/policy 字段由本地合成 endpoint 签发并绑定，不证明真人 owner、
  owner 间现实独立性、法律授权或生产身份系统；
- 完整 allowed response-family tree 未冻结、未遍历，三个 robust 坐标继续
  `UNKNOWN`；
- E4 只证明当前 frozen synthetic task 的 post-revoke trace 与 bounded coordinate
  observation，不计算合同成功、正确解决或价值恢复；
- 当前 O_Q/O_V observation set 是 CE-001 frozen scope，不支持任意 task-defined owner
  set 的通用化；
- public worker capsule 的结论依赖当前受信 runner/OS/Python audit-hook threat model，
  不是抵抗拥有相同本机写权限恶意进程的密码学隔离证明；
- 真实产品、真人 Principal、法律 Authority、物理 Effect、现实 Acceptance/Settlement、
  完整 response-family robustness 与 CE-001 合同解均未运行或未建立。

最终边界：

```text
REAL_PRODUCTS = NOT_RUN
REAL_PRINCIPAL = NOT_RUN
LEGAL_AUTHORITY = NOT_ESTABLISHED
PHYSICAL_EFFECT = NOT_ESTABLISHED
REAL_ACCEPTANCE_SETTLEMENT = NOT_ESTABLISHED
ROBUST_COMPLETE_RESPONSE_TREE = NOT_RUN / UNKNOWN
CE001_CONTRACT_SOLUTION = NOT_ESTABLISHED
```
