# Wave 004-A local controller executor

状态：`LOCAL_SYNTHETIC_EXECUTOR_IMPLEMENTED`  
作用域：补上 `G1-HWB-FIRST-RUN.md` 暴露的 controller executor 缺口；不改写 HW-B
候选，不读取 HW-B oracle、scorer 或 controller-index。

## 它实际增加了什么能力

`executor.py` 不再把 holder 的 `AUTHORIZED` 当成 route 已完成。它只接受
`contract.json` 冻结登记的 canonical holder payload hash，并实际执行三类有界动作：

1. `DIRECT_PROJECTION`：把最小 task-relative projection 写入指定 recipient store；
2. `DERIVED_ONWARD`：把 direct hop、controller 派生的 onward authorization 和 onward
   hop 作为一个不可拆分事务提交；
3. `RECIPROCAL_EXCHANGE`：校验双方 direction、compatibility key、counterparty 和 policy
   后，把两侧 disclosure 作为一个 all-or-nothing 事务提交。它进一步区分：
   - `CENTRAL_COLLECTION`：双方只投递到同一个中心，不能声称双方已经互相收到；
   - `COUNTERPARTY_EXCHANGE`：每一侧 policy 分别授权另一侧为 recipient，并且双方
     recipient store 均完成 readback 后，才称为对手方互投。

成功结果仍明确写为：

- `relation_status = NOT_ESTABLISHED`；
- `commitment_status = NOT_CREATED`；
- `authority_status = NOT_INFERRED`。

它证明的是本地冻结条件下 route/exchange 可以被执行并读回，不证明现实关系、承诺、授权、
效果或采用已经发生。

## 成功证据顺序

成功动作采用文件锁和两阶段持久化：

1. 校验完整 command；command 的 canonical hash 包含 `idempotency_key`、world/step、
   holder envelope、route、recipient、purpose、retention、depth 和 projection；
2. 将该 route 的全部 delivery 作为一个 transaction，同时写入 authoritative delivery
   event log、各 recipient store 和 recoverable pending record；
3. 以同目录临时文件、`fsync` 和 `os.replace` 原子替换 state 文件；
4. 从磁盘重新加载 state，独立按 recipient 读回每一条 delivery，重算 event hash 和
   authoritative state root；
5. 只有读回 postcondition 完整后，才签发 controller execution receipt 并再次原子持久化。

成功 receipt 绑定：

- frozen contract hash；
- 完整 input/command hash 与显式 idempotency key；
- trusted holder envelopes hash；
- policy snapshot hash；
- prior controller state 与 prior event；
- recipient delivery event hash；
- authoritative delivery-store root；
- readback hash；
- output hash。

如果第一次原子提交后、receipt 签发前中断，pending record 允许相同 command 只读回并完成
原 receipt，而不再提交 delivery。

## 幂等与拒绝

- 相同 idempotency key + 相同完整 command：返回同一 outcome、receipt、delivery event 和
  state root，`state_changed=false`，不新增 event；
- replay 或 pending recovery 之前重新校验 frozen contract、pending hash、delivery-store
  root chain、controller event chain、execution receipt、历史 readback 与当前 recipient
  store；contract 改变、旧 event 被改写或 recipient record 丢失都会拒绝，不返回旧
  `EXECUTED`；
- 相同 key + 不同 command：`IDEMPOTENCY_CONFLICT`；
- holder hash、world、world-step、direction、compatibility key、counterparty、
  recipient、purpose、retention、depth 或 revoked 任一不满足：明确拒绝；
- 所有拒绝均为 `state_changed=false`，不会建立 state 文件、写 recipient store、消耗
  disclosure budget 或追加 controller event。

## 冻结输入

- `contract.json`：四个 trusted holder receipt hash、world/step、预算、facet compatibility；
- `inputs/direct-projection.json`；
- `inputs/derived-onward.json`；
- `inputs/reciprocal-exchange.json`。

这些是独立合成 fixture，不是 HW-B completion receipt，也未借用 HW-B oracle 解。

## 威胁与证据边界

当前 source authentication 只是
`FROZEN_TRUSTED_CONTRACT_REGISTRY_SIMULATION`：受信 controller 将 canonical payload hash
与本地冻结 registry 比对。holder 没有真实签名，execution receipt 也只是 hash-bound issuer
record，不具备外部不可否认性。

本地 file lock、`fsync`、atomic replace、hash chain 和 readback 能发现普通误改、重复提交、
越界 route 与流水线内不一致；不能抵抗能改写同目录文件或进程的恶意主体。当前 recipient
readback 仍由同一受信 controller 执行，不是 recipient 独立签名 ACK。

`DERIVED_ONWARD` 也只在 contract 明确允许受信 controller 代表第一 recipient 执行第二跳
的合成权限模型中成立。源 holder 的 onward policy 本身不证明第一 recipient 自主同意或执行；
没有 recipient ACK 时，不能把本实验外推为跨 Authority 的 onward execution 证明。

更强结论至少需要：

- holder 签名或可验证 credential；
- recipient-side 独立 ACK；
- controller 无权改写的 append-only external anchor / Git object / 签名账本；
- 不同权限域中的恢复与并发故障试验。

## 运行

```bash
python3 -m unittest discover -s tests -v
python3 executor.py \
  --contract contract.json \
  --input inputs/direct-projection.json \
  --state /tmp/towow-wave004-controller-state.json
```

第二次执行同一命令应得到 `IDEMPOTENT_REPLAY`，且 state bytes 不变。

当前回归为 `24/24`，其中新增了 changed-contract replay/pending、tampered audit event、
missing recipient store 和 counterparty exchange 双边 readback 反例。
