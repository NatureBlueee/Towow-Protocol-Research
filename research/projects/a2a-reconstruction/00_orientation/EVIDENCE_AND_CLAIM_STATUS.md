# 证据与主张状态

## 证据角色

| 角色 | 定义 | 当前代表 |
|---|---|---|
| DECISIONAL | 反向结果本可以改变设计，实际结果导致或限制了设计 | R5、R5.2、R5.4、R5C |
| CONFIRMATORY | 结果主要确认已决定方向，仍可说明适用边界 | Boundary、概率、部分历史诊断 |
| CI / ASSURANCE | 防止实现退化或抓住被建模捷径 | 并发、本体、materiality、mutation |
| ARCHIVAL_CALIBRATION | 发现现实变量与反例，不估计 treatment effect | 七案、QDR、OPC 公开语料 |
| INSTRUMENTATION | 使将来的真实问题可观察、可复算 | Fieldkit、事件目录、研究导出 |
| PREREGISTERED / OPEN | 已设计但未执行或未完成 | Q1–Q5、真人实验 |

## 当前稳定主张

| 主张 | 支撑 | 作用域 |
|---|---|---|
| Attempt 不等于 Effect | R5、R5.2 | 真实 Harness 与相似异步执行链 |
| Effect 不等于 Adoption / Acceptance | R5.2、R5C | 目标域采用与主体接受必须有各自权威 |
| Capability 与 Authority 正交 | 形式反例、R5/R5.2 工程事实 | 不推出具体 UI 或法律效力 |
| 生产者不能自证消费者采用 | R5C 消融与 readback | 单宿主、本地、合成技术源 |
| 多轮协商不自然保证新能力 | R5.4 负结果 | 当前任务和模型配置 |
| 形成后可由较简单中心执行 | R5C 局部闭环 | 冻结接口和有限技术域 |

## 受支持但必须限域的主张

- 任务相关边界可能比全量静态披露更有效；
- probe、countercondition、工具、伙伴和授权可能形成新路径；
- 版本化权威图能保留形成、撤销和重开历史；
- 某些稳定关系可以被编译成确定性运行；
- 不同权威和制度环境可能需要不同机制组合。

它们尚未得到真实 OPC 的因果净值、长期复用和策略行为证据。

## 已降级或被推翻的主张

- `NAC` 作为普遍跨主体语义基础；
- 软件仓库或进程自动等于真实 Principal；
- 多轮 A2A 自然创造新能力；
- 主权 A2A 普遍优于中心；
- 测试、checksum、完整包或绿色状态足以证明现实完成；
- 一次成功足以建立可承诺能力；
- v0.3 报告中的大样本数字在缺少原始实现时可承担独立复现。

## 当前开放主张

- Authority-aware central Hub 是否已覆盖绝大多数近期产品价值；
- 显式 Mandate 是否能被 OPC 用户准确维护；
- 现实 causal formation 是否存在且净增益为正；
- Router 判据是否可从真实原始材料可靠获取；
- 编译复用是否降低真实高认知成本；
- 联邦拓扑在哪些信息与权威条件下不可折叠；
- 对抗、权力和第三方外部性是否会使当前形成机制失效。

## 原始账本

- v1.2 决策账本：
  `02_WORKSPACE_SNAPSHOT/Towow_v1.2_Decision_Program/evidence/decision_ledger.csv`
- v1.2 证据重分类：
  `02_WORKSPACE_SNAPSHOT/Towow_v1.2_Decision_Program/evidence/evidence_reclassification.csv`
- 原始交接证据状态：`SRC-HANDOFF-EVIDENCE`

