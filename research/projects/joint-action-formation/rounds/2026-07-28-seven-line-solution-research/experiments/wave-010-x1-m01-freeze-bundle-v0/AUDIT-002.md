# M01 freeze bundle — independent audit 002

日期：2026-07-29  
决定：`ACCEPT ONLY AS SCOREABLE-PAIR FREEZE CANDIDATE`

这不是 scoreable episode、accepted scoreable pair 状态写回、已运行方法或方法有效性证据。
当前仍是：

- semantic episode candidates：2；
- scoreable episode candidates：0；
- accepted scoreable pairs：0；
- methods / runner / runs：0 / false / 0；
- coverage：不可用。

## 审查轨迹

第二审将首审的八个阻断收敛为三个：

1. exact G1 requests 未绑定 episode，语义状态被 padding 污染；
2. `T_G1_TO_G2` 反向嵌入 G2 truth projection，形成下游语义回边；
3. G1 non-success 使用未注册 placeholder pair。

修复后，第三审又发现一个更小但真实的 fail-closed 缺口：已验证但未注册的 upstream
category/reason pair 会产生无 typed pair 的 `NOT_REACHED`。最终修复把上游 non-success
闭合为互斥且完备的三类：

- verified + registered：实际 pair byte-exact passthrough；
- source binding 无效：`INVALID / INVALID_TRANSITION_BINDING`；
- binding 有效但 pair 未注册：
  `UNRESOLVED_SCHEMA / UNREGISTERED_CATEGORY_REASON_PAIR`。

后两类都要求 owner-signed typed receipt 绑定 attempted raw return hash；未注册 pair 还绑定
reason registry hash。禁止无 registered category/reason 的 `NOT_REACHED`。

第四次极窄只读审查接受了该 exact package。

## 接受所绑定的闭包

- content manifest entries：23；
- content root：
  `c3df52b88c272a056f4d783a394be44194d32a071dba55e3d4caf1c7c45aecf8`；
- T ledger root：
  `5e16c308d67f6275a2af47185431d4a7cd0721b5cee3ae8fc4fe627cfc5807f3`；
- T raw：
  `9d954bd4e179f9cbe3c046a60aa014fbaf2f24e507411b31fc1b2f692e944b1c`；
- G2 raw：
  `9a09aab1dc92ea22f83743e0c852595b1026498b7398446e4331f33b7a0f162d`；
- Bearing certificate raw：
  `04d401160b587a89d1b4c1c7bc474e8af554b438ff5169e479752d1e16fcc701`；
- validator raw：
  `ff5bf3f3b1681bc62392f8b19363116be32b58836d3aaf6e7a9ba74514fc8667`；
- outcome raw / schema preimage / reason-registry preimage：
  `4492aeb31048044a2aacd54de72b2f86a4317236f36f788125014da9c9ba5b88` /
  `be1a818eef4f7438ed238559ed6594aa422b056af36f26ee7ff90f53aff3d4fe` /
  `6ab1de71f251c87414d00bc14693a970ddfa35474956a78928d9b65928b0d8dc`。

独立复算还确认：

- 每个 directory/local request 分别绑定自己的 episode，跨 episode transplant 因 request
  hash 不匹配而 fail closed；
- T truth inputs 只有 common + G1，不再有 G2→T raw 或语义回边；
- G2 只单向绑定 finalized T raw；
- bundle 中 93 个显式 category/reason pairs 全部已注册；
- G2/G3/G5 equality hashes 与四个 G5 owner roots/closure 重算匹配；
- `NOT_REACHED` 不缩 integration denominator。

## 证据边界与下一道门

审查者是同一工作区内的结构分离 Agent，不是独立机构、独立模型家族或真实 truth owner；
接受决定没有生成任何密码学 owner signature，也没有证明同权限恶意进程隔离。

下一步只能进入 owner commitment 与 process allowlist 候选门，然后再由没有生成 private
truth fragments 的实现者分别实现强中心、成熟组合、人工接口和候选 arm。不得从本审查直接
进入评分、覆盖率或方法晋升。
