# 当前全局理解

更新时间：2026-07-27  
来源截点：`Towow_Complete_Research_Archive_v1.2_2026-07-27`

## 研究对象

材料共同指向的问题不是“Agent 怎样通信”，而是：

> 当一个对外可归因、可授权、可追责的 Agent Entity 内部可能包含人、模型、工具、账户、
> 工作流和多个局部权威，并与其他不可互相代行的主体发生关系时，怎样使一个尚未完整定义
> 的机会成为可理解、可拒绝、可形成、可承诺、可执行、可见证、可采用、可接受、可复用和
> 可重新打开的现实行动。

因此，A2A、中心 Agent、平台、确定性服务、人类经纪和人工裁决都是候选机制。研究边界由
问题、信息和权威结构决定，不由部署拓扑或协议名称决定。

## 材料中存在的七个互相连接、但不应被熔平的研究核

| 研究核 | 它处理的缺口 | 代表性历史结构 |
|---|---|---|
| 发现与边界 | 静态画像无法穷尽任务相关行动空间 | HDC、FHRR、NAC、BIC、Boundary Oracle |
| 问题与关系构成 | 任务、角色、动作和条件本身尚未稳定 | Coordination Schema、SJAC、JAA |
| 可能性形成 | “当前不可行”可能缺工具、伙伴、权限或新的任务表示 | Unknown 分类、PFE、formation operator、countercondition |
| 能力兑现 | 一次成功不能支撑未来承诺 | CRA、Capability Claim、AssuranceCase |
| 权威与规范 | 模型判断、身份、授权、认领和承诺不能互相替代 | Principal、Agent Entity、Authority Locus、Mandate、Standing、Commitment |
| 现实效力 | 执行日志不能证明目标世界改变或主体接受 | ActionAttempt、Effect、Verification、Adoption、Acceptance、Settlement |
| 运行与演化 | 形成不能无限持续，稳定关系也不能永久冻结 | Harness、Compiled World、Defeater、scoped reopen、mechanism Router |

六个 canonical roots 是 v0.4 以后形成的**实现收敛候选**，不是对上述七个研究核的替代。
一个研究核没有成为 aggregate root，不意味着其问题已经消失。

## 当前最强的经验支点

1. R5/R5.2 证明，外层成功、终态标签和生产者自述不足以证明目标世界 Effect；R5.2 的
   17 个真实 Harness 场景中，naive 终态标签错 10 次。
2. R5.2 能力 holdout 没有全部过门，迫使 Capability Claim 绑定执行器、环境、权限、
   资源、观察和恢复，而不是使用静态能力标签。
3. R5.4 是负结果：真实模型多轮互动形成了更丰富的条件，却没有签署、补丁、目标域采用
   或被接受的新能力；中心基线又因传输失败而没有得到公平结论。
4. R5C 是最强的有限建设性证据：在技术权威域内，probe、拒绝、最小 countercondition、
   目标域 readback、撤销和恢复共同形成了一条此前不可运行的路径；它仍不是现实人类
   Principal 或商业净值证据。

## 当前最有信息量的系统假说

材料支持但尚未充分判别的架构次序是：

1. 先提供 Mandate、RelationVersion、Effect、Acceptance 和 reopen 等权威语义；
2. 能被成熟制度、平台、确定性服务或可信中心无损处理的任务直接折叠；
3. 私有世界不能授权集中、可信 Hub 不存在或权威不可代行时，才保留联邦关系；
4. 未稳定局部使用适应性形成，稳定局部编译运行；
5. 新 Defeater 只重开受影响依赖。

这个顺序不是现行事实。Q1 强中心基线仍未完成，因此“语义价值大于拓扑价值”只能作为待判别
假说。

## OPC 的位置

OPC 是首发参数区，不是理论边界。它把四个变量推到容易观察的区域：

- Authority Locus 更集中；
- 高认知注意力更稀缺；
- 既有制度框架较薄；
- 冷启动关系通常较低对抗、较易撤回。

大型机构材料已经说明同一表示可跨尺度工作，但没有证明同一产品形态或协调成本函数跨尺度
成立。

## 当前证据空白

- 真实用户能否理解、修订和撤销显式 Mandate；
- 一个强中心 Agent 在公平信息、工具、权限和 Effect Gate 下能做到什么；
- 是否存在真实 Principal 参与、过消融、进入 Q4 Effect 的 causal formation；
- Router 判据能否从未编码的真实材料可靠获得；
- 第一次形成以后，第二次运行是否真的降低人类注意力、披露、验证和错误成本；
- 策略性虚报、边界钓取、权力不对称和第三方外部性如何改变机制。

## 能力审计后的当前结构

历史能力审计识别了 39 项设计能力：15 项保留、5 项转换、18 项部分保留、1 项明确丢失。

明确丢失的是第二轮本地 `column generation`：当前 `RelationVersion` 能保存最终候选，却没有
owner 负责“候选在私有世界生成，只提交改善当前解的最小贡献，中心无权取得完整行动集”。

主要部分损失集中在：

- HDC/NAC 的发现协议行为和前缀披露预算；
- Boundary Oracle 的 cut/witness/unknown/refuse 类型提升；
- JAA 的多作者贡献回放；
- Unknown 到 formation action 的路由；
- prospective capability holdout 和组合容量；
- Harness 三类 IR、Context Compiler 和 Evidence Closure；
- Router 从未经编码材料冷启动的能力。

现实效力链、精确版本 Stance、Mandate、Commitment/Reservation 和负状态恢复是保真度最高的
部分。

完整判断见 [历史设计能力审计](../04_audit/README.md) 和
[当前系统能力图](../04_audit/current_system_capability_map.md)。

## 读者不应从当前材料推出的结论

- 不应推出“联邦 A2A 普遍优于中心化”；
- 不应推出“六个 root 已完整表达所有历史设计能力”；
- 不应把合成样本量、测试数或零错误自评分当作现实证据；
- 不应把公开制度档案或 QDR 访谈当作 OPC 用户效果；
- 不应把 R5C 的技术权威域闭环写成人类主体的真实认领；
- 不应把 v1.2 的决策程序误作已完成实验。

## 主要来源

- 最新包当前状态：`00_START_HERE/CURRENT_RESEARCH_STATE.md`
- 原始研究谱系：关键来源 `SRC-HANDOFF-LINEAGE`
- R5.2 当前系统修订：`SRC-R52-PATCH`
- R5.4 核心实验与净值：`SRC-R54-CORE`、`SRC-R54-NET`
- R5C 当前修订与形成记录：`SRC-R5C-PATCH`、`SRC-R5C-FORMATION`
- v1.2 决策账本：物理文件
  `02_WORKSPACE_SNAPSHOT/Towow_v1.2_Decision_Program/evidence/decision_ledger.csv`

这些短 ID 的完整路径见 [关键来源登记](../01_catalog/SOURCE_REGISTER.md)。
