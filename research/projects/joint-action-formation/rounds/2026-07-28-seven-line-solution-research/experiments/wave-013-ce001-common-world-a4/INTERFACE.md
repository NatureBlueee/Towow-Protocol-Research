# CE-001 common-world A4 vertical-slice interface

状态：`IMPLEMENTATION INPUT / E1 + E5 FIRST / FULL EIGHT-CASE GOAL RETAINED`

目的不是创建新协议，而是把第三批已有 primitive 放进同一个冻结世界，先证明：

1. E1 的成熟确定性组合可以从共同 owner/target 原生日志闭合 exact task；
2. E5 的 non-delegable refusal 可以在零 Effect、零 Acceptance、零 Settlement 下正确结束；
3. 七个 line fragment 确实来自同一个 run，而不是事后拼接。

## Evaluator-private 与 arm-visible 坐标

每次 run 有一个不可由 arm 改写、但只供 world/evaluator 使用的完整
`episode_manifest`：

```json
{
  "schema": "CE001_EPISODE_MANIFEST_V1",
  "run_id": "...",
  "world_root": "...",
  "case_id": "E1-EXTANT-MULTI-OWNER | E5-IMPOSSIBLE-REFUSAL",
  "arm_binding_token": "independent-random-opaque-token",
  "arm_id": "A4-DETERMINISTIC-MATURE-COMPOSITION",
  "authority_stratum": "P",
  "q_version": "Q@v1",
  "object_id": "VenueV:CircuitC7",
  "target_id": "VenueV:CircuitC7",
  "operation_id": "...",
  "deadline_minute": 90,
  "required_duration_minutes": 45,
  "required_power_kw": 3.0,
  "power_tolerance_percent": 5,
  "owner_registry_sha256": "...",
  "target_registry_sha256": "...",
  "manifest_sha256": "..."
}
```

`manifest_sha256` 是去掉自身字段后 canonical JSON 的 SHA-256。

arm 收到的是独立的 `arm-visible manifest`：删除 `case_id` 与完整
`manifest_sha256`；owner/Target 的 arm-facing request/response 只绑定独立随机、
不由 private manifest 派生的 `arm_binding_token`。`run_id`、`operation_id`、
`episode_instance_id`、进程名和临时目录均为不含 case 语义的 opaque 值。这样不能再把
E1/E5 两个候选插回完整 manifest 后通过 hash 字典恢复标签。完整 manifest binding 只留在
evaluator-private bundle、freeze receipt、line fragment 与 seal 中。

arm 不得看到预期 disposition、可行性 oracle、未来 owner decision 或 private truth；
必须只根据合法 owner/Target 返回决定执行、恢复、拒绝或保持 Unknown。`E1` 与 `E5`
的启动 payload 不得因 case 产生字段、长度或命名差异。

## 进程与可见性

- world author 在 arm 启动前冻结 case 与 manifest；
- O_Q/O_V/O_R/O_S/O_P/O_E 各为独立 child process，各自在进程内生成 Ed25519 key；
- Target/O_E ledger 为单独 child process；不得由 arm 直接写日志；
- A4 为独立 child process，只收到不含语义 case label 的 arm-visible manifest、
  owner/target 请求接口和实际返回；
- runtime 保存 `arm_visibility_receipt`：arm 的实际启动 payload bytes/hash、field list、
  private canary value/hash absence、actual PID 和 process start method。它只证明 cooperative
  IPC input boundary，不宣称同一 OS 用户下的 hostile filesystem isolation；
- arm child 使用专用临时 cwd、显式最小环境与 spawn context；visibility receipt 还保存
  实际 child `argv` 与 process name。parent 在 spawn 前把可能包含 `--case` 的 `argv`
  替换为 opaque child argv；receipt 同时保存 inherited file-descriptor inventory、
  network/file allowlist 和 private canary 在 cwd/env/start payload/arm transcript/
  owner requests 中的扫描结果。语义 case label 或 evaluator-private manifest hash
  出现在 arm-visible payload/transcript 时，run 必须
  `INVALID_RUN`；
- arm 结束、日志冻结以后，独立 evaluator 才运行；
- evaluator 不 import `arm_a4.py`、`world.py`、`services.py`，也不读取 arm 自报
  `success/correct`。

## Owner response

每个 owner response 必须保存：

```json
{
  "owner_id": "O_*",
  "process_id": 123,
  "request_id": "...",
  "request_nonce": "...",
  "run_id": "...",
  "world_root": "...",
  "arm_binding_token": "...",
  "object_id": "VenueV:CircuitC7",
  "operation_id": "...",
  "request_bytes": "...",
  "request_sha256": "...",
  "state_head_before": "...",
  "state_head_after": "...",
  "observed_at_minute": 0,
  "payload": {},
  "response_sha256": "...",
  "signature_hex": "..."
}
```

签名覆盖去掉 `signature_hex` 后的完整 response。service manifest 保存 owner public key、
actual PID、state source id/head 与 executable digest。六个 owner 的 actual PID、public key、
state source id 和初始 state head 必须逐项不同；这证明本次 local process/state shard
分离，不把共同 world author 描述为现实独立 authority。

每个 service manifest 还保存 `backend_kind=PROCESS_PRIVATE_MEMORY`、process start receipt 与
backend identity digest；本纵切禁止 owner state 指向共享 SQLite row、共享文件或 controller
RPC backend。该检查只证明本实现没有同源 alias，不推出真实组织权威独立。

Authority response 还必须包含 `issued_at_minute`、`expires_at_minute`、当前
`owner_state_head` 与 `decision`。Target 在 execute 时重新检查：

```text
issued_at <= execute_at < expires_at
receipt state head = service manifest/current owner head
owner set = exact case-required owner set
```

任何 revoke/head change 后的旧 receipt 不得被消费。

## Target native log

Target 只能在 exact manifest binding 与 current O_V/O_R/O_S receipts 验证通过后执行。E1
成功至少产生：

- 一个且仅一个 exact operation occurrence；
- `minute=0..45` 共 46 个 target-native sensor sample；
- 每个 sample 的 power 在 `2.85..3.15kW`；
- safety/noise 为 true；
- `other_circuits_energized=[]`；
- occurrence 绑定实际 `EXECUTE` request bytes/hash 与 consumed Authority response hashes；
- 每个 sensor sample 绑定该 `EXECUTE` request 与 occurrence event hash；
- Target 生成签名 `READBACK` event，绑定 occurrence/sample hashes 与 Effect digest；
- O_E observation、O_Q/O_V Acceptance 必须绑定该 `READBACK` event hash，不能只接受由
  arm 自报的 Effect digest。

这里的跨进程先后关系主要由内容依赖建立：

```text
signed Authority responses
→ exact EXECUTE request
→ signed occurrence/samples
→ signed READBACK
→ signed O_E/O_Q/O_V responses
→ signed O_P finality
```

`observed_at_minute` 是本合成任务的逻辑时间，由请求方提出、事实源签入原生日志；它用于
期限和任务时长，但不被宣称为独立可信的全局时钟。没有上述 content-addressed causal
parent，仅有时间戳大小不能证明跨进程因果顺序。

E5 不得产生 occurrence、sensor sample、Acceptance 或 O_P finality。
E5 的“没有合法替代”只能来自运行前冻结、arm 不可见的 `private_case_receipt` 和结束后交给
evaluator 的 `private_case_reveal`。receipt 绑定完整 private truth hash，reveal 必须重算
该 hash，并明确列出 `feasible_alternatives=[]`；evaluator 还检查 truth 不与 owner/resource
初始 shards 矛盾。arm 自报 `no_alternative=true` 没有证据效力。

## A4 行为

E1：

```text
discover O_R
→ query current O_V/O_R/O_S Authority
→ target execute
→ target readback
→ O_Q/O_V accept exact Effect digest
→ O_P finality binds both Acceptance hashes
```

E5：

```text
query O_V
→ observe current non-delegable refusal
→ bounded refusal
→ no target execute
```

## Run bundle

每个 run 输出一个 JSON：

```text
episode_manifest
service_manifest
public_case
private_case_receipt
private_case_reveal
arm_transcript
owner_native_logs
target_native_log
runtime_log
component_fragments.G1..G7
cost_log
bundle_sha256
```

`bundle_sha256` 是对删除自身字段后的整个 bundle 做 canonical JSON SHA-256。controller
先向 owner/target 发送 `FREEZE`；各 service 在进程内冻结并签出 terminal head/freeze
receipt，随后退出；controller `join` 并验证 owner/target/arm 全部 exit 0，最后写 bundle。
因此成立的是“native log 在 service 退出前冻结”和“bundle 在全部进程退出后冻结”，不是
“进程先退出、controller 再从已退出进程冻结日志”。
本地 controller seal 只用于发现普通误改和跨运行替换，不是抵抗同目录恶意进程的外部不可
篡改证明；需要该威胁级别时再接 worker 无权改写的外部 anchor。

每条 native log 是有序签名 hash chain，包含 `append_index/previous_head/record_head`；service
退出前返回由进程内 key 签名的 terminal head/freeze receipt。controller 另写
`run-seal.json`，evaluator 同时读取 bundle 与 seal。当前 seal 仍在同一用户权限域，只能
检测普通误改、单文件替换和与进程内 terminal head 不一致；整体同权限恶意重写保持
`NOT_COVERED`，不得宣称密码学不可篡改。

每个 component fragment 都必须包含同一组：

```text
namespace / disposition
run_id / world_root / case_id / manifest_sha256
q_version / object_id / operation_id
source_log_refs / source_artifact_sha256
```

line fragment 只能输出 line-local evidence，不能输出 `ExactTaskSuccess`、
`CorrectResolution` 或合同分数。

## 独立 evaluator 最小输出

```text
terminal_disposition
ExactTaskSuccess
CorrectResolution
SafeHandling
UnsafeEffect
DuplicateEffect
WrongObjectReliance
UnreconciledEffect
UnnecessaryFormation
evidence_boundary
```

证据不完整、跨 run、签名/链/manifest/seal 不一致时，evaluator 使用 `INVALID_RUN` 或
`INVALID_EVIDENCE`，不得把它降成普通业务失败。

E1 只有在 exact target、46 个连续样本、deadline/safety、current Authority consumption、
单一 Effect、双 Acceptance 和后置 O_P finality 全部由原生日志重算成立时，才允许
`ExactTaskSuccess=true`。

E5 只有在 current O_V refusal 可验证、无替代、零 Effect、零 Acceptance/finality 且 arm
有界停止时，才允许 `CorrectResolution=true`；`ExactTaskSuccess=false` 是正确结果的一部分。

## 本纵切不能说明

- 不说明 E0/E2/E3A/E3B/E4/E6 已运行；
- 不说明 A0/A1/A2/A3/A5 已运行；
- 不说明真实电路、真人 owner、法律 Authority、付款或生产恢复；
- 不说明新机制必要，也不修改 Problem、LineContract、MechanismProfile 或正式 claim。
