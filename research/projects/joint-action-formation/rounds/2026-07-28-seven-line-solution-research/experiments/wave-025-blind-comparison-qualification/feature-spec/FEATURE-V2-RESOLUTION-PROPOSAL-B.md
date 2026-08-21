# Feature V2 Resolution Proposal B

状态：`INDEPENDENT_COMPETING_PROPOSAL_NOT_ADOPTED`  
日期：2026-08-01  
解除目标：`FORMAL_BLOCKER_NORMATIVE_UNDERDETERMINATION`  
不得直接用于 formal run；必须先经选择、写回权威 spec、重新绑定 profile，并通过独立 conformance。

## 0. 独立性声明

本方案只基于：

- `FEATURE-SPEC.json`；
- `reference_extractor.py` 及其 tests，且只把它们视为 non-authoritative implementation；
- `EXECUTABLE-ATTACK-PROFILE.json`；
- `NORMATIVE-COMPLETENESS-AUDIT.md` 与其中的 11 个 minimal pairs。

本方案没有读取：

- `full-evaluator-engine/engine.py`；
- 任何 engine differential audit；
- 任何 Proposal A。

F smoke 的结果不参与本方案的语义选择。方案中的选择来自原 spec 已声明的攻击能力、类型语义、跨语言确定性和最小发射原则；不能因为某个选择更接近 F 的既有输出而获得优先权。

## 1. 选择原则

Proposal B 使用五条约束：

1. **最大保留已登记攻击能力**：exact category、record association、ordered events、numeric order、string morphology、n-gram、integer residues 与 signed hashing 都继续存在。
2. **语义最小**：一个 transform 只产生其名字要求的 feature；不把递归遍历本身当成新增 predictor 的授权。
3. **类型不坍缩**：string `"1"`、number `1`、boolean `true` 与 null 永远有不同 typed bytes。
4. **跨语言可重建**：hash preimage 只依赖显式 bytes、big-endian length frames、exact rational 与 IEEE-754 的已定义基本运算，不依赖某一语言的 `repr`、字典顺序或默认 quantile。
5. **未知即失败**：未知 path、未知字段、非法 Unicode、超长 frame、numeric identity collision 或 holdout-only numeric identity 都 `NOT_QUALIFIED`，不静默忽略或偷偷新增 generic transform。

## 2. 公共 byte primitives

下文所有 `||` 表示 byte concatenation。

Byte 公式中的 quoted domain literals 一律是所示 ASCII bytes，不包含引号或末尾 NUL/LF。

### 2.1 整数与 framing

- `U32(n)`：无符号 32-bit big-endian，范围 `0..2^32-1`。
- `U64_DEC(n)`：无符号 64-bit 的最短 ASCII 十进制，无符号、无前导零；零只能写 `"0"`。
- `FRAME(x) = U32(len(x)) || x`。
- 任一被 frame 的 byte string 超过 `2^32-1`，或聚合 count 超过 `2^64-1`，立即失败。

所有 hash preimage 都对每个可变字段使用 `FRAME`。固定 domain 也 frame，使 preimage 无需依赖分隔符不能出现在值中的假设。

### 2.2 Unicode 与 JSON strings

- 输入 JSON 必须解码为 Unicode scalar values；lone surrogate 即失败。
- 不执行 NFC、NFD、case folding 或 locale conversion。
- UTF-8 必须是最短、合法编码。
- feature artifact 的 JSON string bytes 规则为：`"` 和 `\` 必须转义；U+0008/0009/000A/000C/000D 分别使用 `\b/\t/\n/\f/\r`；其余 U+0000..001F 使用小写 `\u00xx`；其他 scalar 直接写 UTF-8；禁止 `\/` 和对可直接编码字符使用 `\u`。

### 2.3 Exact rational number

所有合法 JSON number lexeme 先被解释为十进制有理数，不经过 binary64：

1. 按 JSON number grammar 拆出 sign、integer digits、fraction digits、exponent；
2. 形成精确整数 numerator 与 `10^k` denominator；
3. 约分到 `gcd(|n|,d)=1` 且 `d>0`；
4. 所有正零和负零统一为 `n=0,d=1`。

只有 routing table 明确标记为 `DECIMAL_INTEGER_STRING` 的 string 才可按相同方式解析，且 grammar 必须是 `0|-?[1-9][0-9]*`。其他看起来像数字的 strings 仍然是 strings；禁止按字段后缀猜测。

数值 feature 用一对 canonical ASCII decimals 表示：`numerator` 是 `0` 或无前导零的负/正整数，`denominator` 是无前导零的正整数。

### 2.4 Typed Value Encoding：`TVE2`

`TVE2` 是 category 与 record-bag 的唯一 scalar/record encoding：

| JSON value | bytes |
| --- | --- |
| null | `0x00` |
| false | `0x01` |
| true | `0x02` |
| number | `0x03 || FRAME(numerator_ascii) || FRAME(denominator_ascii)` |
| string | `0x04 || FRAME(exact_utf8)` |
| array | `0x05 || U32(count) || FRAME(TVE2(item_0)) ...`，保留原顺序 |
| object | `0x06 || U32(count) || FRAME(key_utf8) || FRAME(TVE2(value)) ...`，keys 按 raw UTF-8 bytes 升序 |

对象中重复 key 在 JSON parse 阶段即失败。`TVE2` 不保留 JSON number 的表面 spelling，因此 `1`、`1.0` 与 `1e0` 是同一数值；它保留 JSON type，因此 string `"1"` 不同。

## 3. Context identity

Context 不是自由拼接的字符串，而是 typed segment sequence：

```text
CTX2 = FRAME("WAVE025_CONTEXT_V2") || U32(segment_count) || SEG_0 ... SEG_n
KEY(name)      = 0x01 || FRAME(name_utf8)
ORDERED(index) = 0x02 || U32(index)
BAG_ITEM       = 0x03
DERIVED(name)  = 0x04 || FRAME(name_ascii)
```

- `KEY` 表示 JSON object member。
- `ORDERED` 只允许出现在 routing table 标为 ordered 的 array，index 从 0 开始。
- `BAG_ITEM` 只允许出现在明确登记的 record/multiset bag；原始 index 不进入 identity。
- `DERIVED` 只允许使用本方案登记的固定 transform id，例如 `residue.2`。

Predictor artifact 保存 `context_hex = lowercase_hex(CTX2)`。人类可读 JSON Pointer 可以放入独立 audit artifact，但不得成为第二个 predictor identity。这样既消除 `/0`、`/@0000`、`*` 的歧义，也避免真实 object key 与 marker 碰撞。

例：

- `/cwd`：`00000012574156453032355f434f4e544558545f5632000000010100000003637764`
- `/argv/0`：`00000012574156453032355f434f4e544558545f5632000000020100000004617267760200000000`
- `/environment/<bag-item>`：`00000012574156453032355f434f4e544558545f563200000002010000000b656e7669726f6e6d656e7403`

## 4. Closed predictor artifact 与 vector shape

### 4.1 唯一输出结构

```json
{
  "schema": "WAVE025_FEATURE_VECTOR_V2_B",
  "features": {
    "numeric": [
      {
        "family": "F02_ARGV_ENV_CWD",
        "context_hex": "...",
        "stat": "shape.byte_length",
        "numerator": "7",
        "denominator": "1"
      }
    ],
    "categorical": [
      {
        "family": "F02_ARGV_ENV_CWD",
        "context_hex": "...",
        "value_sha256": "lowercase-64-hex",
        "count_u64": "1"
      }
    ]
  }
}
```

成员集合是 closed：

- root 只能有 `schema`、`features`；
- `features` 只能有 `numeric`、`categorical`；
- numeric entry 恰有五个成员；categorical entry 恰有四个成员；
- 禁止额外 extractor version、source hash、audit 或 debug member 混入该 artifact。

Numeric identity 是 `(family_utf8, raw_CTX2, stat_ascii)`。同一 identity 只能出现一次；重复即实现错误。Categorical identity 是 `(family_utf8, raw_CTX2, value_digest_32)`，重复 occurrence 聚合为 `count_u64`。

排序：numeric 按上述 identity 三元组的 raw bytes 字典序；categorical 按其 identity 三元组 raw bytes 字典序。artifact 使用递归 UTF-8 key sort、compact JSON、上节 string escaping，并恰有一个最终 LF。artifact 内没有 JSON numeric tokens，从而不依赖语言的 float serializer。

### 4.2 Model matrix shape

- N-gram：F02..F07 每个 family 固定 4096 个 bucket columns；缺失 sparse entry 等于 0。
- Hashed categorical：每个 family 固定 16384 个 bucket columns；缺失等于 0。
- Ordinary numeric：column registry 是 calibration receipts 中全部 numeric identities 的 label-blind union，按 identity 排序，并在读取 calibration labels 前冻结和 hash-anchor。
- Holdout 缺少已登记 numeric identity 是 missing；使用 spec 的 median fill 与 missing indicator。
- Holdout 出现 calibration registry 未登记的 numeric identity，不得忽略或扩列，结果为 `NOT_QUALIFIED_SCHEMA_DRIFT`。
- C01 对 numeric 使用 exact rational equality/ordering，对 categorical 使用未哈希的 `(family,context,digest,count)`；C02/C05 和 C03/C04 再按原 spec 进入固定 hashing/presence blocks。

该规则给每一挑战形成一个冻结、可重放的 column shape，同时不让 holdout 内容改变 calibration fit。

## 5. Exact category 与 record bag

### 5.1 Category digest

```text
CATEGORY_PREIMAGE =
  FRAME("WAVE025_CATEGORY_V2") ||
  FRAME(family_utf8) ||
  FRAME(raw_CTX2) ||
  FRAME(TVE2(value))

value_sha256 = lowercase_hex(SHA256(CATEGORY_PREIMAGE))
```

Family 和 context 都进入 hash。`value_sha256` 的 hex 只是输出表示；后续 model hashing 必须解码为 raw 32 bytes。

### 5.2 Record bag

一个登记为 record bag 的 array：

- 每个完整 item 以 `TVE2(item)` 作为一个 atom；
- category context 为 array context 加 `BAG_ITEM`；
- 相同 record digest 聚合 count；
- 不保留原始 item index；
- whole-record category 不自动授权任何 leaf transform。只有 routing table 单列的 child path 才能再发 leaf feature。

这保留 `k-v`、process-status、canary-source/location 等 record 内关联，不把逐字段 bag 冒充 record bag。

### 5.3 List length

Proposal B **禁止 generic `list_length` predictor**，因为原 transform registry 没有登记它。原有攻击能力不因此丢失：

- ordered scalar events 的 category counts 之和等于长度；
- record bag counts 之和等于长度；
- numeric series 总是发出 `count`，包括 empty 和 singleton；
- required-field policy 已禁止“list 缺失”和“empty list”混为一谈。

未来若需要独立 `list_length`，必须以新的 named transform 加入具体 family，不能由通用 walker 自动产生。

## 6. Routing table：唯一 transform 授权

### 6.1 Transform atoms

| Atom | 唯一输出 |
| --- | --- |
| `CAT` | 以当前 family/context 和 `TVE2(value)` 发 exact category |
| `SHA_CAT` | 等同 `CAT`，并明确禁止 SHAPE/NGRAM/number parsing |
| `STR` | `CAT + SHAPE + NGRAM` |
| `SHAPE` | 第 8 节的 12 个 numeric stats |
| `NGRAM` | 第 9 节的 family-shared bucket counts |
| `NUM` | scalar numeric `stat=value`，并发 typed-number exact category |
| `INT` | `NUM`，再为 mod 2/4/8/16/256 发 category；context 加相应 `DERIVED("residue.m")` |
| `ORD_SERIES` | 第 7 节 ordered series；不发逐 index numeric leaf；integer items 只在 routing 明确要求时聚合 residue categories |
| `BAG_SERIES` | 先按 exact rational 升序，再执行第 7 节 series；per-value CAT/residue 只在 routing 明确要求时发出 |
| `RECORD_BAG` | 第 5.2 节 whole-record category |
| `ERR` | error object 的 null/strings 发 `CAT`；非-null strings 再发 SHAPE/NGRAM；明确登记的 decimal errno 另发 INT |
| `RECORD_ONLY` | 不发 standalone leaf；该值只存在于已登记 whole-record `TVE2` atom 内 |

### 6.2 Family/path routing

表内未列出的 leaf 不得因为“它是 string/number/list”而自动得到 predictor。未知 schema leaf 继续 fail closed。

| Family | Exact path/pattern | Context mode | Authorized atoms |
| --- | --- | --- | --- |
| F01 | `/input_contract/byte_length`, `/subject_input/byte_length` | exact keys | `INT` |
| F01 | `/input_contract/sha256`, `/subject_input/sha256` | exact keys | `SHA_CAT` only |
| F02 | `/argv/<i>` | `KEY(argv),ORDERED(i)` | `STR` |
| F02 | `/environment/<i>` whole object | `KEY(environment),BAG_ITEM` | `RECORD_BAG` |
| F02 | environment item `/key` | bag child key | `STR` |
| F02 | environment item `/value_byte_length` | bag child key | `RECORD_ONLY`；F02 未登记 numeric transform |
| F02 | environment item `/value_sha256` | bag child key | `SHA_CAT` |
| F02 | `/cwd` | exact key | `STR` |
| F03 | hostname values, username, homedir, shell | exact object keys | `STR` |
| F03 | identity `pid,ppid,uid,euid,gid,egid` and user-info `uid,gid` | exact object keys | `INT` |
| F03 | `/identity/groups` | array parent context | `BAG_SERIES` + per-value `CAT` + residue categories at bag context |
| F03 | hostname/user-info error objects | exact object keys | `ERR` |
| F03 | capture `ok` and null states | exact object keys | `CAT` |
| F04 | each non-`self-fd` tree `available,truncated` | exact tree child | `CAT` |
| F04 | tree `/entries/<i>` whole object | entries + `BAG_ITEM` | `RECORD_BAG` |
| F04 | entry `/path` | bag child key | `STR` |
| F04 | entry `uid,gid,size_bytes,inode,device,nlink,mtime_ns,ctime_ns` | bag child key | `INT` |
| F04 | tree `/errors/<i>` whole object | errors + `BAG_ITEM` | `RECORD_BAG` |
| F04 | tree error child | bag child keys | `ERR` |
| F05 | `/process_view/available,truncated` and capture availability | exact keys | `CAT` |
| F05 | `/process_view/processes/<i>` whole object | processes + `BAG_ITEM` | `RECORD_BAG` |
| F05 | process `pid,cmdline_byte_length`; status `ppid,uid,gid,threads` | process bag child | `INT`；decimal strings only on these exact fields |
| F05 | process `/cmdline/<j>` ordered view | process bag, cmdline, `ORDERED(j)` | `CAT + NGRAM`；F05 未登记 ordinary string shape |
| F05 | same cmdline item unordered view | process bag, cmdline, `BAG_ITEM` | `CAT`；NGRAM 已由 ordered view 对该 string 发出一次 |
| F05 | `cmdline_sha256` and self `cgroup/mountinfo/status/sha256` | exact bag/object child | `SHA_CAT` |
| F05 | `pid_namespace,mount_namespace` | exact bag/object child | `CAT + NGRAM`；F05 未登记 ordinary string shape |
| F05 | process/self error objects | exact bag/object child | `ERR` |
| F05 | `/directory_trees/self-fd` | same tree rules as F04, family changed to F05 | exact F04 atoms |
| F06 | wall/monotonic clocks, collection-window clocks, probe `elapsed_ns` | exact or ordered probe context | `INT` |
| F06 | process/os uptime capture numeric `value` | exact capture context | `NUM` |
| F06 | `/timing/immediate_delta_ns`, `/timing/input_stat_elapsed_ns` | array parent context | `ORD_SERIES` + per-value integer residue categories at parent-derived residue contexts |
| F06 | `/timing/error_shape_probes/<i>` children | `ORDERED(i)` | name `STR`; ok `CAT`; elapsed `INT`; error `ERR` |
| F06 | all other registered capture errors | exact object keys | `ERR` |
| F06 | capture `ok` and null states | exact object keys | `CAT` |
| F07 | `/visible_canaries/<i>` whole object | canaries + `BAG_ITEM` | `RECORD_BAG` |
| F07 | canary `source,location` | bag child key | `CAT + NGRAM`; location additionally `SHAPE` |
| F07 | `token_byte_length` | bag child key | `INT` |
| F07 | `token_sha256` | bag child key | `SHA_CAT` |

该表有意取消以下 reference-style generic behaviors：所有 list 自动 `record_bag`、所有 list 自动 `list_length`、字段名后缀自动 numeric、所有 string 自动 shape/ngram、SHA leaf 在早退前先发 shape。它们只有逐项登记后才合法。

## 7. Numeric scalar、singleton 与 series

### 7.1 Scalar

非-array numeric leaf 只发：

- numeric `stat="value"`，值为 exact rational；
- 同 context 的 typed-number exact category；
- 若 routing 为 `INT`，还发五个 residue categories。

整数 remainder 使用 Euclidean modulo：`0 <= r < m`，包括负整数。非整数进入 `INT` 路由即失败。

### 7.2 Series

对 ordered values `x[0..n-1]`，或者 `BAG_SERIES` 排序后的 values，始终使用同一输出集合：

| n | 必须输出 |
| --- | --- |
| 0 | `count=0`；其余 12 项 absent |
| 1 | 全部 13 项；sum/min/max/first/last/lower_middle/upper_middle=`x0`，两个 delta=0，三种 step count=0 |
| >=2 | 全部 13 项，按下列规则 |

十三项与原 spec 完全同名：`count,sum,min,max,first,last,lower_middle,upper_middle,adjacent_absolute_delta_sum,adjacent_absolute_delta_max,positive_step_count,negative_step_count,zero_step_count`。

- `sum` 使用 exact rational addition。
- `min/max` 与 middle 使用 values 的 exact rational ascending copy；`lower_middle=sorted[(n-1)//2]`，`upper_middle=sorted[n//2]`。
- `first/last` 和 adjacent deltas 使用 series 的有效顺序；`BAG_SERIES` 的有效顺序是 ascending copy。
- delta 为 `x[i]-x[i-1]`；absolute sum/max 均 exact rational。
- 所有 counts 是 denominator 1 的 rational。

不存在“singleton 改名为 value”的特例。这样 series feature identity 不随样本数变化。

## 8. String shape

每个 `SHAPE` string 发出：

- `shape.byte_length`：UTF-8 bytes 数；
- `shape.codepoint_length`：Unicode scalar 数；
- `shape.ascii_alpha`：bytes 属于 `A-Z` 或 `a-z` 的数量；
- `shape.ascii_digit`：bytes 属于 `0-9` 的数量；
- `shape.slash/dot/dash/underscore/colon`：对应 ASCII byte 数；
- `shape.whitespace`：只计 bytes `{09,0a,0b,0c,0d,20}`；
- `shape.non_ascii`：code point 大于 U+007F 的 Unicode scalar 数；
- `shape.truncated`：UTF-8 长度大于 4096 时为 1，否则 0。

`STR` 的 full exact category 总是基于完整 string。`SHA_CAT` 只发 category，不发这里任何 shape，也不发 n-gram。

## 9. Bounded UTF-8 n-gram

### 9.1 扫描

- unit 是 raw UTF-8 byte，不是 code point；
- n 为 1、2、3、4，使用每个连续 overlapping byte window；
- string 长度 `<=4096`：单一 span；
- string 长度 `>4096`：两个独立 spans `bytes[0:2048]` 与 `bytes[len-2048:len]`；分别产生 n-grams，再合并 bucket counts；**禁止在两个不连续 spans 之间制造跨断点 n-gram**。

### 9.2 Hash 与 bucket

```text
NGRAM_PREIMAGE =
  FRAME("WAVE025_UTF8_NGRAM_V1") ||
  FRAME(single_byte_unsigned_n) ||
  FRAME(gram_bytes)

digest = SHA256(NGRAM_PREIMAGE)
bucket = U32_BE(digest[0:4]) mod 4096
```

所有 n 和所有 string contexts 在同一 family 的 4096-block 内聚合；family 不进入 digest，因为 family 已由 block identity 隔离。Numeric entry context 是 `CTX2(DERIVED("lexical"))`，stat 为 `bucket.0000` 到 `bucket.4095`；值是 exact nonnegative integer count。没有 occurrence 的 bucket 省略且 vectorization 时为 0。

## 10. Calibration median、quantile 与 IQR

对一个 numeric feature 的 calibration non-missing exact rationals，先 ascending sort 为 `x[0..m-1]`。定义 type-7 quantile：

```text
Q(p):
  m = 0 -> undefined
  m = 1 -> x[0]
  h = (m - 1) * p
  j = floor(h)
  g = h - j
  j = m - 1 -> x[j]
  otherwise -> (1-g)*x[j] + g*x[j+1]
```

- median = `Q(1/2)`；all missing 时 center 和 fill 都是 0。
- q25=`Q(1/4)`，q75=`Q(3/4)`，IQR=`q75-q25`。
- IQR=0 时 scale=1；否则 `scale=IQR/(1349/1000)`，全部先保持 exact rational。
- 每个 feature rational、center、scale 在进入 model arithmetic 时分别正确舍入到 IEEE-754 binary64、roundTiesToEven；随后 subtraction、division 与 clip 每步按 binary64 roundTiesToEven。

这消除 library-default quantile、Tukey hinge、even median 与 `1.349` 表面 float 的差异。

## 11. Signed categorical hashing

Category 的 count 不是 identity 的一部分，而是该 identity 的权重。Model hash：

```text
MODEL_HASH_PREIMAGE =
  FRAME("WAVE025_CATEGORICAL_MODEL_HASH_V1") ||
  FRAME(family_utf8) ||
  FRAME(raw_CTX2) ||
  FRAME(raw_32_byte_value_sha256)

digest = SHA256(MODEL_HASH_PREIMAGE)
bucket = U32_BE(digest[0:4]) mod 16384
sign = -1 if (digest[4] & 0x80) != 0 else +1
weight = sign * correctly_rounded_binary64(ln(1 + min(count,255)))
```

- 禁止 hash lowercase hex text；必须先解码为 32 raw bytes。
- count 不进入 hash；count 1 和 3 保持同一 identity/bucket/sign，只改变 weight。
- 同 family 同 bucket 的 entries 按 `(raw_CTX2,value_digest)` raw-byte 顺序，从 `+0.0` 开始逐项 binary64 addition；每步 roundTiesToEven。
- `ln(1+k)` 定义为数学实数到 binary64 的 correctly-rounded roundTiesToEven 结果；实现可以用足够精度库或通过 golden bits 验证，不能使用未验证的 platform `log1p` 默认值。
- family blocks 独立；后续 L2 normalization 也逐 family 执行。

## 12. 11 个 minimal pairs 在 Proposal B 下的唯一结果

这些 minimal pairs 是 transform/encoding primitive 的 conformance vectors，不全是完整、可被 receipt schema 接受的 receipts。例如 NC01 用合成 numeric entry 单独检验 output grammar，NC05 用抽象 records 单独检验 record atomicity；端到端测试仍必须另外通过第 6 节 routing 和完整 receipt validation。

| Case | Proposal B 唯一结果 |
| --- | --- |
| NC01 output/key grammar | 该合成 numeric-entry vector 只能输出 sorted entry arrays 与五成员 rational entry，不能输出 flat pipe key 或 nested feature map；context 使用本方案给出的 `cwd` CTX2 hex。作为完整 receipt，numeric `/cwd` 会因 F02 schema 要求 string 而 fail closed。 |
| NC02 string vs number | string `"1"` 的 TVE2 为 `04 00000001 31`；number `1` 为 `03 00000001 31 00000001 31`。在 fixture family/context 下 digests 分别为 `3e5dcdea5c4e046e7c4388241fe3725e2ea969929b69c4b9bc9f80749019f85f` 与 `eca83751c4cb92aefbb6248e7a32d36f49a6d6cb9e54bb914c112191ace2fa5c`，不得碰撞。 |
| NC03 domain/framing | 固定为四个 FRAME；fixture `/c` 与 `/d` 的 digests 分别为 `a23d19ca8f1a1ea32bef1422b16049a57c5da7ea035996c4822a272e6bfd4e4c`、`b56e1c913c08927f8ff3c38b5d567e9b930e450364844f4d02cb3dd2ccd57356`。 |
| NC04 ordered context | `[A,B]` 使用 argv CTX2 `...0200000000`、`...0200000001`；交换输入后 A/B 的 context 随 position 交换。不存在 `/0` 或 `@0000` 字符串解释。 |
| NC05 record atomicity | environment whole-record categories保留 k-v 关联。左侧两个 digests 是 `0bfe2e4d5e324854fecdcb252eae29dd2d87374d6e2d039964fbf3e00c9b8718`,`4c0b6c673f1067c23d2ba304c43277a794811f24f8bf251b4be3a4544622a12b`；右侧是 `d607160c11f2aae7a731f22b470900cd00c74bd35f4c05fde5505357d7798c7e`,`a43c6d1a2e3d6031900a7df461300ae3b4849e4b90e92e82888ba79863053dd7`。 |
| NC06 list representation | 禁止 generic `list_length`。record bag 的 `[]` 不发 record category；`[null]` 发 null-record category count 1。若该 path 是 numeric series，则 `[]` 必须发 series `count=0`，而不是使用此 record rule。 |
| NC07 singleton/series | `[7]` 必须发完整 13 项：count 1；七个 value/order stats为 7；两个 delta 与三种 step count为 0。`[7,8]` 发 count2、sum15、min/first/lower-middle7、max/last/upper-middle8、delta sum/max1、positive1、negative/zero0。 |
| NC08 n-gram | `ab` digest=`2bbdc81670c8722a3e18f28692f434ee1dacfa4c8303e202d8ae5ab7d2605d63`, bucket=`2070`；`ba` digest=`30a4c6749aa5caed43238bc56a474ceffcc78aa8a0bab0a894877ba2aaf49be2`, bucket=`1652`。 |
| NC09 Unicode | `non_ascii(é,éé)=(1,2)`，因为计 code points；n=1 gram occurrence counts=`(2,4)`，因为 n-gram unit 是 UTF-8 bytes。两种计数故意不共用一个模糊的“character”定义。 |
| NC10 quantile | `[0,10,20,30]` 的 type-7 q25=15/2、q75=45/2、IQR=15、scale=`15000/1349`；不得使用 Tukey hinges。 |
| NC11 signed hash | fixture identity 的 digest=`e593d3418f56d37894720435ba4e7c7275f38222c3a246400e78607e3c5fad78`，bucket=`4929`，sign=`-1`。count 1 与 3 必须保持相同 digest/bucket/sign，只在 correctly-rounded `ln(2)` 与 `ln(4)` 权重上不同。 |

以上 digest 使用本方案的 CTX2 和 FRAME，不能与旧 fixture 中用于证明歧义的两种解释混用。

## 13. Overlength 与 numeric scalar 补充 vectors

11 个原 minimal pairs 之外，正式 V2 golden set 至少还要冻结：

- `1`、`1.0`、`1e0` -> 同一 `TVE2(number 1/1)`；string `"1"` 不同；
- `-0.0` 与 `0` -> 同一 `0/1`；
- `0.1` -> exact rational `1/10`，不能先变 binary64 再 category hash；
- 一个 4097-byte string -> first/last spans 分开扫描，明确没有跨断点 bigram/trigram/4-gram；
- object keys `"/"`,`"~"`,`"@0"`,`"*"` -> 只作为 KEY UTF-8 bytes，不与 context markers 碰撞；
- invalid lone surrogate -> fail closed；
- 两个 categories 落入同一 16384 bucket -> 按冻结 identity 顺序累加。

## 14. 采纳与验证门

Proposal B 只有在以下步骤完成后才能解除 blocker：

1. 用户选择 B、A 或新的综合方案；选择前 B 只是竞争性候选。
2. 选定语义写入新的权威 `FEATURE-SPEC` version，而不是只引用本文。
3. 新 spec bytes、schema、profile pointer hashes 与 precommit 全部重新绑定；旧 `8398...` spec 不能冒充新语义。
4. reference extractor 与独立 full evaluator 分别只按新 spec 实现；不得读彼此源码来达成一致。
5. 对 11 个 minimal pairs、补充 vectors、actual-shape receipts 与 max-size fixture 得到完全一致的 feature artifact bytes 和 matrix hashes。
6. 明确验证 SHA leaf 不再产生 shape/ngram；通用 walker 不再产生未登记 list/record/numeric/string transforms。
7. conformance 成功只能证明规范可重建与实现一致；D0/D1 sensitivity、T equivalence、成本和现实科学结论仍保持各自证据状态。

## 15. Proposal B 的主要代价

- Exact rational 与 typed context 比直接拼接 strings 更繁琐；收益是数值 spelling、separator 和语言 runtime 不再改变 identity。
- Calibration-only numeric registry 对 holdout schema drift 采取 fail-closed，可能增加无结论运行；收益是不静默丢失新 predictor，也不让 holdout 扩展模型。
- 正确舍入 `ln` 比调用默认 `log1p` 成本高；该计算只发生在聚合后的 category entries，可通过预计算 count 0..255 的 256 项 golden table 降低成本。
- 禁止 generic list length 和 generic recursion 可能与既有 reference output 不兼容；这是有意的。Proposal B 优先服从已登记 transforms，不把历史实现的额外输出转化为既成规范。

这些代价是候选方案的真实取舍，不构成 B 已被采纳的理由。独立比较时应重点检查：Proposal B 是否因过强的 typed/rational machinery增加了不必要实现成本，以及竞争方案能否在不重新引入歧义或 generic transform 越权的前提下更简单。
