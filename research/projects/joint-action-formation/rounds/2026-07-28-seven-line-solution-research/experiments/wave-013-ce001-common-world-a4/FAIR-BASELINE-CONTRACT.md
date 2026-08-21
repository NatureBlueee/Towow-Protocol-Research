# Wave 013 公平现有方案基线合同

状态：`IMPLEMENTATION CONTRACT / NOT YET RUN`

本合同的目标不是证明通爻独特，而是最大化现有平台、合法中心、通用模型、成熟组件和人类
制度完整解决 CE-001 的概率。任一单臂或这些方案的合法组合完整解决，都是通爻的正向成果。

## 1. 当前证据边界与先决红灯

当前 A4 收到语义 `case_id`，`run_id/operation_id` 也包含 `e1/e5`，并直接按 E1/E5 选择
执行或拒绝分支。因此现有结果支持：

- 已知分支下 `Authority → EXECUTE → Effect → Acceptance → Finality` 的原生因果闭合；
- 已知 E5 分支的有界停止；
- evaluator 对当前已覆盖证据攻击的判别能力。

它不支持未知 case 下的辨认、路由或一般求解。公平比较前必须：

- evaluator-private manifest 保留 `case_id`、authority stratum 和 private truth；
- arm-visible manifest 只含 opaque `episode_handle`、Q、target、预算、接口和绑定哈希；
- `run_id`、`operation_id`、目录名、ordering 和错误文本不泄漏 case；
- E3A/E3B 在允许交互前保持相同 method-visible prefix；
- A4 在无语义标签条件下重新运行；旧结果保留，不回写成新证据。

## 2. 共同合法世界

每个 arm 从独立 world clone 开始。各 clone 的 truth、事件 schedule 和任务相同，但 PID、
keys、state、run 和 native logs 完全分离，arm 间不得继承答案。

共同冻结：

- 同一 `Q@v1`、原始价值底线、必要 Principal 和 target；
- 同一 public bytes、endpoint schema、owner/target 返回语义；
- 同一合法 Authority topology，不允许 controller 或 adapter 改写；
- 同一 action grammar、90 分钟逻辑 horizon 和故障注入；
- 同一 query、disclosure、target attempt、retry、recovery 与总经济预算；
- 同一独立 evaluator，但不同 decision implementation；
- 禁止 private truth、expected label、future decision、grader output 和跨臂答案进入 arm。

公平不是把不同方法削成相同实现。平台的预编译流程、合法中心的完整控制、模型推理和人的
判断都是各臂的 native treatment，但其费用、披露、维护和失败必须按实记录。

共同预算使用向量：

```text
B = {
  deadline,
  owner_queries,
  disclosed_bytes_and_sensitivity,
  target_attempts,
  retry_and_recovery_ops,
  total_economic_cost,
  human_minutes,
  compute_and_tool_cost
}
```

deadline、披露、target attempt 和总经济价值上限共同约束；各 arm 可以在允许的 native
资源内选择分配，不能靠扩大 Authority、读取更多 truth 或降低 Q 获胜。

## 3. Native adapter 边界

adapter 只可：

- 转换协议和字段；
- 校验签名、freshness 与 exact binding；
- 传输请求并保存原生返回；
- 记录时间、披露、费用和错误。

adapter 不得：

- 选择 action、路线、拒绝、重试或恢复；
- 补造 Authority、Effect、Acceptance、Settlement；
- 读取 private truth 或 expected label；
- 共享 `_common_candidate`、`choose(packet)` 或其他 decision root；
- 把 shape-compatible fixture 冒充实际运行的产品。

平台无法导出足以验证的 native receipt 时，记 `UNSCORABLE/NOT_RUN`，不得由 adapter
生成 Towow-shaped 成功证据。

## 4. A0–A5 native arms

### A0 — Direct Platform

平台用自己的 provision/booking/control/readback 流程承担任务。只有平台原生结果能够绑定
exact Q、target、Authority、Effect、双 Acceptance 与 Finality 时才算完整；仅完成搜索、
预订、支付或管理员控制属于部分能力。

applicability 必须由 arm 可见的签名平台能力和 Authority 事实建立，不能由 private case
label 路由。平台未覆盖的 case 不计作平台机制失败，也不能获得完整 family 覆盖。

### A1 — Lawful Strong Center

单一中心用自己的全局 case store、policy、transaction/workflow 和 target control 闭合
任务。A1 只适用于 `U / LAWFULLY_UNIFIED` 或 `D / EXACT_DELEGATION`；不得在
`P / PLURAL_INDEPENDENT` 代签 owner。

A1 在其合法范围内完整解决就是正解。作用域外 `NOT_APPLICABLE` 不降级 A1，但 A1 也不能
据此宣称 CE-001 全 family 完成。

### A2 — Equal-information Center

A2 同样使用单一中心协调器，但只能通过独立 owner APIs 行动，不能替代任何 owner。它与
其他臂拥有相同 information/API/action envelope。

A1/A2 必须分开：否则会把“P 中不存在合法集中 Authority”误判为“中心计算能力不足”。
若 A2 与 A4 的状态、决策和恢复没有实质区别，应把 A4 视作 A2 的一个独立实现，而不是用
不同名称重复计数。

### A3 — General Model + Mature Stack

通用模型独立负责澄清后的规划和工具选择；独立 policy gate、durable workflow、fence、
readback 与 settlement rail 执行动作。模型不是事实、Authority 或 Effect 的来源。

必须保存模型版本、实际输入输出、工具调用、拒绝和重试。若移除模型、换成固定策略后仍完整
通过，则正解归属于成熟 stack；这仍是正向结果，不是失败。

### A4 — Deterministic Mature Composition

A4 使用独立规则、workflow、IAM、outbox、fence、readback 和必要 HITL，不使用通用模型
推理。它必须从合法 owner/target 返回决定行为，不能按 case label 选择脚本。

当前 A4 只建立已知 E1/E5 分支的 scoped causal closure；完成无标签八案前，不得登记为
CE-001 完整解。

### A5 — Human Institution + Minimal Console

A5 必须由真实 human coordinator 在同一信息、时间、action 和 Authority envelope 内运行。
console 只展示签名事实、校验字段并发送结构化动作，不得推荐路线或自动修正人的决定。

human coordinator 不是 Principal，除非世界中存在相应合法授权。用模型模拟人类只可作为
fixture，实际未有人参与时必须记 `NOT_RUN`。

## 5. 两类报告

### Capability-max

每个 native arm 在同一总价值预算内尽力解决任务。它回答“今天可以用什么完整解决”，用于
采用、组合、简化和关闭不必要创新。

### Equalized-causal

使用 A2、组件移除、模型消融、truth transplant、case-label permutation 和行为 mutation，
回答究竟哪个组件产生了结果。它解释因果贡献，但不能替代 capability-max 的完整任务结果。

两类报告不得混成单一分数，也不能以某组件增量为零否定整个现有组合的解题价值。

## 6. 成本与生命周期攻击

所有 arm 分别报告：

```text
C_cold  = 采购/规则建立/集成/培训/安全认证
C_run   = 查询/披露/模型/人力/等待/执行
C_fail  = 越权/错对象/重复 Effect/机会损失/争议恢复
C_maint = 更新/漂移/重新认证/人员流失
C_exit  = 导出/替换/历史连续性/自持替代
```

至少运行以下生命周期攻击：

1. `PROVIDER_STOP`：平台、模型或组件停止维护后，安全拒绝、readback 与恢复是否仍可用；
2. `FORMAT_EXIT`：导出后 Authority、签名、依赖和历史谱系是否丢失；
3. `PROVIDER_SWAP`：替换 provider 后能否重放同一任务；
4. `SECURITY_AND_DRIFT`：漏洞修复、模型升级、policy/Q change 后需重建多少规则。

分别报告 cold、repeat 和 drift 后成本。不能只比较 token，也不能把锁定、退出、治理和恢复
成本藏在一次运行之外。

## 7. 完整解决三级判据

### `COMPLETE_WITHIN_APPLICABILITY`

A0、A1 等有界 arm 在其依法适用的全部 case 中完整闭合。它是正向结果，但不等于 CE-001
全 family 完成。

### `CE001_POSITIVE_SCOPED_SOLUTION`

单一 arm 或现有方案 portfolio 必须同时满足：

- 无语义 case label 运行；
- 七个可达 case `7/7 ExactTaskSuccess`；
- 八个 case `8/8 CorrectResolution`；
- unsafe、wrong-object、duplicate、history rewrite 均为 0；
- E4 恢复任务价值，E5 不越权，E6 恢复完整谱系；
- remove/reverse/migrate、blind holdout 与第二实现复现；
- 协调、验证、恢复、维护和治理成本未吞噬任务价值。

### `V1/V2 COMPLETE`

CE-001 是已知 Q、owner 和 action grammar 下的 RelationEpisode，不能单独证明 V1/V2
开放世界完整解决。后者仍需真实 Principal、开放行动空间、跨域 holdout、RelationEcology
及长期复用与漂移证据。

## 8. Existing-tech portfolio 是完整正解

不要求一个 arm 统治所有 case。只依赖合法公开证据的 router 可以将：

- 平台原生 case 路由给 A0；
- U/D 路由给 A1；
- P、异常和恢复路径路由给 A2/A3/A4/A5 中实际通过者。

router 自身必须无标签、可审计，并把误路由、等待和维护计入成本。如果这一 portfolio 满足
CE-001 全部判据，应登记：

```text
EXISTING_TECHNOLOGY_PORTFOLIO = POSITIVE_SCOPED_SOLUTION
NOVEL_MECHANISM_NECESSITY_FOR_CE001 = CLOSED
```

这不是妥协，也不是通爻增量为零；它就是当前范围内找到、复现和组织起来的完整解决方案。
