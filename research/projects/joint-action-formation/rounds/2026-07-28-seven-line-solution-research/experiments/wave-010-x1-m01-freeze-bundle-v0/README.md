# Wave 010 X1 M01 freeze bundle v0

状态：`ASSEMBLED CANDIDATE / AWAITING INDEPENDENT REVIEW / NOT RUN`

## 它冻结了什么

这是 Wave 010 的第一个最小任务分母候选，不是 runner 或方法结果。两个 episode 面对同一个
现实任务：在 36 小时内形成河口盐度传感器紧急校准与独立验证的 authority-valid joint-bid
front half。

两侧的 Intent、V0、BE0、Q_episode、动作空间、期限和本地 capability fact 相同。唯一
primitive delta 是：

- 一侧的 current directory 已经有 lawful candidate projection；
- 另一侧没有入索引，但相同 candidate 可以通过相同预算内的 purpose-bound local
  projection 合法得到。

因此目录单项应只覆盖前者；能继续使用合法本地投影的强中心或成熟组合可以覆盖两者。哪种
方案获胜都属于正向解题结果。

## 为什么先做 bundle

过去的 synthetic world 容易让同一个 world factory 同时生成输入、答案和四条线的 truth。
这个 bundle 先把承重事实拆开：

- G1 又分为 directory index owner 与 local projection owner；
- G2 单独冻结 relation semantics；
- G3 只从 lawful G1/G2 handoff 后评价 pre-existing path，不读取上游目录路线；
- G5 保留 program、calibration、independent validation、site-data steward 四个 Authority
  domain，中心和 evaluator 都不能替它们签名；
- `BearingDeltaCertificate` 明确允许传播、禁止传播与 conditional scoring。

组装时已经发现并修复两类真实错误：G3 曾错误绑定 V0/Q 的 canonical hash；G5 曾把多方
Mandate、Commitment 与 resource Reservation 压进 program center，并预置成功状态。两者若
未被修复，后续绿色结果都没有解释力。

## 当前边界

现在只有两个 semantic episode candidates，尚有：

```text
scoreable episodes = 0
accepted pairs = 0
implemented methods = 0
runner = NOT IMPLEMENTED
runs = 0
coverage = NOT AVAILABLE
```

private fragments 仍位于同一研究仓库。未来方法必须使用进程读取白名单；当前只能声称
cooperative/non-reflective 隔离候选，不能声称抵抗同权限恶意本机进程。

下一步是独立攻击 bundle 的 exact-byte 绑定、pair orthogonality、信息泄漏、G2/G3/G5
等同性和 Authority owner collapse。只有审查接受，才进入强中心与成熟组合的实现。
