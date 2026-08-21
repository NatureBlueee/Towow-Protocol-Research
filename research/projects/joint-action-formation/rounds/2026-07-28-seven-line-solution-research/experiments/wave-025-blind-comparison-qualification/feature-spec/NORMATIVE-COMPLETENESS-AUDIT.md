# Wave-025 predictor 规范完备性独立审计

审计日期：2026-08-01  
审计状态：`FORMAL_BLOCKER_NORMATIVE_UNDERDETERMINATION`  
作用域：从 candidate-visible 原始 receipt 到 predictor feature bytes/keys，以及 categorical model hashing 与 numeric preprocessing 的必要确定性语义。

## 结论

当前 `FEATURE-SPEC.json` **不足以让一个只读取权威规范的独立实现者唯一重建 predictor bytes、feature keys 与后续 model inputs**。这不是参考实现与另一实现之间普通的工程差异，而是正式执行阻断项。

原因不是规范完全没有约束。相反，它已经冻结了不少重要选择，例如 feature families、n-gram 的 `n=1..4`、bucket 数、若干 domain 名、无 Unicode normalization、integer residue moduli、nonfinite reject、feature order 与 classifier 集合。但在把这些名义规则变成唯一字节序列时，仍缺少一组承重的 byte-level 定义。最小反例表明：多个实现可以遵守现有文本，却为同一输入产生不同的 feature identity、bucket、sign、numeric value 或输出 key。

这会直接破坏已选 profile 的三个要求：

1. `FEATURE-SPEC.json` 的 bytes 才是 semantic authority，`reference_extractor.py` 只是 non-authoritative comparison implementation；
2. full evaluator 必须从 raw receipts independently extract，不能把 runner-supplied vectors 当作权威；
3. deterministic replay 对 feature matrices 与 evaluation output 的允许 byte differences 为 0。

因此，不能用“独立实现照抄参考实现”消除阻断；那会把未登记的参考代码偷偷提升为规范。应先补齐最小规范，再用 golden vectors 检查参考实现与独立实现。

本结论只阻断 formal use 和独立重建，不支持或反驳任何 D0、D1、T 科学假说，也不把 F smoke 描述成正式运行。

## 盲审边界与材料绑定

本审计刻意没有读取：

- `full-evaluator-engine/engine.py`；
- 任何针对该 engine 的 differential audit。

实际读取并绑定的材料为：

| 材料 | SHA-256 | 审计角色 |
| --- | --- | --- |
| `FEATURE-SPEC.json` | `8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a` | 唯一语义权威 |
| `reference_extractor.py` | `710602d7e259c0cdab151979ab2aeb439279faae270eda40357f24726beb5bf5` | 非权威实现，用于观察一种可能选择 |
| `tests/test_reference_extractor.py` | `dd5c3f093700b67748d7ff3fd1e0ab3a55129536e8f3df09fb23979b4ddeddf0` | 非权威实现测试 |
| `EXECUTABLE-ATTACK-PROFILE.json` | `64a4e366a67ec2c12b1194d6fb01fab5b633529035a16f20b22acbf83346e5a7` | 正式使用、独立提取和零差异要求 |
| F smoke 的 12 份 `collector-features.json` | 由测试逐份读取 | 仅判断歧义是否被当前样本形状触发 |

可执行的非规范最小反例保存在 `fixtures/NORMATIVE-COMPLETENESS-MINIMAL-PAIRS.json`；其测试只导入 reference extractor 来刻画参考选择，不把该选择升级为规范。

## 判定方法

一个规则只有在独立实现者能够从权威文本唯一确定下列结果时，才算具备 normative completeness：

- 读取哪些原始 leaf，以及同一 leaf 属于哪个 family/context；
- category/hash 的精确 preimage bytes；
- feature identity 与输出 key 的精确 UTF-8 bytes；
- 数值样本如何分组、汇总、插值和序列化；
- digest 如何映射到 bucket 与 sign；
- list、record、ordered index、bag multiplicity 如何保留或消除结构；
- 最终 predictor container 的 exact schema 与 canonical bytes。

若存在两个与现有文本相容、但输出不同的解释，本审计判为 `UNDEFINED`。只有当规范已经给出唯一规则，而参考实现产生了规则禁止的输出时，才判为 `CLEAR_SPEC_VIOLATION`。这样避免把“审计者偏好的实现”误写成规范。

## 最小正式 blocker 集

| Blocker | 未冻结的承重语义 | 为什么会改变正式结果 | F 是否触发 |
| --- | --- | --- | --- |
| B-NC-01 | `features.numeric` / `features.categorical` 的 exact container schema、flat/nested 形态、feature-key grammar、分隔与 escaping | 同一逻辑 feature 得到不同 key bytes、排序和 matrix columns | 是，所有 receipts |
| B-NC-02 | category domain、family/context/value framing；string 用 raw UTF-8 还是 canonical JSON scalar；JSON number/bool/null 的 exact scalar bytes | 改变 exact-category identity；raw string `"1"` 与 number `1` 甚至可能碰撞 | 是，string categories；F 还含 24 个 float scalars |
| B-NC-03 | raw path 到 context 的 grammar；哪些 arrays ordered、哪些 bag；index 是 `/0`、`/@0000` 还是别的表示 | 改变 category preimage、numeric keys 与是否保留顺序 | 是，argv、cmdline、timing、errors 及多类 arrays |
| B-NC-04 | `record_bag`/`tree_record_bag`/`process_record_bag` 的 atomic record bytes、multiplicity、nested recursion，以及是否/何时发出 `list_length` | 逐字段 bag 会丢掉 record 内关联；不同 list 规则产生不同 features | 是，264 个 arrays，其中 160 个多元素 arrays |
| B-NC-05 | numeric scalar、singleton series、multi-value series 的 grouping、key naming、empty/singleton outputs、middle 与 delta 定义 | 改变 feature set、数值与 missingness | 是，singleton 和多样本 series 均存在 |
| B-NC-06 | UTF-8 n-gram 的 unit、overlap、`n` encoding、hash preimage、digest-to-bucket slice/endian/modulo，以及 overlength 两窗口是否跨窗拼接 | 改变 4096-bucket counts；共享 block 不足以确定 bucket | ASCII n-gram 主体是；Unicode/overlength 分支不是 |
| B-NC-07 | median、q25/q75、IQR 的 exact interpolation/hinge 算法与偶数样本规则 | 改变 center、scale、clip 后数值，进而改变 C02/C05 | 是，校准和 numeric preprocessing 会使用 |
| B-NC-08 | signed categorical hashing 的 exact preimage、`value_sha256` 是 ASCII hex 还是 raw 32 bytes、count 是否入 hash、bucket digest slice/endian、sign bit/polarity、collision accumulation | 改变 C02/C05 的 bucket、sign、权重与 prediction | 是，所有 categorical preprocessing |

这八项是最小 blocker 集，不代表规范中其他文字都已达到出版级形式化；它们是当前最先必须消除、否则独立 evaluator 无法唯一重建的差异。

## 最小输入对与两种文本相容解释

完整预像和已计算 digest 位于 fixture。下表列出每个反例所区分的现实差异。

| Fixture | 最小输入对 | 解释 A | 解释 B | 输出差异 |
| --- | --- | --- | --- | --- |
| NC01 | `/cwd=7` 与 `/argv/@0000=7` | flat `family\|context\|stat` map | nested family/context/stat object | key/container bytes 不同 |
| NC02 | string `"1"` 与 number `1` | string raw UTF-8，其他 scalar compact JSON | 所有 scalar compact JSON | A 发生跨类型 hash collision；B 不碰撞 |
| NC03 | 同值 `"x"`，contexts `/c` 与 `/d` | `domain NUL family NUL context NUL scalar` | `domain NUL canonical([family,context,value])` | SHA-256 不同 |
| NC04 | `["A","B"]` 与 `["B","A"]` | ordered context `/@0000`, `/@0001` | JSON Pointer `/0`, `/1` | context 与所有下游 hashes 不同 |
| NC05 | `[{k:A,v:1},{k:B,v:2}]` 与交换 v 关联的 records | whole canonical record 作为 bag atom | k 和 v 分别做 field bags | A 区分两输入；B 丢失关联而不区分 |
| NC06 | `[]` 与 `[null]` | 每个 list 发出 numeric `list_length` | 只用 record/category multiplicity | feature set 与空 list 表示不同 |
| NC07 | `[7]` 与 `[7,8]` | singleton 折叠为未列名 `value`，多项才汇总 | singleton 也发出完整注册 series keys | keys、count、delta 与 missingness 不同 |
| NC08 | `ab` 与 `ba`，`n=2` | one-byte n、digest 前 4 bytes big-endian `%4096` | decimal n 加 NUL、whole digest `%4096` | buckets 分别为 `3592/2329` 与 `2223/3341` |
| NC09 | `é` 与 `éé` | `non_ascii` 计 UTF-8 bytes，n-gram 为 byte windows | 计 code points，n-gram 为 code-point windows | counts 为 `2/4` 与 `1/2` |
| NC10 | `[0,10,20,30]` 与 `[0,10,20,40]` | type-7 linear quantiles | Tukey hinges | 第一输入 IQR 为 15 与 20，scale 不同 |
| NC11 | 同 category identity，count 1 与 3 | hash 不含 count；前四字节 bucket、第五字节高位 sign | canonical record 含 count；whole digest bucket、末位 sign | bucket/sign 及 count collision 行为不同 |

NC02 还暴露一个规范内部张力：`predictor_output` 允许 “exact UTF8 or canonical scalar with family and context”，而 `string_transform.full_value_category` 写的是 `SHA256(domain || 0x00 || utf8_bytes)`。前者没有选择 string 的 scalar encoding，后者又没有冻结 domain 内容以及 family/context 的 framing。参考实现选择了第三个更具体的 preimage，并不能反向证明该 preimage 已被规范定义。

JSON numeric canonicalization 也没有由 `UTF8_RECURSIVE_KEY_SORT_COMPACT_ONE_LF` 唯一补齐：`1.0`/`1`、`-0.0`/`0`、exponent spelling 以及 LF 是否属于 scalar hash preimage，仍需要明确。F 的 24 个 float scalars 使这不是纯理论边缘。

## F smoke 对歧义的实际覆盖

对 12 份 F `collector-features.json` 的递归扫描得到：

- string scalars：5732；
- float scalars：24；
- arrays：264，其中多元素 arrays 160；
- 最大 string UTF-8 长度：305 bytes；
- non-ASCII strings：0；
- 超过 4096 bytes 的 strings：0。

因此，category/context/list/record/numeric/n-gram/quantile/signed-hash 的主体歧义确实落在当前 F shape 上。Unicode 的 `non_ascii`/ngram unit 与 overlength 两窗口边界没有被 F 触发；它们仍是 formal profile 的条件性 blocker，因为 profile 要求 max-size fixtures，而且没有 ASCII-only 或 `<=4096` admission gate。

作为非权威行为观察，在 D1 slot `s_5c227844cf83c9b6242bbb868d17bb34` 上重新运行 reference extractor 得到 6905 个 numeric keys 与 1276 个 categorical entries；其中确实包含 F01 SHA leaf 的 `shape.byte_length` key。这个观察说明差异会物化为大规模 predictor columns，但不把该列集合认定为正确答案。

## 明确定义、未定义与明确违反必须分开

### 已明确、不应误报为 blocker

- `EXACT_UTF8_NO_UNICODE_NORMALIZATION` 已明确禁止 Unicode normalization；不能再把 NFC/NFD 选择说成开放。
- n-gram sizes `1..4`、bucket count `4096`、shared block、domain label、最大扫描 4096 bytes、首尾各 2048 bytes 已命名。缺的是 preimage 和映射细节，不是这些常量。
- map key ordering、integer residue moduli、nonfinite reject、model bucket count、clip range 和若干 tie rules 已给出。

### 未定义，不能判 reference 对或错

- reference 对 ordered parents 使用 `@0000`、对 bag arrays 使用 `*`；规范没有登记这份 path registry 或 grammar。
- reference 对每个 list 发出 `list_length`，并对每个 item 发出 whole-record `record_bag` category；规范没有说明 transforms 列表是否 exhaustive，也没有定义这些通用发射规则。因此这是 non-normative addition/underdefinition，尚不能单靠现有文本判为明确违反。
- reference 对 singleton numeric group 只发 `value`，对多元素 group 发 series summaries；规范只列出 series outputs，未定义 singleton contract。
- reference 令 `non_ascii` 等于 UTF-8 中高位 bytes 的数量；规范列了名字，没有定义计数单位。

### 可明确判定的 reference/spec 不一致

`F01_PUBLIC_INPUT_BYTES.transforms` 只列 `exact_category`、`integer_summary`、`integer_residues`；同时 `sha256_leaf_rule` 是 `EXACT_CATEGORY_ONLY_NO_NGRAMS`。但 reference extractor 在 `sha_leaf` 早退之前仍发出 `shape.byte_length` 与 `shape.codepoint_length`。F 的实际 reference 输出也包含：

`F01_PUBLIC_INPUT_BYTES|/input_contract/sha256|shape.byte_length|value`

因此，在通常语义下这是明确的 `CLEAR_SPEC_VIOLATION_REFERENCE_SHA_LEAF_SHAPES`：`EXACT_CATEGORY_ONLY` 不能同时允许额外 shape predictors。若原意其实是“允许 shapes，只禁止 n-grams”，必须修改规范文字，不能靠参考实现猜测。

## 对 formal use 的影响

当前问题不能降级为“两个 evaluator 结果做 differential，选一个”。在 semantic authority 明确指向 spec bytes 的前提下：

- 若两个独立实现采用不同但文本相容的规则，零 byte-difference replay 无法成立；
- 若强制独立实现复制 reference，则 `extract_from_raw_receipts_independently` 退化为同一未声明实现的复制，不再检验规范完备性；
- 若等看到 F/formal outputs 后再选 framing、quantile 或 hash rule，会形成 post-observation extractor selection 风险；
- 不同规则甚至可能改变 leakage detector 的 sensitivity，而不只是文件格式。

所以新增的正式门应是：在 feature spec byte rules 修订并重新绑定 profile 之前，`PREFORMAL_REHEARSAL` 与 `FORMAL_USE` 均保持 blocked。已有其它 blocking 不会替代这个 blocker；即使其它外部 bindings 全部补齐，本项仍独立存在。

## 最小规范补丁：必须逐字节冻结的规则

不需要把 reference code 变成规范，只需加入以下最小、实现无关的 normative rules 与 golden vectors：

1. **Exact output schema**：定义 `features.numeric`、`features.categorical` 的 JSON types、record fields、ordering、duplicate/collision rule；若用 flat key，冻结 UTF-8 key grammar、分隔符与 escaping；若用 nested schema，冻结层级。
2. **Category preimage**：选择一个明确 domain；逐字段给出 type tag、length-prefix 或不可歧义 framing；明确 family/context bytes、string raw UTF-8 或 canonical JSON string、number/bool/null bytes，以及 LF 是否进入 preimage。
3. **Context/path registry**：给出 JSON Pointer escaping；冻结每个 family/source 下 ordered 与 bag paths；定义 ordered index width/overflow 和 bag wildcard 表示。
4. **Record/list semantics**：定义 whole-record canonical bytes、是否递归再发 leaves、multiplicity aggregation、empty/null handling、`list_length` 是否存在及准确 key。
5. **Numeric grouping**：定义 frozen numeric field names、decimal-string grammar、scalar/singleton/empty/multi grouping、完整输出 keys、sum/first/last/middle/delta 顺序与 integer/float serialization。
6. **String shape**：逐项定义 byte/codepoint/ASCII/whitespace/non-ASCII 的计数单位和有效 Unicode 处理；保持 no-normalization 规则；明确 SHA leaves 究竟只发 category，还是 category+shape。
7. **N-gram bytes**：定义 byte windows 或 code-point windows、overlap、每个 n 的 encoding、完整 hash preimage、首尾窗口是否独立、是否允许人工跨窗 n-gram；定义 digest slice、endian 与 modulo。
8. **Quantile/median**：指定公式或标准算法，例如 type-7；定义 even median、q25/q75、zero-IQR、all-missing 与 floating-point operation order。
9. **Signed hash**：冻结 preimage/domain/framing；`value_sha256` 用 raw digest 或 lowercase ASCII hex；count 是否入 hash；bucket digest slice/endian/modulo；sign bit 与 polarity；`log1p(min(count,255))` 的先后；bucket collision accumulation 与 float order。
10. **Golden conformance vectors**：至少覆盖本审计的 11 个 cases，再加 `1.0/-0.0/exponent`、escaped path key、4097-byte overlength、invalid Unicode admission、hash collision accumulation。每个 vector 保存 exact input bytes、expected feature JSON bytes、numeric/categorical matrix hashes、spec hash。

最小修补后，接受条件不是“reference tests green”，而是：两个未读取彼此源码的实现只读取新 spec 与 golden vectors，从同一 raw receipts 得到完全一致的 predictor bytes/keys；reference 的 SHA-leaf 额外 shapes 要么删除，要么由修订后的规范明确允许。

## 审计产物与边界

- 非规范反例：`fixtures/NORMATIVE-COMPLETENESS-MINIMAL-PAIRS.json`
- 反例与来源绑定测试：`tests/test_normative_completeness_fixture.py`
- 本文没有修改 feature spec、reference extractor、reference tests、selected profile 或 evaluator。
- 本文没有给出候选 spec 版本，也没有替用户决定具体选择 A 还是 B；它只证明现有权威文本无法唯一决定输出，并给出解除 blocker 所需的最小规则面。
