# Wave 003：组合构造假说

状态：`ACTIVE_HYPOTHESIS / NOT_VALIDATED`  
日期：2026-07-28  
来源：Wave 002 的 A、B、A+B 同分母失败，不是为了保留通爻独立机制而提出。

## 当前最小问题

在动态、局部私有、需求和能力事前未公开成 card 的世界里，目录和端侧模型各自只完成一半：

- 目录能路由已经表达且仍然有效的对象；
- 端侧模型或规则能看到局部变化和潜在相关性；
- 两者之间缺少一个可验证的转换：局部可能性怎样成为有边界、可撤销、能双向确认并可进入
  relation constitution 的候选。

因此当前构造对象不是新搜索引擎，也不是大一统协议，而是一条组合链：

> `local trigger → task-relative projection → routing → reciprocal probe → versioned candidate handoff`

## 候选组合

### 1. Local trigger

本地模型、规则、事件检测器或人类操作在主体权限域内发现一个可能与当前任务有关的局部事实。
它可以调用 MCP、本地工具或既有应用数据，但此时只形成 `LOCAL_CANDIDATE`：

- 不等于公共能力声明；
- 不等于可用 capability；
- 不等于愿意披露；
- 不等于存在匹配方。

### 2. Task-relative projection

主体只生成路由所需的最小投影：

- `direction`；
- task-relative `compatibility_key`；
- 当前 `version`；
- recipient 或 recipient class；
- purpose、retention、depth、onward rule；
- authority/policy witness；
- invalidation route。

这里可以使用通用模型做语义压缩，也可以用确定性 adapter；模型不是 Authority，projection
必须由本地 policy/Authority 允许。

### 3. Routing

ARD、A2A Agent Card、事件总线、目录、强中心或点对点传输都可以承担这层。它们的任务只是：

- 路由当前有效的 projection；
- 不把同 facet 自动当作互补方向；
- 接受版本失效通知；
- 不把返回结果升级为 commitment。

若 ARD/A2A 加少量 adapter 可以完整承担这一层，就直接作为通爻组合的一部分。

### 4. Receipt-backed reciprocal probe

只有单边 projection 不足以建立双方当前互补性。probe controller 必须：

1. 验证双方方向和 compatibility；
2. 分别询问每个 holder 是否愿意为同一 purpose、版本和对方披露最小 fact；
3. 每次披露生成 receipt，绑定 sender、recipient、fact、purpose、retention、version；
4. 两边都成功且 receipt 可核验时才得到 `DISCOVERED`；
5. 任一拒绝、超时、过期、版本变化或 policy 不允许，分别返回
   `REFUSE / UNKNOWN / INVALIDATED / UNFINDABLE_UNDER_POLICY`；
6. probe 完成仍然只产生候选关系，不产生 Commitment。

### 5. Versioned handoff

`DISCOVERED` 必须使用同一 detection identity 进入
`CANDIDATE_NOT_COMMITMENT` handoff，保留 evidence、未决问题和来源版本。失效通知只能关闭受
影响候选，不能删除历史 receipt，也不能把另一个机会一起关闭。

## 为什么现有技术“都有”，问题仍未自动解决

不是因为已有技术弱，而是各自契约停在不同边界：

| 现有能力 | 已经解决 | 没有自动解决 |
|---|---|---|
| 本地/通用模型 | 从本地上下文生成候选、摘要和询问 | Authority、披露 policy、版本、双向 receipt |
| MCP | 模型与工具/资源的上下文交互 | 跨独立主体机会生成与关系构成 |
| ARD/目录/A2A Card | 已表达资源和 Agent 的发现、路由 | query/card 之前的局部触发与未表达机会 |
| OAuth/GNAP/RAR/policy engine | 请求与授权边界 | 语义方向、互补性和 relation handoff |
| CloudEvents/event bus | 已知事件的传输和版本通知 | 哪些局部事件值得成为任务投影 |
| workflow/commitment protocol | 已定义过程和承诺的推进 | 过程、参与者和关系尚未形成时的发现 |

这些缺口可以由组合 adapter 解决，也可能需要一个很薄但语义承重的 controller。两种结果都
是成功；只有新留出任务证明现有组合无法表达或安全执行时，才登记新的机制身份。

## Wave 002 失败如何改变构造

- A 的 SEEK/SEEK false wakeup：强制 `direction` 与 compatibility 分开；
- B 恢复了局部状态却召回为零：projection 必须具有可路由 signature，不能只有自然语言；
- A+B reciprocal miss：增加双边 receipt 和完成态，不接受双方各说“可能有”；
- closed-population disclosure policy failure：成员负证据只用于 claim resolution；没有
  合法 recipient/purpose 时不另造 disclosure event；
- relation handoff failure：handoff 必须引用已经 `DISCOVERED` 的同一 detection ID；
- dynamic invalidation 只形成 claim：update 必须引用可观察 pair/projection identity。

## 证伪条件

这个组合在以下任一情况下失败：

- 仍依赖事前公共 card 才能生成第一个 projection；
- 只能靠 holder 名称或自然语言暗示猜 direction；
- 单边披露被当作 reciprocal completion；
- receipt 不绑定目的、接收者、保存期和版本；
- 失效后旧 projection 仍可被路由；
- `UNKNOWN / REFUSE / ABSENT / UNFINDABLE` 再次混淆；
- handoff 偷渡 commitment；
- 在 T5 简单平台任务中增加多余协商和披露。

## 下一验证

1. 在未知的 `T1-HW-B` 留出世界实现确定性 holder、probe controller 和 coordinator；
2. 与 A、B、A+B 使用同一 evaluator 比较，不能在 HW-A 已揭示 truth 上报告新盲分；
3. 把相同 controller 迁移到 T4 joint-bid，检验多方、资源和 Authority 组合；
4. 在 T5 负控中旁路为现成平台；
5. 对本地模型、ARD/A2A、policy engine 和 event transport 做可替换实现，测语义损失和退出成本。
