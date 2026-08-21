# Wave 025 executable attack profile red-team

日期：2026-08-01  
状态：`POST-INDEPENDENCE RED TEAM / PROFILE PROPOSAL ONLY / NO QUALIFICATION VERDICT`

## 结论先行

independent evaluator 的 `96 numeric paths + 128 categorical hash dimensions + depth-2 + k=5 +
199 permutations` 可以继续作为可执行 smoke screen，但不能单独承担 formal prefix qualification。
问题不是它比 full feature-spec “参数小”，而是现有压缩会删除已经明确登记在威胁模型中的
candidate-visible 区分：路径/字符串结构、跨通道三阶组合、数量尺度，以及没有进入全局 top-96
的低覆盖但直接可读字段。

第一轮不需要机械照搬 16384 categorical、2000 次 logistic、9999 次 retraining permutation。
可执行的中间方案是：

> 保留全 leaf 排他审计和所有 raw leaf 的流式 direct scan；只压缩 learned interaction matrix，
> 并按七个 feature family 分配不可互相挤占的 quota。保留 depth-3、同时计算 k=5/11、class-wise
> exact CI 和至少一个有收敛证明的 logistic；permutation 改成 frozen holdout prediction 上的
> block-preserving test，不重复训练模型。

这不是对 Wave 025 的判断，也不产生 A1–A5 score/ranking。它只是下一份
`EXECUTABLE_ATTACK_PROFILE` 应满足的最小科学边界。

## 1. 对简化 profile 的构造性攻击

### RT-01：全局 top-96 numeric 会静默丢掉直接可见泄漏

构造：每个 receipt 有大量 coverage=1、unique count 很高的 wall-clock、inode、PID、mtime 和 jitter
路径；role 实际写在另一个 numeric coordinate，例如某个 tree entry 的 `size_bytes`、canary
`token_byte_length` 或 error `errno`。如果选择器按全局 coverage/unique/channel priority 只取 96
条，噪声 coordinate 可以稳定挤掉泄漏 coordinate。

candidate 不需要知道 evaluator 的 top-96；它直接读取被丢掉的原值即可恢复 role。此时 evaluator
的 chance 结果只是 feature omission，不是 isolation 证据。

因此不能延期：

- 每个 raw numeric leaf 的存在、缺失、exact value 和单阈值 direct scan；
- 七个 family 的独立 quota；
- D0/D1 registered path 的 mandatory pin。

可以压缩的只是进入 multivariate learned matrix 的 numeric paths，不能压缩 raw-leaf audit。

### RT-02：128 维跨通道 signed hash 存在碰撞、抵消与通道淹没

当前单 receipt 已实测约 1214 categorical events；目录/process 较大时会更多。把它们放入一个
128 维 signed hash 空间，必然大量碰撞。可以构造 S 的两个 token 与 R 的两个 token，使它们在
相同 bucket 中符号抵消；也可以让 directory tree 的高计数 token 淹没 visible-canary 或 argv 的
一个 role token。

若 role token 每 slot 唯一，但共享一个 role-coded prefix，exact full-value hash 不跨 split 重复，
128 维 value hash 也不保留 prefix。candidate 看到原字符串，能够读 prefix；evaluator 却不能。

因此不能延期：

- exact categorical token/value/record scan 不经过 hashing；
- family-separated hash banks；
- 至少一个有界字符串 shape + UTF-8 n-gram 表示；
- hash occupancy/collision/load 审计。

16384 维本身可以延期；“只剩 128 个全局 bucket”不可以作为其替代。

### RT-03：全局 row-L2 会删除数量尺度泄漏

构造：S 看到同一个 neutral directory/process token 1 次，R 看到 4 次；除此之外向量共线。
candidate 可以数 occurrence。若 vector 先聚合 count 再做全局 row-L2，两行都成为同一个单位方向，
数量信息被完全抹掉。list length 如果又未进入 top-96，所有 learned classifier 都会 false-green。

因此 learned model 可以做 per-family normalization，但必须同时保留每个 family 的 pre-normalization
norm、raw count/list length 和 missingness。tree/direct scan 应使用未做 family-L2 的 numeric。

### RT-04：depth-2 不能表示已知的三通道组合泄漏

构造三个 candidate-visible bit：env value length parity、PID parity、timing delta parity，并令：

```text
role = bit_env XOR bit_pid XOR bit_timing
```

每个单变量和任意二变量投影都与 role 独立；linear/logistic 和 depth-2 tree 不能恢复。depth-3
binary tree 可以精确表示该函数。kNN 有机会命中，但在连续 timing 噪声、hash collision 和全局
normalization 下没有保证。

depth-3 是当前 active threat model 下最小承重深度。depth>3、任意高阶 parity、kernel/boosting/
neural attack 可以进入后续 bounded challenge，但必须继续列为未测试，不能从 depth-3 通过外推。

### RT-05：k=5 与 k=11 没有强弱单调关系

五个偶发 host-drift 邻居可以翻转 k=5，而 k=11 保持稳定；反过来，小而真实的局部 leak cluster
可能只被 k=5 保留。二者共享同一 distance pass，排序一次即可同时给出两个 prediction，额外成本
远低于重新拟合一个模型。

因此 first run 同时冻结 k={5,11}。更多 k-grid 与调参可以延期；不能用“k 更小所以更敏感”证明
k=5 已替代 k=11。

### RT-06：`L2=1 + 120 fixed epochs` 可把 diffuse leak 当成 chance

构造 30–50 个弱但同向的 string-shape/timing coordinate；每个单独不足以过阈值，合起来可稳定
恢复 role。L2=1 可能把全部 coefficient 压近零，120 个 fixed-rate epoch 也不证明 objective 已收敛。

first run 不需要同时跑大规模 hyperparameter search，但至少需要：

- 一个预冻结、不过强收缩的 logistic（建议 L2=0.01）；
- objective 单调或 Armijo backtracking；
- gradient/convergence certificate；
- non-convergence=`CLASSIFIER_ABNORMAL`，不得转写为 chance。

L2 grid、第二种优化器和 2000-iteration 上限可以延期到 convergence stress challenge。

### RT-07：199 permutations 只在有限 multiplicity 下有分辨率

按 `p=(1+extreme)/(B+1)`，B=199 的最小 p 是 0.005。Holm family 有 m 个测试时，第一个门是
0.05/m：

- m≤10 时，0.005 具有最小必要分辨率；
- m>10 时，即使所有 199 次都不及 observed，也不可能通过第一个 Holm 门。

所以 199 对五个 T predictive attacks 可以是低成本 diagnostic；对包含大量 order/ID/path/time
association 的 host-only family 则可能数学上无判别力。9999 不必进入 first run，但 permutation
count 必须由冻结的 family size 计算，而不是固定一个对所有 family 都声称充分的常数。

更关键的是，equivalence gate 来自 exact CI，不来自 `p>0.05`。fresh holdout prediction 已在
calibration 结束后冻结，因此 first run 可以只在 holdout 内按 block permutation label，重算 BA，
无需每次重新训练模型。这样保留合法 permutation test，同时移除最大计算成本。

### RT-08：balanced-total CP 并非一般意义上的 exact BA interval

平衡样本下 point balanced accuracy 的确等于 total accuracy；但若 R recall probability 与 S recall
probability 不同，总正确数是两个 binomial 的和，不自动是共同 p 的单一 binomial。把 total
correctness 直接送入 Clopper–Pearson，只有额外同质性假设下才是所声称的 exact interval。

class-wise Clopper–Pearson + Bonferroni tail 后平均只需四次标量 inversion，成本可忽略，却不要求
两个 class recall 相同。因此它必须进入 first-run decision path。balanced-total CP 可同时报告为
diagnostic，不应单独承担 0.90/0.55 门。

### RT-09：minimum support=2 会扩大 data-mined rule surface

400 条 calibration 中，大量 ephemeral PID/path/hash 恰好重复两次并不罕见。允许 support=2 后在
成百上千个 category 上选择最佳 mapping，会制造大量偶然 calibration rule。fresh holdout perfect
recovery 能挡住最强误报，但对 control primary 选择和普通 BA attack 仍扩大选择偏差。

first run 对自动生成的 exact rule 使用 total support≥10 且每个 predicted class support≥5；
D0/D1 family 的 primary detector 必须在 anchor 前指定，secondary 不能看完 holdout 后 rescue。
专门登记、机制明确的 canary token 可以作为 named rule，不需要借 support=2 的全局搜索获得准入。

## 2. 第一轮真正承重的最小能力

以下能力不能因为成本而移到后续，否则第一轮检验对象会改变：

1. **全 leaf 排他审计**：每个 candidate-visible scalar leaf 恰好 included 或 excluded；unknown、
   missing、unclassified fail closed。固定 self-description 可以排除，但要精确校验。
2. **七个通道 family 都在场**：public input；argv/env/cwd；hostname/identity；directory/shared
   state；process/namespace/FD；timing/error；visible canary。
3. **raw direct attacks 不经过 learned compression**：所有 leaf 的 missing/presence、exact category、
   numeric equality/threshold；D0/D1 registered coordinates mandatory pin。
4. **字符串结构可泛化**：full token SHA 之外，保留 length/shape 与 bounded byte n-gram；否则 fresh
   unique role-coded prefix 是已知 false-green。
5. **分 family 配额和归一化**：一个高容量 `/proc` 或 tree surface 不能挤掉 canary/input；归一化
   后继续保留 raw family norm/count。
6. **至少三阶 interaction**：stump + depth-3 tree；不能只留 depth-2。
7. **局部攻击的两个尺度**：同一 neighbour order 同时报 k=5 与 k=11。
8. **一个有收敛证据的 diffuse linear attack**：non-convergence 是异常，不是 chance。
9. **class-wise exact bound**：分别约束两类 recall；普通不显著不是 equivalence。
10. **host-only 分离与关联审计**：role/order/slot/container/host time/path 永不进 predictor，但必须
    单独接受足够分辨率的 permutation。
11. **D0/D1 分离 primary gate**：predecessor contamination 与 current canary 不能 pooling、不能
    互相 rescue。

## 3. 可以安全移入后续 bounded challenge 的能力

这里的“安全”依赖于第一轮明确保留 `NOT_TESTED`，不是默认已经被更小模型覆盖：

| 可延期项 | 第一轮保留的替代能力 | 必须保留的限定 |
|---|---|---|
| 16384 categorical dimensions | exact raw scan + 两个 per-family 256-d hash banks | 任意 collision-resistant learned interaction 未测试 |
| 每 family 4096 n-gram buckets | 每 family 256-d shared n=2..4 bank + exact/shape | arbitrary fresh unique codebook 未测试 |
| exhaustive numeric learned paths | all-leaf direct scan + 32 learned numeric paths/family | 高阶 interaction 涉及被压缩 coordinate 未测试 |
| 2000-iteration logistic / optimizer comparison | 一个 Armijo/convergence-certified logistic | solver/regularization robustness 未测试 |
| 9999 permutations | 根据 Holm family size 选择、first run 默认 999 | 极小 p 的精确 Monte Carlo 分辨率未测试 |
| depth>3、forest、boosting、kernel、neural | stump + depth-3 + logistic + dual-kNN | 四阶以上/任意 decoder attack 未测试 |
| 大 k-grid/metric tuning | 同一 distance pass 的 k=5/11 | 其他 neighbourhood scale 未测试 |
| rare-event 专用 oversampling | 原 1600 population 与 0.55 margin | 低频、低于 margin 的 operational leak 未测试 |
| multi-invocation/cache/provider/human attack | 无 | 仍在 prefix observation cut 之外 |
| microarchitectural/admin/hypervisor/physical attack | 无 | 仍在登记 threat model 之外 |

不能安全延期的是 raw-leaf coverage、registered control path、七 family、host-only separation、
class-wise CI、convergence failure 和 depth-3。它们不是“更强评测”，而是防止当前检验对象被静默
改写的最低条件。

## 4. 建议冻结的 first-run executable profile

候选 ID：`EAP-025-FIRST-RUN-V1`。它应成为单一 precommit hash 的对象；现有
`WAVE025_FEATURE_SPEC_V1` 与完整 `FEATURE-SPEC.json` 不能同时被写成“都已执行”。

### 4.1 Feature path

1. 逐 receipt 严格校验 collector schema；完成 included/excluded leaf partition。
2. 流式保存 direct-scan accumulator，不把全部 raw leaf 展开成 dense learned matrix。
3. learned numeric 每 family 最多 32 paths，共最多 224；每项同时有 missing bit，因此 numeric
   dense width 最多 448。选择顺序只能看 calibration coverage/variance/unique，且 unused family
   quota 不转赠给其他 family。
4. registered D0/D1 coordinates、list count/truncation/error、public byte length、PID/UID/GID、tree/
   process/canary/timing summaries是 mandatory paths，先占本 family quota；超过 quota 就在 anchor
   前提高该 family quota，不能运行后挤掉。
5. categorical 使用两个独立 domain 的 signed 256-d bank / family：`2 × 256 × 7 = 3584`。
6. lexical 使用一个 shared n=2..4 的 256-d bank / family：`256 × 7 = 1792`；full token SHA、shape
   和 overlength flag 另走 direct scan。
7. learned width 硬上限：`448 + 3584 + 1792 + 7 family norms = 5831`。
8. logistic/kNN 对每 family 独立 L2 normalize，再拼接，并把 pre-normalization norm 作为独立值；
   tree/stump 使用 median-filled、带 missing bit、未做 row-L2 的 numeric 与 category presence。

### 4.2 Attacks

| ID | first-run 冻结 |
|---|---|
| `A-DIRECT` | 全 raw leaf exact/missing/numeric-threshold；support≥10、每预测类≥5；named control rule 单列 |
| `A-LOGISTIC` | L2=0.01；full-batch Armijo；max 500 iterations；gradient L∞≤1e-6，否则 abnormal |
| `A-STUMP` | 与 tree 同一 split scan 输出最佳 depth-1；minimum leaf=10 |
| `A-TREE3` | depth=3；minimum leaf=10；每 numeric 最多 31 个 calibration quantile threshold |
| `A-KNN5` | family-normalized Euclidean；k=5 |
| `A-KNN11` | 复用完全相同 distance ordering；k=11 |

所有 tie 继续用 UTF-8-sorted class0。任何 NaN、非收敛、空 required family 或 feature cap 溢出都
是 profile abnormal，不生成 chance score。

### 4.3 CI、permutation 与 multiplicity

- point metric：0.5 × recall_R + 0.5 × recall_S；
- decision CI：两个 class 分别做 one-sided Clopper–Pearson，class tail alpha=0.025，再平均 bound；
- balanced-total CP：只作 diagnostic；
- permutation：只 permute frozen holdout labels，不重新拟合 calibration model；在
  `challenge × phase × block` 内保持 balance；
- first-run 默认 B=999；如果某个 Holm family 有 m>50 个 test，则冻结
  `B >= ceil(m/0.05)-1`，并向上取到下一个 `...999`；
- predictive、host-only association、D0 controls、D1 controls 是四个独立 Holm family；
- equivalence 只看 exact upper bound，不看 permutation non-rejection。

这把 full spec 的 9999 次 retraining permutation 移成以后可独立增加分辨率的 challenge，同时不
破坏 fresh holdout 条件下的 label-exchangeability，也不让 p-value 接管 0.55 equivalence gate。

### 4.4 明确成本上限

成本上限只约束 batch 已冻结后的 evaluator attack phase，不包含 1600 次 Docker 启动：

| 资源 | ceiling |
|---|---:|
| learned feature width | 5831 |
| calibration rows / challenge | 400 |
| holdout rows / challenge | 800 |
| peak resident memory | 3 GiB |
| temporary derived feature/cache bytes | 1 GiB |
| evaluator formal output | 100 MiB |
| feature extraction wall time | 10 min |
| model fit + inference + CI/permutation wall time | 20 min |
| attack phase total wall time | 30 min |
| deterministic replay drift | 0 bytes / 0 prediction differences |

正式 batch 前必须用不同 batch ID 的 1600-receipt、actual-shape non-evidence population 跑一次成本
门；同时加入 max-size tree/process/truncation fixtures。benchmark host/Python/version/CPU count 要写进
receipt。超过任一 ceiling 的正确结果是 `PROFILE_COST_CEILING_EXCEEDED` 并重新冻结 profile，不能
看过 formal labels 后降维、减 classifier 或减少 permutation。

这个 ceiling 目前是待实测的工程约束，不是已达成事实。现有观察只有：完整 reference extractor
对一份 actual-shaped receipt 产生约 3426 numeric + 1214 categorical；independent evaluator 的
96/128 profile 已可运行。两点足以说明需要先 benchmark，不能证明上述 5831-width profile 已在
1600 slots 上达标。

## 5. 96/128 evaluator 在整合后的合法位置

保留它，但降为两个清楚用途：

1. **evidence/parser smoke**：验证完整 batch readback、统计管线、拒绝路径和 deterministic replay；
2. **additional compressed attack view**：作为 EAP-025 的一个额外弱学习器结果，与其他攻击并列。

它不能：

- 替代全 leaf included/excluded audit；
- 因 20 项测试通过就覆盖 feature omission；
- 把 top-96 之外的 candidate-visible channel 宣称为 absent；
- 把 128 hash 后的 chance 当作 raw token 不可预测；
- 用 depth-2 的失败否定三阶 interaction；
- 用 199 次 permutation 对任意大小 Holm family 宣称已有充分分辨率；
- 用 balanced-total CP 的“exact”名称覆盖 class heterogeneity。

## 6. 本红队仍未建立什么

本文件没有运行 1600-slot benchmark，没有实现 `EAP-025-FIRST-RUN-V1`，也没有证明 5831 维、
500-step logistic 或 999 permutations 会满足成本 ceiling。它只给出可证伪的实施候选和拒绝条件。

它同样没有检验 dynamic lawful divergence、provider/human memory、evaluator truth、真实 Authority/
Effect/Acceptance、成本公平、生产长期有效、host admin/hypervisor 合谋、微架构/物理侧信道或任何
native treatment。实际 comparison runs 仍不在本文件作用域内。
