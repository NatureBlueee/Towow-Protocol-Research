# Cohort 003 G5-final

日期：2026-07-30  
状态：`COMPLETE LOCAL SYNTHETIC COMPONENT MODEL / CONTRACT REOPEN CANDIDATE /
NO FORMAL PROMOTION`

## 结论

CE-001 的 G5 Authority/race/fence module 已在限定目录内形成可运行闭环。与 cohort 002
不同，本轮的 U 路径没有由 controller 填 `CORRECT`；U/D/P 都实际调用 owner subprocess
和 target subprocess。fence 由 target 自己比较并持久化，Saga 也实际执行
`ENERGIZE → DEENERGIZE → target readback OFF`，不是记录 compensation intent。

当前最窄结论是：

```text
G5_LOCAL_COMPONENT_MODEL = POSITIVE_SCOPED
OWNER_NATIVE_EXACT_BINDING = EXECUTED
TARGET_SIDE_FENCE = EXECUTED
SAGA_TARGET_COMPENSATION_AND_READBACK = EXECUTED
REAL_POLICY_PRODUCTS = NOT_RUN
FULL_CE001_AUTHORITY_CLOSURE = NOT_ESTABLISHED
FORMAL_STATUS_CHANGE = NONE
```

这轮没有证明真实法律 Authority、真实供电 Effect/Acceptance、跨故障域线性一致性或新机制
必要性。

## 三名内部 Agent

本次按 `COMMON.md` 实际建立了三个内部 Agent：

- `/root/g5_agent_a`：只读独立重建 CE-001 G5 接口、不变量、测试矩阵和合同缺口；
- `/root/g5_agent_b`：只写
  `experiments/wave-012-ce001-power-restoration/g5-authority/`，实现 owner/target worker、
  harness、runner、tests 和 artifacts；
- `/root/g5_agent_c`：不读取 A/B 的预期结论，先制定 truth-copy、alias、substitution、
  fence、Saga、Standing 和 migration 攻击，再只读复跑。

三者共享模型家族、仓库和研究传统，提供的是职责与失败路径隔离，不是三个现实机构或外部
独立复现。最终判断由根会话完成。

## 实际实现

### Authority 与 exact binding

- 三个 stratum：`U / LAWFULLY_UNIFIED`、`D / EXACT_DELEGATION`、
  `P / PLURAL_INDEPENDENT`；
- owner-native signed outcome 绑定 exact
  `object_id / object_version / scope / expiry / material closure / owner head`；
- frozen CE-001 Q 由 owner 与 target 各自重新校验。controller 构造 `Q@v2` 并重算
  closure，仍被双方分类为 `SUBSTITUTION_INVALID_FROZEN_Q`；
- 5 个 exact binding attack 覆盖 object、version、scope、expiry binding 和 runtime
  expiry；owner 与 target 全部拒绝，target transition 为 0。

### revoke race 与 target fence

运行矩阵为：

```text
3 Authority strata × 4 revoke boundaries = 12 race cells
boundaries = read / sign / reserve / execute
```

- read/sign 撤销通过 owner head/currentness 阻断；
- reserve 后旧 executor 真正抵达 strict target，3/3 返回
  `STALE_FENCE_REJECTED`，target 保持 `OFF / 0 transition`；
- strict、ignore-fence、restart-loses-fence 三个 profile 均实际运行。后两者产生的 stale
  Effect 被保留为 failure injection，不被写成成功；
- 伪造 controller `correct=true` 不能改变 strict target 的拒绝与 readback。

### Saga、Standing 与 migration

- execute 后撤销的 3 个 stratum 都先有 target-native `ENERGIZED`，随后由 target 实际
  执行 `DEENERGIZED`，最终 readback 为 `OFF`，transition 历史保持
  `[ENERGIZE, DEENERGIZE]`；
- 原始供电 Effect 没有被历史改写。补偿只证明后续 target transition，不把 Saga 宣称为
  原子事务；
- `UNRESOLVED` Standing 在四个 owner 侧均返回
  `STANDING_NOT_EXECUTION_ELIGIBLE`，target 侧返回 `TARGET_REJECTED_STANDING`，
  `OFF / 0 transition`；
- migration capsule 核验 schema、exact operation、owner heads/receipt hashes、fence、
  coordinator epoch、Standing、真实 target readback hash 和 G5 范围内 Acceptance 状态；
- 7 类 forged migration mutation 均为 `MIGRATION_LOSS_DETECTED`；
- takeover 后 target 持久 coordinator epoch 2；旧 runtime epoch 1 返回
  `STALE_COORDINATOR_EPOCH_REJECTED`，新 runtime epoch 2 的同 operation replay 返回
  `IDEMPOTENT_REPLAY`，最终只有 1 个 Effect transition。

## 运行与数字

执行命令：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g5-authority

PYTHONPYCACHEPREFIX=/tmp/ce001-g5-pyc \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/ce001-g5-pyc \
  python3 runner.py --check
```

最终证据：

- B：`11/11` tests pass；runner `COMPLETE_LOCAL_COMPONENT_MODEL`；
- C：独立串行复跑 `11/11`，40.052 秒；原三项攻击和追加 fence/substitution 攻击均被
  target/owner 原生状态区分；
- root：最终串行复跑 `11/11`，90.948 秒；
- artifacts：`14/14` validations、`12/12` race cells、`297` raw trace events；
- `3/3` execute-boundary compensation target transitions；
- `5/5` exact binding attacks fail closed；
- results SHA-256：
  `e6de969dbcfcfe3f5b2ed6eb54c867b0fe32503a2531e9723240f8abe413a2d2`；
- raw trace SHA-256：
  `d31206f3b217fbac9a7c0b7abd3668b936fd8b30b58984fd2886e1c1c6227abb`；
- manifest SHA-256：
  `5680c2821c29fada54e9331ce608455396636dfb6152687910ee4a115326f98f`。

本地 subprocess 在并行复跑时出现明显资源竞争；同一 suite 在最终 root 串行运行耗时
90.948 秒。这不改变语义结果，但说明当前 harness 不是低成本高并发基础设施。

## 红灯历史

1. 首次测试为 `8/9`。反 truth-copy 测试用字符串 `expected` 搜索完整 trace，误伤合法的
   optimistic-concurrency 字段 `expected_head`。修复为递归检查精确禁用键，并明确允许
   `expected_head`。private-label canary 当前只证明 label 不进入 material decision
   projection，不支持进程级 blind isolation。
2. 在第一次 `10/10` 绿灯后，C 实际击穿三条伪闭合路径：
   - `UNRESOLVED` Standing 仍可执行；
   - controller 能用自建 config 把 `Q@v2` 变成 owner/target 的 expected truth；
   - forged migration schema/head/hash/fence/readback/Acceptance 仍被接收。
   三项都已形成定向回归并由 C 用原攻击重放通过。
3. root 首次直接运行 `compileall` 时，macOS 默认 Python cache 路径被 sandbox 拒绝；改用
   `PYTHONPYCACHEPREFIX=/tmp/ce001-g5-root-pyc` 后 compile、JSON 解析与 hash 校验通过。
   这是执行环境红灯，不是 Authority 语义失败。

完整记录见 G5 模块内 `FAILURE_HISTORY.md`。

## 产品执行真值

```text
LOCAL_OWNER_AUTHORITY_SERVICE = RUN
LOCAL_TARGET_FENCE_SERVICE = RUN
OPA = NOT_RUN
Cedar = NOT_RUN
OpenFGA = NOT_RUN
XACML = NOT_RUN
```

没有用 shape fixture、同名 adapter 或 schema conformance 冒充任何真实产品运行，也没有
联网安装产品。

## CONTRACT_REOPEN_CANDIDATE

当前 CE-001 contract 不足以唯一决定以下口径，因此本模块只给出有界实现，不反向改写合同：

1. 八个 case 没有冻结到 U/D/P 的唯一 stratum 映射，D 的具体分母尤其未定义；
2. 没有冻结每个 stage 的 required-right owner closure，以及 revoke 的 effective /
   published / observed 顺序；
3. 供电历史 Effect 物理上不可撤销。`DEENERGIZE` 只能改变未来 target state，不能把已发生
   Effect 或 unsafe 历史改写为 0；
4. Standing 的 truth owner、affected-party set、jurisdiction、adjudicator 和 stage effect
   未冻结；
5. migration capsule 必填字段和 material/non-material loss oracle 未冻结；
6. owner-native outcome vocabulary 及其到 `CorrectResolution` 的映射未冻结；
7. U 的同一 Principal 控制不自动等于所有 target 位于同一事务/一致性域。

这些缺口阻止把本轮提升为“完整 CE-001 Authority 合同已通过”，但不否定当前 local
component model 对 race/fence/compensation 失败的判别力。

## 能支持、不能支持与下一接口

能支持：

- 在冻结 CE-001 Q 的本地 cooperative subprocess model 内，U/D/P、exact owner binding、
  四边界 revoke、target fence、实际 Saga compensation、Standing fail-closed 和 migration
  loss 可以被执行、readback 和攻击；
- 成熟 owner receipt、conditional reservation、monotonic fence、Saga、Standing gate 和
  migration capsule 组合仍是正向解决路径，没有出现新协议必要性证据。

不能支持：

- 真人 Principal 理解、授权、拒绝或 Acceptance；
- 真实法律委托、真实 venue/circuit/battery Effect；
- OPA/Cedar/OpenFGA/XACML 产品能力或比较；
- 跨机器/故障域线性一致性、生产可靠性或现实成本赢家；
- 完整 CE-001 的 G1–G7 episode、正式机制晋升或 novel residual；
- private-label 的真实进程级 blind isolation。

给相邻线的最小接口应为：

```text
G5 execution gate
  = exact operation closure
  + owner-native receipts/current heads
  + stratum/delegation disposition
  + reservation/fence/coordinator epoch
  + Standing disposition
  + target transition/readback
  + invalidated refs / reopen reason / migration loss
```

G6 只依据 target-native transition/readback 判断 Effect；G7 依据 invalidated refs、
coordinator epoch 和 migration loss 恢复。二者都不能反向把 G5 的 Authority、Standing
或 compensation 晋升为成功。下一次若继续，应先由根合同冻结 case→stratum、required
rights、Standing owner/jurisdiction 和 migration capsule contract，再把一个真实安装的
policy product 接入同一 owner/target API；在产品实际运行前继续保持 `NOT_RUN`。
