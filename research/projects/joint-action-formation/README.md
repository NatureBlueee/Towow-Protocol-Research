# 共同可行动性构成：核心试点

本项目是有界自治研究环境的第一个试点。`Problem v0 / SEED` 已完成七线定义批次；
`Problem v1 / CANDIDATE` 作为第一份正式问题快照完整保留；当前正式问题是
`Problem v2 / ACTIVE`。

V2 不是重写 V1。它用前序文件 SHA-256 完整继承 V1，并显式冻结后续独立研究者必须共享的
世界前提、服务对象、核心区别、评价框架和有界机制研究范式。用户已经通过
`DEC-2026-07-28-ACTIVATE-PROBLEM-V2`，按五件材料闭包的精确哈希激活 V2；候选文件继续
作为不可覆写的激活来源，promotion receipt 记录实际生成物。问题激活没有自动激活任何
研究线、场景、机制主张或现实行动。

## 当前版本关系

1. `problem/v0.json`：历史 `SEED` 和 R4 问题定义批次锚点；
2. `problem/v1-candidate.json`：保留的第一份候选问题快照；
3. `problem/v2-candidate.json`：V2 的不可覆写候选来源和共享知识底座；
4. `problem/v2.json`：当前 `ACTIVE` 问题，由精确用户决定和 promotion receipt 约束；
5. V1 与 V2 并存；新版本不把旧版本标记为错误或 `SUPERSEDED`；
6. 研究线激活、机制稳定化和现实场景仍需各自独立的用户决定。

## 七条原生线

1. 发现与边界
2. 问题与关系构成
3. 可能性形成
4. 能力兑现
5. 权威与规范
6. 现实效力
7. 运行与演化

每条线继承历史能力审计中的 capability ID，但不因名称存在而获得正确性。它必须说明：
去掉本线区分后会重新出现什么错误，什么结果会缩窄哪个有界主张，以及什么场景能够判别。

七条线是问题家族，不是七个大一统机制。历史默认不要求每批同时运行；用户已明确要求
2026-07-28 新一轮七条母线同时启动，当前调度以
`rounds/2026-07-28-seven-line-solution-research/PROGRAM.md` 为准，并在并发资源有限时分波完成
每线的异质多 Agent 职责。现有七份 v0 合同作为历史快照保留；V2 机制通过新的 2.0
LineContract 逐项迁移和按需运行。运行器只允许
`line.problem_ref` 与所选 Problem 精确一致的 `ACTIVE` 线进入批次。

## 有界机制研究

机制统一登记在 `mechanisms/`。每项机制分别记录：

- 环境与前提；
- 原始问题；
- 承诺能力和逐项 scoped claim；
- 明确非目标；
- 当前证据状态、失败和开放问题；
- 历史机制与现成方案检查；
- 只影响受检验主张的结果策略；
- 无损替代与整合条件。

首个恢复的 profile 是 `MEC-NAC / v1`。它处于 `ACTIVE_RESEARCH`，因为历史上有独立规格、
预注册和失败门但关键实验未运行。相应的 `LINE-01-NAC / v1` 当前是 `ACTIVE`：它属于
“发现与边界”母线，且只冻结 `E-H1′ → MC-NAC-ANCHOR`，不会自动带起 H2–H8、其他六条
问题家族或配套 M3/M5 机制。新一轮另用七件 closure manifest 确保研究者直接读取 IF-2、
总体设计、专利说明、M1/M3/M5 与 B7/E-H1′，但这仍不等于它们已被验证或全部激活。

一个机制没有解决其作用域外问题，不构成降级。一个子主张失败，只改变该子主张。现成平台、
标准、制度或 adapter 完整满足要求时直接复用；部分满足时只扩展缺口；只有确认真实缺口后
才创建新机制。组合与整合必须保留原正例、能力和移除失败。

## 当前入口

- 2026-08-01 研究结果、理由与独立规划收口：`settlements/2026-08-01-full-settlement/README.md`
- 当前 V2 人类说明：`problem/v2.md`
- V2 不可覆写候选来源：`problem/v2-candidate.md`
- V2 历史继承审计：`problem/v2-history-alignment.md`
- V2 激活材料闭包：`problem/activation/v2.json`
- V2 promotion receipt：`promotions/PRB-JOINT-ACTION-FORMATION-DEC-2026-07-28-ACTIVATE-PROBLEM-V2.json`
- V1 保留快照：`problem/v1-candidate.md`
- NAC 机制档案：`mechanisms/nac.md`
- NAC ACTIVE 研究线：`lines/01-nac.md`
- 当前七母线研究纲领：`rounds/2026-07-28-seven-line-solution-research/PROGRAM.md`
- NAC 七件输入闭包：`rounds/2026-07-28-seven-line-solution-research/nac-seven-archive-manifest.json`
- 生命周期成本与价值：`economics/lifecycle-cost-model.md`
