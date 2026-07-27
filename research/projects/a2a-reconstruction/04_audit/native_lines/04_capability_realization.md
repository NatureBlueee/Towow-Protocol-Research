# 原生研究线 04：能力兑现

## 当时面对的真实问题

静态能力标签把“安装了工具”“曾成功”“当前可执行”“有权限”“可恢复”混成一件事。
CRA、Capability Claim 和 Assurance Case 试图把能力改写为环境相关、可验证、会过期的主张，
并区分干预后成功与未来可依赖能力。[SRC-R52-CAPABILITY:3-48]

## 原生机制与能力

### CAP-CAP-001：环境索引能力

- 区分：抽象技能名称与在特定执行器、环境、权限、资源、版本和时间下可兑现的能力。
- 机制：Capability Claim 绑定 executor、environment、authority、resource、recovery、version、time。
- 关键决定：能力不是 Entity 的永久布尔属性。
- 正例：同一 adapter 在 revoked/offline 与 restored 环境下结论不同。
- 移除失败：看到已安装组件就承诺执行，运行时因权限或目标版本失败。
- 来源：[SRC-R52-PATCH:56-73] [SRC-R52-CAPABILITY:28-48]

### CAP-CAP-002：前瞻 holdout

- 区分：对已观察案例的解释与对冻结未见任务的预测。
- 机制：在干预前冻结 claim，在 held-out 条件执行并由独立 readback 判断。
- 关键决定：干预后的成功不能倒推干预前已有能力。
- 正例：R5.2 六轴判断 4/6，优于静态 3/6，但仍未达到预注册门槛。
- 移除失败：用训练/修复后结果回填“原来就会”，产生循环证明。
- 来源：[SRC-R52-CAPABILITY:3-26] [SRC-R52-CAPABILITY:50-69]

### CAP-CAP-003：能力证据的来源与目标 readback

- 区分：执行者日志、自报结果与目标域可验证后置状态。
- 机制：Assurance Case 引用来源、版本、probe、witness 和反例。
- 关键决定：能力证明不能由执行者单方面闭合。
- 正例：目标域读回 adopted/revoked/offline/recovered，而非只看 producer exit code。
- 移除失败：producer-only 路径把写出文件当成目标采用。
- 来源：[SRC-R5C-SUMMARY:39-57] [SRC-R5C-ABLATION:3-27]

### CAP-CAP-004：恢复与有效期边界

- 区分：一次成功与可在故障、撤销和恢复后继续承担的能力。
- 机制：claim 包含 recovery 条件、expiry、Defeater 和重新资格化。
- 关键决定：恢复路径是能力的一部分，不是事后运维备注。
- 正例：同一 projection identity 经 revoked、offline/unknown、recovered 后重新采用。
- 移除失败：首次成功被当永久能力，环境漂移后继续承诺。
- 来源：[SRC-R5C-SUMMARY:39-51] [SRC-R5C-PATCH:1-53]

### CAP-CAP-005：组合、容量与漂移资格化

- 区分：单组件能工作与多个能力、资源、时间窗口组合后可承担。
- 机制：CRA 对组合依赖、容量预留、版本漂移和恢复进行资格化。
- 关键决定：能力组合必须经过资源与依赖 Gate。
- 正例：工具、伙伴和预算同时满足后才把路径提升为可承诺。
- 移除失败：多个单点 claim 同时引用同一稀缺资源，形成空头组合能力。
- 来源：[SRC-R52-PATCH:56-73] [SRC-R5C-METHOD:36-53]

## 原始证据与边界

R5.2 的结果不是“能力模型成立”：六轴 4/6、静态 3/6，干预后 6/6 只能说明条件改变后
动作空间扩大，不证明原 claim 具有前瞻性。[SRC-R52-CAPABILITY:3-26] R5C 的 held-out
只覆盖本地 adapter，不能外推到跨主体能力或商业交付。[SRC-R5C-HOLDOUT:1-27]

## 后续解释与整合结果

v0.4 把 CapabilityEnvelope、AssuranceCase 视为派生视图，避免多个事实源；这是可行的，
前提是底层 Assertion、Operation、Effect、Mandate 和依赖仍能重建 claim。
[SRC-V04-ONTOLOGY:197-283] v0.7 的能力、工具和资源组装恢复了生命周期位置；v1.1
实现了部分可执行绑定，但组合容量、漂移与跨伙伴资格化没有现实证据。
[SRC-V07-OPC:56-73] [SRC-V11-MONOGRAPH:2810-2865]

## 当前保留建议

- 事实：带 provenance 的 Assertion、Mandate、Reservation、Operation、Effect。
- 派生视图：Capability Claim 与 Assurance Case。
- 运行时：资格化 Gate、expiry、recovery、Defeater。
- 研究假说：跨 OPC 组合能力是否能被可靠预测与维护。

