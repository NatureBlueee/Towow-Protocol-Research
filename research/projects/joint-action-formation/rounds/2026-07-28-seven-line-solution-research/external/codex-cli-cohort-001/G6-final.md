核心结论：Wave010 的 `7/7` 应降格为“完美 oracle 条件下的开发型布线正例”，不能解释成 G6/G7 已跨 authority 闭环。成熟组件组合仍是当前最佳方案；但 owner readback、因果归属、freshness、connector migration 和 compensation residual 仍是开放的 conformance residual，尚无证据要求发明新协议。

建议状态：

`POSITIVE_DEVELOPMENT_MODEL / PERFECT_ORACLE_UNTESTED / T3_SYNTHETIC_CANDIDATE / T4_NOT_RUN / CROSS_AUTHORITY_RESIDUAL_OPEN`

## 1. 对现有 7/7 的攻击结论

当前 7/7 的真正因果范围是：

> 如果 broker 能即时、正确、无成本地获得五层 truth 和 dependency current head，成熟组合与合法强中心都能把这些答案正确路由。

主要失效点：

- `broker_method_view()` 直接从同一 `world["truth"]["layers"]` 复制五层 readback；dependency query 也直接复制 private truth，不是五个独立 authority service。[Simulator readback](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SIMULATOR.py:96)
- `REVOKED` 对应的三个 reopen 节点被策略源码硬编码，没有真的遍历 dependency graph。[Hard-coded closure](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SIMULATOR.py:160)
- evaluator 只比较 owner 字符串和 `TRUE`，不检查 operation、causal ID、对象版本、head、freshness、签名、前态或并发归因。[Evaluator owner check](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SIMULATOR.py:190)
- false-negative 只计算漏 Effect，不计算漏 Adoption、Acceptance、Settlement，也不要求重建 `FALSE/REFUSED/PENDING/UNKNOWN`。[Missed Effect only](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SIMULATOR.py:202)
- 因而，一个新增的假想 arm 即使只读 Effect 与 dependency oracle、完全忽略 Adoption/Acceptance/Settlement，也能通过现有七门。
- duplicate/recovery 是由 retry profile 与 fixture 布尔值计算，不是从目标 ledger 的真实 effect-count delta 得出。
- 4 个 world 只有 T2/T3/T6；没有 T4、connector migration、stale/refused readback、补偿残差或真实 Settlement。文档自己也明确七门不是 PROGRAM coverage，并承认 dependency API 可能只是包装 private oracle。[Synthesis boundary](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SYNTHESIS.md:185)

所以 7/7 有正价值：它说明“控制拓扑不是决定变量，合法 observation 才是”。但它没有证明 observation 的形成、保鲜、迁移与独立性。

## 2. T2/T3/T4 实际 truth-owner 矩阵

| 任务 | Attempt | Effect | Adoption | Acceptance | Settlement | 当前证据 |
|---|---|---|---|---|---|---|
| T2 企业只读试点 | 服务方 execution ledger；绑定 container、operation、causal ID、买方 sandbox/permission | 买方 sandbox audit；输出 hash、零 raw export、目标 commit | 买方真实 backlog/work-system 变更 | 买方业务 Principal 对精确 output/goal/version 的 stance | 若进入范围，由采购/财务 ledger 建立；原案例未冻结结算 trace | 原案例是答案泄漏型设计；Wave010 另造了 `TRUE/FALSE/FALSE/REFUSED/PENDING` 反例 |
| T3 资源请求 | 候选 makerspace job controller | machine-job ledger；artifact/job identity、材料和完成时刻 | 请求方 inventory/chain-of-custody | 请求方设计 Principal 对精确 prototype 验收 | invoice/payment/refund/chargeback ledger | 原 R7 只是执行资源清单；makerspace 是新 synthetic candidate，不能算历史或现实任务。[T3 correction](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/TASK-TRUTH-CORRECTION-001.md:12) |
| T4 联合投标 | 必须拆开：bid submission attempt 属授权提交者+portal；后续 operational attempt 属实际 executor | `CITY-OPERATIONS` ledger + signed target readback | 当前 oracle 定义为城市 shortlist notice | exact bid-version 的 award notice | CITY payment ledger | 当前所有外部 outcomes 均 `NOT_OCCURRED`；G6 正向链尚未运行。[T4 oracle](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/wave-003-c-joint-bid/oracle/truth.json:525) |

一个重要修正：五个事实不是普遍线性梯子，而是 task-specific DAG。T4 的时序可能是：

```text
submission
→ shortlist（采购 Adoption）
→ award（对 bid 的 Acceptance）
→ operational Attempt
→ CITY-OPERATIONS Effect
→ milestone/payment Settlement
```

因此 `Acceptance=true` 如果不绑定 `object_kind` 和 exact version，connector migration 很容易把“中标”错误翻译为“履约效果已验收”。每项状态至少要绑定 owner/head、对象版本、operation/causal ID、时间、freshness、来源、负状态以及 causal/dependency edge。X2 候选合同已经写出了这一正确要求，但 Wave010 simulator 尚未实现。[X2 five-owner contract](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-X2-INPUT-CONTRACT-CANDIDATE.md:535)

## 3. 误晋升与漏 Effect 边界

必须阻断的误晋升：

- `transaction committed / outbox published / CloudEvent delivered / workflow completed → Effect`
- portal receipt或 eligibility → Adoption/Acceptance
- Effect → Adoption → Acceptance → Settlement
- audit、probe、performer log → target-domain Effect
- hash → 语义正确；signature/receipt → signer 是正确 Authority；event bus → 现实结果发生
- Saga compensation completed → 原世界已恢复
- 多份 outbox/CDC/event-sourcing 记录 → 多个独立 Effect
- 历史 Acceptance → 新版本、未来用途或生产上线也被接受

现有 evaluator 漏掉的 Effect 边界：

- target Effect 已发生，但 readback/ACK 延迟；
- readback 是旧 projection，返回陈旧 `FALSE`；
- 当前 postcondition 由前态或第三方并发动作建立，并非本 Attempt 所致；
- connector A 已 commit，迁移到 connector B 后 causal identity 丢失；
- Adoption/Acceptance 失败，但不可逆物理 Effect 仍存在；
- 补偿后仍有材料消耗、通知、隐私披露、库存或声誉 residual；
- owner 返回 `STALE/UNKNOWN/REFUSED/TIMEOUT`，系统错误压成 `FALSE`；
- 正确终态掩盖中间第二次 Effect——Wave007 已真实暴露过这一 evaluator 盲区。[Wave007 duplicate L3](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-007-AUDIT-STATUS.md:106)

## 4. 当前最佳成熟组合

```text
attempt-time Authority/current-head gate
→ 原子绑定 causal ID / idempotency scope
→ local transaction + transactional outbox
→ durable workflow / retry / timer
→ CloudEvents / CDC 运输
→ target-domain Effect readback
→ operational Adoption readback
→ exact-object human Acceptance
→ Settlement ledger readback
→ append-only history + Saga residual/dispute
→ dependency/current-head query
→ CONTINUE | BLOCK | RECOVER | LOCAL/GLOBAL_REOPEN | HUMAN_AMEND
```

组件的公平责任边界：

| 组件 | 已经解决 | 没有自动解决 |
|---|---|---|
| Transaction/outbox | 单数据库业务写与待发布事件原子化 | 外部 target Effect |
| CloudEvents/CDC | envelope、数据库变化传播 | 事件语义、Authority、Adoption |
| Event sourcing | 本 store 的历史与重放 | 其他 authority 的当前事实 |
| Durable workflow | retry、timer、持久编排和恢复 | workflow green 是否在现实中作数 |
| Saga | 有界补偿编排 | 世界回到原态、补偿 residual 消失 |
| Idempotency | 冻结 scope 内去重 | 跨 connector/scope、非幂等外部 target |
| Independent readback | 一个目标域的 postcondition | 其他四层与因果归属 |
| Human acceptance | Principal 对精确对象接受/拒绝 | Effect、Adoption、Settlement |
| 强中心 | 计算、等待、缓存、路由、恢复决策 | 不能代签外部 owner；无新 observation 时不能破解隐藏依赖 |

因此行业组件在自己的局部合同里基本已经解决问题。尚未自动解决的是这些合同之间的非蕴含跨越。若 truth owner API 与迁移 conformance 成立，这个成熟组合就是通爻 G6 的正向完整方案，不需要新 event bus 或新五层事实根。

## 5. 是否存在跨-authority residual

当前判断是“有开放 residual，但尚未证明它需要新协议”：

- readback 是否确实来自当前 authority head，而不是缓存、旧 epoch 或代理副本；
- postcondition 是否由本次 exact operation 造成；
- owner 能否返回 `UNKNOWN/REFUSED/STALE/CONFLICTING` 并允许后到证据更新；
- Acceptance 是否绑定正确对象、目标与 RelationVersion；
- Settlement 是否需要多个账本共同构成，而非单个 finance 标签；
- connector migration 是否保留 owner、head、causal ID、负状态、争议、补偿 residual 与 dependency；
- dependency API 是否现实存在、及时、合法、可负担，而不是免费 oracle。

hidden dependency 在合法 transcript 完全相同时是信息论边界，强中心也无法猜中。只能创建新的合法 observation、保持 `BOUNDED_UNKNOWN` 并 broad block/global reopen，或由有权主体 discovery/amendment。

## 6. 下一轮 held-out 设计

至少冻结七组、由不同 owner/evaluator 构造的 opaque worlds：

1. workflow-green：target commit / reject / DLQ。
2. preexisting/concurrent Effect：当前快照相同，但 causal attribution 不同。
3. timeout-before-commit / timeout-after-Effect × same/split causal ID。
4. Adoption=true × Acceptance=`TRUE/REFUSED/UNKNOWN/wrong-version`。
5. fresh readback / validly signed stale head / rollback-after-read。
6. compensation complete / residual / compensation itself fails。
7. connector migration lossless / owner-head 丢失 / enum 压缩 / dedup namespace 改变。
8. dependency query=`CURRENT/REVOKED/UNKNOWN/REFUSED/STALE/TIMEOUT`。

必要纪律：

- 五层和 dependency 分属独立 package、runtime key、append-only ledger；不得共享 `world_factory`、truth dataclass、expected table、keyspace 或 writer。
- Effect 同时评分 state、归因、causal identity、对象/version/head 和 count delta。
- 五层都分别计算 false promotion、false negative、wrong owner、wrong object/version；不再只测漏 Effect。
- owner API latency、披露、人工、拒绝和成本进入记录。
- truth 泄漏、免费 oracle、无法冻结前态或缺 base trace时整轮标 `INVALID/NOT_RUN`，不能算 candidate 失败。

Connector migration 要做 old/new connector 对同一 owner store 的只读 shadow readback和 round-trip，对 `TRUE/FALSE/UNKNOWN/REFUSED/STALE/REVOKED` 分别验证；cutover 后必须从目标域重新 readback，而不是相信迁移工具自报。

## 7. 低风险真实 readback 设计

不执行，仅作为下一阶段候选：

- T2：纯合成数据、买方控制的隔离 test namespace。服务方只能提交 exact operation；买方审计凭据独立读取 artifact、commit index、causal ID、head；买方 test backlog 单独决定 Adoption；Principal 在另一界面对 exact artifact 接受/拒绝；不付款。注入 ACK loss，并做 v1/v2 connector 双读。
- T3：资源 owner 的专用测试日历中创建无现实占用价值的 dummy slot；请求者、资源 owner、adopting calendar、human accepter 使用分离账户；测试拒绝、counter、撤销、ACK-loss-after-commit 和迁移；不启动机器、不占生产容量、不付款。

出现真实个人/客户数据、生产 namespace、付款、不可逆资源占用、owner credential 无法分离或清理路径不明确时停止。即使成功，也只支持这两个 sandbox，不外推生产或商业价值。

## 8. 最终证据边界

- 历史最强局部证据仍是 R5.2：naive 标签在 17 场景错 10 次，authoritative readback 重建 17/17；它支持语义分离，不支持真人 Acceptance 或跨域普遍性。[Native G6](/Users/nature/通爻协议研究/research/projects/a2a-reconstruction/04_audit/native_lines/06_reality_effect.md:56)
- Wave006 的 45/45 因 truth label、authority key 和 evaluator 泄漏失效，只留下 signer 自晋升攻击 4/4 被拒绝。[Wave006 invalidation](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-006-AUDIT-INVALIDATION.md:64)
- Wave007 A2 支持本地 synthetic 的 attempt-time idempotency、bytes-bound chain 和 L3/L4 分离，但不是 blind、独立实现或现实证据。[Wave007 boundary](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-007-AUDIT-STATUS.md:221)
- Wave010 自身状态已经正确标为 `LOCAL_SYNTHETIC DEVELOPMENT RUN / NOT X2 / NO FORMAL PROMOTION`。[Wave010 status](/Users/nature/通爻协议研究/research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/WAVE-010-G6-G7-SYNTHESIS.md:1)

本轮严格只读；未改文件、未运行生产或外部真实动作。