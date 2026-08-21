# Wave 005-B cross-authority receipt simulation

状态：`LOCAL_CROSS_AUTHORITY_SIMULATION_IMPLEMENTED`

## 这轮解决了哪个具体缺口

Wave 004-A 的 controller 同时写 delivery store、执行 readback、签发 receipt；holder 只有
冻结 hash，没有签名，第一 recipient 也没有独立签发 onward authorization。因此它能检验
受信单 controller 内的执行一致性，不能阻止 controller 把自己的记录伪装成跨 Authority
执行证据。

本实验把同一有界问题拆成四种权限域：

1. `HolderAuthority`：签发授权，独立维护 issued/revoked 状态并签发当前状态；
2. `CrossAuthorityController`：编排状态机并签 controller receipt，但没有 recipient 或
   anchor 的私钥；
3. `RecipientAuthority`：独立 prepare、commit、abort，并为 derived route 的 onward
   跳签发自己的 authorization；
4. `ExternalAnchor`：独立维护 append-only hash chain，并为每个 decision/checkpoint
   签名。

签名采用环境已有 `cryptography` 的 Ed25519。仓库中的私钥是测试代码里可复现的合成密钥，
只用于本地模拟；controller 实现只接收自己的私钥和其他域的方法端点。

## 三种有界动作

- `DIRECT`：holder 签名授权 → recipient `PREPARED_ACK` → anchor `COMMIT` →
  recipient `COMMIT_ACK` → anchor complete/route-complete → controller receipt。
- `DERIVED`：第一跳完成后，第一 recipient 必须用自己的 key 为精确的第二跳签发
  `ONWARD_AUTHORIZATION`；controller 不能从源 holder 的 `max_depth=1` 自行制造 onward
  已执行事实。
- `RECIPROCAL`：双方先独立 prepare，唯一 anchor `COMMIT` decision 同时绑定两个
  `PREPARED_ACK`；controller 只有拿到双方独立 `COMMIT_ACK` 后才允许返回 `EXECUTED`。

`RECIPROCAL` 的 all-or-nothing 是**决定与成功声明层**的：崩溃可能造成一个 recipient 已
materialize、另一个尚未 materialize 的短暂恢复窗口；anchor 中只有一个同时包含双方的
不可分裂 COMMIT decision，controller 此时没有成功 outcome，恢复后补齐另一侧并获得双方
ACK。它不是物理意义的同时可见，也不声称解决 Byzantine atomic commit。

## 已验证的失败与恢复

12 个回归覆盖：

- controller 用自己的 key 伪造 recipient ACK：拒绝；
- 修改已持久化 ACK 的 payload/signature：恢复时重新验签并拒绝；
- holder 在 reservation 前撤销：不创建 controller/anchor 状态；
- holder 在 prepare 后、COMMIT decision 前撤销：签发 ABORT，recipient 不 commit；
- anchor 即使持有正确 anchor key，但签出不延伸 controller pinned head 的 fork：拒绝；
- reciprocal 在第一侧 commit 后崩溃：没有成功 outcome；恢复后补齐第二侧；
- anchor decision 后崩溃：复用原 decision，不追加第二个 COMMIT；
- exact replay：controller 与 anchor bytes 不变；同 key 不同 command 拒绝；
- holder v1 key 在 step 7 已过期：拒绝；轮换后的 v2 key：成功；
- direct、derived、reciprocal 的正常路径分别需要 1、2、2 个 recipient commit ACK。

运行：

```bash
python3 -m unittest discover -s tests -v
```

## 证据边界

本实验只支持以下有界结论：

> 在固定合成 contract、诚实执行的域服务、独立 Ed25519 keys、单个外部 anchor 视图和可恢复
> 本地持久化下，controller 无法仅凭自己的签名制造 recipient ACK；direct、derived 和
> reciprocal 可以把授权、recipient acknowledgement、anchor decision 与 controller
> outcome 分开验证。

不支持：

- OS/容器级进程隔离、HSM 或真实密钥托管；
- 多观察者 gossip、透明日志或对恶意 anchor 向不同 client 等价签发不同历史的完整检测；
- Byzantine consensus、网络分区下的可用性、跨数据库真正原子提交；
- 真实主体已经理解、同意、建立关系、形成承诺或产生现实效果；
- 这些消息类型必须成为新的通爻协议。成熟 credential、transaction coordinator、
  transparency log 或 signed webhook 能完整满足同一边界时，应直接采用。

这轮的主要增量不是一个新名词，而是把 Wave 004 的“受信 controller 自证”改成了可被三个
外部权限域分别反驳的执行证据链，并明确保留了 transient partial materialization 与
single-view anchor 的未解决边界。
