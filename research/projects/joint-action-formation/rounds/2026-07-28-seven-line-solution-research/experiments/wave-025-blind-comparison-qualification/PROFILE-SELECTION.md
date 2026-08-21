# Wave 025 executable attack profile selection

日期：2026-08-01  
状态：`ROOT PREFORMAL SELECTION / FULL PROFILE ADOPTED / FORMAL USE STILL BLOCKED`

## 决定

Wave025 第一轮正式 evaluator 选择完整叶级 profile：

- 正典：`EXECUTABLE-ATTACK-PROFILE.json`
- SHA-256：`64a4e366a67ec2c12b1194d6fb01fab5b633529035a16f20b22acbf83346e5a7`
- schema SHA-256：`841c3517e5c9574cc91532c9f7d5e03091667574275dbe25ea9bbbfb5c9d1f8e`
- 继承的 feature semantics：`feature-spec/FEATURE-SPEC.json`
  (`8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a`)

它保留所有 candidate-visible leaf、F01–F07、C01–C05 原参数、class-wise exact CI、9,999 次
block-preserving frozen-holdout-prediction permutation、host-only Holm、D0/D1→C01 primary control、
float64 single-thread NumPy provider 与双 replay。formal 人口为 3,200：D0/D1 各 200，T
calibration=400、holdout=2,400。

这是研究方法的选择，不是运行结果。profile 内所有科学结果仍为 `NOT_TESTED`，11 个外部 binding
仍是 formal blocker；未运行的全模型重训置换继续独立标为 `MODEL-SELECTION-RANDOMIZATION =
NOT_TESTED`。

## 为什么没有采用压缩候选作为 formal profile

竞争候选 `feature-spec/EXECUTABLE-ATTACK-PROFILE.candidate.json`
(`2eba3bbbd2c99ebdf6ece4107ff535589e89066f3588063e9e9c3408c478b444`) 仍保留为 smoke/additional
attack 方案，不删除。它有三个建设性贡献：全 raw-leaf direct scan 不受 learned cap、family quota、
以及 k=5/k=11 双尺度局部攻击。

但它把 learned interaction 压到 5,831 维、限制 numeric path，并把完整 16,384 categorical / 每
family 4,096 n-gram 攻击列为未测试。独立 benchmark 没有支持这种削减的必要性：当前机器上完整
extractor 的 1,600-receipt 外推约 45.79 秒，23,250 维 dense float64 的 400+800 矩阵约 212.9 MiB，
logistic 2,000 步的 warning-free 下界约 29.3 秒，kNN 外推约 7.67 秒。真正不可接受的是 9,999
次每模型重训，而不是完整叶或完整 learned representation。

因此 formal 选择遵守：

> 已构造的假绿反例不能只因一个未经实测的成本担忧而被删除；只有被 benchmark 证明承重的成本
> 才允许改变科学主张。

## 被拆分而非伪装完成的成本

9,999 次 frozen-prediction block permutation 是秒级可行路径，V1 保留。9,999 次全模型
retrain-and-rescore 仅 logistic 下界就约 61–81 小时，拆为后续
`MODEL-SELECTION-RANDOMIZATION`。只有 extractor/feature/hyperparameter/control primary 全部
precommit、holdout 不参与选择、prediction 在 label join 前冻结并锚定时，V1 shortcut 才适用；
任一条件不成立，batch 直接 `NOT_QUALIFIED`。

## 仍需完成

1. 把完整 profile bytes、D0/D1 registry、host-only test inventory 与 exact shared evidence schemas
   纳入 runner precommit，而不是只传 hash。
2. 独立 evaluator 按 profile 新实现完整 leaf/C01–C05/provider，不得沿用当前 96/128 内部默认。
3. 用实际形状 receipt 完成 3,200-row rehearsal、双 replay、最大树/process/truncation fixture 与成本
   ceiling；不得用合成下界冒充实测。
4. 完成这些 binding 后重新生成 formal precommit 与外部双锚；当前 F smoke 只验证 V1.3 runner，
   不包含本 profile，不能升级为 formal profile evidence。
