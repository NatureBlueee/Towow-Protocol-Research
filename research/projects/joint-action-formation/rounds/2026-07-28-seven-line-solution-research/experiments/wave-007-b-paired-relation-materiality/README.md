# Wave 007-B：paired relation materiality

状态：`LOCAL_SYNTHETIC_SELF_TEST_COMPLETE_PENDING_INDEPENDENT_AUDIT`

本实验修复 Wave 006-A 的核心失真：候选不再读取 semantic case/truth，representation 会实际
改变候选收到的 evidence bytes 与 API operation，evaluator 从签名证据、authority response、
withdrawal、reuse trace 和原始操作日志独立重建错误与成本。候选可见的 `public_api.py` 不含
world truth、私钥或签名器；authority 的 private state、证据库存与 evaluator truth 不进入
候选输出。

## 问题与 paired worlds

固定任务是 `W6-STERILE-ROUTE-SIMULATION-001`。实验交叉两项 evaluator-only 真值：

- 一次操作后必须结束，或已存在一次明确、有限的 reuse authorization；
- relation evidence 有效，或缺失/相互矛盾。

候选只看到 opaque handle 与所选 representation 实际读取到的证据。四种 representation
不是预设 winner：

- `TASK_BOUND`：delivery + 两个独立主体的 task ACK；
- `EXPLAIN_BACK`：在 task-bound 上增加双方 explain-back；
- `BOUNDED_RELATION`：再增加 exact proposal、双方独立的 bounded authorization 与
  withdrawal observation；
- `NO_EVIDENCE`：零证据基线。

## 本地合成结果

| evaluator world | representation | constituted | reuse | missed | stale | withdrawal residual | evidence cost | net value |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ONE / valid | TASK_BOUND | 0 | 0 | 0 | 0 | 0 | 12.120850 | -12.120850 |
| ONE / contradictory | TASK_BOUND | 0 | 0 | 0 | 0 | 0 | 12.120850 | -12.120850 |
| BOUNDED / valid | TASK_BOUND | 0 | 0 | 1 | 0 | 0 | 12.120850 | -52.120850 |
| BOUNDED / valid | EXPLAIN_BACK | 0 | 0 | 1 | 0 | 0 | 20.899658 | -60.899658 |
| BOUNDED / valid | BOUNDED_RELATION | 1 | 1 | 0 | 0 | 0 | 42.264893 | 17.735107 |
| BOUNDED / valid | NO_EVIDENCE | 0 | 0 | 1 | 0 | 0 | 1.000488 | -41.000488 |
| BOUNDED / contradictory | BOUNDED_RELATION | 0 | 0 | 1 | 0 | 0 | 36.208740 | -76.208740 |

这里有三个不同结论，不能压成一个通用 winner：

1. 在 `ONE_OPERATION_ONLY` 条件下，task-bound evidence 足以避免把一次交付错误升级为持续
   relation。这是简单现有证据的正向结果，不需要为了“独特性”制造 relation 对象。
2. 在真实存在一次 bounded reuse 权限且证据完整时，task ACK 和 explain-back 都不足以执行
   reuse。产生可观察增量的是：双方 unique task ACK、双方一致 explain-back、绑定同一
   operation/relation/version 的 exact proposal、双方 unique bounded authorization；withdrawal
   则负责清除该有限权限。
3. 当真实授权存在但证据缺失或矛盾时，安全拒绝仍然产生 `missed legitimate reuse=1`。这不是
   relation 机制成功，而是证据形成失败的成本，不能用“没有误执行”掩盖。

`NO_EVIDENCE` 在一次性世界最便宜且没有误构成，但它无法跨 paired worlds 解决真实 bounded
reuse，因此低成本本身不构成充分方案。

## 预注册攻击的本地回归

本地测试覆盖：

- opaque rename、label/function swap、truth-only flip；
- 逐项删除 delivery、两个 ACK、两个 explain-back、proposal、两个 authorization；
- candidate self-report 注入；
- duplicate authorization 与 allowlist 外主体的有效签名 authorization；
- 已签 proposal bytes 改写、错误 evidence kind、合法主体对错误 purpose 的重新签名；
- allowlist 外主体签发 withdrawal，不能清除 relation；
- 直接绕过 candidate 调用 authority 时，对 duplicate 与 cross-purpose authorization 的拒绝；
- `UNKNOWN / REFUSE / ABSENT` 区分；
- 从 raw operation log 重排、增加调用并重新计费；
- 无证据自行宣布 ACTIVE；
- withdrawal 后再次请求 reuse 并恢复 ACTIVE。

这些回归当前全部通过，但它们仍是同一实现者的自测。`SUPPORTED_SCOPED` 仅表示本地合成结果
满足当前 scoped claim 条件，不等于独立验证、现实频率、生产有效或通爻整体主张成立。

## Provenance

- shared task 当前实际 SHA-256：
  `0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`
- repair harness 开工 handoff SHA-256：
  `934e0fb834577530ce523b79476a9a4bbaa286ac91f14abb012fd0bd0a54f212`
- repair harness 本轮实际读取 SHA-256：
  `7b6fe448b16cbeb48b749b76b454c8b3fd10e1669605927b49c28e575cdee653`
- independent audit protocol 当前实际 SHA-256：
  `5eec08681a819d6c1ade908c127baa986da8db689b2f6df8765cf0d83ad7e98f`

repair harness 的变化发生在开工后，来自 duplicate-vote 共同攻击条件更新；007-B 专项语义未
改变。本产物绑定并测试实际读取版本，不把 handoff 的旧 hash 伪称为冻结命中。

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/wave007b-pycache \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/wave007b-pycache \
  python3 evaluator.py --output results.json
```
