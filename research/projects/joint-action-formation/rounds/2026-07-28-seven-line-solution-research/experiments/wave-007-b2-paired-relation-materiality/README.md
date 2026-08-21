# Wave 007-B2：paired relation materiality process repair

状态：
`SAME_RESEARCHER_REPAIR_LOCAL_SELF_TEST_COMPLETE_PENDING_ROOT_REAUDIT`

B2 是对 B v1 独立审计失败的修复，不覆盖、不改写原目录，也不把同研究者回归冒充独立证据。

## 为什么 B v1 无效

独立攻击 `audits/wave-007/root_attack_b.py` 实际证明：

1. candidate 拿到的 callable closure 含 `HiddenAuthorityService`，可直接读出 private world
   truth；
2. 同一 closure 可取得 authority 的 mutable operation log，并把日志从 1 条清成 0 条；
3. `_private_key(authority)` 使用公开 deterministic seed，可重建 contract 中完全相同的公钥；
4. `BOUNDED_RELATION` implementation 自报 `TASK_BOUND` 后，evaluator 将其身份错误改成
   `TASK_BOUND`，同时仍记录 relation constituted 与 reuse executed。

因此 B v1 的“候选隔离、日志独立、authority key boundary、implementation identity”主张均
不能保留。B2 只继承 paired-world 问题和证据语义。

## B2 修复

### 父进程 authority broker

`AuthorityBroker` 仅存在于 parent runner：

- private world state、evidence inventory、运行时 Ed25519 signer 与 mutable operation log
  全部保留在 parent memory；
- 每次 run 使用 `Ed25519PrivateKey.generate()` 生成新 signer，不存在 deterministic seed
  或可调用的 `_private_key(authority)`；
- 对外只有固定 RPC allowlist：read、verify、record decision、request reuse、poll withdrawal；
- `get_private_world_state`、`clear_audit_log`、`sign_for_authority` 均返回
  `METHOD_NOT_ALLOWED`；
- runner 只能取得深拷贝 snapshot，清空 snapshot 不改变 broker 内的 authoritative log。

### spawned candidate process

runner 使用独立 PID 启动 `candidate_worker.py`，通过 newline-delimited JSON-RPC 与 parent
broker 交互。candidate 只持有 `JsonRpcEvidenceGateway`；它的方法没有 parent service
closure，也没有 broker/audit handle。

### runner-owned implementation identity

evaluator 从 raw RPC operation log 重建实际 evidence interface，再与 runner 读取的
representation registry 匹配得到 `implementation_id`。runner transcript 中的 identity
字段只是待核对声明；candidate 则可输出任意 `candidate_label`，但只会被记录为
`candidate_claimed_label_ignored`。实测 `BOUNDED_RELATION` 自报 `TASK_BOUND` /
`NO_EVIDENCE`，或事后把 runner identity 字段改成 `TASK_BOUND`，evaluation identity 仍是
`BOUNDED_RELATION`，且后者产生 binding failure。

## paired-world 结果

问题、表示和证据语义保持不变：

- `ONE_OPERATION_ONLY` 与 `EXPLICIT_BOUNDED_REUSE_AUTHORIZED`；
- relation evidence valid 与 missing/contradictory；
- `TASK_BOUND`、`EXPLAIN_BACK`、`BOUNDED_RELATION`、`NO_EVIDENCE`。

主要本地合成结果：

| evaluator world | implementation | constituted | reuse | missed | stale | residual | evidence cost | net value |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ONE / valid | TASK_BOUND | 0 | 0 | 0 | 0 | 0 | 12.120850 | -12.120850 |
| ONE / contradictory | TASK_BOUND | 0 | 0 | 0 | 0 | 0 | 12.120850 | -12.120850 |
| BOUNDED / valid | TASK_BOUND | 0 | 0 | 1 | 0 | 0 | 12.120850 | -52.120850 |
| BOUNDED / valid | EXPLAIN_BACK | 0 | 0 | 1 | 0 | 0 | 20.899658 | -60.899658 |
| BOUNDED / valid | BOUNDED_RELATION | 1 | 1 | 0 | 0 | 0 | 42.264893 | 17.735107 |
| BOUNDED / valid | NO_EVIDENCE | 0 | 0 | 1 | 0 | 0 | 1.000488 | -41.000488 |
| BOUNDED / contradictory | BOUNDED_RELATION | 0 | 0 | 1 | 0 | 0 | 36.208740 | -76.208740 |

本地结果仍只支持以下有界判断：

- one-operation world 中 task-bound evidence 足以避免把一次交付自动升级为持续 relation；
- valid bounded world 中，可观察增量来自 dual unique ACK、dual explain-back、exact
  proposal 与 dual unique bounded authorization，withdrawal 清除该有限权限；
- explain-back 不是 reuse authority；
- no-evidence 的低成本不能跨 paired worlds 解题；
- 授权事实存在而证据缺失时，安全拒绝仍计 `missed legitimate reuse=1`。

## B2 回归攻击

20 项测试覆盖：

- 四项 root 攻击：closure truth leak、mutable log clear、deterministic key reconstruction、
  candidate identity spoof；
- runner identity transcript tamper；
- 三种禁止 RPC 的真实子进程请求；
- parent/worker PID 与 broker/audit handle transfer；
- 两次运行 public keys 不同；
- snapshot 清空不影响 parent log；
- 全部 B v1 证据删除、签名、authority、truth flip、rename、self-report、raw-log cost 与
  withdrawal 攻击。

结果文件不保存随机签名或 public keys，只保存独立重建后的 metrics 与 boolean mutation
结果，因此运行时 keys 每次不同而 `results.json` 仍可确定性复算。

## 诚实的隔离边界

B2 证明的是：

> 当前 candidate module 通过受限 JSON-RPC 运行时，不能通过 gateway closure 取得 parent
> broker memory、signer 或 mutable log。

B2 **没有 filesystem sandbox**。candidate 与 parent 仍是同一用户权限，恶意 candidate
理论上可以读取同权限 workspace 文件，包括 evaluator fixture，也可能利用操作系统允许的其他
同权限进程能力。B2 因此不声称 hostile-code containment，也不把“parent memory 未经 RPC
传输”扩大为“同权限文件不可见”。若后续结论需要抵抗恶意 candidate，必须增加独立 UID、
container/sandbox、只挂载 candidate packet，或 remote authority boundary。

## Provenance

- B v1 independent root attack：
  `audits/wave-007/root_attack_b.py`
- root attack SHA-256：
  `acd60ef55d297e098ed247de8f944359a943e33912a6f67d3efd488f398add9e`
- shared task SHA-256：
  `0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`
- actual-read repair harness SHA-256：
  `7b6fe448b16cbeb48b749b76b454c8b3fd10e1669605927b49c28e575cdee653`
- independent audit protocol SHA-256：
  `5eec08681a819d6c1ade908c127baa986da8db689b2f6df8765cf0d83ad7e98f`

## 运行

```bash
PYTHONPYCACHEPREFIX=/tmp/wave007b2-pycache \
  python3 -W error::ResourceWarning -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/wave007b2-pycache \
  python3 evaluator.py --output results.json
```
