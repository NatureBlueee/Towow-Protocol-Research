# Wave025 V2S routing post-fix 独立验收

状态：`POST-FIX REJECTED / CURRENT PATH-PSEUDO TABLE SUPPORTED / EXECUTABLE ROUTING STILL BLOCKED`

日期：2026-08-01

本验收由原 `ROUTING-V2S-INDEPENDENT-REDTEAM.md` 红队执行。没有修改 routing 实现，没有读取
旧 feature engine/reference 作为答案，也没有把 receipt semantic admission、C01--C05、model、G、
功效或 clean-room provider 尚未完成算作 routing 失败。

## 1. 冻结的验收对象

| artifact | bytes | SHA-256 |
|---|---:|---|
| `FEATURE-ROUTING-V2S.candidate.json` | 102226 | `3aa9e17fd8d2d73bdc3e1434de48eec3209a1c2da2cb354023eb3fdb89694246` |
| `FEATURE-ROUTING-V2S.candidate.schema.json` | 12385 | `d255b9056598b0788cf4a1c71777e87774dab4e69f1415b0bca1d645f9e3dced` |
| `routing_v2s_coverage.py` | 42545 | `035143bf9c261e630ab335608af5eccd4766b5d4b45f2abe8350e6dabb11354b` |
| `tests/test_routing_v2s_coverage.py` | 17087 | `b4e4b36f8c7f7fd5128cda97f94491337b4925b4a064b367e667d4b50d96701b` |
| `ROUTING-V2S-AUDIT.md` | 10672 | `554d5afcac6df717aa46c59aac856e47df78263b72fea97b821fed302caaa5e6` |
| `COLLECTOR-RECEIPT-V1.candidate.schema.json` | 27874 | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` |
| `V2S-PRIMITIVES.candidate.json` | 12178 | `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b` |

Routing candidate 是 compact、key-sorted UTF-8 JSON 加一个 LF，独立重编码逐 byte 相等。
Primitives candidate 也相等。Receipt schema 当前是 pretty JSON，不是相同 canonical form；routing
绑定的是它的**实际 27874 raw bytes**，所以这不是当前 structural routing 失败。它是统一机器发行包
要求所有 JSON canonical 时的 release blocker：一旦 canonicalize，必须更新 receipt hash/length 和
routing candidate，不能沿用当前绑定。

## 2. 基础复现与独立结果

原实现测试：

```text
tests/test_routing_v2s_coverage.py: 48 passed
feature-spec/tests: 117 passed
```

checker 报告：

```text
route_count=109
families=9,7,21,16,31,19,6
manifest_leaf_variants=454
manifest_unique_path_atom=371
pseudo specs=9 branch + 7 container + 5 record + 3 absence
channel_stat_matrix_entries=641
bag_numeric_identity_owners=1140
structural_ownership=PASS
admission_or_semantic_completeness=NOT_PROVEN
```

我另写了不 import `routing_v2s_coverage.py` 的 matcher、runtime selector、scalar/pseudo walker 和
CTX2 encoder。十二份 F receipt 的独立结果为：

| receipts | scalar | pseudo | scalar/pseudo bad | scalar-one collision |
|---:|---:|---:|---:|---:|
| 8 | 528 | 71 | 0 | 0 |
| 4 | 547 | 74 | 0 | 0 |

我又把 receipt-schema test 中十一份 source-reachable legal branch mutation送入修复后 runtime
router：hostname failure、etc-hostname failure、user-info failure、tree unavailable、process unavailable、
process read error、process-entry error、self-file error、empty status、uptime error 和 timing-probe
success 全部 `ZERO_UNCLASSIFIED`。

独立派生而非读取 checker 报告得到：

- exact seven full family identifiers在 routing、所有 row、routing→primitives binding和 primitives
  routing contract 四处一致；
- 641-entry matrix SHA 为
  `1b5a0a9da3e90f9f945dfb51a8d71f5485244d60e4b2f98356496a2b956e62af`；
- 以当前 rows按 `(family, concrete CTX2, base_stat)` 检查 BAG numeric input-channel
  前置，得到 1140 个 identity、零当前 collision。

## 3. 原 B01--B06 / V01--V03 逐项结论

### B01 named capture 与 concrete CTX2：`REJECT`

已接受的修复：

- 旧 `$FIELD/$TREE/$INDEX` 已清零；
- unnamed、duplicate、unbound capture和非规范 `01` index会被拒绝；
- 当前 R028 pid/ppid、五个 tree、self-file和 field alternation均得到不同 concrete CTX2；
- F receipts 当前没有 `SCALAR_ONE` runtime collision。

但有一个当前 artifact 本身的阻断，而不是 mutation-only validator 缝隙：

`context_binding.views.PARENT` 被定义为 `all declared segments`，`resolve_context()`也只在
`BAG/LEXICAL_BAG` 删除 `ORDERED`。因此：

```text
R032 /identity/groups/0 vs /1: PARENT CTX2 不同
R093 /timing/immediate_delta_ns/0 vs /1: PARENT CTX2 不同
```

R032/R093 的 `ORDERED_SERIES` channel正使用 `PARENT`。绑定的 primitives却要求一条 series的
summary进入 `parent_context + DERIVED(series.stat)`；item才保留 `ORDERED(index)`。当前机器义会把
每个 item放到不同 parent，无法形成一个 32-sample series，或迫使 provider把它们当 per-index
singleton summaries。这会直接改变 feature，不是 admission/model/provider 实现细节。

另一个 validator 缝隙：把 R028 的 `KEY:{field}` 改成合法字面 `KEY:collapsed`，静态
`verify_candidate_bytes()`仍报 `PASS`；只有把 F receipt同时送入 runtime才发现
`SCALAR_ONE` collision。当前文件没有这个 collapse，但 verifier尚未静态证明“所有 finite
SCALAR_ONE concrete identities唯一”。

必须让 `PARENT` 删除所有 `ORDERED` segments，并至少加入：同 series index 0/1 的 ORDERED不同、
PARENT相同；不同 `{series}` capture 的 PARENT仍不同；删除一个决定 identity的 capture引用必须
静态失败。

### B02 pseudo manifest/owner：`ACCEPT CURRENT / VALIDATOR PARTIAL`

原始最小攻击全部关闭：

- 删除 R053：`owner route missing`；
- 只复制 R053：`not bijective`；
- 错路由 R053：`owner path_pattern mismatch`；
- 不存在或 open record `$defs`：拒绝；
- 当前 24 specs 与 24 non-scalar rows一一对应，所有当前 schema target reachable；
- 当前 F 与十一份 branch cases 的 runtime pseudo owner均唯一。

仍有较窄 hardening 缝隙：同步复制 R053 row与 spec，并重算 matrix 后，静态 verifier可报告
10 branch specs和 `PASS`；实际 F runtime随后因两个 owner拒绝。当前 exact 109/24 artifact没有该
问题，完整 package 的 F runtime也能拦住，但“静态 pseudo expected manifest自身不可重复”尚未
被独立证明。建议按 `(event_kind, concrete schema node/trace)`再做唯一键，而不是只做
spec↔owner-row bijection。

### B03 schema-legal `-0`：`ACCEPT`

`mtime_ns/ctime_ns` 使用独立 `SIGNED_DECIMAL_INT_STRING`，R109声明
`NORMALIZE_SIGNED_ZERO...`。将真实 F tree timestamp只改为 `"-0"` 后 schema仍合法、路由到
R109、零 unknown，规范输入为整数 `0`。正整数也进入同一 signed route。

### B04 union trace/selector：`ACCEPT CURRENT`

- static trace现在参与 scalar owner；success UTF8由 R019拥有，错误 branch上的同 path UTF8无
  owner，错误 null由 R020拥有；
- unknown variant label拒绝；
- selector mutation但不更新 binding会拒绝；
- 当前全部 F和十一份 legal branch runtime selector均恰好一个 active alternative。

若同时修改 selector并重算内部 selector hash，静态 verifier仍可通过；实际 runtime branch case会
拒绝。Hash只证明当前 candidate内部一致，不证明 selector等价于 schema branch。对本轮 exact
artifact，十一份异质 branch cases提供了当前映射证据；正式稳定前仍应给每个 registry branch一个
正例和相邻反例，而不是把 binding hash描述成语义证明。

### B05 missing expected channel/context：`ACCEPT`

R068/R070/R072均逐 expected channel列出完整 ordered `expected_stats`，字段 capture进入 CTX2；
name/state、ppid/threads、uid/gid不再坍缩。删除 expected channel被 schema拒绝，错误 stats被
matrix derivation拒绝，empty status branch产生六个 concrete missing paths及对应 pseudo events。

### B06 actual receipt/primitives bytes binding：`ACCEPT`

替换传入 receipt bytes或 primitives bytes但保持 candidate旧 binding，分别得到
`input_schema exact byte binding mismatch` 和 `primitives_binding exact byte binding mismatch`。
verifier hash与 parse的是同一参数 bytes，不再回读默认 path。

### V01 SHA exact-only allowlist：`ACCEPT`

当前六个 SHA row只有允许的 exact-category pair；加入 `DIGEST_PREFIX/HEX_PREFIX_8` 被明确
allowlist拒绝，不再依赖 transform名称 substring。

### V02 closed record reachability/closedness：`ACCEPT`

五个当前 projection `$defs`均存在、closed且在点名 path reachable。不存在或把
`environmentEntry.additionalProperties`改为 true并重绑 schema，都会被拒绝。

### V03 recursive `**` disposition：`ACCEPT`

当前唯一 recursive row是 R007 EXCLUDE；把 INCLUDE R028改为 `/identity/**`被拒绝。

## 4. 新发现：BAG exactly-one-input-channel gate 实现错键

结论：`REJECT VERIFIER PRECONDITION`。

Repaired primitives精确要求：

> for each family, bag_child_context and base_stat, routing authorizes exactly one
> input channel

当前 checker却用 `(family, ctx, channel, stat)`作为 collision key。把 `channel`放进 key以后，两种
不同 input channel永远不会互相碰撞，正好绕过要验证的条件。

当前 artifact按正确的 `(family, ctx, stat)`独立重算仍是 1140/零 collision，所以这不是当前 row
表已有的 collision；但 verifier不能守住它声称已验证的 bound-primitives precondition。最小攻击：

1. 在 registry增加 `ALT_NUMERIC -> stats=[value]`；
2. 给 R109同一 BAG context再加 `ALT_NUMERIC/value`；
3. 合法重算 channel/stat matrix。

结果：

```text
verify_candidate_bytes: PASS
matrix_entries=642
bag_numeric_identity_owners=1150
```

按 primitives要求，这时同 `(family, context, value)`已有 `NUMERIC_SCALAR` 与 `ALT_NUMERIC`两个
input channels，必须 `NOT_QUALIFIED_ROUTING_PRECONDITION`。修复应以
`(family, ctx, base_stat)`聚合 `(route_id, channel)` owner，并要求集合大小恰好 1；报告中的 1140
也应由这个正确 key派生。

## 5. 不属于本轮 routing 失败的边界

以下继续保持 `UNKNOWN/NOT_PROVEN`，没有被本验收误报为 routing失败：

- receipt semantic admission和 producer一致性；
- raw JSON number token、duplicate key及其他 parser/admission边界；
- transform/provider byte实现及两个 clean-room providers一致性；
- C01--C05、deterministic math、model input；
- G、D0/D1/T、因果、功效和成本。

Receipt schema非canonical也仅是未来统一 release package blocker；它当前被 raw-byte准确绑定，
没有造成 path/selector/CTX2错误。

## 6. 复现命令

```sh
PYTHONPYCACHEPREFIX=/tmp/wave025-routing-postfix-pycache \
  python3 -m pytest -q feature-spec/tests/test_routing_v2s_coverage.py

PYTHONPYCACHEPREFIX=/tmp/wave025-routing-postfix-suite-pycache \
  python3 -m pytest -q feature-spec/tests

python3 feature-spec/routing_v2s_coverage.py

shasum -a 256 \
  feature-spec/FEATURE-ROUTING-V2S.candidate.json \
  feature-spec/FEATURE-ROUTING-V2S.candidate.schema.json \
  feature-spec/routing_v2s_coverage.py \
  feature-spec/tests/test_routing_v2s_coverage.py \
  feature-spec/ROUTING-V2S-AUDIT.md \
  feature-spec/COLLECTOR-RECEIPT-V1.candidate.schema.json \
  feature-spec/V2S-PRIMITIVES.candidate.json
```

## 7. 最终决定

本轮不能签发 post-fix acceptance：

1. `PARENT` view保留 index，是当前 exact candidate中的直接 `ORDERED_SERIES`语义错误；
2. BAG uniqueness verifier没有执行 bound primitives规定的 exactly-one-input-channel key。

因此判定：

> `POST_FIX_REJECTED / EXECUTABLE_ROUTING_STILL_BLOCKED`。

同时保留正向结果：当前 109-row path/variant表、当前 24 pseudo specs、F运行时覆盖、十一种合法
branch、signed zero、missing、raw dependency binding、SHA和record/recursive gates均比前版实质改进，
不应回退或因这两个剩余阻断被整体否定。修复两项后只需让原红队重跑本文件中的反例和独立派生，
不需要重做 admission/model/G研究。
