# Wave025 model-input layout study 独立红队

状态：`SCOPED_ACCEPT_ARITHMETIC_ONLY / REJECT_FOR_MODEL_LAYOUT_DECISION`

边界：本次只读检查 `model-input-layout-study/`、其声明绑定的四份 feature-spec
候选、F smoke 的十二份公开 `collector-features.json`，以及公开的
`public-plan.json` / `closed.json` 完整性凭据。没有读取 `runner-private-state.json`、
`reveal.json`、角色分配、结果标签或 private registry；没有修改候选实现。C01 的真实
phase boundary 仍未闭合，G 与正式 3200 均保持 `NOT_RUN`。

## 结论

这份研究可以作为**当前十二份 F receipt 的后验结构和存储算术记录**：十二份输入确实是
公开 plan/closed 所列的完整集合，当前 result 可 byte-rebuild，CSR 公式和在其自定义布局
下的 nnz 算术可以重现，E1--E3 的局部表示反例成立。

它还不能决定 MODEL-INPUT，也不能授权删除 signed hash。三个关键原因是：

1. `47 unbounded ordered` 和 `39 open-category` 都不是代码实际证明的量；
2. 6/6 novelty 使用包含实验机制痕迹的 receipt 全字节 hash 分组，且 209 个
   probe-only identity 中 203 个只在十二份 receipt 中出现一次；58.2% 主要是一次性运行
   身份/目录形状压力，不是功效或可迁移 OOV 证据；
3. “exact sparse 覆盖 novelty 后删除 signed hash”尚未成为可执行条件：当前 exact 字典
   使用十二份 receipt 的全集，而不是只由冻结 calibration 形成；所谓 hybrid 又给所有
   category 重复加 hash，而不是只给 calibration-OOV 加 fallback。

因此 scoped verdict 是：

- `ACCEPT`：公开 F 集合的当前快照完整性；当前代码定义下的 shape/CSR 重算；E1、E2、
  E3 的有界表示差异；“这些都不证明 power”的边界。
- `QUALIFIED_ACCEPT`：E4 只证明“纯 family L2 view 且不保留 norm”会丢单轴幅度；
  E5 只证明冻结非零 exact-rational affine map 在数学上可逆。
- `REJECT`：把 2,715 称为真实 predictor universe；把 47 称为 ordered/unbounded；
  把 39 称为 open；把 58.2% 当成 signed-hash 的任务证据；当前删除条件；用当前
  logical-column 数进入 release ceiling。

## 1. 选择防火墙与 F 集合

### 没有显式读取 private/label，但 receipt 本身携带处理痕迹

源代码的实际文件入口与声明相符：四份候选字节和
`slots/*/collector-features.json`，没有 private registry、reveal 或 evaluator 输入。
所以“没有 join 外部 role/outcome label”成立。

但“没有 role/phase leakage”不能成立。十二份公开 receipt 的内容形成清楚的 4/4/4
结构：

- 4 份包含 `WAVE025_CANARY_D1_CURRENT_*`；
- 4 份包含 `current-role-token` 且 cwd 为 `/shared-residue`；
- 4 份不含上述两种标记。

这些可能正是实验要检测的机制痕迹，保留它们不是错误；错误是把基于这些 receipt 的
novelty 当成与处理结构无关的开放世界证据。当前按 receipt SHA-256 交替得到的 6/6 为：

| 公开可见结构 | reference | probe |
|---|---:|---:|
| canary-marked | 1 | 3 |
| shared-role-marked | 3 | 1 |
| unmarked | 2 | 2 |

因此这个 split 虽然没有读 private label，却也不是相对于公开处理形状的分层 split。
SHA-256 是 receipt 全内容的函数，不能把“未显式读标签”加强成“分组与机制内容独立”。

### 十二份 receipt 当前确实完整，但研究本身没有验证该谱系

独立比对得到：glob 的十二个 slot id 与 `public-plan.json` 和 `closed.json` 的 slot set
逐项相同；十二个 `collector-features.json` 的 SHA-256 均与 closed manifest 相同，
`closed.status=CLOSED` 且 `unexpected_slot_entries=[]`。

但是 `layout_study.py` 只要求“恰好十二个文件”，并把它们自己的 set hash 写回 result；
它没有读取并绑定 public plan、closed manifest、slot id 集合或 V1.1 admission receipt。
把任意一份替换为另一份 schema-valid receipt，再重建 result，当前检查仍可能通过。因此：

- 当前这批数据的完整性：`OBSERVED_PASS`；
- 研究程序对正式 F 集合的 admission/provenance 保证：`NOT_PROVEN`。

这不影响它作为探索性快照，但阻止它进入 G input admission。

## 2. routing 静态结论的独立重建

独立解析 exact routing candidate（不调用 study 的三个汇总函数）得到：109 rows、641
route/channel/stat matrix entries，并能按它的“有限 alternation + 每个 `*` 只代入 0”
规则重建 2,715。数字本身可重现，名称和解释不成立。

### 2,715 是 mixed representative keys，不是 predictor universe

该集合混合了三类不同的东西：

- 2,312 个 numeric contextual identities；
- 193 个普通 categorical templates；
- 82 个按 `expected_stat` 分开的 MISSING templates；
- 128 个 route-aware ngram templates。

然而 V2S primitives 的 MISSING category row identity 不含 `expected_stat`，82 个这里应收敛
为 20 个 category templates；direct ngram 最终又按 `(family,bucket)` 聚合，128 个 routing
templates 只来自 6 个实际启用 ngram 的 family。按 primitive 的**输出 template 语义**重算，
代表量是 2,312 numeric + 213 categorical + 6 ngram-family = 2,531，而这仍不是 category
value 展开后的最终列宇宙。

所以 2,715 只能命名为 routing-study 自定义的 `mixed representative keys at index=0`，不能
供模型列分配或宣称为静态 predictor universe。

### 47 不是 “unbounded ordered”

代码只检查 path pattern 是否含任何 `{:*}`，没有检查 capture 是否进入 ORDERED context。
独立分类的 47 行中：

- 只有 11 行在 `context_segments` 中保留 ORDERED capture；
- 另外 36 行是 BAG/CONTAINER 路径，item capture 被有意丢弃。

此外 exact receipt schema 对相关数组有 `maxItems`，CTX2 的 ORDERED index 也受 u32
约束。可以说 routing pattern 没有在自身语法里展开所有 index，但不能说 47 行都是
ordered，也不能从绑定系统推出数学意义的无界。

### 39 不是 “open category” 证明

39 是这段启发式实际数出的 route/channel 对：channel 不是 MISSING/BRANCH、transform
名字含 `CATEGORY`、且不含 `NULL_CATEGORY`。routing candidate 没有 `open` 属性，代码也
没有检查 receipt schema 的 enum/domain。例如 R042 和 R056 的 input atom 是
`JSON_BOOL`，其值域显然不是 open。故 39 最多可报告为
`category-transform route/channel pairs`；开放值域需要按绑定 schema 和规范逐路证明。

## 3. exact sparse / hybrid / CSR 重算

### 成立的部分

- 当前 observed union 的 1,604 numeric、586 category、4,887 occupied ngram bucket、
  62,251 nnz 可以复现。
- 标准 `float64 data + uint32 indices + uint32 indptr` 的 12-row CSR 算式为
  `62,251*12 + 13*4 = 747,064 bytes`，正确。
- 39,264-byte category manifest 等于 586 个 64-hex JSON string 的 canonical array
  开销，正确。
- 三档 hash 的 signed/presence nnz 与 CSR 算术在“hash-all-category”的自定义布局内一致；
  E2 也正确说明 presence 不能由 signed sum 推出。

### 固定 ngram width 多分配了一个永远无路由的 family block

routing 中只有 F02--F07 六个 family 具有 NGRAM_DIRECT route，F01 没有。study 无条件用
`7*4096=28,672`，因此它的 logical width 包含 4,096 个在当前 exact routing 下不可到达的
列。若 layout 的目标是“由 exact candidate 可达的固定列”，则应是：

| layout | study | routing-reachable |
|---|---:|---:|
| exact logical columns | 30,862 | 26,766 |
| exact dense bytes / 12 rows | 2,962,752 | 2,569,536 |
| hash-all 4,096 logical columns | 59,534 | 55,438 |
| hash-all 8,192 logical columns | 88,206 | 84,110 |
| hash-all 16,384 logical columns | 145,550 | 141,454 |

零列不改变当前 CSR nnz，所以 747,064 仍对；它会改变 dense/column ceiling。若团队有意为
未来 routing 预留七个 block，需要在 MODEL-INPUT 里把“预留而非当前可达”写成规范，不应
归因给当前 candidate。

### 当前 hybrid 不是 calibration-OOV fallback

study 的 exact dictionary 取十二份 receipt 的全集 586 columns，同时又把每份 receipt 的
**全部** category identity 投入 signed/presence hash。它测的是
`transductive exact-union + hash-all duplicate view`，不是“冻结 calibration exact + 只对
OOV fallback hash”。

在同一 SHA 6/6 下，reference category dictionary 只有 377 列，probe 有 209 个 dictionary
外 identity。按“reference exact + OOV presence fallback”做结构重算：

| hash width/family | logical columns（6 个 ngram family） | total nnz | CSR bytes |
|---:|---:|---:|---:|
| 4,096 | 55,229 | 62,249 | 747,040 |
| 8,192 | 83,901 | 62,250 | 747,052 |
| 16,384 | 141,245 | 62,250 | 747,052 |

这不是推荐新设计，而是证明当前 4,096/8,192/16,384 hybrid 数字依赖一个尚未声明的
hash-all 语义，不能直接用于 fallback 取舍。

missing、family、route identity 在当前十二份数据的 primitive-compatible路径上没有发现
重复/漏算：numeric 使用 `(family,CTX2,channel,stat)`；category 使用
`(family,CTX2,channel_identity,value_digest)`；MISSING 按 expected channel 聚合；direct
ngram 最终按 family/bucket 聚合。需保留的限定是：这是 observed-union shape，不证明正式
semantic provider 对原始 number lexeme、缺失和所有 cardinality 的实现。

## 4. 6/6 novelty 的稳定性与含义

对同一十二份 open identity set 穷举全部 `C(12,6)=924` 个 reference/probe 划分：

- probe-only fraction 范围：56.06%--62.78%；
- 中位数：57.75%；
- 当前 SHA-alternating：58.22%（209/359），接近中位数，不像从这些 924 个划分中挑出的
  极端最大值；
- 当前划分互换 reference/probe 后为 57.75%。

因此没有证据说 58.2% 是为了得到更大数字而在这些组合中挑选的；但也没有 precommit
证明这个 split 规则是在看结果前确定。更重要的机制解释是：

- 全部 564 个 observed open identity 中，408 个只出现于一份 receipt；
- 当前 209 个 probe-only identity 中，203 个是全十二份里的 singleton；
- probe-only 按 family 分布：F04 168、F02 12、F03 12、F05 12、F07 5。

所以它可靠说明“该 collector 暴露大量每运行变化的 exact strings/records”，不能说明：

- 这些 OOV 与隐藏角色或任务结果相关；
- signed hash 能从它们恢复可迁移信号；
- exact sparse 在正式 calibration/holdout 上失败；
- 58.2% 是未来分布频率、一般化率或 detector sensitivity。

一个同样合理的设计响应是丢弃/归一化大量 ephemeral identity，而不是默认 hash 它们；必须
由 C01 任务差异实验决定。

## 5. E1--E5 最小对的实际判别力

### E1：`ACCEPT_SCOPED`

同一路由的 `alpha`/`beta` 得到不同 exact row identity，而 route-only 相同。它证明
route-only 丢值身份；不证明该身份对 C01 有用，也不证明 exact dictionary 能处理未见值。

### E2：`ACCEPT_SCOPED`

确定性搜索确实找到同一 4,096 bucket 的异号 pair，signed sum 为 0 而 presence 为 1。
它证明若同时需要 magnitude 和 occupancy，presence 必须独立计算；不证明 presence 或
signed hash 有 power。

### E3：`ACCEPT_CONDITIONAL`

在“缺失数值被填 0，且观测值等于冻结 center”的条件下，独立 missing bit 是唯一差异。
这是有效的移除反例。它不替代 routing 对每个 optional numeric 的 MISSING 所有权证明。

### E4：`ACCEPT_ONLY_FOR_PURE_NORM_VIEW`

两个单轴 row `[1]` 与 `[10]` 经 row-wise family L2 都成为 `[1]`，所以**不保留 norm 的纯
normalized view**会丢 family volume。若同时保留 family norm，`([1],1)` 与
`([1],10)` 仍可区分；多轴方向信息也不是该 fixture 检验对象。故“family norm 不能作为
唯一 view、除非任务 ablation 支持”合理；不能扩张为“family norm 一般有害”。

### E5：`REJECT_SPARSE_CLAIM / ACCEPT_EXACT_INVERTIBILITY_ONLY`

冻结、非零 scale 的 exact-rational affine map 可逆，这一点成立。但 fixture 的
`sparse_shape_equal=true` 是错误的：raw `[0,1,2,1000]` 有 3 个非零值，按该 center/IQR
变换后 4 个都非零。逻辑列宽可相同，zero-compressed sparsity 不相同。

而且可逆不等于给定 learner 下等价：正则化、截距约束、阈值、binary64 rounding 和
implicit-zero 语义都可能改变模型。E5 只能支持“冻结参数不会在 exact rational 层面合并
两个 present scalar”，不能支持 robust scaling 的功效或 CSR 等价。

## 6. signed hash 删除条件为什么尚不可执行

当前条件是“如果 formal label-blind calibration dictionary 覆盖 required open values 且满足
ceilings，就删除 signed hash”。这里 `required open values` 未定义，而未来 novel value 按
定义不可能由有限 calibration exact dictionary 预先枚举。用十二份全集证明 coverage 又会
读取 probe，形成循环。

至少需要把删除 gate 改写为以下任一可判定条件：

1. **闭域条件**：该 route 的合法 value registry 在 calibration 前已经完整、冻结且绑定，
   exact dictionary 枚举闭域，新增值被判 schema/registry drift；或
2. **OOV 可合并条件**：MODEL-INPUT 预先规定单一 OOV/忽略语义，独立 holdout 在冻结任务、
   loss margin 和多环境压力下证明相对 hash fallback 无不可接受损失；或
3. **保留 fallback**：任务要求区分未见 value，则 exact one-hot 本身不能覆盖该要求，只有
   当另一个已验证机制承担 novelty 后才能删除 signed hash。

还应冻结：exact dictionary 的唯一生成 phase、hash-all 或 OOV-only、OOV collision/overflow
统计、allowed family blocks、resource ceiling，以及无标签的 removal margin。否则“exact
覆盖后删除”只是结论依赖自己成立的循环条件。

## 复核记录

- `layout_study.py --check RESULTS.candidate.json`：`RESULT_MATCH`。
- 原有 9 tests：9/9 pass；这些测试只说明当前摘要与当前实现一致。
- 独立 routing 重算：109 rows、641 matrix entries、2,715 code-defined mixed keys；按
  primitive output-template 语义为 2,531；47 wildcard rows 中 11 ordered / 36 bag-container。
- F 完整性独立比对：12/12 slot set 与 public plan/closed 相同，12/12 collector hash 匹配。
- 6/6 穷举敏感性：924/924 splits；当前 58.22%，全范围 56.06%--62.78%。

输入快照：

- `layout_study.py` SHA-256 `08bec144e9e8893b5b6fc3a68036b73ccdbafc0eb893a79ac1d511af0b2df83d`
- `RESULTS.candidate.json` SHA-256 `6e95c06839bcb858f8f2fe5980b957aaaa04c8133291cec30c4a1810ab1b8192`
- routing candidate SHA-256 `0f8e294d31d70fe065df4b8fab963827a0b8c52fdc2d549bc27197da0a848439`
- routing schema SHA-256 `1cb50ad5b74c94cfff6fd048b427c964b3e84d22665d6920ae561613d4f25444`
- V1 receipt schema SHA-256 `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209`
- V2S primitives SHA-256 `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b`

