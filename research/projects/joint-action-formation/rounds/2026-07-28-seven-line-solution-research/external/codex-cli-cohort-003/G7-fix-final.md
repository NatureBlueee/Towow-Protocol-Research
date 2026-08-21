# G7 CE-001 根红灯修复最终报告

日期：2026-07-30  
结论：`LOCAL_PROCESS_STATE_SEPARATED_COMPONENT_EVIDENCE`  
公开 schema：`g7.evolution.line-local-evidence.v2`  
当前 integration preflight：`QUALIFIED_COMPONENT_OUTPUTS / CONTRACT_SCORE_NOT_COMPUTED`

## 1. 本轮解决了什么

本轮不再把首轮 `33/33 PASS` 当作完成证据。第二轮把根审计指出的五类伪边界改成了
可攻击、可落盘复核的局部边界：

1. `O_Q`、`O_V`、`O_P` 分别由独立 OS process、durable state、runtime identity、
   state source 和 act source 产生响应；协调进程只接收实际序列化 bytes。
2. target dispatch 不再接收 `authority_allowed=True`。`O_R`、`O_S` 各自从独立
   receipt-issuer process 和独立 durable signing state 发出 current receipt；target
   process 验证 receipt set，并写出 target-native consumption event/hash 后才发生一次
   transition。
3. E6 的 source、target、old-source restart 和 external fence owner 是实际不同进程。
   source 与 target 使用不同 durable state path；source 退出后启动 target，再重启旧
   source；外部 fence owner 从 durable epoch `8` 拒绝旧 epoch `7` 的提交。
4. capsule、dependency graph、source/target state、history prefix、owner response、
   target occurrence、receipt consumption 和 fence state 的引用均由实际传输或落盘
   bytes 计算，不再用 fixture 常量冒充。
5. `EvolutionModule.run_all()` 只返回 G7 line-local evidence 和 namespaced integration
   fragment，不返回合同成功判断。旧 E4/E6/field-loss API 只保留为首轮回归风险面，不
   进入公开 envelope。

这只修复了 G7 当前可执行局部机制的根红灯，不是完整 CE-001 成功，也不是现实产品或
生产恢复证据。

## 2. A/B/C 的建立、身份与独立性

| 身份 | 会话 | 实际产物 | 证据作用 |
|---|---|---|---|
| A | `/root/g7_a_v2` | `g7-evolution/A-boundary-reconstruction-v2.md` | 独立重建 owner/runtime/lineage 权威边界与 fail-closed 条件 |
| B | `/root/g7_b_v2` | `g7evo/boundary.py` 等实现、process tests、原始运行记录 | 实现 A 所要求的跨进程、跨状态边界 |
| C | `/root/g7_c_v2` | `tests/test_root_redlights_v2.py`、`raw/root-redlights-v2.json`、`C-root-redlights-v2.md` | 在未读取 B 方案时建立并冻结攻击面 |

C 在 B 实现前的实际首跑是：

```text
19 tests / 17 RED / 2 PASS controls / 0 ERROR / exit 1
```

原始记录保存在 `g7-evolution/raw/root-redlights-v2.json`，没有被绿灯结果覆盖。C 后续只
校正了两处测试合同矛盾：公开 `run_all()` 与 legacy direct controls 的分层，以及
preflight 中 actual G7 digest 对 G6 引用的运行时同步；校正时仍未读取 B 的实现方案。

A/B/C 的分工用于产生相互独立的边界设计、实现路径和失败攻击。三者同意不是证据；下文的
进程记录、durable bytes、攻击后状态和主会话复跑才是本轮证据。

## 3. 实际 owner 与 receipt source

本报告引用的主会话运行根目录是：

```text
/private/var/folders/n5/tk_v_x1500bcqwdp0vlsv3tm0000gn/T/g7-evolution-v2-jo7jumcg
```

### 3.1 post-occurrence owner acts

| owner | PID | durable state path | 独立 source |
|---|---:|---|---|
| `O_Q` | 11367 | `.../owners/O_Q/state.json` | `state-source:O_Q:889a894b-4fbc-433d-90c1-16cfc4f03fde` / `act-source:O_Q:9cf6f05acd40a6fb` |
| `O_V` | 11372 | `.../owners/O_V/state.json` | `state-source:O_V:33913e3c-0e43-4e5b-ad91-0e804655e893` / `act-source:O_V:2c104efc42e85f59` |
| `O_P` | 11373 | `.../owners/O_P/state.json` | `state-source:O_P:3c0bad5f-d56e-4a35-a0ef-dc0a1884544d` / `act-source:O_P:147ab894dfa3b6a2` |

三份 owner response frame hash 分别是：

```text
O_Q  1faa3f5322f7dd480da6c1ff34ec263b73c627716a8da2a8adb3f7372ec03709
O_V  f98c2b554d7181acb9fbe82bcff6ae056d4cb0eb2ac4e94cc8cfb122efee468f
O_P  5018b0010304be445bb4a3e13e60370a999143d070f20dc14a47f2c560f8445f
```

这些 hash 来自实际 response bytes；`O_P` 的请求携带 `O_Q/O_V` 的传输 frame 和 public
trust anchors，而不是直接引用同进程对象。

### 3.2 current receipt issuers 与 target-native consumption

| issuer | PID | durable state path | receipt bytes hash |
|---|---:|---|---|
| `O_R` | 11234 | `.../receipt-issuers/O_R/identity-state.json` | `00eb3e87361364b3446906ddff17d72d5aacdfbd15be4220b7ceb957e007aa4b` |
| `O_S` | 11235 | `.../receipt-issuers/O_S/identity-state.json` | `595e7836ed20831fe0b0df16fa401b5d108a9f09b601434f9497f8ff712c46a2` |

target gate 是 PID `11236`，state path 为 `.../target-gate/state.json`。它记录的 native
consumption event hash 是：

```text
5b867f4a4d8c3d8d7eac2138c1e4c82c4e644d0ed5cf4cf0cb267c9f9fee9231
```

该 event 的 `transmitted_receipt_hashes` 与 `consumed_receipt_hashes` 精确相等，并绑定
episode、Q version、object、operation 和 target。旧 controller boolean 已从 dispatch
签名移除；继续传入该关键字会触发 `TypeError`，不会产生 target transition。

## 4. E6 实际迁移与外部 fence

| 角色 | PID | runtime / epoch | durable state path | 观察 |
|---|---:|---|---|---|
| source | 11397 | `coordinator-old` / 7 | `.../migration/source/state.json` | exit `0`，`termination_observed=true` |
| target | 11398 | `coordinator-new` / 8 | `.../migration/target/state.json` | source 退出后启动并消费 capsule |
| fence install | 11399 | external fence owner / 8 | `.../migration/fence/state.json` | durable epoch 从 7 安装到 8 |
| old source restart | 11400 | old runtime / 7 | 读取旧 source state | `actually_restarted=true` |
| fence readback | 11402 | reload durable fence / 8 | 同一 fence durable path | `REJECTED_OLD_EPOCH`，transition count `0` |

关键结果：

```text
source state hash  0ad5c03045dfe57e72b70cd0ced25f3f1c0af78ffaad63deee821f9c46426f8d
target state hash  6ac1c17bbc9aad11c24ac23df4da547aa99cfdcbfdf1396a81e04f734de8db8c
fence state hash   fbb14d30100643baee04840d4c9660eaf203ce054351b4c2b754c74a08030bf0
capsule hash       265d8be00374f5ed83cced44ab07493e2aac3f1e9d32a0c4dd4f3dad83da3e3b
history prefix     442e1ef3cd9a73461b43608c525ff0d71f9198435e2029770c2f6a461d6d1d6d
old request frame  46061b1a9c08f225cfe6b55454d614739a83da42ff10d65ff60710f79e1568e3
fence response     52abed9c21f478d8dad370bf69b1501a77a626ef9c02fe24f834e358f1acd627
```

source/target PID、runtime identity、state boundary ID 和 state path 均不相同。旧 runtime
重启不是同一函数内的布尔模拟；它产生实际 restart request bytes，外部 fence owner 在另一个
进程中重载 durable state 后拒绝。

## 5. 冻结攻击与 fail-closed 结果

### 5.1 owner/source attacks

以下九项均启动实际攻击 owner process，结果均为 `state_act_count=0`：

```text
duplicate_owner
response_transplant
stale_response
wrong_episode
wrong_q
wrong_object
wrong_operation
wrong_target
wrong_effect_occurrence
```

### 5.2 receipt consumption attacks

以下七项均启动实际 target process，结果均为 `REJECTED_RECEIPT_SET` 且
`target_transition_count=0`：

```text
wrong_receipt
stale_receipt
tampered_receipt
receipt_set_transplant
missing_receipt
duplicate_receipt
wrong_current_head
```

### 5.3 migration/capsule attacks

- history rewrite：攻击者改写传输 history 并重算裸 history hash，但不能重签 source seal；
  target import process 拒绝。
- capsule field loss：删除 owner evidence 等承重字段后，target import process 拒绝。
- old runtime restart：实际重启旧 source 后，由 external durable fence 拒绝 epoch `7`。
- negative-control mutant：刻意让旧 runtime 可提交时，auditor 以 exit `1` 返回
  `RED_DETECTED`，证明审计器没有对该 split-brain mutant 假绿。

## 6. 主会话独立验证

```text
runner audit                         PASS
原首轮风险测试                       33/33 PASS
C 冻结根红灯                         19/19 PASS
新增 process-boundary tests           6/6 PASS
unittest 全套                         58/58 PASS
py_compile                            PASS
negative control                     exit 1 / RED_DETECTED（预期）
integration preflight composition    QUALIFIED_COMPONENT_OUTPUTS
preflight contract score             NOT_COMPUTED
```

此外，主会话独立重算了：

- 10 组嵌入式 transmitted/durable bytes：全部与声明的 SHA-256 相等；
- 8 个当前 owner、receipt issuer、source、target、fence durable state 文件：全部存在且
  文件 SHA-256 与运行记录相等；
- 公开 `raw/run-traces.json` 与 `results.json`：不存在旧 fixture digest
  `sha256:effect-001`、`sha256:accept-*`、`sha256:op-finality`，也不存在
  `ExactTaskSuccess`、`CorrectResolution`、`RecoveryToValue` 字段。

preflight 测试只证明：当 integration assembler 提供与本次 actual G7 digest 对齐的 G1–G6
引用时，这个 G7 fragment 能通过当前结构与引用检查。它没有运行一个真实完整 G1–G7 产品
链，也没有计算 CE-001 合同分数。

## 7. 精确 G7 integration envelope

以下是上述 run 的精确、run-specific namespaced fragment：

```json
{
  "namespace": "G7",
  "qualification": "QUALIFIED_COMPONENT_OUTPUT",
  "evidence": {
    "append_only_history_hash": "dd34d064ce3e15fad3a9b31edeac32228afc08839230b1620f4d9d1e9aa45256",
    "dependency_graph_hash": "8d6659897c44efa659e429e78c76291e2a3a00bc3191613a78ca08ec577ea0db",
    "evidence_boundaries": {
      "adapter_semantic_independence": "NOT_ESTABLISHED",
      "cold_repeat_full_lifecycle": "NOT_MEASURED",
      "hidden_pair": "NOT_CONSTRUCTED",
      "production_split_brain": "NOT_RUN",
      "real_product": "NOT_RUN",
      "safety_liveness_frontier": "NOT_RUN"
    },
    "migration": {
      "lineage_verification": {
        "capsule_consumer_frame_hash": "265d8be00374f5ed83cced44ab07493e2aac3f1e9d32a0c4dd4f3dad83da3e3b",
        "capsule_hash": "265d8be00374f5ed83cced44ab07493e2aac3f1e9d32a0c4dd4f3dad83da3e3b",
        "capsule_producer_frame_hash": "265d8be00374f5ed83cced44ab07493e2aac3f1e9d32a0c4dd4f3dad83da3e3b",
        "effect_hash": "22e3e55722081a390f511a40fa7d0c146fd55c704adbe617dbc073d565e42b68",
        "effect_occurrence_count_for_operation": 1,
        "fence_state_bytes_hash": "fbb14d30100643baee04840d4c9660eaf203ce054351b4c2b754c74a08030bf0",
        "history_fork_detected": false,
        "history_prefix_hash": "442e1ef3cd9a73461b43608c525ff0d71f9198435e2029770c2f6a461d6d1d6d",
        "object_id": "VenueV:CircuitC7",
        "owner_evidence_hashes_verified": true,
        "owner_verification_event_hash": "0bb1ec50defdb19e079438c261f09549d883f7e7afd58cc55c1a1acf6366e5ef",
        "q_version": "Q@v1",
        "restart_request_frame_hash": "46061b1a9c08f225cfe6b55454d614739a83da42ff10d65ff60710f79e1568e3",
        "restart_response_frame_hash": "52abed9c21f478d8dad370bf69b1501a77a626ef9c02fe24f834e358f1acd627",
        "source_runtime_hash": "0ad5c03045dfe57e72b70cd0ced25f3f1c0af78ffaad63deee821f9c46426f8d",
        "target_consumption_event_hash": "5b867f4a4d8c3d8d7eac2138c1e4c82c4e644d0ed5cf4cf0cb267c9f9fee9231",
        "target_runtime_hash": "6ac1c17bbc9aad11c24ac23df4da547aa99cfdcbfdf1396a81e04f734de8db8c"
      },
      "old_runtime_restart": {
        "actually_restarted": true,
        "current_epoch": 8,
        "external_fence_event_hash": "52abed9c21f478d8dad370bf69b1501a77a626ef9c02fe24f834e358f1acd627",
        "fence_result": "REJECTED_OLD_EPOCH",
        "presented_epoch": 7,
        "process_id": 11400,
        "process_start_event_hash": "6d9927f3e44d1c36493e9ad0bdce63c31148b1983277fd03c8a6ae2708315ee0",
        "request_frame_hash": "46061b1a9c08f225cfe6b55454d614739a83da42ff10d65ff60710f79e1568e3",
        "response_frame_hash": "52abed9c21f478d8dad370bf69b1501a77a626ef9c02fe24f834e358f1acd627",
        "restart_observed": true
      },
      "recovery": {
        "acceptance_hashes": [
          "1faa3f5322f7dd480da6c1ff34ec263b73c627716a8da2a8adb3f7372ec03709",
          "f98c2b554d7181acb9fbe82bcff6ae056d4cb0eb2ac4e94cc8cfb122efee468f"
        ],
        "finality_hash": "5018b0010304be445bb4a3e13e60370a999143d070f20dc14a47f2c560f8445f",
        "owner_transport_manifest_hash": "0bb1ec50defdb19e079438c261f09549d883f7e7afd58cc55c1a1acf6366e5ef",
        "recovered_from_owner_sources": true
      },
      "source_runtime": {
        "epoch": 7,
        "process_id": 11397,
        "runtime_id": "coordinator-old",
        "state_boundary_id": "9d5e1bb581d75e62a17737fa5b6b4b7411e4c818c513f3c80ad9eaf3a65c286a"
      },
      "target_runtime": {
        "epoch": 8,
        "process_id": 11398,
        "runtime_id": "coordinator-new",
        "state_boundary_id": "0c4fffd77d42f82608b47f32558e1367d6877cf9a65a07a754bbef64901924dc"
      }
    },
    "reopen_set": [
      "e6:owner-source-recovery",
      "e6:lineage-reconciliation"
    ]
  }
}
```

`effect_hash`、`acceptance_hashes` 和 `finality_hash` 是 integration preflight 当前要求的
跨线 opaque digest 引用名；在 G7 中它们只指向实际 occurrence/owner response bytes，
不是 G7 对 `Effect`、`Acceptance`、`Settlement` 或合同成功的判断。

## 8. 保留的负面结果与残余边界

本轮没有改写以下状态：

- E4 alternative recovery：保留；
- E6 effect/acceptance gap：保留；
- append-only 与 exact occurrence reconciliation：继续作为必要条件；
- capsule field loss：fail closed；
- cold/reused full-lifecycle cost：`NOT_MEASURED`；
- adapter semantic independence：`NOT_ESTABLISHED`；
- hidden safety-liveness pair：`NOT_CONSTRUCTED / NOT_RUN`，未伪造相反 final requirement；
- real product：`NOT_RUN`；
- human owner：`NOT_RUN`；
- legal Authority：`NOT_RUN`；
- physical Effect：`NOT_RUN`；
- production split-brain：`NOT_RUN`；
- cross-product portability：`NOT_ESTABLISHED`；
- full-lifecycle net value：`NOT_ESTABLISHED`；
- complete CE-001：`NOT_ESTABLISHED`。

当前密码学与进程隔离仍依赖可信本地 harness、可信 public trust manifest 和同一用户权限域。
它能发现普通字段注入、transplant、stale state、history rewrite 和 old-epoch replay，但不
宣称抵抗拥有同一目录写权限、能读取 owner 私钥状态的恶意本机进程。生产级独立权限域、
外部 append-only anchor、真人认领和长期漂移均未运行。

## 9. 产物与修改边界

本轮只修改：

- `experiments/wave-012-ce001-power-restoration/g7-evolution/`
- `external/codex-cli-cohort-003/G7-fix-final.md`

完整原始运行记录见 `g7-evolution/raw/run-traces.json`，窄摘要见
`g7-evolution/results.json`。没有修改其他 research、contract、preflight 或根状态文件，
也没有执行部署、生产写入或正式机制状态晋升。
