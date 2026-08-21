# Wave 009 failure history

本文件保留真实实现顺序，不把最终绿灯倒写成一次成功。

## 1. tests-first 首轮红灯

先只创建完整行为测试，尚无实现。命令：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave009-first-red \
  python3 -m unittest discover -s tests -v
```

精确结果：

```text
ImportError: Failed to import test module: test_wave009_crossed_square
ModuleNotFoundError: No module named 'authority_truth_broker'
Ran 1 test in 0.000s
FAILED (errors=1)
```

这是预期红灯：测试先冻结 24-world 分母、双 broker 隔离、非蕴含门、六组 mutation、
presentation controls、攻击与 T5 bypass，随后才实现任何模块。

## 2. 实现策略

首轮红灯后一次性补齐：

- runtime-random world/run ID；
- relation/authority 两个独立 truth broker 和随机 Ed25519 key space；
- parent-owned process transport、exact bytes、operation/ledger/exit capture；
- B0–B5 七个注册实现；
- 两个独立 evaluator 与只读 public integration evaluator；
- 六组 paired mutations、presentation controls 和 T5 executable bypass。

这一轮没有出现需要隐藏的中间测试失败。首次完整 suite 运行即通过 17 项。不能据此推断
设计普遍正确；它只表示首轮红灯所冻结的本地行为合同已被实现。

## 3. 首轮完整绿灯

```text
Ran 17 tests in 19.659s
OK
```

Runner 随后实际生成 168 个核心运行（24 worlds × 7 baselines）、六组 B5 配对 mutation、
两组 presentation control 和 T5 state-machine trace。

这一绿灯及其输出现在标记为 `V1 FALSE POSITIVE INVALIDATED`。旧输出 SHA-256：

```text
ec529db69d6083263fcbd5bcdf6130f1a58acf9c9f3b09708aeec6a707bffa2b
```

## 4. 仍然保留的失败边界

- T3 不是现实任务，T4 仍是合成任务；
- 两个 broker、baseline 与 evaluator 来自同一 authoring stream；
- 子进程没有同权限 filesystem sandbox；
- presentation 的语义已经显式结构化，不能证明未声明 Intent 被恢复；
- 首版 B0/B1/B5 实际共享同一解析器，不能登记为三个成熟方案；
- 没有真人授权、独立实现、盲式外部复核、生产或长期漂移证据。

因此最终绿灯不能被提升为 V1/V2 一般解、真实产品保证或现实主体 Acceptance。

## 5. 独立复核推翻首版

Root 独立复核发现六类阻断性问题：

1. B0/B1/B5 都调用同一个 `full_relation/full_authority`，只有 label 和 trace 不同；
2. Authority section 没有绑定顶层 world/text、current head/version 和 section issuance
   context，旧完整 section 或跨世界 section 可被重放；
3. duplicate reservation 只是顺序 fixture，不是原子并发；
4. T5 是每次新建结果的无状态函数，没有 parent-owned state、真实 readback 或幂等冲突；
5. 核心 invalid worlds 因枚举索引错误只覆盖 stale/revoked，controller/duplicate 只存在
   于外围 mutation；
6. 所谓 held-out language pair 的文本完全不参与判断，不能支持语言理解结论。

这说明 17/17 只证明首版测试没有覆盖这些攻击。B0/B1/B5 `24/24` 的旧表述不能保留。

## 6. Repair tests-first 红灯

先把六类反例写入测试，再修改实现。精确结果：

```text
Ran 22 tests in 56.663s
FAILED (failures=1, errors=5)
```

具体红灯：

```text
missing binding_attack_results
missing center_relation_path
core missing CONTROLLER_SUBSTITUTION and DUPLICATE_RESERVATION
missing concurrent_reservation_probe
missing presentation-control result fields
missing T5AuthoritativePlatform
```

## 7. Repair 实现

- B0 direct table、B1 workflow-state、B5 component-composition 改成六个不同 high-level
  functions，并冻结源码 fingerprint；状态只允许
  `DISTINCT_PATHS_SAME_AUTHORING_STREAM`。
- 两个 broker 新增签名 `SECTION_CONTEXT`；每个 event 绑定 context hash、owner domain、
  world、task、version/head。
- 新增跨世界 section/event、顶层 world/text、旧 head/version section replay 回归。
- reservation check+insert 置于同一 lock 临界区；duplicate world 使用两个 barrier-synchronized
  threads 实际竞争。
- T5 改成 parent-owned state machine、account readback、idempotency registry 与 ledger。
- 核心 invalid enumeration 修复为四类各 3 个。
- held-out language 结论删除，改为 presentation no-op controls。

修复后首次完整 suite：

```text
Ran 22 tests in 23.998s
OK
```

这个绿灯仍只属于本地合成、同一 authoring stream，不构成独立实现或现实证据。

随后把 B1/B5 在 duplicate core 上的可观察行为差异和 T5 单次 provision ledger 也加入
回归。最终 suite：

```text
Ran 23 tests in 15.270s
OK
```

manifest 与 frozen output 写入后再次执行同一 suite：

```text
Ran 23 tests in 21.402s
OK
```

## 8. 第二轮独立复核仍为 OPEN

第二次 root 复核又找到五个会保留伪阳性的缺口：

1. Relation/Authority evaluator 按 kind 聚合，逆序事件仍可能形成；B1 workflow 甚至把
   `PROPOSAL_RECEIVED` 写成初始常量；
2. `full_existing` 只看 B0/B5 核心计数，不消费 binding、非蕴含、顺序、并发、T5 和
   presentation scope，外围攻击失败仍可能保持 positive/no residual；
3. `AuthorityPrivateWorld` 同时保存 `authority_valid` 与 `authority_mode`，可构造互相矛盾
   的两份真值；
4. completed run 的 operation/ledger 没有 seal，原地清空后只能靠重跑一个新 run 掩盖；
5. `EXPLAIN_BACK_NOT_STANCE` 从一个原本就缺 explain-back 的 invalid world 删除 stance，
   没有隔离 stance 的作用。

这些反例再次说明第一轮 repair 的 23/23 仍不是充分攻击面。

## 9. 第二轮 repair tests-first 红灯

先写入反例，未改实现。精确结果：

```text
Ran 28 tests in 19.296s
FAILED (failures=1, errors=4)
```

失败分别为：

```text
authority_valid remained a second dataclass truth field
missing verify_completed_run_record
missing isolated non_implication_probe_details
missing residual_matrix
missing sequence_cardinality_attack_results
```

## 10. 第二轮 repair

- Relation 现在要求唯一 proposal、proposal-first、各阶段 predecessor、严格 kind order 和
  cardinality；Authority 要求 principal-order mandate/commitment pairs、revocation/
  reservation/standing 阶段顺序与基数。
- B0/B1/B5 都直接运行 reverse、delete-proposal、duplicate-proposal 攻击。
- `AuthorityPrivateWorld` 删除 `authority_valid` 字段，只保留 `authority_mode`；
  `authority_valid` 仅是 `mode == NONE` 的派生 property。
- Parent 对 exact bytes、operations、两个 broker ledgers、exit 和 identity 计算 evidence
  anchor；两个 evaluator 与 integration 都绑定同一 anchor。
- 完成 run 另由 parent runtime key 签名。row 内不携带可替换 public key；verifier 只接受
  parent 提供的 trusted public key。清空任一 ledger/operation、修改 exit 或使用错误 trusted
  key 都使原 completed run 失效。
- `full_existing/B6` 改由 residual matrix 唯一决定，矩阵覆盖 core、mutations、binding、
  non-implication、sequence/cardinality、concurrency、T5、presentation scope、run seals、
  single truth 与 scoped path distinction；任一 false 都返回
  `RESIDUAL_PRESENT_OR_HARNESS_INVALID / PENDING_RESIDUAL_DIAGNOSIS`。
- ACK/explain-back 与 explain-back/stance 分别从其他条件均合法的同一个 bounded world
  单独删除并复跑。

修复后的完整 suite：

```text
Ran 28 tests in 29.474s
OK
```

最终 runner 重生成 frozen output 后，再次执行完整 suite：

```text
Ran 28 tests in 30.438s
OK
```
