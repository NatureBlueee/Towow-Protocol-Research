# Failure history

只记录实际出现过、并改变实现或证据边界的失败。

## F1 — tests-first 时核心模块不存在

**触发**

```text
PYTHONPYCACHEPREFIX=/tmp/w9g1-first-red \
python3 -m unittest discover -s tests -v
```

**实际结果**

```text
ModuleNotFoundError: No module named 'query_genesis'
Ran 1 test
FAILED (errors=1)
```

**意义**

冻结测试先于实现建立，证明当前绿灯不是先写实现再为现状补断言。随后实现了 22
世界、父 runner、request-only gateway、七条独立策略和 evaluator。

## F2 — 候选仍能通过类属性冒用 Router 身份

**攻击**

新增一个未登记的 `ForgedRouter`，把自己的 `strategy_id` 写成
`router_composition`，并返回伪造的 `cost=-1000` 与 `truth=HANDOFF`。攻击测试
要求父 runner 拒绝它。

**第一次结果**

```text
test_unregistered_candidate_cannot_claim_a_registered_identity ... FAIL
AssertionError: ValueError not raised
Ran 15 tests
FAILED (failures=1)
```

**根因**

`run_one` 曾把 `strategy_type.strategy_id` 当成 canonical identity。这个字段由
候选类拥有，与“runner-owned identity”相冲突；即使 cost 和 truth 不参与评分，
候选仍可污染策略归属。

**修复**

- 增加父 runner 独占的 `TRUSTED_STRATEGY_REGISTRY`，以类对象映射 canonical ID；
- 未登记类型立即失败，不能冒用已登记身份；
- 候选返回只保留为“不用于评分”的键名诊断，不再把原始自报对象放进结果；
- 后续矩阵、行为签名、native scope 和 T5 gate 都从父 registry 取 identity。

**回归**

攻击测试与全部原冻结测试随后共同通过：

```text
Ran 15 tests in 0.124s
OK
```

## F3 — 跨 runtime opaque evidence 重放攻击

**攻击**

在第一个父 runtime 中取得 `CURRENT_COMPAT` evidence ref，再把它交给第二个父
runtime 的 `handoff`。

**结果**

第二个 runtime 返回 `HANDOFF_REJECTED`，handoff log 保持为空。opaque refs 由每个
runtime 的随机 key、nonce 与私有 evidence store 共同约束；此攻击没有产生新的
实现失败，但被保留为回归门。

## 当前仍未解决的攻击面

候选与 broker 仍运行在同一 Python 进程和同一文件权限域。对象封装、HMAC seal 与
source import gate 能发现普通越界、伪造与重放，但不能抵抗能够反射运行时对象、
读取源码或改写同目录文件的恶意本机进程。要提升到该威胁模型，需要独立进程/权限域、
只读候选环境以及 worker 无权改写的外部或签名锚；本轮没有伪装成已经完成。

