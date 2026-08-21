# Wave025 Feature V2 Proposal A — 独立规范红队

状态：`INDEPENDENT REDTEAM / PROPOSAL A NOT READY FOR CANON`

审查边界：本轮只读取 `FEATURE-V2-RESOLUTION-PROPOSAL-A.md`。未读取 Proposal B，也未读取或运行
现有 reference extractor、full engine；因此以下结论检查的是 Proposal A 能否独立决定规范，而不是它与
某个既有实现是否一致。

## 结论

**Proposal A 目前不能直接转为正典，也不能据此授权两个独立 provider 开始正式实现。**

它已经正确解决了若干旧歧义：typed context、raw UTF-8 exact value、path-specific routing、显式
TRUNCATED=false、n-gram direct block、singleton series 和 route-declared numeric mode 都是有价值的
方向。但仍有 13 个会让两个文本合规实现产生不同 predictor rows、bytes 或 model inputs 的
`BLOCKER`。最承重的四个是：

1. unordered wildcard 下的 string shape 会生成重复 numeric identity，当前输出 schema 无法表示；
2. canonical JSON、JSON number 类型与 record bytes 仍未被逐字节决定；
3. calibration missing universe 丢失被缺失的原 transform，且 numeric missing 没有封闭接口；
4. `log1p`、L2、量化与碰撞累加没有确定性数学内核，C01–C05 也没有唯一 model-matrix contract。

因此，A 可以作为 V2 的设计输入，但必须先修正下列 blocker、生成 machine-readable golden bytes，并让
两个独立小实现对未公开 holdback 得到逐字节一致结果，才可能转正典。

## 严重度定义

- `BLOCKER`：允许两个合理的文本合规实现产生不同 predictor identity/value/model input，或使合法输入
  无法由当前 closed interface 表示。
- `SHOULD_FIX`：不会必然改变 predictor，但会破坏自包含性、可实现性、审计唯一性或形成高概率误用。
- `ACCEPTABLE_TRADEOFF`：损失已被明确限定，且不会伪装成更强保证。

## BLOCKER

### A-RT-B01 — 没有冻结 self-contained receipt schema 与 route-to-context 映射

引用：§2.1 `unknown field fail closed`；§8 “`/**` 只在 closed schema 子树展开”；§12；§14.1。

Proposal A 只给出路径表和 schema 名 `WAVE025_LEAK_ONLY_FEATURES_V1`，没有包含或绑定该输入 schema 的
exact bytes，也没有定义 human path `/environment/*/key` 到 typed context
`/k:.../u/k:...` 的规范转换算法。因而实现者无法仅靠本提案判断：

- error object 允许哪些字段、哪些字段 optional；
- `success/error/null` union 的判别字段是什么；
- 哪些 array 是 ordered、哪些是 unordered；
- closed subtree 中出现一个新字段应拒绝、排除，还是被“error routing 的所有 scalar”接收。

最小反例：F06 error 为 `{"name":"E","detail":"x"}`。一个实现把 `detail` 当 unknown field 拒绝；
另一个依照“所有 nonnull string”生成 S features。两者都能从当前文字找到依据。

修补文字应至少冻结：`receipt.schema.json` exact SHA/length、每个 union 的 discriminator、每个 array 的
order class、每个 optional field、human-path 到 typed-context 的转换；并规定 route linter 必须证明
`每个允许 leaf = 恰好一个 INCLUDE 或 EXCLUDE route`。不能仅引用“现有 schema”。

### A-RT-B02 — canonical JSON 不是跨语言唯一规范

引用：§2.1；§4.1；§4.3；G07。

“UTF-8 codepoint lexicographic key order + `ensure_ascii=false` + 非整数使用 RFC 8785 number”不是一个
完整 canonicalizer：

- `ensure_ascii=false` 是 Python 选项，不规定 control characters、solidus、U+2028/U+2029 的 escaping；
- RFC 8785 的 object-key order 是 UTF-16 code units，而“codepoint lexicographic”会在补充平面字符上
  得到不同顺序；
- arbitrary-precision integer 的 canonical bytes 没有定义，RFC 8785 的 number domain 不能直接承接它；
- record bytes是否允许一个 mathematically integral binary64 token按 integer 打印也未说明。

最小反例：对象 keys 为 U+E000 与 U+10000。按 Unicode scalar 排序是 U+E000 在前；按 JCS UTF-16 code
units 排序是 U+10000 在前。两个 record digest 不同。另一个反例是 integer `9007199254740993`：按任意精度
decimal 与先转 binary64 后 JCS 会产生不同 bytes。

修补文字必须二选一：完整采用并绑定一个明确 profile 的 RFC 8785（同时放弃超出其 number domain 的输入），
或逐项定义 custom canonicalizer：key order、escape table、integer grammar、binary64 shortest-roundtrip
算法、negative zero、invalid scalar 和 LF。必须给出上述两个反例的 expected hex bytes。

### A-RT-B03 — JSON number 的 INTEGER/BINARY64 分类依赖未保存的词法形式

引用：§2.1；§3.1；§7.1；§10.1。

“native JSON integer/finite number”不是 JSON 数据模型中的封闭类型。`1`、`1.0`、`1e0` 在许多 parser 中
都会成为同一数值；canonicalization 又可能把它们都写成 `1`。一个实现会把三者视为 INTEGER，另一个会
根据原 token 把后两者视为 BINARY64。随后 output kind、series arithmetic、sorting、sum 和 model rounding
全部可能不同。

最小反例：ordered series `[9007199254740993,1.0]`。若第二项的 `.0` 类型信息已丢失，series 可被当作
纯 integer；若保留 token，它是 mixed binary64 series。sum 与 output kind 不同。

另有两个未决点：numeric string `"-0"` 是否规范成 integer `0`；负整数 residue 使用 Euclidean modulo
还是语言原生 remainder。`-3 mod 4` 可为 `1` 或 `-3`，后者还违反“nonnegative residue”。

修补文字应规定分类发生在何时，并绑定 raw token：例如“JSON token exact 匹配 integer grammar 才是
INTEGER，其他 number token parse 为 binary64；parser 必须保留该 tag”。同时明确 `-0 -> 0`、
`residue_m(x)=x-m*floor(x/m)`，以及每个 numeric stat 在 pure/mixed series 下的 output kind。

### A-RT-B04 — unordered repeated strings 无法装入唯一 numeric identity

引用：§3.1 numeric identity 必须唯一；§5.1 shape；§8 F02/F04/F05/F07；G05/G06。

typed context 用 `u` 有意抹去 unordered row identity。categorical rows 能以 digest+count 合并，但每个 S
string 都会生成多个 numeric `STRING_SHAPE` rows。两个不同 unordered records 的同一路径因此产生同一个
numeric id，违反“identity 必须唯一”；当前 schema也没有 numeric count 或 multiset value来承载它们。

最小反例：

```json
{"environment":[
  {"key":"A","value_byte_length":0,"value_sha256":"..."},
  {"key":"LONG","value_byte_length":0,"value_sha256":"..."}
]}
```

两个 key 的 `byte_length` 都映射到
`[F02,"/k:environment/u/k:key",STRING_SHAPE,byte_length]`，值分别为 1 和 4。一个实现拒绝 duplicate；一个
保留最后值；一个求和；一个生成 multiset。四者当前都未被文字排除。相同问题出现在 entries path、
unordered errors、processes 下同 index cmdline、visible canary location/source。

修补方案必须选定一种唯一表示，例如：unordered repeated route 中每个 shape stat进入
`UNORDERED_MULTISET` 六项汇总，并将 identity 显式包含 `shape.<stat>`；或把 shape value改为 categorical
count；不能使用不稳定的 source row order补 identity。随后增加 2 条/重复/不同长度/permutation golden。

### A-RT-B05 — categorical “identity” 的定义内部矛盾

引用：§2.1 “duplicate feature identity fail closed”；§3.1 “相同 identity+digest 合并 count”；§4.3；G06。

同一个 unordered context 合法地会有多个不同 categorical values。例如两个 environment keys应共享
`id=[family,context,EXACT]` 但有两个 digest。若 `id` 就是 feature identity，第二个值必须 fail closed；若
`(id,digest)` 才是 row identity，则 §2.1 的禁止条件含义不同。

最小反例：`environment.key = A,B`。实现一因 duplicate `id` 拒绝，实现二输出两个 digest rows；二者分别
符合 §2.1 与 §3.1。

修补文字应固定术语：`context identity=(family,context,transform)`；
`categorical row identity=(context identity,value_sha256)`；只禁止重复 row，重复 row合并 exact count。
numeric row identity另行定义并必须唯一。

### A-RT-B06 — Brec 的 “完整 list item” 绕过 path-specific routing

引用：§1.3；§4.3；§8 F02/F04/F05/F07。

`RECORD_BAG` 要 hash “完整 list item”，但没有定义这是 source record、仅 routed predictor projection，还是
去掉 branch/error envelope 后的 record。若取 source item，则一个没有单独授权的 nested field仍会通过
record digest成为 predictor，违反“每个 path 只运行 routing table授权 transform”。若取 projection，不同
实现又可能选择不同字段或 presence encoding。

最小反例：process record包含允许的 `pid/cmdline`，以及 optional `diagnostic_detail`。实现一在 leaf router
拒绝/排除 detail，但 Brec 仍 hash原 record；实现二只 hash routed projection。RECORD_BAG digest不同，且前者
发生隐性 source-scope 扩张。

修补文字应为每一条 Brec route列出 exact record projection schema、field presence/null语义与 canonical
bytes。更简单的方案是明确“Brec 只接受该 route 的 closed predictor projection；任一未分类 field在 record
hash前即 fail closed”。对应 schema/manifest必须绑定。

### A-RT-B07 — branch/error/presence 规则没有唯一 tagged-union 算法

引用：§4.3 BRANCH；§8 F03–F06；§9。

`SUCCESS|ERROR|NULL` marker 被定义了，但 Proposal A 没规定怎样从对象判定三态，也没规定 marker 的 exact
context。F05/F06 的“其他 nonnull scalar / 所有 nonnull scalar”还与 fail-closed route冲突。optional
`symlink_target presence 用 Br` 也没有说明 absent 是 NULL 还是另一个状态。

最小反例：capture 为 `{"ok":false,"error":null}`。它可能被解释为 ERROR（按 ok）、NULL（按 payload），
或 schema-invalid。另一个反例是 symlink_target absent 与显式 null：当前都可能得到 BRANCH=NULL，也可能前者
得到 MISSING。

修补文字必须逐 union 给出：discriminator path/value、三种合法 object shape、marker context、所选 branch
允许的 child routes、absent 与 explicit null的差异、非法组合。error fields不能再用开放式“所有 scalar”，
而应枚举 closed field set。

### A-RT-B08 — missing universe 丢失原 transform，并缺少 numeric missing 的 closed row

引用：§3.1；§9；G08/G15。

categorical universe 冻结的是 `[family,context,transform]`，但缺失时输出
`[family,context,MISSING]`，原 transform被丢掉。若同一 context在 universe 中同时有 EXACT、TRUNCATED 或
SCALAR_BAG，两个缺失都会尝试创建同一个 id。当前文字没有说明是只发一个 context-level missing、每个
transform各发一个（但冲突），还是把原 transform编码到 marker value。

最小反例：calibration row1的 S route在 context C产生 EXACT 与 TRUNCATED；row2缺 C。按“每个
[family,context,transform]”应有两个 missing，按 schema却都成为 `[family,C,MISSING]`。

numeric missing 更未出现在 feature-vector schema中：没有 indicator id/value encoding、排序、family block
位置，也没有明确它是在 provider artifact还是 model-matrix阶段注入。

修补文字应定义 route-universe item的完整 identity，并让 missing保留 `expected_transform`，例如扩展 id为
`[family,context,"MISSING",expected_transform]`；branch 已完全表达 absent child时，应明确是否从 universe移除。
numeric missing indicator也必须有 closed identity、binary value、排序和 model offset。冻结/注入只能读取
calibration membership，且应产出独立可哈希 manifest。

### A-RT-B09 — 浮点模型映射不是逐字节确定的

引用：§7.1–7.2；§10.1–10.4；G16/G17。

IEEE-754 round-to-nearest不足以让以下操作跨语言逐 bit一致：

- `log1p(count)` 与 `log1p(norm)` 通常依赖不同 libm；
- L2 的平方累加顺序、是否用 FMA、sqrt实现未冻结；
- R-7 的 `(1-g)*a+g*b` 可被 compiler融合为 FMA；
- `IQR/1.349` 的 constant parse与 operation sequence未冻结；
- categorical collision 的 algebraic sum没有规定 row顺序与 summation algorithm。

最小反例：一个 family含数值 coordinates 3 与 4。一个实现先平方/顺序 sum，另一个向量库并行 reduction；
更一般的非整数向量会产生不同 norm bits，继而整个 normalized block与 `log1p(norm)`不同。category count=255
的 `log1p` 也不能仅凭数学表达式保证相同 binary64 bits。

修补方案应冻结 deterministic numeric kernel（含版本/source SHA）、每一步 round与禁止 contraction，规定
coordinate iteration和 collision accumulation order，并为 log1p/sqrt/quantile/norm给出 input-bits →
output-bits fixtures。更强且更易审计的选择是把 model input量化为指定 fixed-point/rational encoding，再训练。

### A-RT-B10 — C01–C05 没有唯一 model-matrix contract

引用：§9；§10.2–10.4；§1 非目标。

即使 provider rows唯一，Proposal A也没有封闭下列 model-input决定：

- family的 exact顺序与 block offsets；
- calibration numeric identity universe、排序及 unseen/missing indicator位置；
- robust numeric、categorical 16384、ngram 4096、norm coordinate 的拼接顺序；
- C03/C04 的 “category bucket presence” 是“任一 row hash到此 bucket”还是“signed algebraic sum != 0”；
- C01 的 raw numeric/category/ngram candidate identity、value、tie order；
- C02/C05之外的 shared preprocessing差异以及异常 row如何进入 classifier状态。

最小反例：两个 categorical rows hash到同一 bucket，幅度分别 `+a` 与 `-a`。一种 C03 实现把 presence置1
（曾观察到 row），另一种因碰撞和为0置0。两者都符合“bucket presence”。

修补文字可以不重写 classifier算法，但必须冻结 companion `MODEL-INPUT-V2`：逐 classifier列出 input row
schema、coordinate manifest、offset/order、collision semantics、missing/unseen handling、matrix canonical bytes
和 hash。否则“only features are predictors”仍不能导出唯一 predictor matrix。

### A-RT-B11 — family/transform/stat token 没有封闭枚举，golden 又使用不同拼写

引用：§3.1；§5.1；§7.2；§8；G10/G11。

family 被写成“现有 F01 至 F07 exact IDs”，属于外部依赖；numeric stat只说“本文件定义的 stat”，没有一张
machine enum。更直接的冲突是 §7.2 使用 `adjacent_absolute_delta_sum`、
`adjacent_absolute_delta_max`、`positive_step_count`，G10 却写 `abs_delta_sum`、`abs_delta_max`、
`positive`。shape中的 `slash/dot/dash/...` 也可能被实现成不同 token。

最小反例：两个实现对同一 `[3,1,4]` 分别输出 stat `adjacent_absolute_delta_sum` 与 `abs_delta_sum`；数值都为5，
但 predictor identity bytes不同。

修补文字应在 closed JSON spec中逐字列出 family、transform、stat、branch marker、route code所有 enum，禁止
alias；golden只使用 exact wire token。

### A-RT-B12 — audit/source envelope 的 exact bytes 与 hash provenance 未定义

引用：§3；§14.4。

目标要求 independent provider产生逐字节相同 feature vector，而 output包含尚未定义的 audit fields：
`included_paths_sha256` 的 preimage/order/multiplicity、`excluded_fields` item schema/order、
`unclassified_paths`、`routing_counts` key/value语义均未知。`feature_spec_sha256`、`resolution_sha256` 也没有
指明 hash的是哪一个 exact file、是否含LF/manifest、怎样避免把一个包含自身 hash的 artifact变成循环定义；
`receipt_bytes_sha256` 是原传输 bytes还是重新 canonicalize后的 bytes也未说明。

最小反例：included paths `[P,P,Q]`。一个实现 hash sorted unique `[P,Q]`；另一个保留 multiplicity；
predictor rows相同但完整 artifact bytes不同，§14.4 differential会阻断。

修补方案有两种：完整定义 envelope每个字段的 schema、排序和 hash framing；或把 predictor projection与
audit envelope拆成两个 artifact，conformance分别比较，formal manifest再绑定二者 exact SHA/length。所有
source digest必须由非自引用 manifest给出明确 filename、byte length和raw SHA。

### A-RT-B13 — G01–G18 仍是说明性公式，不是可执行正典向量

引用：§11 Golden provenance；§14.2–14.5。

Proposal A 自己已正确承认 digest hex尚未求值；但这也意味着它尚不能排除 domain terminator、LP endian、
context encoding、JSON escaping、float bits或排序的一字节差异。G01–G18 还没有完整 receipt bytes、完整 expected
artifact bytes和 negative expected failure，因此不能充当两个实现之间的规范裁判。

最小反例：G01只说明 value bytes为 `0x41`，没有给完整 category preimage和 digest hex；family/context exact
token任一字符差异都不会被当前 case发现。

转正典前必须先生成 hand-authored machine fixture manifest：每例固定 raw input bytes、expected typed
contexts、每个 hash preimage hex、expected rows、完整 canonical output bytes/SHA；至少两个独立公式求值器一致，
并加入 unseen holdback。此项不是可以在正式 batch之后补做的文档工作。

## SHOULD_FIX

### A-RT-S01 — overlength UTF-8 window 可切在 codepoint 中间，需明确禁止重解码

引用：§5.2；§6；G12。

文字说按 UTF-8 bytes切 first/last 2048，原则上已指向 byte slicing；但 golden只有 ASCII。合法 string
`"€"*1366`（4098 bytes）的 first 2048会在一个三字节 codepoint中间结束。一个实现直接扫描 raw bytes，
另一个先按完整 codepoint修剪窗口，会产生不同 grams。

修补一句即可：“scan segments是原 UTF-8 byte stream的精确 byte slices；slice可为非独立有效 UTF-8，MUST
NOT decode/re-encode、repair或移到 codepoint boundary。”增加 non-ASCII split golden。

### A-RT-S02 — “可流式完成”与 length-prefix-before-value 不相容

引用：§4.2；§5.2；§1.5。

category preimage把 `LP64(value_bytes)` 放在完整 value之前。单向 streaming parser直到字符串结束才知道
byte length，不能在不缓存、spool或二次读取的情况下先写 length再增量 hash。proposal声称 incremental SHA
即可且无需保留完整长字符串，遗漏了这一点。

这不改变公式唯一性，但会导致实现以非规范 shortcut替代。应明确允许 seek/two-pass/temp spool，或改成
可单遍 framing并重新冻结 domain/goldens；不能一边要求 LP prefix一边声称未知长度单遍 hash。

### A-RT-S03 — typed context 的基础编码仍应逐字绑定

引用：§2.3。

应明确 `BASE64URL_NOPAD` 是 RFC 4648 URL-safe alphabet、禁止 padding、空 key编码，以及 u64 index上界。
还应给出 nested unordered→ordered context的完整 golden，例如
`processes/u/cmdline/i:000...001`，防止实现遗漏 `u` 或把 index按decimal编码。

### A-RT-S04 — normalizer 的 risk statement 不能替代 abnormal threshold

引用：§10.1；§15 no scale floor。

IQR 极小但正数时 scale会放大 measurement noise，这是明确 tradeoff；但“依靠 T/block audit暴露”没有规定
何时把 run标 abnormal。应由 companion evaluator contract给出 finite/overflow、max magnitude、condition
number或异常率的判定，而不是事后解释 false fail。

### A-RT-S05 — schema 名 `V2A` 不应在采纳后继续表达竞争分支身份

引用：§3；§13。

竞争阶段使用 V2A 合理；若采纳，应生成新的 immutable canonical resolution ID，不把“A获胜”写成长期
语义。旧 proposal SHA继续作为 provenance，正式 spec使用内容版本和兼容性边界。

## ACCEPTABLE_TRADEOFF

### A-RT-T01 — 4096 direct n-gram collision 与 n/context 身份丢失

引用：§6；§15。

这会损失某些 lexical distinguishability，但 bucket公式、scope和不能宣称的能力都已清楚限定；它是受检验
攻击族的设计选择，不是规范歧义。前提是后续不得把 non-detection升级为“无 lexical leak”。

### A-RT-T02 — 不做 Unicode normalization，shape用 codepoint而非高位 byte count

引用：§2.1；§5.1；§15。

相同可视字符串的不同 normalization会保持可区分，编码宽度不由单一 coordinate表示。这两点均已显式，
raw bytes和 shape units也能唯一实现，因此属于可接受的 bounded sensitivity选择。

### A-RT-T03 — holdout 新 numeric identity 令 classifier abnormal

引用：§9；§15。

这可能提高 false-fail，但它避免 silent ignore制造假绿，而且结果状态明确不等同于 chance。正式 contract
只需进一步规定 abnormal如何阻断 qualification以及其它 classifier是否仍可报告局部结果。

## 最小修正闭包

Proposal A 若要进入独立实现，至少需要同时形成以下 immutable artifacts，而不是继续补解释性 prose：

1. `RECEIPT-V2.schema.json`：closed fields、union、optional、ordered/unordered annotations；
2. `FEATURE-ROUTING-V2.json`：每个 schema leaf唯一 INCLUDE/EXCLUDE、context mapper、Brec projection；
3. `FEATURE-VECTOR-V2.schema.json`：closed enums、row identity、shape multiset、missing rows；
4. `MODEL-INPUT-V2.schema.json`：C01–C05 matrix layout、universe、offset、collision与 abnormal；
5. `DETERMINISTIC-MATH-V2.json` 或 fixed-point替代：operation order、libm/source hash、bit fixtures；
6. `GOLDEN-V2.json`：完整 input/preimage/output bytes，以及 duplicate、Unicode key order、mixed number、
   unordered shape、missing-transform、collision-cancellation、non-ASCII split等反例；
7. 非自引用 manifest：逐项绑定 filename、schema、byte length、SHA-256，再由新 batch precommit绑定 manifest。

只有这七件材料形成闭包，且两个不接触既有实现的 provider在公开 fixtures与未公开 holdback上逐字节一致，
Proposal A 才能从“设计候选”升级为“可冻结正典候选”。当前答案是：**不能直接转正典。**
