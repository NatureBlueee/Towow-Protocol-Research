# 主研究者独立规划：原本路线、纠偏与下一步

作者身份：当前 root / 共同首席研究者  
日期：2026-08-01  
状态：`PROPOSAL / PAUSED_PENDING_USER_ALIGNMENT / NOT_STARTED`

## 0. 我对这份计划负责什么

这不是从历史文件自动拼出的执行清单。我需要对三件事承担判断责任：

1. 选择下一项真正能推进原问题的工作，而不是最容易产生文件和绿色结果的工作；
2. 说明我原本准备做什么、为什么当时觉得合理、现在发现了什么错误；
3. 给出一条能够回到产品、完整 RelationEpisode 和原始决策门的路线，并明确何时停止。

用户确认前，本计划不授权新实验运行、产品写入、现实接触或 Wave 025 扩建。

## 1. 我原本准备做的事情

### 1.1 原本路线

在发现 Wave 025 后半段失去产品决定、T3 来源不是真实任务、T2 泄漏答案后，我原本准备：

1. 新建 PT-001，把“模糊目标到非标准资源协作”作为产品链；
2. 先比较 D1 的纯访谈、可撤回模型假设、本地许可上下文和人工 fallback；
3. 再比较 D2 的目录、task-relative projection 和必要 probe；
4. 逐节点扩到 RelationVersion、Capability、Authority、Execution、Effect、Acceptance 和 reopen；
5. 每个节点输出 `ADOPT / COMPOSE / REMOVE / INVENT / KEEP_UNKNOWN`；
6. 某个节点小型评测不足时，调用 Wave 025 的相应设施。

已经为这条路线形成了：

- `TASK-SPEC.md`：三个合成任务；
- `PRODUCT-ARMS.md`：六类 D1/D2 产品行为；
- `EVALUATION-CONTRACT.md`：fresh truth/solver 分离与 D1/D2 判定。

### 1.2 当时为什么这样做

这条路线试图解决三个真实问题：

- 让比较重新绑定产品行为，而不是继续完成通用实验设施；
- 修复 T3 没有任务前态、T2 有答案泄漏的问题；
- 把分散的七条母线第一次翻译成用户可以经历的产品旅程。

这些动机仍然成立。特别是 PT-001 的目标保持、拒绝、Unknown、direct 旁路和 completion gate，
应该继续进入产品约束。

### 1.3 我现在确认的错误

若把这条路线按 D1→D2→D3……顺序独立扩张，它会产生四个问题：

1. **重复上游研究**：Wave 001--009 已经做过大量 discovery、projection、probe 和 handoff；
   新合成任务若不进入完整 episode，只是换素材重跑。
2. **把入口变成主线**：V2 核心从 Intent 进入协调；模糊目标→Intent 是产品入口扩展，不能替代
   RelationEpisode。
3. **继续推迟集成**：每个节点都可以产生更精细 evaluator，但原计划要求的是同一个事项贯穿
   关系、权威、执行、Effect、Acceptance 和重开。
4. **再次替代 Q1--Q5**：局部合成结果会继续推迟公平强中心、真人 explain-back、真实 causal
   formation 和第二次复用。

所以我不再建议把 D1/D2 评测作为下一主线。其材料保留为任务接入和反例检查，不独立扩张。

## 2. 纠偏后的唯一主目标

> 让一个具体事项通过一个可使用的 P0 产品壳，完整走完一次 RelationEpisode；在同一事项中
> 嵌入 Q1、Q2、Q3 和 Q4 的最低判别，获得 Target Effect 与独立 Acceptance；随后用同一路径
> 完成第二次运行，检验 Q5。

这不是新规划，而是恢复 v1.2 决策程序和七母线原定跨线集成。

### 2.1 产品必须呈现的最小体验

用户不应看到七条研究线。一个合作工作区至少应让用户看见：

- 我们当前理解的目标、原始底线和仍为 Unknown 的内容；
- 当前候选路径以及为什么值得继续；
- 谁需要知道什么、谁尚未回应、谁拒绝或 counter；
- 当前提案的版本差异、资源、责任、退出和验收方式；
- 能力、Authority、Commitment、Reservation 分别处于什么状态；
- 精确行动是否发生、Target 读回了什么；
- 谁接受、部分接受、拒收或保持未决；
- 发生变化后，哪些部分继续、阻断、替换或重开。

产品内部可以路由到 direct 平台、中心协调、人类、跨域 adapter 或组合；用户不必理解这些研究
分类。

## 3. 执行顺序：一条 episode，而不是九段研究

### Phase 0：收口与冻结

当前动作就是本目录。

完成条件：

- 历史结果、负结果、Unknown、未运行和失效结论有统一入口；
- PT-001 D1/D2 被标为入口探针、未运行；
- Wave 025 保持按需，安全部分保持转交；
- 用户确认下一主目标。

停止条件：若用户认为本计划仍偏离原目标，不启动 Phase 1，先重写。

### Phase 1：选择一个完整事项与 P0 壳

只选择一个主事项，不同时经营三个任务世界。要求：

- 7--14 天内可完成；
- 低风险、可撤销或可补偿；
- 至少两个独立 Authority locus；
- 至少一个真实 Unknown、Reject 或 capability gap；
- 能执行一个可观察 Target Effect；
- 有一名独立 Acceptance/裁决来源；
- 可以由一个简单 P0 产品工作区真实承载。

选择时可以使用 PT-001A 可触摸样机方向，但必须重新取得可认领的 S0，而不是把合成 oracle 当
现实用户。

本 Phase 不要求全面实现协议。若人工协调和简单工作区足以承载，先用它们完成 P0。

产物：`EPISODE-BRIEF`、S0/V0/Q、Authority map、Target/Acceptance source、退出与风险边界。

### Phase 2：把入口层接到核心 episode

PT D1/D2 只承担：

```text
模糊目标
→ 主体确认的 Intent
→ 必要条件与合法 Unknown
→ 一个可进入共同提案的候选路径
```

这里不运行全局 arm 大赛。最多选择两个产品行为进行任务内观察：

- P0 的简单人工/中心路径；
- 一个有明确理由的辅助路径。

若简单路径完整、低负担地形成合格 Intent 与候选，停止入口研究并采用它。若辅助路径没有改变
后续 episode，删除它。

### Phase 3：在同一事项中闭合 RelationEpisode

同一 episode 必须连续产生并保留：

1. 当前共同提案和 material change；
2. 各方 explain-back、拒绝、counter 与未决项；
3. operation-specific capability qualification；
4. 当前 Authority、Mandate、Commitment 和 Reservation；
5. exact ActionAttempt；
6. Target-native Effect readback；
7. Adoption / Acceptance / Settlement 的独立状态；
8. 失败、撤销或变化的处理路径。

七条母线在同一 episode 上分别读取自己的 native truth，不创建七个产品或七套世界。

本 Phase 的失败结果可以是：`DISCOVERY_ONLY / CLARIFICATION_ONLY / NO_MATERIAL_GAIN /
HARMFUL_OVERHEAD / PROTECTIVE_STOP / UNKNOWN`。不为了完成而强行生成 formation。

### Phase 4：把 Q1--Q4 嵌入一次 episode

不另建四套大型实验。

| 决策门 | 在同一 episode 中怎样得到判别 |
|---|---|
| Q1 | 冻结 S0 后离线重放公平强中心路径；给相同 Mandate、信息、工具、查询与 Effect Gate |
| Q2 | 对关键 goal/Mandate/RelationVersion 做真实参与者 explain-back；记录理解、修订和维护负担 |
| Q3 | 定位一个主要 formation operator；运行 operator 前后与消融 replay；检查路径是否首次出现 |
| Q4 | 用未带作者编码的原始材料让独立 evaluator/模型填写 Router 判据，并与独立 coding 比较 |

只有 Q3 的七条 causal formation 判据全部满足，才称一次 formation。若失败，依结果把相应对象
降级为发现、澄清、翻译、记录或辅助工具。

### Phase 5：Effect、Acceptance 与失败 replay

真实 episode 结束前必须区分：

- action 没发生；
- Attempt 发生但 Effect 没发生；
- Effect 发生但不是由本次 actor/operation 造成；
- Effect 发生但未 Adoption；
- Adoption 发生但 Acceptance 拒绝或 Unknown；
- ACK 丢失但 Effect 已发生；
- revoke/counter/goal change 导致局部重开或退出。

评价设施只实现这些真假分支所需的最小 readback、owner decision 和 replay。不扩成全局 tournament。

### Phase 6：Q5 第二次运行

只有第一次 episode 得到相称接受后，才运行同一路径的第二次事项。比较：

- 高认知人工分钟；
- 询问和披露；
- 目标/Authority/资源确认；
- 错误、等待和返工；
- reopen 和迁移成本；
- 用户是否仍认领编译后的路径。

若第二次没有更低成本、更少错误或更快完成，Formation/Compiled 双制度不能晋升为产品核心。

### Phase 7：第二任务迁移与产品编译

第一条路径成立后，再选择一个结构不同的任务族和一个留出变体：

- 检查哪些语义可以直接复用；
- 哪些只能通过 adapter 转换；
- 哪些必须重新形成；
- 哪些 provider/平台可以替换；
- 哪些依赖使产品被锁定；
- 哪些反例要求完整创新。

只有在两个任务族中稳定成立的部分，才进入产品内核；其余保持任务策略、adapter、人工流程或
Unknown。

## 4. 七条母线在这份计划中的职责

| 母线 | 同一 episode 中的唯一职责 | 交付物 |
|---|---|---|
| G1 | 找到可合法继续判断的候选，不把 no-match 写成无解 | candidate + findability/refusal boundary |
| G2 | 形成双方能修改和反对的提案 | current proposal + material differences + local objections |
| G3 | 诊断和创造缺失条件，不偷换目标 | operator trace + ablation + path delta |
| G4 | 在 attempt 前判断 operation 能否依赖 | prospective qualification + expiry + abstention |
| G5 | 让当前 Principal/Authority 分别决定并消费 | current decision + grant/commit/reservation state |
| G6 | 从 Target 和相应主体重建 Effect/Acceptance | exact readback + acceptance stance |
| G7 | 第二次运行、变化和失败时安全继续或重开 | dependency/reopen trace + reuse cost |

任何一条线都不能用自己的 PASS 创建另一条线的正式事实。

## 5. 评测设施的建设规则

我只会在同时满足以下条件时建设或恢复设施：

```text
一个命名产品决定确实被卡住
AND 当前 episode 的直接证据不足以区分
AND 已发生或高代价的假绿能由该设施阻止
AND 没有更小 paired/removal/readback 方法
AND 预先写明反向结果与停止点
```

核心设施仍然要做：

- S0/V0/Q 和 method-visible input 分离；
- owner/Target 原生 decision/readback；
- Effect 与 Acceptance gate；
- 同一 base episode 的 refusal/revoke/ACK-lost/drift replay；
- 产品完成、保护性停止和 Unknown 状态。

当前不主动扩建：

- 无命名产品决定的通用大样本；
- 通用 classifier/feature 大赛；
- 全臂 tournament；
- 自动删除失败或晋升研究主张；
- 与用户已转交给安全人员的网络/权限攻击面。

## 6. 理论、模拟和产品怎样并行

现实 episode 的协调不应阻塞理论研究，但理论研究必须服务同一 episode：

- 理论：明确 operator、不可达、Authority、Effect 和 reopen 的可观察区别；
- 模拟：在真实 episode 尚未出现的危险分支上做 failure injection；
- 产品：让用户能够表达、拒绝、counter、执行和验收；
- 工程：接入 Target readback、当前 Authority 和可恢复状态；
- 独立评审：攻击目标偷换、controller 代做、错误归因和净值。

不再建立一套与产品事项无关的理论任务宇宙。

## 7. 依赖、自持、维护与产品包容

进入产品的每项能力都要回答：

- 它在 episode 中负责哪个状态变化；
- source of truth 在哪里；
- 格式是否丢失目标、Authority、版本或 Acceptance；
- provider 停更或改变接口时怎样替换；
- 能否导出、迁移、回放和降级；
- 是否制造第二事实源；
- 自持核心的成本是否低于长期锁定和语义损失；
- 哪些部分值得自研、专利或成为 conformance layer。

最终产品可以包容平台、中心、人类、开放协议、adapter、自有内核和人工 fallback；判据只有它们
是否共同完成 episode 并保持原始边界。

## 8. 明确停止条件

本计划在以下任一情况暂停并回到用户：

- 用户不认可“一个完整 episode”为当前唯一主目标；
- 事项没有真实可观察 Target Effect 或独立 Acceptance source；
- 主要参与者、Authority 或受影响方不清楚；
- 为完成任务必须偷换 V0、Q 或遗漏必要主体；
- 高风险、不可逆或超出授权范围；
- 继续研究只会增加同质合成样本或设施，而不改变产品行为；
- 出现两个会实质改变产品方向、且不能由当前证据选择的分叉。

## 9. 我请求用户确认的唯一事项

请确认或修正下列定位：

> 当前不运行独立 D1/D2 评测，也不继续扩 Wave 025。下一主线恢复为一个完整 RelationEpisode：
> 使用一个可用 P0 产品壳，在同一低风险事项中从入口走到关系、Authority、真实行动、Target
> Effect、独立 Acceptance，并嵌入 Q1/Q2/Q3/Q4；第一次成立后立即做 Q5 第二次运行。

一旦该定位被确认，我再把它转换为具体 episode brief、产品界面、参与者/Authority map、实验
包和执行调度。未经确认，不把本提案描述为正式规划或已开始执行。
