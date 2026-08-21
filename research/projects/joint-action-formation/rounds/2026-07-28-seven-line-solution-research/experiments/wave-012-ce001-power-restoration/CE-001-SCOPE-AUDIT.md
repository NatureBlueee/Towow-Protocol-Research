# CE-001 作用域审计与开放生态后继候选

日期：2026-07-30  
状态：`ROOT-ACCEPTED SCOPE CORRECTION / SWITCHBACK DEMOTED / INDUSTRIAL ECOLOGY PROPOSED NOT FROZEN`

## 修正

CE-001 仍然值得完成，但它只能承担：

> 给定 exact Q、已知 owner 类型、已知 owner API 与有限 action grammar，现有方案能否在
> Authority、Effect、Acceptance、恢复和迁移边界下完成一次跨主体 RelationEpisode？

它不能承担 V2 的完整主问题。即使现有组合在 CE-001 达到 `7/7` 可达成功和 `8/8` 正确
resolution，也只关闭：

```text
NOVEL_MECHANISM_NECESSITY_FOR_CE-001
```

不能关闭 V2 的开放形成与 RelationEcology 问题。

## 为什么会发生作用域缩小

CE-001 已预先给出：

- `O_Q / O_V / O_R / O_S / O_P / O_E` 等角色；
- query、delegation、reserve、commit、execute、readback、accept、settle 等动作语法；
- exact target、Q、成功标准和有限 owner API；
- E0–E6 的任务家族及其主要故障类型。

因此主要困难已经被研究者预编译为 workflow。它没有真正检验 V2 中这些承重要求：

- 问题、角色、动作、伙伴、条件、证据或 Acceptance 方式事前尚未完整存在；
- 海量、异构、动态网络中的候选缩减、漏配、误唤醒和高级智能分配；
- 新形成路径怎样在重复任务中降本并被编译；
- material difference 出现时怎样只重开必要部分；
- 多个 episode 怎样争夺资源、产生外部性并保留各自 Principal；
- 伙伴退出、runtime 迁移和部分历史仍有效时怎样替代与连续。

这不是 CE-001 失败，而是 `RelationEpisode` 与 `RelationEcology` 两个尺度不能互相冒充。

## 后继候选：OPEN-ECOLOGY-SWITCHBACK-001

### 环境

- 约 1,000 个动态 Agent Entity；
- 原生描述、current state、Authority root 与交互接口可依法查询；
- 本轮不设置隐私 residual；
- 禁止把 Intent 广播给全部实体，也不能逐个调用高级模型；
- 不提供 task-specific role label、expected partner、expected plan 或 formation label。

### 八个已经进入 V2 协调接口的 Intent

| Intent | 主要区分 |
|---|---|
| I1 | 现有活动平台可直接完成无障碍场地预订 |
| I2 | 单一组织内部合法中心可调度字幕与工作人员 |
| I3 | 成熟物流、合同、IAM 与 workflow 组合可直接复用 |
| I4 | 让视障参与者能独立到达六个非标准展区；伙伴、责任、动作组合和 Acceptance 方式均未预编译 |
| I5 | I4 在同场地重复，检验新路径能否沉淀并降低全生命周期成本 |
| I6 | 相近任务迁移到新场地，但消防规则、受影响主体和 Acceptance criterion 改变 |
| I7 | 两个已形成 relation 同时请求同一稀缺资源，且各有独立 Principal |
| I8 | 核心伙伴退出、runtime 迁移，旧 relation 部分仍有效 |

I4 不预先指定无障碍顾问、触觉地图制作方、现场引导员或某条标准解。方法可以使用通用模型、
搜索、ARD、A2A、人工、合同、中心、workflow 和任何成熟工具，提出角色和组合，再由实际
Principal 理解、修正、拒绝、授权和认领。

### 最强现有组合上界

不把成熟能力拆成互斥阵营。主 baseline 是一个可逐 Intent 自由组合的上界：

```text
平台直达
+ 合法权威感知中心
+ 通用前沿模型
+ 搜索 / ARD / 目录
+ A2A / 原生 API / MCP
+ workflow / CLM / IAM / policy
+ 人工协调、合同与例外
+ outbox / fence / readback / reconciliation
+ durable history / migration
```

候选新机制只能作为 `现有组合上界 + candidate delta` 参加比较；不得获得更多 truth、
Authority、候选集、时间或人工。

### 必须产生区分的观察

- I1–I3 是否主动采用最短的现成路径，没有强造 relation；
- I4 是否在没有预设角色/伙伴/动作时形成被主体认领、可执行且产生 Effect/Acceptance 的新路径；
- I5 是否在不增加错误的情况下显著降低 repeat cost；
- I6 是否只重开受新规则影响的真实依赖；
- I7 是否保留冲突 Principal、拒绝、机会损失和第三方外部性；
- I8 是否形成替代伙伴并恢复，而不重写旧事实和责任；
- candidate narrowing recall、false elimination、false wakeup、高级模型调用与人工高认知负担；
- wrong Authority、task substitution、unsafe action、Effect/Acceptance/Settlement 与净价值。

### 关闭创新必要性的条件

若最强现有组合在同一冻结生态中：

- I1–I3 选择并完成现成路径；
- I4 完成没有预给解法的开放形成；
- I5 正确编译且降本不增错；
- I6 精确局部重开；
- I7 不越过任何 Principal，并得到成功、协商、拒绝或替代的正确结果；
- I8 完成伙伴替代、迁移和历史连续性；
- 没有 candidate-exclusive success；
- 不同 truth author 与相邻任务迁移仍复现；

则登记：

```text
NOVEL_RELATION_ECOLOGY_MECHANISM_NECESSITY
= CLOSED_FOR_OPEN-ECOLOGY-SWITCHBACK-001
```

这仍然是通爻的完整正向结果：成果是对平台、合法中心、通用模型、成熟系统与人工制度的
条件化选择、组合、编译和重开方法，而不是为了原创另造协议。

## Pro 返回后的处置

独立 Pro 复核已经返回，结论是：

```text
OPEN-ECOLOGY-SWITCHBACK-001 = DO_NOT_FREEZE_AS_V2_MAIN_EXPERIMENT
```

原因不是 I1–I8 缺少 expected partner，而是它仍把
“平台直达→合法中心→成熟组合→开放形成→编译→局部重开→资源冲突→退出/迁移”
写成透明课程大纲。solver 因而提前得到 expected mechanism class、lifecycle stage 和
evaluator attention；无障碍展区案例也从常识强烈暗示了一组标准角色。这个问题不能通过
删掉角色名称解决。

I1–I8 保留为：

```text
ECOLOGY-CONFORMANCE-SUITE-001
```

它可以验证一个系统是否声明并实现了相应能力，但不能证明系统从无标签开放事件中发现了
正确 episode、角色、路径和重开边界。

新的 V2 主实验候选改为：

```text
OPEN-INDUSTRIAL-RECOVERY-ECOLOGY-001
```

最小设计约束：

- 输入是无标签连续工业恢复事件流；episode class 只能由 evaluator 事后判定；
- 动态生成主体、状态、staleness、churn、资源竞争、受影响主体和伙伴退出；
- 不给 expected partner、role、plan、formation、compile 或 reopen label；
- 允许多条合法 trajectory，不设置 canonical plan；
- truth author、solver、owner services、target readback、Acceptance 与 Settlement 分离；
- `EXISTING_HYBRID_UPPER` 与 `U + Δ` 使用相同 truth、Authority、候选集、时间、模型和人工；
- 先过权利、安全、Authority 和 target-truth 硬门，再比较 owner-wise value vector 与
  lifecycle net value；
- conformance、hidden main worlds、状态不一致 worlds 与小型 live-validation 分层，
  任一 synthetic 结果都不冒充现实频率或生产效果。

首个承重 motif 是“定制零件交付恢复”：测量、加工、热处理、内部工程与客户 QA 只声明局部
能力；可行路径可能需要形成新夹具或工艺条件与多个 owner act。随后改变材料牌号并让核心
加工伙伴退出，用于检验 repeat、material difference、局部重开、替代和历史保留。这个 motif
仍只是候选，不是 canonical solution。

当前状态：

```text
OPEN_ECOLOGY_SWITCHBACK_001 = TRANSPARENT_CONFORMANCE_CANDIDATE
OPEN_INDUSTRIAL_RECOVERY_ECOLOGY_001 = PROPOSED_NOT_FROZEN
EXISTING_HYBRID_UPPER_FULL_WIN = EXPLICITLY_ALLOWED
NOVEL_RELATION_ECOLOGY_MECHANISM_NECESSITY = NOT_TESTED
```

## 当前行动

1. 不停止、不改写已冻结 CE-001；完成其 episode 级组合实验。
2. CE-001 结果不得升格为 V2/RelationEcology 结论。
3. 不冻结 `OPEN-ECOLOGY-SWITCHBACK-001` 为 V2 主实验，只把它保留为 conformance 候选。
4. 在冻结 `OPEN-INDUSTRIAL-RECOVERY-ECOLOGY-001` 前，先由独立 world author 生成无标签
   event stream，再让不知道 motif 期待答案的 solver 与 evaluator 分别审查可判别性。
5. 若新候选仍预给关键角色、路径、阶段或唯一答案，继续重写，不能为了开跑牺牲判别力。
