# Wave025 model-input layout study V2 最终独立复核

状态：`ACCEPT_SCOPED_RETROSPECTIVE_SHAPE / REJECT_MODEL_LAYOUT_DECISION / REJECT_FORMAL_LINEAGE_OR_DELETION_GATE`

本复核读取了 V2 实现、result、tests、README 和 `POST-FIX-AUDIT.md`，但没有继承实现者的
结论。复核独立重算 routing 分类、全部宽度/nnz/byte 公式、public plan/closed/disk 对应、
公开 challenge 分层、category singleton/OOV、四种 reference-frozen layout 和 E5；另对
receipt 替换、challenge 替换、重复谱系项、共同改写与 signed-hash gate 做了最小变异。

没有读取 `runner-private-state.json`、`reveal.json`、private registry、结果标签或私有角色
分配。需要准确限定：V2 为了按 public challenge 分层，读取了公开的
`D0-HOST-LEAK` / `D1-OCI-CANARY` / `T-OCI-ISOLATED` challenge assignment。因此它是
**private-role/outcome blind、public-treatment aware**，不是不读取任何处理标签的广义
label-blind。

C01 的真实 phase boundary 仍是 `EXTERNAL_UNRESOLVED_DEPENDENCY`；没有 classifier fit，
power 仍为 `UNKNOWN`；G 和正式 3200 均为 `NOT_RUN`。

## 最终判定

### 可以接受的有界结果

1. V2 已正确拆开 2,715 mixed routing keys 与 2,531 primitives-emittable representative
   templates；两者都没有被称为最终 predictor universe。
2. 47 个 wildcard row 已正确分成 11 ORDERED、35 BAG 和 1 CONTAINER；不再声称全部
   ordered 或数学无界。
3. category domain 不再由 transform 名称猜测。当前 586 个 observed category identity 中，
   28 个落在 grammar-proved closed 类、51 个 SHA grammar 类、507 个保持 UNKNOWN。
4. 只有六个 ngram family 可达，snapshot 与三档 layout 的 width/nnz/CSR/dense 算术均可
   重建。
5. 当前磁盘十二份 receipt 与当前 public plan/closed 的 slot、challenge 和 collector hash
   的**观察性关系**成立。
6. public-challenge-stratified split 确实每层 2 reference / 2 probe；204 个 probe-only
   category identity 全部是全十二份中的 singleton，因此
   `CURRENT_12_INSUFFICIENT_FOR_NOVELTY_OR_HASH_VALUE_DECISION` 是正确结论。
7. exact-only、exact+OTHER、category hash-only、exact-known+OOV-hash 的 dictionary phase
   已冻结在 reference；probe 不扩字典。四类布局在机械上真正不同。
8. E5 已正确记录 raw 3 nnz、robust-transformed 4 nnz；只保留逻辑宽度相同和 exact-rational
   affine 可逆的有界结论。
9. 当前 signed-hash decision 为 `UNKNOWN_DO_NOT_DELETE`，这是安全且与证据强度相称的当前
   决定。

### 仍不能接受的晋升

- 不能据此选择最终 MODEL-INPUT layout、hash width、OTHER 语义、normalization 或 learner。
- 不能把 singleton-heavy OOV 当成 transferable novelty，更不能当成功效。
- `verify_f_lineage` 还不是形式化 admission/provenance gate；它对 list multiplicity 和共同
  改写不闭合。
- 八布尔 signed-hash gate 还不是 proof-bearing qualification gate；它目前只是一个对人工
  布尔声明做 AND 的 fail-closed policy stub。

所以 V2 足以作为下一步实验设计的**结构与资源账本**，不够作为模型布局决定或 G admission
输入。

## 1. routing 数量复核

### 2,715 mixed 与 2,531 emittable

从 exact routing candidate 独立展开 finite alternatives，并对每个 `*` 只代入 index 0：

- routing rows：109；
- route/channel/stat matrix entries：641；
- mixed representative keys：2,715；
- numeric context/stat templates：2,312；
- category context/channel templates before value：213；
- direct-ngram final family templates：6；
- primitives-emittable representative templates：`2312 + 213 + 6 = 2531`。

差异来自 primitives 的真实聚合边界：MISSING category identity 不含 `expected_stat`，direct
ngram 最终按 `(family,bucket)` 聚合。V2 对这两个数字的命名、用途与否定边界正确。

### 47 wildcard 的细分

逐行检查 `{:*}` capture 是否真正进入 `ORDERED:{capture}`：

| 类别 | 行数 |
|---|---:|
| ORDERED context retained | 11 |
| BAG item capture dropped | 35 |
| CONTAINER item capture dropped | 1 |
| 合计 | 47 |

这修复了 V1 的核心误述。V2 也正确保留 schema bounds 与 CTX2 u32 bounds 是另外约束。

### category domain

静态 route/channel grammar 分类可重建为：

- `CLOSED_JSON_BOOL`：2；
- `CLOSED_JSON_NULL`：19；
- `CLOSED_RESERVED_MISSING2`：3；
- `CLOSED_ROUTING_VARIANTS`：9；
- `NONENUMERABLE_SHA256_GRAMMAR`：6；
- `UNKNOWN_NEEDS_SCHEMA_DOMAIN_PROOF`：31。

当前 receipt identity 层为 28 closed、51 SHA、507 UNKNOWN，共 586。这里的 “SHA
non-enumerable”只能理解为**无法作为实用静态词典枚举**；SHA256 值域在数学上是有限的。

最小闭域检查：JSON_BOOL、NULL、MISSING、routing branch 只在 grammar 明确时被关闭；
UTF8_STRING 和 CLOSED_RECORD 即使 transform 名包含 category 仍保持 UNKNOWN。这个方向是
保守的，没有复发 V1 的 transform-name 推断。它还没有做 per-route schema-domain proof，
因此不能把 507 UNKNOWN 自动交给 open/OOV 机制。

## 2. 六个 ngram family 与 snapshot 算术

routing 中 NGRAM_DIRECT 只出现在 F02--F07，固定 block 为 `6*4096=24,576`。

独立公式：

- snapshot columns：`1,604 numeric + 586 category + 24,576 ngram = 26,766`；
- snapshot nnz：62,251；
- CSR：`62,251*(8+4) + (12+1)*4 = 747,064 bytes`；
- dense：`12*26,766*8 = 2,569,536 bytes`；
- exact category manifest：39,264 bytes。

所有值与 V2 result 一致。snapshot 使用全十二份 receipt，只可接受为 retrospective
arithmetic；V2 已明确不把它当 frozen model allocation。

## 3. public-plan / closed / disk 谱系

### 当前字节的观察性通过

独立检查当前实际输入：

- plan list、closed list、disk directories、receipt files 均为 12；
- plan/closed slot id 均 12 个且唯一；
- 每个 closed slot 为 `COMPLETE`；
- plan 与 closed 的 challenge 逐 slot 相同；
- 12/12 `collector-features.json` SHA-256 与 closed manifest 相同；
- batch id 相同；closed status 为 `CLOSED`；unexpected slot entries 为空。

这足以接受
`OBSERVED_PUBLIC_LINEAGE_PASS__NOT_V1_1_ADMISSION` 对**当前冻结字节**的陈述。

### 最小攻击结果

| 变异 | V2 verifier |
|---|---|
| 改一份 shape 的 collector hash | REJECT：collector hash mismatch |
| 只改 public plan 的一个 challenge | REJECT：plan/closed challenge mismatch |
| 在 plan list 末尾追加一个完全重复 slot entry，slot_count 仍为 12 | **ACCEPT** |
| 在 closed list 末尾追加一个完全重复 slot entry | **ACCEPT** |
| plan 与 closed 都追加重复 entry | **ACCEPT** |
| plan 与 closed 同时改写相同 challenge | relational verifier 可接受；若破坏每层四个，后续 split 才拒绝 |

原因是 plan/closed 被先转为 dict，重复 id 在检查 list length/uniqueness 前被覆盖；同时两份
公开文件和 result hash 都位于同一可改写域，没有外部 expected preimage。V2 tests 只检查
当前正例，没有 duplicate/co-edit negative fixture。

所以当前观察关系可以 scoped accept，但“sets match exactly / complete public lineage gate”不能
用于正式资格化。修复方向至少包括：先验证两个原始 list 都恰好 12 且 id 唯一；验证 plan
declared count、closed declared count、list multiplicity 与 disk cardinality全相等；若要抵抗
共同改写，再绑定 precommit/anchor 或 worker 无权修改的外部 expected hashes。V1.1 admission
仍是独立缺口。

## 4. public challenge 分层与 novelty

当前 public plan 明示三个 treatment challenge，每个四个 slot。V2 的 domain-separated
slot-id ranking 独立重建后，每层确实选出 2 reference / 2 probe；选择函数不读取 receipt
content，但规则是在 F 之后写入，未 precommit。

当前分层结果：

- reference exact dictionary：382 category identities；
- probe category union：382；
- reference/probe 交集：178；
- probe-only：204；
- probe-only singleton：204/204；
- 全部 category singleton：408/586；
- probe-only family：F04=168，F02=12，F03=12，F05=12；
- numeric structural drift：0；category template drift：0。

分层修复了 V1 的公开机制 1/3 与 3/1 失衡，但没有创造独立性：每层只有两份 probe、规则未
precommit、数据来自同一 smoke，且所有 OOV 都是 singleton。它无法区分：

- 每次运行必然变化但无任务价值的 inode/hostname/digest/record；
- 真正可迁移、与 C01 目标相关的新类别；
- 临时环境噪声；
- 可被归一化或删除而无需 hash 的身份。

因此 novelty/hash verdict 的 `INSUFFICIENT` 可以接受；204、53.4%（204/382）或 singleton
数量本身都不能作为保留、删除或选择 signed hash 的效果量。

## 5. 四种 reference-frozen layout 与全部宽度/bytes

reference-only 冻结量：1,604 numeric、382 exact、106 OTHER templates、24,576 fixed ngram。
probe 不扩展这些字典。

### 4,096 buckets/family

| category layout | columns | nnz | CSR bytes | dense bytes |
|---|---:|---:|---:|---:|
| exact-only | 26,562 | 62,047 | 744,616 | 2,549,952 |
| exact+OTHER | 26,668 | 62,107 | 745,336 | 2,560,128 |
| hash-only presence | 54,852 | 62,234 | 746,860 | 5,265,792 |
| hash-only signed | 54,852 | 62,218 | 746,668 | 5,265,792 |
| hybrid-OOV presence | 55,234 | 62,250 | 747,052 | 5,302,464 |
| hybrid-OOV signed | 55,234 | 62,249 | 747,040 | 5,302,464 |

### 8,192 buckets/family

| category layout | columns | nnz | CSR bytes | dense bytes |
|---|---:|---:|---:|---:|
| exact-only | 26,562 | 62,047 | 744,616 | 2,549,952 |
| exact+OTHER | 26,668 | 62,107 | 745,336 | 2,560,128 |
| hash-only presence | 83,524 | 62,237 | 746,896 | 8,018,304 |
| hash-only signed | 83,524 | 62,223 | 746,728 | 8,018,304 |
| hybrid-OOV presence | 83,906 | 62,251 | 747,064 | 8,054,976 |
| hybrid-OOV signed | 83,906 | 62,251 | 747,064 | 8,054,976 |

### 16,384 buckets/family

| category layout | columns | nnz | CSR bytes | dense bytes |
|---|---:|---:|---:|---:|
| exact-only | 26,562 | 62,047 | 744,616 | 2,549,952 |
| exact+OTHER | 26,668 | 62,107 | 745,336 | 2,560,128 |
| hash-only presence | 140,868 | 62,238 | 746,908 | 13,523,328 |
| hash-only signed | 140,868 | 62,225 | 746,752 | 13,523,328 |
| hybrid-OOV presence | 141,250 | 62,251 | 747,064 | 13,560,000 |
| hybrid-OOV signed | 141,250 | 62,251 | 747,064 | 13,560,000 |

公式逐项成立：

- exact-only width = `1604 + 24576 + 382`；
- exact+OTHER 再加 106；
- hash-only 再加 `7*width`，不保留 exact dictionary；
- hybrid-OOV 在 hash-only width 上再加 382 exact known columns；
- CSR = `12*nnz + 52`；dense = `96*columns`。

机械语义也与命名一致：exact-only 丢/log OOV；OTHER 只为 reference-known structural
template 合并 OOV；hash-only hash 所有 category；hybrid 只 hash OOV，同时保留 known exact。

可接受的是**布局差异与资源算术**，不是排名。尤其 exact+OTHER 的 60 个新增 occupied cells、
hash collision 或更少 bytes 都没有说明 C01 需要保留哪些 pair。

## 6. E5 与 transform 边界

V2 的 type-7 quantile 可重建：calibration `[0,1,2,1000]`，center=`3/2`，Q1=`3/4`，
Q3=`503/2`，scale=`1003/4`。原值非零数 3；四个 transformed value 均非零，所以为 4。

因此以下 scoped claims 成立：

- logical width 可以不变；
- zero-compressed nnz 可能变化；
- frozen nonzero exact-rational affine transform 在纯数学层可逆。

它不证明 binary64、implicit zero、regularization、intercept、threshold 或 learner output
等价。V2 已保留这些限制，没有再用 E5 选择 robust scaling。

## 7. 八布尔 signed-hash deletion gate

八个条件的方向覆盖了上一轮指出的主要缺口。当前只有 `structural_drift_zero=true`，其余七项
false/unknown，所以 `UNKNOWN_DO_NOT_DELETE` 正确且 fail-closed。

但是 `signed_hash_deletion_gate(evidence)` 只检查调用者提供的八个值是否为 literal `True`。
最小攻击为构造八个全 true 的 dict；无需提供 split manifest、independent probe receipt、
C01 receipt、resource ceiling、route-wise domain closure、fixture result 或 lost-pair report，函数
立即返回 `DELETE_SIGNED_HASH`。现有 test 正是在验证这一行为，而不是验证八份证据。

因此：

- 当前“不删除”决定：`ACCEPT`；
- 八条件作为设计 checklist：`ACCEPT_SCOPED`；
- “executable evidence gate / 可授权未来删除”：`REJECT`。

要成为 proof-bearing gate，每个布尔项需要由绑定 exact bytes 的 verifier 产生，至少包含输入
artifact SHA/length、phase、population、route/claim closure 和失败明细；gate 还应拒绝人工
布尔覆盖、缺少 receipt、定义 hash 变化和 probe/dictionary 交叉污染。

## 8. 最终可用范围

V2 现在能够回答：

> 在当前 exact routing 与当前十二份公开 F receipt 的观察性快照下，四种成熟 sparse
> category layout 的列宽、占用和标准 CSR payload 如何不同；哪些表示差异会被 E1--E5 的
> 最小对暴露。

V2 仍不能回答：

> 哪种 layout 能解决 C01；公开 treatment 之外的新环境会出现什么；singleton 是否有任务
> 价值；signed hash 是否应删除；任何 classifier 的功效、阈值、迁移或净价值。

下一步若继续，不应再扩大同类 shape 统计。高信息增益动作是闭合 C01 phase boundary，冻结
真实 calibration/probe 规则和 required distinguishing pairs，然后让四种 layout 在相同任务、
相同 resource ceiling 和独立 probe 上竞争。

## 复核凭据

- `layout_study.py --check RESULTS.candidate.json`：`RESULT_MATCH`。
- V2 tests：12/12 pass；只证明当前实现与当前 result 自洽。
- 独立公式检查：三档所有 width、nnz、CSR、dense 均通过。
- receipt replacement：REJECT。
- plan-only challenge replacement：REJECT。
- duplicate plan/closed list entry：ACCEPT，确认 lineage multiplicity gap。
- all-true Boolean evidence：返回 `DELETE_SIGNED_HASH`，确认 gate 尚无 evidence binding。

复核输入 SHA-256：

- `layout_study.py`：`9915c77219ebedae7ad15bfdc3c8b456ae0a1d5a12ce3b174fefe00f642cecac`
- `RESULTS.candidate.json`：`5129149124c76562a780f96267b5f7f2ef332a379a189e48e13a5af35aa4018a`
- `README.md`：`933d5203233352feeada2472e50f198d8e66f80b4447d3bb99dfc65704b0f9a6`
- `tests/test_layout_study.py`：`8025c3af6457fbe919e220f397ef01a99c22ff7f55f177148efb05af00f8465c`
- `POST-FIX-AUDIT.md`：`77b8be87a7ae4fed35851d24845573d3ad2695235763fd9eb459d349391e4e72`

