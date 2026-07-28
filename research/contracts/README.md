# 研究契约

这里的 Schema 只保护会影响判断的边界，不规定研究结论或统一理论。

- `ProblemContract` 决定正在研究什么，以及什么会推翻或重开它。
- `ScenarioContract` 把抽象问题绑定到可判别的具体世界、权威和结果。
- `LineContract` 允许异构研究线保持自己的问题与失败机制。
- `RunManifest` 固定一次运行实际看见的输入、工具和成本。
- `ResearchResult` 强制区分观察、来源、推断、设计建议和负结果。
- `ClaimCandidate` 记录主张的证据边界；自动研究不能把它晋升为 `STABLE`。
- `HistoricalInheritanceAudit` 不要求旧术语继续成为正式对象，但要求每个历史设计能力都有
  明确的保留、降级、缺口或有证据拒绝去向。默认项目中的候选与激活问题不得省略它；
  `ACTIVE` 问题还必须绑定状态为 `REVIEWED` 且建议为 `READY` 的审计。

Schema 通过 `python3 tools/researchctl.py validate` 校验。完整状态转换和人工门禁由
`researchctl` 的语义检查负责，不能只依赖 JSON 字段合法。
