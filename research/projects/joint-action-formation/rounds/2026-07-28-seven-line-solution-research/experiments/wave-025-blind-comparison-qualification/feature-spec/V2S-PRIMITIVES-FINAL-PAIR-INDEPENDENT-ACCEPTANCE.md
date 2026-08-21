# V2S primitives final-pair 独立验收

> 日期：2026-08-01
>
> 范围：只复核 post-fix 报告中的两个 outer-pair `UNKNOWN`，并对 B01–B06/B08
> 做窄回归。本轮不修改候选实现，不 import oracle 作为独立答案，不读取或
> 判定正在并发修复的 routing 中间态。
>
> 最终结论：`ACCEPT_FOR_ROUTING_REBIND`。

## 结论

post-fix 报告保留的两个 `UNKNOWN` 已经关闭：

1. `QUALIFIED_FEATURE_EXTRACTION` 的 outer pair 现在冻结 schema discriminator，并为
   predictor 和 audit 分别绑定 filename、byte length 和 SHA-256；六个字段中任意
   一个错配都 fail closed。
2. `NOT_QUALIFIED` 现在是唯一的 audit-only 状态：`predictor_binding=null`、
   predictor bytes absent、outer pair absent。任何 attempted predictor bytes、non-null binding 或
   outer pair 都被拒绝。

窄回归证明 B01–B06/B08 的关键常量没有因这次修订漂移。因此，primitives 候选
不再保留 outer-pair `UNKNOWN`，可从上轮 `ACCEPT_FOR_ROUTING_REBIND_ONLY` 明确收敛为
`ACCEPT_FOR_ROUTING_REBIND`。

这仍不是 formal adoption、model acceptance 或 smoke G acceptance。

## 新六文件冻结面

| 文件 | bytes | SHA-256 |
|---|---:|---|
| `V2S-PRIMITIVES.candidate.json` | 12178 | `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b` |
| `FEATURE-LEAF-AUDIT-V2S.candidate.schema.json` | 9293 | `0fa3cc639968df2279d2d558a4aadbc5eb9a0879eb64187637c102afec7272fe` |
| `FEATURE-VECTOR-V2S.candidate.schema.json` | 5096 | `8fe1a3185adfcdd9579400d80a84b236ebbf493b037f9f8d957ec12d56f8e2a3` |
| `GOLDEN-V2S-PRIMITIVES.candidate.json` | 59062 | `620628f3c895f3edf3f4a0122eb69ed1b1bcfa196dfefee8e9f585b191d82b96` |
| `v2s_primitives_oracle.py` | 99671 | `e66a5d81825a30917a299c221cab5f97f18f0da1a01de49a846f2d105d44a80e` |
| `tests/test_v2s_primitives_oracle.py` | 17903 | `ee7c4f2cbd4eee29ce3016b4bc10aeb44cb4ca669d017f67568abf29acf231e6` |

## Qualified outer pair：`ACCEPT`

### Positive exact pair

独立重建 predictor/audit fixture 得到：

- predictor filename：`feature-vector.v2s.json`；
- predictor length：111；
- predictor SHA-256：
  `035783cf506c226d0ce742035a0d70947ae2ef17d5374495fe24b0c69a96efbc`；
- audit filename：`feature-leaf-audit.v2s.json`；
- audit length：1798；
- audit SHA-256：
  `4ff1176e934c7dfc415c2193821ebe1fb1f2b4e4a6f70df8521b314f231adbee`；
- outer schema：`WAVE025_PREDICTOR_AUDIT_PAIR_V2S_CANDIDATE`。

独立构造的对象与新 golden 的 `expected.outer_pair` 逐字段相同。

### 六个逐字段负例

下列每个变异均独立得到 `NOT_QUALIFIED_AUDIT_CROSS_FIELD`：

| 侧 | 变异字段 | 结论 |
|---|---|---|
| predictor | `filename` | `ACCEPT_REJECTION` |
| predictor | `byte_length_u64` | `ACCEPT_REJECTION` |
| predictor | `sha256` | `ACCEPT_REJECTION` |
| audit | `filename` | `ACCEPT_REJECTION` |
| audit | `byte_length_u64` | `ACCEPT_REJECTION` |
| audit | `sha256` | `ACCEPT_REJECTION` |

缺失 pair 和错误 outer schema discriminator 同样由规则 fail closed。本轮的决定性字段不再依赖
外层未表达的假设。

## NOT_QUALIFIED audit-only：`ACCEPT`

独立重建的正例是：

- status：`NOT_QUALIFIED`；
- failure code：`NOT_QUALIFIED_UNKNOWN_PATH`；
- `predictor_binding=null`；
- predictor bytes：absent；
- outer pair：absent；
- audit filename：`feature-leaf-audit.v2s.json`；
- audit length：1666；
- audit SHA-256：
  `457fc03f19b0ebc3a49186a1561a1fb0ebd1758c81d910d4a96abf0b6636d229`。

该对象与新 golden 逐字段相同。下列三个负例均得到
`NOT_QUALIFIED_AUDIT_CROSS_FIELD`：

1. `NOT_QUALIFIED` 但传入 attempted predictor bytes；
2. `NOT_QUALIFIED` 但 audit 含 non-null `predictor_binding`；
3. `NOT_QUALIFIED` 但传入 outer predictor/audit pair。

这关闭了上轮关于“失败态是否还要绑定 attempted predictor”的二义性，也防止未合格
predictor bytes 被意外递交给 classifier。

## canonical/hash/length 与窄回归

### 四 JSON

不 import oracle 的独立 canonical serializer/parser 复核得到：

- 四个 JSON 均与 raw-UTF-8-key sort、规定 escapes、compact JSON 和 exactly-one-LF
  重建 bytes 完全相同；
- 无 duplicate decoded object key；
- 两个 schema 通过 Draft 2020-12 meta-schema；
- golden 对 primitives/oracle 的 length/SHA bindings 与实际文件相同。

### B01–B06/B08 无漂移

以下 8 个 feature-vector hard SHA 与上轮完全相同，且每个都通过独立
length/SHA/canonical 复算：

| case | SHA-256 |
|---|---|
| `TYPED_STRING_NUMBER_NULL_MISSING` | `d06f4dc1c745e3f5b2f5b3b8f3195f4749b83787ca1679bd8850c7c819571618` |
| `CATEGORICAL_TWO_OCCURRENCES_ONE_ROW` | `d38b7662873bf97421b4de7d5771d8f809ea5543bf682f3956d001f32513afe5` |
| `BAG_MULTISET_TWO_VALUES` | `5191f77fb1e12202d4bedb54f2ff24aa05845911d9d08fed82d2fa245c8a96c3` |
| `ORDERED_SERIES_SINGLETON` | `1e4ef0a2b1a79edb360c34cebe914ee49829f8402af620598fa91c1450671467` |
| `ROUTE_AWARE_CWD_ARGV_NGRAM` | `a1996d4dab0ba78ab876bbccfb83b12a581022db81acba1c8a55c9da520e0cc4` |
| `NGRAM_DISTINCT_ROUTE_DIGEST_BUCKET_COLLISION_MERGED` | `fd4d5e2338fb7f3a96a8255a9c2d41fdc7921ad03bd936ed7d7198f2a303a51b` |
| `UTF8_4097_BYTE_SPLIT_INSIDE_CODEPOINT` | `d5a6ffbeab76be00615ff8e1d073020a7592e5e66ea890028a0d9578d2344c29` |
| `CATEGORY_LENGTH_FRAMING_COLLISION_RESISTANCE` | `ad19541d2f5bc2e89240a4f934e30bb0b58831e18d7f6de03a51dc2ba4f554ac` |

同时窄回归了：

- leading-zero exponent atom `0300000001310000000131`；
- 769 mantissa digits 越界；
- derived 4865-digit rational 越界；
- MISSING2 双向错配；
- duplicate raw JSON key；
- overlong raw UTF-8。

全部与 post-fix 验收结果一致。

## 执行命令

候选包字节自检：

```sh
python3 research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/v2s_primitives_oracle.py --check
```

结果：`V2S primitive candidate artifacts: byte-exact`。

候选回归：

```sh
python3 -m pytest -q research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/tests/test_v2s_primitives_oracle.py
```

结果：`18 passed in 0.97s`。

冻结面复核：

```sh
shasum -a 256 research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/{V2S-PRIMITIVES.candidate.json,FEATURE-LEAF-AUDIT-V2S.candidate.schema.json,FEATURE-VECTOR-V2S.candidate.schema.json,GOLDEN-V2S-PRIMITIVES.candidate.json,v2s_primitives_oracle.py,tests/test_v2s_primitives_oracle.py}
```

另执行了一组不 import oracle 的 Python standard-library clean-room 验收，包括：

- 四 JSON canonical/duplicate/metaschema/binding；
- qualified pair positive + 六个逐字段负例；
- NOT_QUALIFIED audit-only positive + 三个负例；
- 8 个 feature-vector SHA 及 6 个边界常量无漂移。

该脚本输出 `FINAL_PAIR_CLEAN_ROOM_ACCEPT`。

## 边界与下一步

| 层级 | 结论 |
|---|---|
| primitives 候选，作为 routing 底层依赖 | `ACCEPT_FOR_ROUTING_REBIND` |
| 正在修订的 routing 中间态 | `OUT_OF_SCOPE` |
| formal canon/adoption | `NOT_ESTABLISHED` |
| 完整第二 feature provider | `NOT_ESTABLISHED` |
| model C01–C05 | `NOT_ACCEPTED_YET` |
| smoke G | `NOT_ACCEPTED_YET` |

下一步可以使用本报告冻结的 primitives SHA 继续 routing rebind，但不应跨过 routing
覆盖、clean-room provider agreement、model binding 和 smoke G 各自的验收门。
