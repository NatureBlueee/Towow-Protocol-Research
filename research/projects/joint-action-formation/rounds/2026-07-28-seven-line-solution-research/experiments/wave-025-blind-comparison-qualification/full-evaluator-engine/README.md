# Wave025 full-leaf evaluator engine

状态：`RUNNABLE PREFORMAL ENGINE / F V1.3 READ-ONLY ADAPTER / NO QUALIFICATION VERDICT`

## 它解决什么

本目录从同级已选定的 `EXECUTABLE-ATTACK-PROFILE.json` 和其逐字节绑定的
`feature-spec/FEATURE-SPEC.json` 独立实现候选可见 receipt 的完整叶攻击引擎。它不读取或依赖
runner 提供的 feature vector，也没有复用现有 evaluator 实现。

引擎当前包含：

- 严格 raw receipt schema 与 scalar-leaf partition；每个叶只能进入 F01–F07 或冻结的 excluded
  集合，unknown leaf fail closed；
- 全量路径和 16,384 categorical hashing buckets、每族 4,096 n-gram buckets；没有 96/128
  visible-leaf 或 numeric-path cap，也不做 bucket reduction；
- C01 exact categorical/numeric scan 与 calibration-support TOP256 二 token conjunction；
- C02 `lambda=0.01`、float64、full-batch gradient descent、step 1、backtrack 0.5、Armijo
  `c=0.0001`、最多 2,000 次、gradient L-infinity `1e-10`；
- C03 depth-1 stump、C04 depth-3 tree，二者 `minimum_leaf=10`；
- C05 Euclidean kNN `k=11`，包括所有第 11 位边界同距邻居、unweighted vote、class0 tie；
- class-wise one-sided Clopper–Pearson、balanced-accuracy bounds；
- 9,999 次 fresh-holdout frozen-prediction block permutation，不重训、不重选；
- predictive Holm 与只作用于 `T-OCI-ISOLATED` fresh holdout 的独立
  `T_HOST_ONLY_ROLE_ORDER_ASSOCIATIONS` Holm family；D0/D1 host values 不进入该 family；
- exact NumPy/Python/provider binding、nonfinite/warning/nonconvergence abnormal，以及两次独立运行的
  十类 SHA-256 replay manifest，任何 byte/prediction/statistic 差异 fail closed。

`MODEL-SELECTION-RANDOMIZATION` 明确保留为 `NOT_TESTED`。短路 permutation 只能校准已经冻结的
holdout prediction；它没有证明 calibration-stage model selection/fitting 的无条件随机化有效性。

## 输入边界

CLI 接收一个 JSON array。每一项只是 evaluator-side envelope：

```json
{
  "receipt": {"schema": "WAVE025_LEAK_ONLY_FEATURES_V1"},
  "challenge": "T-OCI-ISOLATED",
  "phase": "calibration",
  "block": "c000",
  "opaque_slot_id": "opaque-id",
  "role": "revealed-role"
}
```

真实 `receipt` 必须包含 collector 的完整严格输出。`private_family` 与 `host_only` 是可选的 evaluator
metadata；它们不会传入 raw feature provider。执行顺序是：逐 receipt 校验和提取 → 冻结 numeric、
categorical 与 excluded-leaf audit hashes → 才 join challenge/phase/block/role/private family。

`batch_adapter.py` 是与引擎分离的只读边界：它不 import runner、旧 evaluator 或 collector，也不读取
或覆盖 evaluator-owned `evaluation.json`。它按 `BATCH-EVIDENCE-CONTRACT.md`、shared evidence
profile/schema 和 F 原始 bytes fail closed 地重算：

- 六个 runner-owned 根对象的 canonical bytes、closed schema、top-level hash links 与外部 anchor；
- 三个 domain commitments，以及 population、opaque IDs、role/padding/token mapping、execution order；
- 12 个 slot 的完整文件清单与 raw hashes、V1 Merkle、collector 三通道逐字节相等；
- 每槽 post-cut 五个 host exec / 19 个 daemon event 的 exact projection、exec IDs、TERM 与时序；
- raw inspect 对 host launch 的身份、argv/env/cwd、隔离、资源限制、mount 和必要 diagnostics 投影；
- `holdout -> fresh_holdout` 的 engine records，以及单独哈希冻结的 host-only rows。

适配结果只声明“这些 bytes 通过当前输入边界校验”，不产生 qualification verdict 或 treatment
ranking。V1.3 的 FEATURE-SPEC 仍是 batch 外的 hash-bound bytes；未来 V1.4 若嵌入 self-contained
profile/spec bytes，本 adapter 会明确 `UnsupportedBatchVersion`，不能把新接口静默解释成旧接口。

引擎本身仍可直接消费已构造的 records，调用形状：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave025-full-engine-pyc \
python3 full-evaluator-engine/engine.py records.json \
  --precommit-sha256 <64-lowercase-hex>
```

输出只包含 attack execution、CI、permutation、Holm、异常与 replay evidence；字段明确声明
`qualification_verdict_produced=false`、`treatment_score_or_ranking_produced=false` 和
`formal_use_claimed=false`。

## 两个必须显式锚定的局部解析

冻结 spec 规定了算法类别和 hash domains，但没有逐字节规定以下两点。本实现必须选定一种可运行
解析，同时禁止把它悄悄描述成唯一语义：

1. signed categorical hashing：使用
   `SHA256("WAVE025_CATEGORICAL_MODEL_HASH_V1" || 0x00 || token_utf8)`；完整 digest 取模
   16,384 得 bucket，digest 第一个 byte 的最低位给 sign；
2. permutation seed：`PRECOMMIT_SHA256` 与 `FEATURE_SPEC_SHA256` 作为各自 64 个 lowercase ASCII
   hex bytes 参与拼接，不先解码成 32 raw digest bytes。fixture 同时计算两种约定并证明它们不同，
   engine output 也报告 `LOWERCASE_ASCII_HEX...` resolution。

numeric median/IQR 使用 sorted linear-interpolation quantiles。以上解析在 formal external anchor 前
必须被明确采纳或替换；替换会改变 source manifest、feature/model/permutation hashes，不能作为兼容
小改动静默发生。

## 定向验证

```bash
PYTHONPYCACHEPREFIX=/tmp/wave025-full-engine-pyc \
python3 -m unittest discover -s full-evaluator-engine/tests -v
```

fixtures 不是只查函数名，而是分别构造并验证：

- 220 个 directory records 和深层 process leaf，证明完整叶审计超过 128 且 F01–F07 全部出现；
- 单 token 最多 0.75、只有 TOP256 pair conjunction 能达到 1.0 的 C01 分布；
- stump 不能完整恢复、depth-3 才能恢复的三阶 interaction；
- k=5 会投 class0、k=11 加边界同距后投 class1 的局部邻域；
- 每个 coordinate 单独恰为 chance、32 个 coordinate 联合达到 0.95 且严格 Armijo 收敛的
  diffuse logistic；
- unknown nested leaf、NaN、optimizer nonconvergence、provider mismatch 与 replay hash mismatch
  均 fail closed 或标为 abnormal，绝不解释为 chance；
- 9,999 frozen-prediction permutations、class-wise CP、predictive/host-only Holm；
- D0/D1 host-only 值即使被极端修改也不能改变 T-only host family；
- 两次完整 engine orchestration 返回十类相同 hashes，同时仍无 verdict、无 treatment ranking。

另外，adapter tests 逐字节使用 F 作为 exact fixture，锁定 12 槽、V1 Merkle 与只读边界；并分别
注入 raw channel 篡改、runner-owned unknown field、额外 daemon event 和错误 reveal mapping，四种
反例均 fail closed。测试还拦截对 `evaluation.json` 的读取，并在运行前后比较其 hash/mtime 与 F
目录清单。

这些是实现与本地 synthetic fixture 证据，不是 3,200-slot preformal rehearsal、external anchor、
qualification 或现实 treatment comparison 证据。
