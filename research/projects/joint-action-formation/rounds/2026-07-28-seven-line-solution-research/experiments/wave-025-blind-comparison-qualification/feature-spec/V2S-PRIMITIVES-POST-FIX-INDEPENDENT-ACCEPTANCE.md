# V2S primitives post-fix 独立验收

> 日期：2026-08-01
>
> 验收者边界：本轮不修改候选六文件，不读取/借用旧 engine 或 reference 作为
> 答案，不 import `v2s_primitives_oracle.py` 作为独立常量的来源。
>
> 总判定：`ACCEPT_FOR_ROUTING_REBIND_ONLY`。

## 结论先行

原独立红队报告中能够造成 primitives/predictor bytes 分叉的决定性问题已经关闭。
特别是：

- categorical 已按完整 framed `channel_identity` 排序；
- 独立重算和新 golden 都得到
  `d06f4dc1c745e3f5b2f5b3b8f3195f4749b83787ca1679bd8850c7c819571618`；
- exact-rational 限制、MISSING2 双向关系、categorical occurrence 聚合、raw JSON
  边界、audit array/cross-field 语义已被补齐；
- 四个 JSON 候选产物均是独立复算的 canonical bytes，它们的 binding 与 schema
  基础检查通过。

因此，此版 primitives 可以成为下一步重写/编译 routing contract 的候选底层语义。
但它仍然不是 formal canon，当前 routing 也不能直接绑定它，更不能立即作为 model
或 smoke G 的输入。

## 六文件冻结面

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `V2S-PRIMITIVES.candidate.json` | 11733 | `6a3c5ae7884ca06facc8551ab04db977616e832e955286ab770f3c6b1bab1255` |
| `FEATURE-LEAF-AUDIT-V2S.candidate.schema.json` | 8872 | `9a70a9217a6dbbafed924589c283b2cc9b681b581dc6f0af2f0fb06604c85d40` |
| `FEATURE-VECTOR-V2S.candidate.schema.json` | 5096 | `8fe1a3185adfcdd9579400d80a84b236ebbf493b037f9f8d957ec12d56f8e2a3` |
| `GOLDEN-V2S-PRIMITIVES.candidate.json` | 56392 | `5980c14d5deddc130954936c284fe69d208fd3f98a2f818e77a050b611c1e158` |
| `v2s_primitives_oracle.py` | 92427 | `57f541b5e56f4afc701f46988da4036e3aa3e60fe104212a6617f883dc9a6560` |
| `tests/test_v2s_primitives_oracle.py` | 15870 | `6d8ae146669b836ccd8bd65a30b37663ea61024bbcf70f4ee54fbfbbee6b5c63` |

验收完成后重新计算了这些值；候选六文件未被本验收修改。

## 原 B01–B08 逐项复核

### B01 — framed categorical 排序：`ACCEPT`

以不 import oracle 的 FRAME32/CTX2/channel-identity 小实现重算：

- 裸 channel 文本顺序是 `EXACT_CATEGORY -> MISSING`；
- 完整 framed `channel_identity` 顺序是 `MISSING -> EXACT_CATEGORY`；
- 将 typed-category 向量按后者归一化后，SHA-256 是
  `d06f4dc1c745e3f5b2f5b3b8f3195f4749b83787ca1679bd8850c7c819571618`；
- 新 golden bytes 与独立归一化 bytes 完全相同。

原先 `061d...` 与 authoritative sort 冲突已消失。

### B02 — TVE2 exact-rational/limits：`ACCEPT`

决定性边界全部关闭：

1. `1e0000000` 在 1024-byte lexeme、768 mantissa-digit 和 `abs(exponent)<=4096` 下合法，
   独立结果是 `1/1`，TVE2 atom hex 是 `0300000001310000000131`。
2. `0.` + 767 个 `0` + `1` 现在按“所有 mantissa digits”计为 769，结果唯一地
   `NOT_QUALIFIED_NUMERIC_BOUNDS`。
3. 两个 4864-digit 合法整数的 sum 可生成 4865 digits，新规则在每个派生
   sum/delta/interpolation 后重新检查，因而 fail closed。
4. 负号不计 magnitude digit；JSON depth 改为 root=1 的 inclusive count，depth 64 接受、
   depth 65 拒绝。
5. `max_decoded_input_bytes` 现在明确是 post-transport/pre-JSON exact document bytes，
   包含 whitespace 和 escape syntax。

本验收不将这些结果外推为“所有数学运算已经 formal 证明”；它仅证明原反例
已经被唯一化。

### B03 — failure vocabulary：`ACCEPT`

`NOT_QUALIFIED_CONTEXT`、`NOT_QUALIFIED_CARDINALITY`、
`NOT_QUALIFIED_MISSING_ATOM_MISMATCH`、`NOT_QUALIFIED_AUDIT_ARRAY_ORDER`、
`NOT_QUALIFIED_AUDIT_CROSS_FIELD`、`NOT_QUALIFIED_INPUT_BYTES` 和
`NOT_QUALIFIED_ROUTING_PRECONDITION` 均已进入 primitives 和 audit schema 的相同 enum。

原 unknown CTX2 segment 和 empty BAG 现在分别有可序列化的唯一 code。

### B04 — MISSING channel/atom 双向关系：`ACCEPT`

机器语义现在明确是：

`channel == MISSING  iff  atom == MISSING2`。

两个反向最小反例均得到 `NOT_QUALIFIED_MISSING_ATOM_MISMATCH`：

- `MISSING + TVE2_NUMBER_1`；
- `EXACT_CATEGORY + MISSING2`。

这项不能仅从 predictor 中的 digest 倒推，因此候选包正确地要求它在 digest
前由被绑定的 routing/provider 执行。这是明确的上游前置，不是 primitives 内部未解。

### B05 — categorical occurrence 和 ngram collision 聚合：`ACCEPT`

- 两个相同 categorical occurrence 现在先经 checked-u64 聚合，输出唯一行
  `count_u64=2`；
- 零次发生不输出行，emitted count 是 `1..U64_MAX`；
- emitted vector 里再出现相同 identity 时是 duplicate failure；
- 独立 ngram 重算确认 `KEY(r1)` 与 `KEY(r16)` 的 digest 不同、bucket 同为
  2561，新 golden 在 hash 后只输出一行 `count_u64=2`。

### B06 — BAG identity/channel-stat/routing 前置：`ACCEPT_AS_DECLARED_DEPENDENCY`

primitives 现在明确要求：

- 每个 BAG call 非空；
- 对每个 `(family, bag_child_context, base_stat)` 恰好只有一个授权 input channel；
- 完整 family/channel/stat 与 categorical expected-channel matrix；
- 全部 context 是 canonical CTX2；
- categorical occurrence 以聚合前形式交付。

这消除了原来“input identity 包含 channel，但输出 identity 丢失 channel”的静默折叠。
该不变式仍需由上层 routing 提供证据，但它不再是 primitives 内部的隐含条件。

### B07 — audit 排序/去重/count/pair：`ACCEPT_CORE + UNKNOWN_OUTER_FILENAME`

独立重建的 qualified audit fixture 得到：

- audit length 1798，SHA-256
  `4ff1176e934c7dfc415c2193821ebe1fb1f2b4e4a6f70df8521b314f231adbee`；
- predictor length 111，SHA-256
  `035783cf506c226d0ce742035a0d70947ae2ef17d5374495fe24b0c69a96efbc`。

下列独立 mutation 现在都被拒绝：

- reverse `included`；
- 复制一个 `included` identity；
- 声明 routing count=1 但 included sum=2；
- 缺少 outer pair；
- outer predictor SHA 被篡改。

schema 自身仍会接受“顺序置换”和“count 错配”，但 primitives/schema 已明确宣告这些
是 semantic validator 的强制责任，并且候选 validator 能直接拒绝。这是合理的结构/语义分层。

尚有一个边界保持 `UNKNOWN`：authoritative dependency text 要求 outer manifest 同时绑定
filename + length + SHA，但六文件中没有 outer-manifest schema，候选 oracle fixture/check
只展示 length + SHA。这不会改变 predictor/audit 本身的 bytes，且 primitives 已明确把它
列为必需上层依赖；因此本验收不把它误判为 primitives 内部 `REJECT`。但在外层
schema 冻结并验证 filename 前，不能把 golden 的 pair 描述升格为“完整 outer pair
closure”。

另一个需在 outer contract 明示的细节是：`NOT_QUALIFIED` 状态下
`predictor_binding=null`，但 outer pair 是否仍必须绑定“未合格的尝试 predictor bytes”。当前六文件
没有给出该失败态 fixture；这也属于 outer evidence contract，不影响本轮对 qualified primitives
bytes 的接受。

### B08 — 独立常量/非单 oracle 自证：`ACCEPT_DECISIVE_HOLDBACKS`

本轮用另一个只依据规范文字的小型实现重算了：

- typed string/number value digest；
- null/MISSING row hash；
- framed categorical 整体 vector SHA；
- route-aware ngram digest/bucket 及 collision merge；
- exact-rational 三个资源边界；
- categorical occurrence count=2；
- 4097-byte UTF-8 split 行为；
- audit/predictor 硬常量及五个变异。

重算值与新 golden 一致。这已经足以关闭原报告的决定性反例，但不等于“第二个
完整 feature provider 已经实现”。后者仍是 promotion/model 的后续门槛。

## 原 S01–S04 逐项复核

| 项 | 结论 | 验收结果 |
|---|---|---|
| S01 结构 schema vs semantic validator | `ACCEPT` | primitives 现在明确 Draft 2020-12 不充分；audit 绑定 feature-vector schema 和 provider manifest，semantic validator 强制 CTX2、顺序、唯一性、count、rational 和 routing matrix。 |
| S02 raw duplicate key 边界 | `ACCEPT` | raw JSON 以 object-pairs 边界检查 decoded duplicate key，在 map 转换前拒绝。 |
| S03 invalid UTF-8 vs valid-full/invalid-span | `ACCEPT` | overlong raw UTF-8、lone continuation、lone surrogate 均拒绝；合法全文的 2048-byte ngram span 即使单独不可 decode 仍按 raw bytes 扫描，两者未混淆。 |
| S04 audit 内部一致性 | `ACCEPT_CORE` | array identity/order、routing sums、truncation spans、binding readback、qualified closure 均已进入语义规则；outer filename/failed-predictor 语义保持 B07 所述 `UNKNOWN`。 |

## 四 JSON 的 canonical/binding/schema 验证

独立 serializer 按 raw UTF-8 key 排序、规定 escape、compact JSON 和 exactly-one-LF 重建了
四个 JSON。结果：

- 四文件都与独立 canonical bytes 逐字节相同；
- 四文件都只有末尾一个 LF；
- raw parse 未发现 duplicate object key；
- golden 内 primitives/oracle length+SHA bindings 与实际文件一致；
- 两个 schema 通过 Draft 2020-12 meta-schema 检查；
- primitives failure-code enum 与 audit schema enum 相同；
- primitives exact-family enum 与 feature-vector 的 numeric/categorical/ngram 三处 enum 相同；
- golden 中 8 个 feature-vector artifact 的自身 length/SHA、canonical bytes 和 feature-vector
  结构 schema 全部通过。

## 与当前 routing 的兼容性

结论：`REJECT_DIRECT_BINDING__REBIND_OR_COMPILATION_REQUIRED`。

当前 `FEATURE-ROUTING-V2S.candidate.json` SHA-256 是
`371ad0d78741296c186457d325f40be132e67c7adcdad168f33f872d8aa3deb4`。它不能直接作为
新 primitives 要求的 routing contract，原因是：

1. primitives 冻结了七个完整 family ID：
   `F01_PUBLIC_INPUT_BYTES` ... `F07_VISIBLE_CANARY`；当前 routing 仍是短 ID
   `F01` ... `F07`。
2. 当前 routing 的 `channels` 是上游 route/transform vocabulary，包括 `NUMERIC_SCALAR`、
   `INTEGER_RESIDUE`、`EXACT_ERROR_CATEGORY`、`RECORD_EXACT_CATEGORY` 等；primitives
   要求的是输出 channel/stat matrix，包括 `RAW_NUMERIC`、`INTEGER_RESIDUE_CATEGORY`、
   `RECORD_BAG_CATEGORY`、`ORDERED_SUMMARY` 等。这两套词汇不应被简单判为
   语义冲突，但必须有唯一、冻结、可验证的 compilation mapping。
3. 当前 routing 不是 primitives validator 期待的直接 contract shape：它尚未产生
   `numeric_matrix`、`categorical_matrix`、`bag_output_owners` 以及六个 required boolean
   claims。
4. 当前 routing authority/known-static-proof-limits 仍写着“primitives independently BLOCKED”，
   也没有绑定本报告的新 primitives SHA。

这是一个真实的上层重绑/编译任务，不是对 primitives post-fix 的反证。只有当新
routing artifact 以完整 family IDs 编译出唯一 matrix/owners/claims，并绑定精确 primitives
bytes 后，这项才能从 `REJECT_DIRECT_BINDING` 转为 `ACCEPT_BOUND_ROUTING`。

## 产物边界判定

| 层级 | 本轮判定 | 理由 |
|---|---|---|
| V2S primitives 候选语义 | `ACCEPT_FOR_ROUTING_REBIND_ONLY` | 原 predictor-byte 决定性反例已关闭；可作为重建 routing 的底层候选。 |
| 当前 routing 直接绑定 | `REJECT` | family IDs、contract shape、matrix/owners/claims 和 SHA 均未重绑。 |
| outer predictor/audit evidence | `UNKNOWN` | length/SHA 核心已验证，filename 与 failed-predictor 语义尚等外层 schema。 |
| formal canon/adoption | `UNKNOWN_NOT_AUTHORIZED` | candidate 自身明确为 NOT_ADOPTED，还需 root decision、完整 clean-room provider 和 holdback agreement。 |
| model C01–C05 输入 | `REJECT_UNTIL_BOUND` | model 必须同时绑定 primitives、routing、schema、predictor 和 audit；目前 routing/outer 未闭环。 |
| smoke G | `REJECT_UNTIL_REBUILT` | 不能用未重绑 routing 或单 provider 结果宣称 V2S/model/G 闭环。 |

## 执行命令与结果

候选包自身字节检查：

```sh
python3 research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/v2s_primitives_oracle.py --check
```

结果：`V2S primitive candidate artifacts: byte-exact`。

候选回归：

```sh
python3 -m pytest -q research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/tests/test_v2s_primitives_oracle.py
```

结果：`17 passed in 0.73s`。

冻结面 SHA：

```sh
shasum -a 256 research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/{V2S-PRIMITIVES.candidate.json,FEATURE-LEAF-AUDIT-V2S.candidate.schema.json,FEATURE-VECTOR-V2S.candidate.schema.json,GOLDEN-V2S-PRIMITIVES.candidate.json,v2s_primitives_oracle.py,tests/test_v2s_primitives_oracle.py}
```

另执行了两组不 import oracle 的 Python standard-library clean-room 重算：

1. 递归 canonical JSON + duplicate-key parser + Draft 2020-12 meta/schema 校验；
2. 手写 FRAME32/CTX2/channel/category/ngram/exact-rational/audit 决定性反例。

第二组重算共输出 50 个 `ACCEPT` 检查行，8 个 feature-vector golden 通过独立
length/SHA/canonical/schema 验证。关键常量和 mutation 已在上文逐项记录，不以 oracle
回传作为答案。

## 下一个可接受动作

现在可以启动 routing rebind/compiler：将当前 route rows 编译为完整 family IDs、唯一
numeric/categorical matrices、BAG owners 和可验证 claims，并运行独立路由覆盖审计。
在这个 rebind 完成之前，不应开始 model 重放或 smoke G。
