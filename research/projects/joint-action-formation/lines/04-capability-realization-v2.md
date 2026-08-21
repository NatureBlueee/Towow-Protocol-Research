# 研究线 04-V2：指定操作的前瞻能力兑现

Contract：`LINE-04-CAPABILITY-REALIZATION-V2 / v1`

状态：`ACTIVE`。本状态只授权开展 Problem v2 下的本地、有界、可逆研究；不表示
`SC-CAP-PROSPECTIVE-REALIZATION` 已获得支持，也不表示 CRA 或 Capability Claim 已成为正式
机制或权威事实。

本线立即启动 `E-CAP-01-PROSPECTIVE-REALIZATION`：在相同 held-out operation、首次执行
机会、probe、资源与人工预算下，比较：

1. `STATIC`：安装状态、自报与历史成功；
2. `MATURE-COMPOSITE`：provenance、eval/CI、IAM、health/readiness、telemetry、
   reservation、workflow 与 recovery；
3. `DERIVED-CLAIM`：在相同底层事实之上增加 operation、environment、authority、
   resource、freshness、oracle、expiry、recovery 与 Defeater 的派生闭包。

能力判断必须在首次尝试前冻结。修复、补路径、改变 temp root、增加权限或重做 reservation
后的成功是 intervention，不能回填成原 claim 的前瞻正确。Oracle 至少分开保存 executor
result、authoritative postcondition 与独立 readback；producer 文本、安装状态和外层 exit
code 都不能单独闭合。

本线采用 `EXTEND`，不是 `NEW_GAP`。成熟系统已分别承担 provenance、策略、probe、
telemetry、审批、资源和恢复；当前只检验跨来源派生视图是否在未见任务和漂移上产生不可由
更小组合重建的额外判别力。若没有，Capability Claim 应降为 adapter 或查询，不建立第二套
正式现实。

允许立即开展：本地 manifest、合成 held-out、错误 provenance、权限/approval 差异、资源
竞争、dependency/version drift、revocation 与 recovery replay。需要真实账户、生产写入、
现实资源预留或扩大权限时必须停止并另取授权。

本线不启动或证明 Principal 授权、Commitment、关系形成、目标域 Effect、Adoption、
Acceptance、Settlement、稳定商业履约或一般 Agent 能力。任何结果只能更新
`SC-CAP-PROSPECTIVE-REALIZATION`；其他母线与 NAC 主张保持不受影响。
