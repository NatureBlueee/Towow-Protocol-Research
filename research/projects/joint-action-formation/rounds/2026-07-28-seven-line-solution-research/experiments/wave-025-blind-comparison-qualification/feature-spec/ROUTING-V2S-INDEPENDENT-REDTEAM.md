# Wave025 V2S structural routing 独立红队

状态：`SCALAR-PATH SUBSET SUPPORTED / EXECUTABLE ROUTING BLOCKED`

日期：2026-08-01

本轮独立审查只攻击 structural routing 的有界主张。没有读取旧
`reference_extractor.py` 或 evaluator engine 作为答案；也没有把 primitives 的 byte/sort
争议、collector admission、canonical release、C01--C05 model layout 或经验功效算成 routing
自身的失败。

审查对象与本轮读取 SHA-256：

| artifact | SHA-256 |
|---|---|
| `FEATURE-ROUTING-V2S.candidate.json` | `371ad0d78741296c186457d325f40be132e67c7adcdad168f33f872d8aa3deb4` |
| `FEATURE-ROUTING-V2S.candidate.schema.json` | `03db9d373fbaf41e15b674f9ca870e18833895358f26cda59b1c756a4374c362` |
| `routing_v2s_coverage.py` | `bc4840abe01f9fa38632b69bb9880c955611a7d2eaecb6af78e84ddf596334e9` |
| `tests/test_routing_v2s_coverage.py` | `2bcb7ae454aa6d697951b0ab831c04921c95ec79f06ddbcb402856c14d71b57e` |
| `ROUTING-V2S-AUDIT.md` | `3c427cdd5033f94bcfb4ab2c1074c97503cf54e5c4689649e8dfb284f0648b6c` |
| `COLLECTOR-RECEIPT-V1.candidate.schema.json` | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` |

## 独立支持的部分

以下较窄结论可以保留：

1. 原 28 项 routing tests 全部通过。
2. 原 checker 对当前 schema 生成 454 个带 trace 的 scalar/absence manifest variants、371 个
   unique `(path pattern, atom, absence)` shape，并报告 scalar/absence owner 零缺失、零重复。
3. 我另外写了不 import `routing_v2s_coverage.py` 的逐 segment matcher 和 scalar walker，独立遍历
   十二份 F receipt。结果仍为 8 份 528 leaves、4 份 547 leaves，每个**实际出现的 scalar
   leaf**都恰好命中一个当前 `SCALAR_LEAF` row。
4. 当前表的六个 SHA row 人工复核均只有 `EXACT_CATEGORY`；23 个当前 lexical row 均有
   full-byte-length、truncated 和 `LEXICAL_ROUTE` n-gram；五个 closed-record row 当前点名的
   `$defs` 都真实存在。
5. F05 当前表确实列出了三份 self-file 的 `byte_length`，并把 status `uid/gid` 声明为
   `TAB_DECIMAL_INT_SERIES`。

这些结果证明“当前 F 样本中的 scalar path/atom 可以被这张表分区”。它们不证明 pseudo-event
owner、concrete context identity、branch selector 或任意 schema-legal scalar value 已闭合。

## 阻断 1：route capture 到 CTX2 的机器语义不存在

68 个 row 的 `context_segments` 含 `$INDEX`、`$FIELD`、`$TREE`、`$FILE`、`$CAPTURE`、
`$SERIES` 或 `$POINT`，但 candidate、schema、checker 和 audit 都没有定义：

- 哪一个 path-pattern segment 建立哪个 capture；
- alternation choice 和 array index 怎样绑定到占位符；
- 占位符怎样变成 primitives 所需的具体 `KEY(name)` / `ORDERED(index)`；
- 未绑定、多绑定、同名 capture 或非规范 index 怎样 fail closed。

这不是排版缺口。按当前机器文件的字面值，`KEY:$FIELD` 只能是名为 `$FIELD` 的固定 KEY，
不是 path capture。于是同一个 `SCALAR_ONE` identity 会收到多个值。第一份真实 F receipt 已经
出现：

| row | 同一声明 context 下的 concrete occurrences |
|---|---:|
| R028 identity pid/ppid | 2 |
| R029 uid/euid/gid/egid | 4 |
| R034 user_info username/homedir/shell | 3 |
| R042 五棵 tree 的 truncated | 5 |
| R078 三份 self-file byte length | 3 |
| R079 三份 self-file digest | 3 |
| R084 wall-clock start/end | 2 |
| R085 monotonic start/end | 2 |
| R097 三个 timing probe elapsed | 3 |
| R101/R102 collection start/end | 各 2 |

R010 的两个 argv、R038 的五个 tree branch、R077 的三份 self-file branch也依赖同一未定义
机制。若 provider 把占位符当字面量，就发生 duplicate identity 或 field/tree collapse；若 provider
自行猜测替换规则，两份 clean-room provider 没有理由产生相同 CTX2 bytes。

最小建设性修复是二选一：

1. 把每个静态 alternation 展开为 concrete route，数组 route 另有明确 index binder；或
2. 冻结 capture grammar，例如 path pattern 直接声明 `{field=name|code|...}`，并冻结
   `capture -> typed context segment` 的注入位置、raw bytes 和失败码。

然后应在 concrete match 后核验 numeric identity：每个 `SCALAR_ONE` 恰好一次，
`ORDERED_SERIES` 以 concrete parent 分组，`BAG_MULTISET` 不跨 tree/field/route 误合并。

## 阻断 2：21 个非 scalar route 完全不在 owner proof 中

当前 108 行由 84 `SCALAR_LEAF`、3 `ABSENCE`、9 `UNION_BRANCH`、7 `CONTAINER` 和 5
`CLOSED_RECORD` 组成。`generate_variant_manifest()`只生成 scalar leaf 和 optional absence；
`verify_candidate()`只对这两类调用 `matching_rows()`。因此 9+7+5=21 个 pseudo route 没有
schema-derived expected manifest，也没有 zero/one-owner 检查。

以下最小变异都被 `verify_candidate()`报告为 `PASS`：

| mutation | checker result |
|---|---|
| 删除 process-view branch R053 | `PASS`, route_count 107 |
| 复制 R053 为 R999 | `PASS`, route_count 109 |
| 把 R053 改路由到 `/invented/process_view` | `PASS`, route_count 108 |
| 把 R104 的 projection 改成不存在的 `#/$defs/DOES_NOT_EXIST` | `PASS`, route_count 108 |

固定的 `route_count == 108` 测试只能偶然拦住前两项；后两项仍然通过。更重要的是，数量恒定不等于
branch/container/record 恰好对应 schema 中一个 reachable node。

因此 audit 中“108 routing rows complete structural assignment”“union/empty/record 已被机器
区分”的表述过强。当前只能说这些 pseudo rows **被写在表里**。

需要从 schema 独立生成三类 expected pseudo manifest：

- 每个选定 `oneOf` node 的 branch selector、reachable branch 和 concrete path；
- 每个点名 array/container 的 count event；
- 每个点名 closed-record projection 的 reachable object node、真实 `$defs`、closedness 和 union
  branch mapping。

再对三类分别做 zero/one owner，不能用总行数替代。

## 阻断 3：schema 合法的 `"-0"` 直接逃出 scalar coverage

receipt schema 的 `signedDecimalString` 是 `^-?(0|[1-9][0-9]*)$`，所以 tree
`mtime_ns/ctime_ns = "-0"` 合法。静态 `_schema_atom()`把它概括为
`DECIMAL_INT_STRING`；运行时 `DECIMAL_INT_RE = 0|-?[1-9][0-9]*` 却拒绝 `-0`，把同一个值
判成 `UTF8_STRING`。

在第一份 F receipt 中只把
`/directory_trees/challenge/entries/0/mtime_ns` 改为 `"-0"` 后：

```text
JSON Schema validation: PASS
classify_receipt status: STRUCTURAL_ROUTING_FAILURE
unknown: path=/directory_trees/challenge/entries/0/mtime_ns atom=UTF8_STRING
```

这直接反驳“每个 schema-legal scalar leaf 均有 owner”，不是 admission 或 primitive byte 实现问题。
必须统一 schema 与 route atom grammar：要么 schema 明确拒绝 signed zero，要么 routing parser接受
`-0` 并按冻结规则规范到整数零；静态和运行时必须调用同一 grammar source。

## 阻断 4：union trace 被保存，但从不参与匹配或验证

manifest 的 `union_trace` 只进入报告对象。`matching_rows()`只看
`event_kind + path_pattern + input_atom`，完全不看 row 的 `union_variant`。把 R019 的
`union_variant` 改成 `BOGUS_BRANCH`，schema 与 ownership仍然 `PASS`。

原 audit 已诚实承认 trace-label registry 尚未冻结，但仍把 454 个 trace-bearing entries称为
zero-unowned variants，容易误解为 active branch 已有机器 owner。准确表述应是：

> 454 个 trace-bearing traversal records 在忽略 trace 后，都能按 path/atom 命中一行。

正式 routing 需要冻结 schema traversal trace、branch label 和 selector 的一一映射，并拒绝未知、
遗漏、重复和 unreachable label。

## 阻断 5：missing route 没有可编码的 expected channel

R068/R070/R072 都只含：

```json
{"channel":"MISSING","transform":"EXPECTED_CHANNEL_MISSING_COUNT","context":"BAG"}
```

但 row/channel schema 没有 `expected_channel` 字段，也没有说明该 transform 要为哪些原始
channel 生成多少个 missing identity。与此同时这些 row 仍用未绑定的 `KEY:$FIELD`，所以 name/state、
ppid/threads、uid/gid 也可能互相坍缩。

这不是要求本轮解决 primitives 算法；它是 routing 没有提供 primitives 明确要求的输入。
至少要为每个 optional concrete leaf冻结 expected route/channel identity、categorical 或 numeric
missing disposition、multiplicity 和 bag grouping。否则“absent 与 null 分开”只有人类可读行，不能
产生唯一 predictor identity。

## 阻断 6：checker 没有绑定传入的 receipt schema

`verify_candidate(routing, routing_schema, receipt_schema)`声称接收待验证 schema object，却把
`routing.input_schema.sha256` 与模块常量 `DEFAULT_RECEIPT_SCHEMA` 的文件 SHA 比较，而不是与传入
对象/bytes 比较。

我删除传入 schema 的 `/cwd` property，仍把原 routing 和原 SHA 声明传给
`verify_candidate()`；结果继续 `PASS`。这允许调用方审查 schema B，同时报告自己绑定 schema A。

checker 应接收实际 schema path/raw bytes，先验证声明 SHA，再 parse 同一 bytes 做 traversal；不能
让 object 参数与 hash source 分叉。

## 次要但应修正的 audit/validator 夸大

- 当前六个 SHA row 的内容确实 exact-only；但 checker 只拒绝 transform 名含
  `SHAPE|NGRAM|LENGTH`。给 R002 添加 `DIGEST_PREFIX/HEX_PREFIX_8` 仍然 `PASS`。所以 audit
  不能说 checker 已验证“仅 EXACT_CATEGORY”，应改为 channel allowlist。
- checker 对 closed record 只检查存在 `closed_projection`；不检查 `$defs` 存在、目标 reachable、
  目标及分支 closed，或 `allowed_variants` 与 schema 对应。
- schema 宣称 `**` 只允许 EXCLUDE row，但 checker 仅校验它位于 pattern 尾部，未校验
  disposition。当前表没有违反，validator 仍未证明该 invariant。
- F receipt 的 `classify_receipt()`只遍历实际 scalar values；不生成 branch、container、record 或
  missing events。因此“12 份 receipt 零 unknown”不能用来支持这些 event 的运行时覆盖。

## 复现命令与观测

在 Wave025 根目录运行：

```sh
PYTHONPYCACHEPREFIX=/tmp/wave025-routing-redteam-pycache \
  python3 -m pytest -q feature-spec/tests/test_routing_v2s_coverage.py

python3 feature-spec/routing_v2s_coverage.py \
  --receipt runs/smoke-v13-20260801-f/slots/*/collector-features.json
```

本轮原始观测：

```text
28 passed
route_count=108
manifest_leaf_variants=454
manifest_unique_path_atom=371
structural_scalar_ownership=PASS
F receipts: 12 ZERO_UNCLASSIFIED; 8 x 528 leaves, 4 x 547 leaves
```

变异攻击通过 deepcopy candidate/schema 后直接调用
`verify_candidate(mutant, routing_schema, receipt_schema)`；输出逐项为：

```text
REMOVE_UNION_R053 PASS 107 0 0
DUPLICATE_UNION_R053 PASS 109 0 0
MISROUTE_UNION_R053 PASS 108 0 0
MISSING_RECORD_DEF_R104 PASS 108 0 0
BOGUS_UNION_LABEL_R019 PASS 108 0 0
SHA_NONEXACT_BYPASS_R002 PASS 108 0 0
UNBOUND_ALTERNATE_SCHEMA_OBJECT PASS 108 0 0
```

## 结论

`FEATURE-ROUTING-V2S.candidate.json` 可以保留为有价值的**人工候选分区**：它比 V1 更明确地列出
了 path、atom、cardinality 和拟保留机制，而且当前 F scalar leaf 的零未知结果可独立复现。

它现在不能进入 clean-room provider，原因不是“还没有证明功效”，而是 provider 尚不能仅凭机器包
唯一重建：concrete context、pseudo-event、union branch、missing identity 和全 schema-legal atom
路由。当前决定应为：

> `BLOCKED_FOR_EXECUTABLE_ROUTING`，但不否定 `CURRENT_F_SCALAR_PATH_PARTITION_SUPPORTED`。

下一版在修复上述六项后，应加入本轮所有最小变异为负测试；之后再审 primitives binding、model
input 和两个 clean-room provider，不能用增加 route 数或维持 108 这一数字代替修复。
