# Study — NAC E-H1′ 数据与标签可运行性审计

日期：2026-07-28

状态：`DATA AUDIT STARTED / SCIENTIFIC RUN NOT STARTED`

作用域：只检查当前档案与派生视图中，是否已经存在可供
`E-H1-PRIME → MC-NAC-ANCHOR` 使用的有向 `SEEK Intent → OFFER 画像` 数据、独立标签、
候选池、合成生成器、模型 embedding receipt 或可恢复原始结果。本文件不激活研究线，不运行
模型，也不改变 NAC 其他 scoped claims。

## 结论

当前仓库里有三类可复用材料，但**没有一类已经构成可判读的 E-H1′ 数据集**：

1. 一个明确标为虚构、`research_only=true` 的四方企业 AI 只读试点样例，可用于字段映射和
   schema smoke test；
2. 七个公共档案案例、58 个回溯编码事件，可用于标注规范演练、困难关系族发现和泄漏测试；
3. 第二轮合成机制实验的数值型约束世界，可用于 evaluator CI、负例构造和结构压力测试。

没有发现：

- 冻结的 `query → relevant_offer_ids` gold；
- 大于 100 且逐 query 固定的候选池；
- 独立于受测 embedding 模型的 E-H1′ 标注过程；
- 五个模型/版本的预计算 embedding receipt；
- NAC、vec2vec、Procrustes 和共享参考编码器的同输入输出；
- 可恢复的 E-H1′ 历史运行。

所以可以立即启动**数据契约、schema 映射和非评价性 smoke fixture**，但不能把这一步或下面
10–20 份材料编码后的分数称为可解释的 `Recall@100`。

## 1. 本次核查覆盖了什么

### 1.1 正典实验要求

历史 B7 规格只冻结了：

- 数据类型为有向意图→画像标注集，允许语料加合成扩充；
- `5+` 异构嵌入模型、跨骨干难对和跨语言组；
- `K × 锚点选择 × 前缀 × max/mean × vec2vec`；
- 跨厂商 top-100 Recall 达到同厂商 80% 的门槛。

它没有给出数据文件或标签 manifest。原文位于
`research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files/2b/2b8e039b222ef710247f5db108ba7611ebe77351ae4d7c774af7c2f14fb032ce.md:21-25`，
内容 SHA-256 为
`2b8e039b222ef710247f5db108ba7611ebe77351ae4d7c774af7c2f14fb032ce`；原始 ZIP 成员由
`research/projects/a2a-reconstruction/01_catalog/zip_members.csv:1116` 定位。

同一规格还明确说 E-H1′ 可先做合成扩充，真语料随后补入，并要求原始数据不可变留存
（上述派生文件第 55 行）。这说明“合成先跑”是允许的实验阶段，不说明当前档案已经包含该
合成数据或生成器。

### 1.2 档案与派生视图扫描

本次读取了当前唯一源包的完整物理文件目录与 ZIP 成员目录：

- `research/projects/a2a-reconstruction/01_catalog/physical_files.csv`
  （159 条，SHA-256
  `91977b869475c3eaace558e02797d23f9aa1f99182e96ba77d0a0389571a9656`）；
- `research/projects/a2a-reconstruction/01_catalog/zip_members.csv`
  （2771 条，SHA-256
  `404654afd58dfc9705212f74ad725d586cd913683f2d8e166ba5f47f19cff89c`）。

两个目录中均没有 `npy/npz/parquet/arrow/pkl/pt/safetensors/h5/sqlite/faiss` 等向量或模型结果
扩展名，也没有路径名命中 `embedding_receipt`、`model_receipt`、`candidate_pool`、
`query_id`、`profile_id`、`positive_ids`、`relevant_ids` 或 `dataset_manifest`。这不是证明
任何未编目外部位置不存在；它证明当前正典档案与其可逆派生视图没有给出可恢复的 E-H1′
embedding 包。

档案中的 `MANIFEST.json/csv` 是归档清单，不是实验数据 manifest，不能据此推断 query、
candidate、标签、split 或模型 receipt 已冻结。

## 2. 可复用候选及其正确身份

| 候选材料 | 直接观察 | 可用于 | 不能用于 |
|---|---|---|---|
| R7 四方只读试点样例 | 1 个虚构案例；四个参与者，各有 intake 与 mandate；案例正文显式写有“虚构示例”、`research_only=true` | 将 `hard_constraints`、`acceptable_outcomes`、`resources_actually_available`、`shareable_projections` 映射为 SEEK/OFFER 字段；schema smoke test；难负例规则演练 | 真实语料结论、跨语言结论、Recall@100、模型间差异 |
| R7P 公共档案扩展 | 7 个案例、58 个事件；单一编码者；理论抽样而非总体样本 | 发现关系族、Authority/约束/结果字段；建立标注手册；做案例级 holdout 和专名泄漏测试 | 直接生成有向检索 gold；把事后成功当作事前 relevance；统计现实发生率 |
| Round2 Team Constitution | 300 个生成实例、4 个方法，共 1200 行数值结果 | evaluator CI；构造“公开画像不足、私有贡献模式决定可行性”的合成反例 | 自然语言语义检索、跨模型 embedding 比较、现实画像分布 |
| Round2 Boundary Oracle | 300 个生成实例、9 个方法，共 2700 行数值结果 | split/seed/负对照和隐藏约束压力测试的设计先例 | E-H1′ query/candidate 集或现实标签 |
| R6 机制实验报告 | 报告描述了模拟器、ground truth 与原始结果文件名 | 合成实验边界和 manifest 字段参考 | 可恢复数据：当前物理目录与 ZIP 成员目录没有报告所列 `R6-*.csv.gz`、`run_manifest.json` 或 `towow_r6/` |

### 2.1 R7 样例的证据边界

案例文件的内容 SHA-256 是
`e52d36bd39a663da1553ebe6a84ed08d483a00901d99c15f8bed393ac2ee0419`，可读副本位于
`research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files/e5/e52d36bd39a663da1553ebe6a84ed08d483a00901d99c15f8bed393ac2ee0419.json:1`，
原始成员及四组 intake/mandate 的逐文件哈希见
`research/projects/a2a-reconstruction/01_catalog/zip_members.csv:24-32`。

这套材料最有价值的不是样本量，而是它已经把公开投影、硬约束、私有不可共享事实、资源、
未知和授权范围分开。它可作为新数据 schema 的种子，但案例的四个角色属于同一个预先写好的
成功路径，没有足够无关候选、困难负例或独立 relevance 判断。

### 2.2 公共档案的证据边界

公共扩展结果明确记录 `unique_cases=7`、`events=58`、`single_coder=true`、
`theoretical_sampling_not_population_sample=true`，见
`research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files/d2/d2d98089c93c80416adcaf3f89ec3c7fe647b6044cb8668f8ed60f96f1243402.json:2-10`；
其正文、事件和案例画像的源成员及 SHA-256 见
`research/projects/a2a-reconstruction/01_catalog/zip_members.csv:136-138`。

该结果自己的解释边界也写明：七案例仍是单编码者、回溯官方记录有筛选、可能省略非正式
权力与失败替代项，只能校准构念和工具，不能证明 live Agent 委托或相对强中介的因果净值
（上述结果文件第 440–449 行）。

因此这 7 案例/58 事件可以派生一个**非评价性 annotation pilot**，例如让编码者从某个事前
时间点写 SEEK、从当时可知材料写 OFFER，并标记 `RELEVANT / NOT_RELEVANT / UNKNOWN`；
但在没有新的盲化标注、案例级留出和足够候选池前，不进入 headline metric。

### 2.3 旧合成实验的证据边界

Team Constitution 的 1200 行来自 300 个生成实例重复比较 4 个方法，内容 SHA-256 为
`1d28f66efd996f0acd13a1b1818078a8ca5f9bc114d2df194e43effe9657dfbf`；
Boundary Oracle 的 2700 行来自 300 个生成实例重复比较 9 个方法，内容 SHA-256 为
`ba166a6a3ffd43eb1257975d7875d31ff6924bae0db725cb97481825def9e5ac`。原始成员、大小和哈希
分别见 `research/projects/a2a-reconstruction/01_catalog/zip_members.csv:1048` 与
`research/projects/a2a-reconstruction/01_catalog/zip_members.csv:1052`。

实验账本将它们明确标成 `synthetic_mechanism`、`synthetic capability modes` 或
`synthetic oracle domains`，见
`research/projects/a2a-reconstruction/02_derived/zip-text-search-corpus/files/57/5757b6c827ff84fc4a27832307e29dcc661946a99d21d40d29cfa60fa4e22110.json:26-68`。
它们的标签由生成器定义，可验证 evaluator 是否正确处理 seed、split、负例和隐藏约束，
不能验证自然语言画像的跨模型召回。

R6 报告本身也限定：合成结果只支持在明确生成模型与 ground truth 下比较机制，不支持把
模拟参数当现实频率或商业回报；见
`Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_A2A_Independent_Research_v0.3/experiments/R6_机制判别实验报告_v0.2.md:443-459`。

## 3. 标签必须区分什么

E-H1′ 的 gold 不能只写“发生过合作”。建议冻结三层、保留 Unknown：

1. **Eligibility**：OFFER 是否满足 SEEK 已公开的必要条件；
2. **Potential relevance**：在只看冻结前态的情况下，是否值得进入 top-100 深判；
3. **Observed outcome**：之后是否接洽、执行、成功或失败。

主 Recall 的正例应由预先选定的 `eligibility` 或 `potential relevance` 规则产生；outcome
只作独立结果字段。否则会把“没被发现所以没发生”、权威否决、资源不足和执行失败全部误标成
语义不相关。

每条 pair 至少需要：

- `query_id`、`offer_id`、不可变文本哈希和来源时间；
- 明确 `SEEK → OFFER` 方向；
- `label ∈ {RELEVANT, NOT_RELEVANT, UNKNOWN}`；
- `label_basis` 与必要条件/反例；
- 编码者、盲化状态、分歧和裁决记录；
- `relation_family`、语言、陌生/长尾、复杂合取切片；
- `observed_outcome` 另列，不进入默认 relevance gold。

## 4. 当前最危险的泄漏

1. **事后泄漏**：公共档案含签约、终止、Outcome 和完整时间线；用最终结果写 query/profile
   会让模型从结果词猜标签。必须按 cutoff time 重建冻结前态。
2. **案例/主体泄漏**：同一公司、事件或关系族若横跨 train/test，名称和模板会替代语义
   泛化。split 必须按案例/主体/关系族成组。
3. **档案重复泄漏**：同一 SHA 内容在 v0.6、v0.7、Public Evidence Pack 中重复出现；
   必须按内容 SHA 去重，不能把 ZIP 路径当独立样本。
4. **模板泄漏**：R7 样例和合成扩充若共享固定槽位或措辞，模型可从模板猜正例。模板族必须
   整体 holdout。
5. **模型参与 gold**：不得用任何受测 embedding 模型生成、筛选或裁定自身测试正例；LLM
   辅助只能提出候选，最终来源与人类裁决需独立记录。
6. **锚点/test 泄漏**：锚点选择、Procrustes/vec2vec 对应样本和所有 learned baseline
   不得读取 test label 或 test relation family。
7. **跨语言镜像泄漏**：同一语义的翻译版本不能一份进 train、一份进 test；同时必须单列
   翻译等价和真正跨语言长尾。
8. **方向性归因泄漏**：SEEK/OFFER token 若只给 NAC 或标签由方向 token 直接决定，会把
   `MC-NAC-DIRECTION` 效果算给 anchor。所有比较臂取得相同方向字段，anchor 主结果另做
   direction-fixed 报告。
9. **不完整 gold**：只标已知命中而未审查候选池，会把未标正例算假阳性、夸大或压低
   Recall。每个 query 的相关集合必须定义其审查边界。

## 5. 最小可运行条件

### 5.1 公平不等于强制 same-K

各比较臂必须在相同冻结的 test query、candidate pool 和 gold 上评价，但允许使用各自原生的
非测试信息条件：

| 方法 | 允许的原生信息条件 | 必须单独计入资源账 |
|---|---|---|
| NAC / relative coordinates | 有正典顺序的 parallel anchor 文本；各模型分别编码同一锚点 | anchor 获得/治理、每模型编码、坐标存储、版本双写与重投影 |
| vec2vec | 两个空间各自的大规模 unpaired corpus embeddings；不要求 paired/shared semantic samples | 两侧语料、全部 encoder 调用、训练、best-of-seeds、adapter/backbone、存储与版本重训 |
| Procrustes | 跨空间 correspondence pairs | 对应样本获取、闭式拟合、full-pair 或 hub 映射数、新版本重估 |
| 共享参考编码器 | 所有公开 query/candidate 另用同一 reference encoder 编码 | 共享模型依赖、全量重编码、在线/离线调用、迁移与治理成本 |

vec2vec 原论文条件和公平性校正见
`research/projects/joint-action-formation/prior-art/nac-h1-existing-solutions-2026-07-28.md:67-99`；
Procrustes 与 correspondence 条件见同文件第 103–125 行；该文件第 161–196 行已经明确否定
“所有臂相同共享样本数才公平”。

因此不得给 vec2vec 强塞 NAC 的 `K`，也不得让 NAC 免费取得 anchors、让共享 encoder
免费重编码。主比较应同时输出：

- **能力曲线**：同一 test gold 上的 Recall、最坏模型对和最坏切片；
- **总资源曲线**：各自原生数据、encoder 调用、训练、存储、组件数、onboarding、迁移、
  停机和治理依赖。

只有 evaluation truth source 相同；训练/对齐信息结构不必相同。

### 5.2 可以现在启动的 `E0 / NON_EVALUATIVE`

- 用 R7 虚构案例建立 SEEK/OFFER 字段映射；
- 从七个公共案例选少量 cutoff-time 片段，进行标签手册双人试标；
- 用旧合成世界验证 manifest 校验、group split、内容哈希去重、Unknown 和 evaluator 算法；
- 所有输出显式标记 `NON_EVALUATIVE_FIXTURE`，不计算或不发布机制胜负。

这一步的成功判据是数据契约能拒绝泄漏和缺字段，不是 NAC Recall 达标。

### 5.3 首个可解释的 `E1 / PILOT`

在模型运行前至少冻结：

- 候选池严格大于 100；每个 query 的 pool 大小和全部已知正例数固定；
- 至少一个真实臂与一个合成臂，绝不混合汇报；
- train/dev/test 按主体、案例和关系族成组切分；
- 至少一部分 test gold 经独立双人盲标与分歧裁决；
- 所有锚点、correspondence 和 unpaired training corpora 都与 test label 隔离；按各方法原生
  信息条件分别冻结，不强制 same-K；
- 五个模型的精确 provider、model ID、revision、维数、归一化、输入哈希、输出哈希和生成
  receipt；
- 所有有序模型对使用同一 query/candidate 文本、候选池和标签版本；
- 同模型分母、80% 的三个候选归一化值、关键切片、bootstrap/permutation 和实质差异在
  结果可见前冻结。

`>100` 只是让 `Recall@100` 不退化的机械下限，不是科学样本量。正式 query 数、正例数和
分层配额应在标签 pilot 后按观察到的方差、稀有切片覆盖和所需置信区间做功效/精度规划，
不应现在拍一个整数冒充充分性。

### 5.4 Manifest 的最小文件边界

建议首个输入包至少有：

```text
dataset.json                 # 数据版本、来源、许可、真实/合成身份、split 与去重策略
queries.jsonl                # SEEK 文本、方向、时间 cutoff、语言、关系族、内容哈希
offers.jsonl                 # OFFER 画像、可公开字段、时间 cutoff、语言、内容哈希
candidate_pools.jsonl        # 每 query 的冻结 offer IDs
labels.jsonl                 # 三态 pair label、basis、coder、adjudication、版本
anchors.jsonl                # 只由 train/dev 选择的公共锚点及顺序
models.json                  # 精确模型版本与编码规范
embeddings/<model>.receipt   # 输入集合哈希、输出哈希、shape/dtype、运行环境
budget.json                  # 各臂原生数据条件、算力、存储、传输、onboarding 与版本更新
```

任何数据正文、label、anchor、model receipt 或 budget 改动都产生新 dataset/run ID，不能
同步改写旧 manifest 后继续声称是同一运行。

## 6. 这一审计改变了什么行动

当前最合理的启动方式不是“从档案中随便抽十几份文本算 embedding”，而是并行两条：

1. **马上启动 E0 数据工具线**：把现有 R7/公共档案/旧合成材料各自封装成
   `schema-smoke / annotation-pilot / evaluator-CI`，保留非评价身份；
2. **马上启动 E1 数据形成线**：定义真实 SEEK/OFFER 采集与盲标协议，先形成候选池和标签
   pilot，再用观察到的正例密度决定正式规模。

现成材料缩短的是 schema、标注和校验工具的准备时间，不消除真实有向检索数据的缺口。
如果现在报告机制 Recall，数字主要反映样例选择、模板和事后信息，而不是公共锚点跨模型
判别力。
