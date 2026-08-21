# CE-001 现有技术实时边界核验

日期：2026-07-30  
状态：`OFFICIAL-SOURCE BOUNDARY CHECK / PRODUCT RUNS NOT YET PERFORMED`

## 核心判断

现有技术没有“无效”。相反，它们已经分别很好地解决了发现、通信、持久执行和授权判断。
问题尚未整体解决的主要原因是：这些系统通常从一个已经表达、已经建模、已经接入的对象开始，
而 V2 还要求处理这些前提本身如何产生、由谁认领、何时仍然 current、是否真的改变了世界，
以及成功路径怎样沉淀、迁移和局部重开。

这不是新协议已经必要的证据。它首先要求把现有 primitive 按 truth-owner 边界正确串起来，
并在完整任务上运行。若组合后闭合，结果就是通爻的正向完整方案。

## 官方能力与停止位置

| 技术 | 官方已经提供 | 它不会自动提供 | 对 CE-001 / V2 的位置 |
|---|---|---|---|
| Google ARD | 组织发布 catalog，registry 像搜索引擎一样抓取、索引和返回可验证 publisher metadata；支持 MCP、A2A、OpenAPI 等资源 | 没有被发布的主体/能力；query 之前尚未形成的角色与可能性；owner 当前承诺；执行后的 Effect/Acceptance | G1 已表达资源的发现与信任入口。官方明确在发现后“steps out of the way”，后续用原生协议直连 |
| A2A Agent Card / Task | Agent 自述 identity、skills、endpoint、security；消息、长任务、流式和异步交互 | 统一 registry API；server 内部 authorization 的合法来源；自述是否 current/真实；外部 Effect、主体认领和 Settlement | 已知 Agent 的互操作与任务传输，不是开放形成、权利生成或世界结果证明 |
| Temporal | durable workflow state、event history、replay、retry、signal、activity 与 crash recovery | 外部 Activity 是否恰好执行一次；外部系统的 Authority；业务 Effect 是否发生；Acceptance 是否由正确 owner 作出 | G5/G7 的执行与迁移 substrate。官方说明 Activity 在 worker 调用后崩溃仍可能因 timeout 被重试，因此 exact external Effect 仍需 idempotency/readback/reconciliation |
| OPA / Cedar | 对应用提供的 principal/action/resource/context、policy 和 entity data 做 allow/deny 判断 | 相关实体资料是否完整/current；权利是否真实产生；owner 是否理解或认领；执行是否发生 | G5 policy decision。应用仍须收集并提供正确输入，policy engine 不能代替 owner act |
| OpenFGA | 保存 object-relation-user tuples，执行 Check/Read/Expand/List 等关系授权查询 | tuple 是否代表真实且 current 的法律/组织关系；新关系是否被主体形成；外部 Effect/Acceptance | 已物化关系的权限图，不是关系形成或结果验证 |

## 为什么“他们都有”仍没有直接解决完整问题

1. **每个产品只承诺一段箭头。**  
   ARD 找资源，A2A 交换任务，Temporal 保持流程，policy engine 判断已建模请求。没有一个产品
   声称自己同时拥有其他 owner 的事实、权利、承诺、目标系统状态和价值验收。

2. **必要前提通常由应用负责。**  
   Catalog、Agent Card、policy entity slice、relationship tuple、workflow activity 和
   idempotency scope 都要先由某人正确构造。未声明 Intent、未形成角色、错误 object/version
   或 stale owner state 不会因为接入成熟产品而自动消失。

3. **内部完成不蕴含外部 Effect。**  
   workflow history、outbox published、A2A task completed 或 policy allow 都可能全绿，但
   目标电路未送电、送错对象、已送电却 ACK 丢失、owner 已撤销或 Acceptance 尚未发生。

4. **Authority 与技术控制权不是同一件事。**  
   U/D 环境中的合法中心可以完整获胜；P 环境中的管理员账号、API token 或相同文件权限不能
   代替独立 Principal 的 non-delegable act。这一差异必须由实验环境给出，不能由 controller
   自报。

5. **生态问题比单次 episode 更大。**  
   CE-001 可验证一条已知目标的完整 episode；它尚未验证未预编译角色/伙伴/动作的开放形成、
   重复关系降本、跨 episode 稀缺资源冲突、伙伴退出后的替代和 material difference 的局部
   重开。即使 CE-001 完全闭合，也只能关闭其 scoped family。

## 当前下一步

- 继续 CE-001，实际比较最强现有组合，不因其“只是组合”而降级；
- product 未安装/未运行继续写 `NOT_RUN`；
- 把 CE-001 定位为 `RelationEpisode` 级端到端验收；
- 另建开放生态任务，取消预给角色、伙伴和 formation label，使最强现有组合能够真正挑战
  V2 的 `RelationEcology` 问题；
- 只有在两级任务上都出现重复、同边界 residual 后，才创建有界创新候选。

## 官方来源

- Google Developers Blog, [Announcing the Agentic Resource Discovery specification](https://developers.googleblog.com/announcing-the-agentic-resource-discovery-specification/)
- A2A, [Protocol specification](https://google-a2a.github.io/A2A/specification/)
- A2A, [Agent discovery](https://google-a2a.github.io/A2A/latest/topics/agent-discovery/)
- Temporal, [Workflow Execution overview](https://docs.temporal.io/workflow-execution)
- Temporal, [Activity Execution](https://docs.temporal.io/activity-execution)
- Open Policy Agent, [HTTP API authorization](https://www.openpolicyagent.org/docs/http-api-authorization)
- Cedar, [How authorization works](https://docs.cedarpolicy.com/auth/authorization.html)
- OpenFGA, [Authorization concepts](https://openfga.dev/docs/authorization-concepts)

来源证明各产品的官方作用域；“停止位置”和跨产品组合判断是本研究的推断，尚未由真实产品
端到端运行验证。
