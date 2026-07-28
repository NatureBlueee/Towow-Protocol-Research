# NAC 有界机制研究

Profile：`MEC-NAC / v1`

状态：`ACTIVE_RESEARCH`，不是 `VALIDATED_SCOPED`。NAC 有完整历史设计、冻结规格、预注册
实验和失败门，但关键实验没有运行；“研究在继续”与“机制已经证成”必须同时区分。

## 原始问题

在亿级、异构、动态、局部私有且没有全局世界持有者的 Agent 网络中，怎样把方向性的 Intent
或能力转为跨模型可比较、可分级传播、可逐步筛选、可版本演化的外部信号，使大量无关节点
不必运行高级智能，少数潜在相关节点才进入深层判断。

NAC 历史上不是一个随手提出的格式。它拥有：

- 独立问题定义；
- 冻结的 `IF-2 · NAC 信号格式规格`；
- 跨模型锚点、多尺度前缀、SEEK/OFFER、自描述 header、provenance 和版本迁移设计；
- M1 信号生成、M3 路由与披露、M5 演化等配套模块；
- 独立预注册的 `E-H1′` 锚点判别实验，以及尚未运行的 H1–H8 历史验证计划。

当前关键边界是：交接材料明确记录 H1–H8 未运行。因此我们可以确认它是成熟的纸面设计和
正式未决研究线，不能确认它在现实网络中有效。

## 身份承重性与可迁移性是两个维度

1. `MC-NAC-ANCHOR / IDENTITY_CORE + SUBSTRATE_BOUND`：公共外部锚点能否跨模型保持发现
   判别力；
2. `MC-NAC-PREFIX / IDENTITY_CORE + PORTABLE`：多尺度前缀是“Nested”的身份构件，
   同时可能迁移到其他表示；传播剪枝和候选唤醒效果属于 M3 等配套路由假说；
3. `MC-NAC-DIRECTION / IDENTITY_SUPPORTING + PORTABLE`：SEEK/OFFER 是否独立减少同向
   主题误配；
4. `MC-NAC-SELF-DESCRIPTION / IDENTITY_SUPPORTING + PORTABLE`：schema、版本、facet、
   grounding、TTL 与 provenance 是否使信号可解释、可追溯；继续询问依赖 IF-1、M3；
5. `MC-NAC-MIGRATION / IDENTITY_SUPPORTING + CROSS_MECHANISM`：重投影、双写和版本窗口
   与 M1、M3、M5 组合后，能否在演化中保留旧信号关系。

身份承重性回答“失败是否要求 NAC 改名或重建基底”，可迁移性回答“原能力能否被别的表示
继续承载”；两者不能再压成互斥的单一等级。

这里的历史能力 ID 只作精确映射：`CAP-DISC-003` 是跨模型锚点，`CAP-DISC-004` 是前缀式
渐进披露，`CAP-DISC-005` 只表示 SEEK/OFFER 方向性。自描述 header 和迁移接口仍是 NAC
的独立 scoped claims，但当前没有冒用上述三个 ID；以后若形成新的正典能力，另行登记。

`E-H1′` 是这里唯一明确预注册的 NAC 实验。其原门槛是：完成锚点数、选择策略、前缀长度与
聚合函数扫描后，跨厂商 top-100 召回达到同厂商 80%；到饱和仍未达到，或同预算下显著低于
vec2vec，则当前锚点坐标基底选型作废。这个结果可以真正反驳 NAC 的 identity core，不能
被“局部失败”语言稀释；但它不自动删除 SEEK/OFFER、自描述、provenance 或多分辨率信号
等仍可能迁移到其他表示的能力。自然语言加稳定 Schema 是 V2 新增的公平比较臂，不冒充原
预注册内容。

H2 检验前缀排序；H3 属于 M3 包络路由；H4 是 NAC、M1、M3、M5 的迁移计划；H5/H6 属于
M3 quest 与 disclosure；H7/H8 属于 M3/M5 路由反射和联合工作点。把这些 ownership 分开，
是为了不再用配套栈效果替 NAC 格式背书，也不因配套机制失败而删除可迁移能力。

## 明确非目标

NAC 不研究上游怎样从行为数据推断 Intent；不负责授权、承诺、PFE、能力形成、Effect、
Adoption、Acceptance 或 Settlement；不承担开放世界的普遍本体；也不预设中心、联邦或
Gossip 拓扑。

这些非目标不能用来否定 NAC。反过来，NAC 也不能因为自己的信号设计完整，就替代其他研究
线。

## 下一阶段研究门

下一轮不能再只读取压缩后的 native-line 摘要。它应直接冻结原始问题定义、IF-2、总体设计、
专利说明、M1/M3/M5 和 E-H1′，先完成已有方案检查，再逐项运行：

- 锚点 vs vec2vec、自然语言加稳定 Schema 和其他强基线；
- 前缀排序、复杂合取与长尾漏检；
- 包络路由的剪枝、误唤醒和结构性漏检；
- 版本迁移、双写、重投影与反演风险；
- 从中心试验到联邦或混合运行的语义保真。

任何结果都必须返回“受影响 scoped claim—未受影响主张—适用前提—替代解释”。H1 失败
可以反驳坐标基底，但不能自动删除可迁移能力；其他结果也不得越过自己的 owner 和作用域给
整个发现母线一个单一的“升格/降级”结论。

若未来进入 `REFUTED_SCOPED` 或 `REBASE_REQUIRED`，profile 必须同时列出受影响的 claim、
hypothesis、capability 和全部未受影响 claims；不能只留下一个整体状态词。进入
`VALIDATED_SCOPED` 时也只能登记真实完成实验所覆盖的 claim—hypothesis—capability 闭包，
H3/H5–H8 这类配套机制假说不能被塞进 NAC 的已验证范围。
