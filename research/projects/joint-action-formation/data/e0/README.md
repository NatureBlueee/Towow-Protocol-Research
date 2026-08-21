# NAC E-H1′ E0 数据夹具

状态：`NON_EVALUATIVE_FIXTURE`

这个目录把档案中的 R7 虚构四方只读试点封装成一个**只验证数据边界**的最小夹具。它用于
检查：

- 来源能否回到固定 SHA-256；
- SEEK 与 OFFER 的角色能否在不复制 private intake/mandate 正文的前提下声明；
- 后续数据工具能否拒绝没有候选池、gold labels 和模型 receipts 的输入；
- E0 工具通过能否继续与 E-H1′ 机制结论保持隔离。

它不是 `NACH1EmbeddingManifest`，也不应通过
`research/contracts/nac-h1-embedding-manifest.schema.json`。这里故意没有：

- 可供 embedding 的文本；
- `query → positive_candidate_ids`；
- 大于 100 的候选池；
- train/dev/test split；
- anchors、correspondences 或 unpaired training corpora；
- 五模型 receipt；
- NAC、vec2vec、Procrustes 或共享参考编码器输出。

因此本目录不得计算或发布 Recall、Recall@100、80% 门、模型排名、机制支持/反驳或生命周期
优胜结论。

## 文件

- `dataset.json`：夹具身份、观察事实、允许用途与硬禁止；
- `field-mapping.json`：SEEK/OFFER 的来源角色和安全物化规则；
- `records.jsonl`：两个不含正文、不可 embedding 的方向性记录壳；
- `source-hashes.json`：案例与四方 intake/mandate 的原始成员定位和内容哈希；
- `CHECKSUMS.sha256`：本目录文件校验和。

若未来需要物化文本，必须新建更高版本数据包，经来源/披露审查后只提取允许公开的字段，
冻结新的内容哈希；不能原地把本夹具变成评价集。
