# Wave 024 runtime design

日期：2026-08-01  
状态：`MIXED SCOPED RESULT / INDEPENDENT EVALUATOR PASSED`

## 解决的有界问题

本实现不创造新的宏大协议。它把成熟的签名凭据、单调 fencing token、SQLite 串行事务、
operation ledger、ACK-lost status/readback 与 owner-native append 组合成一个本地高保真 twin，
专门检验：

> 对 exact Q、object、Target、operation 和 delegation，Target 已持久消费的 superseding
> Authority fence 能否与 Effect/refusal 共用一个 Target-local 线性化边界；candidate 在结果 ACK
> 丢失并被终止后，能否只靠 Target-native exact status/readback 恢复且不 replay。

这是 `CL-024-TARGET-CONSUMED-AUTHORITY-FENCE`，不是 Authority-global instantaneous
revocation。Authority 已撤销但 Target 尚未 durable ACK 的 U 世界明确不评分。

## 独立运行域

实际运行由以下本地进程组成，私钥均在各自进程内生成，controller 只接收公钥和签名结果：

- Principal/Authority service：签发 exact delegation 与 matching revocation，并写
  `authority-native.sqlite3`；它在启动时固定 lab root，签 successor revocation 前自行验证
  完整 S Target certificate、receipt signature、Q/object/Target/operation、epoch/head、decision
  与 Effect，而不是签 controller 提供的裸 hash；
- lab key registry：为各 Target 自生成公钥签本地合成证书，并写
  `lab-key-registry.sqlite3`；
- Target reference monitor：拥有唯一 mutation boundary、durable fence、Effect/refusal、
  exact status/readback 与 `target-native.sqlite3`；
- candidate source/recovery：同一个 `twin_runtime.py` artifact 的两个真实进程；
- ACK-drop proxy：真实消费 Target receipt，验证后写自己的 drop receipt，但不向 candidate ACK
  channel 投递；
- O_Q、O_V、O_P：分别生成自己的 key、写自己的 SQLite owner store；
- controller：只冻结输入、安排 S/R/U 干预、释放 ingress、外部 `SIGTERM` source 并收集文件。

这些进程仍共享同一个本机用户和文件系统，因此这里只建立 cooperative local process separation，
不建立 hostile same-UID isolation。

## 跨域前驱修复

最初冻结运行把 S `target_receipt_sha256` 交给 Authority 签入 revocation，但 Authority 没有验证
产生该 hash 的完整 Target-native evidence。哈希相等只证明 controller 送入了同一字符串，不能
单独证明 Authority 确认了前驱事实。该运行已降级。

当前实现先启动 lab registry，再把其公钥作为 Authority 进程的启动时固定信任根。Authority
收到完整 S receipt 后，独立验证 lab certificate、Target signature、committed Effect、exact
scope，以及 Target 在 commit 时消费的 delegation epoch/head；验证通过才产生 revocation，
并在签名记录中绑定 receipt、certificate、request 与 Effect。controller 只运输证据，不能用
任意字符串制造前驱。

## Target-local 原子性

Target 的 `APPLY_AUTHORITY` 与 `EXECUTE` 都进入同一个 SQLite state machine。

`APPLY_AUTHORITY` 在 `BEGIN IMMEDIATE` 内验证签名及 exact
delegation/principal/actor/Q/object/Target/operation、连续 epoch 与 predecessor head，然后同时：

1. 追加 durable Authority head；
2. 追加 `FENCE_ADVANCED` native event；
3. commit 后才返回 Target-signed durable ACK。

`EXECUTE` 先验证 exact request/delegation 绑定、grant schema/status、epoch、有效期和完整 desired
state，再在另一个 `BEGIN IMMEDIATE` 中同时：

1. 重读 Target 当前 durable fence；
2. 追加 exact request ingress；
3. 以 `presented epoch/head == durable CURRENT fence` 作为唯一 current 条件；
4. current 时 CAS 写一次 exact Effect，否则写一次 `REJECTED_STALE_EPOCH`；
5. 在同一事务保存 Target-signed receipt。

因此在 exact Target 上，`FENCE_ADVANCED` 与 `REQUEST_INGRESS / EFFECT_COMMITTED` 具有一个可重算
的本地顺序。R 只有在 Target durable matching fence ACK 已返回后才释放 candidate ingress；U
虽有 Authority revocation record，却不向 Target 安装 fence，结果固定标记为
`CONCURRENT_OR_UNORDERED/NOT_SCORED`。

## ACK 丢失与恢复

source 先把 exact request 写入自己的 durable SQLite state，再向 Target 发送一次请求。Target
receipt 被独立 proxy 消费、验证、持久记录为 `candidate_ack_delivered=false`；source 阻塞在真实
ACK queue 上，controller 随后用 `SIGTERM` 终止它。

recovery 是新的进程。它重开 source DB，向同一 Target 查询 exact request status/readback，验证
Target 证书及两份签名，然后：

- S：认出历史 `COMMITTED` 与 Effect count 1，返回 `RECOVERED_COMMITTED_NO_REPLAY`；
- R：认出历史 `REJECTED_STALE_EPOCH` 与 Effect count 0，返回
  `RECOVERED_REVOKED_NO_RETRY`。

两边的 `ack_received_count=0`、`retry_execute_count=0`。fence 不改写已经发生的历史 decision。

## 原生后置条件

只有 recovery 验证出 exact committed Effect 时，controller 才把同一 Target-native evidence 交给
O_Q 与 O_V。二者在自己的进程中再次验签并各追加一份 Acceptance。O_P 验证两份独立签名、Q
与同一 Effect ID 后追加一次 finality。R 的三个 owner store 保持零事件；拒绝不会被包装成
Effect Acceptance 或 task finality。

## 复用与新增

| 来源 | 复用的成熟能力 | 本轮没有重复发明的内容 |
|---|---|---|
| Wave 015 | SQLite `BEGIN IMMEDIATE`、CAS、Target ledger、signed receipt/readback | exact-once local transaction pattern |
| Wave 016 | ACK lost 后 status/reconcile、禁止盲 retry | recovery state machine |
| Wave 020 | durable fence/history、外部终止、owner-native postconditions | local fencing 与主体后置条件分离 |
| 通用成熟技术 | Ed25519、独立进程、SQLite FULL synchronous、append-only rows | 密码学和数据库基础 |

本轮实际新增的研究组合只有：

- exact object/Target/operation scope 的 Authority head 被 Target 原生消费；
- fence gate 与 semantic Effect/refusal 在同一 Target transaction；
- S/R 加 U 负控，使 Target-consumed currentness 与 Authority-global currentness 不再混淆；
- 独立 ACK-drop proxy + source hard termination + new-process readback recovery；
- 同一 frozen candidate startup surface 在 S/R/U 的记录级比较。

独立 evaluator 已确认这套成熟组合闭合三个有界主张：Target-consumed fence、ACK-lost
exact recovery 与 cooperative owner-native postconditions。它因此是正向 Towow 解决方案，
不需要为了“独占性”再制造额外机制。完整同形盲性没有成立，不能由前三项成功带过。

## 明确未建立

- `CL-024-GLOBAL-AUTHORITY-CURRENTNESS`：`NOT_TESTED`；
- Target 自身 crash/restart 后 fence persistence：`NOT_TESTED`；
- hostile same-UID 枚举、旁路写入和 timing blindness：`NOT_ESTABLISHED`；
- worker 无法改写的 external append-only root：`NOT_ESTABLISHED`；
- 法律 Authority、真实物理供电、生产可靠性、A1–A5 对比、V1/V2 整体解决：均不声称。

`CL-024-ISOMORPHIC-BLINDNESS` 的 recorded cooperative startup surface equality 成立，但完整
claim 因固定运行顺序、同 UID 文件/进程可见性与 timing side channel 被独立 evaluator 判为
`FAIL`，不能升级为 hostile blindness，也不能直接进入 A1–A5 公平比较。
