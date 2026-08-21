# Wave 006-A：Relation materiality

状态：`LOCAL_SYNTHETIC_COMPARISON_COMPLETE`  
共享分母：`W6-STERILE-ROUTE-SIMULATION-001`  
共享任务 SHA-256：
`0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`

## 问题

在一次有界 sterile-route simulation 已经产生 delivery、cross-authority ACK、domain
postcondition 和 beneficiary acceptance 后，把这次协作进一步表示为 Relation，是否会改善
后续任务结果；还是 task-bound receipt/ACK 已经足够？

本实验不以 RelationVersion 胜出为目标。完整解决当前问题的 controller receipt、双 ACK 或
其他成熟组合都是正向结果。

## 共享边界

三组面对同一 `E0–E8` 事件流、operation、input、truth、权限、扰动和成本模型。唯一变化是
relation layer 如何表示证据：

- A：relation layer 只保留 delivery receipt；
- B：保留双方 recipient ACK，但 ACK 只证明本任务收到；
- C：双 ACK、双方 explain-back 和 version-bound relation proposal。

共同 operation truth 已由 fixture 冻结。A 胜出不表示 delivery receipt 可以替代
cross-authority ACK 或 beneficiary acceptance；它只表示在“是否认领持续关系”这个局部问题
上，不增加 Relation 已经足够。

初始 contract 明确为 `ONE_OPERATION_ONLY`。C 的两个 explain-back 都复述
`FRESH_TASK_AUTHORIZATION_REQUIRED`，所以 relation proposal 必须保持
`PROPOSED_NOT_CONSTITUTED`。Proposal 不是 relation，delivery/ACK/acceptance 也不是 relation。

## 冻结任务与扰动

E6 是相似但非相同的 `RUN-STERILE-ROUTE-SIM-v1.1`。schema alias 没有改变语义，但 operation
已经变化；三组都必须澄清并使用 fresh task authorization，不能沿用一次性任务。

E7/E8 同时检验：

- exact replay 与 schema-compatible alias；
- recipient key rotation、environment drift；
- same idempotency key / changed command；
- material purpose change、anchor fork、beneficiary refusal；
- withdrawal 后残留。

`UNKNOWN`、`REFUSE`、`ABSENT` 分别计数，不合并成失败。

## 结果

| 组 | Reuse success | False relation | Stale reuse | Withdraw residual | Clarification | Disclosure | Coordination | Net value |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A delivery only | 1 | 0 | 0 | 0 | 1 | 2 | 2 | **51** |
| B dual ACK | 1 | 0 | 0 | 0 | 1 | 2 | 4 | 49 |
| C ACK + explain-back + proposal | 1 | 0 | 0 | 0 | 1 | 4 | 9 | 42 |

在这个冻结任务中：

1. A/B/C 都没有把一次任务误写成持续关系；
2. B 的 dual ACK 已足以表达双方收到本任务，但不产生 future authority；
3. C 没有增加 reuse success、降低 stale reuse、降低 withdrawal residual 或减少 clarification；
4. C 相对 B 的 net value 为 `-7`；
5. relation-representation 局部最优是 A：保留 task evidence，同时不创建 relation。

因此当前正向结论是：

> 使用更简单的现有 task-bound evidence，不物化持续关系。需要跨权限域证明本次送达时仍使用
> dual ACK；需要执行相似新任务时使用 fresh task authorization。

这不是对 RelationVersion 的全局否定。它只说明在一次性、fresh-authorized reuse 的当前任务
中，RelationVersion 没有材料性增益。

## 最强反例

`ATTACK_ONE_SHOT_AS_CONTINUING_RELATION` 在 E2 收到一次 delivery 后直接置
`relation_state=ACTIVE`，随后：

- 对相似非相同任务执行 stale auto-reuse；
- withdrawal 后继续保留 active relation；
- 自报 false-positive 为零。

Evaluator 不读取候选自报分数，而是从 trace 重建，得到：

- false relation constitution：7 个 active checkpoints；
- stale reuse：1；
- withdrawal residual：1；
- false positive：9；
- false negative：1；
- net task value：`-116`。

该反例被拒绝，说明“一次性检索/送达被误当持续关系”不能借漂亮 relation 对象通过。

## 来源与证据边界

只使用以下公开材料作为历史边界：

- Wave 004-A：trusted local controller receipt/readback 的能力与限制；
- Wave 005-B：dual recipient ACK、external anchor 和 cross-authority evidence 的能力与限制；
- Wave 006 frozen shared task 与 integration rubric。

没有读取 HW-C private packet、tests、oracle 或 controller-index。

本实验只能证明在固定合成 truth 和成本下三种 relation representation 的判别力与净值；不能
证明真人理解、现实关系形成、医疗安全、生产有效或跨域频率，也不证明需要新的通爻协议。

## 复现

```bash
python3 simulator.py
python3 -m unittest discover -s tests -v
python3 -m py_compile simulator.py evaluator.py
```

`simulator.py` 生成三组候选和最强反例；`evaluator.py` 从冻结 trace 独立重建
false positive、false negative、reuse、withdrawal、disclosure、coordination、recovery 和
net task value。
