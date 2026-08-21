# G2-O1 owner evidence + open-schema discriminator

状态：`IMPLEMENTED / LOCAL SYNTHETIC ONLY`

## 研究问题

本候选不预设新 Relation engine。它只检验两个较窄的问题：

1. 在 controller 不持有全部 Principal key、方法只看到各自合法 local view 的条件下，能否
   分别判断 `constituted / understood / claimed / authorized / activated`，而不把签名、
   workflow completion 或统一摘要误当成主体理解和认领；
2. 在 schema、必要角色、private column 或 relation-level constraint 未预编码到方法输入时，
   structured human institution、equal-envelope strong center、成熟组件组合或签名副本能否
   正确保持 `Unknown / Withheld / Refused / Stale`，并识别真正的 schema reopen。

强中心、成熟采购/CLM/CMMN/IAM/HITL、人工制度或平台直达若完整解决，均是正结果。签名副本
不因“分布式”获得先验加分。

## 12-world 冻结分母

- 4 个 fresh T2-blind：参数变化与真正 schema change、理解与误解、current 与 stale stance；
- 4 个 fresh T4-held-out：private column absent/withheld、局部异议、relation-level coupled
  constraint；
- 2 个 T5 platform-direct controls；
- 2 个 Authority topology pressures：shared institution 与 plural authorities 下的
  partition/equivocation。

公开 fixture 不保存 `relation_valid`、`material_change`、`opposition_preserved` 等可直接
读取的答案。private oracle 只供独立 evaluators 使用；方法 worker 不得读取它。

## Truth-owner 分域

```text
world/schema author
  ├─ public task + initial schema
  ├─ PrincipalActor_i ─ local view + independent key + refusal/claim policy
  ├─ PrivateColumnOracle ─ ABSENT/WITHHELD/DISCLOSED/UNDISCLOSABLE
  ├─ ConstitutionEvaluator ─ institution + exact version + constitutive acts
  ├─ AuthorityEvaluator ─ mandate/revoke/reservation/current head
  └─ TargetAcceptanceOwner ─ activation/readback/acceptance

method worker
  └─ sees only public packet and routed owner events
```

签名只证明相应 actor 对精确字节作证；结构化 explain-back 的内容正确性由独立 comprehension
evaluation 判断。`FORMED`、`AUTHORIZED` 和 `ACTIVATED` 不互相自动推出。

## 比较臂

- `structured_human_institution`
- `equal_envelope_strong_center`
- `actual_mature_composition`
- `signed_replicated_state`

四臂使用相同 owner actors、local-oracle API、Authority endpoint、task Q 和观察预算。
Authority topology 是 world 环境，state placement 是方法实现变量；结果按同一 topology
内的 central/replicated 对比报告，禁止把 shared/plural trust root 的变化归因给 storage。

## 指标

首要五轴：

- `constituted`
- `understood`
- `claimed`
- `authorized`
- `activated`

另报 schema-change detection/false reopen、private-column recall/false infeasible、
provenance/opposition round-trip、stale/revoke、duplicate reservation、
partition/equivocation recovery，以及可观察的询问、披露、人工、操作和恢复成本。

## 证据边界

本实验是 12 个手工构造 world 上的本地合成 discriminator。scripted owner 只支持
`SCRIPTED_OWNER_CONFORMANCE`，不支持真人理解、现实授权、真实 Effect、成熟产品部署、
长期漂移或 V1/V2 一般解。测试绿灯只说明当前实现满足已写入的攻击合同。

## 复现与冻结结果

依赖：Python 3、`cryptography`；运行测试还需要 `pytest`。

```bash
python3 runner.py
python3 -m pytest -q tests/test_g2o1.py
```

冻结输出为 `outputs/results.json`：

- 12 worlds × 4 arms = 48 runs，四臂逐 world 完整覆盖；
- 五轴 true 计数：`constituted=24 / understood=44 / claimed=24 /
  authorized=32 / activated=24`；
- method 五轴对 event-derived reference：`240/240`；
- schema-change：`48/48`；opposition provenance round-trip：`48/48`；
- 每个 world 的四臂五轴完全相同，未观察到 signed replicated state 的 relation-semantic
  增益，也未观察到需要新增 G2 专属机制的 residual；
- 两个 T5 control 四臂均走 4-operation platform-direct 路径，不创建 relation artifact；
- 本次冻结 runner 实测 `51.28s`，报告 106 个 distinct owner actor PIDs。

冻结 SHA-256：

- `fixtures/public_worlds.json`：
  `c67a6c8ac1ac872cc6940ba8dea233b0a8624fe096468f1c412632210ab08a12`
- `private/oracle.json`：
  `58c9cb16802be29dbc443067410f0eac1c6325c3a51e09686bb0b7e8c8dec018`
- `outputs/results.json`：
  `7437ba36a238b5aef5fffb13c20c6209d011a5cf48776447db7b02ceff95d4a4`

内部研究者 C 在加 T5 专门断言前的最终敌对复核为 `12 passed in 101.72s`，包含 baseline
与 private `expected.axes` 全反转后的第二次 48-run；两次 measured axes/diagnostics
完全相同。根会话随后加入 T5 真旁路断言并重新运行最终套件：
`13 passed in 201.78s`。较长用时来自两次完整 48-run 子进程执行，是当前实现的实际成本
负结果，不是可扩展性通过。完整攻击历史与判断见本 cohort 的 `G2-final.md`。
