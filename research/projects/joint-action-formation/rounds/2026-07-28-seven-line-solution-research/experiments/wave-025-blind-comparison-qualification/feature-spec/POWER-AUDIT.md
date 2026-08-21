# Wave 025 POWER-NOTE V3 independent audit

日期：2026-08-01  
状态：`INDEPENDENT STANDARD-LIBRARY RECOMPUTATION / NO CONTRACT OR PROFILE CHANGE`

## 结论

`POWER-NOTE.md` V3 的三个单攻击数值和“五攻击 union-bound 下界”均复算成立，舍入方向也正确：

| 每类 holdout `n_c` | `CP_upper(n_c/2,n_c; tail α=.025)` | 单攻击 `P(pass)` |
|---:|---:|---:|
| 400 | 0.550092112258985 | 0.488072095266342 |
| 800 | 0.535217969600060 | 0.880009800683206 |
| 1200 | 0.528676790882859 | 0.982255246856065 |

对 `n_c=1200`：

```text
five-attack all-pass lower bound
= 1 - 5 × (1 - 0.982255246856065)
= 0.911276234280323
```

该下界不要求五个攻击相互独立。它要求的是更早一层假设：对每个攻击，S/R 的正确数确实可以
建模为两个独立的 `Binomial(1200, .5)`，类内 episode correctness 独立且真实 recall 都为 0.5。
block balance 只冻结每类样本数，不能证明 correctness 独立。

但是，V3 不能支持当前 `EAP-025-FIRST-RUN-V1` 的“六个攻击都作为 T gate”这一扩展。相同
`n_c=1200` 下，六攻击 union-bound 下界是：

```text
1 - 6 × (1 - 0.982255246856065) = 0.893531481136387
```

它低于约 0.90 的联合接纳设计目标。因此必须明确选择其一：

1. 只有五个攻击承担共同 pass gate，另一个是 diagnostic；
2. 为六个 gated attacks 重新做 block-aligned exact power design；
3. 明确接受 0.89353 而不是 0.90 的 union-bound 下界。

本审计不替任何一项作决定，也不修改 candidate。不能用 V3 的“五攻击 0.9113”给六攻击 profile
背书。

## 1. 独立实现

最小复现代码是 `feature-spec/power_audit.py`。它不 import runner、evaluator、feature extractor 或
candidate profile，只使用 Python 标准库。

one-sided class-wise CP upper 对 `k<n` 定义为根：

```text
P_U[X <= k] = 0.025,  X ~ Binomial(n,U)
```

实现以 `k/n` 和 1 为 bracket 做 80 次 bisection，返回最终 bracket 的高端，因此浮点残差不会把
边界上的失败翻成通过。`k=n` 返回 1。pass event 严格按：

```text
(U(K_S) + U(K_R))/2 <= 0.55
```

双 Binomial 权重用整数精确计算：每个 lattice cell 的 numerator 是
`C(n,K_S) × C(n,K_R)`，共同 denominator 是 `2^(2n)`。生产计算利用 CP upper 的单调性，以每个
`K_S` 对应的最大通过 `K_R` 做累计和；测试另外用小 n 的 literal O(n²) 双循环逐 cell 枚举，两者
得到完全相同的 `Fraction`。

## 2. alpha、threshold 与方向检查

方向正确：

- `0.975` 是每类 one-sided confidence；对应 tail alpha 是 `0.025`，不是把 CDF 设为 0.975；
- alpha 越小，CP upper 越大，门越保守；
- `k` 越大，CP upper 单调增大；
- 只有平均 upper `<=0.55` 才通过；
- 两个 97.5% class upper 由 Bonferroni 给出至少 95% simultaneous coverage，再平均成 BA upper；
- union bound 用 false-fail `1-P(pass)`，方向为 `1-mq`；不能写成攻击准确率的 union。

这也解释了 `n_c=400,k=200` 的中心点 upper 已略高于 0.55，但双 Binomial pass probability 仍非
零：pass lattice 允许一个 class 低于中心、另一个稍高，只要两个 upper 的平均不超过阈值。

## 3. 数值误差与 pass lattice 稳定性

三个中心 CP upper 又以 80 位 `Decimal` 和独立 Decimal binomial recurrence 复核：

| `n_c` | Decimal CP upper | float–Decimal 绝对差 | float CDF root residual |
|---:|---:|---:|---:|
| 400 | 0.5500921122589880 | 2.66e-15 | 7.22e-16 |
| 800 | 0.5352179696000630 | 2.66e-15 | 1.46e-15 |
| 1200 | 0.5286767908828530 | 6.22e-15 | 2.46e-15 |

最靠近 `U_S+U_R=1.10` 的 lattice 边界为：

| `n_c` | 最近 pass 到 1.10 的余量 | 最近 fail 超过 1.10 的余量 |
|---:|---:|---:|
| 400 | 3.39e-6 | 8.77e-6 |
| 800 | 5.83e-7 | 2.46e-6 |
| 1200 | 8.73e-7 | 7.31e-7 |

这些余量至少比 float–Decimal 差大约八个数量级，当前 pass/fail cell 集合不受观察到的数值误差
影响。`n_c=1200` exact pass numerator 的十进制整数 SHA-256 为
`86630e7afd1e076e8bcfdd0df4d8d3326f1a97a8d7d06ef24e656fa2a9af6a80`，共同 denominator 是
`2^2400`，便于不同实现核对枚举身份而不在文档中粘贴巨型整数。

## 4. block balance

按 block size=20、每 block S/R 各 10：

| challenge/phase | slots | blocks | 每 role |
|---|---:|---:|---:|
| D0 calibration | 100 | 5 | 50 |
| D0 holdout | 100 | 5 | 50 |
| D1 calibration | 100 | 5 | 50 |
| D1 holdout | 100 | 5 | 50 |
| T calibration | 400 | 20 | 200 |
| T holdout | 2400 | 120 | 1200 |

合计 3200 slots、160 blocks，T holdout 的确给出双 Binomial 枚举使用的 `n_c=1200`。

但 block balance 只证明 label population 与分块数量正确。若同一 block 的 daemon/thermal/time
shock 使 episode correctness 相关，则 `K_S,K_R ~ independent Binomial` 的功效模型不再精确；
permutation/block audit 可以发现部分相关性，却不能让这份 pre-run IID 功效计算自动适用于任意
相关结构。

## 5. 离散样本量不是单调光滑的

CP gate 是离散 lattice。作为六攻击重新设计的警告，额外 spot-check 得到：

| `n_c` | single `P(pass)` | six-attack union lower |
|---:|---:|---:|
| 1210 | 0.983606830762 | 0.901640984572 |
| 1220 | 0.983245283659 | 0.899471701954 |
| 1230 | 0.984520349229 | 0.907122095375 |
| 1240 | 0.985703456485 | 0.914220738911 |

所以不能假定“再增加一个 block 就一定提高 exact power”，也不能从 1210 直接宣布所有更大 n
都满足目标。若六攻击都要 gated，应在允许的 block-aligned 候选范围上完整扫描并冻结一个具有
适当稳健余量的 n，而不是事后增样。

## 6. 可复现方式与证据边界

运行：

```bash
python3 feature-spec/power_audit.py
python3 -m unittest discover -s feature-spec/tests -p 'test_power_audit.py' -v
```

测试覆盖：CP edge/direction、float/Decimal、V3 三组数字、literal/optimized 双枚举一致、pass lattice
误差余量、五/六攻击 union bound、3200 人口与 block balance、非法参数拒绝。

本审计支持的是：“在两类真实 recall=.5、每个攻击内部符合双独立 Binomial episode model 时，
V3 对五攻击给出的数值和 union bound 正确。”它不证明现实 correctness 独立、不证明 detector
充分、不证明 feature coverage、blindness、资格结果或任何 treatment 比较。
