# 研究成果地图

## 一、理论与问题定义成果

| 成果 | 它新增的判别力 | 当前身份 |
|---|---|---|
| 静态投影不普遍充分 | 区分“画像里没有”与“任务相关边界尚未问出” | 稳定理论方向；真实最优边界方法未定 |
| 搜索 / 协调 / 构成三分 | 区分已有候选优化与候选、角色、条件本身形成 | 核心问题重写 |
| Capability / Authority 正交 | 阻止模型变强、工具成功被误写成授权扩大 | 稳定设计不变量 |
| Agent Entity / Principal 分离 | 区分可认证代理实体与能作出原生认领、承担责任的主体 | 核心主体模型 |
| Attempt / Effect / Adoption / Acceptance 分离 | 阻止日志、退出码或生产者完成冒充目标世界结果 | 最强工程语义成果 |
| formation / compiled runtime 双制度 | 区分开放边界形成与稳定关系低成本运行 | 有限机制支持；现实复用净值开放 |
| 权威拓扑而非网络拓扑 | 区分分布式部署与不可代行的授权、拒绝、责任 | 待强中心基线进一步判别 |

## 二、协议与系统设计成果

- 版本化 RelationVersion / Shared Artifact；
- scoped、可撤销、可过期的 Mandate；
- claim-specific WitnessPolicy 与 authoritative readback；
- Commitment 与资源预留分离；
- Effect Gateway、Event Ledger 和目标域 adoption receipt；
- Defeater 与 dependency-closure reopen；
- 形成期机制组合与稳定局部编译；
- A2A、MCP、OAuth、VC、策略引擎等作为适配器而非理论本体。

这些设计分布在多轮材料中。v1.1 长文的逐章拆分入口：

- [主体、世界与权威](../02_derived/large-docs/monograph-v1.1/08_4-主体、世界与权威：agent-entity-不是模型实例.md)
- [可能性形成](../02_derived/large-docs/monograph-v1.1/12_8-可能性形成：把-做不了-转化为可构造缺口.md)
- [现实效力链](../02_derived/large-docs/monograph-v1.1/15_11-从-operation-到现实：effect、adoption、acceptance-与-settlement.md)
- [形成与编译](../02_derived/large-docs/monograph-v1.1/16_12-形成期与编译运行期：局部稳定、局部重开.md)
- [多机制 Router](../02_derived/large-docs/monograph-v1.1/17_13-多机制协调：中心化、a2a-与人类判断的组合器.md)
- [系统架构与连接器](../02_derived/large-docs/monograph-v1.1/19_15-系统架构、协议内核与外部连接器.md)

## 三、真正改变设计的实验成果

### R5 / R5.2

- 识别 outer success、终态标签、原始 producer bytes 与 canonical Effect 的差异；
- 把 authoritative readback 提升到完成判定之上；
- 将能力主张从标签改为绑定环境、权限、资源、观察和恢复的合同；
- 局部任务中 least-privilege central 优于更重的主权协调。

### R5.4

- 证明不同权威角色的拒绝和 countercondition 会改变候选规范；
- 同时否定“更多轮次自然形成能力”；
- 保存 central transport failure，避免把缺席基线误作 A2A 胜利；
- 把 `AcceptedOriginalValue=0` 与规范增量同时保留。

### R5C

- 建立跨技术权威域 adopted→revoked→offline→recovered；
- producer-only 与 wrong-authority 路径不能闭合；
- 形成与 holdout 分离，负面和 BLOCK/COUTNER/UNKNOWN 历史不被最终 PASS 擦除；
- 得出“边界形成后，中心确定性执行可以足够”的限域结论。

## 四、校准、工具与保障成果

| 成果族 | 正确价值 | 不应承担的主张 |
|---|---|---|
| 公开制度七案 | 暴露 Standing、Declared/Enacted、五维稳定、制度化 Compile | Towow treatment effect |
| QDR 52 访谈 | 校准多种协调配置和自治/权威变量 | OPC 总体频率或产品效果 |
| 盲化 checkpoint | 高召回风险扫描和 probe 排序 | 自动预言下一变化 |
| 三机制 Replay | 验证版本图保存已编码结构 | 自动理解或商业效果 |
| 本体/materiality 实验 | 验证实现表达和回归 | 现实语义零错误 |
| Fieldkit v0.4–v0.8 | 把理论对象转为可记录、可重算研究仪器 | 生产身份、支付、法律签署 |
| OPCBench | 暴露 Router 构造缺口并形成 CI fixture | 真实成功率或优于强中心/经纪 |

## 五、尚未成为成果的计划

以下内容在最新包中是协议或预注册，不是完成结果：

- Q1 强中心真实模型基线；
- Q2 三人 Mandate explain-back；
- Q3 单案 Q4 causal formation；
- Q4 Router 原始材料盲测；
- Q5 真实重复关系编译净值；
- 完整 H1–H4 真人实验。

