# Wave 007 independent audit status

日期：2026-07-29  
状态：`PAUSED_ROOT_RECHECK_COMPLETE`

本文件记录 root 按 `WAVE-007-INDEPENDENT-AUDIT-PROTOCOL.md` 对实现者返回产物的直接 mutation。
实现者自测与 root 攻击分开记录。

## 007-C v1：三项承重攻击成功

候选目录：
`experiments/wave-007-c-access-metered-reliance/`

实现者结果：

- 10/10 tests PASS；
- 15 opaque worlds；
- 同一 EvidenceAPI、Ed25519 验签、binding/freshness/authority checks；
- cost 从 API operation log 重建；
- Pareto frontier 为 Declaration 与 Latest Probe；
- 实现者明确标记 self-tests 不是独立证据。

root 复现原测试 `10/10 PASS` 后，直接运行三个未被原测试拦住的 mutation：

### A. 合法旧 ACTIVE receipt 覆盖当前 REVOKED

把 active world `w7c-50de71` 在 step 7 签发的合法 `ACTIVE` authority status 原样复制到
revoked world `w7c-a76e20` 的 step 8。该 receipt 仍满足 `max_age=1`，但没有绑定 current
authority head/epoch/version。

结果：

| 策略 | 原 revoked world | 注入旧 ACTIVE receipt 后 |
|---|---|---|
| Declaration | `REFUSE` | `RELY` |
| Latest Probe | `REFUSE` | `RELY` |
| Receipt Window | `REFUSE` | `RELY` |
| SLA Recovery | `REFUSE` | `OBSERVED_FAILURE` |

因此“验签 + 一步 freshness + subject/key/status”不能证明当前未撤销。

### B. candidate 清空同进程 raw log

恶意 strategy 先调用正常 `declaration(api)` 得到相同决策，然后执行 `api._log.clear()`。
`run_candidates` 随后读到：

```text
api_operations = 0
total_evidence_cost = 0.0
```

所以当前 operation log 虽然不是按标签收费，却仍由 candidate 所在进程可改，不能作为独立
计费 truth source。

### C. candidate 自报 implementation identity

strategy 可以把返回中的 `implementation_id` 改为任意其他实现。Evaluator 的 `_metrics`
按该字段分组，故实现身份仍是 candidate 自报事实。

## 007-C v1 当前判定

`PARTIAL / REPAIR_REQUIRED`

保留：

- strategy label 本身不再改变相同 operation log 的成本；
- fixture 中 signature、exact evidence binding、evidence deletion、UNKNOWN/REFUSE/ABSENT
  等局部 checks；
- 当前 15 worlds 与权重下的分数可作为这个已知有漏洞实现的描述，不作为安全 reliance 方案。

撤回：

- raw operation log 已经位于 candidate 不可改的独立边界；
- current authority/revocation 得到充分验证；
- Pareto frontier 足以支持当前 G4 方案选择。

修复正在新目录 `experiments/wave-007-c2-access-metered-reliance/` 进行，必须：

- 绑定 trusted request 的 current authority head/epoch/version，拒绝旧 ACTIVE replay；
- 由 candidate 无法取得或改写的 parent broker/process 记录 evidence operations；
- evaluator identity 由 registry/runner 确定，忽略 candidate 自报 identity；
- 直接纳入上述三项 mutation；
- 保留原 C 目录不改，并说明同研究者修复不构成独立证据。

## 其他线

- 007-A opaque Authority：v1 已被 root 攻击缩窄，A2 修复中；
- 007-B paired relation materiality：v1 隔离与 identity 无效，B2 修复中；
- 007-C2 access-metered reliance：修复中。

## 007-A v1：终态正确掩盖 L3 重复，spawn 不等于文件隔离

候选目录：
`experiments/wave-007-a-opaque-authority-harness/`

实现者结果与 root 重跑：

- 17/17 tests PASS；
- 13/13 terminal match、13/13 accepted-effect delta match；
- unique allowlisted witness quorum 能拒绝 duplicate/replay/cross-checkpoint/cross-slot；
- parent-side Authority keys 与 operation log 不直接传入 candidate。

root 攻击脚本：
`audits/wave-007/root_attack_a.py`

### A. partial 后 same-key changed command 到达第二个 L3

构造 beneficiary `REFUSE` world，先用 baseline request preload 到 domain postcondition，再以同一
idempotency key 改 command。由于当前 registry 只在 beneficiary acceptance 后登记，第二次
请求没有在 controller attempt 被拒绝，而是再次经过：

```text
REQUEST_EFFECT_ATTEMPT
REQUEST_DELIVERY
REQUEST_ANCHOR_COMMIT
REQUEST_RECIPIENT_ACK
REQUEST_DOMAIN_POSTCONDITION
REQUEST_BENEFICIARY_DECISION
```

Evaluator 仍返回 `REFUSE / terminal_match=true / accepted-effect delta=0`。这说明它只跟踪 L4
acceptance，没有观察第二个 L3 domain postcondition，因而把中间现实重复藏在正确终态下。

### B. spawn 子进程可以读 hidden fixture

同一 Python、同一 OS 用户权限的 peer process 能直接读取
`fixtures/hidden-worlds.json`，并看到 `expected_terminal`。`spawn` 只隔离进程内存；没有
filesystem sandbox 时，不能声称 untrusted candidate 无法读取 truth。

### C. anchor paired world 的边界

`anchor=EQUIVOCATED` 由 host hidden state 主动构造不一致 witness response 并返回 Unknown。
这可测试 central detector fixture 与 unique quorum verifier，但不是恶意 anchor 在两个隔离
client view 中自证 equivocation 的端到端证据。

### 当前判定

`PARTIAL / REPAIR_REQUIRED`

保留：

- fixed candidate source 当前没有读取 truth 文件；
- process boundary 保护 parent memory、private keys 与 raw log 不被当前 candidate 直接取得；
- unique issuer/checkpoint/slot/branch quorum verifier 的局部 mutation；
- revoked/withdrawn/refused Authority 对当前 fixed chain 的 signed terminal observations；
- L4 acceptance 不能由 controller 自签。

撤回或缩窄：

- same idempotency key + changed bytes 在所有 partial stages 都安全拒绝；
- accepted-effect delta 足以代表 G6 的所有 domain Effect；
- spawn 本身提供 adversarial truth isolation；
- host-driven anchor fixture 证明真实 cross-view equivocation detection。

A2 必须在首次合法 attempt 即绑定 idempotency key，分别跟踪 L3 与 L4 delta，并诚实声明
filesystem threat model。原 A 保留不改。

## 007-B v1：callable closure 泄漏 truth/log，确定性私钥可重建

候选目录：
`experiments/wave-007-b-paired-relation-materiality/`

实现者结果与 root 重跑：

- 24/24 tests PASS；
- paired worlds 使 one-shot 与 explicit bounded reuse 不再共享同一任务行为；
- evidence deletion、duplicate/wrong-purpose authorization、withdrawal 与 self-report 等自测
  均通过；
- local results 能重建 missed legitimate reuse，而不是把保守拒绝都算成功。

root 攻击脚本：
`audits/wave-007/root_attack_b.py`

### A. EvidenceGateway callable closure 泄漏整个 service

Candidate 收到的 `gateway.read_evidence` 是闭包。通过 Python `__closure__` 可取得
`HiddenAuthorityService`，继而直接读取：

```text
reuse_truth = EXPLICIT_BOUNDED_REUSE_AUTHORIZED
relation_evidence = VALID_BOUNDED_REUSE
withdraw_after_first_reuse = true
```

同一路径还能取得 `__operation_log` 并执行 `clear()`；root 实跑把 audit operation count 从
`1` 清为 `0`。

### B. Authority private keys 可由公开固定 seed 重建

`_private_key("LAB-SEEK")` 是导入可用的确定性 helper。root 重建出的 public key 与 contract
登记值完全一致，因此“candidate 不持有 signer”只由当前 candidate source 自律，不是机制
边界。

### C. evaluator identity 仍由 candidate 自报

Root 运行实际 `BOUNDED_RELATION` representation，但传入 `candidate_label="TASK_BOUND"`；
evaluator 随即把它登记为 `TASK_BOUND`，同时 relation constituted/reuse 仍为 true。比较表的
实现身份因此可被 candidate 改写。

### 当前判定

`PARTIAL / REPAIR_REQUIRED`

保留：

- paired-world 设计明确区分 one-shot、bounded authorization 与 contradictory evidence；
- 从签名 bytes 重建 dual ACK/explain-back/proposal/authorization 的局部 evaluator；
- “保守拒绝可能产生 missed legitimate reuse”这一评价维度；
- 当前 fixed candidate 的行为结果，作为已知不隔离实现的合成描述。

撤回：

- candidate 无法访问 truth、keys 或 audit log；
- raw log 是 candidate 不可改的成本来源；
- candidate label 不影响方案身份；
- v1 结果可以作为独立 relation materiality 证据。

B2 必须使用 parent broker/process boundary、运行时随机私钥和 runner-owned implementation
identity；若没有 filesystem sandbox，必须像 A2 一样缩窄威胁模型。原 B 保留不改。

## A2/B2/C2 root 收尾复核

用户要求完成本轮后暂停。Root 没有开启新问题或 Wave 008，只重新执行修复版本的完整测试与
精确攻击回归：

| 修复版本 | Root 复跑 | 前一版攻击在修复边界中的结果 | 当前判定 |
|---|---:|---|---|
| A2 opaque Authority | 17/17 PASS | attempt-time idempotency 阻止 L1/L2/L3/L4 partial 后 same-key changed bytes；L3/L4 分开计量 | `SUPPORTED_SCOPED_ROOT_RECHECKED` |
| B2 paired relation | 20/20 PASS | parent broker 拒绝 truth/log/sign RPC；随机 runtime keys；identity 从 raw operations + runner registry 重建 | `SUPPORTED_SCOPED_ROOT_RECHECKED` |
| C2 access-metered reliance | 15/15 PASS | 旧 ACTIVE receipt 不匹配 current head/epoch；candidate 清日志无效；candidate identity spoof 被忽略 | `SUPPORTED_SCOPED_ROOT_RECHECKED` |

合计 `52/52 PASS`。这里的 `ROOT_RECHECKED` 表示 root 独立执行了完整 suites，并确认先前 root
反例被绑定为回归；A2/B2/C2 仍由原实现者修复，不冒充独立实现或新的 blind evidence。

### 当前可保留结论

- **G2**：在 one-operation world，不自动物化持续关系是充分的安全约束；在明确 bounded
  reuse world，task ACK 或 explain-back 单独不够，dual ACK + dual explain-back + exact
  proposal + dual bounded authorization 才在当前合成任务产生一次合法 reuse。证据矛盾时
  安全拒绝仍计 missed legitimate reuse。
- **G4**：当前 15 个合成 worlds 中 Declaration 与 Latest Probe 位于 Pareto frontier；
  failure frequency/损失变化会翻转选择，不存在普遍 winner。Receipt Window 与 SLA
  Recovery 的当前劣势只限本 fixture。
- **G5/G6/G7**：受信 parent broker、独立随机签名 authority、attempt-time idempotency、
  bytes-bound chain、L3/L4 分离和 unique-witness verifier 能解决当前本地合成 scope；这是
  现有密码学、workflow、broker 与 evaluator 组合的正向方案，不要求新增协议机制。

### 仍然不成立

- 没有 filesystem sandbox 时，spawn/peer process 不能阻止同权限恶意代码读取本地文件；
- A2 anchor world 只是 central hidden-state detector fixture，不证明恶意 anchor 自证；
- root recheck 不是独立实现、blind holdout、现实主体授权、真人 Acceptance 或生产保证；
- HW-C external blind extraction 仍是 `0/11 NOT_STARTED`。

本轮在这里暂停；恢复时先从本文件与 `WAVE-007-PAUSE-HANDOFF.md` 进入，不重新解释已失效的
Wave 006 或 Wave 007 v1 绿灯。
