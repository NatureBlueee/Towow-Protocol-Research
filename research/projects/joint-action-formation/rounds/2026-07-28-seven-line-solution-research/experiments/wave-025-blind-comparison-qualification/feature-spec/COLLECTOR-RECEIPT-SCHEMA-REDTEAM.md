# Wave 025 Collector Receipt V1 schema 独立红队

Date: 2026-08-01  
Status: `REDTEAM / NOT_AN_ADMISSION_APPROVAL`  
Target: `COLLECTOR-RECEIPT-V1.candidate.schema.json`  
Target SHA-256: `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209`  
Producer source: `attackers/leak-only-collector/collector.js`  
Producer SHA-256: `bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699`

## 1. 结论

**该 candidate schema 可以作为 V2S 的“结构 path/union 枚举输入”，但现在不能作为
collector V1 语言的精确定义，也不能单独作为 formal admission oracle。**

原因不是它没有闭合 object，而是它与真实 producer 之间存在双向差集：

1. schema 接受了 collector 不会生成的排序、重复 identity、矛盾时间、无源 canary
   和伪造 digest/length 关系；
2. collector 源码确实能生成、schema 却因未在 producer 中实施的 cap 或 grammar 而拒绝的
   receipt；
3. schema 不能从已经损失原文的 receipt 重建 environment value、raw cmdline、canary token、
   subject bytes 或 raw error，所以部分 hash/length/provenance 关系必须依赖外部冻结输入或受信
   collector 执行证据。

对 V2S 的直接含义是：可以用该 schema 生成“每个可出现 JSON pointer 必须恰好被
INCLUDE/EXCLUDE 一次”的静态覆盖证明；不能把 `schema-valid` 升格为“这是 collector 可达、
语义自洽、与原材料一致的 receipt”。在语义 validator 和 producer/admission 差集被处理前，
V2S route-completeness 状态应保持 `STRUCTURAL_ONLY / NOT_FORMALLY_ADMISSIBLE`。

## 2. 范围与方法

红队仅读：

- 逐行检查 `collector.js` 中的生成分支、排序、上限、损失性投影和时间顺序；
- 逐节检查 candidate schema 的 union、regex、number、status、environment、tree、process、
  timing 与 error shape；
- 只读 F smoke 的 12 份 `collector-features.json`；
- 从一份 F receipt deep-copy 后做单点变异，用 Draft 2020-12 validator 证明接受/拒绝；
- 对“collector 可达但 schema 拒绝”的关键主张，直接调用原 `collector.js` 导出函数，
  仅在子进程内替换 Node `fs` 返回值，没有修改 source/schema/test/F。

F 的 12 份 receipt 都通过 candidate schema，但覆盖很窄：每份只有 6 个 environment rows、
1--18 个 tree entries、0--1 个 tree errors、2 个 processes、0 或 2 个 canaries；status 都是常规
Linux decimal/TAB 文本。因此 F 能证明正常样本兼容，不能区分下面的差集。

## 3. BLOCKER：schema 接受 producer 不可达或语义矛盾的 receipt

### RT-B01 — `uniqueItems` 不是 producer identity 唯一性

`collectEnvironment()` 从 `Object.keys(environment)` 出发，key 在输出中天然唯一且排序。
schema 的 `uniqueItems: true` 只比较整个 row，因而接受：

- 两个相同 environment `key`，但 digest 不同；
- 排序被打乱的 environment rows。

相同问题出现在 tree `path`、process `pid` 与 visible-canary row identity。最小变异结果：

| mutation | schema result | producer invariant |
|---|---|---|
| duplicate environment key, different digest | `ACCEPT` | `Object.keys` 不会产生重复 key |
| swap first two environment rows | `ACCEPT` | source 在 map 前 `.sort()` |
| duplicate tree path, change `size_bytes` | `ACCEPT` | traversal 每个 relative path 只 visit 一次 |
| reverse two process rows | `ACCEPT` | source 按 numeric PID 升序 |
| duplicate PID, change cmdline hash | `ACCEPT` | 标准 `/proc` 中 PID directory identity 唯一 |

**为什么是 BLOCKER：** V2S 对 unordered bag 依赖 identity 聚合；重复 key/path/pid 会改变 count、
record atom 和 numeric multiset。只检查 row 不完全重复，不能防止 last-write、double-count 或两个实现
对同一 receipt 做出不同聚合。

### RT-B02 — tree 的 availability、path 与 truncation 语义没有闭合

schema 接受 `available=true, entries=[], errors=[], truncated=true`。源码不可能产生这个组合：
只要 `existsSync(root)` 为 true，访问必须要么生成 root `.` entry，要么生成一个 root error；
`truncated=true` 又要求在 entry cap 或深度 cap 之前至少成功观测一个 entry。

schema 也允许空字符串、绝对路径、`..` 穿越、不按 collector traversal 排序的 path，以及同一 path
同时出现在互相矛盾的 entry/error 中。`statFeature()` 的 root 只能是 `.`，child path 由已枚举
basename 递归拼接，这些都不是 producer language。

**为什么是 BLOCKER：** F04/F05 的 path、metadata、error 与 container-count 都是 predictor 输入。
如果 formal admission 允许不可达的 tree，route completeness 只能证明“把伪结构也分类了”，
不能证明它对真实 collector 语义唯一。

### RT-B03 — process count/order/truncation 的跨字段关系缺失

`collectProcessView()` 的可达关系是：

- `available=true` 时，`len(processes) = min(number_of_numeric_proc_names, 256)`；
- `truncated=true` 时 `len(processes)` 必须恰为 256；
- process rows 按 PID numeric 升序；
- 在标准 Linux `/proc` provider 中 PID 唯一。

schema 接受 `available=true, processes=[], self=<object>, truncated=true`、乱序 PID 和重复 PID/不同 row。
如果允许非标准 proc provider，源码的 `/^[0-9]+$/ -> Number` 还会把 `01` 和 `1` 折叠为同一 PID，
或生成大于 JS safe integer 的数；schema 不能代替 provider grammar。

### RT-B04 — monotonic timing 允许不可达因果顺序

两个单点变异都被 schema 接受：

- `timing.monotonic_end_ns = "0"`，而 start 保持正数；
- `collection_window.end.monotonic_ns = "0"`，而 timing interval 保持原值。

但源码调用顺序决定：

```text
collection.start.monotonic
  <= timing.monotonic_start
  <= timing.monotonic_end
  <= collection.end.monotonic
```

并且 `sum(immediate_delta_ns) + sum(input_stat_elapsed_ns)` 不能大于 timing monotonic interval。
这些是 `hrtime.bigint()` 的顺序关系，不受 wall-clock 回拨影响。

**为什么是 BLOCKER：** F06 正是 timing attack family。让不可达的时间向量进入模型，
会使“时序泄漏”与“伪造或损坏的 receipt”无法区分。

### RT-B05 — hash/length/source 只是各自合法，不是关系合法

schema 接受把 `subject_input.sha256` 改为 64 个 `0`，其余 receipt 不变。同类漏洞还包括：

- `input_contract.byte_length/sha256` 与原 config bytes 不匹配；
- environment `value_byte_length/value_sha256` 与同一 key 在 launch environment 的 value 不匹配；
- process `cmdline_byte_length/cmdline_sha256` 与 raw NUL-separated bytes 不匹配；
- file digest capture 的 length/hash 与 raw proc bytes 不匹配；
- visible canary 的 token length/hash 与实际 token 不匹配；
- `source=environment-*` 的 canary `location` 根本不是任何 environment key（最小变异
  `definitely-not-an-environment-key` 被 `ACCEPT`）。

**为什么是 BLOCKER：** 这些 length/hash/source 本身是 F01--F07 route 的可见信号。
如果它们不与冻结原材料或受信执行证据重算关联，schema 只证明 digest “长得像 digest”。

### RT-B06 — error shape 闭合了字段，没有闭合 operation provenance

`normalizedError` 本身是 closed object，各 success/error union 也没发现重叠分支。但 schema 对 error 只做
局部 shape 检查，以下矛盾全部可以结构合法：

- tree outer `path` 与 `error.path` 指向不同节点；
- process row `pid` 与 `error.path` 中的 PID 不同；
- process-self `cgroup/mountinfo/status` 的 error path 指向另一个 filename；
- timing probe 名为 `read-fixed-missing-file`，但 error `syscall/path` 来自另一个 probe；
- `/etc/hostname` 失败分支的 error path 不是该固定文件。

如果 V2S 对 error code/path/message 发送 exact/shape/ngram，这些跨字段关系必须在进 routing 前验证，
或者明确依赖 sealed collector 执行而不宣称 schema 已证明它们。

### RT-B07 — visible-canary 观测没有 completeness/truncation state

environment canary 在 source 中先无上限收集；challenge traversal 则在 `hits.length >= 2048` 时停止进入
新节点，且一个文件内的 token loop 可以一次跨过该界。receipt 只有 `visible_canaries: []`，
没有 `truncated` 或 scan-complete 信号。

所以“没有某个 challenge canary”可能意味着它不可见，也可能意味着扫描在到达它之前已被截断。
这是 F07 攻击语义的 BLOCKER，不能用 array `maxItems` 修复。需要 collector 可观测的 completeness
状态，或者 formal setup 证明输入不可触发截断并在每 slot 验证。

## 4. ADMISSION_TRADEOFF：schema 拒绝 source 可达 shape

### RT-A01 — 未在 producer 实施的 count/size caps

| field | schema restriction | collector behavior | executable result |
|---|---:|---|---|
| `environment` | max 4096 rows | map 所有 `Object.keys(process.env)` | `collectFeatures()` 输出 4097 rows |
| tree `errors` | max 8192 | error push 不增加 `entries.length`，不受 2048 cap 限制 | `collectTree()` 输出 8193 errors |
| `visible_canaries` | max 65536 | environment phase 没有 hit cap | `collectVisibleCanaries()` 输出 65537 hits |
| `subject_input.byte_length` | max 1 GiB | `readFileSync()` 后直接使用 Buffer length | source 没有 1 GiB check |
| generic decoded string | max 1,048,576 code points | `/etc/hostname` 等 read/normalize 路径没有该 cap | 1,048,577-char mutation 被 schema 拒绝 |

前三项不是纯理论：直接调用未修改的导出函数得到：

```text
{"environment_rows":4097}
{"available":true,"entries":1,"errors":8193,"truncated":false}
{"hits":65537,"first":19,"last":19}
```

对应 receipt 变异的 schema 结果是 `REJECT / REJECT / REJECT`。这些 cap 可以是合理的资源防御，
但必须在正式决定中二选一：

1. collector 在读取/append 前实施同一 cap，以 fail-closed 或显式 `truncated` 生成新版本 receipt；
2. schema 不把它们宣称为 producer invariant，把批次资源 admission 与 collector receipt language 分层。

否则可见环境可以通过增加 rows/errors/canaries 使整个 slot 变成 `NOT_QUALIFIED`，形成一个
未评估的 admission-DoS 路径。

### RT-A02 — status regex 是 Linux admission policy，不是 parser invariant

`parseStatus()` 对 allowlist key 只做 `trim()`，不验证内容。直接让原 `collectProcessView()` 读取以下
status 文本：

```text
PPid: abc
Uid: 1 2 3 4
Gid: -1
Threads: NaN
```

原 collector 输出：

```json
{"name":"agent","state":"R","ppid":"abc","uid":"1 2 3 4","gid":"-1","threads":"NaN"}
```

candidate schema 会拒绝该 process row。另一方面，`fourIdVector` 的总 `maxLength=323` 没有对每个
capture group 单独限制 80 digits，所以它反而接受第一段 317 digits 的
`<317 digits>\t0\t0\t0`。这对标准 Linux ID 不可达，却比毗邻 decimal primitive 宽。

因此当前 grammar 同时“比 parser 窄”和“比所宣称 Linux 环境宽”。如果 formal provider 只接受特定
Linux `/proc/*/status`，这可以是 admission tradeoff，但要把 kernel/proc provider 与 grammar 写入冻结
execution contract，并让 collector 在生成 success receipt 前按同一 grammar fail closed。否则 V2S 不能一方面
声称 schema 枚举了所有 legal receipts，一方面依赖没有实现的 parser contract。

### RT-A03 — number/provider 界限需要显式冻结

schema 对 PID/UID/GID/count 使用 JS safe integer 是合理的模型输入防御，但 `collectProcessView()`
对任意 digit-only directory name 直接 `.map(Number)`，没有 `Number.isSafeInteger()` 或 canonical PID-name
检查。标准 Linux `/proc` 使这个问题不触发；任意 proc provider 则可生成 unsafe PID 或 `01`/`1`
折叠。

`numberCapture.value` 只限定非负 JSON number，不能单独证明 finite/canonical lexical form；这需要严格
JSON parser 先拒绝 `NaN/Infinity`，再对 canonical receipt bytes 重算。此项不要通过放宽 V2S numeric
规则解决，而应通过冻结 provider 和 collector-side validation 解决。

## 5. SCHEMA_LIMITATION：不应试图只用 JSON Schema 表达的事

### RT-L01 — 损失性投影使部分关系无法从 receipt 重算

- environment 只保留 value length/hash，不保留 value；
- cmdline 保留 UTF-8 decode 后、删除空 segment 的 array，原 NUL placement 与 invalid UTF-8 bytes 已丢失；
- canary 只保留 token length/hash，不保留 token；
- subject 和 input config 只保留 length/hash；
- normalized error 是对原 error 的投影。

因此语义 validator 不能只读 receipt 就证明这些 digest。它需要 runner-frozen config/subject/launch
environment、权威 control registry/reveal，以及必要时的 raw proc capture；或者把证据主张降级为
“receipt 是已绑定 collector source 在隔离运行中产生的 exact bytes”。

### RT-L02 — raw JSON/UTF-8/canonical bytes 在 schema 之前已经丢失

duplicate member name、invalid UTF-8、JSON number lexical form、one-LF 和 recursive-key ordering 不是 parsed-object
schema 能证明的性质。`maxLength` 计算 Unicode code points，不是 UTF-8 bytes。必须保留当前 audit
提出的顺序：

```text
strict raw UTF-8/JSON and duplicate-key check
  -> schema
  -> exact canonical-byte recomputation
  -> semantic validator
  -> feature routing
```

### RT-L03 — producer sort 不是跨运行时的 byte-order 规范

environment 使用 JavaScript default `.sort()`，tree children 和 canary rows 使用
`localeCompare(..., "en")`。schema 不能检查顺序，而 `localeCompare` 的结果还依赖 Node/ICU provider。
F 只覆盖 ASCII-dominant 字符串，没有测到这个差异。若 V2S 对这些 list 按 bag 处理，
predictor 可不依赖 producer order；但 raw receipt reproducibility/sidecar 仍需绑定 Node/ICU 或改为明确的
byte comparator。

### RT-L04 — declarative contract 不是执行证据

`contract.network_calls=0`、`lawful_truth_api_calls=0` 和“不评分/不排序”是 producer 写入的声明。
schema 的 `const` 只证明这几个字出现了，不证明没有 network syscall、没有读取 control field 或没有
隐性评分。这些主张仍依赖 source hash/audit、runtime isolation、exec evidence 和 channel validation。

## 6. Union/regex 审计的正向与剩余边界

没有发现当前 `oneOf` 的结构重叠：hostname capture、user-info、tree available/unavailable、
process available/unavailable/read-error、process success/error、file digest success/error、number capture 和
timing probe 都由 const、required 与 `additionalProperties:false` 区分。timing probe 的三个位置也因
`timingProbe` 要求 `name`，不会被 `allOf/properties` 缺 `required` 绕过。

SHA-256 lowercase regex、stat decimal strings、signed nanosecond strings 和 `mode_octal` 与当前源码格式一致。
但这些局部正确性不会修复第 3--5 节的 identity、provenance、admission 和损失性问题。

## 7. 可执行最小反例结果

从一份 F receipt 出发的 15 个单点/单边界反例：

```text
A01 duplicate env key/different row: ACCEPT
A02 unsorted environment: ACCEPT
A03 duplicate tree path/different stat: ACCEPT
A04 truncated tree with no observation: ACCEPT
A05 unsorted process pids: ACCEPT
A06 duplicate pid/different row: ACCEPT
A07 backwards timing monotonic interval: ACCEPT
A08 collection closes before timing: ACCEPT
A09 orphan environment canary: ACCEPT
A10 forged subject digest relation: ACCEPT
R01 parseStatus arbitrary PPid: REJECT
R02 parseStatus space UID vector: REJECT
R03 4097 environment rows: REJECT
R05 subject > 1GiB: REJECT
R06 uncapped etc-hostname string: REJECT
```

额外的 source-direct 反例是 8193 tree errors、65537 canary hits与非 canonical status，输出见第 4 节。
这些命令都只在子进程内运行并读取仓库，未写入 F、schema、test 或 collector source。

## 8. V2S routing 枚举的准入条件

### 8.1 可以现在使用的部分

将此 schema 作为 **structural path grammar**，枚举：

- 根和 closed object fields；
- optional fields；
- `oneOf` 分支；
- array wildcard child path；
- scalar JSON type、const 和 nullability。

route linter 必须证明每个这样的 structural leaf 恰好有一个 INCLUDE 或 EXCLUDE，并且不把 F 的
181 个 observed path shapes 当成完整集。

### 8.2 进入 formal V2S admission 前必须满足

1. **处理 producer/schema 双向差集。** 对 caps、status grammar、proc grammar 选择并冻结：在
   collector 中实施，或从 producer-language schema 移出并放到独立 admission policy。
2. **语义 validator 在 routing 前运行。** 至少验证：
   - environment key 唯一/顺序；
   - tree path identity、entry/error 一致性、root/path/depth grammar、排序和 truncation 前提；
   - process PID 唯一/顺序、count/truncated 关系、冻结 proc/status grammar；
   - visible-canary dedupe/order、source/location 关联和 completeness/truncation；
   - monotonic interval nesting 与 sample-sum 边界；
   - operation name 与 normalized error path/syscall 的可达关系。
3. **对损失性字段使用外部证据关联。** 用冻结 config/subject/launch env/control material 重算可重算
   digest；raw cmdline/error 无法重算时，明确证据只来自 bound collector execution，不伪装成
   schema proof。
4. **保留 raw admission 层。** strict UTF-8/JSON、duplicate-key rejection、canonical bytes 与 exact receipt
   hash 都在 parsed schema 之前/之后独立验证。
5. **路由器不从 regex 猜语义。** process status 只有在 admission 已按冻结 grammar 通过后才能进
   decimal/TAB parser；其他 string 不得因“看起来像数字”而进 numeric route。
6. **完整性失败有专用状态。** 超 cap、canary scan 被截断、无法确认的外部 hash 不能静默
   丢叶子；要么产生冻结 failure code，要么显式进入 predictor 的 branch/truncated 语义。

满足上述条件后，该 schema 可以是 V2S 发行包中的一个被 hash 绑定的结构输入；
它仍不应成为“唯一语义真相”。producer source/provider contract、semantic validator 和 raw/external
evidence bindings 共同才能定义 formal admission。

