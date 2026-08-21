# 研究线 07-V2：跨规范依赖与有条件局部重开

Contract：`LINE-07-SCOPED-REOPEN-V2 / v1`

状态：`ACTIVE`。ACTIVE 只授权冻结关系图、合成漂移、隐藏依赖评分和强基线比较，不表示
真实关系连续、自动 runtime、真人治理接受或长期净价值已经成立。

本线的 target kind 是 `EXISTING_SOLUTION`，prior-solution disposition 已解析为 `EXTEND`：

- `ADOPT` OpenTelemetry、Temporal history/replay、Camunda version/migration、AWS immutable
  versions、Event Sourcing、Saga、RFC 7009 和人工 amendment 已经承担的通用运行能力；
- `COMPOSE` “不可变合同 + 监控 + 人工 amendment”与成熟
  workflow/event-history/version/migration 两个完整强基线；
- 只 `EXTEND` 尚未被它们自动覆盖的跨 Authority、Evidence、Effect、Acceptance 与
  RelationVersion 依赖后果；不新建包办 workflow、监控和治理的总 runtime。

## ACTIVE：本地冻结案例

在一份完整、不可原地改写的 `RelationVersion` 和显式依赖图上运行：

1. 模型升级但 Mandate 与目标不变；
2. Mandate 被权威来源撤销；
3. 账户暂时离线并恢复；
4. 证据到期、被反证或来源不可验证；
5. Principal 将接受对象从 v1 改为 v2；
6. 一条承重依赖只存在于独立评分面，候选 planner 不得预读；
7. 高耦合与低漂移分布分别允许广域重审或普通 workflow 获胜。

每次运行必须分别返回 `BLOCK`、`VALID`、`UNKNOWN`、重开闭包、edge 理由、历史 Acceptance
及其未来适用性、所需 Principal/Authority 决定、unsafe continuation、漏重开、误重开、恢复
延迟和全生命周期成本。workflow replay、migration 成功、日志存在、进程存活或版本递增都不是
relation continuity。

## BLOCKED

- 在真实长期关系中运行和修改生产 workflow；
- 真人 amendment、重新授权、重新接受与退出决定；
- 生产恢复、现实 Effect、系统级净值和长期治理成本；
- 由合成 precision 推出真实分布安全性。

## DEFERRED

- 自动 Router、完整关系 runtime kernel 和中心/联邦拓扑晋升；
- 在七类漂移和两个强基线比较前登记专用 scoped-reopen mechanism；
- 在依赖不完整或 authority provenance 为 Unknown 时宣称安全最小闭包。

支持结果只能影响 `CLM-017`、`CLM-V2-CONTINUITY-IS-LINEAGE` 和
`CLM-V2-SCOPED-REOPEN-CONDITIONAL` 的候选证据。负结果允许人工 amendment、广域阻断或成熟
workflow 胜出，并且不得改写历史 Acceptance、删除失败或影响其他母线主张。
