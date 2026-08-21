# Wave 025 batch evidence contract

日期：2026-08-01  
状态：`V1.3 FROZEN SHARED INTERFACE AFTER REAL-SMOKE AND FIVE-ATTACK POWER CORRECTION / IMPLEMENTATIONS PENDING`

## 1. 目的与独立边界

本合同只规定 runner 与 independent evaluator 交换的证据事实，不规定任一方内部实现。

- runner 不 import evaluator，不输出 qualification verdict，不训练 classifier；
- evaluator 不 import runner 或 collector，不启动、补跑或删除任何 slot；
- collector 不读取本合同、private assignment、host receipt、reveal 或 evaluator material；
- 任一实现遇到未知字段、缺失文件、哈希错误、重复 slot、容器漂移或不完整 close，必须
  fail closed；
- `smoke` 与 `formal` 使用不同 `batch_id`，其证据不可拼接。

## 2. 状态机与目录

```text
PREPARED -> EXTERNALLY_ANCHORED -> RUNNING -> CLOSED -> REVEALED -> EVALUATED
                    \-> ABORTED (terminal; no verdict)
```

每个 batch 是独立目录：

```text
precommit.json
anchor-receipt.json
public-plan.json
runner-private-state.json        # host-only, mode 0600, never mounted to candidate
slots/<opaque_slot_id>/host-launch.json
slots/<opaque_slot_id>/docker-inspect-pre.json
slots/<opaque_slot_id>/docker-inspect-post.json
slots/<opaque_slot_id>/docker-events.jsonl
slots/<opaque_slot_id>/collector-stdout.bin
slots/<opaque_slot_id>/collector-stderr.bin
slots/<opaque_slot_id>/collector-out.bin
slots/<opaque_slot_id>/collector-ready.bin
slots/<opaque_slot_id>/collector-exit-code.bin
slots/<opaque_slot_id>/supervisor-control-stdout.bin
slots/<opaque_slot_id>/supervisor-control-stderr.bin
slots/<opaque_slot_id>/collector-features.json
slots/<opaque_slot_id>/slot-receipt.json
closed.json
reveal.json
evaluation.json                 # evaluator 唯一可新增的正式文件
```

`runner-private-state.json` 保存 prepare 后恢复所需的 seed/nonce/mapping/order，必须以 exclusive
create + `0600` 写入 host-only batch root；batch root、Docker socket 与该文件绝不能挂入 candidate。
commitment 而非权限位负责发现其事后改变。它在 reveal 后仍保留，供 evaluator 逐字核对，不能
删除来制造整洁证据。

runner 只能按状态机顺序创建上述 runner-owned 文件；写成后不得覆盖。evaluator 只读已
`REVEALED` 的 batch，并以
exclusive-create 写 `evaluation.json`。任何失败都保留已经产生的证据，不删 slot 或重编号。

## 3. Canonical JSON 与哈希

所有 JSON 为 UTF-8、递归 key 排序、最紧凑 separators、结尾一个 LF；SHA-256 对完整传输
bytes（包括 LF）计算。时间为 UTC RFC3339，另外保存 host monotonic nanoseconds 以检查顺序；
时间不是 assignment source。

所有正式对象都有精确 `schema`，且只接受本合同列出的字段。实现可在 `diagnostics` 子对象中
写额外诊断，但该对象同样必须在 preimage schema/version 中冻结，evaluator 不把它用作 feature。

## 4. `precommit.json`

schema：`WAVE025_BATCH_PRECOMMIT_V1`。至少冻结：

```text
batch_id, mode, challenges, created_at
question_sha256, qualification_contract_sha256, batch_contract_sha256
collector_source_sha256, collector_dockerfile_sha256, collector_image_id
collector_image_repo_digest_or_null, collector_base_repo_digest
runner_source_sha256, evaluator_source_sha256, feature_spec_sha256
supervisor_script_sha256, evidence_extraction_profile
sample_plan, block_plan, classifier_plan, thresholds
assignment_algorithm, public_id_algorithm, padding_algorithm
assignment_commitment, public_id_commitment, padding_commitment
```

三个 commitment 分别为：

```text
SHA256(domain || 0x00 || seed || 0x00 || nonce || 0x00 || canonical public plan bytes)
```

三个 domain 使用独立的 32-byte OS CSPRNG seed 与独立 32-byte nonce。`precommit.json` 不含
seed、nonce、role mapping、运行顺序或可逆 private ID。

一个 formal qualification suite 是一个 batch，`challenges` 必须精确为
`[D0-HOST-LEAK, D1-OCI-CANARY, T-OCI-ISOLATED]`；三者共享同一 precommit/close/reveal，不能
把最绿的若干子批次事后拼接。formal 默认人口为 D0 calibration/holdout 各 100、D1
calibration/holdout 各 100、T calibration=400、T holdout=2400，共 3200 slots。任一改变必须在
precommit 前由功效/成本理由冻结，不得看过返回再增样。

`precommit.json` bytes 生成后 runner 必须停止；只有 `anchor-receipt.json` 记录了 candidate 无权
改写的外部位置、锚定时间和精确 precommit SHA-256，才允许 `RUNNING`。本地 smoke 可以显式
写 `LOCAL_NONQUALIFYING_ANCHOR`，但最高只能得到 `STRUCTURAL_PREFIX_ONLY`。

## 5. `public-plan.json`

schema：`WAVE025_PUBLIC_PLAN_V1`。只含 batch_id、mode、challenge 集合、每个 slot 的 challenge、
slot 数、block shape、opaque slot IDs、冻结 public packet SHA-256、resource envelope 和各
challenge 的冻结启动模板。不得含 role、seed、
nonce、mapping、role-coded order/path/name/env/hostname 或 case truth。

challenge 不是 hidden role，可以公开；D1 的 canary family/role token 仍属 private mapping，不得
进入 public plan。opaque slot ID 必须由独立 public-id seed 生成，且以 assignment 不可见为测试条件；slot 目录按
opaque ID 命名，不按执行序号、block 或 role 命名。`public-plan.json` 的 slot 列表顺序不是运行
顺序。

`D0-HOST-LEAK` 的 frozen template 必须登记 sacrificial predecessor、shared residue surface 和
cleanup boundary；其 current role/token 不得进入 public plan。`D1-OCI-CANARY` 的 frozen template
登记 canary surface family，但不登记该 slot 的 role/token。`T-OCI-ISOLATED` 不得拥有 D0 shared
mount/session/sibling surface 或 D1 canary。

## 6. slot evidence

`docker-inspect-pre.json` 与 `docker-inspect-post.json` 保存 Docker daemon 返回的原始完整 JSON
bytes；`host-launch.json` schema：`WAVE025_HOST_LAUNCH_V1`，由 host 从两份原始 inspect 和 daemon
version 派生，至少包含：

```text
opaque_slot_id, container_id, image_id, repo_digest_or_null, base_repo_digest
argv, env key/value hashes, working_dir, user
network_mode, readonly_rootfs, cap_drop, security_opt
pid/ipc/uts/user namespace mode, pids/memory/cpu limits
mount type/source-or-source-hash/destination/readonly/options
created/start/finish timestamps, exit_code, oom_killed, daemon_error
```

本地 build 的最终 collector image 可以没有 registry `RepoDigest`，但不得因此回退到 mutable tag：
必须同时绑定最终 content-addressed image ID、Dockerfile/source bytes 和 base image 的 resolved repo
digest；actual container inspect 必须返回同一最终 image ID。

对 `T-OCI-ISOLATED`，host receipt 必须证明：`network=none`、read-only root、non-root、
`cap-drop=ALL`、`no-new-privileges`、固定只读 `/challenge`、独占 `/out` tmpfs、没有 Docker socket、
没有额外 host bind、没有 role-coded env/argv/cwd/container name。任何不一致均使该 slot 失败，
不得由 runner 的期望配置替代 actual inspect。

Docker Desktop real-smoke 已证实 archive/`docker cp` 不能读取 running container 的 tmpfs；该路径
不再属于 V1.1。runner 必须实现 `QUALIFICATION-CONTRACT.md` 冻结的 post-observation extraction：

- collector 的 stdout/stderr 由 PID 1 分别冻结在 `/out/collector-stdout` 与
  `/out/collector-stderr`；PID 1 只在 collector 已退出并写好 ready/exit-code 后向 daemon log 发
  role-free ready frame；
- host 在 ready 前只能轮询 `docker logs` 与 `docker inspect`，其原始 stdout/stderr 分别冻结为
  `supervisor-control-stdout.bin` 与 `supervisor-control-stderr.bin`，不得执行 container 内命令；
- ready 后、TERM 前，host 按 precommit 中的 exact profile，使用 non-root `/bin/cat` exec 分别读取
  `/out/collector-ready`、`/out/collector-exit-code`、`/out/collector-stdout`、
  `/out/collector-stderr` 与 `/out/leak-features.json`。每次 command receipt 必须证明 exact argv、
  monotonic ordering、exit=0、stderr 为空；结果分别落为同名 batch evidence，其中
  `leak-features.json` 的原始 bytes 落为 `collector-out.bin`；
- host 随后只发 TERM；supervisor 必须以 collector 原 exit code 退出，之后保存 post-inspect。
- host 随后按 container ID 与冻结的 create→post-inspect 时间窗读取 daemon events，原样保存为
  `docker-events.jsonl`；必须能一一重建五个登记 exec 的 create/start/die，且不存在额外 exec。

只有 ready/exit-code/ready-frame 合法、五次 read-only exec 全部合规、collector stderr 为空、exit=0、
collector stdout 与 out bytes 逐字相等且为唯一合法 collector schema 时，才可将相同 bytes
exclusive-copy 为 `collector-features.json`。evaluator 必须从 raw control、exec receipt 与文件 bytes
自己重做 observation cut 和 equality，不能信任 runner 的 hash 自报。

`slot-receipt.json` schema：`WAVE025_SLOT_RECEIPT_V1`，只绑定 slot、challenge、上述原始文件、
两份 inspect、daemon events、host-launch、supervisor control、五份 extraction bytes 与
collector-features 的
SHA-256、运行先后序号、exit status 和基础设施
分类；不含 role。业务/collector failure 不
重跑；只有容器尚未 start 的 prelaunch failure 可按原 opaque slot 恢复，并保留全部 attempt。

## 7. close 与 reveal

`closed.json` schema：`WAVE025_BATCH_CLOSED_V1`，按 opaque slot ID 排序列出全部预期 slot、实际
attempt、全部 slot 原始/派生文件哈希、缺失/重复/失败状态、首尾 host 时间、Docker daemon/version、批次
Merkle root（叶为 canonical slot receipt bytes 的 SHA-256）。只有 exact planned population 完整
且全部文件已冻结才可写 `CLOSED`；否则写 `ABORTED`，不得 reveal 后补跑。

`reveal.json` schema：`WAVE025_BATCH_REVEAL_V1`，只能在 `closed.json` 后生成，包含三个 domain
的 seed/nonce、完整 slot→role/block/calibration-or-holdout mapping、实际 execution order，以及
对 precommit commitment、strict block balance、opaque ID 和 padding 的重建结果。它绑定
`closed.json` SHA-256；失败仍保留 reveal，但 batch 为 `NOT_QUALIFIED`。

## 8. evaluator 输入与输出

evaluator 只接受一个 batch 路径，重算所有文件 bytes/hash、commitment、mapping、population、
host config、stdout/out equality 和 feature matrix。它只能从 `collector-features.json` 预冻结的
allowlist 派生 predictor；`opaque_slot_id`、container ID、host timestamps、execution order、role、
block 和任何 host-only receipt 均不得成为 classifier feature，但必须接受单独的 deterministic
association audit。

`evaluation.json` schema：`WAVE025_INDEPENDENT_EVALUATION_V1`，至少逐项输出：

```text
evidence_integrity
detector_sensitivity
oci_prefix_isolation
secret_randomization_closure
host_observed_launch
full_blind_comparison_qualification = NOT_TESTED
classifier/permutation/equivalence results with exact CI and multiplicity rule
excluded feature list and reason
final status: PREFIX_QUALIFIED_SCOPED | STRUCTURAL_PREFIX_ONLY |
              NOT_QUALIFIED | BLIND_QUALIFICATION_FAILED
```

evaluator 不输出 A1–A5 score、coverage、winner 或相对价值判断。

## 9. 第一实现的非承诺

本合同不声称 Docker 配置本身证明无泄漏，不覆盖内核/hypervisor/admin 合谋与微架构侧信道，
也不解决动态 lawful divergence、provider/human 跨 run 记忆、evaluator truth、Effect、Acceptance
或完整 V1/V2。它只让第一批 prefix 证据具备可拒绝、可重算和不可由 candidate 自报的结构。
