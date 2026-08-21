# G2 CE-001 根红灯第二轮修复

日期：2026-07-30  
状态：`LOCAL SYNTHETIC SIGNED OWNER-PROCESS BOUNDARY REPAIRED /
INDEPENDENT ATTACK RECHECKED / NO FULL CE-001 RUN / NO FORMAL PROMOTION`

实现目录：
`experiments/wave-012-ce001-power-restoration/g2-relation/`

## 结论

本轮关闭了 `G2-final.md` 留下的两个已知假边界，并由 C 新发现、根会话修复了一个更深的
identity collision 红灯：

1. 五个 owner 不再是同进程 `OwnerEndpoint`。`O_Q/O_V/O_R/O_S/O_P` 各自运行在不同
   subprocess，只读取自己的 profile/state，并各自在进程内生成 Ed25519 private key；
2. `act_hash` 不再冒充签名。每个 receipt 保存 exact canonical raw bytes、SHA-256、
   Ed25519 signature、public key、key id、PID、process instance、worker source 与
   profile source hash；
3. controller 验证签名及 exact owner、episode、Q、object、purpose、revision、relation
   version、time、decision、scope 和 payload binding；
4. controller 还核对 ready manifest PID 等于实际 `Popen.pid`，并在任何 query 前强制
   五 owner 的 PID、process instance、key id 和 public key 分别唯一；
5. RelationVersion 只是一份从已验签 owner evidence 派生的 content-addressed snapshot，
   明示 `NOT_AN_OWNER_ACT / NOT_AUTHORITY / NOT_EFFECT / NOT_ACCEPTANCE`；
6. T5 不再接受 `platform_direct_applicable` 裸布尔。独立 platform-native process 必须
   对 exact episode/Q/object/purpose/revision 返回签名 capability proof，再返回绑定该
   proof 的签名 current capability readback；
7. 缺 owner policy 继续为 Unknown，refusal 与 blocking opposition 继续阻断对应 owner
   downstream；nonblocking opposition 同时保留支持与反对来源；
8. `authorized` 与 `activated` 继续只输出 `G5_UNVERIFIED` 与
   `G6_UNVERIFIED_NO_EFFECT`，没有绿色总状态，也没有 O_E act。

当前最强结论是：

```text
G2_SIGNED_OWNER_EVIDENCE_COMPONENT = POSITIVE_SCOPED_LOCAL_SYNTHETIC
CROSS_OWNER_PROCESS_KEY_IDENTITY_GATE = ATTACK_RECHECK_PASS
T5_PLATFORM_APPLICABILITY = SIGNED_NATIVE_PROOF_AND_READBACK_LOCAL_SYNTHETIC
G5_AUTHORITY = UNVERIFIED
G6_EFFECT = NOT_RUN
REAL_OWNER = NOT_RUN
LEGAL_SUFFICIENCY = NOT_RUN
ACCEPTANCE = NOT_RUN
CE001_COMPLETE_SOLUTION = NOT_ESTABLISHED
```

## 实际 A / B / C

| identity | 职责 | 实际结果 |
|---|---|---|
| `/root/g2_fix_a_boundary` | A：只读重建 owner act、RelationVersion、T5 与 G5/G6 权威边界 | 发现旧实现 128 个 act 中 signature/key/PID/raw/time/manifest 均为 0；给出签名 preimage、process/profile 隔离和攻击矩阵；未改文件 |
| `/root/g2_fix_b_implement` | B：实现 process-isolated owner、Ed25519 receipt、派生 RelationVersion 与 native platform proof | 初版修复、23 项测试、双跑 runner、raw trace 与 manifest |
| `/root/g2_fix_c_attack` | C：不读取 A/B 讨论，不选择赢家，只写公开接口攻击 | 初始 21/21 通过；加入主动五 owner 身份复用后得到 21/22，留下不放宽的红灯测试与 `C-FIX-ATTACK.md` |

根会话重读正典、复跑旧基线、检查 B 实现、修复 C 的 identity collision、重新生成证据并
运行合并套件。三者共享仓库、模型家族和本机权限；它们形成职责与失败路径隔离，不构成
外部组织或独立实验室复现。

## 权威边界

### Owner act

controller 只读取 endpoint descriptor。每个 descriptor 指向一个 worker source 和一个
owner-local profile source；profile 内容只由对应 child 读取。controller 的 config、
trace、receipt 与 manifest 不返回 profile 内容，只保存 child 自报且由保存包复核的
profile source id/hash。

owner receipt 的签名 preimage包含：

```text
schema_version
owner_id
episode_id
query_id
Q id/version/statement/hash
object_id
purpose
relation_revision
relation_revision_hash
relation_version_hash
time
decision
kind
scope
payload
ordinal
worker source
PID / process_instance_id / key_id
```

`act_hash` 只是 signed raw bytes 的定位摘要。接受 receipt 必须同时满足：

- raw bytes 与 displayed canonical preimage 一致；
- raw SHA-256 与 `act_hash` 一致；
- Ed25519 signature 对 exact raw bytes 有效；
- public key/key id 与该 owner process ready manifest 一致；
- signed source、PID、process instance、key 与 manifest 一致；
- owner、episode、Q、object、purpose、revision、version 和 scope 与当前 request 逐项一致。

篡改 payload 后同步重算 `act_id/act_hash/raw_sha256` 仍会因 signature 不匹配被拒绝。
O_V receipt 配 O_Q manifest/key、旧 episode、wrong Q/object/purpose/revision/version 也会
fail closed。

### RelationVersion

RelationVersion 不是由 controller 替 owner 宣布的权威事实。controller 先验证 O_R 的
private-column act 和五个 owner 的 constitution acts，再派生绑定 exact
Q/object/purpose/revision/schema 与 ordered source act hashes 的 snapshot。随后每个 owner
对 exact RelationVersion 分别 explain-back、claim/refuse/opposition。

缺 policy、坏签、wrong binding 或 stale relation hash 不会由 controller 补 act。它们进入
Unknown 或 rejected evidence；refusal/blocking opposition 停止该 owner 的
AUTHORIZE/ACTIVATE intent。RelationVersion 不汇总出“关系整体成立”。

### Authorized / activated

签名 AUTHORIZE 仍只是 `G5_UNVERIFIED_OWNER_INTENT_ONLY`；G2 没有 current Authority
owner、commit-time head 或法律充分性判断。签名 ACTIVATE 仍只是
`G6_UNVERIFIED_NO_EFFECT`，payload 明确 `effect_asserted=false`，O_E 为 `NOT_RUN`。
任何 downstream consumer 都不能把这两轴读取成 G5/G6 已闭合。

### T5 platform-direct

E0/T5 fixture 现在只携带 platform endpoint descriptor 与 profile-case selector，不携带
applicability 布尔。独立 platform process 从自己的 native state 产生两份签名 receipt：

1. capability proof：exact target、完整任务 capability、U stratum 与 relation-free
   applicability；
2. capability readback：绑定 proof hash、exact target 与 current capability state。

裸布尔、缺 proof、缺 readback、wrong-object readback、坏签名或 source substitution 都被
拒绝。该 readback 只支持当前本地合成平台 capability applicability，不是执行 readback，
`effect_asserted=false`，真实平台产品和 Effect 仍为 `NOT_RUN`。

## 红灯历史

### 旧基线绿但未覆盖根问题

第二轮开始时，旧测试仍为 `18/18 PASS`，但代码是同进程 `OwnerDirectory`，fixture 直接
携带全部 `owner_profiles`，receipt 无签名/PID/key/raw/time/manifest，T5 使用裸布尔。
所以这 18 项只作为回归基线，不是修复证据。

### A 的结构红灯

A 对旧产物核对得到：

```text
owner acts = 128
acts with signature/key_id/PID/raw_bytes/time/manifest = 0
controller-visible complete owner profiles = true
T5 native proof/readback = absent
```

旧 `act_hash=digest(unsigned)` 还引用未完整落盘的 ordinal，既不是签名，也无法从保存输出
独立重算完整 preimage。

### C 的主动 identity collision

C 的最初 21 项攻击全部通过。随后它新增 adversarial worker：五个真实 child 都返回可验签
receipt，但故意共用：

```text
manifest pid = 424242
process_instance_id = REUSED-PROCESS-INSTANCE
key/private-public pair = 同一组
```

修复前实际观察：

```text
accepted_receipts = 26
rejected_receipts = 0
unique manifest PID = 1
unique process instance = 1
unique key id = 1
```

C 原样运行得到 `21 PASS / 1 FAIL`。这证明“默认随机生成后恰好不同”不等于 controller
保证 owner process/key 独立。

根会话增加 actual-child PID binding 和跨 owner identity uniqueness gate 后，未修改 C 的
worker 或断言：

```text
collision 定向复跑 = 1/1 PASS
C 完整攻击复跑 = 23/23 PASS
合并测试 = 46/46 PASS
```

controller source 改动后，C 的 persisted-evidence 测试还先拒绝了旧 output manifest 中的
source hash。重新执行 runner 生成新证据后才通过，说明 source drift 能被检测。

## 最终运行

运行命令：

```bash
cd research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-012-ce001-power-restoration/g2-relation
python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 run.py
PYTHONPYCACHEPREFIX=/private/tmp/g2-fix-root-pycache python3 -m py_compile \
  g2_relation.py owner_worker.py platform_worker.py run.py \
  tests/test_g2_relation.py tests/test_adversarial.py \
  tests/test_root_fix_adversarial.py
python3 -m json.tool outputs/summary.json >/dev/null
python3 -m json.tool outputs/process-source-manifest.json >/dev/null
```

最终数字：

- 合并测试：`46/46 PASS`，严格 ResourceWarning 模式；
- 2 次完整复跑，每次 6 个场景（5 个 E2、1 个 T5）；
- 250 份 signed receipt；
- 52 个 process instance、52 个 unique PID、52 个 unique Ed25519 key id；
- 52/52 child exit code 为 0；
- 764 条 trace；
- raw bytes preserved：`true`；
- semantic rerun equal：`true`；
- semantic rerun SHA-256：
  `7fcfde6a2fad3d4034d59d71da9e0b6a14fa6ae2c9dee8b074014c79ace691c5`；
- 最终 trace canonical SHA-256：
  `dab2fe5c993e48fbbc429af9609ce1b502966132f27bd88e26e0b85f4ab5d828`。

关键 source SHA-256：

| 文件 | SHA-256 |
|---|---|
| `g2_relation.py` | `b7e6c1bc91642751bb26ec573582b4823e4d2799a850c121fdafc03a2ea5942e` |
| `owner_worker.py` | `e685f79cbeb086be055b852b6b27f661712f503c4beac3af96a8a173d42c545a` |
| `platform_worker.py` | `cd598148d15b38bb74b480d0bfe36ee2dcc90aa79ed59a76697c0daff787b3ca` |
| `run.py` | `cfe79890a11c8aaef729384590d6f311b8d24a30fb4a1d872dc940794492889c` |
| `tests/test_root_fix_adversarial.py` | `6531cbec101571d719e2bd9142e45a9ccc858b0aecbf393d194943d6a53cf76e` |

保存产物：

- `outputs/rerun-1.json`、`rerun-2.json`：完整 receipt、raw bytes、signature 和轴级结果；
- `outputs/raw-trace.json`：query、receipt 与 verification 时序；
- `outputs/process-source-manifest.json`：PID/key/source/profile hash/exit；
- `outputs/semantic-rerun.json`：剥离随机 time/key/PID 后的语义复跑；
- `outputs/summary.json`：计数、digest、复跑状态和真实性边界。

## 能支持

- 当前 local synthetic run 中五 owner 的 process/state/key 分离由 controller 强制检查，
  不只依赖随机正例；
- 每个 owner act 的 exact raw bytes、身份、来源、时间、决策和 task binding 可独立验签；
- digest 自洽但 signature 不匹配的伪造不能进入任何轴；
- controller-visible surface 不持有或反射全量 private profile 内容，定向修改一个 profile
  只改变对应 owner；
- missing policy、wrong binding、refusal、blocking/nonblocking opposition 在轴级和
  downstream gate 中保持差异；
- RelationVersion 是可重算的派生 evidence snapshot，不冒充 owner act 或 downstream truth；
- T5 applicability 来自签名 native proof + proof-bound readback，而非裸布尔；
- source 改变会使旧 persisted manifest 失效；
- 两次运行在新 key/PID/time 下保持相同语义结果。

## 不能支持

- 真人是否理解、认领、反对、拒绝或授权；
- Ed25519 receipt 的法律充分性、组织授权或现实 owner identity；
- 对恶意同一 OS 用户、本机管理员、可改 worker/profile/controller 文件者的强隔离；
- 独立外部 key registry、HSM、签名证书、组织 PKI 或跨权限域部署；
- current G5 Authority、commit-time policy head 或 delegation 法律效力；
- O_E target-native Effect、requester/venue Acceptance、Settlement；
- 真实平台产品、CMMN/CLM/IAM/workflow/HITL 或完整 CE-001 八 case；
- E2 formation operator 的现实因果性、长期关系价值或 remove-operator 现实结果；
- 强中心、成熟组合、人工制度、通用模型或新机制的赢家；
- V1/V2 一般解、真实生产恢复、正式 claim 或机制状态变化。

本地 subprocess 在同一用户、同一目录和同一 controller 下运行。当前 gate 能发现普通错路由、
manifest 伪报、key reuse、source drift 与 receipt 伪造，但不是抵抗恶意本机进程的安全证明。

## 写入边界

本轮只修改：

- `experiments/wave-012-ce001-power-restoration/g2-relation/`
- `external/codex-cli-cohort-003/G2-fix-final.md`

未修改 `COMMON.md`、`G2-PROMPT.md`、`G2-FIX-PROMPT.md`、`ROOT-LIVE-AUDIT.md`、
`G2-final.md`、CE-001 contract、`research/NOW.md`、PROGRAM、Problem、LineContract 或
机制状态。
