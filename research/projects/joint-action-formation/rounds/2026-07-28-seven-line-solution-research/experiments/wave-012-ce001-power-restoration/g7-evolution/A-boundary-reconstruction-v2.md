# G7 第二轮 Agent A：权威边界独立重建

日期：2026-07-30  
身份：`G7_AGENT_A_V2 / independent boundary reconstruction`  
作用域：CE-001 的 E4/E6 owner、runtime、lineage 与 integration handoff  
状态：`DESIGN BOUNDARY / NO B IMPLEMENTATION READ / NO FORMAL STATUS CHANGE`

## 0. 读取与独立性

本轮 A 完整读取了 cohort-003 的 `COMMON.md`、`G7-PROMPT.md`、
`ROOT-LIVE-AUDIT.md`、旧 `G7-final.md`，G7 旧 `README.md` 与
`C-adversarial-audit.md`，CE-001 contract，以及 integration preflight 的 README、实际
validator 和 E6 schema fixture。A 没有读取或等待 B 的第二轮方案，也不实现代码。

旧 A/B/C 身份与首轮红灯不能被第二轮覆盖。本文件是新的独立问题重建，不把多 Agent 一致、
33/33、字段齐全、不同字符串 ID 或 preflight 通过当作事实独立性的证据。

## 1. 根问题重建

本轮要修的不是一个 simulator 少了几个字段，而是以下四个非蕴含边界此前被同一 Python
对象图抹平：

1. controller 能安排 owner 调用，不因此拥有 owner state 或 owner act；
2. G5 能形成 current receipt set，不因此证明 target 在 dispatch 时消费并接受了这组
   receipts；
3. coordinator 能构造 source/target 对象，不因此发生了进程终止、状态迁移、旧 runtime
   重启或外部 fence 拒绝；
4. G7 能观察 line-local history、reopen、migration 和 lineage，不因此有资格计算 CE-001
   合同结论。

因此，第二轮的成功判据不是“对象 ID 不同”，而是：

```text
owner act       = 独立 owner process 从自己的 durable state 作出的 transmitted-byte act
target gate     = target process 对 current receipt bytes 的原生验证与落盘消费事件
migration       = source 实际终止、target 实际接管、old source 实际重启并被外部 epoch 拒绝
lineage evidence= 从真实传输帧和 durable bytes 计算的 digest 与 readback
G7 output       = 只有 line-local evidence；未来独立 evaluator 才形成合同结论
```

## 2. 权威 owner 与事实 owner

### 2.1 不可合并的 owner sources

| owner | 自己拥有的 durable state | 自己才能作出的 act | G7 的权限 |
|---|---|---|---|
| `O_Q` | current Q、Q version、不可替代约束、requester decision head | 对 exact post-occurrence bytes 作 requester act，或拒绝/Unknown | 只能请求、保存返回原始 bytes 和引用其 hash |
| `O_V` | Venue V、Circuit C7、operation/target revision、venue decision head | 对同一 exact post-occurrence bytes 作 venue act，或拒绝/Unknown | 同上 |
| `O_P` | payment/beneficiary obligation、当前 obligation head | 只有验证两份独立 post-occurrence owner acts 后，才作自己的 post-two-act finality act | 只能保存其返回；不能从前两份 act 派生或代写 |
| `O_R` | resource、reservation、revocation/current head | resource receipt/defeater | G5/E4 消费，G7 只保留 lineage |
| `O_S` | safety policy/current head | exact-operation safety receipt | G5/target 消费，G7 只保留 lineage |
| `O_E` | target-native occurrence/readback state | exact operation occurrence/readback record | G6 权威；G7 只引用 occurrence digest 做 reconciliation |

至少 `O_Q`、`O_V`、`O_P` 必须各有：

- 不同 OS process；
- 不同 runtime identity 与 process-start event；
- 不同、非 symlink alias、非同 inode 的 durable state root；
- 不同持久 `state_source_id`；
- 不同 `act_source_id`、私钥与 out-of-band trust anchor；
- 自己的 current revision/head；
- request/response 的原始 transmitted frames。

controller 不能持有 owner 私钥，不能把一个 owner response 改标签成另一个 owner，也不能把
一个 owner 的 state object 注入另一个 owner。当前仍是同一主机、同一用户权限下的本地
合成隔离，不抵抗能够读取所有目录与密钥的恶意同权限进程，更不建立真人或法律独立性。

### 2.2 owner act wire contract

owner request 必须传输完整的 exact bytes，而不是只传一个 controller boolean 或 fixture
hash。请求至少绑定：

```text
protocol_version
request_id + unpredictable challenge
owner_id
episode_id
Q_version
object_id
operation_id
target_id
target occurrence/readback raw-frame hash
target occurrence/readback raw bytes
expected owner state head
request expiry
```

`O_Q`、`O_V` 分别从自己的 durable state 读取 current head，验证 occurrence/readback frame
及其 trust anchor，再返回自己的签名 response frame。response 至少绑定原 request hash、
challenge、全部 exact identity、occurrence hash、owner state head、decision 和 expiry。

`O_P` 不接受 controller 传入的 `both_accepted=true`。它必须收到 `O_Q`、`O_V` 两份完整
response frames，按两个独立 trust anchors 验签、检查 exact identity/effect reference、
distinct owner、current head 和 decision，然后从自己的 durable state 作出新 act。它的
response 必须绑定两份实际 response frame hashes，且不能复用任一前序对象或 act source。

producer 与 consumer 都对同一个 length-delimited transmitted frame 计算 SHA-256，并记录
byte length；只对 parse 后 dict 重新 canonicalize 得到的 hash 不算传输证据。

### 2.3 必须 fail closed 的 owner 攻击

- 用 `O_Q` response 复制或改标签冒充 `O_V`；
- duplicate `O_Q` 或 duplicate `O_V`；
- response transplant 到不同 episode、Q、object、operation、target 或 occurrence；
- 复用旧 challenge/request 的 response；
- receipt 发出后 owner current head 已前进、撤销或过期；
- response bytes、签名、owner trust anchor 或 declared source 被篡改；
- `O_P` 在两份 owner act 之前动作；
- `O_P` 只收到 hash/boolean 而未收到并验证两份原始 frames；
- `O_P` 从 owner act object 派生 finality，或复用任一 owner 的 process/state/act source。

所有拒绝都要求零 owner-state 错误推进、零 target dispatch，并保留原始拒绝 frame；不能只让
最终 summary 变为 false。

## 3. current receipt set 与 target-native consumption

### 3.1 G5 与 target 的职责不相同

G5 可以输出一组 candidate current receipts，但不能替 target 宣布其已满足 gate。dispatch
API 中不得存在 `authority_allowed=True`、`authorized=True` 或等价 controller override。

target process 的唯一执行入口必须接收 actual receipt frames。它使用自己的 out-of-band
owner trust anchors 与 frozen CE-001 target configuration，逐项验证：

- exact episode/Q/object/operation/target/scope/expiry；
- required owner/role set，无缺失、重复或替代；
- 每份签名对 actual native receipt bytes 有效；
- receipt state head 与 dispatch 时 owner current-head evidence 一致；
- resource、safety、venue fence/standing 仍 current；
- set 中没有 stale、wrong-run、wrong-target 或 tampered receipt。

receipt-set digest 必须从 actual transmitted frames 计算。若需要稳定集合 digest，使用明确
长度前缀和确定性 owner 排序；不能 hash 一个 fixture 常量或 controller 重建后的 dict。

### 3.2 原生消费事件

target 在任何 target transition 之前，把 verification result 作为 target-native
append-only event 落到自己的 durable state。event bytes 至少包含：

```text
target runtime/process/state identity
request frame hash
receipt-set transport hash
each consumed receipt frame hash
owner current heads actually checked
trust-anchor/config version
exact episode/Q/object/operation/target
decision + rejection reason
previous target state head
event sequence/head
```

`consumption_event_hash` 必须由落盘 event 的 actual bytes 计算，并由独立 readback 再读。
只有 event 决定为允许后，target 内部状态机才可 dispatch。controller 记录了 receipts、
设置 `consumed_by_target=true` 或返回一个同名 hash 都不构成消费事实。

wrong/stale/tampered/missing/duplicate receipt、错误 current head、错误 target 或 controller
boolean 注入必须在 target process 内 fail closed，且 target state transition count 保持零。

该事件属于 G6 的 target-native evidence。G7 迁移 capsule只能保留其 opaque digest 和 raw
frame lineage，不能重新生成或升级其语义。

## 4. E6 的真实 process/state/fence 边界

### 4.1 至少四个进程域

E6 不能再由同一进程内的 source coordinator、target coordinator、`EffectTarget` 和 fence
对象完成。最低运行拓扑是：

1. `source coordinator process`：source runtime identity、source durable state root；
2. `target coordinator process`：不同 runtime identity、PID/start token、durable state root；
3. `external fence-owner process`：第三 durable state root，持有 current coordinator epoch；
4. `target service/readback process`：在每次提交时原生验证 fence-owner 的 current epoch。

owner processes 另行独立。不同 PID 字符串本身不是证明；raw lifecycle evidence 必须绑定
PID、process start time/token、executable hash、runtime instance UUID 和 state-boundary
UUID。source/target state root 的 realpath、store UUID、device/inode 均不得 alias。

### 4.2 必须实际发生的时序

```text
source process(epoch n)
  → target service 已落盘一次 exact occurrence
  → source history 记录 response missing，尚无 O_Q/O_V post-occurrence acts
  → flush source state/history/capsule export
  → 实际 terminate source；wait 得到 exit observation

target process(epoch n+1)
  → 从 transport 收到 capsule raw bytes
  → 验 source seal、capsule bytes、source state/history prefix 与 owner evidence lineage
  → external fence owner 用 CAS/lineage 安装 epoch n+1 并落盘
  → target durable state 导入 source prefix，byte-for-byte 验证
  → target service readback 对账 occurrence count=1，禁止 replay
  → 从独立 O_Q/O_V/O_P processes 恢复后序 owner acts

old source restart process(epoch n)
  → 新 PID/start token，但沿用 source runtime identity 与旧 source durable state
  → 实际向 target service 提交
  → target service 查询/验证 external fence epoch n+1
  → 返回 REJECTED_OLD_EPOCH，且零 target transition
```

如果 old restart 只得到 `DEDUPLICATED`，E6 fence 仍是红灯：idempotency 不能替代旧 epoch
拒绝。若只是创建一个 old runtime object、布尔写 `actually_restarted=true`，或 source 未
先退出，也不算 restart。

fence owner 重启后必须从自己的 durable store 恢复 epoch n+1；若 fence state 跟随 source、
target 或 target service object 消失，仍是 volatile fence。

### 4.3 source/target state 与 history lineage

source history prefix 是实际 durable history file 的原始 prefix bytes。target import 后，
target history file 的前 N bytes 必须与该 prefix byte-for-byte 相同，之后只追加 takeover、
reconciliation、owner-source recovery 与 old-epoch rejection records。

必须分别保存并复算：

- source process flush 后的 source state bytes hash；
- capsule exporter 实际发送 frame 的 hash；
- importer 实际收到 frame 的 hash；
- target import 后的 target state bytes hash；
- source history prefix raw bytes hash；
- target history实际前缀 raw bytes hash；
- owner evidence actual response frame hashes；
- target service occurrence/readback raw frame hash；
- external fence state/event raw bytes hash；
- old restart request/response raw frame hashes。

producer/consumer hash、byte length或 prefix bytes 任一不一致即 fail closed。hash 值来自
fixture、常量、预期表或 parse 后重建，都不能充当已验证 lineage。capsule hash 还必须被
source runtime seal 绑定；裸 hash 不能防止攻击者改 payload 后重算。

append-only 在此只保证受信 harness 与分离 worker 下能检测普通误改、越界写入和流水线内
替换；它不宣称抵抗拥有相同目录写权限的恶意本机进程。

## 5. E4 与其他必须保留的负空间

E4 必须继续区分：

- primary resource revocation 的 Defeater 与历史保留；
- primary branch 的 exact effect reconciliation；
- alternative `O_R` 的新 owner-source receipt、current head 和 exact commitment；
- local causal reopen 与共享 root 变化导致的 global reopen；
- safe block 与真正恢复到原 Q 的不同后置事实。

G7 只输出 reopen set、dependency/history digests、alternative lineage 与上游 occurrence
references。它不能自行写合同级“恢复成功”。已有 primary occurrence 被 dedupe 不能冒充
alternative 路径产生了新后置状态。

以下边界不得因第二轮变绿而消失：

```text
E4 alternative recovery evidence             required
E6 occurrence / owner-act gap                 required
append-only + exact occurrence reconciliation required
capsule field loss                            FAIL_CLOSED, not portability success
cold/reuse full-lifecycle cost                NOT_MEASURED
second-adapter semantic independence          NOT_ESTABLISHED
hidden pair                                   NOT_CONSTRUCTED
safety-liveness frontier                      NOT_RUN
```

除非真的构造两个 final requirement 相反的 hidden worlds，否则不得生成 pair 或 frontier
数字。valid world 必须要求继续，否则计 liveness loss；revoked world 禁止继续；两侧相同
保守动作永远不能支持不可兼得结论。

## 6. G7 与 integration preflight 的精确接口

### 6.1 ownership

- top-level `episode` 和 `owner_sources` 由 integration assembler 从真实 upstream/owner
  outputs 组装，G7 不伪造；
- G5 namespace 拥有 current receipt closure；
- G6 namespace 拥有 target consumption、occurrence、O_Q/O_V acts 与 O_P finality；
- G7 namespace只拥有 evolution/reopen/migration/lineage evidence；
- future independent evaluator 才能计算 CE-001 合同结果。

G7 只产出自己的 component fragment，不能用手写 G1–G6 fixture 补齐七个 namespace 后声称
进入 integration。`qualification=QUALIFIED_COMPONENT_OUTPUT` 只表示局部结构有资格送
preflight，不是 G7 或 CE-001 成功。

### 6.2 preflight-compatible G7 fragment

以下是当前 preflight 所需的精确字段。所有 `<...>` 必须由本轮 actual bytes/events 填充，
不能复制 `qualified-e6.json` 的 fixture 字符串：

```json
{
  "namespace": "G7",
  "qualification": "QUALIFIED_COMPONENT_OUTPUT",
  "evidence": {
    "append_only_history_hash": "<sha256 actual target history bytes>",
    "dependency_graph_hash": "<sha256 actual dependency graph bytes>",
    "reopen_set": ["<actual line-local node ids>"],
    "migration": {
      "source_runtime": {
        "runtime_id": "<source durable runtime uuid>",
        "process_id": "<hash actual source process-start event>",
        "state_boundary_id": "<hash source store uuid plus realpath/inode binding>",
        "epoch": 7
      },
      "target_runtime": {
        "runtime_id": "<target durable runtime uuid>",
        "process_id": "<hash actual target process-start event>",
        "state_boundary_id": "<hash target store uuid plus realpath/inode binding>",
        "epoch": 8
      },
      "old_runtime_restart": {
        "actually_restarted": true,
        "restart_observed": true,
        "presented_epoch": 7,
        "current_epoch": 8,
        "fence_result": "REJECTED_OLD_EPOCH",
        "process_start_event_hash": "<sha256 actual restart event bytes>",
        "request_frame_hash": "<sha256 actual old submit frame>",
        "response_frame_hash": "<sha256 actual target rejection frame>",
        "external_fence_event_hash": "<sha256 actual fence-owner event bytes>"
      },
      "lineage_verification": {
        "capsule_hash": "<sha256 actual transmitted capsule frame>",
        "source_runtime_hash": "<sha256 actual flushed source state bytes>",
        "target_runtime_hash": "<sha256 actual imported target state bytes>",
        "history_prefix_hash": "<sha256 actual target prefix bytes>",
        "owner_evidence_hashes_verified": true,
        "effect_hash": "<opaque exact G6 occurrence digest reference>",
        "q_version": "Q@v1",
        "object_id": "VenueV:CircuitC7",
        "history_fork_detected": false,
        "effect_occurrence_count_for_operation": 1,
        "capsule_producer_frame_hash": "<sha256 exporter frame>",
        "capsule_consumer_frame_hash": "<sha256 importer frame>",
        "target_consumption_event_hash": "<opaque exact G6 target event digest reference>",
        "owner_verification_event_hash": "<sha256 target recovery verifier event bytes>"
      },
      "recovery": {
        "acceptance_hashes": [
          "<opaque exact G6 O_Q act digest reference>",
          "<opaque exact G6 O_V act digest reference>"
        ],
        "finality_hash": "<opaque exact G6 O_P act digest reference>",
        "recovered_from_owner_sources": true,
        "owner_transport_manifest_hash": "<sha256 actual owner request/response manifest bytes>"
      }
    },
    "evidence_boundaries": {
      "hidden_pair": "NOT_CONSTRUCTED",
      "safety_liveness_frontier": "NOT_RUN",
      "cold_repeat_full_lifecycle": "NOT_MEASURED",
      "adapter_semantic_independence": "NOT_ESTABLISHED",
      "real_product": "NOT_RUN",
      "production_split_brain": "NOT_RUN"
    }
  }
}
```

当前 preflight 为 E6 硬性要求 `effect_hash`、`acceptance_hashes` 与 `finality_hash` 这三个
兼容字段。G7 对它们只能保存 opaque、exact cross-line digest references：不能复制 G6
objects、生成对应语义、加入成功布尔或把 hash 命名成 G7 自己的结论。若把用户的禁止理解为
连这三个 preflight-required key 也不能出现，则当前 preflight schema 与本轮写入边界冲突，
必须由 integration owner 另行版本化；G7 不得私改 preflight。

除上述兼容引用外，G7 输出采用严格 allowlist。递归扫描 key 与自报状态，拒绝
`ExactTaskSuccess`、`CorrectResolution`、`RecoveryToValue`、`Authority`、`Effect`、
`Acceptance`、`Settlement`、coverage、winner、contract success 以及改名同义结论。
line-local raw event、digest、count、reopen set 和 lifecycle observation不是合同判定。

### 6.3 bytes-derived evidence manifest

每个 envelope digest 都必须能回到一个 manifest row：

```text
artifact_kind
producer_process_start_event_hash
consumer_process_start_event_hash
producer_frame_hash
consumer_frame_hash
byte_length
durable_path / state-boundary UUID
readback_frame_hash
previous history head
new history head
```

manifest 本身也从落盘 bytes 计算 hash。不存在 raw bytes、producer/consumer 对不上，或只能
回到 fixture 常量的字段，保持 absent 并使 qualification 失败；不得补一个看似合法的
`sha256:*` 字符串。

## 7. 第二轮不可妥协的攻击矩阵

旧 33 项风险覆盖必须完整保留，且至少新增：

| 攻击族 | 必须观察到的拒绝 |
|---|---|
| merged owner | O_Q/O_V/O_P 任一复用 process、state root、state source、act source 或 trust anchor，qualification fail |
| duplicate/transplant | 重复 owner，或跨 episode/Q/object/operation/target/occurrence 移植 owner response，owner/G6 fail closed |
| stale owner act | owner head 前进、撤销、expiry 过期后复用 response，fail closed |
| controller gate injection | dispatch 传 boolean 或绕过 receipt frames，target 零 transition |
| receipt set mutation | wrong/stale/tampered/missing/duplicate/current-head mismatch，target 零 transition |
| fake consumption | 只有 controller log/boolean/hash、没有 target durable event与readback，qualification fail |
| same-process migration | source/target PID/start token 或 runtime/state boundary alias，qualification fail |
| fake termination | source 未实际 exit 就启动 target，qualification fail |
| fake restart | 没有新的 old-source process-start/submit/response frames，qualification fail |
| volatile fence | target/fence process重建后丢 epoch，old commit 必须使测试变红 |
| idempotency masquerade | old restart 返回 dedupe 而非 `REJECTED_OLD_EPOCH`，E6 fail |
| capsule fixture hash | hash 不是从实际 producer/consumer frames 计算，或 frame hash 不同，fail |
| state/history rewrite | source/target state、prefix 或 target appended history 任一 byte 改写，fail |
| field loss | 删 capsule required field，即使重算裸 hash，也只能 fail closed |
| contract passthrough | G7 任意层出现合同字段、成功布尔、coverage、winner 或同义结论，scanner reject |

红灯的原始输入、stdout/stderr、process lifecycle、exit status、target state readback 和未发生
transition 的证据必须保留。最终全绿不能改写首次失败。

## 8. 本轮仍不能建立

即使上述条件全部实现并通过，也只能支持本地 process/state-separated component evidence。
以下精确保持：

```text
REAL_PRODUCT_RUN                         NOT_RUN
REAL_HUMAN_OWNER_ACT                     NOT_RUN
LEGAL_AUTHORITY                          NOT_ESTABLISHED
PHYSICAL_POWER_EFFECT                    NOT_RUN
PRODUCTION_SPLIT_BRAIN                   NOT_RUN
CROSS_PRODUCT_PORTABILITY                NOT_ESTABLISHED
SECOND_ADAPTER_SEMANTIC_INDEPENDENCE     NOT_ESTABLISHED
COLD_REPEAT_FULL_LIFECYCLE_NET_VALUE     NOT_MEASURED
HIDDEN_SAFETY_LIVENESS_PAIR              NOT_CONSTRUCTED
HIDDEN_SAFETY_LIVENESS_FRONTIER          NOT_RUN
FULL_CE001_EIGHT_CASE                    NOT_RUN
FULL_G1_TO_G7_COMPOSITION                NOT_ESTABLISHED
CE001_CONTRACT_SCORE                     NOT_COMPUTED
COMPLETE_CE001_SOLUTION                  NOT_ESTABLISHED
```

preflight 通过只说明 namespaced component output 没触发当前结构红灯。它仍不能证明 ID 背后
真的独立，所以最终报告必须同时列出实际 PID/start token、runtime identity、durable state
path、raw byte manifest、攻击与残余边界。
