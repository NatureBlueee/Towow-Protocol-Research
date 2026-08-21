# Wave 002：首轮盲跑与组合比较

状态：`RUN_COMPLETE / RESEARCH_CONTINUES`  
日期：2026-07-28  
纲领：`PROGRAM.md`  
证据级别：仅为本地合成任务与档案设计派生 truth task；不是现实主体、生产或长期有效性证据。

## 结论先行

首个同分母比较已经给出一个建设性结果：

| 方法 | G1 通过要求 | 覆盖率 | 机会召回 | 错误唤醒 |
|---|---:|---:|---:|---:|
| A：公共动态目录/索引 | 0/8 | 0.0% | 1/3 | 1 |
| B：本地主体最小投影 | 1/8 | 12.5% | 0/3 | 0 |
| A+B：目录 + 本地投影/拒绝/失效更新 | 5/8 | 62.5% | 2/3 | 1 |

因此，本轮不是“目录无用”或“必须发明独占新机制”，而是：

1. 公共目录擅长已表达对象，但单独不能恢复未表达机会、端侧变化、拒绝和封闭总体负证据；
2. 本地投影单独保真地解决了 `UNKNOWN / REFUSE / ABSENT`，但没有公共信号时缺少足够的候选
   路由与互惠确认，不能独立完成发现；
3. 两者组合产生了真正的互补增益：相对最好单项 B 提升 50 个百分点，并恢复一个未预制
   公共 card 的机会、处理动态撤销和 policy 下不可发现；
4. 组合仍没有解决双向 probe、方向验证和合法 disclosure receipt，因而不是完整解。

这正是通爻所要的成果形式：现有索引结构与端侧最小投影的组合已经解决一部分原问题；剩余
创新只应针对已经暴露的有界断点，而不是为了证明通爻特别而另造一套目录。

## G1 冻结运行

任务：`T1-HW-20260728-A`。  
评分器：`experiments/hidden-world-discovery/evaluator.py`。  
三种方法使用同一 latent truth、同一八项要求和同一评分器。

### 方法 A：公共动态目录

输入只包含 coordinator 公共目录、公开 claim 和 query。

- 通过：0/8；
- 能找到一个已表达 opportunity；
- 把一个 SEEK/SEEK decoy 错配为机会；
- 没有端侧撤销，继续把失效 GPU offer 当作有效；
- 看不到未表达机会、明确拒绝和成员级封闭总体负证据。

提交 SHA-256：
`68b7543edc5afdd6b57589351fd6fbadd9bb1621233afb51e29cec8a802b9865`。  
评分 SHA-256：
`0c2ae0357fe67b3e04531cdf4e84c7adc82c156a419afd2aec2422e1cb708594`。

### 方法 B：本地主体最小投影

11 个隔离 holder 实例各自只读取一个本地 packet；协调者看不到公共目录信号，只接收最小
投影、claim observation、拒绝、失效更新和不能支持项。

- 通过：1/8，仅 R5；
- `UNKNOWN / REFUSE / ABSENT` 区分正确；
- 没有错误唤醒；
- 端侧存在未表达任务/能力投影，但协调者在没有路由和双向 probe 时保守保持 `UNKNOWN`；
- 失效通知只有 claim 形式，缺少可映射的 seeker/provider signature；
- reciprocal holder 没有产生 receipt-backed 双向披露。

提交 SHA-256：
`1811e3b216dc1561ff73b4f5eea0d0ab0cc3b5efef21ba684e0c8c9ac9022281`。  
评分 SHA-256：
`19b5698035917388e174f34b7f2f651c1967d0f78698f12bd486cecbbf52be72`。

### 方法 A+B：公共目录 + 本地主体通道

- 通过 R1、R2、R3、R5、R6，共 5/8；
- 恢复未表达 data-cleaning opportunity；
- 正确使动态 GPU offer 进入 `INVALIDATED`；
- 正确区分 offline=`UNKNOWN`、explicit refusal=`REFUSE`、closed population=`ABSENT`；
- 正确标记 policy-unfindable opportunity；
- 仍把公开的同 facet SEEK/SEEK decoy 错配；
- reciprocal probe 未完成；
- 两个 closed-population disclosure event 没有合法 policy，虽然 claim 的成员负证据正确；
- reciprocal opportunity 未进入合法 relation handoff。

提交 SHA-256：
`bfcd65b0406d42a2576b54ea8e201c4003a8643b5bb2af82b8675d4f30e142a2`。  
评分 SHA-256：
`8c716696d5381c93a6666a22440caeee9b1071c1f540af4ed53a6d3e99b28d85`。

### G1 下一构造

不能用同一个已揭示 truth world 修补后再宣称盲测通过。下一步应：

1. 构造 `T1-HW-B` 留出世界；
2. 把方向与 facet 分开，不把同 facet 当互补；
3. 建立 receipt-backed reciprocal probe 状态机；
4. 让投影 policy 决定 disclosure event 是否可发送，而不是见到 witness 就发；
5. 使 projection version update 带完整 observable pair signature；
6. 只在同一 `detection_id` 上进入 `CANDIDATE_NOT_COMMITMENT` handoff；
7. 在新 world 上重新运行 A、B、A+B 和上述修复组合。

## T2：从拒绝到合法下一步

T2 使用档案设计派生但答案隔离的 blind input。求解器先只看到 V1 的拒绝、价值底线、资格化
谓词和四个 Authority 接口；controller 用四轮、15 项带 hash receipt 的最小披露回答：

1. 数据权威的最小反条件与服务方替代路径；
2. 有界 probe 技术条件与测试授权；
3. 买方 witness、撤销、恢复、业务门槛、范围、价格和周期；
4. 数据用途、当前 capability evidence、预算 stance 和 Adoption 条件。

形成的最好候选不是“试点已经成功”，而是：

- V1 保持 `REJECTED`；
- `REL-T2-V2-CANDIDATE` 是 material change 后的新候选；
- 固定容器进入买方 sandbox 是可测试路径；
- 当前环境 capability evidence 明确为 `none_for_this_environment`；
- bounded probe 尚未运行，capability 保持 `UNKNOWN`；
- 测试授权不延伸为正式试点授权；
- Effect、Adoption、Acceptance、Settlement 全部未发生；
- 合法下一步是先满足有界测试授权和精确依赖，再运行 probe，再资格化 exact operation，
  最后让四个 Authority 对 probe 后的精确版本重新认领。

同模型的独立 evaluator 实例按 R1–R8 给出 8/8 `PASS`；另一个对抗实例未发现状态升级偷渡。
这只能支持“候选方案忠实地构造了下一条合法可执行路径并守住状态边界”，不能支持现实任务
完成、真实 capability、商业价值、严格 formation、生产有效性或协议独占性。

候选 SHA-256：
`19ac2def266c355179a401fede37a8c33523c7c1a6237c5706eae798a6ca5e2e`。  
模型评估 SHA-256：
`6370903eaa6ab68726006e161179c3ab73798d9b10e466255edb7c3ae6f4c2e3`。  
对抗复核 SHA-256：
`666ba7415278e8e45f481a6215605379b8590eefc784ee6fb3d0f665e978a4d1`。

可从 `runs/wave-002-first-blind-comparisons/` 执行 `python3 verify.py`，重新核验全量产物哈希、
A/B/A+B 分数、15 项 controller receipt，以及
`probe=NOT_RUN / capability=UNKNOWN / outcomes=NOT_OCCURRED` 没有被后续文档或文件静默升级。

## 独立性与外发边界

- 未使用 AgentKey；
- holder、coordinator、solver 和 evaluator 都是不同的 Codex 实例，但都来自同一
  `OpenAI / gpt-5.6-sol` provider，因此是执行隔离，不是模型多样性证据；
- G1 holder 只读取各自 packet，协调者只读取 coordinator 与 holder 输出；
- T2 求解器看不到 oracle，最终候选冻结后 evaluator 才读取 oracle；
- 本地 filesystem 隔离与 prompt allowlist 是 controller 威胁模型，不是抵抗同机恶意进程
  的密码学证明；
- 所有外发材料均为非 NAC 合成材料；NAC 专利交底原文没有进入第三方 payload。

## 当前研究含义

这轮第一次把“为什么已有技术没有解决我们的问题”变成了可测断点：

- 目录失败不在检索能力，而在输入世界没有先提供 query、方向、当前版本和可披露投影；
- 本地智能失败不在感知局部状态，而在缺少跨主体路由、双向 receipt 和关系 handoff；
- 组合解决了两者的大部分互补盲区，但没有自动产生 reciprocal verification；
- 关系、能力、Authority、Effect 和 reopen 的组合可以把一次拒绝推进到合法 probe，但不能
  用条件齐备冒充 probe 已运行。

下一波应同时推进：G1 留出世界与 reciprocal 状态机；T2 bounded probe simulator；以及把
T2 的 Authority/capability/effect/reopen 组合迁移到 T4 joint-bid，验证它不是单一案例拟合。
