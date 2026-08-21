# Wave 007-A opaque authority harness

状态：`IMPLEMENTED_SELF_TESTED_AWAITING_INDEPENDENT_AUDIT`  
范围：只构建 Wave 007-A 的 G6/G7 最小闭环；不输出 winner，不继承 Wave 006-E 的
`13/13` 结论。

## 它实际检验什么

共享任务仍是 `W6-STERILE-ROUTE-SIMULATION-001`。这个 harness 检验一个有界主张：

> 在固定 operation、purpose、retention 和 E0–E8 任务边界内，候选只能通过独立 Authority
> 的窄 API 请求授权、执行、交付、锚、ACK、postcondition 和 beneficiary decision；evaluator
> 能否仅用 evaluator-only truth、签名证据、effect snapshot 与原始 operation log，区分合法
> world、撤销/退出/拒绝、锚冲突和主体缺失，并正确处理 replay 与 semantic drift。

它不证明现实部署、跨组织安全、长期稳定性、商业净价值或通爻整体协议。所有本目录测试都是
实现者自测；root 按结果前冻结的 `WAVE-007-INDEPENDENT-AUDIT-PROTOCOL.md` 另做 mutation，
才可能产生独立复核结论。

## 隔离与事实来源

- public fixture 只有 opaque token 到 request bytes 的映射；候选进程从不接收 token。
- hidden fixture 由 harness/Authority/evaluator 持有，候选进程不接收 world state、expected
  terminal、display label 或 evaluator。
- 每次候选执行使用 `multiprocessing` 的 `spawn` 新进程。子进程只持有一个 RPC pipe；
  AuthorityNetwork、private key、public registry、operation log 和 effect snapshot 都只留在
  host。
- 各 Authority 在 host 内各自生成并独占 Ed25519 private key。不存在可由公开常量重建私钥
  的 helper；候选自签名不会出现在本次 public registry。
- beneficiary acceptance 只能由 `BENEFICIARY-REVIEWER` 签发；controller 只能签
  attempt/delivery。
- evaluator 不读 strategy label，也不接受候选自报的 `accepted`、confusion、promotion、
  cost 或 net value。
- 成本由 raw operation log 重新计数：public read、Authority request、witness request、
  verification、cache hit、response bytes、披露单元和总协调操作。

这里的隔离模型依赖受信任 host/harness 与 OS 进程隔离；它不是抵抗能够修改 host Python
进程、fixtures 或 evaluator 的本机恶意管理员的密码学证明。

## Paired worlds

所有名称都只是 harness 外层的 opaque token；策略逻辑没有 token 分支。

| 对比 | 正 world | 负/变化 world | evaluator 预期 |
|---|---|---|---|
| holder | `X7-A03` | `X7-A91` | `ACCEPTED / REFUSE` |
| recipient | `X7-B17` | `X7-B64` | `ACCEPTED / REFUSE` |
| beneficiary | `X7-C28` | `X7-C73` | `ACCEPTED / REFUSE` |
| replay/change | `X7-D11` | `X7-D82` | exact `Δeffect=0`；新 key material change `Δeffect=1` |
| alias/drift | `X7-E05` | `X7-E96` | allowlisted alias `Δeffect=0`；environment drift 重新授权并 `Δeffect=1` |
| anchor | `X7-F39` | `X7-F88` | `ACCEPTED / UNKNOWN` |
| closed population | — | `X7-G52` | `ABSENT` |

另有 mutation 单独检验：baseline 已存在时，沿用同一个 idempotency key 却改变 command，
controller 必须返回签名 `REFUSE`，不得产生第二个 effect。

## Quorum 修复

Anchor quorum 的计票单位不是 attestation 条数，而是：

`contract allowlist ∩ signature-valid ∩ same checkpoint ∩ same slot ∩ same branch`

中的 unique issuer。门槛为 2。自测同时运行：

- 两个不同 allowlisted issuer：通过；
- 同一对象重复：不通过；
- 同一 attestation 的深拷贝 replay：不通过；
- 另一个 checkpoint 的合法 attestation：不通过；
- 另一个 slot 的合法 attestation：不通过。

因此这里没有继承 Wave 006-E “重复 attestation 也能形成 quorum”的失真。

## 攻击面与当前自测结果

`runner.py` 运行 13 个 normal worlds 和以下 mutation：

- opaque rename；
- evaluator-only expected terminal flip（复用同一 candidate output，不重跑候选）；
- 删除决定性 ACK；
- 用同一 holder authorization 冒充两个 holder，以及只保留两份 replayed ACK；
- 用 controller attempt 冒充 beneficiary acceptance；
- 注入 candidate 自报 accepted/confusion/cost/net value；
- strategy function relabel；
- command、purpose、idempotency key、environment bytes rebinding；
- same idempotency key + changed command；
- operation-log 删除、增加和重排后重算成本；
- duplicate、replay、cross-checkpoint、cross-slot attestation。

本地自测快照：13/13 terminal match，13/13 effect delta match，0 FP，0 FN；terminal 保留为
`8 ACCEPTED / 3 REFUSE / 1 UNKNOWN / 1 ABSENT`。这是回归结果，不是独立证据。

## 输入谱系

- 开工交接时 repair packet 的旧 SHA-256：
  `934e0fb834577530ce523b79476a9a4bbaa286ac91f14abb012fd0bd0a54f212`
- 开工后 root 因 Wave 006-E duplicate-vote 攻击更新 repair packet；本实现实际绑定的新
  SHA-256：
  `7b6fe448b16cbeb48b749b76b454c8b3fd10e1669605927b49c28e575cdee653`
- 结果前冻结的 independent audit protocol SHA-256：
  `5eec08681a819d6c1ade908c127baa986da8db689b2f6df8765cf0d83ad7e98f`
- shared task SHA-256：
  `0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3`

这不是“命中旧冻结 hash”；manifest 明确记录版本变化与实际执行输入。

## 复现

在本目录运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/wave007-pycache python3 runner.py
PYTHONPYCACHEPREFIX=/tmp/wave007-pycache python3 -m unittest -v tests/test_harness.py
```

macOS 系统 Python 若无 `PYTHONPYCACHEPREFIX`，可能尝试在受限的
`~/Library/Caches/com.apple.python` 写缓存；该环境问题不影响实验语义。

## 文件

- `fixtures/public-requests.json`：候选可见 request bytes；
- `fixtures/hidden-worlds.json`：Authority/evaluator-only world truth；
- `protocol.py`：canonicalization、allowlisted alias、签名与验证；
- `authorities.py`：独立 domain state、key ownership、idempotency 与 quorum；
- `strategy.py`：只使用 RPC facade 的候选；
- `evaluator.py`：签名链、truth、effect 和 log 重建；
- `runner.py`：spawn 隔离、paired world 运行与 mutation；
- `tests/test_harness.py`：实现者回归；
- `results.json`：可检查的稳定摘要；
- `manifest.json`：输入/产物 hash 与运行边界。
