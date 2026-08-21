# 研究线 01-NAC：E-H1′ 跨模型坐标基底

Contract：`LINE-01-NAC / v1`

状态：`ACTIVE`。由用户决定 `DEC-2026-07-28-ACTIVATE-NAC-H1-LINE` 激活。它是“发现与
边界”母线下独立推进的机制线，不是第八个全局问题；激活只授权研究
`E-H1′ → MC-NAC-ANCHOR`，不自动带起 H2–H8。

2026-07-28 的激活前研究已完成第一轮现成方案核验。当前 disposition 从 `UNRESOLVED`
收敛为 `EXTEND`：Relative Representations 已覆盖锚点相似度跨空间坐标的技术内核，
vec2vec 提供无 paired data 的可学习翻译强基线，2025 年 Procrustes 提供
correspondence 对齐基线，共享参考编码器则是必须公平比较的强中心方案。故本线不再把
“相对坐标原理存在”当作 NAC 的独立新证据，而只检验它在通爻目标分布、最坏模型对、
跨语言切片及多模型生命周期成本上是否仍有可归因价值。

详细核验与激活缺口见：

- `research/projects/joint-action-formation/prior-art/nac-h1-existing-solutions-2026-07-28.md`
- `research/projects/joint-action-formation/studies/nac-h1-activation-readiness-2026-07-28.md`
- `research/projects/joint-action-formation/studies/nac-h1-fairness-correction-2026-07-28.md`

本线只研究 `MEC-NAC / v1` 的 `E-H1-PRIME → MC-NAC-ANCHOR`：公共锚点坐标这一
identity core 是否具有跨模型判别力。它将读取原始问题、IF-2、总体设计、专利材料、M1
与预注册实验，不再只依据压缩后的 Line 01 摘要。

本线的核心判别不是“NAC 这个名字是否保留”，而是：

- 完成锚点数、选择策略、前缀长度与聚合函数扫描后，跨厂商 top-100 召回能否达到同厂商
  80%；
- 在允许各方案使用原生信息条件、统一核算总资源后，是否显著低于 vec2vec 对照；
- 自然语言加稳定 Schema 这一 V2 新增臂是否无损覆盖坐标问题，但不改写原门槛；
- 失败是否要求当前坐标基底进入 `REFUTED_SCOPED` 或 `REBASE_REQUIRED` 候选。

其中 `E-H1′` 采用历史原门槛：完成原定扫描后，跨厂商 top-100 召回达到同厂商 80%；
到饱和仍未达到，或在原生信息条件与完整资源账下显著低于 vec2vec，则坐标基底选型作废。
自然语言加稳定 Schema 是 V2 新增比较臂。H2 与 Direction、Self-description、Migration
将分别建立后续有界线；
H3、H5–H8 属于 M3/M5 等配套机制，不能被计作本线或 NAC 单体已经完成的验证。

NAC 不负责上游 Intent 推断、授权、PFE、能力形成、Effect、Adoption 或 Acceptance。它没
解决这些问题，不是本线的反向结果。本线同样不能从网络发现成功推出完整关系已经形成。

本线已经正式启动，但 E-H1′ 尚未开跑：当前没有冻结的 gold labels、>100 候选池或五模型
embedding receipts。首批三条并行工作流已经返回：预计算 embedding manifest/evaluator、
数据与标签审计、公开强基线与反例复核。它们已建立 E0 工具与拒绝门，但工具测试、合成夹具
和论文作者报告都不是机制结果。
