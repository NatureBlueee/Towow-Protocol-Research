# External independent task — Wave 025 model input

Task ID: `W025-MODEL-INPUT-PRO-B`  
Packet version: `2026-08-01-minimal-v1`

## Question

对于一个盲泄漏资格实验，怎样用成熟统计、哈希与稀疏矩阵技术，唯一、可移植地把三类已冻结
predictor rows 编译为 C01–C05 的模型输入，同时避免标签泄漏、holdout 扩列、哈希抵消假阴性和
跨实现浮点分叉？

请独立比较：

- A. 完全由静态 route/schema 派生的列宇宙；
- B. 在不读取标签前，仅由 calibration membership 冻结的数据依赖列宇宙；
- 也可以提出更简单或混合的现有方案。

不要预设某个本地设计正确，也不要追求专有贡献。

## Why it matters

如果列宇宙、missing、presence、row/column order 或 binary64 bytes 不唯一，后续两个独立
provider、2400-row fresh holdout 和 C01–C05 比较都可能形成假绿或不可复现。

## 冻结输入

1. 每个样本的 predictor 只有：
   - numeric: `(family, typed CTX2, channel, stat, exact rational numerator/denominator)`
   - categorical: `(family, typed CTX2, channel, expected_channel, typed value SHA256, positive count)`
   - ngram_counts: `(family, bucket 0..4095, positive count)`
   - 审计 sidecar、receipt path、来源、hash/provenance/debug 严禁进入 classifier。
2. family 有且仅有 `F01_PUBLIC_INPUT_BYTES`、`F02_ARGV_ENV_CWD`、
   `F03_HOSTNAME_IDENTITY`、`F04_DIRECTORY_AND_SHARED_STATE`、
   `F05_PROCESS_NAMESPACE_FD`、`F06_TIMING_AND_ERRORS`、`F07_VISIBLE_CANARY`。
3. calibration 与 fresh holdout 分离；任何数据依赖 identity/universe 必须在读 label 前冻结。
   holdout-only numeric identity 必须 fail 为 schema drift，不能静默丢弃或扩列。
4. C01 exact rule scan：单 exact categorical presence、单 categorical context total mapping（含
   missing）、单 numeric exact value（含 missing）、TOP256 calibration-support token 的二项
   conjunction；support 至少总10、每预测类5；按 calibration balanced accuracy、较低复杂度、
   UTF8规则序列化择优，holdout不重选。
5. C02 L2 logistic：robust-scaled numeric + signed hashed categories，family 内 L2 normalize，并
   保留 `log1p(pre-normalization family norm)`；全批梯度下降/Armijo。
6. C03 stump 与 C04 depth-3 tree：median-filled unclipped numeric + missing indicator +
   categorical/ngram bucket presence；presence必须是“任一 row 命中 bucket”的 OR，不能用 signed
   sum 是否非零。
7. C05 kNN-11：robust-scaled clipped[-8,8] numeric + signed hashed categories，family 内 L2
   normalize并保留 family norm；欧氏距离。
8. categorical signed hash 目标16384 buckets；ngram是每 family固定4096 direct columns。
   count transform需确定地实现 `log1p(min(count,255))`。numeric/missing、signed category、
   route-aware direct ngram、family norm 的列顺序必须唯一。
9. matrix row order、column order、rational→binary64、+0、endianness、bytes/hash preimage必须冻结。
   现有 provider限制为CPython/NumPy float64/single-thread/einsum optimize=false，但你可指出更简单、
   跨语言更稳的成熟方案。
10. 实验总3200 rows：D0 200、D1 200、T 2800（400 calibration + 2400 holdout），按
    challenge/phase/block 内角色严格平衡。

## 当前已知

- typed value、exact rational、missing atom、predictor/audit物理分离已有独立字节复核。
- 旧实现曾因 ordered argv 交换仍给同向特征而假绿，说明不能把旧 engine 当答案。
- 结构 routing 与 collector admission仍在独立修复，因此请把 route→identity binding当外部依赖，
  不假定已完成。
- 目前没有 G、3200-run、模型效果或成本结论。

## Required result

构造一份竞争性模型输入方案，而非同意既有方向。优先复用成熟方法；如果更简单的强中心、单一
provider或现有库在相同 blindness、holdout、可复现和成本条件下完整解决，也算成功。

## Success means

- 明确判定 static、calibration-derived 或 hybrid 哪个在什么条件下更好；
- 给出逐分类器的 exact eligible channels、列 identity/order、missing/presence/hash语义；
- 给出至少5个最小反例，分别证明删除某机制会产生漏检、假绿或实现分叉；
- 指出哪些设计只是形式复杂度、应删除；
- 给出两个不共享实现的 provider 所需 public goldens、hidden holdbacks、failure codes和验收顺序；
- 说明资源上界、维护/停更/格式锁定/迁移风险；
- 不报告未执行的测试或测量。

## Hard boundaries

- Do not assume access to local files, tools, tests, or unlisted history.
- Do not invent measurements, citations, or external acceptance.
- Existing, central, general-model, human, adapter, or combined solutions count as success.
- Do not optimize for Towow uniqueness.

## Return

1. Problem reconstruction.
2. Best design and strongest alternatives.
3. Exact machine-contract decisions still required.
4. Counterexamples and removable mechanisms.
5. The single next local experiment that best distinguishes alternatives.
6. Missing material only if it would materially change the answer.
