# Cohort 003 G5 CE-001 根红灯修复

日期：2026-07-30  
状态：`COMPLETE LOCAL SYNTHETIC COMPONENT MODEL / POSITIVE_SCOPED /
NO FORMAL PROMOTION`

## 结论

首轮 G5 的根红灯已经在本地、可信 bootstrap、可靠 owner-event ingest、cooperative
subprocess 与 shared durable store 的限定范围内修复：

```text
TARGET_CONSUMES_CURRENT_SIGNED_OWNER_RECEIPTS = EXECUTED
OWNER_HEAD_AND_RESOURCE_FENCE_CHANNEL = EXECUTED
U_D_P_TOPOLOGY_CLOSURES = EXECUTED
TARGET_NATIVE_NEGATIVE_GATES = 14/14
RACE_MATRIX_NATIVE_RESOLUTION = 12/12
SAGA_TARGET_TRANSITION_AND_READBACK = 3/3
SIGNED_TAKEOVER_LEASE_PROCESS_RESTART = EXECUTED
CROSS_FAILURE_DOMAIN_MIGRATION = NOT_RUN
OPA / Cedar / OpenFGA / XACML = NOT_RUN
FULL_CE001_AUTHORITY_CLOSURE = NOT_ESTABLISHED
FORMAL_STATUS_CHANGE = NONE
```

这轮修复不再把 controller 的顺序、`authority_allowed`、裸 fence、配置标签、Saga action
记录或 coordinator 自报 epoch 当作 Authority/recovery truth。

## 实际 A/B/C

- A：`/root/g5_fix_a`，只读重建 target enforcement、Authority truth、U/D/P topology、
  owner-head/resource-fence 命名空间与 migration 证据边界；
- B：`/root/g5_fix_b`，只写
  `experiments/wave-012-ce001-power-restoration/g5-authority/`，实现 owner/channel/target、
  race、攻击、migration、tests 与 artifacts；
- C：`/root/g5_fix_c_review`，不修改仓库，先击穿首轮和 B 的第一次 migration 修复，再对
  第二次修复做独立负例与 PID/trace 复跑。

最初建立的 `/root/g5_fix_c` 在开始研究前被工具安全过滤器中止，没有产生攻击结果，也没有
被计作 C 证据；随后重新建立的 `/root/g5_fix_c_review` 承担了完整 C 职责。

A/B/C 共享模型家族、仓库和研究传统，只提供职责与失败路径隔离，不构成外部实验室复现。
最终判断由本主会话负责。

## A：问题重建

A 对首轮 v1 直接实测：

1. 完全不启动 owner process，不提供任何 owner receipt，fresh target 仍可裸
   `EXECUTE` 并返回 `ENERGIZED`；
2. controller 裸发 `ADVANCE_FENCE=999`，target 返回 `FENCE_ADVANCED`；
3. receipt verifier 信任 receipt 自带 public key，没有 target 的 out-of-band trust
   anchor；
4. D/P 的 revoke 使用 O_V head，reservation 使用 O_R fence，controller 却把两个独立
   counter 的相同整数当成同一全局 epoch；
5. U/D/P 的差异主要来自 operation/config 标签，D 没有可验证的 exact delegation closure；
6. migration 只是新 process 复用同一 JSON store，所谓旧 runtime replay 不是旧 source
   PID 的实际重启与重放。

A 因此冻结的 target-native gate 顺序是：

```text
canonical trusted topology
→ trusted channel/owner keys
→ signed current Authority snapshot
→ exact required-owner set
→ signed EXECUTE_CHECK receipts
→ exact Q/object/revision/scope/expiry/Standing binding
→ current owner-head vector
→ signed resource reservation/fence
→ exact coordinator epoch
→ idempotency
→ target transition/readback
```

## B：实现

### Authority channel 与 target truth

新增独立 `workers/authority_channel.py`。owner receipt 由 channel 对预置 owner keys 验签
后单调 ingest；target 再对预置 channel key 验证 signed snapshot。controller 可以搬运
bytes，不能裸写结论。

strict target 的 `ENERGIZE` 实际消费并检查：

- canonical U/D/P topology closure；
- exact trusted owner set、owner keys 与 channel key；
- current signed channel snapshot；
- 每个 required owner 的 current signed `EXECUTE_CHECK` receipt；
- resource owner 的 signed reservation receipt；
- `q_id / q_version / object_id / object_revision / scope / expiry`；
- material operation closure、`Standing=ADJUDICATED_CURRENT`；
- owner-head vector、resource fence 与 exact coordinator epoch。

owner head 和 resource fence 是不同字段、不同 issuer、不同命名空间，不再跨 owner 比较裸
整数。

### U / D / P topology

| Stratum | Target trusted closure | Required acts |
|---|---|---|
| U | `UNIFIED_PRINCIPAL_ACT` | 一个 `O_UNIFIED` 对 Q/Venue/Resource/Safety 四个角色的 act |
| D | `EXACT_DELEGATED_ACT` | O_Q/O_V/O_R/O_S 对固定 `C_COORDINATOR` 的 exact delegated acts |
| P | `DIRECT_OWNER_ACT` | O_Q/O_V/O_R/O_S 各自直接 act，不发生 Authority transfer |

三者复用 verifier 代码，但 topology closure、required owners、role owners 与 delegatee
不同。operation 的 stratum relabel 不能选择或证明 target topology。这里的 topology/key
仍是可信 bootstrap 输入，不是现实 lawful ownership 证明。

### target-native 负例

最终 14 个 attack 全部由 target/channel 原生拒绝，且各自 target transition 为 0：

```text
NO_OWNER_RECEIPTS
NAKED_FENCE_INJECTION
POST_CHECK_REVOKE
WRONG_OWNER
STALE_HEAD
CHANGED_Q
CHANGED_OBJECT_ID
CHANGED_OBJECT_REVISION
CHANGED_SCOPE
CHANGED_EXPIRY
RUNTIME_EXPIRED
RELABELED_TOPOLOGY
FORGED_RECEIPT
ACTIVE_SNAPSHOT_COMPENSATION
```

其中 post-check revoke 不是 controller 填一个新 head：owner 签名新 head/status，channel
ingest 后签发新 snapshot，target 再以该 snapshot 拒绝旧 execute receipts。

### Saga

三个 execute-boundary case 都实际产生：

```text
target ENERGIZE
→ signed owner Authority loss
→ signed channel snapshot
→ target DEENERGIZE
→ target readback OFF
```

最终 transition history 为 `[ENERGIZE, DEENERGIZE]`。只发 compensation intent，或在
snapshot 仍全部 ACTIVE 时发 `DEENERGIZE`，target 返回
`TARGET_REJECTED_COMPENSATION_WITHOUT_AUTHORITY_LOSS`。

### Migration / process restart

C 在 B 第一次修复后又发现两条红灯：

1. trace 中 `OLD_RUNTIME_REPLAY` 实际仍由 restored target PID 执行，旧 source PID 已关闭；
2. migration capsule 没有 coordinator epoch 的可信来源。与当前 store hash 一致但
   `coordinator_epoch=999` 的无签名 capsule仍可 restore。

B 的第二次修复把 coordinator epoch 放入 authority-channel durable state：

- `SNAPSHOT` 不再接受 caller 指定的 epoch；
- channel 只签发单调 `+1`、绑定 exact operation/topology/source-state/runtime scope/
  Acceptance 的 takeover lease；
- target `RESTORE` 对 trusted channel key 验签；
- target execute 只接受 exact current epoch，不接受大于 current 的自报 epoch；
- restore 后实际启动第三个 `old-source-restarted` process，由该 PID 用 epoch 1 replay。

冻结 artifact 的 PID 为：

```text
source runtime             = 84089
restored target runtime    = 84090
old-source-restarted       = 84091
```

raw trace 中 `ACTUAL_OLD_SOURCE_RESTARTED_REPLAY` 的 service PID 与 response target PID
都是 `84091`，不是 restored target `84090`，返回
`STALE_COORDINATOR_EPOCH_REJECTED`。restored target 的 epoch 2 replay 返回
`IDEMPOTENT_REPLAY`，最终只有 1 次 Effect transition。

定向 migration 负例：

```text
controller request epoch 999 lease → TAKEOVER_EPOCH_NOT_NEXT
tampered signed lease epoch 999    → TARGET_REJECTED_FORGED_TAKEOVER_LEASE
unsigned lease                     → TARGET_REJECTED_FORGED_TAKEOVER_LEASE
execute self-report epoch 999      → UNISSUED_COORDINATOR_EPOCH_REJECTED
old lease reuse                    → MIGRATION_LOSS_DETECTED
```

这仍只证明三个本地 process 对同一个 durable store 的
`SHARED_DURABLE_STORE_PROCESS_RESTART`。跨机器、跨 region、store failure、并发多副本
takeover 和其他故障域继续是 `NOT_RUN`。

## 最终复跑

主会话：

```bash
PYTHONPYCACHEPREFIX=/tmp/ce001-g5-root-final-pyc \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/ce001-g5-root-final-pyc \
  python3 runner.py --check
```

结果：

- unittest：`13/13 PASS`，20.365 秒；
- runner：`COMPLETE_LOCAL_COMPONENT_MODEL`；
- race：`12/12` native resolution；
- target-native attacks：`14/14` 拒绝、0 transition；
- Saga：`3/3` target-native compensation/readback；
- validations：`13/13 true`；
- raw trace：`1232` events；
- compileall、全部 JSON/JSONL 解析通过。

独立 C：

- 全套 unittest：`13/13 PASS`，20.704 秒；
- 定向 run 的 source/restored/old-source-restarted PID 为
  `84200 / 84201 / 84202`；
- old-source-restarted `84202` 自己返回
  `STALE_COORDINATOR_EPOCH_REJECTED`；
- high-epoch、unsigned/tampered lease、stale lease、duplicate Effect 攻击均被预期 gate
  区分，最终 `transition_count=1`、`duplicate_effect=false`。

## 保存的证据

`g5-authority/artifacts/` 保存 input、public key/fingerprint、process PID inventory、raw
trace、results 与 manifest。private key 没有复制到 artifacts。

冻结 hash：

| Artifact | SHA-256 |
|---|---|
| `input.json` | `209c876cb0baf1b75b44e597c3857a8d240830bb00f67f8b4cf8652375a61270` |
| `public-keys.json` | `d51344f827a68142b2f87ba58510caaf3eeaea0c91035942e9f6db75a15a5240` |
| `process-inventory.json` | `b19404edb0f93c6a97cff1b168f8167774924d77d8aa1456577d7ca50bcda2dd` |
| `raw-trace.jsonl` | `6bb8ba2d1803340a01a22c273c44c29e1347fec2c62b80bdec794e45bff09905` |
| `results.json` | `06191a35dd23671b5cdf83d37c8adbeb71f2b41315b242bd4d8abd5470434fc8` |
| `manifest.json` | `ea6a6d2cd9f0dc365cad9c16c130d106b94e46140a97bc32bd0ba30b9d7126d5` |

主会话与 C 均复算：manifest `5/5` artifact hashes、`12/12` source hashes 匹配；
process inventory 为 176 records / 176 unique PIDs；public-key evidence 为 143 records，
只含 public key 与 fingerprint；artifact 扫描没有 private PEM、secret 或 seed material。

## 能支持与不能支持

能支持：

- 在可信 bootstrap 与可靠 owner-event ingest 的本地 cooperative process model 内，
  target 可以实际验证 current signed owner receipts、exact operation、Standing、owner
  heads、resource fence 和 signed coordinator takeover lease；
- U/D/P 的拓扑差异不再由 operation 标签自证；
- post-check revoke、wrong owner、stale head、changed Q/object/scope/revision/expiry、
  forged receipt 与 controller fence/epoch 注入能够在 target-native gate fail closed；
- Saga compensation 与 shared-store process restart 可以由真实 PID、transition 和
  readback 复算。

不能支持：

- 现实 Principal 的理解、认领、拒绝或 lawful Authority；
- trusted bootstrap 本身的合法性；
- 恶意 controller/transport 阻断 revoke 到 channel；可靠 ingest 仍是承重假设；
- 真实供电 Effect、真人 Acceptance、Settlement 或生产可靠性；
- 跨故障域 migration、线性一致性或恶意同机写者威胁；
- OPA/Cedar/OpenFGA/XACML 产品执行或比较；
- 完整 CE-001 G1→G7 episode、正式机制晋升或新机制必要性。

## 仍需合同重开/冻结的接口

若下一轮继续，根合同仍需明确：

- 八个 case 到 U/D/P 的唯一映射；
- 每个 stage 的 required-right closure、真实 trust bootstrap owner 与 key rotation；
- revoke 的 effective/published/ingested/observed 顺序及 withholding threat；
- Standing owner、jurisdiction 与 compensation Authority；
- coordinator lease 的现实签发主体与跨故障域 durable/consensus 语义。

在这些输入被冻结并由现实 owner/product/failure domain 运行前，本轮保持
`POSITIVE_SCOPED LOCAL COMPONENT MODEL`，不把局部绿灯晋升为完整 Authority closure。
