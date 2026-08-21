# Wave 025 independent evaluator

状态：`RUNNABLE FAIL-CLOSED PROFILE / FORMAL ADMISSION BLOCKED BY SHARED-INTERFACE AMBIGUITY`

## 它做什么

`evaluator.py` 只接受一个已经 `REVEALED` 的 batch 目录。它不会 import runner 或 collector，
不会启动、补跑、修复、删除或重编号 slot，也不会输出 A1–A5 的 score、coverage、Pareto、ranking
或 winner。

它从原始证据重新完成：

- canonical JSON、重复 key、schema、字段白名单和完整人口检查；
- shared contracts、collector source、Dockerfile、evaluator source 的 SHA-256；
- 三个 seed/nonce domain 的 commitment、分域性、opaque IDs、block-balanced mapping、execution
  order、padding 以及 `runner-private-state.json` 与 reveal 的逐项一致性；
- 每个 slot 的 raw Docker inspect pre/post、host-launch 派生值、image ID、可空 final RepoDigest 的
  替代绑定、D1/T isolation profile 和跨 slot stable config；
- raw stdout、stderr、stopped-container out 与 frozen feature bytes 的逐字比较；
- slot receipt、closed population 和 Merkle root；
- D0 predecessor/shared-state contamination 与 D1 current-run canary 的逐 family 正控门；
- T calibration/fresh holdout 的 deterministic categorical scan、L2 logistic、depth-2 tree、5-NN、
  label permutation、Holm 校正和 one-sided exact confidence bound；
- host-only order/ID/container/time/path association 的单独审计；这些字段永不进入 candidate
  feature matrix；
- external anchor 的真实 Git blob readback。评估器调用 `git cat-file` 读取 object type 和 bytes，
  不把 `anchor-receipt.json` 的自报当作锚定证据。

输出逐项保留五个冻结 claim；`CL-025-FULL-BLIND-COMPARISON-QUALIFICATION` 永远是
`NOT_TESTED`。

## 运行

依赖只有：

- Python 3.9 或更高版本的标准库；
- formal dual anchor 校验需要本机 `git` CLI；
- 不需要 numpy、scipy、scikit-learn，也不会安装或下载依赖。

```bash
cd /Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/independent-evaluator
python3 evaluator.py /absolute/path/to/revealed-batch
```

评估器以 `O_EXCL` 创建 `<batch>/evaluation.json`。文件已存在时退出并拒绝覆盖。证据被拒绝时
仍可写一份 `NOT_QUALIFIED` 结果，但不会改变任何 runner-owned 文件。

运行测试：

```bash
PYTHONPYCACHEPREFIX=/private/tmp/wave025-evaluator-pycache \
  python3 -m unittest discover -s tests -v
```

## 冻结统计规则

formal suite 的唯一默认人口是：

| Challenge | calibration | fresh holdout |
|---|---:|---:|
| D0 | 100 | 100 |
| D1 | 100 | 100 |
| T | 400 | 800 |

总计 1600 slots，每个 split 内 S/R 严格平衡，每 block 20，S/R 各 10。

纯 Python feature encoding 使用：96 个按 coverage、unique count 和通道优先级确定的 numeric path，
每个 path 同时带 missing bit；其余 categorical leaf 进入固定 128 维 signed SHA-256 hashing；全部
参数只由 calibration 拟合，然后 row-L2 normalization。四种 classifier 的参数与 tie-breaking 在
`SUPPORTED_CLASSIFIER_PLAN` 中固定。

balanced class 下，balanced accuracy 等于总正确率，因此用总正确数给出
`CLOPPER_PEARSON_BALANCED_TOTAL_ONE_SIDED_V1` 的 95% 单侧精确界：

- D0/D1 每个预登记 family 的 holdout 下界必须 `>= 0.90`；
- T 每个 classifier 的 holdout 上界必须 `<= 0.55`；
- T deterministic rule 若在 holdout 达到 `1.0`，直接形成
  `BLIND_QUALIFICATION_FAILED`；
- `p > 0.05` 不作为等价证据；permutation p-value 只作为攻击诊断，等价门仍由预登记上界决定。

800 个平衡 T holdout 在恰好 50% 正确时，当前实现重算的单侧上界约为 `0.52967`；400 个时约为
`0.54227`。这只是给定冻结阈值和样本量下的统计行为，不是未知侧信道不存在的证明。

## 本地可执行 profile 与共享合同的区别

当前 shared contract 要求所有对象拥有“精确 schema”，但仍用“至少包含”描述多项对象，且没有
给出所有嵌套 preimage。为了让解析器、统计器和拒绝路径现在即可运行，本目录定义了显式版本化
的本地 profile：

- `HMAC_SHA256_BALANCED_FISHER_YATES_V1`；
- `HMAC_SHA256_OPAQUE_SLOT_V1`；
- `HMAC_SHA256_UINT32_PADDING_V1`；
- `SHA256_SORTED_LEAVES_DUPLICATE_ODD_V1`；
- `WAVE025_FEATURE_SPEC_V1`；
- `WAVE025_CLASSIFIER_PLAN_V1`；
- `DUAL_CODEX_COMMENTARY_AND_GIT_BLOB` anchor shape。

这些名称和编码不是被悄悄宣布为 shared truth。`evaluation.json.contract_ambiguities` 会原样报告
尚未冻结的接口差异；只要 blocking ambiguity 仍在，formal batch 即使完全符合本地 profile，
最高仍是 `NOT_QUALIFIED`，不会得到 `PREFIX_QUALIFIED_SCOPED`。另一方面，若原始 T features
已经显示稳定泄漏，评估器仍可给出 `BLIND_QUALIFICATION_FAILED`，因为这类负证据不需要把本地
profile 冒充正式标准。

当前仍需在 shared contract 中精确冻结：

1. anchor、public plan、private state、host launch、slot receipt、closed 与 reveal 的所有顶层和
   嵌套字段；
2. seed/nonce 编码、HMAC stream、Fisher–Yates、partition/block/order、opaque ID 与 padding 的
   逐字算法；
3. Merkle internal-node domain separation、奇数叶和空树规则；
4. `feature_spec_sha256` 所对应 bytes 在 batch 中的正式位置；
5. D0/D1 family registry、path allowlist、private token commitment/reveal 的精确形状；
6. host monotonic nanoseconds 的字段和绑定位置；
7. raw Docker inspect 必须保存 daemon 原字节，还是必须 canonical reserialize 的冲突。

## 结果边界

即使将来所有 blocking ambiguity 被正式消除且 prefix suite 通过，本评估器也只支持：在冻结
collector、登记 probe、当前 OCI/host profile 和 `T0 SEALED → T1 PUBLIC-PREIMAGE` observation cut
内，没有观察到超过阈值的 role recovery。

它不证明动态 broker、earliest lawful divergence、provider/human memory、evaluator truth、现实
Authority、Effect、Acceptance、成本公平、生产可靠性或完整 V1/V2；实际 A1–A5 comparative
runs 仍为 0。
