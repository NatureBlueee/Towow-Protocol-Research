# V2S primitives 独立红队审计

> 状态：`BLOCKED_AS_ROUTING_OR_MODEL_DEPENDENCY`
>
> 审计日期：2026-08-01
>
> 作用域：Wave025 V2S primitives 候选包六文件。本审计没有读取或借用
> 旧 `engine.py` / `reference_extractor.py` 作为答案，没有修改任何候选文件。

## 结论

当前包不能被 routing 或 model 作为可冻结的底层依赖。这不是因为它的主要设计方向
无效，而是因为它尚未满足一个更基础的条件：

> 两个不共享实现的工作者，不能仅依据当前候选包同时得到唯一相同的接受/拒绝
> 结果、predictor bytes 和 audit bytes。

最直接的反例已经出现在公开 golden 内：primitives 规定 categorical 按完整
`channel_identity` 原始字节排序，但 oracle/golden 实际按裸 `channel` 文本排序。
两种排序对 `MISSING` 和 `EXACT_CATEGORY` 给出相反顺序，并生成不同的
predictor SHA-256：

- 当前 golden（裸文本顺序）：
  `061d6c1f184bf6790a1e65677f2b64424418457a81df9cc38c4bda67bf1a4037`
- 按 authoritative candidate JSON 的 `channel_identity` 顺序：
  `d06f4dc1c745e3f5b2f5b3b8f3195f4749b83787ca1679bd8850c7c819571618`

因此，即使不考虑其他问题，现有六文件也无法被同时满足。

## 审计输入

| 文件 | 审计时 SHA-256 |
|---|---|
| `V2S-PRIMITIVES.candidate.json` | `9963e7c636285bdc0a9c7a336f5ba234165c2ed1a8a5cd015ff5198d64709c66` |
| `FEATURE-LEAF-AUDIT-V2S.candidate.schema.json` | `daa01bcd9f9c6cc7b2d9e8a3d13779bbce6394696ea2d344682d42e7c4e00cea` |
| `FEATURE-VECTOR-V2S.candidate.schema.json` | `48025900de2e7639efef8a010994ae606f4201ef9d89ba3378ab77873ccf939f` |
| `GOLDEN-V2S-PRIMITIVES.candidate.json` | `044730ed9767d810c93110bf011b1d24050c23f8d92ce3373c9858086fa6db43` |
| `v2s_primitives_oracle.py` | `82172513eaae5afdd6c19c7923f3ebc4f7009df795ba1db57e14a26ead087eff` |
| `tests/test_v2s_primitives_oracle.py` | `91a8b0b771d4ac96b3b26fbed67b866ef9aabb37801c58e97e2800747fdb89ee` |

## BLOCKER

### B-01 — authoritative categorical 排序与 golden/oracle 字节冲突

`V2S-PRIMITIVES.candidate.json` 和 feature-vector schema 都将 categorical identity 定义为：

`(family_utf8, raw_CTX2, channel_identity, raw_value_sha256)`。

`channel_identity` 不是裸文本，而是：

`FRAME32(domain) || FRAME32(channel) || FRAME32(expected_channel)`。

所以在 family/context 相同时，长度 7 的 `MISSING` 的 `FRAME32` 字节应排在长度 14 的
`EXACT_CATEGORY` 之前。oracle 的 `vector()` 却以裸 `channel` 和裸 `expected_channel`
排序，golden 因此是 `EXACT_CATEGORY -> MISSING`。

这不是“实现细节不同”，而是对公开预测字节的直接分叉。必须选定一个规则，
并重生 oracle、golden 及独立常量。按当前 authority 声明，应优先保留完整
`channel_identity` 的原始字节顺序。

### B-02 — exact-rational 资源边界不唯一，且 oracle 加入了未声明限制

存在三个最小分叉：

1. 候选 JSON 只声明数值指数绝对值不超过 4096，但 oracle 额外拒绝“指数文本位数
   大于 6”。`1e0000000` 的 lexeme 仅 9 bytes，数值指数为 0，且显著数字为 1；
   它通过所有已声明限制，却被 oracle 拒绝。
2. `max_significand_digits` 没有说明是“mantissa 中的所有数字”还是“数学有效
   数字”。`0.` + 767 个 `0` + `1` 的 lexeme 长 770 bytes，两种计数结果分别为
   769 和 1，因而分别被拒绝和接受。
3. 没有冻结 4864-digit numerator/denominator 上限是否应用于派生运算。两个各自
   合法的 4864-digit 整数做 bag sum 可以得到 4865-digit 结果；一个实现可以
   fail closed，另一个可以输出它。

还需要冻结 JSON depth 的根节点计数方法、符号是否计入 canonical digit limit，以及
`max_decoded_input_bytes` 精确指哪一层的字节。

### B-03 — 公开 failure vocabulary 不能表达 oracle 的两个实际失败

oracle 会产生：

- `NOT_QUALIFIED_CONTEXT`（未知 CTX2 segment）；
- `NOT_QUALIFIED_CARDINALITY`（空 BAG_MULTISET）。

两者均不在 primitives `failure_codes` 和 audit schema enum 中。所以工作者要么无法生成
schema-valid audit，要么必须自行将它们改写成另一个 code。空 bag 可以被 routing 在调用
primitive 前处理，但这个前置条件必须成为机器契约，而不能依赖隐含调用顺序。

### B-04 — `MISSING` channel 与 `MISSING2` atom 没有冻结成双向不变式

当前只规定：

- `channel=MISSING` 时 `expected_channel != NONE`；
- 非 missing channel 时 `expected_channel=NONE`；
- MISSING “uses” reserved atom `07`。

但没有机器规则明确表达：

`channel == MISSING  <=>  atom == MISSING2`。

实际 schema 会接受 `channel=MISSING, expected_channel=EXACT_CATEGORY` 但
`value_sha256=SHA256(TVE2("1"))` 的行；oracle `category_eval()` 也允许这个组合。反向的
“非 missing channel + atom 07”同样未被禁止。这会让两个 extractor 使用不同 typed-value
digest，而且两者都能指向当前文字。

需要增加双向不变式、一个唯一 failure code，并加入两个反向 negative golden。

### B-05 — categorical 重复发生时是聚合还是拒绝，没有唯一规则

predictor categorical row 带 `count_u64`，同时候选包要求行 identity 唯一并提供
`NOT_QUALIFIED_DUPLICATE_CATEGORICAL_ROW`。但它没有说明原始路由中的两个相同 atom
应当：

- 先聚合成一行 `count_u64=2`；还是
- 将第二次发生视为 duplicate failure。

ngram 已经明确规定“先 route-aware hash，再按 family/bucket 聚合”，categorical 没有
对应规则。此外 schema 对 emitted count 要求 `>=1`，但 `x-v2s-semantic-rules`
写的是 `0..U64_MAX`。需要区分“零次发生=不发行”和“已发行行的合法计数”。

### B-06 — BAG 的 input identity 在输出中不是单射，需 routing 补充可验证前置

`BAG_MULTISET.input_identity` 包含 `channel`，但输出 identity 只保留 fixed
`BAG_SUMMARY` channel 和 `bag_child_context + DERIVED('bag.' + base_stat)`。如果同一
family/context/base_stat 下允许两个不同 input channel，它们会折叠到同一 numeric
identity。当前 feature schema 又没有 channel/stat 合法组合矩阵，例如
`channel=RAW_NUMERIC, stat=shape.byte_length` 可通过结构 schema。

可以在 routing 层解决，但在它成为冻结、可验证的唯一性前置前，primitives 不能先被
model 依赖。

### B-07 — audit bytes 没有冻结数组排序/去重，且 pair binding 依赖未绑定的外层

predictor 和 audit 的物理分离是正确的：audit 单向绑定 predictor SHA/length，predictor
不含 path/provenance/debug。但当前候选包没有规定以下 audit arrays 的排序和唯一性：

- `included`；
- `excluded`；
- `routing_counts`；
- `truncation_audit`；
- `unknown_paths`；
- `failure_codes`（schema 只禁止重复，不规定顺序）。

两个实现仅交换两个 `included` 项的顺序，就会生成不同但都通过 schema 的
audit bytes。数组还允许相同项重复。

另外，单向 `audit -> predictor` 只有在外层 slot/leaf manifest 同时绑定该 audit 和
predictor 时才足够。否则两个不同 receipt 恰好产生同一 predictor 时，可以替换同样
指向该 predictor 的 sidecar。外层 exact-pair binding 尚不在本包中，因此必须作为上层契约
的强制前置，而不能把“物理分离”直接当成证据闭环。

### B-08 — golden 与测试仍是单 oracle 自证，而 B-01 证明自证未能阻止语义漂移

11 个现有测试全部通过，但四个 candidate JSON、golden 和测试期望都由同一
oracle 生成或重算。测试中确实有一些 hard constants，它们能阻止无意更改；但它们不是
从 authoritative JSON 独立实现得到的第二个意见。B-01 就在所有测试为绿时仍然存在。

当前 golden 也没有覆盖：empty/singleton BAG 边界、MISSING/atom 反向错配、CTX2
非法 segment、duplicate JSON key、lone surrogate/非法原始 UTF-8、裸 channel 与 framed
channel 的排序分叉、categorical 聚合、ngram bucket collision 合并、audit array
置换/重复、derived rational 越界。

## SHOULD_FIX

### S-01 — 将“结构 schema 通过”与“V2S 语义有效”明确分层

标准 Draft 2020-12 validator 不会执行 `x-v2s-*` 扩展。独立试验表明，以下都可以通过
现有 feature schema：

- `context_hex="00"`（并非合法 CTX2）；
- `RAW_NUMERIC + shape.byte_length`；
- 重复且未排序的 categorical rows；
- `MISSING` channel 配 string typed-value digest。

这不是 JSON Schema 的 bug。需要一个被绑定的 semantic validator，并把上述责任明确放到
schema 或 validator 之一，不应让两者都假设对方会处理。

### S-02 — 给 TVE2 一个能保留重复 key 信息的输入边界

TVE2 文本要求 duplicate object key fail closed，但普通 map/dict 在进入 encoder 前已经丢失这个
信息。应冻结为“从保留 pair 的 raw JSON parser 接收”，或者要求上游附带 duplicate-free
proof/binding。

### S-03 — 把“原始非法 UTF-8”和“合法全文在截断窗口中不可解码”分成两个测试

后者是允许的 ngram byte behavior，前者应是 `NOT_QUALIFIED_INVALID_UNICODE`。当前 golden
只覆盖后者；应增加 overlong UTF-8、lone continuation byte 和 lone surrogate 输入边界。

### S-04 — 为 audit 补充完整的内部一致性规则

除排序/去重外，还应对 `routing_counts == sum(included multiplicity by route)`、truncation
spans 与 full length 的关系、bindings 的真实字节回读、qualified 状态下所有未知路径关闭
进行语义校验。

## CONFIRMED

### C-01 — typed-value digest 与 row hash 分离是清楚且可独立复算的

本审计以只依据候选 JSON 的小型字节实现重算，未 import oracle，得到：

- TVE2 string `"1"` value SHA:
  `fd49870273bf5b0816211d0e881dab5fd8af15505dc85bdaca1c356638b82f1c`
- TVE2 number `1.0 -> 1/1` value SHA:
  `15f43bbec9eaf2e6329b4cf8b48f0ed0e24dc53a911f758fbb67fcb8fc9fb3e7`
- JSON null row SHA:
  `ad3011609813cd082cc67a0936f143bd58cead5c7b94f885b019a656b5d13847`
- MISSING2 row SHA:
  `d4a4d438b1321d4e548ab82ee82b5dcaec797321957ee90a4f45fe115b3fcdfe`

这些与公开 hard constants 一致。predictor 存 value digest，row SHA 仅是包含
family/context/channel/value digest 的派生检查值；两者不应互换。

### C-02 — CTX2 与 channel framing 本身具有明确域分离和长度边界

KEY/ORDERED/BAG_ITEM/DERIVED 的 tag 分离、segment count、FRAME32 和全局不做 Unicode
normalization 的方向是确定的。已公开的 `KEY(a)+STRING(bc)` 与
`KEY(ab)+STRING(c)` 碰撞对被正确分开。B-01 是“对 framed identity 如何排序”的
实现冲突，不是 framing 本身不可区分。

### C-03 — BAG 在非空输入上的值语义是可复算的

独立计算得到：

- singleton `[7]`：`count=1, sum=min=max=lower_middle=upper_middle=7`；
- `[1,4]` 和 `[4,1]`：都是 `count=2, sum=5, min=1, max=4, lower=1, upper=4`。

因而非空 bag 的 permutation invariance 成立。empty bag 被明确留给 routing 决定也是一个可以
保留的分层，但必须解决 B-03 中的调用前置和 failure 语汇冲突。

### C-04 — route-aware ngram hash 与截断字节窗口可独立复算

未 import oracle 的重算得到：

- `cwd`, n=2, gram=`ab`: digest
  `51b3833f77ac54c3beb831cfd8820835a8baa30c90c73657010b791064f834b9`, bucket 831；
- `argv[0]`, 同样 gram: digest
  `5ee2cb19daf48d830429d0541cf409e4c4a0ad89280113f1efa58ea53477c333`, bucket 2841。

这证明 route CTX2 确实进入 hash。另外，独立搜索找到 `KEY(r1)` 和 `KEY(r16)`
在 n=1, gram=`a` 上同落 bucket 2561，但 digest 不同。按当前规范，它们必须在
hash 之后合并为一个 `(family, bucket)` count，而不能生成两个重复行。该合并规则
已经足够清楚。

4097-byte 合法 UTF-8 样本被分为两个 2048-byte 窗口，两个窗口各自都不可
UTF-8 decode，但按 raw bytes 扫描是允许的。1..4-gram 窗口总数是 16372，两窗口之间
没有人工 cross-gap gram。这与 golden 一致。

### C-05 — canonical JSON 对已归一化对象的序列化规则足够明确

原始 UTF-8 key 排序、小写 `\\u00xx`、五个 short escapes、不转义 solidus、可直接编码
scalar 不 ASCII-escape、compact JSON 及唯一 LF 已经确定。一个手工常量是：

- semantic object：`{"a":"U+0001 + LF", "é":"/ + U+2028"}`；
- canonical bytes hex：
  `7b2261223a225c75303030315c6e222c22c3a9223a222fe280a8227d0a`；
- SHA-256：`f33a9138c22f68eae978af81a4b63067a26c9572017df665dbbe8bb016307bac`。

剩余问题在“数组中的语义行如何先归一化”，而不在 JSON string/object serializer 本身。

### C-06 — 候选包没有把自己伪装成正式 canon

`candidate_status=NOT_ADOPTED__NOT_FORMAL_CANON`，oracle 明确标记 non-authoritative，promotion
显式要求 clean-room byte conformance、holdback agreement 和独立 routing/model 决定。这些声明
是真实的边界，也正是本审计建议继续执行的门槛。

## 解除阻塞的最小闭包

在 routing/model 可以绑定 V2S primitives 前，至少需要：

1. 解决 B-01，生成与 authoritative 排序一致的新 golden；
2. 将 numeric limits 的计数单位、派生结果上限、depth 和 input-byte 边界写成机器
   可判定规则，去掉 oracle 的未声明限制；
3. 关闭 failure-code enum，并冻结 empty BAG 的调用前置；
4. 增加 MISSING channel/atom 双向不变式与 categorical occurrence 聚合规则；
5. 让 routing 给出并验证 channel/stat 矩阵、BAG identity 唯一性和 empty 映射；
6. 冻结所有 audit array 的 sort/unique identity，并让外层 manifest 同时绑定 exact predictor
   和 exact audit；
7. 由两个不共享 oracle 与测试 helper 的实现独立重算全部 decisive golden，特别
   加入本文的最小反例；
8. 在两实现字节一致后，再让 routing 和 model 各自绑定新 primitives SHA。

在此之前，当前 primitives 可以继续作为设计候选和反例载体，但不能被当作已冻结
的 predictor/audit byte contract。
