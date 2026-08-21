# Executable evaluator profile compatibility

> 状态：`SYNTHESIS / NO VERDICT / NO RANKING / NO EVALUATOR CODE CHANGE`
>
> 本文只回答：独立特征规范与当前可执行评估器之间哪些差异会改变所检验的主张，哪些只影响成本或统计功效，以及在当前机器上最小而仍保持候选可见叶覆盖的精确执行剖面是什么。本文不判断任何候选是否通过，也不对候选排序。

## 1. 输入边界与材料身份

本轮只比较以下冻结材料；没有读取 runner 源码，也没有把 runner 的实现当作独立事实来源：

| 材料 | SHA-256 |
|---|---|
| `feature-spec/FEATURE-SPEC.json` | `8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a` |
| `feature-spec/reference_extractor.py` | `710602d7e259c0cdab151979ab2aeb439279faae270eda40357f24726beb5bf5` |
| `feature-spec/README.md` | `3ff6227ef7ecc8d68bebfe87de6ff1c2f44fa73ea45c06b82ce25820d8c126f1` |
| 根目录 `INTEGRATION-FINDINGS.md` | `41a330dd882915b1b60ac87fe5222cb30bd46b0bf0f5003f4eb81d97f8be619b` |
| 当前独立评估器实现（仅用于比较现有执行剖面） | `40864bff4bfa43e323fddebbb129fdc407a1ca366f081288396e7d4ba40bdc95` |

工作区内没有可供本轮复测的真实 `collector-features.json`。因此下文性能数字来自本轮新生成的、满足输入结构的确定性合成 receipt 与确定性矩阵；它们证明当前机器上的计算可行性和量级，不证明真实 receipt 的内容分布、候选效果或总体运行时间。

## 2. 核心结论

当前机器上没有证据要求删减候选可见叶、把 16,384 个类别桶压缩到 128 个，或删除任一已冻结分类器。完整叶审计、完整 F01–F07 特征族、C01–C05 五类攻击和 1,600-slot 数据规模都具有可执行路径。

真正不可接受的成本集中在一个位置：对五个分类器做 `9,999` 次“每次重训再评分”的置换。仅 logistic 的确定性向量化下界就约为 61–81 小时，还未计 Armijo 回溯、其余模型和 I/O。最小可执行剖面因此应当：

1. **保留全部候选可见叶和五类冻结攻击；**
2. **保留 9,999 次 block-preserving 置换，但在冻结、无调参、标签无关的特征与模型管线下，对冻结 holdout 预测做置换；**
3. **把 9,999 次全量重训置换拆成后续独立的 `MODEL-SELECTION-RANDOMIZATION` 挑战，不能悄悄宣称已经满足原规范的这项要求。**

这得到的是一个“叶覆盖精确、攻击集合精确、随机化范围被明确缩窄”的可执行剖面，不是与最终 `FEATURE-SPEC.json` 完全同一的执行语义。

## 3. 兼容性差异：假绿风险与成本/功效必须分开

| 冻结规范位置 | 当前评估器位置 | 差异性质 | 最强假绿路径 | 处理 |
|---|---|---|---|---|
| 对所有 candidate-visible leaves 做 inclusion/exclusion partition，F01–F07 全覆盖 | 只验证顶层并 flatten 已知根；最多保留 96 numeric | **直接改变主张** | 泄漏只出现在被截断的 timing/path/count/nested leaf，评估器根本没有观察它 | 采用完整叶分区；任何未分类可见叶 fail closed |
| 每族 4,096 个共享 n-gram 桶；model 类别 16,384 桶 | 剩余值压入 128 个 signed-hash 类别槽 | **直接改变主张** | 正负碰撞相消，或高频无关值淹没低频候选编码 | 保留规范桶数；不得以维度 cap 代替 |
| raw exact categorical/value、numeric 与 TOP256 两 token conjunction；support total 10 / class 5 | 单路径 total mapping；minimum support 2；无冻结 conjunction | **直接改变主张** | 单 token 各自无信息，但两 token 共现唯一编码候选 | 采用 C01 精确扫描与 bitset conjunction |
| L2 logistic `lambda=.01`，robust median/IQR，clip `[-8,8]`，Armijo，最多 2,000 步 | `L2=1`、固定学习率、120 epochs、row L2 | **直接改变攻击能力** | 弱而分布式的信号被强正则或不同归一化压没 | 采用规范语义；只替换为数值等价、冻结的向量化 provider |
| depth-1 stump 与 depth-3 tree | 一个 depth-2 tree，每特征最多 9 个阈值 | **直接改变攻击能力** | 泄漏依赖窄区间、三路交互或不在九个阈值中的切分 | 同时保留 C03 与 C04；向量化枚举规范候选 |
| k=11，包含第 11 邻居同距离 ties | k=5 | **直接改变攻击能力** | 稀疏局部群在 k=11 才稳定，或 tie 处理改变多数票 | 采用 k=11 与规范 tie 规则 |
| 每类 one-sided Clopper–Pearson，class-tail `alpha=.025`，再平均两类界 | balanced total-correct Clopper–Pearson | **改变决策主张与覆盖**，不是计算优化 | 总体正确数掩盖一个类别的异常，或给出与冻结门槛不同的边界 | 正式运行采用 class-wise + Bonferroni；功效冲突另行显式处理 |
| 9,999 次、challenge×phase×block 内置换 | 199 次 derived shuffle，且不保 block | 次数差异主要是**分辨率/功效**；不保 block 是**主张改变** | 时间/批次漂移被打散后形成错误 null，或 p 值分辨率不足遮蔽近阈值异常 | 保留 block 与 9,999 次；采用冻结预测置换；全重训另列挑战 |
| host-only association 单独成族并作 Holm | 简化 host audit | **直接改变随机化闭包** | host 聚类/运行主机关联没有进入同一 multiplicity 语义 | 保留独立 host family、9,999 次与 Holm |
| D0、D1 为不同 learned controls；每族预先承诺 primary detector | 可由较小攻击集合吸收控制 | **直接改变控制含义** | 事后挑“最会通过”的模型掩盖某族控制失效 | 每族预注册唯一 primary；禁止 secondary rescue |
| 精确 float64 数值语义与可复现 provider | 纯 Python 缩减矩阵 | provider 本身可只是**成本差异**；float32/不稳定路径会改变语义 | 舍入、非有限值或线程非确定性使边界样本翻转 | 冻结 NumPy provider、dtype、线程和 replay；非有限值 fail closed |
| 向量可流式缓存 | 全部 Python 对象常驻并非规范要求 | **仅成本/内存** | 无；前提是缓存内容由同一冻结输入重算并哈希验证 | 允许临时流式缓存，不允许缓存成为新的 truth source |

判断原则：模型参数、特征叶、哈希空间、控制语义、CI 定义和 block 结构都不是“实现细节”。只有在数学输出、输入覆盖和失败语义保持不变时，provider、批处理、缓存和向量化才属于纯成本优化。

## 4. 当前机器的确定性合成基准

### 4.1 完整 reference extractor

使用本轮生成的有效合成 receipt，并逐步扩大每棵嵌套树的 entry 数量：

| 每树 entries | receipt 大小 | raw leaves | numeric | categorical | 单次耗时 | tracemalloc peak |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 7,255 B | 383 | 3,957 | 1,311 | 0.0537 s | 1.59 MiB |
| 16 | 19,135 B | 1,043 | 4,133 | 2,231 | 0.1386 s | 2.21 MiB |
| 64 | 66,655 B | 3,683 | 4,658 | 4,631 | 0.5568 s | 4.37 MiB |
| 128 | 130,015 B | 7,203 | 5,164 | 7,831 | 1.0536 s | 7.31 MiB |

另一份固定 receipt 连续提取 50 次共 1.4310 s，即 28.6203 ms/receipt；顺序处理 1,600 份约 45.79 s。该 receipt 产生 3,719 numeric、983 categorical，序列化向量为 506,973 B；按相同大小线性估计，1,600 份约 773.6 MiB。

根集成材料报告的一份真实 receipt 为 3,426 numeric、1,214 categorical，与上述合成量级一致；但本文没有重跑该真实文件，所以不能把 45.79 s 或 773.6 MiB 当作真实批次的已测结果。结论限于：完整叶提取适合流式执行或临时磁盘缓存，没有计算理由先删叶。

### 4.2 当前缩减评估器基线

在 400 train / 800 test、320 维确定性纯 Python 矩阵上：

| 操作 | 耗时 |
|---|---:|
| logistic fit / predict | 2.3521 s / 0.0197 s |
| depth-2 tree fit / predict | 0.6225 s / 0.0011 s |
| kNN-5 fit / predict | 0.0017 s / 14.6884 s |

约 17.7 s 的核心模型耗时说明缩减版能运行，但不能为 96/128 维 cap 提供科学理由；它只说明纯 Python 的 kNN 路径会成为瓶颈。

### 4.3 完整维度的向量化下界

按 3,426 numeric、每 numeric 一个 missing indicator、16,384 categorical 与少量 family norms，稠密近似维度为 23,250。400+800 行 float64 矩阵约 212.9 MiB。

在当前环境的 NumPy 2.0.2 上：

- 使用 warning-free `np.einsum(..., optimize=False)`，3 个 logistic 固定步为 0.04394 s；线性外推 2,000 步为约 29.3 s，尚未计 Armijo 回溯。
- kNN 距离点积测得 20×400 为 0.19186 s；线性外推 800×400 为约 7.67 s。
- 对 400×3,426 numeric：全特征排序 0.08363 s，累计类别计数 0.01780 s。
- 对 400×16,384 categorical：presence counts 0.06992 s；depth-3 的朴素重复上界约 1.20 s。
- TOP256 的 32,640 个 bitset conjunction 交集与计数为 0.07457 s。

普通 `@`/matmul 路径虽然给出约 22.0 s/2,000 步的更低外推，却在有限输出下产生了 63 条运行时 warning；float32 路径也出现相同类别异常。它们不能进入精确剖面。这里采用的 29.3 s 仍只是固定步下界，不是完整 Armijo 实测；正式运行前必须用冻结 provider 做一次 1,600-slot rehearsal。

### 4.4 置换成本

- 800,000 个确定性 SHA key（1,000×800）耗时 0.6200 s；9,999 次约 6.20 s，再加预测评分仍为秒级。
- 若每次置换都重训，单 logistic 以 22.0–29.3 s 的下界计算，9,999 次约为 61.1–81.4 小时；实际还要加入 Armijo、其余四模型和 I/O。

所以应削减的是“每次置换重训”这一计算重复，不是候选可见信息，也不是分类器集合。

## 5. 最小可执行的精确剖面

建议冻结为 `WAVE025_EXECUTABLE_ATTACK_PROFILE_V1`。这里的“精确”表示：以下字节级剖面一旦冻结，评估器只能执行它，不能用内部默认值重新定义攻击；不表示它已覆盖所有可能攻击。

### 5.1 科学上不可移除的核心

1. **输入与叶覆盖**
   - 从每份 raw `collector-features.json` 独立重提取；不得信任 runner 提供的向量。
   - 逐叶执行 final feature spec 的 inclusion/exclusion partition；未知 leaf、重复路径冲突、schema 漂移均为 `NOT_QUALIFIED`。
   - 保留 F01–F07、字符串 shape、UTF-8 n-gram 1–4、每族 4,096 n-gram 桶、16,384 model categorical 桶、numeric summaries/residues 和 missing indicators。

2. **五个冻结攻击**
   - C01：raw exact categorical/value、numeric 和 TOP256 双 token conjunction；support total 10 / class 5。
   - C02：L2 logistic，`lambda=.01`，median + IQR/1.349（退化时 1），clip `[-8,8]`，full-batch gradient + Armijo，最多 2,000 步。
   - C03：depth-1 stump。
   - C04：depth-3 tree。
   - C05：k=11，包含 kth-distance ties。
   - 每个 family 的 D0/D1 primary detector 在运行前唯一绑定；不得以其他模型事后 rescue。

3. **精确决策语义**
   - 正式 CI 使用 per-class one-sided Clopper–Pearson、每类 tail alpha `.025` 后平均，不能退回 total-correct CI。
   - 9,999 次 challenge×phase×block 内 label permutation；对冻结 holdout predictions 评分。
   - host-only association 单独 9,999 次，按冻结 family 做 Holm。
   - 置换非拒绝只作诊断，不作“等价”证明，也不能覆盖 CI gate。

4. **冻结计算 provider**
   - Python 3.9、NumPy 2.0.2、float64、单线程；C02/C05 使用 `np.einsum(..., optimize=False)` 的已审路径，C03/C04 使用确定性向量化枚举，C01 使用 raw token bitset。
   - 绑定 NumPy distribution/wheel hash、平台、线程环境、dtype、tie break、排序稳定性和非有限值策略。
   - 同一输入做两次独立 replay；矩阵、模型输出、预测和统计量哈希不一致即 fail closed。

5. **资源策略**
   - receipt、向量和预测允许按 slot 流式处理并写入 batch 内临时/派生缓存；缓存必须绑定 raw receipt hash 与 profile hash，能够被删除后完整重算。
   - 不要求把约 0.8 GiB 的序列化向量同时保留为 Python 对象。

### 5.2 明确采用、拒绝和拆分

| 决定 | 项目 | 理由 | 若错误削减时的最强假绿 |
|---|---|---|---|
| 采用 | final reference extractor 的完整语义，但由 evaluator 独立实现/核验 | 叶覆盖是攻击面，不是性能装饰 | 未分类嵌套叶携带候选身份 |
| 采用 | 3,426 级 numeric 与 16,384 categorical，不设 96/128 cap | 当前机器可处理 | 被丢弃叶或碰撞相消形成不可见泄漏 |
| 采用 | C01–C05 全部规范参数 | 五者覆盖不同信号结构 | 分布式、窄阈值、三阶交互或局部群漏检 |
| 采用 | class-wise CP + Bonferroni | 与冻结科学主张一致 | 总体正确数遮蔽类别条件异常 |
| 采用 | 9,999 block-preserving frozen-prediction permutations | 保持 block null 与精细 p 分辨率，秒级可行 | 不保 block 会把漂移当标签信号或抹去真实条件结构 |
| 采用 | 9,999 host-only + Holm | host 泄漏需独立闭包 | host 聚类逃逸 multiplicity 控制 |
| 采用 | float64、单线程、warning-free NumPy provider | 是数学等价的成本优化候选 | warning/舍入使边界统计静默翻转 |
| 拒绝 | 96 numeric / 128 categorical cap | 没有计算必要性且改变可见攻击面 | 被裁剪或碰撞的唯一编码通过 |
| 拒绝 | row L2、`L2=1`、120 epochs、k=5、depth-2/9 thresholds | 都改变冻结攻击，不是 provider 优化 | 弱分布式、局部或窄交互信号通过 |
| 拒绝 | 199 次非 block permutation | 同时损失分辨率并改变 null | 漂移/host/block 混杂被错误校准 |
| 拒绝 | float32 或产生 warning 的 matmul 路径 | 数值身份和失败语义不稳定 | 非有限中间值或边界舍入被忽略 |
| 拆分 | 每模型 9,999 次 retrain-and-rescore | 当前机器至少需 61–81 小时/仅 logistic，不能伪装为已执行 | calibration 使用标签选叶、调参或选择模型时，冻结预测置换看不见选择偏差 |

拆分后的挑战名为 `MODEL-SELECTION-RANDOMIZATION`。在 V1 中，只有同时满足“extractor 完全标签无关、超参数和 primary detector 预先绑定、没有 holdout 调参、实现与依赖哈希冻结”时，frozen-prediction permutation 才可运行；任一条件不满足，整个批次 `NOT_QUALIFIED`，不能用 V1 绕过全重训检验。

## 6. CI 功效冲突不是性能问题

在 T 每类 400、总计 800 且目标上界 0.55 时：

- total-correct CP 在 400/800 时上界约 `0.5296669`；
- 规范的 per-class CP 在每类 200/400、tail alpha `.025` 时，每类上界约 `0.5500921`。

因此“恰好 50% 且两类完全均衡”的结果会以约 `0.0000921` 越过规范门槛。换言之，当前样本量与 class-wise gate 对真实 chance 行为只有约一半的接纳概率量级；这与材料中偏向 total-correct 口径的功效预期不一致。

这不授权 evaluator 静默改用 total-correct CP。正式运行前必须在新的冻结决定中二选一：

1. 接受 class-wise gate 的高 false-fail 风险；或
2. 增加 T holdout / 调整阈值，并重新给出同一 class-wise 判据下的功效计算。

未作新冻结决定前，`WAVE025_EXECUTABLE_ATTACK_PROFILE_V1` 保留 class-wise 语义，并把功效不足列为显式限制。这里主要风险是错误拒绝而非计算成本；改用另一种 CI 则会进一步引入类别条件异常被总体数遮蔽的假绿风险。

## 7. evaluator 如何独立绑定剖面，而不是自己定义攻击

正式 batch 必须包含 canonical `EXECUTABLE-ATTACK-PROFILE.json` 的**完整字节**，而非只包含 evaluator 自报的配置摘要。precommit 和外部双锚至少共同绑定：

- profile bytes SHA-256 与 profile ID；
- `FEATURE-SPEC.json` 字节哈希；
- evaluator 的独立 extractor、五个 classifier、CI/permutation 实现源码哈希；
- Python、NumPy distribution、平台、dtype、线程、排序/tie/非有限值策略；
- D0/D1 的 family→primary-detector 映射；
- slot population、train/test 切分、CI 阈值、permutation count/block key、host family 与 Holm 规则；
- 缓存/流式策略、资源上限、已拆分的 `MODEL-SELECTION-RANDOMIZATION`；
- raw receipt manifest、slot→receipt hash、profile→output artifact 谱系。

评估器的职责仅是：加载这些冻结字节，验证其 ID/hash 是自己明确支持的版本，然后执行。内部默认值不得覆盖 profile；不认识的字段、provider、版本或约束必须 `NOT_QUALIFIED`，不能忽略。

独立性还要求：

1. `FEATURE-SPEC.json` 是语义 authority；`reference_extractor.py` 只是可对照实现，不是评估器应直接 import 的 truth source。
2. evaluator 应从 raw receipt 独立实现提取，或者把冻结 extractor provider 当作不受信输出，并独立重做 leaf partition、schema、计数与不变量核验。
3. evaluator 不接受 runner 的 feature vector、模型预测、统计量或“已验证”标志。
4. 每个 slot 留下 raw receipt hash、独立 vector hash；每个 classifier 留下 calibration/train identity、prediction hash、CI/permutation输入和输出 hash。
5. 同一冻结输入的独立 replay 不一致、出现 warning/non-finite、或发现 profile 与代码支持表不一致，均不得产生候选结论。

这样 profile 定义攻击，evaluator 只证明“自己忠实执行了被锚定的攻击”；二者不会循环自证。

## 8. V1 仍明确不检验的攻击与最强残余假绿

即使完整执行 V1，下列情况仍不能被描述成“已排除全部泄漏”：

- **全量重训随机化未运行：** 最强残余是假如 calibration 阶段实际读取标签并选择叶、阈值、模型或超参数，冻结预测置换可能保留被选择出来的偶然优势。V1 以标签无关实现、预注册和 fail-closed 审计约束它，但没有用重训置换直接测量它。
- **有限模型族：** 高阶 parity、一次性 codebook、跨 receipt 长程状态或只在未建模序列关系中可解码的信号，可能逃过 C01–C05。这些属于后续 attack-family expansion，而不是删除叶的理由。
- **合成性能基准：** 真实 receipt 可能有更大字符串、更多叶或极端类别基数；正式 rehearsal 必须验证最坏 slot、总磁盘、峰值内存和超时，不能从合成基准推断真实分布。
- **同机独立性的上限：** 哈希/replay 能发现普通漂移和不一致，不能证明拥有同一写权限的恶意本机进程无法同时篡改输入与输出；需要更强威胁模型时必须使用 worker 无权改写的外部锚或签名域。

## 9. 进入正式运行前的最低 rehearsal

在不改写上述科学语义的前提下，先用冻结 provider 做一次完整 1,600-slot rehearsal，并只验证执行能力：

1. 所有 candidate-visible leaves 被且仅被分入 inclusion/exclusion；零 unknown leaf。
2. 两次独立 replay 的 vector/model/prediction/statistic hashes 完全一致，零 warning、零 non-finite。
3. C01–C05、D0/D1 primary、class-wise CI、9,999 block permutation 与 host-only Holm 全部实际触发。
4. 记录总 wall time、峰值 RSS、缓存体积和最慢 slot；资源超限只能优化 provider/批处理，不能自动删叶、减模型或改变统计定义。
5. 对一个人为注入的“只存在于深层叶”“只存在于 conjunction”“只存在于三阶交互”“只存在于 k=11 局部群”和“只存在于 block/host 关联”的确定性 fixture，分别证明对应攻击确实被触发；这些是执行连通性测试，不是候选 verdict。

如果 rehearsal 证明 Armijo 或向量化 provider 的实际成本明显高于这里的下界，应先做等价实现优化和 profiler 定位；只有新的、被单独冻结且写明假绿后果的研究决定，才可以改变攻击语义。
