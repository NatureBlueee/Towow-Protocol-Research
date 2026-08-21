# Wave 007-A2 opaque authority harness

状态：`REPAIRED_SELF_TESTED_AWAITING_NEW_INDEPENDENT_AUDIT`  
关系：A2 是对 A v1 被 root 独立攻击推翻后的新版本；原
`wave-007-a-opaque-authority-harness/` 保持不变。  
范围：G6/G7 最小闭环；不输出 winner。

## 为什么 A v1 无效

root 在结果后直接运行
`audits/wave-007/root_attack_a.py`，构造了此前未覆盖的序列：

1. 同一 network 先用 baseline request 走到 domain postcondition；
2. beneficiary 返回 `REFUSE`，因此没有 L4 acceptance；
3. 再用同一个 idempotency key 提交 changed command。

A v1 把 `idempotency_key → request_sha` 只登记在 L4 acceptance。于是第二次 changed request
仍获得新的 EFFECT_ATTEMPT、delivery 和 domain postcondition，最后又因为 beneficiary
REFUSE 而让 evaluator 报出 `actual_terminal=REFUSE / terminal_match=true`。L4 结果掩盖了
已经发生的第二次 L3。

root 的实际观察是：

- `controller_refused_at_attempt=false`；
- `new_domain_postcondition_called=true`；
- 同权限 OS peer 可直接读取 `fixtures/hidden-worlds.json`。

因此 A v1 的 effect/idempotency 闭环和 adversarial truth-isolation 表述均被推翻。A2 的自测
不能把这个独立反例抹掉，也不构成新的独立支持。

## A2 修复

### 1. Idempotency 在第一次合法 attempt 原子绑定

controller 在验证两份 holder authorization 后、签发 EFFECT_ATTEMPT 前，在锁内执行：

```text
unbound key               -> bind key to exact normalized request SHA
same key + same SHA       -> replay existing attempt/evidence path
same key + different SHA  -> signed REFUSE before new EFFECT_ATTEMPT
```

这个绑定不依赖 delivery、anchor、ACK、L3 postcondition 或 L4 beneficiary acceptance 是否
发生。A2 分别从先前停在 L1 attempt、L2 delivery、L3 postcondition、L4 beneficiary REFUSE
的状态发起 changed request；四种情况下都在新 attempt 处拒绝，且不再调用 delivery 或
domain postcondition。

当前 binding ledger 是单个受信 host 内的内存状态并以锁保护 compare-and-bind。它没有证明
进程崩溃后的持久化、跨节点共识、灾难恢复或恶意 host 安全；这些属于后续实现条件，不能从
本轮结果外推。

### 2. 分开跟踪 attempt、L3 和 L4

snapshot/evaluator 现在分别重建：

- idempotency attempt-binding delta；
- L3 `DOMAIN_POSTCONDITION` delta；
- L4 `BENEFICIARY_ACCEPTANCE` delta。

正常 beneficiary REFUSE world 的结果是：

```text
terminal = REFUSE
L3 domain postcondition delta = 1
L4 beneficiary acceptance delta = 0
```

而“此前已到 L3/REFUSE，随后 same-key changed-command”的结果是：

```text
terminal = REFUSE at the new attempt
new L3 delta = 0
new L4 delta = 0
```

所以 terminal match 或 L4 delta 不能再遮蔽 L3 重复。

### 3. 缩窄 truth-isolation 主张

`spawn` 子进程只说明：固定受审 candidate 没有被传入 parent 的 AuthorityNetwork 实例、
private keys、operation log、snapshots 或 evaluator。A2 的 `strategy.py` 源码审计未观察到
fixture/truth 文件读取。

它不提供 filesystem sandbox。root 已证明同 OS 权限 peer 可以读取 hidden fixture；A2 将
其记录为：

`FILESYSTEM_TRUTH_ISOLATION = REFUTED_NOT_CLAIMED`

若未来需要 adversarial filesystem truth isolation，必须引入真实 sandbox、不同 UID/容器、
权限隔离或把 hidden truth 移出 candidate 可读域；仅用 `spawn` 不够。

### 4. 缩窄 anchor 主张

当前 `anchor=EQUIVOCATED` paired world 仍由 host hidden-state detector 触发。它只能证明：

- central detector fixture 能让候选进入 `UNKNOWN`；
- verifier 对 allowlist 内、绑定同一 checkpoint/slot/branch 的 unique issuer 计 quorum；
- duplicate、replay、cross-checkpoint、cross-slot attestation 不增加 quorum。

它不能证明恶意 anchor 会自证 equivocation，也不能证明独立观察者一定能发现所有 fork。
`MALICIOUS_ANCHOR_SELF_PROOF` 明确为 `NOT_CLAIMED`。

## 当前自测

- 13 个原 paired worlds：terminal、attempt binding、L3、L4 均 13/13 match；
- 0 FP，0 FN；
- root 原攻击在 A v1 上仍可复现；
- A2 对同一攻击在新 attempt 返回 REFUSE，之后无 delivery/L3；
- L1/L2/L3/L4-REFUSE 四个 partial-history 变体均通过；
- exact replay 与 allowlisted schema alias：新 L3/L4 delta 均为 0；
- material command/new key 与 environment drift/new key：attempt/L3/L4 delta 均为 1；
- evidence deletion、unauthorized beneficiary signature、self-report、truth flip、function relabel
  回归保留；
- quorum verifier 的 duplicate/replay/cross-checkpoint/cross-slot 攻击保留。

这些全部是同研究者修复后的自测，不是独立证据。root 需要针对 A2 再做新的 mutation。

## 依赖与闭包

A2 不复制 A v1 的完整签名链实现和 13 个 fixtures，而是只读复用并在 manifest 中绑定其精确
SHA-256；A2 覆盖 AuthorityNetwork、evaluator、candidate source、runner、tests、results 和
manifest。依赖 hash 变化时，本次结果失效。

关键输入：

- root attack SHA-256：
  `1e99f17136f4868de724d13c52cb7018c48dc880b18c2cce35ce8ee5d8b9a72f`
- repair harness SHA-256：
  `7b6fe448b16cbeb48b749b76b454c8b3fd10e1669605927b49c28e575cdee653`
- frozen independent audit protocol SHA-256：
  `5eec08681a819d6c1ade908c127baa986da8db689b2f6df8765cf0d83ad7e98f`

## 复现

在本目录运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave007-a2-cache python3 runner.py
PYTHONPYCACHEPREFIX=/tmp/wave007-a2-cache python3 -m unittest -v tests/test_harness.py
```

输出状态必须继续写作 `SAME_RESEARCHER_SELF_TEST_ONLY`，直到新的独立审计完成。
