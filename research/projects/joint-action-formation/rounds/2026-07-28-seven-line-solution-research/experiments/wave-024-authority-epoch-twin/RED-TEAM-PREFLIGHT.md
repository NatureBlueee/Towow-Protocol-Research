# Wave 024 Authority epoch twin：独立红队预注册

日期：2026-08-01
状态：`PREFLIGHT RED TEAM / IMPLEMENTATION NOT READ / RUN NOT STARTED`

## 审计边界

本文在读取根 `AGENTS.md`、`research/NOW.md`、Wave 023 的 `RED-TEAM.md` 与
`INDEPENDENT-AUDIT.md`、Wave 016 和 Wave 020 的 root acceptance 后形成。本文形成期间没有
读取、运行或修改 Wave 024 的实现、夹具、测试、候选或 Pro 返回，因而以下攻击不是针对实现
细节补洞，而是从 Authority、Effect、Acceptance 和 finality 的 truth owner 重新构造准入门。

本文只预注册攻击与最高可宣称边界，不是实验结果，也不证明任何门已经关闭。

## 先把问题问准确

本 twin 不能直接检验：

> 一个 owner 在任意远端撤销后，所有 Target 是否立即、全局地拒绝旧 Authority。

在异步跨域系统中，owner 的撤销与 Target 的提交如果没有可验证的 happens-before，就没有
足够事实判定哪一个“先发生”。依赖两台机器的 wall clock、controller 写入的时间戳，或“先
调用 revoke 函数、后调用 execute 函数”的脚本顺序，都不能建立跨域线性顺序。

当前可检验的尖锐问题应当是：

> 在冻结的本地数字世界中，当 Target 自己已经原生、持久地接收并确认 exact delegation 的
> 新 Authority fence 后，携带旧 epoch 的同一 exact request 能否仍在 Target 线性化点提交；
> 当 fence 尚未推进且 delegation 在该线性化点 current 时，同一请求能否在 ACK 丢失与进程
> crash 后被准确恢复，同时不产生第二次语义 Effect。

这里的唯一干预量不是 `case_label=S/R`，而是：

```text
TARGET_NATIVE_FENCE_AT_EXECUTE_LINEARIZATION = e      # S
TARGET_NATIVE_FENCE_AT_EXECUTE_LINEARIZATION = e + 1  # R
```

owner 的 revoke 只有在 Target 产生 durable `FENCE_ADVANCED(e+1)` ACK 之后，才有资格进入 R。
若 revoke 与 execute 不能排序，该样本必须是 `CONCURRENT_OR_UNORDERED / NOT SCORED`，不能按
预期标签补写成 R。

## 冻结 twin 的最小因果形状

### 共同前缀

S/R 必须具有相同的：Q bytes、Target、object、semantic occurrence key、operation/request
bytes、delegation scope、delegate、candidate executable、launch surface、executor 收到的
bytes、初始 Target state、initial owner head、故障注入程序和恢复程序。直到隐藏 Authority
干预发生前，两个世界的可观察 transcript 必须逐字节相同。

### S：current at commit

1. owner-native head 证明 exact delegation `D@e` 对 exact Q/Target/object/operation/delegate
   current；Target durable fence 仍为 `e`；
2. 同一 executor request 到达 Target；Target 在**同一个原子线性化事务**内重算 scope、expiry、
   head 与 `presented_epoch == durable_fence == e`，并提交一次 exact semantic occurrence；
3. Target 先持久化 decision/receipt/readback，再向 executor 发 response；独立 transport fault
   domain 丢弃 response，随后独立 supervisor 终止 executor；
4. 恢复进程只从 outcome-agnostic pre-crash state 出发，对 exact request/operation/Target 做
   authoritative status/readback；它识别已提交并且不重试 Effect；
5. O_Q、O_V 在读取 exact Target-native readback 后分别产生 Acceptance；O_P 在读取两份
   Acceptance 与同一 readback 后产生 finality。

### R：Target 已消费撤销

1. 在共同前缀后，owner-native head 撤销 exact `D@e`；Target 原生、持久地推进 fence 到
   `e+1` 并向 root 返回 ACK；该 ACK happens-before 同一 execute request 的 ingress；
2. 与 S 完全相同的 executor request 到达同一 Target implementation；Target 在原子线性化
   事务中拒绝旧 `e`，持久化 `REJECTED_STALE_AUTHORITY`，exact semantic Effect 为零；
3. 与 S 相同的 response-loss 和 crash 边界发生；恢复查询得到 covered-through-current-head 的
   revoked/negative status，并且不以新 request ID、operation ID、capability 或 Target alias
   重试；
4. 可以产生 `REVOCATION_HANDLING_ACK` 或 protective-success 评价，但不得把它写成 Effect
   Acceptance、任务完成或 O_P finality。

S/R 的首次 candidate-visible 差异应来自 crash 后的 Target-native exact status/readback。若 R
在提交前直接获得 `REVOKED` label、不同错误形状、不同路径或不同延迟，实验测到的是 candidate
对泄漏标签的分支，不是 Target Authority fence 的因果作用。

## 可执行反例矩阵

每一项都应作为真实 mutation 重新生成全部普通哈希后运行；只因旧哈希失配而拒绝不算关闭。

| ID | 可执行攻击 | 会制造的假结果 | 必须观察到的拒绝或原生证明 |
|---|---|---|---|
| `A01-SELF-SIGNED-AUTHORITY` | 为 S/R 新建一套 fixture key，自行签 grant/revoke/head，再同步替换 registry 和所有普通哈希 | 任意夹具都能自称合法 current/revoked | 信任根必须在本次 world/fixture 之前由独立 Principal registry 锚定；换根后即使全量重签也拒绝 |
| `A02-CONTROLLER-OWNS-OWNER-TRUTH` | controller 直接写 owner DB，或用持有的 O_Q/O_V/O_P 私钥生成 owner head、Acceptance 和 finality | scheduler 代替现实 owner 决定 Authority 与接受 | controller 没有 owner private key/DB 写权；receipt 的 OS/process/key/store provenance 来自独立 owner domain；controller key 伪造被拒绝 |
| `A03-WRONG-SCOPE-OR-REAUTH` | revoke 另一 delegation、delegate、Target、operation 或 scope；或 revoke 后追加 successor grant，却继续把 `D@e` 标为最终 revoked | unrelated revoke 被当作因果变量 | owner head chain 必须精确绑定 delegation ID、Q、object、Target、operation、delegate、scope、expiry；提交点前不得有恢复 Authority 的 successor |
| `A04-TOCTOU-CACHED-CURRENT` | executor/Target 在 t1 查询 `CURRENT`，t2 owner revoke 且 Target durable fence=e+1，t3 仍用缓存布尔值提交 | “做过 Authority check”冒充 commit-time currentness | scope/head/fence 比较与 Target commit/reject 在同一线性化事务；改变 t2 后 S commit 必须变成 R stale-fence reject |
| `A05-FAKE-REVOKE-ORDER` | 让 commit 实际先发生，再用可调 wall clock 或 controller event order 把 revoke 标成更早；或 revoke 后未等 Target ACK 就执行 | 把 unordered/late revoke 写成 R 的零 Effect | owner revoke → Target durable `FENCE_ADVANCED` ACK → Target ingress/linearization 形成可重算跨域链；不满足者为 `UNORDERED`，不得评分 |
| `A06-WRONG-REJECTION-CAUSE` | 让 R 因 deadline、safety、version conflict、missing capability 或 controller 不发送请求而零 Effect，最后把 reason 改名为 revoked | 相关性被包装成 stale-epoch causality | Target-native ingress 证明 exact request 确实到达；decision receipt 必须记录实际比较的 presented epoch、durable fence、exact authority head 和唯一 rejection reason |
| `A07-TWIN-LABEL-LEAK` | 在 filename、path、env、argv、key ID、epoch明文、payload 长度/顺序、响应延迟或可字典反查的 hash 中编码 S/R；或为两边使用不同 runner | candidate 主动选择“该成功/该拒绝”的脚本 | candidate-visible pre-decision bytes、launch、代码与 I/O shape 同形；commitment 使用不可字典反查的 root secret/nonce；只允许预注册 hidden intervention diff |
| `A08-HELPER-COMMITS-S` | candidate 不发请求，由 controller/helper 对 Target 提交 S；R 中 helper 不提交 | 同样 Target state 被误归因为候选和 Authority | Target ingress、request signature、executor process/connection 与 commit actor 必须闭合；helper/controller actor 的 matching state 是外因，pair 不成立 |
| `A09-FAKE-ACK-LOSS-OR-ASYMMETRIC-FAULT` | controller 写 `ack_lost=true` 但 response 实际已被 worker 读取；或只在 S 丢 ACK、R 直接看到 reject；或 crash 在 Target decision 之前 | 不同故障路径被误当 Authority 差异 | 独立 transport proxy 证明 decision 已 durable、response 发出后被丢弃且 worker 未读取；独立 supervisor 证明两边同一边界 crash |
| `A10-STALE-FENCE-ON-RESTART` | Target 或旧 runtime crash/reopen 后把 durable fence 从 e+1 回退为 e，旧 worker 再执行；或新 runtime 只在内存拒绝旧 epoch | 正常一次拒绝掩盖恢复后的 unauthorized Effect | Target fence store 经 crash/restart 保持单调；预冻结旧-runtime restart 必须真实运行，所有旧-epoch execute 在重启后仍被 Target-native fence 拒绝 |
| `A11-DUPLICATE-BY-ALIAS` | S 在 ACK 丢失后用新 request/operation/capability ID 重做同一语义动作；R 改 Target alias、直接写底层 store 或调用第二 endpoint | evaluator 只数 exact operation ID，报告 no-duplicate/zero Effect | Target-native semantic occurrence key 与 alias closure 覆盖所有 mutation endpoint；审计 exact Target 及 aliases、全部 request IDs 和 transient history，S=1、R=0 |
| `A12-TRANSIENT-OR-OFF-LEDGER-EFFECT` | R 先 energized 再 rollback，最后 state 为零；或写另一个 circuit/side-effect sink；或绕过 operation ledger 直接写 Target DB | 最终 snapshot 的零被当作“从未发生 Effect” | 唯一 mutation reference monitor/append-only Target history + 独立状态 timeline 证明全区间无 exact semantic occurrence、无 transient、无 bypass；否则只能说 final state zero |
| `A13-FAKE-NEGATIVE-READBACK` | 用 stale replica、旧 negative、错误 Target/operation、无 covered head 的“not found”，或 self-configured Target key 回答 R | 证据缺失被升级为零 Effect/REVOKED | Target registry 预锚 key；nonce-bound signed status 绑定 request/operation/semantic key/current ledger head/coverage range/rejection receipt；负结果必须来自唯一 mutation boundary |
| `A14-FAKE-POSITIVE-READBACK` | S 返回签名 positive，但 receipt、commit、readback 分属不同 Target/actor/version，或 readback 由 controller capsule复制 | ACK 丢失恢复看似成功 | Target-native receipt/readback/commit/head/semantic occurrence 内容哈希闭合；恢复进程必须实际查询 authoritative Target，controller summary/capsule 不作为 truth |
| `A15-DUPLICATE-HIDDEN-BY-COMPACTION` | 先产生两次 Effect，再让 ledger compaction、rollback 或 final snapshot只保留一次 | `occurrence_count=1` 假绿 | append-only semantic occurrence history 与 Target DB physical/logical snapshot同时冻结；compaction 映射保留 predecessor heads和全部 occurrences |
| `A16-FAKE-ACCEPTANCE-FINALITY` | controller 预先生成 O_Q/O_V/O_P receipt；同一 key 扮演三者；重放旧 operation 的 Acceptance；先 finality 后 readback | Target Effect 自动推出主体接受与最终性 | 三个独立 owner domain 原生签名，分别绑定 exact Q/Target/operation/commit/readback hash/current owner head；顺序为 readback→双 Acceptance→finality，角色/Principal alias 被拒绝 |
| `A17-PROTECTIVE-SUCCESS-CONFLATION` | 将 R 的正确安全拒绝同时记作 task success、Effect Acceptance 和 finality | 零 Effect 世界也被算作任务已完成 | 结果向量分离 `handling_correct`、`task_effect`、`Effect Acceptance`、`finality`；R 最多是 revoked protective handling，不是 effect completion |
| `A18-POSTHOC-ROOT-REWRITE` | 运行后修改 world、evaluator、receipt 或结论，再重算 manifest、自哈希、测试和本地 `ROOT-ACCEPTANCE` | 同目录作者可让任何结果最终全绿 | 运行前锚定 code/Q/world-diff-mask/trust roots/evaluator/RNG，运行后由 worker 无权改写的外部 append-only 或签名 root 绑定全部 native receipts；仅 `0444` 与本地 self-hash 不足 |

## 对 CL-024 四项 claim 与独立事实域的逐项映射

事实域缩写仅用于本表：

- `PA`：Principal/Authority 独立 key、registry、delegation/revocation head；
- `T`：Target currentness gate、operation ledger、Effect/refusal、status/readback；
- `CR`：Candidate runtime 的真实进程、启动面、输入输出；
- `Q/V/P`：O_Q、O_V、O_P 三个独立 append-only owner 域；
- `C`：Controller 只冻结/调度/收集，不产出任务 truth；
- `R`：Root evaluator 与运行前/后独立锚。

| 攻击 | `CURRENTNESS` | `EXACTLY-ONCE-RECOVERY` | `NATIVE-POSTCONDITIONS` | `ISOMORPHIC-BLINDNESS` | 必须独立的事实域 |
|---|---:|---:|---:|---:|---|
| `A01` self-signed root | 主攻击 | 间接 | 间接 | — | `PA + R`；fixture/controller 不能定义自己的 Authority root |
| `A02` controller 代写 owner truth | 主攻击 | 间接 | 主攻击 | 间接 | `PA + Q/V/P + C + R`；controller 只能收集不可伪造的 native receipt |
| `A03` wrong scope / reauthorization | 主攻击 | — | 间接 | — | `PA + T + R`；两域共同绑定 exact delegation/head/scope |
| `A04` cached-current TOCTOU | 主攻击 | 间接 | — | — | `PA + T + R`；Target 线性化事务消费 current head/fence |
| `A05` fake revoke order | 主攻击 | — | — | — | `PA + T + C + R`；controller 调度不等于跨域 happens-before |
| `A06` wrong rejection cause / no ingress | 主攻击 | 间接 | — | 间接 | `T + CR + R`；Target ingress 与 native reason 闭合 |
| `A07` public-prefix label leak | 间接 | 间接 | — | 主攻击 | `CR + C + R`；比较 actual visible bytes，不信 plan 声明 |
| `A08` helper/controller commits S | 间接 | 主攻击 | 间接 | 主攻击 | `CR + T + C + R`；Target ingress actor 必须是 frozen candidate path |
| `A09` fake/asymmetric ACK loss | — | 主攻击 | 间接 | 主攻击 | `T + CR + C + R`；Target decision、drop、未交付、termination 有连续 receipt |
| `A10` restart fence rollback | 主攻击 | 主攻击 | — | — | `PA + T + CR + R`；持久 fence 经真实 reopen 后仍单调 |
| `A11` duplicate by alias | — | 主攻击 | 间接 | — | `T + CR + R`；semantic occurrence/alias closure，不只 exact operation ID |
| `A12` transient/off-ledger Effect | — | 主攻击 | 主攻击 | — | `T + R`；Target 唯一 mutation boundary 与全时段 history |
| `A13` fake negative readback | 间接 | 主攻击 | 间接 | — | `T + PA + R`；current-head covered authoritative negative |
| `A14` fake positive readback | — | 主攻击 | 主攻击 | — | `T + CR + R`；恢复进程真实 query，controller capsule 不作 truth |
| `A15` compaction hides duplicate | — | 主攻击 | 间接 | — | `T + R`；append-only predecessor/occurrence closure |
| `A16` fake Acceptance/finality | — | 间接 | 主攻击 | — | `Q/V/P + T + R`；三 owner 域与 exact readback 顺序闭合 |
| `A17` protective success conflation | 间接 | 间接 | 主攻击 | — | `T + Q/V/P + R`；handling 与 Effect/Acceptance/finality 分型 |
| `A18` posthoc root rewrite | 主攻击 | 主攻击 | 主攻击 | 主攻击 | `PA + T + CR + Q/V/P + C + R`；运行外不可改写锚 |

表中的“间接”表示该攻击不只会污染一个 claim。例如 self-signed Authority 首先使
`CL-024-AUTHORITY-CURRENTNESS` 无法成立；若继续沿该假根生成 readback 和 Acceptance，也会让
后两项看似闭合。四项必须逐项判定，不得因同一个全绿 artifact 将污染同时升级为四项支持。

### controller 代写的跨 claim 攻击面

`Controller` 是本轮最容易从“受信调度器”漂移为“万能 truth author”的位置。以下任何一个
发生，都应直接拒绝相应 claim，而不是因为 controller 签过总 manifest 而接受：

| controller 越界行为 | 被伪造的事实 | 必须替代它的原生域 |
|---|---|---|
| 现场生成 Principal registry、owner key 或 delegation/revoke head | current / revoked Authority | `PA` 预锚 registry 与 owner head chain |
| 写 Target ingress、fence、commit/refusal、status 或 readback JSON | commit-time gate、Effect、零 Effect、恢复结论 | `T` 的原子 gate、ledger 与 signed readback |
| 写 `ack_lost=true` 或仅终止进程但不证明 response 未交付 | ACK-lost recovery prefix | `T/CR` 之间独立 fault boundary + process supervisor receipt |
| 以 helper 身份执行 S，或在 R 不把同一 request 送达 Target | candidate 行为与 Authority 因果差值 | `CR` actual outbound + `T` ingress/actor binding |
| 写 O_Q/O_V Acceptance 或 O_P finality | 主体接受与最终性 | `Q/V/P` 独立进程、key、store |
| 选择不同 runner、路径、handle 或错误形状 | isomorphic public prefix | `R` 对 actual launch 与 candidate-visible byte transcript 的比较 |

controller 可以冻结 world、持有 hidden assignment、调度 revoke/drop/termination 并收集文件；
它不能因为知道预期 S/R 就生成能够决定 evaluator 结果的 owner/Target/postcondition receipt。

### public-prefix 同形的专门攻击门

`CL-024-ISOMORPHIC-BLINDNESS` 不能用“两边 schema 相同”或“都只有 opaque handle”验收。必须
对真实 candidate-visible surface 做以下攻击：

1. **值级 dictionary attack**：只含 S/R 两种 preimage 的普通 SHA-256 即使不写 label，也可
   由 candidate 枚举反查。公开 commitment 必须含 candidate 不可见的 root nonce/secret；
2. **opaque handle attack**：交换或重采样 handle 后，candidate disposition 不应随 handle 值
   固定翻转。handle 长度、前缀、排序、映射表位置都不能与 S/R 相关；
3. **launch metadata attack**：比较 actual binary hash、argv、env、cwd 内容及 metadata、FD、
   process name、network endpoints、TLS/key IDs、可读取文件树；任一 treatment-specific value
   都使 twin 无效；
4. **error/timing attack**：在第一个 lawful response 前，response count、shape、length、顺序、
   timeout、retry/backoff、rate-limit 与可观测延迟不得由 case 决定。若不能消除 timing side
   channel，就必须降级 blindness claim；
5. **out-of-band inspection attack**：candidate 尝试枚举邻接目录、进程、socket、共享 DB、
   environment、controller log 或 external endpoint；任何能恢复 hidden assignment 的通道必须
   被关闭或记录为 claim failure；
6. **bespoke-runner attack**：保持所有 public packet 相同但交换 S/R runner/world root。若结果
   仍跟 runner 而非 native Authority intervention 走，说明存在隐藏 decision root；
7. **earliest-divergence audit**：root 必须逐 byte 找到实际 transcript 首差异，并证明它是
   `PA/T` 原生 lawful response 或其 crash 后 authoritative recovery response；更早差异一律拒绝；
8. **same-request reachability**：R 的零 Effect 只有在 S/R actual outbound request bytes 相同且
   均有 Target-native ingress receipt 时才可参与因果比较。candidate 提前 abstain 虽然可能安全，
   但不能检验 Target currentness gate。

这些门不要求让 Target 看不到 epoch；Target reference monitor 正是需要消费 hidden Authority
state 的域。它要求 candidate 在 lawful native response 前看不到哪个 world 被分配，并要求
Target 的差异来自其原生 fence，而不是 controller/runner 暗示答案。

## 必须由原生域产生的 receipt

### 1. Principal / Authority root domain

- 运行前已经存在的 Principal→owner key registry 锚；不得由 twin fixture 现场定义自身合法性；
- owner-native append-only grant/revoke/head chain，绑定 exact delegation、Principal、delegate、
  Q、object、Target、operation、scope、expiry、revision 和 predecessor head；
- currentness/non-currentness 由完整 head chain独立推导，不接受 controller 的 `authority=current`；
- owner revoke receipt 与 Target 对该 exact head/epoch 的 durable consume ACK。

这些 receipt 在本地只能证明“相对于冻结信任根的合成 Authority”。没有现实 Principal 的
认领和外部法律/制度绑定时，不得写成 lawful/legal Authority。

### 2. Target Authority-fence domain

- 单调持久的 Target fence ledger，含 predecessor、authority-head hash、applied epoch、durable
  version 和 apply process；
- exact execute ingress receipt，证明 S/R 相同 request bytes 实际到达；
- commit/reject 线性化 receipt，原生记录 presented epoch、durable fence、scope/expiry/head
  verdict、decision reason 与 Target version；
- fence、decision 与 Target state 必须由同一 Target reference monitor 原子关联，不能由
  controller 把三个日志拼在一起。

### 3. Target Effect / status / readback domain

- 唯一 mutation boundary 的 append-only operation/semantic-occurrence ledger；
- exact commit 或 stale-fence rejection receipt；
- nonce-bound authoritative status 与 readback，绑定 current head、coverage、request、operation、
  semantic occurrence key、Target、commit/reject receipt 和 observed state；
- 全 Target alias/endpoint closure 与全时间段 mutation timeline；R 的零 Effect 需要证明没有
  transient、rollback-before-readback、alternate ID 和 bypass，而不只是最终 state=0；
- 数据库物理/逻辑快照及 companion/WAL 边界，避免 ledger 实际状态不在冻结文件内。

### 4. Fault / process domain

- transport proxy 的 `TARGET_RESPONSE_EMITTED → RESPONSE_DROPPED → EXECUTOR_NOT_DELIVERED` receipt；
- OS/supervisor 的 executor process identity、exit reason、crash point、restart identity；若只是
  受控 SIGKILL，表述为 controlled hard termination，不称 unannounced physical crash；
- executor 的 actual launch 与 I/O transcript，证明两边同一 binary/argv/env/cwd/fd/network、
  相同 pre-decision bytes、相同 outbound execute，以及恢复后的 exact status query；
- 预冻结 old-runtime restart probe，证明 crash/restart 后 persistent fence 仍拒绝旧 epoch。

### 5. Acceptance / finality owner domains

- O_Q、O_V 分别从自己的进程、key 和 append-only store 产生 Acceptance；
- 每份 Acceptance 必须绑定 exact readback/commit、Q、Target、operation、owner head 与其实际
  接收的 evidence bytes；
- O_P 只在双 Acceptance 后对同一闭包产生 finality；
- R 的 revocation/refusal receipt 使用不同 schema，不得复用 S 的 Effect Acceptance/finality。

### 6. Independent root domain

- 运行前锚：contract、完整 Q、candidate bytes、两世界 preimage、允许的唯一 hidden diff、
  treatment assignment commitment、所有 trust roots、target/owner/evaluator/fault-injector 代码；
- 运行后锚：actual launch、owner heads、Target fence、ingress/decision/Effect/readback、ACK drop、
  crash/restart、Acceptance/finality、DB 快照、所有攻击输出与 independent evaluator bytes；
- root 必须位于 worker/controller 无写权的权限域或外部 append-only/Git object/签名系统；
  同一目录里可同步重算的 self-hash 只提供内容寻址，不提供事后替换抵抗。

## 独立 evaluator 的 fail-closed 规则

1. controller 的 `PASS`、result summary、fixture status 与 expected label 全部不可信；只从上述
   原生 receipt 重算。
2. 任一关键 receipt 缺失、签名根未锚定、head coverage 不完整或跨域顺序不可判定，结果为
   `INVALID` 或 `UNKNOWN`，不能用预期 S/R 补齐。
3. twin 只要一侧无效，pair causal claim 整体不成立；不能保留另一侧的差值结论。
4. S 需要同时满足：commit-time current、exact semantic occurrence=1、ACK 真丢失、恢复 query
   命中同一 commit、Effect retry=0、双 Acceptance、finality。
5. R 需要同时满足：Target durable fence advance happens-before ingress、exact stale-fence reject、
   exact semantic occurrence=0、ACK 真丢失、恢复 query 得到 current-head covered reject、任何
   old/new-ID retry Effect=0、Effect Acceptance=0、finality=0。
6. R 因其他原因零 Effect 是正确的安全结果也不能支持 Authority 因果主张；必须保留真实 reason。
7. S/R 的 same-shape 审计必须比较真实 candidate-visible bytes 与 actual launch，不比较字段名。
8. 测试应至少全量重签/重哈希执行 `A01–A18` 的代表性 mutation；旧哈希失配只证明 seal 生效，
   不证明 semantic gate 生效。

## 最小攻击集：任何验收前不可删减

若实现阶段只能先执行最小集合，至少必须包含以下八组；任一未关闭就不能运行正式 twin：

1. **Authority root substitution + controller impersonation**：合并 `A01/A02/A03`；
2. **commit-time atomicity + verified happens-before**：合并 `A04/A05/A06`；
3. **same-shape/no-label-leak + same actor/request**：合并 `A07/A08`；
4. **真实且对称的 ACK loss/crash**：`A09`；
5. **restart 后 persistent fence 与旧 epoch 重放**：`A10`；
6. **semantic duplicate/zero-Effect/readback closure**：合并 `A11–A15`；
7. **owner-native Acceptance/finality 与 protective-success 分型**：合并 `A16/A17`；
8. **pre-run external root anchor，抵抗全量事后重写**：`A18`。

这八组关闭的是不同 truth domain，不能用更多 controller 日志、更多 schema 字段或一份总签名
互相替代。

## 最高可宣称边界

只有所有原生门和最小攻击集均通过，才最多可以声明：

> 在本次冻结的本地合成数字世界、预锚的合成 Principal/Target/owner 信任根、独立 root 与
> 合作式进程隔离边界内，现有成熟组件组合——版本化签名 delegation/revocation、Target-native
> 持久 epoch fence、commit-time 原子 Authority gate、幂等 semantic operation ledger、签名
> status/readback、crash recovery，以及 owner-native Acceptance/finality——区分了一个
> current-at-linearization 世界与一个 Target 已持久消费 revocation 的世界。前者在 ACK 丢失和
> controlled crash 后恢复为恰好一次 exact digital Effect，后者对相同 request 拒绝旧 epoch
> 且 exact digital Effect 为零；指定攻击未能制造重放、假零 Effect 或假 Acceptance。

若 same-shape 与 happens-before 都成立，这可以支持一个有界的机制因果判断：

```text
TARGET-CONSUMED AUTHORITY FENCE
  caused the TARGET decision difference in this frozen digital twin,
  under the stated trust and isolation assumptions.
```

它仍然不能证明：

- fixture key 对应现实 Principal、法律授权、制度接受或真实 owner 意志；
- 物理电路 Effect、现实世界全局零 Effect、生产可靠性或跨机器即时撤销；
- 对恶意同用户/同目录 writer、OS/内核攻击或 root 私钥失陷的抵抗；
- 未观察到的并发、网络分区、owner equivocation、再授权、长期 drift 或 provider lifecycle；
- A1–A5 的公平比较、成本赢家、CE-001 全部 case，或 Problem V1/V2 已解决；
- 新 Towow 机制具有必要性。若上述成熟组合完整解决本作用域，它本身就是正向通爻方案结果。

在只具备 fixture self-signature、controller-shaped receipt 或本地可重算 root hash 时，最高表述
仍应停留在：

```text
DEVELOPMENT FIXTURE / ATTACK DESIGN ONLY
AUTHORITY, EFFECT, ACCEPTANCE AND FINALITY NOT ESTABLISHED
```
