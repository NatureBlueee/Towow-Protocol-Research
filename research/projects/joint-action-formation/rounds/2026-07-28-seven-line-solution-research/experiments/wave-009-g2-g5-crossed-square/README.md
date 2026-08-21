# Wave 009 G2/G5 crossed square

状态：
`SECOND_REPAIR_LOCAL_SYNTHETIC / PRIOR FALSE POSITIVES RETAINED / RESIDUAL_MATRIX_FULL`

## 最窄 surviving claim

本实验现在只支持：

> 在 24 个冻结合成 worlds、显式结构化语义、受信 parent、独立 relation/authority truth
> broker、签名 section context、严格 event sequence/cardinality、原子 reservation
> ledger、parent-trusted completed-run seal 和全项 residual matrix 的前提下，两个
> 可检查但同一 authoring stream 的本地路径——B0 direct center path 与 B5 component
> composition path——都能准确重建 G2/G5 核心真值和 integration readiness。这个结果说明
> 现有的签名、hash binding、workflow/policy/commitment、事务唯一性与 HITL 组合在该有限
> 模型中足够；不证明三个独立成熟产品、现实主体或 V1/V2 一般问题已经被解决。

首版“B0/B1/B5 是三个完整成熟方案”的表述无效。B0、B1、B5 当时只是同一个
`full_relation/full_authority` 解析器换标签，独立复核正确识别了这一伪阳性。旧 frozen
output SHA-256 `ec529db69d6083263fcbd5bcdf6130f1a58acf9c9f3b09708aeec6a707bffa2b`
只作为失败历史，不再是当前结果。

## 任务与分母

T3/T4 仍不是现实任务：

- T3：`SYNTHETIC_TASK_SPEC / EXECUTION_RESOURCE_REQUIREMENT_ONLY`
- T4：`SYNTHETIC_TASK_SPEC / FROZEN_SYNTHETIC_WORLD`
- T5：`NEGATIVE_CONTROL_SPEC`

核心分母：

```text
T3/T4
× ONE_SHOT/BOUNDED/DURABLE
× relation valid/invalid
× authority valid/invalid
= 24 worlds
```

Authority-invalid 核心 worlds 现在均匀覆盖：

- `STALE_VERSION`
- `CONTROLLER_SUBSTITUTION`
- `REVOKED`
- `DUPLICATE_RESERVATION`

首版核心只实际采到了 stale/revoked，controller/duplicate 被藏在外围 mutation；这一覆盖
缺口已修复。

Authority private state 只保留 `authority_mode` 这一份权威表示。`authority_valid` 不再是
可独立写入的字段，只是 `authority_mode == "NONE"` 的派生 property；broker、evaluator
和 integration 因而不能分别读取两份可能矛盾的真值。

## B0–B5 的真实实现边界

七个注册 baseline 仍使用相同 public bytes、查询预算和父进程计费边界，但不再把 B0/B1/B5
指向同一高层函数：

- B0：direct decision-table center path；
- B1：显式 relation workflow state transitions；Authority workflow 只能看到 reservation
  receipt，不能裁决并发冲突；
- B2：workflow relation + CLM/approval，不能建立 reservation；
- B3A：OpenFGA + Cedar 形状，只处理 policy permit；
- B3B：OpenFGA + OPA 形状，只处理 policy permit；
- B4：commitment/transactional reservation Authority path，不形成 relation；
- B5：relation sub-components + policy/commitment/atomic-ledger/standing composition。

B0、B1、B5 的六个 high-level path 有不同源码 fingerprint，报告状态为：

`DISTINCT_PATHS_SAME_AUTHORING_STREAM`

它们仍不是独立实现、不同厂商产品或 blind evidence。

## Section 和事件绑定修复

Relation 与 Authority broker 使用不相交的 runtime-random Ed25519 keyspace、private state
和 ledger。每个 section 现在包含 broker-signed `SECTION_CONTEXT`，精确绑定：

- opaque target `world_id`；
- 顶层 `task + presentation + world_id` 的 exact semantic-input hash；
- current relation version；
- current Authority revoke head；
- task fingerprint；
- runtime issuance ID。

每个事件还绑定：

- section-context hash；
- event-owner domain；
- world ID；
- task fingerprint；
- exact version/head/scope。

当前可复现攻击结果：

| Attack | Result |
|---|---|
| 跨世界整段 Authority section 移植 | `SECTION_CONTEXT_INVALID` |
| 顶层 world ID 修改 | `SECTION_CONTEXT_INVALID` |
| 顶层 presentation 文本修改 | `SECTION_CONTEXT_INVALID` |
| current head 改变后重放旧完整 section | `SECTION_CONTEXT_INVALID` |
| current relation version 改变后重放旧完整 section | `SECTION_CONTEXT_INVALID` |
| 单个跨世界事件移植 | `EVENT_CONTEXT_OWNERSHIP_INVALID` |

这解决的是 exact bytes/context 归属，不是自然语言理解。

## Event sequence 与 cardinality

Relation 不再按 event kind 无序聚合。形成必须从唯一 `PROPOSAL` 开始，并严格依次经过：

```text
PROPOSAL
ACK × principals
EXPLAIN_BACK × principals
STANCE × principals
COUNTER
RELATION_VERSION
```

Authority 同样要求按 principal 顺序出现 `MANDATE → COMMITMENT`，随后才允许可选
`REVOCATION`、reservation 结果和唯一 `STANDING`。B0 direct、B1 workflow、B5 composition
分别接受同一组攻击；两域 reverse、删除唯一 proposal、重复 proposal 共 12 个
baseline/attack cells 全部 fail closed。B1 workflow 的初态为 `START`，只有读到真实
proposal 后才进入 `PROPOSAL_RECEIVED`。

## Reservation 并发

`AuthorityTruthBroker` 的 reservation index 现在由 lock 保护，检查与写入处于同一临界区。
duplicate worlds 不再先顺序插入答案，而是让两个真实 Python threads 经 barrier 同时竞争
同一 resource/time/purpose slot。

20 次独立 race regression 中，每次均为：

```text
1 RESERVATION
1 RESERVATION_CONFLICT
```

这只支持当前单进程 broker 的原子性；不证明分布式数据库或跨故障域线性一致性。

## Completed-run anchor 与 seal

每个完成 run 的 evidence anchor 覆盖 exact stdin/stdout bytes、operations、两个 broker
ledgers、exit 和 run identity。Relation/Authority evaluator 与 integration 都必须绑定同一
anchor。Parent 再用 runtime Ed25519 key 对完整 row 签名；row 本身不携带可替换公钥，验证
必须使用 manifest/report 固定的 trusted public key。

对一个已完成 row 原地清空 operations、清空任一 broker ledger、修改 exit，或改用错误
trusted key，都会使原结果验证失败。该检查针对同一个完成记录，不以重新运行产生新记录来
掩盖篡改。它依赖受信 parent private memory，不抵抗 parent runtime compromise。

## Presentation controls，不是 language holdout 证据

首版把两组文本称为 held-out language pairs，容易误导。当前明确降级为 presentation
no-op controls：

- 相同 presentation、不同 signed structured semantics → 决策不同；
- 不同 presentation、相同 signed structured semantics → 决策相同；
- 任意改写 presentation exact bytes 而不重新签发 context → 拒绝。

因此 presentation 文本被完整性绑定，但没有被语义解释。报告明确写入：

`PRESENTATION_NOOP_CONTROL_NOT_LANGUAGE_UNDERSTANDING_EVIDENCE`

本实验不支持未声明 Intent 恢复、自然语言 materiality 泛化或隐私披露问题已经解决。

## T5 parent-owned authoritative state machine

T5 现在由 parent-owned `T5AuthoritativePlatform` 持有：

- authoritative state；
- buyer/account readback；
- exact-request idempotency registry；
- operation ledger。

首次执行：

```text
VALIDATE_EXACT_REQUEST
CREATE_REQUEST
BUYER_APPROVE
PROVISION_SEATS
TARGET_READBACK
CLOSE_REQUEST
```

真实 parent readback 为 `BUYER-01 / SKU-CRM / 5 active seats / CLOSED`。

攻击结果：

- 删除 buyer：`BYPASS_UNAVAILABLE`
- 同 idempotency key + 相同 exact request：`IDEMPOTENT_REPLAY`，不重复 provision
- 同 idempotency key + 不同 bytes：`IDEMPOTENCY_CONFLICT`
- 删除 authoritative state machine：`BYPASS_UNAVAILABLE`

T5 仍创建 0 个 relation object 和 0 个额外 Authority object。

## 修复后核心结果

| Baseline | G2 exact | G5 exact | Integration exact | ready |
|---|---:|---:|---:|---:|
| B0 | 24/24 | 24/24 | 24/24 | 6 |
| B1 | 24/24 | 21/24 | 24/24 | 6 |
| B2 | 24/24 | 3/24 | 18/24 | 0 |
| B3A | 0/24 | 0/24 | 18/24 | 0 |
| B3B | 0/24 | 0/24 | 18/24 | 0 |
| B4 | 0/24 | 24/24 | 18/24 | 0 |
| B5 | 24/24 | 24/24 | 24/24 | 6 |

B1 的 3 个 Authority error 正是 duplicate core worlds：workflow receipt 不等于 atomic
reservation uniqueness。Integration 仍为 24/24，是因为第三 evaluator 只消费两侧 public
assertion，并在 G5 assertion 不精确时 fail closed；它不是对 B1 Authority 的补救。

六组 paired mutation、四类 Authority attack 和八项非蕴含门在 B5 路径中通过。
`EXPLAIN_BACK_NOT_STANCE` 不再从原本已缺 explain-back 的 world 二次删 stance：两个
probe 都从同一个其他条件合法的 bounded world 出发，分别只删除全部 explain-back 或全部
stance；两者均单独令形成失败，并保留另一类事件的完整 cardinality。

当前结果状态为：

`POSITIVE_LOCAL_SYNTHETIC_EXISTING_COMPOSITION_SCOPED`

该状态与 B6 决策不再只看 B0/B5 核心 exact count，而由 11 项 residual matrix 唯一决定：

- B0/B5 核心 exact；
- paired mutations；
- section/event binding attacks；
- isolated non-implication；
- sequence/cardinality attacks；
- atomic concurrency；
- T5 state/readback/idempotency；
- presentation scope honesty；
- completed-run seals；
- Authority 单一真值表示；
- “路径有别但并非独立实现”的范围诚实性。

任一项失败都会取消 positive/no-residual，改为
`RESIDUAL_PRESENT_OR_HARNESS_INVALID / NOT_IMPLEMENTED_PENDING_RESIDUAL_DIAGNOSIS`。
当前 11/11 通过，所以 B6 保持
`NOT_IMPLEMENTED_NO_OBSERVED_RESIDUAL`。这只表示冻结本地残差矩阵没有观察到缺口；若现实
任务、未声明语义、分布式原子性或独立产品测试暴露剩余缺口，再按该缺口决定是否需要 B6。

## 仍不成立

- T3/T4 真实任务覆盖；
- 三个独立成熟方案完整解决；
- 自然语言语义泛化；
- same-UID filesystem adversary 隔离；
- 独立实现、blind review 或不同 authoring stream；
- 真人授权、Acceptance、生产、长期漂移或跨故障域 reservation 保证；
- V1/V2 一般解。

## 复现

```bash
PYTHONPYCACHEPREFIX=/tmp/wave009 \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/wave009-run \
  python3 runner.py
```

完整 parent-owned exact stdin/stdout bytes、operation logs、两个 broker ledger、exit records、
completed-run seals、攻击结果、residual matrix 和 T5 ledger 位于
`outputs/results.json`。
