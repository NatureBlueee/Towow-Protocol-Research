# Wave 025 qualification power note

日期：2026-08-01  
状态：`V3 PRE-FORMAL FIVE-ATTACK CLASS-WISE DESIGN CORRECTION / EXACT BINOMIAL CALCULATION`

## V3：不能只为单个 classifier 设计功效

V2 的每类 800 使单个 chance classifier 约有 88.0% 概率满足 class-wise 0.55 gate，但正式剖面
同时冻结 C01–C05 五个异质攻击，而且要求每一个都通过。不能假定它们的错误独立，也不能把
`0.8800^5` 当成保证。为使五个攻击在真实 recall 都为 0.5 时仍有至少约 90% 的联合接纳下界，
使用同一 exact 双二项枚举，并对五个 false-fail 使用 union bound：

```text
n_c=1200（T holdout 总计 2400）
CP_upper(600,1200,0.975) = 0.5286767909
single-classifier P(pass) = 0.9822552469
five-classifier joint P(pass) >= 1 - 5 * (1 - 0.9822552469)
                              = 0.9112762343
```

因此 V3 冻结 T holdout 为 2400，S/R 各 1200；T calibration 仍为 400。D0/D1 仍各 200，formal
总人口为 3200 slots。该下界不依赖五个 classifier 的错误独立性；代价是更大的真实 batch，但
避免“增加攻击器数量反而把诚实 chance batch 大量误拒绝”的设计缺陷。

独立标准库/80-bit Decimal 复核见 `feature-spec/POWER-AUDIT.md`。其精确复算为：

```text
n_c=1200 single-attack pass = 0.982255246856065
five-attack union lower     = 0.911276234280323
```

它还发现压缩竞争候选登记了六个 gated attacks（额外加入 k=5）；相同人口的六攻击 union lower
只有 `0.893531481136387`，不能继承这里的“五攻击 ≥0.90”结论。正式已选完整 profile 仍精确使用
FEATURE-SPEC 的 C01–C05 五攻击。若将来把 k=5 从 diagnostic 升为第六个 gate，必须先重新冻结人口
或明确接受更低功效，不能借用 V3 数字。

## V2 历史：class-wise exact bound 为什么曾把每类提高到 800

独立兼容性审查指出，V1 的 total-correct Clopper–Pearson 隐含两个 class recall 同质；正式合同
真正需要的是：S、R 各自做 one-sided Clopper–Pearson，class tail `alpha=0.025`，再平均两个上界。
这不是实现细节。下面的 V1 总正确数计算保留为历史推导，但不再决定 formal 人口。

令每类 holdout 大小为 `n_c`，真实两类 recall 都为 0.5，独立正确数
`K_S,K_R ~ Binomial(n_c, 0.5)`。通过事件为：

```text
(CP_upper(K_S, n_c, 0.975) + CP_upper(K_R, n_c, 0.975)) / 2 <= 0.55
```

用当前独立 evaluator 的 exact binomial/Clopper–Pearson 标量实现枚举 `(K_S,K_R)`，得到：

```text
n_c=400（T holdout 总计 800）
CP_upper(200,400,0.975) = 0.5500921123
P(pass | both recalls=0.5) = 0.488072095

n_c=800（T holdout 总计 1600）
CP_upper(400,800,0.975) = 0.5352179696
P(pass | both recalls=0.5) = 0.880009801
```

V2 曾把 T fresh holdout 从总计 800 增至总计 1600，S/R 各 800；该设计解决单 classifier 功效，
但没有解决五个冻结攻击的联合 false-fail，现已由 V3 取代。

## V1 历史：为什么曾把 total-correct holdout 从 400 改为 800

原 red-team minimum 建议二元 T holdout 至少 400、每 class 200，并要求每个 classifier 的
balanced accuracy 单侧 95% 上置信界不高于 0.55。该规则控制了错误资格化，却没有保证在真实
accuracy=0.50 时有足够概率得到可判定通过。

把平衡 holdout 的总正确数视为 `K ~ Binomial(n, p)`，Clopper–Pearson upper 定义为满足
`P_p(X <= K)=0.05` 的 p。对 n=400：

```text
K=203 -> observed accuracy 0.5075 -> one-sided upper 0.549723 -> pass
K=204 -> observed accuracy 0.5100 -> one-sided upper 0.552206 -> not pass
P(K <= 203 | p=0.5, n=400) = 0.6368065424
```

因此即使单个 classifier 完全处于 chance，400 holdout 也只有约 63.7% 概率进入资格区；四个
预注册 classifier 都要过门时，功效可能更低（它们的错误相关，不能简单相乘，但问题不会消失）。
这会制造大量诚实但低信息量的 `NOT_QUALIFIED`。

对 n=800，同一 exact rule 的最大通过点为：

```text
K=416 -> observed accuracy 0.5200 -> one-sided upper 0.549589
P(K <= 416 | p=0.5, n=800) = 0.8783483530
```

所以 V1 曾在任何 formal return 产生前，将 T holdout 从 400 增至 800，calibration 保持 400。
这一步的 total-correct 结论已被上面的 class-wise V2 取代，不能继续作为 formal decision rule。

## 仍然没有解决什么

- 88.0% 是单 classifier、两类真实 recall 均为 0.5 且 episode correctness 独立时的枚举结果，不保证
  多 classifier 联合通过；
- balanced accuracy 的 class-specific dependence、block/time correlation 需要 evaluator 另做
  permutation/block audit；
- 增大 N 不修复 weak detector、feature omission、keyed covert channel、runtime drift 或错误的
  observation regime；
- 这不是看过结果后的扩样。若 formal precommit 已生成或任何 holdout 已运行，本次修改将不合法；
  当前尚无 formal batch，因此修正不污染证据。

第一批仍可能 `NOT_QUALIFIED`，但不再以明显偏低的单分类器功效作为默认设计。
