# Full engine × reference extractor semantic differential audit

状态：`FORMAL BLOCKER / RAW F EVIDENCE PRESERVED / NO IMPLEMENTATION SILENTLY PROMOTED`

审计日期：2026-08-01  
受检对象：F 的 12 份 exact `collector-features.json`  
语义权威：`feature-spec/FEATURE-SPEC.json`（SHA-256
`8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a`）  
比较实现：`feature-spec/reference_extractor.py` 与 `full-evaluator-engine/engine.py` 中的
`RawReceiptFeatureProvider`

## 结论先行

两份实现对 raw leaf 边界完全一致，但没有实现同一个 feature mapping。差异不是显示格式：它会改变
特征维数、token identity、碰撞、numeric scaling、C01 候选集，以及 C02–C05 的实际输入矩阵。

因此：

1. reference extractor 不是权威答案；full engine 也不能凭更宽的 synthetic coverage 自动升为权威。
2. F 的 raw batch、slot hash、Merkle、post-cut extraction 与只读 adapter 结论不受影响；它们验证的是
   输入证据而不是 feature semantics。
3. 当前 FEATURE-SPEC 已经能裁决若干局部错误，但不足以逐字节决定完整 feature vector。不能从两份
   实现中任选一份，再把选择描述为冻结方案。
4. 在 exact mapping 被前置冻结并由 golden vectors 检验前，任何 F classifier output 只能是
   implementation-conditional engineering result，不是 formal qualification evidence。

这正是 differential implementation 应发现的错误，不应通过“让 engine 对齐 reference”来消失。

## 实测差异

方法：每份 receipt 在不加入 challenge、phase、block、role、slot ID 或 host metadata 的条件下，分别由
两份实现提取；比较 feature key population 与 leaf audit。两者在全部 12 槽的
`raw_leaf_count`、`included_leaf_count`、`excluded_leaf_count` 和 `included_paths_sha256` 完全一致。
所以分歧发生在“已纳入的叶怎样变成 predictor”，不是 input boundary。

| challenge | slot | reference numeric | engine numeric | reference categorical rows | engine categorical keys | raw leaves |
|---|---|---:|---:|---:|---:|---:|
| D0 | `s_037e...` | 6227 | 1966 | 1246 | 3418 | 528 |
| D0 | `s_7a90...` | 6226 | 1966 | 1255 | 3439 | 528 |
| D0 | `s_c89d...` | 6231 | 1966 | 1248 | 3437 | 528 |
| D0 | `s_ed96...` | 6229 | 1966 | 1249 | 3420 | 528 |
| D1 | `s_56d5...` | 6902 | 2001 | 1281 | 3828 | 547 |
| D1 | `s_5c22...` | 6905 | 2001 | 1276 | 3821 | 547 |
| D1 | `s_bb1a...` | 6906 | 2001 | 1276 | 3865 | 547 |
| D1 | `s_d86c...` | 6907 | 2001 | 1277 | 3817 | 547 |
| T | `s_335c...` | 6144 | 1966 | 1251 | 3379 | 528 |
| T | `s_5b2d...` | 6139 | 1966 | 1243 | 3338 | 528 |
| T | `s_9cbf...` | 6143 | 1966 | 1250 | 3373 | 528 |
| T | `s_fe76...` | 6140 | 1966 | 1246 | 3355 | 528 |

reference 的 categorical `count` 总和与 engine token count 总和同样不同。例如 `s_7a90...` 是
2240 对 15075。这进一步证明不是 list-vs-map 表示造成的表面计数差。

## FEATURE-SPEC 已经能够裁决的项目

以下判断只依赖冻结 spec 的明确语句，不依赖“reference 看起来更像标准答案”。

### 1. SHA-256 叶必须只有 exact category

Spec 的 `/string_transform/sha256_leaf_rule` 是
`EXACT_CATEGORY_ONLY_NO_NGRAMS`。reference 对 SHA 字符串仍产生 `shape.byte_length` 与
`shape.codepoint_length`，然后才停止；这是明确超出范围。engine 对以 `sha256` 结尾的叶只保留 exact
category，不产生 shape/ngram；这一点 engine 符合，reference 不符合。

### 2. exact string hash 必须吃 raw UTF-8，而不是 JSON quoted string

Spec 的 `/string_transform/full_value_category` 明确为
`SHA256(domain || 0x00 || utf8_bytes)`，并声明不做 Unicode normalization。两份实现都先把字符串变成
canonical JSON scalar，因此将双引号和 JSON escaping 一起送入 hash。对 string leaf 来说，两者都不
符合 `utf8_bytes`。对非 string scalar，canonical scalar 才是 spec 允许的另一分支。

此外，`/predictor_output/categorical_value_representation` 要求 value hash 带 family 和 context。
reference 的 digest preimage 带二者；engine 的 digest 只带 `family:EXACT`，context 仅出现在外层 token，
因此 engine 的 value digest 本身不满足这条文字。不过 spec 没有冻结 category domain literal 和 framing，
所以 reference 使用的 `WAVE025_CATEGORY_V1` 仍只是候选解析，不是可直接晋升的 exact bytes。

### 3. ordered string events 不能全部抹成同一个 context

F02 明确要求 `ordered_scalar_events`，F05 明确要求
`ordered_and_unordered_cmdline_events`。engine 把所有 array index 统一归一为 `[]`；对 argv/cmdline string
没有 numeric first/last 可补救，位置关系已经丢失。reference 至少为已声明 ordered 的数组保留
`@0000`、`@0001` 等位置，因此在“必须保留顺序差异”上更接近明确要求。exact context 字符串语法仍未
冻结，见后面的 blocker。

### 4. n-gram 不能被当作普通 category 再散列一次

Spec 要求“每个 feature family 一个跨 n=1..4 共享的 4096 bucket block”。reference 直接产生
`family|lexical|b0000..b4095` count；engine 先生成至多 4096 个 n-gram category token，随后又通过
16,384 categorical model hash。这样实际 predictor position 不再是冻结的 4096 block，而是二次碰撞
后的 category block。engine 的这层二次散列不满足明确的 block 结构。

这不等于 reference 的 n-gram 完全正确：bucket preimage 和 digest-to-index 仍未冻结。

### 5. truncated 必须有显式 flag，而不只是“发生时加 1”

Spec 的 overlength rule 要保留 `TRUNCATED_FLAG`。engine 对每个非-SHA string 都产生 context-local
0/1 token；reference 只在超长时增加 family-level numeric count，普通字符串没有 false 状态。后者不能
区分“已检查且未截断”与“没有产生该 feature”，不满足显式 flag 的最低含义。flag 的 exact key/type
仍需冻结。

### 6. transform 名称具有叶级作用域，generic walker 不能随意扩大

F04 写的是 `path_string_shape`，F07 写的是 `location_string_shape` 与
`token_sha256_exact_category`，不是“该 family 的所有 string 都做 shape”。两份 generic walker 都会把
额外 string 送入 shape；reference 还会给 token SHA 生成 length shape。至少这些明确点需要按 family
transform routing 修正，不能以“所有 raw leaves 都 included”为由把每个 transform 施加给每个 leaf。

### 7. record-bag/ordered 双表示在已点名的 family 不能被删掉

F02 同时列出 `ordered_scalar_events` 和 `record_bag`；F05 同时列出 ordered/unordered cmdline；F07
列出 `record_bag`。engine 的 record pass 只接收 dict item，因此 argv 的 scalar bag 和 cmdline 的
unordered scalar view缺失。reference 给所有 list item 做 bag，覆盖了这些明确要求，但它也把没有声明
record bag 的 F06 timing list 做 bag；这个 blanket 扩张本身没有 spec 依据。正确修复必须是按 family/path
路由，而不是选一边的全局规则。

## FEATURE-SPEC 目前无法裁决的项目

这些不是“再看一遍代码就能判断”的问题，而是冻结语义缺字节。对 formal run，它们是 blocker。

### A. n-gram bucket 的 exact formula

Spec 冻结了 UTF-8、n=1..4、4096 buckets、共享 block 和 domain 名，却没有冻结：

- preimage 是否包含 `n`，若包含用一个 byte、文本还是定长整数；
- digest 用全部 32 bytes 还是前 4 bytes；
- integer endianness 与 modulo 规则。

reference 使用 `domain || 0x00 || n_u8 || gram`、前 4 bytes big-endian 取模；engine 使用
`domain || 0x00 || gram`、完整 digest big-endian 取模。对 `a/ab/abc/abcd`，reference buckets 是
`866/3592/1841/982`，engine 是 `818/3095/2394/1316`。Spec 不能在这两组间作 exact 裁决。

### B. category digest 与 model hash 的 exact framing

Spec 给出 category 表示需要 family/context/value SHA，并给出 model hash domain 和 16,384 bucket count，
但没有冻结 category domain literal、长度编码或分隔规则，也没有冻结 model hash 的 preimage、取哪段
digest、sign bit。engine README 已把它当作局部解析声明，这种声明是诚实的，但尚未成为 F
precommit 的语义。

### C. context grammar

Spec 能要求 order 被保留，却没有定义：哪些数组是 ordered、bag-only 或二者兼有；index 用 exact
decimal、定宽 decimal 还是 wildcard；tree/process record 的嵌套 context 怎样规范化。`@0000`、`*`、
`[]` 都是实现发明。context 又进入 category identity，因此不是无关命名。

### D. singleton numeric 与 series 的边界

Spec 列出 13 个 `series_outputs`，但没说单个 scalar 是 `value`，还是一元素 series 的完整 13 输出；也没
定义 shape count 在重复 context 下是求和，还是形成 ordered series。reference 对 singleton 只产 `value`，
engine 对 singleton 产完整 13 项；reference 对重复 shape 产 series，engine 只求和。两者都能从现有文字
构造解释，都会改变数千个 numeric keys。

### E. `list_length` 与 record-bag 的 exact scope

reference 为每个 list 额外发出 `list_length`，Spec 没有这个 transform 名；“integer summary”是否包含
容器长度没有定义。record bag 的 canonical item、是否包括 scalar item、空 list 如何表示，也没有 exact
规则。已点名 bag 的路径必须有 bag，但 bytes 仍未闭合。

### F. `non_ascii` 是 byte count 还是 codepoint count

Spec 同时列出 byte length、codepoint length 和 `non_ascii`，但没有定义最后一个的单位。reference 对
UTF-8 bytes 计数，engine 对 Unicode codepoints 计数；字符串 `é` 分别得到 2 和 1。需要明确写成
`non_ascii_utf8_byte_count` 或 `non_ascii_codepoint_count`。

### G. predictor output schema 和 missing category

Spec 给了输出 schema 名，却没有一份 closed JSON Schema 或 key grammar。reference 用 categorical row
array；engine 用 token→count map。`missingness=EXPLICIT_CATEGORICAL_TOKEN` 也没有定义 token identity、
哪些 optional context 必须补 missing、以及它与模型阶段 numeric missing indicator 的关系。两份实现的
self-consistency tests 不能补写这个接口。

## 设计含义与处置

当前应把状态登记为：

`FEATURE_MAPPING_EXACT_SEMANTICS_UNDERDETERMINED`。

它只阻断 feature provider 及其下游模型的 formal interpretation，不回溯否定 F raw evidence 或 batch
adapter。下一步不应修改某个实现来追另一个，而应先形成一个最小但逐字节充分的 resolution packet：

1. closed `WAVE025_REFERENCE_FEATURE_VECTOR_V2` schema 与 feature-key grammar；
2. 每个允许 leaf/path pattern 到 transforms 的显式 routing table；
3. ordered/bag context grammar、list length、singleton/series、missingness 规则；
4. exact string/category/ngram/model-hash preimages，包含长度、separator、n、endianness、digest slice、sign；
5. 每个 shape 的单位，尤其 `non_ascii`；
6. 一组不依赖任何实现生成的微型 golden vectors，覆盖 ASCII/Unicode、空/单/多元素、重复 record、
   超长、SHA leaf、error/null/missing、ngram collisions；
7. 第三个独立实现只读规范和 golden vectors，不读另外两份实现，再做 differential check。

因为 F 已经返回，任何现在选择的解析都可能受 F 可见结果影响。它可以用于定位工程问题和产生候选
结果，但不应追认成 F 当时已经 precommitted 的唯一语义。要取得 formal evidence，应由未来 batch 在
anchor 前绑定新 spec/resolution/golden-vector bytes；F 保持原样并保留这一负结果。

## 证据边界

- 直接观察：12/12 raw leaf audit 相同；12/12 feature population 不同；上表是当前两份实现对 F exact
  receipts 的实际输出。
- 规范判断：来自 FEATURE-SPEC 已冻结字段，reference 只用于暴露差异，不用于决定答案。
- 未做：没有据此修改 engine/reference；没有运行或解释 F classifier；没有产生 qualification verdict；
  没有读取 runner source；没有写入 F 或其 `evaluation.json`。
