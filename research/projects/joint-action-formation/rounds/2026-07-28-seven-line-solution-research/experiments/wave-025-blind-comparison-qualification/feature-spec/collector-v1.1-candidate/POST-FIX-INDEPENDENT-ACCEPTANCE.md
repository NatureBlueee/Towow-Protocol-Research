# Collector V1.1 candidate post-fix 独立验收

Date: 2026-08-01  
Reviewer: original `COLLECTOR-RECEIPT-SCHEMA-REDTEAM` reviewer  
Status: `POST_FIX_REJECTED_FOR_FORMAL_AND_EVIDENCE_BEARING_G`

## 1. 总结论

V1.1 确实关闭了一批原反例：environment/tree/process identity 与排序、
tree/process truncation、status grammar、canonical proc PID、monotonic nesting、timing sample sum、
raw duplicate member、receipt canonical bytes，以及已声明小域内的 canary 完整重建。
producer 的 `collectCandidate()` 也真的调用了新验证，不是只有 fixture 调用 helper。

但本轮仍为 **REJECT**，不能解锁 formal 或 evidence-bearing G：

1. manifest 和历史 source hash 从未被 producer/admission 执行层验证；移除 manifest
   后 admission 仍然成功。
2. receipt、material 和 binding 可同步伪造。collector-input bytes 不是所声明 JSON、
   receipt challenge tree 与 live challenge 不同时，仍可得
   `CANDIDATE_ADMISSION_PASS_BOUND`。
3. V1.1 admission schema 在独立 instance validation 时因 relative `$ref` 无法解析；
   自带测试只 `check_schema`，CLI 则绕过它直接验旧 schema。
4. policy 与两份 schema JSON 自身无法通过 package raw canonical checker。
5. semantic validator 仍接受不可达的 depth-6 tree 和多种错误 provenance。
6. process snapshot 可为 null；error-row snapshot 存在时可在明列 unknown 的同时被
   状态表达式命名为 `PASS_BOUND`。
7. canary completeness 只覆盖文件 `<=65536` bytes。65537-byte 文件内含 canary
   时，bound receipt 可以不包含该 canary。

当前最强可支持主张是：

> 这是有价值的 candidate admission prototype，可用于明确标记 nonformal 的受控
> engineering smoke；还不是把 receipt/material/source 绑定成 formal evidence 的执行门。

`ACCEPT` 表示原 finding 在它声明的 candidate 小域内由真实执行关闭；
`REJECT` 表示仍有可执行反例或主张过强；`UNKNOWN` 表示当前缺少受信外部证据。

## 2. 历史不变性与 manifest

| artifact | SHA-256 | result |
|---|---|---|
| historical collector source | `bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699` | `ACCEPT / unchanged` |
| historical receipt schema | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` | `ACCEPT / unchanged` |
| F `precommit.json` | `d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e` | `ACCEPT / unchanged` |
| F `closed.json` | `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e` | `ACCEPT / unchanged` |
| F `reveal.json` | `7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287` | `ACCEPT / unchanged` |

12 份 F collector receipts 的 `slot-id + SHA-256 + LF` 有序列表 SHA-256 为
`42f7869d5de0caf6babcd95779cf8b2d1bb4dfec36da1640e018ff1962bb46c1`，与原红队逐项记录一致。

manifest 列出的 8 份 candidate files 的 current byte length/hash 全部匹配，两份 historical
input hash 也匹配，所以静态 inventory 是 `ACCEPT`。

但运行时完全不读 manifest。在一个没有 manifest 的临时目录中仅保留
admission、raw checker、binding schema 和旧 receipt schema，admission 仍 exit 0。producer
也只 plain `require("../../attackers/leak-only-collector/collector.js")`，没有重算 source hash。
因此 runtime source/package binding 是 `REJECT`。

## 3. 原红队 finding 逐项回放

| Finding | Result | Independent result |
|---|---|---|
| RT-B01 identity/order | `ACCEPT` | duplicate/unsorted env、duplicate tree path、duplicate/reversed PID 都被 identity/order error 拒绝 |
| RT-B02 tree reachability | `REJECT` | truncation、`../escape`、duplicate path 已拒绝；但含全部 ancestors 的 depth-6 file tree 仍得 `PASS_WITH_UNVERIFIED...` |
| RT-B03 process count/order/provider | `ACCEPT` | process truncation、duplicate/reversed PID 被拒绝；proc name `01` 在 base 运行前得 `PROC_PID_GRAMMAR` |
| RT-B04 monotonic timing | `ACCEPT` | backward interval 得 `MONOTONIC_NESTING`；样本和超 interval 得 `TIMING_SAMPLE_SUM` |
| RT-B05 digest/source relation | `REJECT` | unbound 伪 digest 正确降级；但同步伪造 receipt/material/binding 得 `PASS_BOUND` |
| RT-B06 operation error provenance | `REJECT` | same-PID wrong process leaf、wrong `/etc/hostname` error source、tree `syscall=connect` 都被接受 |
| RT-B07 canary completeness | `REJECT` for full claim | orphan env canary 已拒绝；bound reconstruction 在小域内 exact；>64 KiB file canary 可被忽略 |
| RT-A01 non-producer caps | `REJECT` as resource closure | env/subject 在 base 前拒绝；8193 tree errors 在 base 已物化后才拒绝，generic strings 也 post-collection，`readdir` 在 count gate 前整体分配 |
| RT-A02 status grammar | `ACCEPT` in frozen Linux scope | 真实 `collectCandidate()` 路径中 `ppid="abc"` 得 `STATUS_GRAMMAR`, `baseCalled=1` |
| RT-A03 number/proc provider | `ACCEPT` algorithmically; run `UNKNOWN` | canonical safe PID name/count 在 base 前检查；package 不证明 G 实际 mount/provider |
| RT-L01 lossy projections | `UNKNOWN` | env/config/subject/canary 与 success process snapshot 可重算；raw errors、同时刻 directory metadata 仍不可重建 |
| RT-L02 raw/canonical layer | `REJECT` as release | 12 F receipts、duplicate/pretty cases证明 checker 核心有效；但 checker/Node 未运行绑定，3 份 candidate JSON 自身 noncanonical |
| RT-L03 deterministic order | `ACCEPT` for admitted rows | adapter 将 env/tree/process/canary 归一为 UTF-8 byte/numeric order；node-limit 内 sort-last canary 被扫到，overflow fail closed |
| RT-L04 execution claims | `UNKNOWN` | report 保持 `formal=false`并明列 zero-call/source/isolation unknown；schema/receipt 仍不能证明 |

## 4. 新增 formal blockers

### PF-B01 — V1.1 admission schema 不能独立验 instance

`COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json` 带 HTTPS `$id`，却使用文件式
relative `$ref`。真实执行 `Draft202012Validator(schema).iter_errors(receipt)` 得：

```text
_WrappedReferencingError
Unresolvable: ../COLLECTOR-RECEIPT-V1.candidate.schema.json
```

自带测试仅 `check_schema`，不 resolve reference；CLI 的 `OLD_SCHEMA` 又绕过该 wrapper。
当前它是 decorative manifest member，不是 independent consumer 可执行 schema。

### PF-B02 — 同步伪造获得 `PASS_BOUND`

独立最小世界使用：

- 非 JSON 的 collector-input bytes；
- 任意 subject；
- 一个 65537-byte、含 `WAVE025_CANARY_...` 的文件；
- 从 F 复制但仅同步改写 config/subject/env digest 的 receipt；
- 仍声明正确 parsed schema，仍保留与 live challenge 不同的旧 challenge tree；
- 对所有 synthetic files 同步重算 binding。

实际返回：

```text
SYNC_FORGE_STATUS CANDIDATE_ADMISSION_PASS_BOUND formal=False
LIVE_LARGE_CANARY_ROWS 0 large_bytes=65537
RECEIPT_CHALLENGE_TREE_HAS_LARGE False
```

根因是 binding 无 controller seal，bound config 不被解析并与 parsed object 比较，
live challenge snapshot 不与 receipt tree 联结，CLI `challenge_root` 也不是 binding 锁定的
role/path。`formal=false` 防止它直接假冒 formal，但 `PASS_BOUND` 只能读作
“同时供应的文件内部自洽”，不是 actual-producer binding。

### PF-B03 — tree/error producer language 仍未闭合

除 depth-6 tree 外，以下均得 `PASS_WITH_UNVERIFIED...`：

```text
process error pid=7, error.path=$PROC/7/not-a-collected-file
/etc/hostname error branch, error.path=$TMP/unrelated
tree missing-path error, syscall=connect
```

这些只要进 F03/F04/F05/F06 lexical/exact route，仍可把损坏 receipt 变成 predictor 信号。
G 必须明确选择“受信 producer seal 代替独立重建”或“全部 operation provenance
fail closed”中的一个精确主张。

### PF-B04 — process snapshot 与 status 误报

process view available 但 snapshot=null 时，正确降级为 `PASS_WITH_UNVERIFIED...`。
但 public process/self 都是 error branches、snapshot 只含 PID 和 self null placeholders 时，
`validate_process_snapshot()` 接受并返四个“original unavailable” unknown。状态表达式仅检查
unknown 是否以字面 `raw process` 开头，因此该情况被命名为 `PASS_BOUND`。

G 中 process view available 时 snapshot 必须是 required；完整性应由 closed machine codes 决定，
不能用 human-string prefix 推导。

### PF-B05 — release JSON 与 canonical rule 不一致

| file | raw checker |
|---|---|
| `PACKAGE-MANIFEST.candidate.json` | `ACCEPT` |
| `ADMISSION-POLICY-V1.1.candidate.json` | `REJECT` |
| `COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json` | `REJECT` |
| `EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json` | `REJECT` |

这不导致 receipt 误判，但违反 V2S 已决定的“所有 JSON release bytes 为 canonical”边界。

## 5. Canary completeness 专项攻击

### 5.1 排序与 node cap

创建 2047 child nodes（加 root 恰好 2048），把 canary 放在 UTF-8 排序最后文件名。
`snapshot_challenge()` 仍返回它。再加一个 child，整次扫描以
`CANARY_SCAN_NODE_CAP` 拒绝，没有部分 pass：

```text
EXACT_NODE_DOMAIN PASS entries=2048 canaries=1 ...SORT_LAST
NODE_OVERFLOW REJECT CANARY_SCAN_NODE_CAP
```

当前没找到用排序把域内 canary 放到截断后而仍 pass 的方法。但
`iterdir/readdirSync` 在 2048 gate 前已生成和排序完整 children list，资源安全未闭合。

### 5.2 file-size domain

producer 和 independent reconstruction 都对 `stat.size > 65536` 的文件不做 content canary scan。
snapshot 会记录 full-file hash，但 canary set 为空。因此：

- 明确 `file <=64 KiB` 的小域：`ACCEPT`；
- 任意 candidate-readable challenge file：`REJECT`；
- G 只有在 controller 证明所有可能携带 control canary 的文件均不超限，
  或大文件一律 fail closed 时，才能使用“完整”。

还有 TOCTOU：`stat` 为小文件后、`readFile/read_bytes` 前文件可增长，读取便可超 cap。
需要只读不可变 mount 或 fd-based bounded read。

## 6. Producer/cap 真实执行时序

对 `collectCandidate()` 的独立顺序探针得到：

```text
4097 environment rows -> ENVIRONMENT_CAP, baseCalled=0
subject size 1073741825 -> SUBJECT_CAP, baseCalled=0
proc name "01" -> PROC_PID_GRAMMAR, baseCalled=0
status.ppid="abc" -> STATUS_GRAMMAR, baseCalled=1
8193 tree errors -> TREE_ERROR_CAP, baseCalled=1, already materialized=8193
65537 visible canaries in complete rescan -> VISIBLE_CANARY_CAP
```

所以 producer 确实执行新验证；但 `FAIL_CLOSED_BEFORE_ADMISSION` 不等于 pre-allocation
safety。environment count、subject stat、proc name/count 在 base 前；tree error/string/status 在 base receipt
已构造后；new canary cap 发生在 old base canary scan 后；目录 children 在 gate 前整体物化。

## 7. Raw checker 与 process snapshot

12/12 F receipt raw bytes 通过 checker；duplicate member 由 Python raw parser 拒绝，pretty JSON
由 JS checker 拒绝。checker 的 recursive-key sort/`JSON.stringify` 与历史 base producer 同构，
对 parsed receipt 的 byte-equivalence 核心可 `ACCEPT`。

formal 仍需 controller 绑定 checker hash、绝对 Node binary/runtime，并保证 Python read、Node reopen、
binding hash read 之间文件不可被替换。

success process row 的 cmdline/status/self raw 重算是 `ACCEPT`，修改 cmdline raw 得
`PROCESS_SNAPSHOT_ROW_MISMATCH`。但 process 是 F05 predictor surface；`process_view.available=true`
时 snapshot 必须与同一 worker execution seal 关联且不可选。

## 8. 独立可复现命令与主要结果

在 Wave 025 experiment root：

```bash
python3 -m pytest -q feature-spec/collector-v1.1-candidate/tests/test_admission_v1_1.py
```

实际：`16 passed in 14.80s`。该结果只是起点。额外独立 harness 以
`importlib` 读 admission，deep-copy 一份已接受 F receipt，canonical-write 单点变异到
temporary directory，再调 `admit()`。Node harness 在子进程中对 producer/base 调用顺序加探针。

关键实际输出：

```text
RT-B01 duplicate/order cases: REJECT
RT-B02 depth6 path: ACCEPT PASS_WITH_UNVERIFIED...
RT-B04 backward timing: REJECT MONOTONIC_NESTING
RT-B05 forged subject without binding: ACCEPT PASS_WITH_UNVERIFIED...
RT-B06 wrong process leaf / etc source / tree syscall: ACCEPT PASS_WITH_UNVERIFIED...
RT-B07 unbound canary absence: ACCEPT PASS_WITH_UNVERIFIED...
WRAPPER_INSTANCE_VALIDATION: _WrappedReferencingError Unresolvable
MANIFEST_PRESENT false; ADMISSION_WITHOUT_MANIFEST_RC 0
SYNC_FORGE_STATUS CANDIDATE_ADMISSION_PASS_BOUND formal=False
```

所有额外 fixture 只在 temporary directory 或子进程；未修改 implementation、historical F、
old source/schema 或原 tests。

## 9. Formal / G 边界

### 当前允许

- 保持 `candidate / not adopted / formal=false`；
- 不写入正式 evidence chain 的本地 integration smoke；
- 在 controller 外部已限制小文件/小目录/小 process population 时，测试 failure codes、
  V2S routing 接口和 runner 整合。

### 当前禁止

- 不得把 `PASS_BOUND` 读作 formal material/source binding；
- 不得追认 F；
- 不得把 >64 KiB file 的 canary absence 解释为不可见；
- process view available 但 snapshot 缺失/不完整时，不得让 F05 进 evidence-bearing G；
- manifest/source/runtime 尚未被 controller 外部锁定时，不得启动 formal population。

### 解锁 evidence-bearing G 的最小条件

1. controller precommit 绑定 exact manifest、base source/schema、adapter、admission、checker 与
   Node/Python provider，worker 无权改写。
2. candidate schema self-contained/可解析，并在测试与 CLI 中真实验 instance；所有 release
   JSON 通过同一 canonical rule。
3. binding 位于 worker 不可改写域，绑定 role -> exact config/subject/challenge/process paths；
   解析 config bytes 并与 receipt parsed object 比较。
4. 阻断同步伪造；明确受信 producer seal 与 independent reconstruction 各自的 truth claim。
5. 增加 tree depth 和 exact operation-error provenance，或将其降级为 trusted-producer-only claims。
6. process available 时 snapshot 必填；状态由 closed machine codes 决定，不用 string prefix。
7. G challenge 要么全文件 `<=64 KiB`，要么大文件 fail closed/扩大可验 canary domain；
   directory/process/count 在 base allocation 前由 controller 限定。

```text
FORMAL: REJECT
EVIDENCE-BEARING G: BLOCKED
NONFORMAL CONTROLLED SMOKE: ALLOWED WITH EXPLICIT LIMITS
```

