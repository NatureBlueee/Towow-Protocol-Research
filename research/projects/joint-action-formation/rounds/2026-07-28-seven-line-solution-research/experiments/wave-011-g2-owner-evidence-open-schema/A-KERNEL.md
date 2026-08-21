# G2-O1 A 线：原生 kernel、open-schema 与局部认领数据面

状态：`IMPLEMENTED / LOCAL SYNTHETIC / NOT OWNER-OBSERVED`

本文件只说明 A 线交付，不晋升 G2、V1/V2、LineContract 或任何机制状态。12 个 world 是
fresh synthetic discriminator，不是真人关系、实际产品运行或现实频率样本。

## 1. 文件与访问边界

- `fixtures/public_worlds.json`：方法、runner、actor router 和 evaluator 都可读；
- `private/oracle.json`：只允许 actor router、分域 evaluator 和最终 scorer 按职责读取；
- `g2o1/kernel.py`：method-neutral 结构推导，不内置 world expected answers；
- Principal actor 的私钥由 owner-actor 实现各自生成和持有，不进入 public fixture，也不由
  本 oracle 集中保存。`private/oracle.json` 只保存 actor 的局部可见事实与脚本行为模型。
  T4 held-out 的关系级约束先只出现在相应 schema owner 的 local view，由该 actor 生成可归因
  schema proposal event；method 不能直接读取 `private_facts.schema_observation`。

公开 fixture 的顶层 shape：

```text
{
  schema_version,
  experiment_id,
  evidence_level,
  worlds: [
    {
      world_id,
      family,
      task_skin,
      authority_topology,
      state_placement,
      clock,
      principal_ids,
      base_relation,
      candidate_relation,
      public_context,
      event_schedule,
      query_budget,
      cost_rates
    }
  ]
}
```

每个 relation 都有 `version / schema / parameters`。Schema 分为 `roles / actions / evidence /
exit_rules / evaluation_rules / constraints`。公开 world 不含 author 预先给出的有效性、变化
类型或异议保真答案。

private oracle 顶层为：

```text
{
  schema_version,
  experiment_id,
  access,
  worlds: {
    WORLD_ID: {
      local_views: {
        PRINCIPAL_ID: {
          visible_facts,
          comprehension_model,
          stance_policy
        }
      },
      private_facts,
      column_case,
      constitution_rules,
      authority_facts,
      activation_facts,
      expected: {axes, diagnostics}
    }
  }
}
```

Runner 必须把一个 Principal 的 `local_views` 单独路由给对应 actor；不得把整个 oracle 发给
actor 或 method。constitution evaluator 只消费构成规则与已验证 owner events；Authority
evaluator 只消费 `authority_facts`；target owner 只消费 `activation_facts`。`expected`
仅用于运行后的审计 cross-check，不得进入 method、actor、evaluator 或 runtime scorer 的
axes/diagnostics 推导；把整个 expected block 反转或删除必须不改变 measured execution。

## 2. 12-world 分母

| family | worlds | 承重变量 |
|---|---:|---|
| `T2_BLIND` | 4 | 真 schema delta / 参数更新、正确理解 / 漏解、current / stale stance |
| `T4_HELD_OUT` | 4 | column absent、存在但按 owner policy withheld、局部异议、关系级耦合约束 |
| `T5_CONTROL` | 2 | 标准 SaaS 直接完成、标准支付中有效拒绝；复杂形成路径应旁路 |
| `AUTHORITY_PRESSURE` | 2 | shared institution + equivocation；plural recognized authorities + partition |

Authority topology 与 state placement 没有捆绑。压力 world 的
`state_placement=METHOD_VARIABLE`，同一 world 可由 central canonical、replicated
canonical 或 plural local-state arm 处理。共享制度与多 Authority 的变化必须报告为
environment interaction；不能把它归因于 distributed storage。

## 3. Kernel API

`canonical_digest(value)`

- 对 canonical JSON bytes 取 SHA-256；
- 绑定精确 relation version 或 actor event content；
- digest 绑定不等于理解或认领。

`analyze_schema_delta(base_relation, candidate_relation)`

- 只从结构差异推导 `IDENTICAL / PARAMETER_ONLY / SCHEMA_DELTA`；
- presentation-only 字段和 list 顺序不构成 schema delta；
- 输出 `changed_paths / added_values / removed_values`，不能只用位置或 world id 判定；
- 新版本必要性是结构判断，不等于 Principal 已认领。

`aggregate_owner_evidence(candidate_digest, required_principals, events, comprehension)`

- 当前 claim 必须绑定 candidate digest；
- stale claim 被单列，不能迁移；
- `OBJECT / COUNTER / LIMITED_CLAIM / REFUSE` 保持 actor、scope 与来源边界；
- comprehension 是独立 evaluator 的输入，不能用 digest equality 代替。

`assess_private_column(column_case, response)`

- 区分 `ABSENT_CORRECT / FOUND / MISSED / POLICY_UNDISCOVERABLE / POLICY_BREACH /
  FABRICATED_COLUMN`；
- WITHHELD 是 Principal policy 的合法结果，不是假定“不存在”；
- column 只是 candidate contribution，不构成 stance、Authority 或 Commitment。

`evaluate_coupled_constraints(constraints, assignments)`

- 支持 `ALL_TRUE / AT_LEAST_ONE / IMPLIES / EQUAL / NOT_BOTH / SUM_LTE`；
- 用于关系级 constraint，避免逐条款都绿却遗漏联合不可行。

`derive_axis_result(...)`

- 分别输出 `constituted / understood / claimed / authorized / activated`；
- 不允许由一个 green state 自动推出其他轴。

`load_public_worlds(...)` 与 `load_private_oracle(...)`

- 校验 12-world family 分母、world ID 唯一性、expected 五轴完整性；
- public loader 会拒绝直接答案键；
- loader 只验证形状，不证明 actor 独立性、签名有效或现实 truth。

## 4. 当前能区分什么

这套数据面使 runner 可以检测：

- schema delta 与参数/措辞变化；
- 正确 digest 但理解错误；
- 正确理解但拒绝、局部异议或 stale stance；
- private column 真实 absent 与 policy-withheld 的不同错误；
- 逐条款局部通过但 relation-level coupling 失败；
- Authority 已存在但关系未被 owner claim，或关系已构成但尚未 activation；
- shared institution 与 plural authority topology 在相同 state-placement arm 下的恢复；
- T5 平台 direct / valid refusal 是否被不必要流程拖慢；
- schema reopen、actor query、private query、state message、human review 和 recovery 的成本。

成熟采购、CLM、CMMN、IAM、HITL、强中心或实际成熟组合完整解决任一作用域都是正结果；
kernel 不为新协议保留分数。

## 5. 不能支持什么

- scripted owner 不是实际 Principal，故只能支持 `SCRIPTED_OWNER_CONFORMANCE`；
- synthetic comprehension probe 不是现实主体理解；
- private oracle 是 benchmark truth，不是现实制度本身；
- shared-key 文件隔离不是 hostile same-UID security；
- 12 worlds 不支持现实频率、产品 adoption、商业净值或 V1/V2 一般结论；
- topology pressure 只能支持当前 fault model 下的状态分叉与恢复差异；
- 即便 signed replicated state 胜出，也不能把分布式升为 G2 身份核心；
- 即便所有现成方案失败，也必须先排除观察权、Authority、预算、披露和 actor 行为差异，才能
  提出精确 residual。
