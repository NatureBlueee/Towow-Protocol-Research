# Feature V2 A/B 独立比较

状态：`INDEPENDENT_COMPARISON / NO ADOPTION / NO SPEC OR CODE CHANGE`

日期：2026-08-01

## 1. 比较边界与结论

本比较只读取并依据：

- `FEATURE-SPEC.json`，SHA-256
  `8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a`；
- `NORMATIVE-COMPLETENESS-AUDIT.md`；
- `EXECUTABLE-ATTACK-PROFILE.json`，其当前绑定要求 spec bytes 是语义权威、provider 独立提取、
  replay 的 predictor/matrix byte difference 为零；
- `FEATURE-V2-RESOLUTION-PROPOSAL-A.md`；
- `FEATURE-V2-RESOLUTION-PROPOSAL-B.md`。

我没有读取两份 REDTEAM，也没有读取另一实现的 differential 结论来倒推选择。本文不修改 A、B、
现有 spec、reference extractor、full evaluator 或 profile。

核心结论不是“整份采用 A”或“整份采用 B”：

1. **B 在 predictor/audit 物理分离、typed value、exact-rational numeric、确定性 accumulation 上更强。**
2. **A 在显式 transform identity、逐 path 攻击覆盖、ordered+bag 双视图、route-specific list length、
   branch/missing、所有 lexical route 的 truncation、C01–C05 分块接口上更接近原始解题目标。**
3. **B 的“语义最小”在数处已越过规范消歧，变成攻击能力删减。**尤其是禁止 route-specific
   `list_length`、F02 environment length 只留在 whole-record digest、ordered numeric 不发 position view；
   “长度能从 counts 推出”不等于被冻结的 C01–C05 能学到这项推导。
4. **A 的“最大保留”也不能直接等同于更强检测。**双视图、record exact、list length、branch、missing 和
   per-index numeric 会扩大候选数、hash collision、family normalization 稀释、C01 calibration selection
   机会与 C05 距离成本；未做逐机制 ablation/power/cost 前，增加 feature 也可能制造假绿。
5. 最小综合候选应采用 **B 的值与数值确定性内核 + A 的有界攻击路由与显式 transform 内核**，但先冻结
   一个更小的 closed V2 interface，并把 audit 完全移出 predictor artifact。它仍只是候选，不能追认 F，
   也不能解除 3200-slot rehearsal、D0/D1 sensitivity 或 T equivalence 的独立 blocker。

## 2. 承重点逐项比较

| 承重点 | Proposal A | Proposal B | 更好选择 | 理由 | 新增风险或未决证据 |
|---|---|---|---|---|---|
| closed artifact 与 audit 分离 | 一个 closed root 同时含 `source/features/audit`，以字段声明只有 `features` 是 predictor | predictor artifact 根只含 `schema/features`，audit/debug/source 必须另存 | **B 的物理分离**；把 A 的 source binding 放入独立 audit manifest | 原 spec 明确 source receipt hash 和 excluded audit 都不是 predictor。结构性隔离比 `is_predictor=false` 更难误接入模型，也使 predictor bytes 的独立 replay 边界更小 | 必须另外定义 audit artifact 的 closed schema、receipt hash、spec hash、leaf partition 和两者的交叉引用；分离不能变成丢失来源谱系 |
| typed scalar 与 record | `kind` 区分 STRING/SCALAR/RECORD/MARKER；string raw UTF-8，其他 scalar/record canonical JSON | `TVE2` 对 null/bool/exact rational/string/array/object逐字节编码，record 保序数组和 raw-UTF8-key 排序对象 | **B 的 TVE2 内核** | B 排除 JSON serializer、`1`/`1.0`/`1e0`、string `"1"` 与 number `1` 的跨语言歧义，whole-record association 也有唯一 bytes | exact rational parser、超大 exponent/bignum 与深层 record 可形成 CPU/内存拒绝服务；必须受已绑定 receipt schema 的 byte/depth/count 上限约束，并在 3200 rehearsal 计成本 |
| context 与 transform identity | typed path string；feature id 显式含 `family/context/transform/stat` | binary `CTX2` 后 hex 输出；transform 多数靠 `DERIVED` 或 path 含义隐含，categorical identity 没有独立 transform | **B 的 raw typed context + A 的显式 transform_id** | B 的 context bytes 比展示型 path 更不易碰撞；但 transform 不是 context，`EXACT/BRANCH/MISSING/RECORD_BAG` 需要独立身份，不能靠设计者记得为每个 derived case改 context | context_hex 较大；必须有单一 normative encoder，human pointer 只进 audit。显式 transform 增加 identity 数，但避免不同机制被错误合并 |
| path-specific routing | 七个 family 有细粒度 closed table，并对 F observed shapes 做覆盖自检 | 也有 closed table，但更强调最小发射，部分字段只保留 record atom | **A 的 routing coverage，逐项复审后采用** | 原 profile 要求 F01–F07 full attack surface、无 leaf cap、unknown fail closed。A 更完整保留 F02 length、F04 metadata、F05 cmdline 双视图、F06 position/order 等已声明攻击语义 | A 的 F-shape 自检不是 schema completeness；必须由 receipt schema 派生 route-linter覆盖 error/null/optional/max-size 分支。不得把“F 见过”当成全部合法 shape |
| list length | 所有 table 点名的 list 才发 `LIST_LENGTH`；非 generic | 禁止 generic list length，也没有 route-specific length；主张可由 category/record counts 或 series count推得 | **A 的 route-specific list length** | 对候选可见 cardinality，显式长度是便宜且可能稳定泛化的攻击。被数学推导出来不代表 C01 exact scan、depth-3 tree或固定哈希模型会自动构造该总和。B 因未在旧 transform 名中单列就删除，属于机械合规牺牲检测能力 | 与 bag count/series count高度冗余；会增加 numeric columns。必须以 `length-only ablation` 检查是否提高 D0/D1 recovery、是否降低 T stability或 C05 性能；不允许 generic walker自动添加 |
| ordered / bag | argv/cmdline 等保留 index view，并在明确路径加 scalar bag；record arrays保留 whole-record bag；timing保留 index scalar+series | argv ordered；cmdline ordered+bag；record bag；但 ordered numeric只发 series，不发逐 index numeric | **A 的有界双视图**，但只在原 family 明确声明 order/bag的 paths | `ordered_scalar_events` 与 `ordered_and_unordered_cmdline_events` 是旧 spec 的明示攻击能力；record bag防止 field-wise flatten 丢关联。交换 argv 的假反例正说明不能坍缩 index | 双视图把同一原始事实重复编码，可能放大 C01 search space、L2 family norm和 KNN维度。每个双视图必须有 `order-only/bag-only/both` power/cost ablation；没有增益的冗余视图应移除而不是因“完整”保留 |
| numeric exactness | integer保持 exact；非整数和混合 series按规定 binary64逐步运算，artifact用 integer decimal或 binary64 bits | JSON number先转 exact rational，series/quantile保持 exact rational，进入 model前一次正确舍入 binary64 | **B 到 model boundary 的 exact rational** | 这让解析、sum/delta/middle/type-7 quantile跨语言唯一，且不把运行库的逐步 round order偷偷变成 feature语义。模型阶段仍按 profile的 NumPy float64 provider执行 | 必须明确读取原 number lexeme还是规范化 semantic rational，并要求独立 parser；正确舍入 `ln` 不宜每次依赖重型库，可冻结 count 0..255 的 binary64 bit table。需验证大整数转 float overflow fail-closed |
| missing / branch | null、empty、`SUCCESS/ERROR/NULL`、categorical MISSING、numeric missing indicator、unseen holdout numeric abnormal均有明确区分 | required/empty与 series count较清楚；routing中用 CAT/ERR 表示，但没有 A 那样统一的 branch/missing contract | **A 的单一 branch marker + calibration-frozen missing** | 原 spec要求 explicit missingness且未知 fail closed。一个 union 一个 branch feature能区分现实状态，又避免给未选分支每个 leaf注入重复 missing | calibration-derived context universe若包含 data-dependent index会导致 holdout schema drift；应优先用 schema/routing定义固定 identity，确需 calibration union时必须在 label join前冻结。branch不得重复编码已有 `ok` 数十次 |
| n-gram / truncation | raw UTF-8 byte 1..4 grams，first/last spans独立，direct 4096 family block；所有 S/G lexical routes显式 TRUE/FALSE truncation category | 同样的 bounded byte grams与独立 spans；但 truncation是 SHAPE numeric，`CAT+NGRAM`/无 shape routes可能没有 truncation predictor | **A 的 coverage；hash framing可二选一后冻结** | 两者都消除了 NC08/NC09/overlength歧义。A 更忠实于旧 spec 的“keep truncated flag”，并保证任何 ngram route都不把 false 与 missing混淆 | 4096共享 block丢失 n/context身份并存在碰撞；它是 bounded lexical attack，不是通用 decoder。TRUE/FALSE per-string category增加重复；应按 context聚合 count并做 truncation-only ablation。严禁跨两个不连续窗口制造 grams |
| quantile | R-7，binary64逐步；IQR>0用 IQR/1.349，否则1；不做额外 scale floor | R-7，先 exact rational，`1349/1000` exact，model boundary舍入 | **B** | B 唯一化 median、even case、IQR与常量语义；保留小幅 timing signal，避免 `max(scale,1)`机械压掉检测能力 | 小 IQR 会放大 drift，产生 false fail。必须报告每 family scale分布、clipped比例，并用 T block/role-null placebo检查；不能因“更敏感”直接认定更有效 |
| signed categorical hash | preimage显式含 family/context/**transform**/raw value digest；prefix bucket、末 byte sign；collision说 algebraic sum但顺序不充分 | family/context/raw digest，count不入 hash；明确 bucket/sign、正确舍入 log、固定 identity顺序逐项累加 | **A 的 identity preimage + B 的 accumulation discipline** | transform必须进入 identity；count只影响权重。B 补上了 collision accumulation order和 `log1p` 数值唯一性 | 16384 collision与异号抵消是剩余假绿。固定 256 项 amplitude bits表比“平台正确舍入 ln”更可执行；需 collision fixture和实际 collision-rate报告 |
| C01–C05 interface | predictor 明确分 numeric/categorical/ngram；给 missing、hash、normalization和 C01 raw候选语义 | artifact只分 numeric/categorical，把 ngram sparse rows编码成特殊 numeric，但 matrix又声明独立固定4096 block | **A 的三种语义块 + B 的冻结 column registry** | ngram不是 ordinary numeric：它有固定4096 direct buckets且不做 median registry。三块能减少实现误路由；ordinary numeric registry必须在 calibration label读取前冻结，holdout不得扩列 | 这是 V2 schema的有意变更，不能冒充原 V1 `only_predictor_members`。必须把 C01 是否扫描 ngram counts、C03/C04 presence、C02/C05 count amplitude逐项写明；否则只是把歧义移到 vectorizer |
| 3200 成本 | feature较多：list length、双视图、per-index numeric、branch/truncation；artifact也带 audit/source | artifact较小且少发若干 feature，但 exact rational/context hex较重 | **不能凭文档判通过；先采用有信息价值的 A 路由，再以 rehearsal/ablation决定删减** | 两者的主成本都不是 JSON framing，而是 7×16384 categorical、约6×4096 ngram、numeric registry及 C05 距离。若按 T 的2800 rows构造 dense float64大矩阵，固定哈希块本身已接近数 GiB；必须 sparse/streaming或分 family计算 | profile ceiling是4 GiB、attack 3600s、output 200MiB且明确 `NOT_TESTED`。任何因超限临时降维都违反 profile。必须在 actual-shape+max-size 3200 rehearsal中记录 peak RSS、缓存、matrix representation、每 classifier耗时与输出 bytes |
| self-contained release | 要求收敛为 closed JSON spec+schema、goldens、独立实现、new-batch binding；但保留 proposal/resolution/source多个字段 | 要求选定语义写入新权威 spec、重绑 profile、两实现与 vectors一致 | **合并两者的门，但只设一个 V2 semantic authority** | 正式 provider不应依赖阅读 proposal A/B或 reference code；新 spec应内含 byte grammar、routing、matrix mapping、failure semantics，并和schema/golden manifest/provider source在precommit按exact bytes绑定 | formula-only golden不是 golden。必须冻结 exact input bytes、expected artifact bytes、matrix hashes、failure codes；两实现一致只证明可重建，不证明攻击有功效或现实无泄漏 |

## 3. 机械合规与真实攻击能力

### 3.1 B 的删减不能由“旧表没写这个名字”自动正当化

B 对 generic walker 的拒绝是正确的，但它把两件不同的事合并了：

1. **禁止未授权 generic expansion**；
2. **禁止在 V2 里明确登记一个能提高解题能力的新 transform**。

前者是必要的防漂移，后者不是。`FEATURE-SPEC.json` 是需要修复的 V1，而不是不得改善的神圣边界。
例如 list cardinality 虽可从 bag multiplicity总和恢复，但被冻结的 C01 不是任意算术程序，C03/C04深度有限，
C02/C05又经历 hashing与 family normalization。没有显式长度 coordinate 时，“信息理论上存在”不等于
“本轮被冻结攻击能够使用”。同理，把 environment `value_byte_length` 只藏在 whole-record digest，会让每轮新
key/value形成全新 exact atom，损失 length pattern跨 calibration/holdout 的泛化。

因此，B 更适合作为**字节语义内核**，不适合作为原样采用的攻击路由。

### 3.2 A 的增加也不能由“攻击面更全”自动正当化

A 的 path-specific 增加比 generic expansion安全，但每一项仍需回答：它是否让 C01–C05 在固定样本量下更能
恢复注册控制或拒绝有泄漏的 T，而不是只增加形式完整度。

新增或重复 feature 至少有四种反效果：

- C01 在 calibration 上有更多候选可被选择；在 model-selection randomization 仍为 `NOT_TESTED` 时，这不是
  免费的能力；
- signed hash 的 collision/cancellation随类别数增加，真实 token 可能被其它 feature抵消；
- per-family L2 normalization会让大量无关 ngram/bag coordinates稀释一个窄而稳定的 signal；
- C05 的距离和内存成本随有效非零坐标、训练×holdout pair数增长，超限时正式规则又禁止事后降维。

所以，`ordered+bag`、`list_length`、`record bag+leaf`、`branch+ok`、`truncation+shape` 需要分别做嵌套 ablation。
判据不是“feature 数更多”或“schema tests通过”，而是：

- D0/D1 registered primary recovery 的 classwise lower bound是否提高或至少不下降；
- role-null placebo 与 T 的 false-fail是否恶化；
- fixed profile下峰值资源和 replay是否仍通过；
- 去掉该机制后，哪一种具体、已构造的 leak counterexample重新变成不可检出。

## 4. 最小综合候选 S（未采纳）

以下是足以进入 root 决策与两实现竞争的最小候选，不是 V2 spec：

1. **两个物理 artifact**：
   - `FeatureVectorV2S` 只含 `schema` 与 `features={numeric,categorical,ngram_counts}`；
   - `FeatureAuditV2S` 含 receipt/spec/schema/provider hashes、raw/included/excluded counts、path hashes、
     excluded reasons、unclassified paths、routing counts和 truncation counters。
   两者由同一 slot manifest绑定，但 audit成员永不成为 predictor。
2. **typed bytes**：采用 B 的 `TVE2` 与 exact rational；给所有输入容器、frame、integer digit/exponent、
   nesting和count明确上限。semantic number以约分 rational表示，string raw UTF-8且不 normalization。
3. **identity**：采用 B 的 binary typed context bytes，但每条 feature显式携带
   `(family, context, transform, stat)`；human pointer只进 audit。category digest的 preimage包含这四个
   identity层级、typed value和长度 framing。
4. **routing**：采用 A 的逐 family/path closed table作为起点；未知 path fail closed；由完整 receipt schema
   生成 route coverage证明。保留 SHA exact-only，禁止 generic list/record/string/numeric walker。
5. **结构攻击**：仅在 table点名的 paths保留 route-specific list length；原 spec明确 ordered/bag的路径保留
   ordered和bag双视图；whole-record atom不替代被明确登记的 leaf transforms。
6. **numeric**：direct scalar只发 value；series无论 singleton都发同一13项；ordered series是否另发 per-index
   scalar由 route声明；全部先 exact rational运算，进入 C02–C05 matrix时一次转换到冻结 binary64 bits。
7. **state**：每个 union只发一个 `SUCCESS/ERROR/NULL` branch；empty list由 length/series count表示；
   schema/routing能预定义的 numeric identity不依赖 calibration发现，余下 universe在 label join前冻结；
   unseen holdout numeric identity=`NOT_QUALIFIED_SCHEMA_DRIFT`。
8. **lexical**：UTF-8 byte grams n=1..4，两个 overlength spans独立，per family direct 4096 sparse block；
   每个 ngram route都发显式 TRUE/FALSE truncation category；full exact/shape基于完整 string。
9. **preprocessing**：type-7 quantile用 exact rational和 `1349/1000`；signed category hash包含 transform，
   bucket/sign/collision accumulation顺序冻结；count 0..255 amplitude用预冻结 binary64 bit table；ngram不再
   进入 categorical 16384二次hash。
10. **classifier adapter**：逐项冻结 C01对 exact/numeric/missing/ngram 的 candidate grammar，C02/C05的
    numeric+missing/signed-cat/direct-ngram family block与norm coordinate，C03/C04的 numeric、missing和
    categorical/ngram presence；column registry在任何 label读取前冻结并hash-anchor。
11. **release**：一个 self-contained V2 spec是唯一语义权威；schema、golden manifest、provider source manifest、
    execution provider和profile pointer均按 exact bytes绑定。旧 V1/F没有追认效力。

这是“最小综合”而不是“最少 feature”：它只保留能对应一个已声明攻击、结构区分或明确反例的机制；任何后来
新增 feature 都需同时登记其具体漏检反例、预计 classifier 接口、ablation与成本判据。

## 5. 仍需实验证据

在 S 或任何 A/B 变体被采用前，至少还缺：

1. **byte conformance**：两个互不读源码的实现，对 NC01–NC11、escaped keys、numeric spellings、negative
   zero、invalid Unicode、4095/4096/4097边界、cross-gap grams、duplicate records、hash collision给出 exact
   artifact bytes和matrix hash零差异。formula文本不能代替计算后冻结的 expected bytes。
2. **schema-route completeness**：从完整 receipt schema枚举所有 legal union/optional/max-size shapes，证明每个
   scalar leaf恰好 included或excluded、每个 included path恰好一个 route组合；F observed coverage只作 fixture。
3. **攻击能力 ablation**：在同一 frozen labels/control mapping上比较 B-minimal、A-full和 S；至少单独切换
   list length、ordered/bag双视图、record atom、branch、truncation、per-index numeric。报告 D0/D1 primary、
   五个 classifier holdout结果和 T，不用 calibration improvement冒充能力。
4. **构造性 counterexamples**：每个保留 mechanism至少一个“移除它即漏检”的稳定跨 split任务；特别覆盖
   length-only、order-only、record-association-only、unique lexical code、timing-small-IQR与truncation-only。
5. **假绿压力**：构造高维无关 categories、signed collision/cancellation、unique random record、calibration-only
   context和holdout schema drift，检查新增 feature是否反而淹没已知控制。
6. **3200 actual-shape rehearsal**：不能用12-slot smoke外推。按 profile的200 D0、200 D1、2800 T和 max-size
   fixtures，记录 peak RSS、derived cache、feature output bytes、extract/model/permutation wall time、每 family
   nonzero count、hash collision、C05 distance实现与两次 replay hashes；超限只能 `NOT_QUALIFIED`，不得运行后
   缩减 profile。
7. **因果特异性**：D0/D1 role-null placebo、mapping inversion、marker/token-derived feature ablation、D0→T
   ingress检查；检测到控制不自动证明正式 T collector覆盖所有泄漏。
8. **独立性与自包含**：两实现只读最终 V2 spec/schema/goldens，不读 A/B、reference或彼此代码；然后用未公开
   holdback receipts做 exact differential。共同通过只解除规范可重建 blocker，不解除科学结论 blocker。

## 6. 当前决定边界

本比较支持 root 进一步形成一个 V2 综合候选；它**不支持**现在把 A 或 B 标记为 adopted，不支持改写
`FEATURE-SPEC.json`，不支持把任何 F 输出重算成正式证据，也不支持开始 formal 3200-slot batch。

下一项最有信息量的动作，是先冻结 S 的 exact closed schema、typed/context/hash bytes 与 route table，再让两个
独立实现仅凭这些 bytes和真正求值后的 golden vectors做 blind conformance；其后才运行攻击 ablation和 3200成本
rehearsal。
