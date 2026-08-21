# Feature V2 Proposal B 独立规范红队

状态：`REDTEAM_COMPLETE__NOT_CANONICAL__BLOCKERS_FOUND`  
日期：2026-08-01  
审查对象：`FEATURE-V2-RESOLUTION-PROPOSAL-B.md`  
结论：`CANNOT_PROMOTE_DIRECTLY_TO_CANONICAL_SPEC`

## 0. 独立边界

本红队读取了 Proposal B、现行 `FEATURE-SPEC.json`、其 normative-completeness fixture、
non-authoritative reference extractor，以及已选择的 root `EXECUTABLE-ATTACK-PROFILE.json`。
它**没有读取 Proposal A、full evaluator engine 或 differential audit**。

评价问题不是“B 是否看起来严谨”，而是：两个互不读取源码的实现者只凭 B，能否为同一合法
receipt 产生完全相同的 predictor bytes、keys 与各 classifier 的 model inputs；同时，V1 已登记的
攻击能力是否仍然存在。

## 1. 总结判断

Proposal B 已经实质解决了 TVE2 类型坍缩、category framing、ordered/bag context marker、type-7
quantile、n-gram window/hash 和 category signed-hash 主体歧义；这些方向值得保留。但它目前仍有
**12 项 formal blocker**。其中最先会在普通合法 receipt 上触发的不是边缘数值问题，而是：

> bag item index 被正确抹除后，B 又把每个 bag child 的 `INT`/`SHAPE` 当成单值 numeric 发射；
> 两条 record 立即得到同一个 numeric identity。B 同时规定 duplicate identity 是实现错误，
> 因而自身 routing 与输出契约矛盾。

此外，B 没有保留 V1/C01 要求的 explicit missing category，部分合法 numeric strings 无解析授权，
还遗漏了正常 receipt 中的 self byte-length leaves。N-gram 聚合又抹除了 route/context，能让一种
原本登记为要检出的 fresh-code lexical leak 变成 false green。最后，B 只规范了部分 feature
artifact 与 signed category block，没有唯一规定 C01、C03/C04、family normalization 和 matrix
bytes，尚不能支持 zero-difference replay。

## 2. BLOCKER

### BRT-B01 — bag child numeric identity 必然冲突

**判定：`BLOCKER`**

B 把 record-bag item 的原始 index 从 context 中去掉，这是正确的；但又对 bag child 直接运行
`STR`、`SHAPE` 或 `INT`。例如两条 environment records：

```json
[
  {"key":"A","value_byte_length":1,"value_sha256":"..."},
  {"key":"BBBB","value_byte_length":4,"value_sha256":"..."}
]
```

两个 `/key` 都落到同一
`(F02, KEY(environment), BAG_ITEM, KEY(key), shape.byte_length)` identity，却分别要求数值 1 和 4。
一个实现可以 fail，另一个可以取最后值、求和或做 series；全都没有被 B 唯一选择。目录 entry
metadata、process/status numeric、canary token length/location shape 也同样触发。这不是合成边缘：
正常 receipt 一般都有多条 entries/processes/environment records。

**最小补丁：**区分 `SCALAR_CHILD` 与 `BAG_CHILD`。bag child 的 numeric/shape emissions 必须先按
`(family, bag-child-context, base-stat)` 收集为 multiset，再用明确的 `BAG_SERIES` 规则生成唯一
summary identities；categorical 仍按 digest 聚合 count。不要用原始 item index 修补，否则会把
bag 重新变成伪 ordered list，并使 holdout identity 漂移。

### BRT-B02 — `INT` 与 decimal-string admission 自相矛盾

**判定：`BLOCKER`**

B 规定只有 routing **明确标记** `DECIMAL_INTEGER_STRING` 的 string 才可按数字解析，但表中只有
F05 一行提到 decimal strings。实际合法结构中的 F04 `uid/gid/size_bytes/inode/device/nlink/
mtime_ns/ctime_ns`、F06 monotonic clocks、delta series 和 probe elapsed 多数是 decimal strings；
表只写 `INT`/`ORD_SERIES`，没有授予 string parsing。两个实现可合理地分别 reject 或 parse。

更严重的是 F05 status 的 `uid`/`gid` 不是一个 decimal integer，而是类似
`"65534\t65534\t65534\t65534"` 的四值序列；它不满足 B 的 grammar，却被同一行标成 `INT`。

**最小补丁：**机器 routing 的每个 path 必须同时冻结 input JSON type 与 parser atom：
`JSON_INT`、`JSON_RATIONAL`、`DECIMAL_INT_STRING`、`TAB_DECIMAL_INT_SERIES`。明确列出上述 F04/F06
paths。对 status uid/gid 选择并冻结 whole-string `CAT+NGRAM`，或显式 TSV series；不得称为单值
`INT`。

### BRT-B03 — 正常 F05 self byte-length leaves 无 route

**判定：`BLOCKER`**

B 为 `/process_view/self/{cgroup,mountinfo,status}/sha256` 登记了 `SHA_CAT`，但没有登记同一对象的
`byte_length`。这些是正常成功 receipt 的 included leaves，既不属于允许排除项，也没有被任何
record bag 包住。于是完整 leaf partition 必须失败。

**最小反例：**`/process_view/self/cgroup={"byte_length":5,"sha256":"..."}`。

**最小补丁：**为三个 `byte_length` exact paths 加入相应 integer atom；同时用完整 schema-path
枚举跑一次 leaf-partition fixture，要求每种 success/error union variant 的每个 scalar leaf恰有
一个 included/excluded owner。

### BRT-B04 — V1/C01 的 explicit missing category 被删除

**判定：`BLOCKER`**

V1 明确登记了 `EXPLICIT_CATEGORICAL_TOKEN`，C01 又登记了 categorical context total mapping 和
numeric exact value 的 missing category。B 只说明 numeric matrix 有 missing indicator；没有：

- category context registry；
- numeric identity 对应的 categorical missing token；
- missing 与 JSON null 的不同 bytes；
- C01 在 conditional success/error fields、empty bags、holdout missing 上怎样构造 total mapping。

因此一个实现可把 absence 当全零，另一个可合成 missing digest，产生不同 C01 rules 与 hashed
inputs。`null` 不能复用为 missing，因为它是 candidate 实际可观察的 JSON value。

**最小补丁：**增加非 JSON 的 `MISSING2` typed atom（例如独立 tag，不占用 TVE2 null），冻结
eligible scalar/multiset context registry；对每个 frozen eligible context/identity，若本 row 无值，
发唯一 missing category count 1。明确哪些 multi-valued bag contexts不参加 total-mapping rule，
以及 calibration-only dynamic contexts和 spec-declared static contexts如何冻结。

### BRT-B05 — N-gram 的 family-global 聚合抹掉 route/context

**判定：`BLOCKER_ATTACK_CAPABILITY_LOSS`**

B 把同一 family 的所有 strings 都聚到唯一 `CTX2(DERIVED("lexical"))`，hash preimage 也没有 route
或 context。最小对抗例：

```text
role R: cwd = "R-<fresh-a>", argv[0] = "S-<fresh-b>"
role S: cwd = "S-<fresh-c>", argv[0] = "R-<fresh-d>"
```

若 fresh suffix 使 full categories 不跨 split 复现，context-aware lexical feature 可学到 cwd prefix；
family-global gram multiset却把两条 route 混在一起。更强的完全交换 pair 在每 row 产生相同 n-gram
block。这正是 V1 false-green 风险中 string morphology/n-gram 本应缓解的 fresh unique identifiers，
不是无关的新攻击。

**最小补丁：**在 NGRAM preimage 中加入明确的 `lexical_route_context` frame，再仍然映射到每
family 共享的 4096 columns。对 ordered route说明是否包含 index；对 bag child 使用 bag-child
context而非 item index。共享 column block不等于抹掉 route identity。

### BRT-B06 — NGRAM-only routes 丢失 full length / truncation flag

**判定：`BLOCKER_V1_PROMISE_LOSS`**

B 只让 `SHAPE` 发 `shape.truncated`。但 F05 cmdline、namespace，F07 source 等路径只授权
`CAT+NGRAM`。对 4097-byte string，它们虽有 full category digest，却不发 B/V1 overlength rule
要求的 full byte length 和 truncation flag。不同 route 因是否恰好还有 SHAPE 而改变 NGRAM 的
完整契约。

**最小补丁：**每次 `NGRAM` 必须同时贡献 `lexical.full_byte_length` 与
`lexical.truncated`；在 bag/multi-occurrence context 下按 BRT-B01 的 multiset aggregation处理。
Golden set 要覆盖每一种 NGRAM-only route，而不只覆盖一个 `STR`。

### BRT-B07 — C01 与 derived numeric/ngram 的接口未冻结

**判定：`BLOCKER`**

B 把 n-gram buckets 放进 `features.numeric`，同时说 C01 对 numeric 使用 exact rational
equality/ordering；但 V1 将 C01描述为 raw exact categories/raw numeric/missingness scan。B 没有
定义 C01 是否枚举：n-gram count、shape、series summary、residue category、record category或只
枚举 raw scalar。一个实现可把 28672 个 n-gram buckets 当 C01候选，另一个可只交给 C02..C05。

同样，4.2 的“ordinary numeric registry”没有规范 n-gram entries 是否还会被重复收入 ordinary
numeric columns。

**最小补丁：**给每个 emission 一个冻结的 `channel`/`transform_kind`（可以是 artifact member，
也可以是由 context+stat 唯一可判的 normative table），并为 C01..C05逐一列出 eligible channels、
column ownership和不重复规则。若 transform 不进入 category digest，仍必须能由 artifact 唯一恢复
attack routing。

### BRT-B08 — C03/C04 presence block 与 C02/C05 family normalization 仍不唯一

**判定：`BLOCKER_MODEL_INPUT_UNDERDETERMINATION`**

第 11 节只唯一化了 signed categorical weight 的一个 block。它没有规定：

- C03/C04 的 categorical `presence` 是按同一 bucket hash 后做 OR，还是看 signed accumulated
  value `>0`；碰撞正负抵消时两者不同；
- family vector 的 numeric、ngram、category、missing columns精确拼接次序；
- L2 norm 的 sum-of-squares顺序、binary64 rounding、sqrt、zero-norm行为；
- “retain log1p pre-normalization family norm”的 exact column identity、log function 与 rounding；
- C03/C04 究竟接收 raw/median-filled numeric，还是第 10 节 subtraction/division 后的 numeric。

这些会直接改变 model input，不是训练器内部的次要浮点差。

**最小补丁：**为每个 classifier 发布 closed `MODEL_INPUT_V2` layout：column ID顺序、source
channel、missing-bit位置、category presence OR rule、signed accumulation、family norm算法和
zero-vector规则。所有 binary64 reduction固定 operand order与每步 rounding；必要的 sqrt/log bits
进入 golden vectors。

### BRT-B09 — routing 仍是 prose pattern，不能作为独立实现输入

**判定：`BLOCKER`**

“hostname values”“capture availability”“all other registered capture errors”“tree error child”
和“same tree rules as F04”不是 exact path registry。尤其 `ERR` 的输入究竟是 error parent object还是
每个 child不唯一；当前 `ERR` 文本也没有明确发 whole-error category，可能丢失 V1 的
`exact_error_category`。

**最小补丁：**把 routing 写成机器可校验的 closed rows：exact JSON-pointer pattern、union
variant、input type、context segments、cardinality、aggregation mode、authorized emissions和
leaf-audit owner。`ERR` 应明确先对 null或完整 non-null error object发 parent category，再逐字段
发登记的 CAT/SHAPE/NGRAM/errno numeric（如果这就是选择）；否则明确放弃 whole-error category
并把该 V1承诺作为有意变更审议。

### BRT-B10 — closed feature artifact 没有承载 required leaf audit

**判定：`BLOCKER_EVIDENCE_CONTRACT`**

B 禁止 source hash、audit/debug members进入 feature artifact，本身是良好的 predictor隔离；但它
没有定义另一个 canonical sidecar来保存 V1 required per-receipt leaf partition。因而无法证明：
合法 leaf均被分类、未知 leaf被拒绝、禁止 host/role fields没有进入 predictor。

**最小补丁：**保留 closed predictor artifact，同时新增独立、非 predictor、hash-bound 的
`FEATURE_LEAF_AUDIT_V2` sidecar，冻结 included/excluded path grammar、counts、path-set hashes、
reason codes、source receipt hash、predictor artifact hash和 canonical bytes。classifier不得读取
sidecar，但 evidence manifest必须绑定它。

### BRT-B11 — matrix/hash bytes 与 row order没有 canonical form

**判定：`BLOCKER_ZERO_DIFFERENCE_REPLAY`**

B 要求 conformance 比较 matrix hashes，却没有规定 matrix的 artifact schema、row identity/order、
sparse/dense representation、binary64 endian/bit encoding、`-0.0` normalization、missing-bit encoding
或 hash preimage。两个实现即使数值矩阵完全相同，也可得到不同 bytes/hash；更糟的是它们可用
不同 row order训练。

**最小补丁：**冻结 row order的权威来源（不把 slot ID变 predictor）、column registry artifact、
matrix bytes（例如 header + row/column counts + big-endian binary64 bits）、canonical +0规则和
SHA-256 preimage。C01 raw-rule material另给 closed serialization。

### BRT-B12 — finite decimal 到 model binary64 的失败边界未定义

**判定：`BLOCKER`**

`1e10000` 是有限且合法的 JSON decimal rational，却在 binary64转换时溢出为 infinity；极端
exponent还会在构造 `10^k` 时突破成本上限。B 只说正确舍入，没有说明 overflow、underflow、
subnormal或 numerator/denominator资源界限。一个实现可 reject，另一个可产生 infinity或被资源
耗尽。V1 的 `nonfinite=REJECT` 不能自动决定“输入 rational有限、转换结果非有限”的情况。

**最小补丁：**冻结 receipt/number-lexeme byte cap与 exponent/digit cap；规定 binary64 conversion
若结果为 infinity立即 `NOT_QUALIFIED_NUMERIC_RANGE`，underflow/subnormal与 signed-zero语义也逐项
规定。Golden vectors至少覆盖 max finite、首次 overflow、min subnormal、halfway tie和underflow。

## 3. SHOULD_FIX

### BRT-S01 — correctly-rounded `ln` 语义唯一，但交付不自包含

**判定：`SHOULD_FIX_BEFORE_TWO_ENGINE_CONFORMANCE`**

“数学实数正确舍入”本身不会允许两个真正合规实现输出不同值，所以不是纯 normative ambiguity；
但标准 `log1p` 并不普遍保证 correctly rounded。B提议用 0..255 golden table，却没有实际提供
256 个 binary64 bit patterns。让每个实现各自选择高精度库，会引入额外依赖和难复核成本。

**补丁：**把 `k=0..255` 的 `ln(1+k)` big-endian binary64 bits直接纳入版本化 golden artifact并
hash-bind。若 family norm仍需任意实数 log1p，则必须另行选择可复现算法/库版本，或改用能够精确
规范的单调变换。

### BRT-S02 — empty list 的“可区分”依赖未落盘的 validation事实

**判定：`SHOULD_FIX`**

对 `[null]`，record category count确实给出长度；对 `[]`，artifact没有任何该 list的 emission。
所以 `[]` 与“实现漏跑了该 route”得到相同 predictor bytes。B用 required-field policy说明 missing
input会被拒绝，但 BRT-B10 的 audit sidecar当前不存在。

**补丁：**至少落实 sidecar；更稳妥的是仅对 routing登记的 arrays发
`container.count`/`container.present`，而不是恢复 generic walker list-length。这样保留 B 的
最小发射原则，也让 empty状态成为显式 predictor。若决定不发 count，应把“validated input +
sidecar是 empty/presence 的唯一证据”写成正式取舍。

### BRT-S03 — category digest 不必机械加入 transform，但必须证明 route唯一

**判定：`ACCEPTABLE_ONLY_WITH_FIX`**

在当前设计里，family+typed context已区分 raw path、bag item和 residue derived context；`CAT` 与
`SHA_CAT` 又有相同 exact-category语义。因此把 transform重复塞进 `CATEGORY_PREIMAGE` 不一定增加
现实判别力，反而可能让同一事实因实现路径不同而裂成两个 token。

但 B 目前没有机器检查“同一 `(family,context,value)` 至多有一个 category语义”，也没有解决
BRT-B07 的 attack routing。

**补丁：**保留 category identity不含 transform是可接受选择；同时让机器 routing验证 emission
route互斥，并增加非 identity 的 `channel`或唯一派生规则。missing必须用独立 typed atom，不能靠
transform name伪装 JSON null。

### BRT-S04 — output JSON主体已接近唯一，但应由 schema + byte vectors封口

**判定：`SHOULD_FIX`**

B 已冻结 entry members、array sort、compact JSON、escaping与单 LF，这部分方向正确。仍应明确
object keys按 decoded raw UTF-8 bytes排序后再 escape，给 `count_u64`、rational gcd、hex lowercase、
family/stat enums和 CTX2 decoder写 closed schema。Proposal-specific schema名
`WAVE025_FEATURE_VECTOR_V2_B` 也不能原样冒充最终权威版本。

**补丁：**发布 JSON Schema 与至少一份 hand-audited exact byte fixture；对 predictor artifact
计算 hash时直接 hash这些 canonical bytes，不再二次 parse/reserialize。

## 4. ACCEPTABLE TRADEOFF

### BRT-A01 — 禁止 generic list length 可以保留

**判定：`ACCEPTABLE_TRADEOFF_AFTER_BRT-B10/S02`**

不让通用 walker为每个 array自动造 `list_length` 是合理的；它避免未登记 transform扩张。条件是
empty/present由 route-specific count或绑定 audit唯一证明，并且真实需要 count的 route显式登记。
这不是必须恢复 reference-style generic behavior的理由。

### BRT-A02 — TVE2 number 使用 exact rational 是一致的

**判定：`ACCEPTABLE_TRADEOFF_AFTER_BRT-B12`**

TVE2 对 JSON number使用约分后的 decimal rational、对 numeric-looking JSON string仍保留 string
type，是清楚且有价值的选择。record category可以因此区分 source JSON type，而 leaf numeric route
另行解析 decimal string。需要补的是 parser route和资源/overflow边界，不是放弃 exact rational。

## 5. 必须新增的最小 golden/conformance cases

在 B 已列 vectors之外，至少加入：

1. 两个 bag records在同一 child path产生不同 numeric/shape值，证明无 duplicate identity；
2. F04 decimal-string metadata、F06 decimal-string series、F05 tab-separated uid/gid；
3. `/process_view/self/*/byte_length` success与 error union；
4. JSON null、conditional missing、empty bag三者互异；
5. 同一 grams在 cwd/argv互换，证明 route-aware n-gram不坍缩；
6. 4097-byte NGRAM-only F05/F07 routes都产生 full length与 truncation；
7. n-gram bucket不重复进入 ordinary numeric block，且 C01 eligibility唯一；
8. signed category collision正负抵消时，C03/C04 presence仍按冻结 OR规则；
9. zero family norm、one nonzero category、mixed numeric/category/ngram family的 exact matrix bytes；
10. leaf-audit sidecar与 predictor artifact互相 hash-bind，但 sidecar mutation不改变 predictor；
11. decimal→binary64 max finite/overflow/subnormal/tie/underflow；
12. `ln(1+k)` 全表 hash与至少 0、1、2、254、255 的 hand-audited bits。

## 6. 能否直接转正典

**不能。** Proposal B 可以作为综合方案的重要输入，但至少要先修复 BRT-B01..B12，并让两个
独立实现从新的机器可读 routing、feature schema、leaf-audit sidecar、model-input layout和 golden
artifacts重建出完全相同的 feature bytes与 model-input hashes。修复前，即使 reference tests或单个
evaluator全绿，也不能解除 `FORMAL_BLOCKER_NORMATIVE_UNDERDETERMINATION`。

