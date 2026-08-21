# Wave 007-C：同一 evidence API 下的 access-metered reliance

状态：`LOCAL_SYNTHETIC_REPAIR_COMPLETE_PENDING_INDEPENDENT_AUDIT`

## 修复对象

本实验修复 Wave-006-B / Wave-006-D 暴露的两个承重缺陷：

1. strategy 不再接收 evaluator 预先整理的 truth-like snapshot；四个 strategy 只能通过同一个
   `EvidenceAPI` 读取 declaration、probe、receipt、SLA、health、authority status 和
   recovery receipt；
2. 证据成本不再由 strategy 名称或预设常数决定，而是只从 API 原始 operation log 重建。

共享任务仍是 `W6-STERILE-ROUTE-SIMULATION-001`，绑定 SHA-256：
`0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`。
本目录不修改原 Wave-006 产物。

## 隔离与真实执行

三个角色被分开：

- `private/build_public_fixture.py` 持有确定性测试 private key，只负责生成签名 evidence；
- `strategies.py` 只接收 `EvidenceAPI`，不读取 fixture、truth 或 private key；
- `evaluator.py` 最后才加载 `private/truth.json`，从 candidate decision、hidden truth、
  postcondition 和 raw operation log 计算结果。

Evidence API 对每次调用记录 operation、evidence type、record ID、bytes、延迟、成功/失败、
重试、披露量和 observation。strategy 实际调用 Ed25519 验签，并实际校验 exact binding、
freshness 和当前 authority。这里采用明确的无隐式 cache 语义：相同 bytes 的重复读取、重复
验签和重复 freshness check 都分别记录、分别计费。

## 隐藏世界

15 个不带语义的 opaque token 覆盖：

- static valid / explicit absent；
- active / revoked authority；
- stable / drifted environment；
- authority refuse / beneficiary post-operation refusal；
- valid recovery / missing recovery receipt；
- current operation failure / transient probe failure；
- cold-start insufficient history；
- lapsed SLA but otherwise valid operation；
- open-world unknown。

semantic pair、variant、`safe_to_rely`、operation postcondition 和 beneficiary acceptance 只在
hidden evaluator truth 中。公开 evidence 中的差异由真实签名 bytes、observation 或缺失项
表达，不靠 case 名称。

## 当前合成结果

| implementation | TP | FP | FN | evidence cost | operation success | business accepted |
|---|---:|---:|---:|---:|---:|---:|
| Declaration | 9 | 1 | 0 | 18.101193 | 9 | 8 |
| Latest probe | 8 | 0 | 1 | 20.485833 | 8 | 7 |
| Receipt window | 8 | 1 | 1 | 44.468119 | 8 | 7 |
| SLA + recovery | 7 | 0 | 2 | 36.045724 | 7 | 6 |

这个结果没有预设 SLA，也没有产生一个普遍 winner：

- Declaration 成本最低且不漏掉 valid world，但会在 current failure world 产生一次 false
  reliance；
- Latest probe 避免该 false reliance，但 transient probe failure 产生一次 missed
  opportunity；
- Receipt window 在这些观察维度上不优于前两者且更贵，因此在当前 Pareto 目标下被支配；
- SLA/recovery 能区分 recovery evidence 是否存在，但在 lapsed SLA 和 recovery-evidence
  missing world 更保守；当前样本中被 Latest probe 支配。

被支配只对当前隐藏世界、当前实际操作成本和列出的目标成立。它不是对 receipt、SLA 或外部
技术的普遍否定。

## 条件区间，而非聚合推荐

基础 48 点 failure-loss / missed-opportunity / evidence-cost 扫描中：

- Declaration 在 36 点唯一胜出；
- Latest probe 在 12 点唯一胜出；
- 有 1 个 winner margin 不超过 1 的近边界点。

额外频率扫描把同一 candidate 输出放入六种 scenario-frequency profile。统一频率下
Declaration / Latest probe 分别覆盖 21 / 6 个 winner 点；把 current failure 提高到 8 倍时，
两者变为 10 / 17。该变化说明 winner 是 failure frequency 和损失/成本权重的函数，不是
implementation 名称的属性。Pareto frontier 在当前六个 profile 中均为 Declaration 与
Latest probe；近边界和平局单独保留为 no-conclusion region。

这些 profile 是反事实敏感性，不是现实故障频率估计。

## 预注册攻击的本地回归

`results/evaluation.json` 包含实现者自检：

- opaque rename、truth-label flip、self-report injection；
- label/function swap；
- primary evidence、authority status、probe freshness、recovery receipt deletion；
- unauthorized signature；
- command、purpose、key、environment、semantic bytes binding；
- duplicate receipt；
- raw operation-log delete/add/reorder 与伪造 candidate cost；
- repeated read/verify/freshness billing；
- `UNKNOWN / REFUSE / ABSENT` preservation。

所有这些自检当前通过，但它们不是独立证据。root 仍需按冻结的
`WAVE-007-INDEPENDENT-AUDIT-PROTOCOL.md` 直接替换输入、调用公共接口并重算。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/w7c-pycache python3 private/build_public_fixture.py
PYTHONPYCACHEPREFIX=/tmp/w7c-pycache python3 evaluator.py \
  --output results/evaluation.json
PYTHONPYCACHEPREFIX=/tmp/w7c-pycache python3 -m unittest discover -s tests -v
```

## 证据边界

这是本地合成机制实验。它能检验：在给定 hidden worlds 中，候选是否真的读取和验证了证据，
cost 是否能由 raw operation log 重建，以及哪些策略差异会改变 reliance。它不能证明现实
故障频率、现实 SLA 价值、长期恢复效果、真人 acceptance 或生产可靠性。

如果 declaration、probe、transaction log、SLA、人工制度或它们的现成组合在同一边界内解决
问题，这就是正向解题结果；不需要为保持“通爻独占”重复创造。若未来真实任务暴露当前组合
无法覆盖的缺口，再针对那个有界缺口完整创新。
