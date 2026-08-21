# Wave 018 E4 root acceptance

状态：
`LOCAL_SYNTHETIC_E4_EXISTING_COMPOSITION_ACCEPTED / NO LEGAL OR PHYSICAL CLAIM`

## 冻结运行

- pair：`pair-27938968732963036668`
- evidence bundle：`artifacts/pair-27938968732963036668/e4-pair.json`
- bundle file SHA-256：
  `661ba9fd94451e01947e34f0e00ecdf296544e097c232ee2f6a4aa652336237d`
- internal pair SHA-256：
  `cb9ef1ef850b478ea8b9a49e824a3f77e84c76b8b4ab9ae1072b31d46286b3ac`
- E4 run：`e4-89961569582432394765`
- E4 internal bundle SHA-256：
  `96e7fbe5e7cea6645e5d5a73c8b85f813d95cb88f4832e62604da9098494a20e`
- E4 SQLite：
  `artifacts/pair-27938968732963036668/e4-target-ledger.sqlite3`
- E4 SQLite SHA-256：
  `ba90044dbad105f9ed8abc4c5b57fffd410bec096ea06d5291d92d641d741fe3`
- E4 SQLite logical SHA-256：
  `55b5617f0f2441a3f51660dc75d4eb0e807f17624dcc4109a7d8c700f790c9e2`
- REMOVE_ALTERNATIVE run：`e4-77603755675946939900`
- REMOVE_ALTERNATIVE internal bundle SHA-256：
  `a7956ee95ae3631f3761c08b3a1575e32cfa5bc627a2cad975ecc133563683e6`
- REMOVE_ALTERNATIVE SQLite：
  `artifacts/pair-27938968732963036668/remove-alternative-target-ledger.sqlite3`
- REMOVE_ALTERNATIVE SQLite SHA-256：
  `41139cab13f926a5c114e2da6a2fcb558d4cd2a848b5490b5a0ef96ca634ef10`
- REMOVE_ALTERNATIVE SQLite logical SHA-256：
  `c24ad360a8aee763bd06086ad9a34a5de03066c4ba5f8739ff7342edc1b94b51`

## 结果

E4 世界独立重验为：

```text
evidence_valid = true
ExactTaskSuccess = true
TargetStateSatisfied = true
disposition = RECOVERED_VIA_LEGAL_ALTERNATIVE
PrimaryRevokedBeforeCommit = true
BoundedLocalReopen = true
AlternativeActuallyRediscovered = true
FreshOwnerStatusAtCommit = true
DurableSQLiteTargetLedger = true
StandaloneDeleteJournalTarget = true
PhysicalLogicalDatabaseHashBound = true
ExactCE001CoordinatesVerified = true
UniqueExactOccurrence = true
DualAcceptance = true
AlternativeBoundFinality = true
```

REMOVE_ALTERNATIVE 世界独立重验为：

```text
evidence_valid = true
ExactTaskSuccess = false
TargetStateSatisfied = false
AlternativeRemoved = true
DurableTargetUnchanged = true
StandaloneDeleteJournalTarget = true
PhysicalLogicalDatabaseHashBound = true
disposition = BOUNDED_REFUSAL_NO_ALTERNATIVE
```

这支持一个正向有界结论：在该 local-synthetic E4 world 内，不需要假设通爻独占的新机制；
成熟的 revocation、局部 reopen、compensation、rediscovery、owner receipts、fresh status
和 durable idempotent ledger 的组合已经解决受检验问题。组合与收敛本身就是通爻方案的
有效成果。

## Root 审计修正

初版 9/11 浅层检查曾出现两类假绿，未被接受：

1. 名为 TargetOperationLedger 的对象只是进程内字段，不能提供持久 mutation truth。
2. commit-time current 只读取 receipt 自报的 `current=true`，没有向各 owner truth 查询
   最新 head。

当前版改为实际复用 Wave 015 SQLite ledger，并冻结两个独立数据库；Target 在提交前直接
查询 RESOURCE_ALTERNATIVE、RESOURCE_PRIMARY、O_V、O_S、O_P 五个 endpoint，把 status
hashes、bounded reopen、durable receipt/readback 一起绑定到唯一 occurrence。独立 evaluator
不导入 runtime，并从冻结 SQLite 重新验证存储身份、receipt、readback、exact state 和
exact-once 计数。

Root post-final 复核随后再次打开 acceptance：前一 pair 的两个主文件仍是 WAL header，
pair/root hashes 又只绑定主文件，不包含 `-wal/-shm`，所以它们不能称为 standalone frozen
truth。当前正式 pair 不通过删除 WAL companions 修补原文件，而是对运行时 WAL 数据库使用
SQLite backup API 生成新数据库，再切换并直接读取 SQLite header bytes 18/19，要求
`01/01`（rollback/DELETE），要求三个 companion 均不存在，并分别绑定 physical SHA-256
与 logical snapshot SHA-256。测试还实际构造 WAL header、sidecar 和 logical-hash tamper，
确认 evaluator fail closed。

## 攻击与验证

`tests/test_e4_runtime.py` 当前为 `13 passed`，覆盖：

- 九个实际 spawn process 与 primary/alternative 独立性；
- public startup 和 rediscovery 前不可预写 alternative；
- E4 success 的完整 owner/Target/finality chain；
- exact CE-001 的 46 samples、45-minute duration、3kW tolerance、安全、噪声、其他 circuit
  与 deadline；
- durable semantic replay 不产生第二 mutation；
- REMOVE_ALTERNATIVE 降为 bounded refusal 且 durable Target 不变；
- stale primary、no rediscovery、wrong owner key、unbounded reopen；
- controller preselection fail closed；
- bundle content hash；
- evaluator 不导入 runtime。
- SQLite backup 后必须是 DELETE header 的 standalone 单文件；
- WAL header、任一 journal companion、logical hash tamper 均被 evaluator 拒绝。

冻结 bundle 与两个数据库已在新 Python 进程中重新读取，两个 disposition 均再次通过独立
评估。

## 不能推出

- 不证明 `RECOVERED_VIA_LEGAL_ALTERNATIVE` 中 “legal” 的现实法律含义；
- 不证明真实 resource、actuator、meter 或 3kW physical Effect；
- 不证明真人理解、授权、Adoption、Acceptance 或 Settlement；
- 不证明 provider 停更、迁移、许可、锁定和跨组织部署问题已经解决；
- 不证明 E0/E2/E3A/E3B/E6、A0–A5 公平比较或 V1/V2 总问题；
- SQLite HMAC key 与 DB 同权限域，不抵抗恶意同用户/DBA 协调改写。
