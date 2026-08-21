# Researcher B — cross-owner race and target-fence discriminator

状态：`LOCAL SYNTHETIC PROTOTYPE / NOT A PRODUCT COMPARISON / NO FORMAL PROMOTION`

这个子目录只回答一个窄问题：四个独立 Authority owner 没有共同事务管理器时，顺序读取、
短期稳定承诺、2PC-like hold、saga/compensation 和真实统一中心分别能保证什么；以及
fencing token 只有在 target 实际执行单调比较时才阻止旧 executor。

它不实现或宣称 canonical IR，不修改 `NOW.md`、`PROGRAM.md`、LineContract 或正式状态。

## 实际实现

- 四个 owner 分别运行在独立 Python 子进程：
  `request_owner / budget_owner / supplier_owner / resource_owner`。
- 每个进程拥有独立 JSON store、私钥和公钥。controller 只读取公钥并验证 owner-native
  response；私钥不进入 controller。标准库实现的 textbook-RSA 只用于本地隔离演示，
  **不是生产密码学**。
- owner 可以原生返回 `ACTIVE / EXPLICIT_REJECT / REVOKED`，也可以 outage 或签发 forked
  heads。响应保留 `native_outcome / native_error / model_version / freshness / head /
  branch`，方法没有预读 `ALLOW/REJECT/UNKNOWN/DEFER` oracle。
- race 可在每个 `read / re-read / sign / reserve / execute` 边界之后注入。fixture 列出
  14 个精确 injection points。
- target 支持四种 fence profile：
  durable global enforcement、ignore、restart-loss、cross-region local reorder。
- runner 输出 JSON trace、owner PID/store/key fingerprint、native response、race 位置、
  Effect readback、oracle-at-execute 与 metrics。

## 五种 coordination 路径的精确边界

| 路径 | 本地模型中的能力 | 明确不声称 |
|---|---|---|
| `no_common_transaction` | 顺序 read/re-read/sign/reserve | 多次重读不是跨 Authority 原子快照；reserve 后 revoke 可产生 unsafe Effect |
| `bounded_lease_confirm` | owner 明确签发短期稳定 lease，lease 内 revoke 被延后 | simultaneous snapshot；owner 没有作稳定承诺时不能凭 controller 生成 lease |
| `two_phase_hold` | 四 owner prepare/hold 后再 confirm | 无阻塞、无恢复成本或 fault-tolerant atomic commit；coordinator crash 会留下四个 hold |
| `saga_compensation` | unsafe Effect 后可记录补偿 | 原子回滚；compensation 可以失败，也不能证明历史 Effect 未发生 |
| `unified_center` | 仅在一个 Principal 真正拥有全部 Authority、状态和 Effect 都在同一一致性域时单事务闭合 | 同账号/API/数据库权限等于统一 Authority；外部 non-delegable right 可被中心吸收 |

真实统一中心完整解决是正结果。`unified_center` 在独立 owner topology 中直接返回
`NOT_APPLICABLE_EXTERNAL_NON_DELEGABLE_RIGHT`，不会用技术权限伪造规范 Authority。

## 运行

从本目录执行：

```bash
python3 -m unittest discover -s tests -v
python3 runner.py --strategy no_common_transaction \
  --race-boundary reserve:resource_owner \
  --race-owner budget_owner \
  --race-action revoke
python3 runner.py --strategy bounded_lease_confirm \
  --race-boundary reserve:resource_owner \
  --race-owner budget_owner
python3 runner.py --strategy two_phase_hold --crash-after-prepare
python3 runner.py --strategy saga_compensation \
  --race-boundary reserve:resource_owner \
  --race-owner budget_owner
python3 runner.py --strategy unified_center --authority-topology unified
python3 runner.py --fence-probe enforce
python3 runner.py --fence-probe ignore
python3 runner.py --fence-probe restart_loss
python3 runner.py --fence-probe cross_region_reorder
```

完整 boundary matrix：

```bash
python3 runner.py --matrix --output outputs/race-matrix.json
```

matrix 是本地 synthetic replay，不是统计分母或产品可靠性结果。

## 指标解释

- `unsafe_effects`：target 接受 Effect 时，评测侧 owner snapshot 已有 effective
  revoke/reject/outage/fork。
- `residual_unsafe_effects`：扣除成功 compensation 后仍存在的 unsafe Effect。即使 saga
  将它降到零，`unsafe_effects` 仍保留历史事实。
- `race_deferred`：owner 自己先前签发的 bounded lease/prepare hold 延后 revoke；这不是
  controller 吞掉 owner 拒绝权。
- `blocked_owner_holds`：2PC-like coordinator crash 留下的阻塞。
- `stale_effect_observed`：旧 epoch 真实到达 target 且被接受；不是 ledger 中是否存在 token。

## 已知限制

- owner、Authority、拒绝和 Effect 全部是本地合成，不是真人/组织/法律事实。
- 四个 owner 运行于同一主机和用户权限域；独立进程/store/key 不等于抵抗同 UID 恶意进程。
- 本实现没有接入 OPA、Cedar、OpenFGA、XACML 或 CLM，不能用于产品优劣比较；这些均为
  `NOT_RUN`。
- lease/hold 是 owner service 明确执行的 synthetic promise，不能外推为跨企业现实可用性。
- target 是本地模型；没有真实设备、供应商门户、人工流程、Acceptance 或 Settlement。
- runner 的 direct store snapshot 只属于 evaluator truth，不暴露给 strategy；它仍是同一
  authoring stream 的结构分离，不是独立机构复核。
