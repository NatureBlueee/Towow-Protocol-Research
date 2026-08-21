# Wave025 Feature V2 根决策

状态：`SYNTHESIS_SELECTED / MACHINE RELEASE NOT YET FROZEN / FORMAL USE BLOCKED`

日期：2026-08-01

决策对象：`FEATURE-V2-RESOLUTION-PROPOSAL-A.md`、
`FEATURE-V2-RESOLUTION-PROPOSAL-B.md`、两份彼此隔离的 proposal red-team，以及不读取 red-team
形成的 A/B 独立比较。

## 1. 决定

不原样采用 A，也不原样采用 B。选择综合方向 `V2S`：

> 采用 B 的 typed byte / exact-rational 确定性内核，采用 A 的有界、逐 path、显式 transform
> 攻击路由；predictor 与 audit 物理分离；再用两份 red-team 暴露的重复 identity、missing、
> route-aware lexical、model-input 与 deterministic-math 问题重写机器接口。

这个决定不是因为综合方案更“原创”，而是因为：

- B 的 `TVE2`、typed context、exact rational 和确定性 accumulation 更能让独立实现重建同一字节；
- B 的“语义最小”已经删掉一部分实际检测能力，不能把旧 transform 名单当成不可改善的边界；
- A 的 route-specific list count、ordered/bag、branch、missing、truncation更接近实际解题，但增加
  feature 不能被当成能力证明；
- A、B 都在 unordered bag child 上生成了重复 numeric identity；A、B 都没有闭合 C01--C05
  的完整 model-input bytes；A、B 也都把 n-gram 聚合到 family 后抹掉了 route/context，可构造漏检。

所以，V2S 是待实现、待攻击的候选，不是已经通过的答案。

## 2. 采用的确定性内核

1. 使用 length-framed typed value encoding；string 保留 raw UTF-8，null/bool/number/string/
   array/object 不坍缩。
2. JSON number 在 feature provider 内按输入 number token 的十进制数学值规范成约分 rational；
   `1`、`1.0`、`1e0` 同值，string `"1"` 仍是不同类型。需要冻结 digit/exponent/depth/size上限，
   防止资源型输入。
3. predictor artifact 中不出现 JSON 浮点数；integer/count/rational 使用 closed decimal strings，
   digest/context 使用 lowercase hex。
4. context 使用 typed binary segments并以 exact hex承载；human-readable pointer只进入 audit。
5. category row identity显式包含 `family + context + channel/transform + value_digest`。channel不是
   展示信息：它决定 C01--C05 eligibility与模型列，必须进入 model hash和row identity。
6. record bag只对机器 routing 明确登记的 closed record item生效；它授权该完整 record的
   `TVE2` atom。任一 schema外字段先 fail closed，不能通过 record digest偷偷进入 predictor。
7. quantile采用 exact-rational type 7；进入冻结 model provider前才正确舍入为 binary64。

## 3. 采用并修正的攻击路由

1. 每个 legal receipt path必须由机器 routing恰好分类为一个 `INCLUDE route` 或一个
   `EXCLUDE reason`。禁止 generic “所有 string/list/number 自动变换”。
2. route可显式登记新的、确有解题意义的 transform；“V1 没有单独命名”不是禁止 V2 改善的理由。
3. 对点名路径保留：exact category、whole-record bag、ordered view、unordered bag view、numeric
   scalar/series、string shape、route-specific container count、branch、missing、integer residues、
   bounded n-gram。每一项随后都必须通过“移除它会漏掉哪个构造性反例”的测试与 ablation。
4. SHA/digest leaf为 exact-only，不得生成 shape或 n-gram。
5. 一个 union只发一个 `SUCCESS/ERROR/NULL` branch；absent、explicit null、empty container 与
   collector failure必须可区分。
6. 每个 n-gram route都同时保留 full byte length和 `TRUNCATED=TRUE/FALSE`。4097+ bytes的首尾
   窗口是两个精确 byte slices，可切在 UTF-8 codepoint中间，禁止 decode/repair，也禁止跨缺口 gram。
7. n-gram仍进入每 family固定4096 direct columns，但 hash preimage必须含
   `lexical_route_context`；共享 column block不等于抹掉 cwd/argv/index/bag-child 的 route identity。

## 4. 重复 identity 的唯一处置

unordered record index不得为了避冲突被重新塞进 predictor；那会把 bag伪装成 ordered list。

机器 routing必须为每个 numeric emission登记 cardinality：

- `SCALAR_ONE`：该 context恰好一个值，输出 `value`；
- `ORDERED_SERIES`：保留点名的 per-index scalar，并在 parent输出固定13项 series；singleton仍是
  同一13项；
- `BAG_MULTISET`：同一 bag-child context/base-stat下的全部值先收集为无序 multiset，再输出
  `count,sum,min,max,lower_middle,upper_middle` 六项；不得 last-write、求任意顺序 delta或直接拒绝
  普通多记录输入；
- `CONTAINER_COUNT`：只在 routing点名的 array/container输出显式 count，不做 generic recursion。

因此 environment key shape、tree path shape/metadata、process/status、canary location/length、
unordered process下相同 cmdline index等合法重复值都有唯一 representation。categorical重复 row按
`family/context/channel/value_digest`聚合 exact count。

## 5. Predictor、audit 与 model input分层

### Predictor artifact

`FeatureVectorV2S` 只包含：

- `numeric`：typed identity + exact rational value；
- `categorical`：typed identity + typed value digest + count；
- `ngram_counts`：family + direct bucket + count。

它不包含 receipt hash、source path、excluded fields、debug或 host facts。

### Evidence sidecar

`FeatureLeafAuditV2S` 必须单独、closed、canonical，并绑定：raw receipt bytes、spec、receipt schema、
routing、provider、predictor artifact的 exact SHA/length；同时保存 included/excluded path partition、
reason、multiplicity、unknown path、routing counts和 truncation audit。classifier不得读取 sidecar。

### Universe 与 model input

需要另有 hash-bound、label-blind 的 calibration universe/column manifest：

- categorical missing必须保留 expected channel/context；不能把多个缺失 transform压成同一个 token；
- numeric missing indicator有独立 closed identity与固定列位置；
- schema可静态决定的 identity优先静态登记；data-dependent identity只能在读取 label前从
  calibration membership冻结；
- holdout-only numeric identity是 `NOT_QUALIFIED_SCHEMA_DRIFT`，不得静默丢弃或扩列；
- C01明确哪些 raw exact/numeric/missing/ngram channels可成为候选；
- C02/C05明确 numeric+missing、signed category、route-aware direct n-gram、family norm列的次序；
- C03/C04的 category/ngram presence按“有 row命中 bucket”的 OR 规则，不按 signed sum是否抵消；
- matrix row order、column order、binary64 endian/bits、+0规范、hash preimage全部冻结。

## 6. 确定性数学

feature provider尽量保持 rational/integer，不让 libm进入 feature identity。

model provider继续受已登记执行环境约束，但还必须冻结：

- rational到binary64的 overflow/subnormal/underflow/tie规则；overflow为
  `NOT_QUALIFIED_NUMERIC_RANGE`；
- coordinate与collision累加顺序、每步binary64舍入、禁止未登记 FMA/contraction；
- count 0..255 的 `log1p(count)` 直接使用预冻结的256项 binary64 bit table；
- L2 square/sum/sqrt与 norm-column的 exact operation order/provider source和bit fixtures；
- type-7、zero-IQR、zero-family-norm、signed collision cancellation的 machine goldens。

如果这些在4 GiB/3600秒 ceiling内不可执行，应修改候选并重新做功效分析，而不是运行后偷偷降维。

## 7. 机器发布包

在任何 clean-room provider 开始前，先形成以下 immutable candidate artifacts：

1. `COLLECTOR-RECEIPT-V1.candidate.schema.json`；
2. `FEATURE-ROUTING-V2S.candidate.json` 与 schema-derived route coverage receipt；
3. `FEATURE-VECTOR-V2S.candidate.schema.json`；
4. `FEATURE-LEAF-AUDIT-V2S.candidate.schema.json`；
5. `MODEL-INPUT-V2S.candidate.json`（C01--C05 layout与failure semantics）；
6. `DETERMINISTIC-MATH-V2S.candidate.json`；
7. `GOLDEN-V2S.candidate.json`：完整 input bytes、preimage hex、expected artifact bytes/hash、matrix
   bytes/hash与negative failure code；
8. 一个非自引用 release manifest，绑定以上 exact filename/schema/length/SHA，以及 provider source
   manifest、execution provider和新的 attack profile pointer。

所有 JSON发行 bytes必须是 runner可接受的 canonical bytes。旧 pretty V1、旧 profile和旧 registries
保持历史不变；不能改写或重算 F来追认 V2S。G 使用 canonical V2S后，必须重新生成 public/private
control registries并重新绑定所有 source locks。

## 8. 能力保留与删减标准

任何保留的 transform至少需要：

- 一个边界明确、跨 calibration/holdout的构造性漏检反例；
- `mechanism off` 时该反例失败，`mechanism on` 时恢复；
- 对 D0/D1 classwise lower bound、T、role-null placebo、资源与 collision的影响；
- 不能解决什么，以及其主要假绿/假失败机制。

没有改善实际检测或因果区分的冗余 feature应删除，即使它形式完整。现有方案更简单、强中心或通用
模型若能在相同 raw receipt、blindness与成本条件下更好完成同一任务，也应直接采用；V2S不因“属于
通爻”获得优先权。

## 9. 继续与停止边界

现在可以继续构造机器发布包、独立 byte conformance和构造性 counterexamples；不能：

- 把 A、B 或本文标为 adopted formal spec；
- 启动正式 provider对未闭合 prose自行补义；
- 用 F output选择对 F 最有利的 semantics；
- 运行 G或3200 rehearsal之前跳过 runner独立审计的 B1--B3；
- 用 schema/tests/hash数量替代 D0/D1 sensitivity、T specificity、因果反例与实际成本。

下一次可改变状态的证据是：机器发布包closed，两个不读彼此源码的实现对 public goldens与未公开
holdback逐字节一致，同时每个新增机制至少有一个构造性必要性反例。
