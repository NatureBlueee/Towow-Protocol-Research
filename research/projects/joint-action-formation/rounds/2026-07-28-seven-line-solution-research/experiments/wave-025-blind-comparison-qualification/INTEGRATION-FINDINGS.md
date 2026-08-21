# Wave 025 integration findings

日期：2026-08-01  
状态：`ROOT CROSS-IMPLEMENTATION AUDIT / FORMAL RUN BLOCKED`

## 独立实现没有“自然一致”

这是正向发现。feature-spec 与 independent evaluator 在互不读取的条件下形成了不同攻击计划：

| 项目 | feature-spec line | independent evaluator line |
|---|---|---|
| feature representation | 全 leaf 排他审计；七 family；4096 n-gram + 16384 categorical sparse buckets | 最多 96 numeric paths + 128 categorical hash dimensions |
| deterministic | exact token/value/conjunction，support 10/每类 5 | categorical/value mapping，minimum support 2 |
| tree | stump + depth-3 tree，minimum leaf 10 | 一个 depth-2 tree，最多 9 thresholds/feature |
| kNN | k=11 | k=5 |
| logistic | L2=0.01、full-batch Armijo、最多 2000 iter | L2=1、fixed learning rate、120 epochs |
| permutation | 9999、block-preserving | 199、按 precommit/model/label 派生 |
| CI | class-wise CP、Bonferroni tail 后平均 | balanced-total CP |

两者都满足共享合同“至少四类攻击”的文字，但不检验同一个 frozen claim。把它们的 hash 同时写进
precommit 不会自动使二者兼容；测试总数相加也不能消除语义分歧。

## 哪一方也不能直接获胜

feature-spec 的优势是 candidate-visible leaf coverage、included/excluded partition 和更强的路径/
字符串/高阶攻击；但其 3426 numeric + 1214 categorical 的单 receipt 实测输出，配合 400 条
calibration、16384 维模型、最多 2000 次 full-batch logistic 和五类 classifier，尚无端到端
成本/收敛验证。直接把它称为“更严所以更好”可能得到一个形式完整却无法在 1600 slots 上实际
运行的方案。

independent evaluator 已有 20 项测试、纯 stdlib、四类可运行 classifier、CI/permutation/Holm，
但其内建 feature plan 没有采用最终 `FEATURE-SPEC.json`；它也主动列出 shared-interface ambiguity，
因此当前最高 `NOT_QUALIFIED` 是正确行为，不能因“可运行”而覆盖 feature omission 风险。

## smoke 与 formal 的边界

当前 real smoke 只验证 runner 的真实 Docker/evidence path。它可以、也应该因为 sample 太小、
mode=smoke、contract ambiguity、source drift 或 evaluator/spec mismatch 而拒绝资格。一个完整走通且
最终 `NOT_QUALIFIED` 的 smoke 比伪造 `PREFIX_QUALIFIED_SCOPED` 更有价值。

正式 1600-slot batch 之前必须再冻结一个唯一的 `EXECUTABLE_ATTACK_PROFILE`：

1. 明确选择或组合 feature extractor，而不是同时引用两个不兼容 plan；
2. 用真实 receipt population 做内存、运行时间、收敛与 deterministic replay benchmark；
3. 固定 exact schema/mapping/Merkle/control family/monotonic/raw-inspect 规则；
4. 让 independent evaluator 对该 profile 的 bytes 做新实现或明确审计过的 provider 调用；
5. 重新计算 runner/evaluator/spec/profile hashes 后才 prepare formal batch。

这不是为了追求独立原创，而是为了保证“existing mature combination 能解决”这一结论对应同一个
可复现实验对象。若精简 profile 在相同攻击能力下更可运行，应采用精简方案；若精简会漏掉已经
构造出的反例，应保留必要的复杂度或拆成多个有界 challenge。

## 2026-08-01 后续综合：完整 profile 已选，但尚未执行

独立成本复核与 F actual-shape receipt 推翻了“完整叶必须先压缩才能运行”的担忧：完整 extraction
仍是分钟级线索；真正承重的成本差异是 9,999 次全模型重训。根选择记录见
`PROFILE-SELECTION.md`，正典 bytes 是 `EXECUTABLE-ATTACK-PROFILE.json`。它保留 FEATURE-SPEC
的 F01–F07 与 C01–C05，不采用 96/128 或 5,831 learned-width cap；只把全重训随机化拆为明确的
`MODEL-SELECTION-RANDOMIZATION = NOT_TESTED`，同时保留 9,999 次冻结 holdout prediction 的
block-preserving permutation。

class-wise CP 与五攻击联合 false-fail 又把 formal population 从历史 1,600 修正为 3,200；独立
标准库复核支持五攻击 union-bound 下界约 0.9113。压缩竞争候选额外加入 k=5，若六个都作为 gate，
相同人口下界只有约 0.8935；所以它只能保持 smoke/additional attack 候选，不能借五攻击功效数字
获得 formal 地位。

F 已证明 V1.3 runner structural path 可闭合，但旧 evaluator 对新字段和共享歧义输出
`NOT_QUALIFIED`。这正是独立实现应有的拒绝，而不是需要绕开的红灯。formal 仍需：exact shared
evidence schemas/profile bytes location、完整 evaluator engine、3,200-row rehearsal、双 replay 与
新 precommit/external anchor。上文“正式 1600-slot”因此是历史待办，已由当前 3,200-slot 决定取代。
