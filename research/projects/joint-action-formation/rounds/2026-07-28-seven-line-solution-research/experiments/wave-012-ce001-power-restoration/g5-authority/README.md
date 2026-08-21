# CE-001 G5 Authority / race / fence module

状态：`LOCAL SYNTHETIC COMPONENT MODEL`。本目录不改变 CE-001 contract、Problem、
LineContract、MechanismProfile 或正式研究状态。

## target-native Authority gate

strict target 不接受 controller 的 `authority_allowed`、`correct`、裸 fence 或裸
coordinator epoch。`ENERGIZE` 必须同时消费并验证：

- target bootstrap trust anchor 中 canonical U/D/P topology closure、channel public key
  和 exact owner public keys；
- authority channel 的 current signed snapshot；
- exact required-owner set 的 current signed `EXECUTE_CHECK` receipts；
- resource owner 的 signed reservation receipt；
- 独立的 `q_id / q_version / object_id / object_revision / scope / expiry`、material
  operation closure 与 `Standing=ADJUDICATED_CURRENT`；
- owner head 与 resource reservation fence 两个不同的命名空间。

U、D、P 复用相同 verifier 代码，但闭包不同：U 是一个 owner 对四个角色的 unified
principal act；D 是四个 owner 对固定 delegatee 的 exact delegated acts；P 是四个 owner
的 direct acts。operation 里的 stratum 标签不能改变 target trusted topology；relabel
攻击会被 target-native gate 拒绝。

这里仍明确假设 `TRUSTED_BOOTSTRAP_CONFIGURATION_ASSUMED`。key/receipt 只证明 frozen
topology 内 exact bytes 的 act，不证明现实 lawful ownership。channel currentness还依赖
所有 owner event 被可靠 ingest；恶意 controller 若能阻断 revoke 到 channel，当前本地模型
没有解决该 availability/withholding 威胁，不能据此声称全局 currentness。

## race、fence 与 Saga

- `U/D/P × read/sign/reserve/execute = 12` race cells 均经过 owner process、
  authority-channel process 与 target process。
- post-check revoke 由 owner 签名新 head，channel monotonic ingest 后签发新 snapshot；
  target 以新 snapshot 拒绝旧 execute receipts。
- resource fence 只能由 resource-owner receipt 推进；裸
  `ADVANCE_FENCE=999` 返回 `TARGET_REJECTED_NAKED_FENCE_INJECTION`。
- wrong owner、stale active head、changed Q、changed object id/revision/scope/expiry、
  runtime expiry、topology relabel、forged receipt、无 receipt 与 active-snapshot
  compensation 均为 target-native 负例。
- Saga 先由 strict target 实际 `ENERGIZE`；owner revoke 到达 channel 后，target 才允许
  `DEENERGIZE`，最终 readback 必须 `OFF`。只给 compensation action/intent、但 snapshot
  仍全 ACTIVE 时会拒绝。
- `ignore_fence` 与 `restart_loses_fence` 是故意不安全的 failure profiles；其中 stale
  Effect 只作为红灯，不计成功。

## migration scope

E6 的 coordinator epoch 由 authority channel 持久拥有；`SNAPSHOT` 不接受 controller
提供的 epoch。channel 只签发单调 `+1` 的 takeover lease，并把 exact
operation/topology、source-state hash、Authority snapshot、Acceptance 与 runtime scope
绑定进签名 capsule。target 只接受 trusted channel key 下的 exact lease，且 `EXECUTE`
必须恰好使用 current coordinator epoch；自报更高 epoch 也会拒绝。

E6 实际启动三个不同 PID：原 source、epoch 2 restored target，以及从同一 durable store
重新启动的 old-source runtime。最后一个 PID 以 epoch 1 replay，并由该 PID 原生返回
`STALE_COORDINATOR_EPOCH_REJECTED`；epoch 2 target replay 为 `IDEMPOTENT_REPLAY`。
unsigned lease、篡改为 epoch 999 的 lease、controller 请求直接签发 epoch 999、旧 lease
复用和 forged capsule 均拒绝，Effect transition 只有一次。

这仍只证明 `SHARED_DURABLE_STORE_PROCESS_RESTART`。跨机器、跨 region、store failure 或其他
故障域迁移为 `NOT_RUN`，不得从两个 PID 外推。

## 运行与保存的证据

```bash
PYTHONPYCACHEPREFIX=/tmp/ce001-g5-pyc \
  python3 -m unittest discover -s tests -v

PYTHONPYCACHEPREFIX=/tmp/ce001-g5-pyc \
  python3 runner.py --check
```

`artifacts/` 保存：

- `input.json`：frozen operation/topology/attack/runtime scope；
- `public-keys.json`：只含 public key 与 fingerprint，绝不复制 private key；
- `process-inventory.json`：service PID 及 migration source/target PID；
- `raw-trace.jsonl`、`results.json`、`manifest.json`；
- manifest 同时保存 source 文件和每个证据 artifact 的 SHA-256。

## 产品与证据边界

`OPA / Cedar / OpenFGA / XACML` 均为 `NOT_RUN`。本地 reference workers 不是这些产品，
也不支持产品比较。

本模块只支持：在 trusted bootstrap、可靠 owner-event ingest、cooperative local
subprocess 和 shared durable store 假设下，exact owner receipts、current head、resource
fence、Standing、target transition/readback 与 process-restart migration 可执行、可攻击。
它不证明现实法律 Authority、真人认领、真实供电 Effect/Acceptance、跨故障域一致性、
生产可靠性或新机制必要性。
