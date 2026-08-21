# G2-O1 C：owner oracle、open-schema 与架构混淆攻击

状态：`ATTACK RECHECK COMPLETE / 12 OF 12 PASS / LOCAL SYNTHETIC ONLY`

## 攻击对象

本文件和 `tests/test_g2o1.py` 只攻击本轮 12-world 本地合成候选，不改变 Problem、
LineContract、NOW、PROGRAM 或正式研究状态。

最承重的伪成功不是“签名被篡改”，而是 controller 先持有所有 Principal 的完整语义与
私钥，再替每个 Principal 生成正确 digest、explain-back 和 stance。这样的签名只能证明
parent 生成的字节保持一致，不能证明主体理解、认领或异议。因此测试要求：

- owner key 只存在于 owner actor 进程；controller 和方法臂不得接收全部 key；
- `correct digest / wrong understanding` 必须得到 `understood=false`；
- `correct understanding / refuse` 必须允许 `understood=true, claimed=false`；
- partial claim、silence、opposition 必须保留为独立事件，不能由全局 ACK 压平；
- private oracle 的 `expected.axes` 可全部反转而不改变实测 axes/diagnostics，防止
  truth-copy；变形只允许改变最终 scorer 的 expected-vs-observed 比较。

## Open-schema 攻击

公开 fixture 不得出现 `relation_valid`、`material_change`、
`opposition_preserved` 等答案字段。`schema_change` 必须由 base/candidate 的 role、action、
evidence、evaluation、exit、Standing 或 relation-level constraint 的结构 diff 推导。测试
直接构造 parameter-only 与新增 role/action 两个对象，要求 kernel 作出不同分类，而不是
读取 world author 标签。

private column 至少区分 `ABSENT` 与 `WITHHELD`。两者都可能在公开 transcript 中表现为
“没有 column 返回”，但前者是不存在，后者是 owner policy/拒绝导致的不可观察；把两者
合并会制造 false infeasible 或越权披露。relation-level coupled constraint 不能被拆成若干
局部条款全绿后自动判定成立。

## 架构与 Authority 拆轴

`state placement` 与 `Authority topology` 是两个变量：

- 同一 `Authority topology` 下，每个 world 都必须实际比较 central 与 replicated arm；
- shared institution 与 plural authorities 必须作为 topology 记录，不能由 storage 名称
  反推；
- partition/equivocation 的差异只支持同步、证据和恢复结论，不自动支持 G2 relation
  identity；
- equal-envelope strong center、成熟组件组合或人工制度完整解决均是正结果。

因此 runner 的每个方法输出必须同时报告 `authority_topology` 和 `state_placement`，不得用
“distributed/central”单字段混装信任根、合法 Authority 和存储位置。

## Fail-closed 攻击

五个 axes 必须分别输出：

`constituted / understood / claimed / authorized / activated`

测试不接受单一 `green/ready` 替代它们，并要求：

- 非 T5 world 中，未 claimed 或未 constituted 时不得输出
  `FORMED/ACTIVE/EXECUTION_READY/GREEN/PASS`；
- stale stance、revoked mandate 与 duplicate reservation 均阻断 authorization 和
  execution-ready promotion；
- unresolved equivocation 必须 fail closed 或给出可检查的 recovery；
- opposition 的 round-trip 必须明确 retained/preserved，不能由 fixture 常量宣告。

T5 是刻意保留的边界：固定平台可以不物化新的 Relation 而直接 activation。因此测试不把
“所有 axes 必须同时为真”误写成全局规则。

同理，`activated=true, authorized=false` 在现实上可能表示越权动作确实造成了后置状态；
分轴评分必须保留这个坏结果，不能为了 fail-closed 叙事把 target readback 改成 false。
Fail-closed 约束的是方法的许可/晋升，不是对已经发生事实的删除。

## 证据边界

即使这些攻击全部通过，也只能说明：

1. 当前脚本化 owner actor 的 key custody 与事件分域符合合成合同；
2. evaluator 没有直接复制公开答案标签或 private `expected`；
3. 四种方法臂在 12 个冻结 world 中以相同 axes 接受了 open-schema、Authority 与
   storage 攻击。

它不能证明真人理解、现实主体认领、真实采购/CLM/CMMN/IAM/HITL 产品闭环、跨组织法律
效力、生产线性一致性或 V1/V2 一般解。成熟方案若通过，就是本作用域的正向解；只有在相同
合法 observation、Authority、预算和 owner actors 下留下稳定残余，才有资格提出新机制。

## 攻击运行记录

- 首轮：实现文件尚未齐，`1 failed + 11 errors`，主要为 fixture/runner 不存在；该轮不评价
  方法语义。
- 第二轮：fixture、kernel 和 runner 已出现，静态/结构测试 `3 passed`；完整 runner 在
  `45s` 合同下超时，导致 `9 setup errors`。超时不是语义反例，但它是实际成本负结果：
  当前实现为 12 worlds × 4 arms 启动大量 owner/method 子进程，尚无可扩展性证据。为了继续
  语义攻击，测试上限放宽为 `180s`；这不把慢运行改写成性能通过。
- 第三轮：`8 passed / 4 failed`。private expected 变形运行与 baseline 不同，但该轮 A/B
  仍在并发改实现，故不能归因为 expected leakage；最终稳定复核才排除它。另有两项是攻击
  matcher 自身缺陷：opposition 按全文词汇匹配、`WITHHELD/ABSENT` 被诊断字段名污染，均改为
  结构化事件/精确 status。剩余真实红灯是 shared equivocation 没有
  fail-close/recovery，推动 evaluator 与 topology owner 修复。
- 第四轮在 A/B 同步改写 oracle/worker 期间运行，得到 `9 passed / 3 failed`，不作为稳定
  结论；但它暴露了 stale 与 revoke 被同一个 `REVOCATION` 事件合并，导致 current-head
  stale 不可观察。最终实现改为始终发出 Authority current-head，并在撤销时另发
  Revocation。
- 最终无并发复核：
  `python3 -m pytest -q tests/test_g2o1.py`
  → `12 passed in 101.72s`。其中包含完整 baseline 和 private
  `expected.axes` 全反转后的第二次 48-run；两次 observed axes/diagnostics 相同。

最终 baseline 为 12 worlds、4 arms、48 runs；五轴逐项与 evaluator 从完整 owner event
set 导出的 reference axes 相符（240/240 axis decisions），schema-change `48/48`，
opposition round-trip `48/48`。
runner 报告 106 个 distinct owner actor PIDs，controller/method 未接收 owner keys。四臂在
每个 world 上的五轴完全相同：本合成分母内没有观察到 relation-semantic residual，也没有
观察到 signed replicated state 相对同 Authority topology 的语义增益。

这个绿灯仍有四个重要限制：

1. `ACTUAL_MATURE_COMPOSITION` 是本地用 CMMN/CLM/IAM/reservation/provenance 字典模拟的
   composition，不是实际成熟产品的端到端运行；不能写成现实采购/CLM/CMMN/IAM/HITL 已验证。
2. owner actor key 在 actor 子进程内随机生成，不由输入确定、不返回 private material；
   但 owner 的行为和 local view 仍由受信的 private oracle 编排，且 actor 是脚本进程而非
   现实 Principal。故这里只支持 scripted process-custody conformance，不支持真人
   understanding/claiming，也不支持把受信 benchmark router 写成跨组织密码学独立性。
3. 四臂共享同一个事件生成器、同一 evaluator 和同一实现环境；多个 PID 不是多个独立实现，
   `240/240` 是 method-output 对同一 evaluator reference 的 conformance，不是第二套
   实现或现实形成频率。
4. 当前 cost 只是 operations/disclosure_units/owner_events 的粗计数。最终测试本身用时
   101.72s，单次 runner 曾实测约 38.79s；没有真人认知、等待、产品接入、恢复、迁移或
   锁定成本，不能据此判定生命周期最优臂。
