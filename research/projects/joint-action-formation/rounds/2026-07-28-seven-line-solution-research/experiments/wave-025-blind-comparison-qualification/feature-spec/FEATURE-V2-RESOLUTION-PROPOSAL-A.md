# Wave025 Feature V2 Resolution — Proposal A

状态：`COMPLETE CANDIDATE / NOT ADOPTED / NOT PRECOMMITTED / NO RETROACTIVE EFFECT ON F`

目的：为 `FEATURE-SPEC.json` 暴露的 exact-feature 歧义提出一套逐字节充分、可由两个独立实现得到唯一
结果的竞争方案。它优先保留已声明攻击能力，同时不允许“所有 included leaf 自动套用所有 transform”
这种全局 generic expansion。

本文件不修改、替代或解释性覆盖当前 spec、reference extractor、full engine、attack profile 或 F。
除非未来由独立决定采纳并在新 batch anchor 前绑定 exact bytes，本方案没有 formal 权威。

---

## 1. 设计目标与非目标

Proposal A 必须同时满足：

1. 同一 canonical receipt 在不同语言的合规实现中生成逐字节相同的 feature vector。
2. challenge、role、phase、block、slot ID、execution order、host metadata 永不进入 provider。
3. 每个 path 只运行 routing table 明确授权的 transform；未登记 path fail closed。
4. 保留 exact、lexical、shape、numeric、record、order 与 missing 攻击能力，但不借此扩大 source scope。
5. 单 receipt provider 可流式运行；不得为了 feature extraction 读取整个 batch 或 label。
6. n-gram 是每 family 直接 4096 维 block，不再进入 categorical 16,384 hashing。
7. 失败、截断、空集合、optional branch 和 unseen holdout feature 都有可区分状态。

非目标：不规定 C01–C05 以外的新 classifier；不更改 population、CI、permutation、Holm 或 qualification
阈值；不追认 F 已经冻结本方案。

## 2. Normative byte conventions

本文件中的 MUST、MUST NOT、SHALL 是 Proposal A 内部规范词。

### 2.1 基础类型

- text：UTF-8，无隐含 terminator，不做 Unicode normalization；无效 UTF-8 fail closed。
- unsigned integer：固定宽度 big-endian。
- hex：lowercase，每 byte 两字符。
- SHA-256：计算时为 32 raw bytes；JSON 中为 64 lowercase hex。
- finite number：禁止 NaN、Infinity、`-Infinity`；`-0.0` 输出前规范为 `0`。
- canonical JSON value：递归按 UTF-8 codepoint lexicographic key order，compact `,`/`:`，
  `ensure_ascii=false`；非整数 JSON number采用 RFC 8785 §3.2.2.3 serialization；artifact末尾 exactly
  one LF，嵌入 hash 的 scalar/record bytes不带LF。
- duplicate JSON key、duplicate feature identity、invalid surrogate、unknown field 均 fail closed。

### 2.2 长度前缀

所有 hash preimage 中的变长字段都使用：

```text
LP16(x) = len(x)_u16_be || x
LP32(x) = len(x)_u32_be || x
LP64(x) = len(x)_u64_be || x
```

长度以 bytes 计。超出表示范围 fail closed；不得截断或换用 varint。

### 2.3 Extended context grammar

context 不是展示型 JSON Pointer，而是唯一的 typed path：

```text
context       = "" *( "/" segment )
object key    = "k:" || BASE64URL_NOPAD(UTF8(key))
ordered index = "i:" || 16_lower_hex(index_u64_be)
unordered row = "u"
```

例：`/argv/1` 为 `/k:YXJndg/i:0000000000000001`；environment 任一 record 的 key 为
`/k:ZW52aXJvbm1lbnQ/u/k:a2V5`。

选择 typed segments 而不是 `[]/*/@0001`，是为了消除对象键与保留符、不同 index 宽度和 pointer escaping
之间的碰撞。展示层可另给 human-readable pointer；展示值不得参与 predictor identity。

## 3. Closed feature-vector interface

输出 schema 名：`WAVE025_REFERENCE_FEATURE_VECTOR_V2A`。

根对象及所有子对象 `additionalProperties=false`：

```json
{
  "schema": "WAVE025_REFERENCE_FEATURE_VECTOR_V2A",
  "resolution_id": "W025_FEATURE_V2A_BYTES_V1",
  "source": {
    "receipt_schema": "WAVE025_LEAK_ONLY_FEATURES_V1",
    "receipt_bytes_sha256": "<hex64>",
    "feature_spec_sha256": "<hex64>",
    "resolution_sha256": "<hex64>",
    "source_hash_is_predictor": false
  },
  "features": {
    "numeric": [
      {"id":["<family>","<context>","<transform>","<stat>"],"value":{"kind":"INTEGER","decimal":"0"}}
    ],
    "categorical": [
      {"id":["<family>","<context>","<transform>"],"value_sha256":"<hex64>","count":1}
    ],
    "ngram_counts": [
      {"family":"<family>","bucket":0,"count":1}
    ]
  },
  "audit": {
    "raw_leaf_count": 0,
    "included_leaf_count": 0,
    "excluded_leaf_count": 0,
    "included_paths_sha256": "<hex64>",
    "excluded_fields": [],
    "unclassified_paths": [],
    "routing_counts": {},
    "truncated_string_count": 0,
    "only_features_members_are_predictors": true
  }
}
```

### 3.1 Identity 与排序

- family enum：现有 `F01_...` 至 `F07_...` 七个 exact IDs。
- numeric transform enum：`NUMERIC_SCALAR`、`LIST_LENGTH`、`ORDERED_SERIES`、
  `UNORDERED_MULTISET`、`STRING_SHAPE`。
- numeric stat enum：`value` 或本文件定义的 series/multiset/shape stat。
- categorical transform enum：`EXACT`、`SCALAR_BAG`、`RECORD_BAG`、`INTEGER_RESIDUE_M2`、
  `..._M4`、`..._M8`、`..._M16`、`..._M256`、`BRANCH`、`TRUNCATED`、`MISSING`。
- `numeric` 按 `canonical_json(id_without_LF)` bytes lexicographic 排序；identity 必须唯一。
- numeric value只有两种closed encoding：exact integer用
  `{"kind":"INTEGER","decimal":"-?(0|[1-9][0-9]*)"}`；其他finite binary64用
  `{"kind":"BINARY64","bits_hex":"<16 lowercase hex>"}`。negative-zero bits必须规范为positive zero。
- `categorical` 按 `canonical_json(id)||raw(value_sha256)` 排序；相同 identity+digest 合并 count；
  `count` 是 1..2^63-1 的 exact integer。
- `ngram_counts` 按 family UTF-8、bucket numeric 排序；只输出 count>0 的 sparse rows；同一
  family+bucket 唯一。
- `source` 与 `audit` 不进入 predictor。

采用 structured IDs 而不是 `family|context|...` 字符串，排除了 delimiter escaping 和同名 key
覆盖。代价是 artifact 略大；这是可审计性与独立实现唯一性的合理成本。

## 4. Category、string 与 scalar hash

### 4.1 Value bytes

```text
kind 0x01 STRING: UTF8(value), no JSON quotes or escaping
kind 0x02 SCALAR: canonical JSON bytes of null/bool/number, no LF
kind 0x03 RECORD: canonical JSON bytes of object/array, no LF
kind 0x04 MARKER: exact uppercase ASCII marker declared here
```

### 4.2 Category digest

令 `I=[family,context,transform]`：

```text
SHA256(
  UTF8("W025-FEATURE-V2A-CATEGORY") || 0x00 ||
  LP16(UTF8(family)) ||
  LP32(UTF8(context)) ||
  LP16(UTF8(transform)) ||
  kind_u8 || LP64(value_bytes)
)
```

这一定义使 family、context、transform、type 与 value 全部进入 digest；string 必须使用 raw UTF-8。
被排除的替代包括：JSON-quoted string、只把 context 放在外层 row、无长度的 NUL 拼接、hash 原始秘密以外
的 host/label 字段。最强剩余假绿是 role 编码使用跨 split 全新随机 codebook；exact digest 不会泛化，
只能依赖 shape/ngram/record/numeric attack 或专门 decoder。

### 4.3 Exact、record 与 bag

- `EXACT`：对 routing table 授权的 scalar 使用 kind 0x01/0x02。
- `RECORD_BAG`：对完整 list item 使用 kind 0x03；record object key order canonical，list 内 record order
  不进入 digest；重复 identical records 增加 count。
- `SCALAR_BAG`：对 ordered list 的每个 scalar，另以 list base context、kind 0x01/0x02 发出无序 bag。
- `BRANCH` markers：`SUCCESS`、`ERROR`、`NULL` 三者之一。
- residues：value bytes 是 canonical nonnegative JSON integer，context 保持原 numeric context。

Record bag 不代替 scalar features；它保存字段关联。只允许 routing table 点名的 list 做 bag，F06 timing
array 不因“也是 list”而自动获得 bag。

## 5. String transform

对每个明确带 `S` 的 string route：

1. emit `EXACT` category；
2. shape 基于完整 string；
3. emit context-local `TRUNCATED` category，kind 0x04，value 为 `TRUE` 或 `FALSE`；
4. 执行 n-gram。

带 `G` 的 string route执行1、3、4，但不做shape；带 `X` 的 SHA/digest route只执行 exact category，
不执行 shape、truncated、ngram。

### 5.1 Shape units

`STRING_SHAPE` 的 stat 与 exact 定义：

- `byte_length`：UTF-8 bytes 数；
- `codepoint_length`：Unicode scalar values 数；含 unpaired surrogate 的输入在 UTF-8 validation 已失败；
- `ascii_alpha`：codepoint ∈ `[A-Z]∪[a-z]`；
- `ascii_digit`：codepoint ∈ `[0-9]`；
- `slash/dot/dash/underscore/colon`：对应 ASCII codepoint 次数；
- `whitespace`：仅 ASCII `HT LF VT FF CR SPACE` 六个 codepoints；
- `non_ascii_codepoint`：codepoint > U+007F 的数量。

Proposal A 排除“non-ASCII UTF-8 byte count”，因为它与 `byte_length-codepoint_length` 高度重复，并使一个
字符按编码宽度重复计数。代价是失去直接区分 2/3/4-byte 非 ASCII 字符总量的单一 coordinate；
byte/codepoint length 与 n-gram 仍保留该信息。

### 5.2 Overlength

- 若 UTF-8 byte length ≤4096：形成一个 scan segment `[全部 bytes]`，TRUNCATED=`FALSE`。
- 若 >4096：形成两个独立 scan segments `[first 2048, last 2048]`，TRUNCATED=`TRUE`。
- exact category 与 shape 永远基于完整 string，不基于 scan window。
- n-gram 只在各 segment 内生成；MUST NOT 把 first segment 尾部与 last segment 头部拼成跨断点 gram。

Provider 可用 incremental SHA/shape、first buffer 与 2048-byte ring buffer 流式完成，不需保留完整长
字符串。排除“只在 true 时发 flag”，因为它混淆 false 与 missing。

## 6. Direct n-gram block

对每个 scan segment 内的每个 n=1,2,3,4 contiguous byte gram：

```text
D = SHA256(
  UTF8("WAVE025_UTF8_NGRAM_V2A") || 0x00 ||
  n_u8 || LP16(gram)
)
bucket = U32_BE(D[0:4]) mod 4096
```

因为 n≤4，LP16 是固定且仍显式的。gram 不得跨 string 边界，也不得跨 overlength 的中间缺口。每个
occurrence 给该 receipt 的 family/bucket count 加一；不同 string 与不同 n 共享同一 family 4096 block。
ngram row 不包含 context，不进入 categorical model hash。

选择“含 n、前四 bytes、big-endian、direct block”，排除了：

- 不含 n：相同 bytes 可能跨 n 产生不必要语义碰撞；
- full digest modulo：同样近似均匀但不能从 spec 的 4096 block 推出，且与 prefix 实现不兼容；
- per-context 4096 block：维数随路径膨胀；
- categorical rehash：破坏 direct 4096 position 并产生第二层碰撞。

最强假绿：4096 buckets 仍会 collision，攻击者可构造抵消或高阶 code；共享所有 n 也丢失 n 身份。选择它
是继承原 spec 的 bounded attack，不能宣称覆盖任意 lexical decoder。成本是每 family 4096 sparse coordinate
和完整 byte scan 上限 4096。

## 7. Numeric semantics

### 7.1 Detection

- native JSON integer/finite number；或 routing table 标为 numeric 且匹配 `-?(0|[1-9][0-9]*)` 的 string。
- 不接受 `+1`、leading zero、scientific notation 或 decimal point string。
- integer 在 summary/category residue 前保持 arbitrary precision。JSON non-integer token按 correctly-rounded
  ties-to-even解析为binary64。纯integer series的sum/delta保持exact integer；只要series含binary64，所有
  arithmetic按观察顺序逐步binary64 round-to-nearest-ties-even；unordered multiset先按IEEE totalOrder排序再
  运算。模型输入时integer correctly-round至binary64；溢出或nonfinite fail closed。

### 7.2 Scalar、ordered series、unordered multiset

模式由 routing table 决定，不能由运行时 `len(values)==1` 猜：

- `D` direct scalar：一个 `NUMERIC_SCALAR/value`。
- `O` ordered list：每个 index 产生 index context 的 `NUMERIC_SCALAR/value`；list base 另产生
  `ORDERED_SERIES` 13 项。即使 n=1 也产生完整 13 项。
- `U` repeated unordered context：产生 `UNORDERED_MULTISET` 的
  `count,sum,min,max,lower_middle,upper_middle`；n=1 仍用这 6 项，不改成 `value`。

Ordered series exact outputs：

`count,sum,min,max,first,last,lower_middle,upper_middle,adjacent_absolute_delta_sum,
adjacent_absolute_delta_max,positive_step_count,negative_step_count,zero_step_count`。

n=1 时两个 delta 为 0、三种 step count 为 0。空 list 没有 series row，但有 `LIST_LENGTH/value=0`。
middle 基于升序 values：lower=`[(n-1)//2]`，upper=`[n//2]`。

所有 routing table 点名的 list 发 `LIST_LENGTH/value`；若 list 位于 unordered repeated record 内，其多个
length 作为 `UNORDERED_MULTISET`，不是 duplicate key。

选择 route-declared mode 排除了 reference 的 data-dependent singleton shortcut和 engine 的“一切 numeric
都是 13 项 series”。它多保留 ordered position与delta攻击能力，同时不为无序 tree/process records伪造顺序。
成本是 ordered arrays 的坐标增加；collector 已有硬上限，仍可流式。

## 8. Exact routing table

代码：`E` exact category；`N[D/O/U]` numeric mode；`R` registered residues；`S` exact+shape+truncated+
ngram；`G` exact+truncated+ngram但不做shape；`X` exact-only digest；`Brec/Bscalar` record/scalar bag；
`L` list length；`Br` branch category。

任何未匹配 path fail closed。`/**` 只在该行列出的 closed schema 子树内展开，不是任意 JSON。

### F01_PUBLIC_INPUT_BYTES

| path | transforms |
|---|---|
| `/input_contract/byte_length` | E, N[D], R |
| `/input_contract/sha256` | X |
| `/subject_input/byte_length` | E, N[D], R |
| `/subject_input/sha256` | X |

`/input_contract/parsed/schema`、`/subject_input/path` 按原 spec excluded。

### F02_ARGV_ENV_CWD

| path | order/context | transforms |
|---|---|---|
| `/argv` | ordered | L |
| `/argv/{i}` | exact index | S, Bscalar at list context |
| `/environment` | unordered records | L, Brec |
| `/environment/*/key` | unordered wildcard | S |
| `/environment/*/value_byte_length` | unordered wildcard | E, N[U] |
| `/environment/*/value_sha256` | unordered wildcard | X |
| `/cwd` | direct | S |

### F03_HOSTNAME_IDENTITY

- `/hostname/os_hostname` 与 `/hostname/etc_hostname`：先发 Br；`os_hostname/ok` 用 E；success string
  value 用 S，error object按 error routing。V2A closed schema要求 success value是 string；其他类型fail closed。
- `/identity/{pid,ppid,uid,euid,gid,egid}`：E,N[D],R。
- `/identity/groups`：unordered scalar multiset，L；每个值 E,N[U],R,Bscalar。
- `/identity/user_info`：Br；success 的 `username,homedir,shell` 用 S，`uid,gid` 用 E,N[D],R；error
  branch 按 error routing。
- F03 error routing：`name,code,syscall,path,message` 的 nonnull string用 S；`errno` 若 decimal integer用 E,N[D],R，
  否则用 S；null 用 E。

### F04_DIRECTORY_AND_SHARED_STATE

适用于 `/directory_trees/{challenge,cwd,out,tmp}`：

- tree `available,truncated`：E；`entries/errors`：L。
- `entries`：unordered Brec。
- `entries/*/path` 与 optional `symlink_target`：S；symlink_target presence 用 Br。
- `entries/*/type,mode_octal`：E only。
- `entries/*/{uid,gid,size_bytes,inode,device,nlink,mtime_ns,ctime_ns}`：N[U]，无 residue、无 exact
  category。
- `errors`：unordered Brec；`errors/*/path` 用 S；nested error fields用 F04 error routing。
- F04 error routing：`name,code,syscall,path,message` 的 nonnull string用 S；`errno` integer用 E,N[U]，
  不做 residue；null用 E。

### F05_PROCESS_NAMESPACE_FD

- `/directory_trees/self-fd` 使用 F04 tree structural routing，但 family改为F05且nested error改用下述F05
  error routing。
- `/process_view/available,truncated`：E；optional top error用 Br+F05 error routing。
- `/process_view/processes`：unordered，L+Brec；每项 success/error 发 Br。
- process success `pid`：N[U]+R；`cmdline_byte_length`：N[U]；`cmdline_sha256`：X；
  `pid_namespace,mount_namespace`：G，不做 string shape。
- `cmdline`：每个 process 内 ordered，per-index S，并在 cmdline base Bscalar；per-process length 汇入
  U；不把不同 process 的 argv position合并成一个 ordered series。
- process status 的 `pid/ppid/uid/gid/threads` decimal strings：N[U]+R；`name,state`：G；
  optional absent status field由 frozen categorical missing处理。
- `/process_view/self`：null/success Br；`cgroup,mountinfo,status` 各自 success/error Br；success
  `byte_length` N[D]、`sha256` X；namespace G。
- F05 error routing：`name,code,syscall,path,message` 的 nonnull string用 S；decimal `errno,pid,ppid`
  用 E,N[U],R；其他nonnull scalar E；null用 E。

### F06_TIMING_AND_ERRORS

- direct clocks/durations
  `wall_clock_start_ms,wall_clock_end_ms,monotonic_start_ns,monotonic_end_ns` 及
  collection window 的四个值：N[D]+R。
- `process_uptime_seconds,os_uptime_seconds` capture：Br；numeric value N[D]；error用 F06 error routing。
- `immediate_delta_ns,input_stat_elapsed_ns`：ordered numeric，L+N[O]+R per index。
- `error_shape_probes`：ordered records，L；不做 record bag。每个 index 的 `name` S、`ok` E、
  `elapsed_ns` N[D]+R、error Br+F06 error routing。
- F06 error routing：所有 nonnull scalar E；decimal errno N[D]+R；所有 nonnull string shape、
  truncated、ngram。
- `collection_window/start,end` 保持不同 object contexts；不得 center 或改写成 batch-relative time。

### F07_VISIBLE_CANARY

- `/visible_canaries`：unordered，L+Brec。
- `*/source`：G，无 shape。
- `*/location`：S。
- `*/token_byte_length`：N[U]，无 residue。
- `*/token_sha256`：X。

这保留 D1/D0 visible canary 攻击，但不会把秘密 token、private family 或 expected role从外部 join 进来。

### Global excluded

`/schema`、`/collector_version`、`/contract/**`、`/input_contract/parsed/schema`、
`/subject_input/path` 只进入 excluded audit。它们的 value digest用于审计，不是 predictor。

## 9. Missing、null、empty 与 branch

- null 是观察到的 scalar，用 `EXACT` 或 `BRANCH=NULL`，不是 missing。
- empty list 有 `LIST_LENGTH=0`；不伪造一个 record。
- schema union/optional field必须发 `BRANCH=SUCCESS|ERROR|NULL`；同一对象只发一个。
- calibration extraction 完成后，以不看 label 的方式冻结 categorical context universe，即所有
  `[family,context,transform]`。对某 row 在 universe 内完全没有 value 的 context，加入
  `MISSING` category，kind 0x04、marker=`MISSING`、count=1。
- numeric feature universe同样由 calibration identity冻结；缺 numeric用 median fill和独立 numeric
  missing indicator。all-missing identity不应存在；若被外部 registry强制声明则 fill/center=0、scale=1。
- holdout 出现 calibration 未见 numeric identity：记录 `UNSEEN_HOLDOUT_NUMERIC_IDENTITY` 并令该
  classifier abnormal，不能静默 ignore 后宣称 chance。
- holdout 新 categorical value/context可进入 fixed hash block，但必须审计；C01 candidate vocabulary仍只
  来自 calibration，不重选。

排除“absence=zero”，因为它制造假绿；排除为每个 optional leaf无条件发几十个 MISSING，因为 branch
marker已能无歧义表示 union，重复 missing会放大同一事实。

## 10. Model preprocessing resolutions

### 10.1 Quantile

对 calibration observed numeric values升序 `x[0..n-1]`，采用 R-7：

```text
h=(n-1)*p
j=floor(h), g=h-j
Q(p)=(1-g)*x[j]+g*x[min(j+1,n-1)]
```

`median=Q(.5)`，`IQR=Q(.75)-Q(.25)`；`scale=IQR/1.349` if IQR>0 else 1。计算使用 IEEE-754
binary64、round-to-nearest-ties-even；输入 integer先做 correctly-rounded binary64 conversion。missing fill
median；center median；需要 clip 的 classifier clip至[-8,8]。

排除 nearest-rank、Tukey hinges、data-dependent quantile library default和 `max(scale,1)`。后者会压掉小
幅 timing signal，增加假绿；Proposal A 接受 IQR 很小时放大噪声的 false-fail 风险，并依靠 T、block
randomization与 host-only audit暴露它。

### 10.2 Signed categorical model hash

对 categorical row 的 identity `I` 与 raw 32-byte value digest `V`：

```text
D = SHA256(
  UTF8("WAVE025_CATEGORICAL_MODEL_HASH_V2A") || 0x00 ||
  LP16(UTF8(family)) || LP32(UTF8(context)) || LP16(UTF8(transform)) || V
)
bucket = U32_BE(D[0:4]) mod 16384
sign = +1 if (D[31] & 1)==1 else -1
amplitude = sign * log1p(min(count,255))
```

同 family/bucket collision求 amplitude algebraic sum。bucket使用 prefix、sign使用末 byte，避免把同一 bits
同时承担位置与符号。raw strings永不进入 model hash。

### 10.3 Direct n-gram preprocessing

`amplitude=log1p(min(count,255))` 放入该 family 的 direct bucket；无 sign、无第二层 hash。

### 10.4 Family normalization

对 C02/C05，每 family block由 robust numeric+numeric-missing、signed categorical 16384、direct ngram
4096 拼接；计算 binary64 L2 norm。norm>0 时整 block除以 norm，另保留一个 `log1p(norm)` coordinate；
norm=0 时 block保持0且 norm coordinate=0。C03/C04使用 unnormalized numeric、numeric missing、category
bucket presence和ngram bucket presence。C01使用 raw numeric/category/ngram count candidates，不使用 hash
collision后的值。

## 11. Handwritten golden-vector cases

这些 case 是规范输入与预期规则，不引用任何实现输出。digest写成明确公式，避免先运行代码再把结果
抄成“golden”。正式采用前应把公式求值结果人工/双工具复核后冻结为 machine-readable fixtures。

### G01 raw UTF-8 string category

输入 route：F02 `/cwd`，value=`"A"`。预期：category value bytes为单 byte `0x41`，不是 JSON bytes
`0x22 0x41 0x22`；identity transform=`EXACT`；另有 shape、TRUNCATED=FALSE和 ngrams。

### G02 Unicode shape unit

输入：F02 `/cwd`=`"é"`。预期：byte_length=2、codepoint_length=1、non_ascii_codepoint=1、
ascii_alpha=0；n=1产生两个 byte grams，n=2产生一个。

### G03 SHA leaf exact-only

输入：`/input_contract/sha256`=`"00"*32`。预期：恰好一个 F01 `EXACT` category；该 leaf不产生 shape、
TRUNCATED或 ngram row。

### G04 ordered argv + scalar bag

输入：`argv=["x","y"]`。预期：LIST_LENGTH=2；两个 exact index contexts分别为 i=0/i=1；list base有
SCALAR_BAG(x)=1、SCALAR_BAG(y)=1；交换输入后 ordered identities交换但 bag不变。

### G05 unordered environment permutation

输入：environment records `{key:"A",...}`、`{key:"B",...}`。交换 list order后，record bags、wildcard
scalar categories、shape multisets、list length全部逐字节相同。

### G06 duplicate record count

输入：同一个 canonical environment record两次。预期：该 RECORD_BAG digest count=2；record keys的
value categories也各 count=2；LIST_LENGTH=2。不得生成 duplicate JSON feature rows。

### G07 canonical record key order

输入 record A insertion order `key,value_byte_length,value_sha256`，record B反向 insertion order但值相同。
预期：canonical record bytes相同，RECORD_BAG digest相同。

### G08 empty list

输入：`visible_canaries=[]`。预期：F07 LIST_LENGTH/value=0，无 RECORD_BAG row；在 calibration context
universe含 wildcard canary contexts时，模型阶段为该 row注入对应 MISSING categories。

### G09 direct numeric scalar与 residue

输入：F01 `/input_contract/byte_length`=7。预期：NUMERIC_SCALAR/value=7；EXACT scalar category；residue
m2=1,m4=3,m8=7,m16=7,m256=7。不得生成13个 singleton series stats。

### G10 ordered numeric series

输入：F06 `immediate_delta_ns=[3,1,4]`。预期：LIST_LENGTH=3；三个 index scalar values；base series：
count=3,sum=8,min=1,max=4,first=3,last=4,lower_middle=3,upper_middle=3,
abs_delta_sum=5,abs_delta_max=3,positive=1,negative=1,zero=0。

### G11 singleton ordered series

输入：F06 `input_stat_elapsed_ns=[7]`。预期：index value=7；base series 13 项：count=1、sum/min/max/
first/last/lower/upper均7，两个 delta=0，三种 step count均0。base不得改名为 `value`。

### G12 overlength scan

输入 string UTF-8 bytes=`a*2049 || b*2048`（4097 bytes）。预期：full exact hash吃全部4097 bytes；shape
byte/codepoint length均4097；TRUNCATED=TRUE；两个独立 ngram segments分别为`a*2048`和`b*2048`。
被丢弃的是第2049个`a`，不是任意中间片段；不得产生一个末尾`a`连接开头`b`的伪 n=2 gram，也不得
产生任何跨该缺口的 n=3/4 gram。

### G13 n-gram preimage与 direct block

输入 scan=`ab`。预期 occurrence：n1 `a`、n1 `b`、n2 `ab`；每个 bucket严格按
`SHA256(domain||00||n_u8||LP16(gram))[0:4]` big-endian mod4096；count直接累加至F-family 4096 block，
不得再走 categorical 16384 hash。

### G14 branch distinction

输入 A：`process_view/self=null`；B：success object；C：error branch。预期同一 branch context分别只有
BRANCH=NULL/SUCCESS/ERROR；null不叫 MISSING，未选择 branch的子字段不额外重复几十个 MISSING。

### G15 calibration missing category

两条 calibration rows：row1在 context C有 EXACT(v)，row2无 C。冻结 universe后 row2得到
`[family,C,MISSING]`、marker MISSING、count1；row1不得同时得到 missing。构造过程不得读取 label。

### G16 category model hash

输入 categorical row family F02、context C、transform EXACT、value digest V、count=300。预期 model
preimage按10.2；bucket取D前4 bytes，sign取D[31]低bit，幅度为`sign*log1p(255)`而非log1p(300)。

### G17 quantile

calibration observed values `[0,10]`。预期 Q.25=2.5、median=5、Q.75=7.5、IQR=5、scale=5/1.349；
不是nearest-rank，也不是scale floor 1以外的 library default。

### G18 transform routing negative case

输入 F07 source=`"environment-value"`、location=`"CANARY"`、token_sha256为64 hex。预期 source有
EXACT+ngram但没有 shape；location有完整S；token SHA只有X。generic“所有F07 string都shape”实现必须失败。

### Golden provenance

G01–G18 是从本文件公式正向手写的规范 case；没有运行 reference extractor、full engine 或其他 feature
provider来生成 expected digest。当前故意保留 digest formula而不填写实现产出的 hex，防止把任一现有实现
反向变成权威。只有未来两个独立的小型公式求值器给出相同 hex，并经人工检查 preimage bytes 后，才可把
hex 纳入 machine fixture。

## 12. F-shape routing self-check

只读枚举 F 的12份 collector receipts 得到181种去 index 后的 scalar/list path shapes。逐项对照本 routing
table：

- transport/contract/input fixed paths全部落入 Global excluded；
- F01四个实际 predictor leaves全部覆盖；
- F02 覆盖 argv、environment 三字段与 cwd；
- F03 覆盖 hostname capture、identity scalars/groups、success user_info；
- F04 覆盖四棵普通 tree 的 availability/truncation、entries、empty errors；
- F05 覆盖 self-fd symlink与error、process success records/cmdline/status/namespaces、process self receipts；
- F06 覆盖 direct clocks、两种 uptime capture、两组 ordered samples、error probes与collection window；
- F07 覆盖 empty/nonempty canary list及四个 record fields。

没有 F observed included path落入默认拒绝。该检查只证明 F shapes闭合；unobserved但closed-schema允许的
error/null/optional branches由各 family 的 Br/error routing覆盖，正式采用前仍必须用 schema-derived route
linter证明“每个 union branch恰好一条 route”，不能把 F coverage冒充未来 schema completeness。

## 13. Non-retroactivity

F 的 precommit只绑定 V1 FEATURE-SPEC bytes，没有绑定本 Proposal A、V2A schema、golden manifest或未来
provider source。Proposal A 即使随后被采纳，也只能冻结新的 batch；它不能追认 F 当时已经具有 V2A
唯一语义，不能用于升级、重算或覆盖 F 的正式结论。F 仅可作为非正式工程 fixture 检查未来实现。

## 14. Independent conformance procedure

正式采纳前至少需要：

1. 将本文件收敛为 closed JSON spec+JSON Schema，冻结 raw byte hash；
2. 人工建立 G01–G18 machine fixtures，digest由两个互不依赖的小工具分别求值；
3. 实现 A 只能读取规范和 fixtures，不读 reference/full engine；实现 B 同理；
4. 对 fixtures 与一组未公开 holdback receipts 比较 exact output bytes；
5. differential mismatch一律阻断，不用多数表决；
6. fuzz duplicate key、Unicode、array order、empty/singleton、optional branch、numeric extremes、超长边界；
7. 只有新 batch precommit同时绑定 feature spec、resolution、schema、golden manifest与 provider source bytes后，
   才能形成 formal evidence。

## 15. 选择代价与最强剩余失败

| 选择 | 排除的替代 | 保留能力 | 最强剩余假绿/成本 |
|---|---|---|---|
| typed context | `[]/*/@`自由文本 | order与bag身份唯一 | artifact更长；错误routing仍可漏path |
| path-specific routing | generic all-leaf transforms | 防越权且保留声明攻击 | 新collector字段必须显式升级，否则fail closed |
| raw UTF-8 exact hash | JSON-quoted string | exact byte identity | unique codebook不泛化 |
| structured record bag | 只flatten leaves | 字段关联、重复记录 | 全新record digest不泛化；canonicalization成本 |
| ordered+bag双视图 | 只ordered或只bag | 顺序与集合攻击并存 | feature数增加、碰撞/多重比较负担增大 |
| route-declared numeric mode | len=1 shortcut/all-series | 独立实现唯一、保留顺序 | ordered arrays坐标增加 |
| direct shared4096 ngram | categorical二次hash/per-context block | bounded lexical generalization | collision、n身份在bucket后丢失、每family 4096维 |
| codepoint non-ASCII | UTF-8 high-byte count | 字符级morphology | 单坐标不直接表示编码宽度分布 |
| explicit false/true truncation | true-only counter | false≠missing | 每string增加category |
| R-7、no scale floor | library default/max(scale,1) | 小幅numeric/timing敏感度 | 小IQR放大噪声，false-fail风险 |
| fixed signed hash | implementation-local hash | 模型bytes唯一 | 16384 collision与sign cancellation |
| calibration-frozen missing | absence=0/holdout vocabulary | C01 total mapping与无holdout适应 | universe大；新holdout numeric identity需abnormal |

最重要的边界：Proposal A 仍是有限攻击族。即使它被正确实现并检测到 D0/D1，也不能证明 collector 未覆盖
的 channel、cryptographic unique code、跨调用 adaptive leak 或 4096/16384 collision attack 不存在。
它解决的是“已声明 feature mapping 必须唯一且可复核”，不是“所有泄漏已被穷尽”。
